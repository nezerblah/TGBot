from fastapi import FastAPI
import logging
from .webhook import router as webhook_router
from .bot import bot, setup_bot_commands
from .scheduler import setup_scheduler
from .db import Base, engine
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TGBot", description="Telegram Horoscope Bot")
app.include_router(webhook_router)

# create tables if not exist (simple approach)
try:
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.warning(f"Warning: Could not create tables on startup: {e}")

# start scheduler once on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting scheduler...")
    setup_scheduler(bot)
    try:
        await setup_bot_commands()
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

    webhook_url = os.getenv("WEBHOOK_URL")
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    if webhook_url:
        try:
            await bot.set_webhook(
                url=webhook_url,
                secret_token=webhook_secret,
                drop_pending_updates=True,
            )
        except Exception as e:
            logger.warning(f"Could not reset webhook: {e}")
    logger.info("Scheduler started")

@app.get("/")
async def root():
    return {"ok": True, "message": "Bot is running"}

@app.post("/")
async def root_post():
    return {"ok": True}

@app.get("/health")
async def health():
    return {"status": "healthy"}
