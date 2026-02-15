from fastapi import APIRouter, Request, Header, HTTPException
import os
from .bot import process_update

router = APIRouter()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@router.post("/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    # If a secret is configured, require Telegram to send it via header
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    update = await request.json()
    # Delegate to bot processing
    await process_update(update)
    return {"ok": True}
