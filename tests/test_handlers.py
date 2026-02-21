"""Tests for handlers module."""

from unittest.mock import MagicMock, patch

from app.handlers import (_get_or_create_user, _is_duplicate_callback,
                          _is_valid_sign)


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
