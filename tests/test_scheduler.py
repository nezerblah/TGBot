"""Tests for scheduler module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler import _load_recipients_by_sign, _load_tarot_daily_subscribers


@patch("app.scheduler.SessionLocal")
def test_load_recipients_by_sign_groups_correctly(mock_session_class: MagicMock) -> None:
    """Recipients should be grouped by zodiac sign."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
        ("aries", 100),
        ("aries", 101),
        ("leo", 200),
        ("pisces", 300),
        ("pisces", 301),
        ("pisces", 302),
    ]

    result = _load_recipients_by_sign()

    assert result == {
        "aries": [100, 101],
        "leo": [200],
        "pisces": [300, 301, 302],
    }


@patch("app.scheduler.SessionLocal")
def test_load_recipients_by_sign_handles_empty_result(mock_session_class: MagicMock) -> None:
    """Empty database should return empty dict."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []

    result = _load_recipients_by_sign()

    assert result == {}


@pytest.mark.asyncio
@patch("app.scheduler.fetch_horoscope")
@patch("app.scheduler.asyncio.to_thread")
async def test_send_daily_distributes_to_all_recipients(
    mock_to_thread: AsyncMock,
    mock_fetch_horoscope: AsyncMock,
) -> None:
    """Daily horoscope should be sent to all subscribers."""
    from app.scheduler import send_daily

    mock_bot = AsyncMock()
    mock_to_thread.return_value = {
        "aries": [100, 101],
        "leo": [200],
    }
    mock_fetch_horoscope.return_value = "Test horoscope"

    await send_daily(mock_bot)

    assert mock_fetch_horoscope.call_count == 2
    assert mock_bot.send_message.call_count == 3


@patch("app.scheduler.SessionLocal")
def test_load_tarot_daily_subscribers_returns_correct_ids(mock_session_class: MagicMock) -> None:
    """Should return telegram_ids of users with tarot_daily_subscribed=True."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_db.query.return_value.filter.return_value.all.return_value = [
        (100,),
        (200,),
        (300,),
    ]

    result = _load_tarot_daily_subscribers()

    assert result == [100, 200, 300]


@patch("app.scheduler.SessionLocal")
def test_load_tarot_daily_subscribers_empty(mock_session_class: MagicMock) -> None:
    """Empty database should return empty list."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = _load_tarot_daily_subscribers()

    assert result == []


@pytest.mark.asyncio
@patch("app.scheduler.draw_random_card")
@patch("app.scheduler.asyncio.to_thread")
async def test_send_daily_tarot_sends_to_all_subscribers(
    mock_to_thread: AsyncMock,
    mock_draw_card: MagicMock,
) -> None:
    """Daily tarot should send photo to every subscribed user."""
    from app.scheduler import send_daily_tarot

    mock_bot = AsyncMock()
    mock_to_thread.return_value = [100, 101, 200]
    mock_draw_card.return_value = {
        "name": "Шут",
        "name_en": "The Fool",
        "number": 0,
        "image": "https://example.com/fool.jpg",
        "meaning": "Test meaning",
    }

    await send_daily_tarot(mock_bot)

    assert mock_bot.send_photo.call_count == 3
