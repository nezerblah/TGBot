from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
import logging
from .db import SessionLocal
from .models import Subscription
from .horo.parser import fetch_horoscope

logger = logging.getLogger(__name__)

MSE_ZONE = ZoneInfo("Europe/Moscow")

async def send_daily(bot):
    """Send daily horoscopes to all subscribers"""
    db = SessionLocal()
    try:
        logger.info("Starting daily horoscope distribution...")
        # collect signs
        signs = db.query(Subscription.sign).filter(Subscription.active==True).distinct().all()
        signs = [s[0] for s in signs]

        for sign in signs:
            try:
                text = await fetch_horoscope(sign)
                subs = db.query(Subscription).filter_by(sign=sign, active=True).all()
                logger.info(f"Sending horoscope for {sign} to {len(subs)} subscribers")

                for sub in subs:
                    try:
                        await bot.send_message(sub.user.telegram_id, text)
                    except Exception as e:
                        logger.error(f"Failed to send message to user {sub.user.telegram_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to fetch horoscope for {sign}: {e}")

        logger.info("Daily horoscope distribution completed")
    except Exception as e:
        logger.error(f"Error in send_daily: {e}", exc_info=True)
    finally:
        db.close()


def setup_scheduler(bot):
    """Setup and start APScheduler"""
    try:
        sched = AsyncIOScheduler(timezone=MSE_ZONE)
        # register coroutine job directly; pass bot as arg
        sched.add_job(send_daily, CronTrigger(hour=13, minute=13, timezone=MSE_ZONE), args=[bot], id='send_daily')
        sched.start()
        logger.info("Scheduler started. Daily horoscope will be sent at 13:13 MSK")
        return sched
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}", exc_info=True)
        raise
