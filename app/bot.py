import os
import logging
from aiogram import Bot, types
from aiogram.types import BotCommand
from .handlers import setup_handlers

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set. Set it in Railway or your environment.")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

async def setup_bot_commands() -> None:
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="list", description="Список знаков"),
        BotCommand(command="me", description="Мои подписки"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)

# We won't start polling; webhook calls process_update

async def process_update(update: dict):
    """Process incoming webhook update"""
    try:
        update_id = update.get("update_id", "unknown")
        logger.info(f"Processing update: {update_id}")
        upd = types.Update(**update)
        await setup_handlers(bot, upd)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        raise
