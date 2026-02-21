import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    joke_subscribed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    subscriptions = relationship("Subscription", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sign = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    user = relationship("User", back_populates="subscriptions")
    __table_args__ = (UniqueConstraint("user_id", "sign", name="_user_sign_uc"),)


class CachedHoroscope(Base):
    __tablename__ = "cached_horoscopes"
    id = Column(Integer, primary_key=True, index=True)
    sign = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)
    fetched_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    __table_args__ = (UniqueConstraint("sign", "date", name="_sign_date_uc"),)


class ProcessedUpdate(Base):
    __tablename__ = "processed_updates"
    id = Column(Integer, primary_key=True, index=True)
    update_id = Column(BigInteger, unique=True, index=True, nullable=False)
    processed_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
