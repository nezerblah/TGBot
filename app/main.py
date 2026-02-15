from fastapi import FastAPI
import os
from .webhook import router as webhook_router
from .bot import bot
from .scheduler import setup_scheduler
from .db import Base, engine

app = FastAPI()
app.include_router(webhook_router)

# create tables if not exist (simple approach)
Base.metadata.create_all(bind=engine)

# start scheduler once on startup
@app.on_event("startup")
async def startup_event():
    setup_scheduler(bot)

@app.get("/")
async def root():
    return {"ok": True}

