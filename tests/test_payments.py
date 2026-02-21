"""Tests for payments module."""

import datetime
from unittest.mock import MagicMock, patch

from app.payments import _activate_premium, _is_premium


@patch("app.payments.SessionLocal")
def test_is_premium_returns_false_when_no_premium(mock_session_class: MagicMock) -> None:
    """User without premium_until should not be premium."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_user = MagicMock()
    mock_user.premium_until = None
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    assert _is_premium(12345) is False


@patch("app.payments.SessionLocal")
def test_is_premium_returns_false_when_expired(mock_session_class: MagicMock) -> None:
    """User with expired premium should not be premium."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_user = MagicMock()
    mock_user.premium_until = datetime.datetime(2020, 1, 1)
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    assert _is_premium(12345) is False


@patch("app.payments.SessionLocal")
def test_is_premium_returns_true_when_active(mock_session_class: MagicMock) -> None:
    """User with future premium_until should be premium."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_user = MagicMock()
    mock_user.premium_until = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(
        days=10
    )
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    assert _is_premium(12345) is True


@patch("app.payments.SessionLocal")
def test_activate_premium_sets_correct_date(mock_session_class: MagicMock) -> None:
    """Premium activation should set premium_until to now + 30 days."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    mock_user = MagicMock()
    mock_user.premium_until = None
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    result = _activate_premium(12345)

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    assert result > now
    assert (result - now).days >= 29


@patch("app.payments.SessionLocal")
def test_activate_premium_extends_existing_subscription(mock_session_class: MagicMock) -> None:
    """Premium extension should add days from current expiry, not from now."""
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db

    future_date = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(days=15)
    mock_user = MagicMock()
    mock_user.premium_until = future_date
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    result = _activate_premium(12345)

    expected_min = future_date + datetime.timedelta(days=29)
    assert result >= expected_min


@patch("app.handlers._is_premium", return_value=True)
@patch("app.handlers.SessionLocal")
def test_tarot_limit_bypassed_for_premium_users(mock_session_class: MagicMock, mock_premium: MagicMock) -> None:
    """Premium users should bypass tarot weekly limit."""
    from app.handlers import _check_and_increment_tarot_limit

    allowed, remaining = _check_and_increment_tarot_limit(12345)

    assert allowed is True
    assert remaining == 999
    mock_session_class.assert_not_called()
