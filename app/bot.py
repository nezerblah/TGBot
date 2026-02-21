import logging
import os

from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from .handlers import setup_handlers

logger = logging.getLogger(__name__)

bot: Bot | None = None


def initialize_bot() -> Bot:
    """Initialize bot instance from environment variables."""
    global bot
    if bot is not None:
        return bot

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    return bot


def get_bot() -> Bot:
    """Get initialized bot instance."""
    if bot is None:
        raise RuntimeError("Bot is not initialized. Call initialize_bot() at startup.")
    return bot


async def setup_bot_commands() -> None:
    bot_instance = get_bot()
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="list", description="Список знаков"),
        BotCommand(command="me", description="Мои подписки"),
        BotCommand(command="joke", description="Случайный анекдот"),
        BotCommand(command="tarot", description="🔮 Предсказание Таро"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot_instance.set_my_commands(commands)


# We won't start polling; webhook calls process_update


async def process_update(update: dict):
    """Process incoming webhook update"""
    try:
        bot_instance = get_bot()
        update_id = update.get("update_id", "unknown")
        logger.info(f"Processing update: {update_id}")
        upd = types.Update(**update)
        await setup_handlers(bot_instance, upd)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        raise
