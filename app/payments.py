"""Telegram Stars payment logic for premium subscriptions."""

import datetime
import logging
from typing import Any

from aiogram.types import LabeledPrice

from .db import SessionLocal
from .models import User

logger = logging.getLogger(__name__)

PREMIUM_PRICE_STARS = 10
PREMIUM_PLUS_PRICE_STARS = 100
SPREAD_SINGLE_PRICE_STARS = 15
PREMIUM_DAYS = 30


def _now_for_field(field: datetime.datetime | None) -> datetime.datetime:
    """Return current UTC time, stripped of tzinfo if the DB field is naive."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if field is not None and field.tzinfo is None:
        return now.replace(tzinfo=None)
    return now


def _field_is_active(field: datetime.datetime | None) -> bool:
    """Check if a datetime field is in the future."""
    if not field:
        return False
    now = _now_for_field(field)
    return field > now


def _is_premium(telegram_id: int) -> bool:
    """True if user has Premium OR Premium+ active."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return False
        return _field_is_active(user.premium_until) or _field_is_active(user.premium_plus_until)
    finally:
        db.close()


def _is_premium_plus(telegram_id: int) -> bool:
    """True only if user has Premium+ active."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return False
        return _field_is_active(user.premium_plus_until)
    finally:
        db.close()


def _activate_premium(telegram_id: int, days: int = PREMIUM_DAYS) -> datetime.datetime:
    """Activate or extend Premium subscription. Returns new expiry date."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        base = user.premium_until if user.premium_until and user.premium_until > now else now
        user.premium_until = base + datetime.timedelta(days=days)
        db.commit()
        return user.premium_until
    finally:
        db.close()


def _activate_premium_plus(telegram_id: int, days: int = PREMIUM_DAYS) -> datetime.datetime:
    """Activate or extend Premium+ subscription. Returns new expiry date."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        base = user.premium_plus_until if user.premium_plus_until and user.premium_plus_until > now else now
        user.premium_plus_until = base + datetime.timedelta(days=days)
        db.commit()
        return user.premium_plus_until
    finally:
        db.close()


def _get_premium_info(telegram_id: int) -> dict[str, Any]:
    """Return premium status info for display."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return {"premium": False, "premium_until": None, "plus": False, "plus_until": None}
        return {
            "premium": _field_is_active(user.premium_until),
            "premium_until": user.premium_until,
            "plus": _field_is_active(user.premium_plus_until),
            "plus_until": user.premium_plus_until,
        }
    finally:
        db.close()


async def send_premium_invoice(bot: Any, chat_id: int) -> None:
    """Send Telegram Stars invoice for Premium subscription."""
    await bot.send_invoice(
        chat_id=chat_id,
        title="Premium подписка Таро",
        description="Безлимит на быстрые предсказания — 30 дней",
        payload="premium_30d",
        currency="XTR",
        prices=[LabeledPrice(label="Premium 30 дней", amount=PREMIUM_PRICE_STARS)],
    )


async def send_premium_plus_invoice(bot: Any, chat_id: int) -> None:
    """Send Telegram Stars invoice for Premium+ subscription."""
    await bot.send_invoice(
        chat_id=chat_id,
        title="Premium+ подписка Таро",
        description="Безлимит на ВСЕ предсказания — 30 дней",
        payload="premium_plus_30d",
        currency="XTR",
        prices=[LabeledPrice(label="Premium+ 30 дней", amount=PREMIUM_PLUS_PRICE_STARS)],
    )


async def send_spread_single_invoice(bot: Any, chat_id: int, spread_key: str) -> None:
    """Send Telegram Stars invoice for a single spread purchase."""
    await bot.send_invoice(
        chat_id=chat_id,
        title="Расклад Таро (разовый)",
        description="Один развёрнутый расклад Таро",
        payload=f"spread_single:{spread_key}",
        currency="XTR",
        prices=[LabeledPrice(label="Расклад (разовый)", amount=SPREAD_SINGLE_PRICE_STARS)],
    )
