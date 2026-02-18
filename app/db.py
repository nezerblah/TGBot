import os

from sqlalchemy import create_engine
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
