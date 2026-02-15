import os
from aiogram import Bot, types
from .handlers import setup_handlers

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set. Set it in Railway or your environment.")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

# We won't start polling; webhook calls process_update

async def process_update(update: dict):
    # called from webhook with raw update json
    upd = types.Update(**update)
    # dispatch: simple mapping
    await setup_handlers(bot, upd)
