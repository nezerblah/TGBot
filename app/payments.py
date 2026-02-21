"""Telegram Stars payment logic for premium subscription."""

import datetime
import logging

from aiogram.types import LabeledPrice

from .db import SessionLocal
from .models import User

logger = logging.getLogger(__name__)

PREMIUM_PRICE_STARS = 50
PREMIUM_TITLE = "Premium подписка Таро"
PREMIUM_DESCRIPTION = "Безлимитные предсказания Таро на 30 дней"
PREMIUM_DAYS = 30


def _is_premium(telegram_id: int) -> bool:
    """Check if user has an active premium subscription."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user or not user.premium_until:
            return False
        return user.premium_until > datetime.datetime.now(datetime.timezone.utc)
    finally:
        db.close()


def _activate_premium(telegram_id: int, days: int = PREMIUM_DAYS) -> datetime.datetime:
    """Activate or extend premium subscription. Returns new expiry date."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        now = datetime.datetime.now(datetime.timezone.utc)
        base = user.premium_until if user.premium_until and user.premium_until > now else now
        user.premium_until = base + datetime.timedelta(days=days)
        db.commit()
        return user.premium_until
    finally:
        db.close()


async def send_premium_invoice(bot, chat_id: int) -> None:
    """Send Telegram Stars invoice for premium subscription."""
    await bot.send_invoice(
        chat_id=chat_id,
        title=PREMIUM_TITLE,
        description=PREMIUM_DESCRIPTION,
        payload="premium_30d",
        currency="XTR",
        prices=[LabeledPrice(label="Premium 30 дней", amount=PREMIUM_PRICE_STARS)],
    )
