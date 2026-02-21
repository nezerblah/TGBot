import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATA_DIR = os.getenv("DATA_DIR")
DEFAULT_DATA_DIR = "/data"

if not DATA_DIR and os.path.isdir(DEFAULT_DATA_DIR):
    DATA_DIR = DEFAULT_DATA_DIR

if DATA_DIR:
    os.makedirs(DATA_DIR, exist_ok=True)
    db_path = os.path.join(DATA_DIR, "tg_bot.db")
    DATABASE_URL = f"sqlite:///{db_path}"
else:
    DATABASE_URL = "sqlite:///./tg_bot.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema() -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        if not rows:
            return
        columns = {row[1] for row in rows}
        if "tarot_weekly_count" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN tarot_weekly_count INTEGER NOT NULL DEFAULT 0"))
        if "tarot_week_start" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN tarot_week_start DATE"))
        if "tarot_daily_subscribed" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN tarot_daily_subscribed BOOLEAN NOT NULL DEFAULT 0"))
        if "premium_until" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN premium_until DATETIME"))
        if "premium_plus_until" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN premium_plus_until DATETIME"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
