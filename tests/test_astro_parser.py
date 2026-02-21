"""Tests for astro_parser module."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.astro_parser import SPREADS, fetch_spread


def test_spreads_dict_has_required_keys() -> None:
    """All spreads should have required keys."""
    for key, spread in SPREADS.items():
        assert "url" in spread, f"Spread {key} missing 'url'"
        assert "title" in spread, f"Spread {key} missing 'title'"
        assert "description" in spread, f"Spread {key} missing 'description'"
        assert "num_cards" in spread, f"Spread {key} missing 'num_cards'"
        assert spread["url"].startswith("https://"), f"Spread {key} has invalid URL"
        assert spread["num_cards"] > 0, f"Spread {key} has invalid num_cards"


def test_spreads_has_expected_entries() -> None:
    """SPREADS should contain three_cards and lovers."""
    assert "three_cards" in SPREADS
    assert "lovers" in SPREADS


@pytest.mark.asyncio
async def test_fetch_spread_invalid_key_returns_none() -> None:
    """Passing an unknown spread key should return None."""
    result = await fetch_spread("nonexistent_spread")
    assert result is None


@pytest.mark.asyncio
@patch("app.astro_parser.httpx.AsyncClient")
async def test_fetch_spread_returns_none_on_timeout(mock_client_class: AsyncMock) -> None:
    """Timeout during fetch should return None."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post.side_effect = httpx.TimeoutException("timeout")
    mock_client_class.return_value = mock_client

    result = await fetch_spread("three_cards")
    assert result is None


@pytest.mark.asyncio
@patch("app.astro_parser.httpx.AsyncClient")
async def test_fetch_spread_returns_none_on_request_error(mock_client_class: AsyncMock) -> None:
    """Request error during fetch should return None."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post.side_effect = httpx.RequestError("connection failed")
    mock_client_class.return_value = mock_client

    result = await fetch_spread("lovers")
    assert result is None
