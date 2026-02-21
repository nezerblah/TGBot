"""Tests for tarot module."""

from app.tarot import FULL_DECK, MAJOR_ARCANA, MINOR_ARCANA, draw_random_card


def test_major_arcana_has_22_cards() -> None:
    """Major Arcana should contain exactly 22 cards."""
    assert len(MAJOR_ARCANA) == 22


def test_minor_arcana_has_56_cards() -> None:
    """Minor Arcana should contain exactly 56 cards."""
    assert len(MINOR_ARCANA) == 56


def test_full_deck_has_78_cards() -> None:
    """Full deck should contain exactly 78 cards."""
    assert len(FULL_DECK) == 78


def test_draw_random_card_returns_valid_card() -> None:
    """draw_random_card should return a card with required fields."""
    card = draw_random_card()
    assert "name" in card
    assert "name_en" in card
    assert "number" in card
    assert "image" in card
    assert "meaning" in card
    assert isinstance(card["name"], str)
    assert isinstance(card["number"], (int, str))


def test_all_cards_have_required_fields() -> None:
    """Every card in the full deck should have all required fields populated."""
    for card in FULL_DECK:
        assert card["name"], f"Card {card.get('number')} missing name"
        assert card["name_en"], f"Card {card.get('number')} missing name_en"
        assert card["image"].startswith("https://"), f"Card {card['name']} has invalid image URL"
        assert len(card["meaning"]) > 50, f"Card {card['name']} meaning too short"


def test_all_card_numbers_unique() -> None:
    """All card numbers in Major Arcana should be unique."""
    numbers = [card["number"] for card in MAJOR_ARCANA]
    assert len(numbers) == len(set(numbers))


def test_card_numbers_are_0_to_21() -> None:
    """Card numbers should be 0 through 21."""
    numbers = sorted(card["number"] for card in MAJOR_ARCANA)
    assert numbers == list(range(22))


def test_draw_random_card_can_return_minor_arcana() -> None:
    """draw_random_card should be able to return Minor Arcana cards."""
    # With 78 cards, running 200 times is statistically certain to hit Minor Arcana
    suits_seen = set()
    for _ in range(200):
        card = draw_random_card()
        if "suit" not in card or card.get("name_en", "").endswith(("of Wands", "of Cups", "of Swords", "of Pentacles")):
            suits_seen.add(card.get("name_en", "").split(" of ")[-1] if " of " in card.get("name_en", "") else None)
    assert len(suits_seen) > 1
