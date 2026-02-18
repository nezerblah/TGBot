from fastapi import APIRouter, Request, Header, HTTPException
import os
import logging
import time
import asyncio
from sqlalchemy.exc import IntegrityError
from .bot import process_update
from .db import SessionLocal
from .models import ProcessedUpdate
from .rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_UPDATE_AGE_SECONDS = int(os.getenv("MAX_UPDATE_AGE_SECONDS", "300"))


def _get_webhook_secret() -> str:
    return os.getenv("WEBHOOK_SECRET", "")


def _extract_update_timestamp(update: dict) -> int:
    # Prefer message/edited_message/callback message timestamp if present.
    for key in ("message", "edited_message"):
        msg = update.get(key)
        if msg and isinstance(msg, dict) and isinstance(msg.get("date"), int):
            return msg["date"]
    cb = update.get("callback_query")
    if cb and isinstance(cb, dict):
        msg = cb.get("message")
        if msg and isinstance(msg, dict) and isinstance(msg.get("date"), int):
            return msg["date"]
    return 0


def _mark_update_processed(update_id: int) -> bool:
    """Persist update id and return False for duplicates."""
    db = SessionLocal()
    try:
        record = ProcessedUpdate(update_id=update_id)
        db.add(record)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    finally:
        db.close()


@router.post("/")
@limiter.limit("60/minute")
async def telegram_webhook_root(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    return await telegram_webhook(request, x_telegram_bot_api_secret_token)


@router.post("/webhook")
@limiter.limit("60/minute")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    webhook_secret = _get_webhook_secret()

    if not webhook_secret:
        logger.error("WEBHOOK_SECRET is not configured")
        raise HTTPException(status_code=503, detail="Webhook secret is not configured")

    # If a secret is configured, require Telegram to send it via header
    if x_telegram_bot_api_secret_token != webhook_secret:
        logger.warning("Webhook secret mismatch")
        raise HTTPException(status_code=403, detail="Forbidden")

    update = await request.json()
    if not isinstance(update, dict) or "update_id" not in update:
        # Treat non-Telegram POSTs as ok (health checks, etc.)
        return {"ok": True}

    # Drop duplicate or stale updates
    update_id = update.get("update_id")
    if isinstance(update_id, int):
        is_new_update = await asyncio.to_thread(_mark_update_processed, update_id)
        if not is_new_update:
            return {"ok": True}

    ts = _extract_update_timestamp(update)
    if ts:
        age = int(time.time()) - ts
        if age > MAX_UPDATE_AGE_SECONDS:
            logger.info(f"Dropping stale update age={age}s id={update_id}")
            return {"ok": True}

    try:
        await process_update(update)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)

    return {"ok": True}
