"""Tests for database models."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import User, Subscription, CachedHoroscope, ProcessedUpdate


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_user_model_creates_with_defaults(db_session) -> None:
    """User model should create with default values."""
    user = User(telegram_id=12345, username="testuser")
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.telegram_id == 12345
    assert user.username == "testuser"
    assert user.created_at is not None
    assert isinstance(user.created_at, datetime)


def test_subscription_unique_constraint(db_session) -> None:
    """User cannot subscribe to same sign twice."""
    user = User(telegram_id=12345)
    db_session.add(user)
    db_session.commit()

    sub1 = Subscription(user_id=user.id, sign="aries", active=True)
    db_session.add(sub1)
    db_session.commit()

    # Try to add duplicate subscription
    sub2 = Subscription(user_id=user.id, sign="aries", active=True)
    db_session.add(sub2)
    
    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()


def test_cached_horoscope_unique_constraint(db_session) -> None:
    """Cannot cache same sign for same date twice."""
    from datetime import date

    today = date.today()
    cached1 = CachedHoroscope(sign="aries", date=today, content="Test content")
    db_session.add(cached1)
    db_session.commit()

    cached2 = CachedHoroscope(sign="aries", date=today, content="Different content")
    db_session.add(cached2)
    
    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()


def test_processed_update_unique_constraint(db_session) -> None:
    """Cannot process same update_id twice."""
    update1 = ProcessedUpdate(update_id=123456)
    db_session.add(update1)
    db_session.commit()

    update2 = ProcessedUpdate(update_id=123456)
    db_session.add(update2)
    
    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()


def test_user_subscription_relationship(db_session) -> None:
    """User should have relationship with subscriptions."""
    user = User(telegram_id=12345)
    db_session.add(user)
    db_session.commit()

    sub1 = Subscription(user_id=user.id, sign="aries")
    sub2 = Subscription(user_id=user.id, sign="leo")
    db_session.add_all([sub1, sub2])
    db_session.commit()

    db_session.refresh(user)
    assert len(user.subscriptions) == 2
    assert set(s.sign for s in user.subscriptions) == {"aries", "leo"}
