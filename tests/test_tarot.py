"""Tests for tarot module."""

from app.tarot import MAJOR_ARCANA, draw_random_card


def test_major_arcana_has_22_cards() -> None:
    """Major Arcana should contain exactly 22 cards."""
    assert len(MAJOR_ARCANA) == 22


def test_draw_random_card_returns_valid_card() -> None:
    """draw_random_card should return a card with required fields."""
    card = draw_random_card()
    assert "name" in card
    assert "name_en" in card
    assert "number" in card
    assert "image" in card
    assert "meaning" in card
    assert isinstance(card["name"], str)
    assert isinstance(card["number"], int)
    assert 0 <= card["number"] <= 21


def test_all_cards_have_required_fields() -> None:
    """Every card should have all required fields populated."""
    for card in MAJOR_ARCANA:
        assert card["name"], f"Card {card.get('number')} missing name"
        assert card["name_en"], f"Card {card.get('number')} missing name_en"
        assert card["image"].startswith("https://"), f"Card {card['name']} has invalid image URL"
        assert len(card["meaning"]) > 50, f"Card {card['name']} meaning too short"


def test_all_card_numbers_unique() -> None:
    """All card numbers should be unique."""
    numbers = [card["number"] for card in MAJOR_ARCANA]
    assert len(numbers) == len(set(numbers))


def test_card_numbers_are_0_to_21() -> None:
    """Card numbers should be 0 through 21."""
    numbers = sorted(card["number"] for card in MAJOR_ARCANA)
    assert numbers == list(range(22))
