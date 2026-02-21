from app import models
from app.db import Base, SessionLocal, engine, ensure_schema


def test_create_db():
    ensure_schema()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter_by(telegram_id=12345).first()
        if existing:
            db.delete(existing)
            db.commit()
        u = models.User(telegram_id=12345, username="test")
        db.add(u)
        db.commit()
        assert db.query(models.User).filter_by(telegram_id=12345).first() is not None
        db.delete(u)
        db.commit()
    finally:
        db.close()
