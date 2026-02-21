"""Tests for handlers module."""

import datetime
from unittest.mock import MagicMock, patch

from app.handlers import (
    _check_and_increment_tarot_limit,
    _get_or_create_user,
    _is_duplicate_callback,
    _is_valid_sign,
)


def test_is_valid_sign_accepts_valid_signs() -> None:
    """Valid zodiac signs should be accepted."""
    assert _is_valid_sign("aries") is True
    assert _is_valid_sign("pisces") is True
    assert _is_valid_sign("leo") is True


def test_is_valid_sign_rejects_invalid_signs() -> None:
    """Invalid signs should be rejected."""
    assert _is_valid_sign("invalid") is False
    assert _is_valid_sign("") is False
    assert _is_valid_sign("ARIES") is False  # case-sensitive


def test_is_duplicate_callback_detects_duplicates() -> None:
    """Duplicate callbacks should be detected within debounce window."""
    user_id = 123
    callback_data = "sign:aries"

    # First call should not be duplicate
    assert _is_duplicate_callback(user_id, callback_data) is False

    # Immediate second call should be duplicate
    assert _is_duplicate_callback(user_id, callback_data) is True


@patch("app.handlers.SessionLocal")
def test_get_or_create_user_creates_new_user(mock_session_class: MagicMock) -> None:
    """New user should be created if not exists."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    user, created = _get_or_create_user(
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User",
    )

    assert created is True
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@patch("app.handlers.SessionLocal")
def test_get_or_create_user_returns_existing_user(mock_session_class: MagicMock) -> None:
    """Existing user should be returned without creating new one."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    existing_user = MagicMock()
    existing_user.telegram_id = 12345
    mock_db.query.return_value.filter_by.return_value.first.return_value = existing_user

    user, created = _get_or_create_user(telegram_id=12345)

    assert created is False
    assert user == existing_user
    mock_db.add.assert_not_called()


@patch("app.handlers.SessionLocal")
def test_tarot_limit_first_call_returns_allowed(mock_session_class: MagicMock) -> None:
    """First tarot draw in a week should be allowed, 9 remaining."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    today = datetime.date.today()
    current_week_start = today - datetime.timedelta(days=today.weekday())

    mock_user = MagicMock()
    mock_user.tarot_weekly_count = 0
    mock_user.tarot_week_start = current_week_start
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    allowed, remaining = _check_and_increment_tarot_limit(12345)

    assert allowed is True
    assert remaining == 9


@patch("app.handlers.SessionLocal")
def test_tarot_limit_tenth_call_returns_allowed_zero_remaining(mock_session_class: MagicMock) -> None:
    """10th tarot draw should be allowed with 0 remaining."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    today = datetime.date.today()
    current_week_start = today - datetime.timedelta(days=today.weekday())

    mock_user = MagicMock()
    mock_user.tarot_weekly_count = 9
    mock_user.tarot_week_start = current_week_start
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    allowed, remaining = _check_and_increment_tarot_limit(12345)

    assert allowed is True
    assert remaining == 0


@patch("app.handlers.SessionLocal")
def test_tarot_limit_eleventh_call_denied(mock_session_class: MagicMock) -> None:
    """11th tarot draw should be denied."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    today = datetime.date.today()
    current_week_start = today - datetime.timedelta(days=today.weekday())

    mock_user = MagicMock()
    mock_user.tarot_weekly_count = 10
    mock_user.tarot_week_start = current_week_start
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    allowed, remaining = _check_and_increment_tarot_limit(12345)

    assert allowed is False
    assert remaining == 0


@patch("app.handlers.SessionLocal")
def test_tarot_limit_resets_on_new_week(mock_session_class: MagicMock) -> None:
    """Counter should reset when a new week starts."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    last_week_start = datetime.date.today() - datetime.timedelta(days=7)

    mock_user = MagicMock()
    mock_user.tarot_weekly_count = 10
    mock_user.tarot_week_start = last_week_start
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    allowed, remaining = _check_and_increment_tarot_limit(12345)

    assert allowed is True
    assert mock_user.tarot_weekly_count == 1
