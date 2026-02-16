from fastapi import APIRouter, Request, Header, HTTPException
import os
import logging
import time
from .bot import process_update

router = APIRouter()
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
MAX_UPDATE_AGE_SECONDS = int(os.getenv("MAX_UPDATE_AGE_SECONDS", "300"))
_last_update_id = -1


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


@router.post("/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    # If a secret is configured, require Telegram to send it via header
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        logger.warning("Webhook secret mismatch")
        raise HTTPException(status_code=403, detail="Forbidden")

    update = await request.json()

    # Drop duplicate or stale updates
    global _last_update_id
    update_id = update.get("update_id")
    if isinstance(update_id, int):
        if update_id <= _last_update_id:
            return {"ok": True}
        _last_update_id = update_id

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
        raise

    return {"ok": True}
