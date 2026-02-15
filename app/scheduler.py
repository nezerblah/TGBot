from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from .db import SessionLocal
from .models import Subscription
from .horo.parser import fetch_horoscope
import os

MSE_ZONE = ZoneInfo("Europe/Moscow")

async def send_daily(bot):
    db = SessionLocal()
    try:
        # collect signs
        signs = db.query(Subscription.sign).filter(Subscription.active==True).distinct().all()
        signs = [s[0] for s in signs]
        for sign in signs:
            text = await fetch_horoscope(sign)
            subs = db.query(Subscription).filter_by(sign=sign, active=True).all()
            for sub in subs:
                try:
                    await bot.send_message(sub.user.telegram_id, text)
                except Exception:
                    pass
    finally:
        db.close()


def setup_scheduler(bot):
    sched = AsyncIOScheduler(timezone=MSE_ZONE)
    # register coroutine job directly; pass bot as arg
    sched.add_job(send_daily, CronTrigger(hour=11, minute=0, timezone=MSE_ZONE), args=[bot])
    sched.start()
    return sched
