import asyncio
from app.db import Base, engine, SessionLocal
from app import models

def test_create_db():
    # create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        u = models.User(telegram_id=12345, username='test')
        db.add(u)
        db.commit()
        assert db.query(models.User).filter_by(telegram_id=12345).first() is not None
    finally:
        db.close()

