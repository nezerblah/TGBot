import os
import logging
from aiogram import Bot, types
from .handlers import setup_handlers

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set. Set it in Railway or your environment.")

logger.info(f"Initializing bot with token: {BOT_TOKEN[:20]}...")
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

# We won't start polling; webhook calls process_update

async def process_update(update: dict):
    """Process incoming webhook update"""
    try:
        logger.info(f"Processing update: {update.get('update_id', 'unknown')}")
        # called from webhook with raw update json
        upd = types.Update(**update)
        # dispatch: simple mapping
        await setup_handlers(bot, upd)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        raise
