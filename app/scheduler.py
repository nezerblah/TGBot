from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
import logging
import asyncio
import os
from .db import SessionLocal
from .models import Subscription, User
from .horo.parser import fetch_horoscope

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


def setup_scheduler(bot):
    """Setup and start APScheduler"""
    try:
        enabled = os.getenv("SCHEDULER_ENABLED", "false").strip().lower() == "true"
        if not enabled:
            logger.info("Scheduler is disabled. Set SCHEDULER_ENABLED=true to enable daily distribution.")
            return None

        hour = int(os.getenv("SCHEDULER_HOUR_MSK", "11"))
        minute = int(os.getenv("SCHEDULER_MINUTE_MSK", "0"))

        sched = AsyncIOScheduler(timezone=MSK_ZONE)
        # register coroutine job directly; pass bot as arg
        sched.add_job(
            send_daily,
            CronTrigger(hour=hour, minute=minute, timezone=MSK_ZONE),
            args=[bot],
            id="send_daily",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        sched.start()
        logger.info(f"Scheduler started. Daily horoscope will be sent at {hour:02d}:{minute:02d} MSK")
        return sched
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}", exc_info=True)
        raise
