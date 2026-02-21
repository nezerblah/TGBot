import asyncio
import logging
import os
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import SessionLocal
from .horo.parser import fetch_horoscope
from .models import Subscription, User
from .tarot import draw_random_card

logger = logging.getLogger(__name__)

MSK_ZONE = ZoneInfo("Europe/Moscow")


def _load_recipients_by_sign() -> dict[str, list[int]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(Subscription.sign, User.telegram_id)
            .join(User, User.id == Subscription.user_id)
            .filter(Subscription.active)
            .all()
        )
        recipients: dict[str, list[int]] = {}
        for sign, telegram_id in rows:
            recipients.setdefault(sign, []).append(telegram_id)
        return recipients
    finally:
        db.close()


def _load_tarot_daily_subscribers() -> list[int]:
    """Return list of telegram_ids for users subscribed to daily tarot."""
    db = SessionLocal()
    try:
        rows = db.query(User.telegram_id).filter(User.tarot_daily_subscribed.is_(True)).all()
        return [telegram_id for (telegram_id,) in rows]
    finally:
        db.close()


async def send_daily(bot):
    """Send daily horoscopes to all subscribers"""
    try:
        logger.info("Starting daily horoscope distribution...")
        recipients_by_sign = await asyncio.to_thread(_load_recipients_by_sign)

        for sign, recipients in recipients_by_sign.items():
            try:
                text = await fetch_horoscope(sign)
                logger.info(f"Sending horoscope for {sign} to {len(recipients)} subscribers")

                for telegram_id in recipients:
                    try:
                        await bot.send_message(telegram_id, text)
                    except Exception as e:
                        logger.error(f"Failed to send message to user {telegram_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to fetch horoscope for {sign}: {e}")

        logger.info("Daily horoscope distribution completed")
    except Exception as e:
        logger.error(f"Error in send_daily: {e}", exc_info=True)


async def send_daily_tarot(bot):
    """Send daily tarot card to all subscribed users at 10:00 MSK."""
    try:
        logger.info("Starting daily tarot distribution...")
        subscriber_ids = await asyncio.to_thread(_load_tarot_daily_subscribers)

        if not subscriber_ids:
            logger.info("No subscribers for daily tarot distribution")
            return

        for telegram_id in subscriber_ids:
            try:
                card = draw_random_card()
                caption = (
                    f"🃏 <b>{card['name']}</b> ({card['name_en']})\n"
                    f"Аркан: {card['number']}\n\n"
                    f"{card['meaning']}"
                )
                try:
                    await bot.send_photo(telegram_id, photo=card["image"], caption=caption, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Failed to send tarot photo to {telegram_id}, sending text only: {e}")
                    await bot.send_message(telegram_id, caption, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send daily tarot to user {telegram_id}: {e}")

        logger.info(f"Daily tarot sent to {len(subscriber_ids)} users")
    except Exception as e:
        logger.error(f"Error in send_daily_tarot: {e}", exc_info=True)


def setup_scheduler(bot):
    """Setup and start APScheduler"""
    try:
        enabled = os.getenv("SCHEDULER_ENABLED", "false").strip().lower() == "true"
        if not enabled:
            logger.info("Scheduler is disabled. Set SCHEDULER_ENABLED=true to enable daily distribution.")
            return None

        hour = int(os.getenv("SCHEDULER_HOUR_MSK", "13"))
        minute = int(os.getenv("SCHEDULER_MINUTE_MSK", "13"))

        sched = AsyncIOScheduler(timezone=MSK_ZONE)
        sched.add_job(
            send_daily,
            CronTrigger(hour=hour, minute=minute, timezone=MSK_ZONE),
            args=[bot],
            id="send_daily",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        sched.add_job(
            send_daily_tarot,
            CronTrigger(hour=10, minute=0, timezone=MSK_ZONE),
            args=[bot],
            id="send_daily_tarot",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        sched.start()
        logger.info(f"Scheduler started. Daily horoscope: {hour:02d}:{minute:02d} MSK, Daily tarot: 10:00 MSK")
        return sched
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}", exc_info=True)
        raise
