from fastapi import APIRouter, Request, Header, HTTPException
import os
import logging
from .bot import process_update

router = APIRouter()
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@router.post("/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    # If a secret is configured, require Telegram to send it via header
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        logger.warning(f"Webhook secret mismatch. Received: {x_telegram_bot_api_secret_token}")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        update = await request.json()
        logger.info(f"Received update: {update}")
        # Delegate to bot processing
        await process_update(update)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise

    return {"ok": True}
