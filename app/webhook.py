from fastapi import APIRouter, Request, Header, HTTPException
import os
from .bot import process_update

router = APIRouter()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    update = await request.json()
    # Delegate to bot processing
    await process_update(update)
    return {"ok": True}

