"""Parser for tarot spreads from astrocentr.ru."""

import html as html_module
import logging
import random
import re
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_POSITION_RE = re.compile(r"^(\d+)\s*[–—-]\s*(.+)")


class SpreadInfo(TypedDict):
    url: str
    title: str
    description: str
    num_cards: int


SPREADS: dict[str, SpreadInfo] = {
    "three_cards": {
        "url": "https://www.astrocentr.ru/index.php?przd=taro&str=3cards",
        "title": "🃏 Расклад «Три карты»",
        "description": "Прошлое · Настоящее · Будущее",
        "num_cards": 3,
    },
    "lovers": {
        "url": "https://www.astrocentr.ru/index.php?przd=taro&str=rasklad_vlublennye",
        "title": "💕 Расклад «Влюблённые»",
        "description": "Расклад на отношения и любовь",
        "num_cards": 4,
    },
}

TIMEOUT = 15.0
_CARD_RANGE = range(1, 157)


def _generate_card_ids(num_cards: int) -> str:
    """Generate random card IDs joined with 'i' separator (site convention)."""
    cards = random.sample(_CARD_RANGE, num_cards)
    return "i".join(str(c) for c in cards)


def _clean_text(raw: str) -> str:
    """Clean up parsed text: collapse whitespace, trim."""
    text = re.sub(r"\n{3,}", "\n\n", raw)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _format_spread_lines(content_lines: list[str]) -> str:
    """Format spread content lines with HTML markup for Telegram."""
    result_parts: list[str] = []
    expect_card_name = False

    for line in content_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip digit-only lines (card position numbers from the site)
        if stripped.isdigit():
            continue

        match = _POSITION_RE.match(stripped)
        if match:
            # Position header: "1 – Влияние прошлого..."
            result_parts.append(f"\n━━━━━━━━━━━━━━━\n📍 {html_module.escape(stripped)}\n")
            expect_card_name = True
            continue

        if expect_card_name:
            # Card name line right after position header
            result_parts.append(f"🔮 <b>{html_module.escape(stripped)}</b>\n")
            expect_card_name = False
            continue

        result_parts.append(html_module.escape(stripped))

    return _clean_text("\n".join(result_parts))


async def fetch_spread(spread_key: str) -> str | None:
    """Fetch a tarot spread result from astrocentr.ru.

    Returns cleaned HTML-formatted text with card meanings, or None on error.
    """
    spread = SPREADS.get(spread_key)
    if not spread:
        logger.error(f"Unknown spread key: {spread_key}")
        return None

    url = spread["url"]
    num_cards = spread["num_cards"]
    act_value = _generate_card_ids(num_cards)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                url,
                data={"act": act_value},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": url,
                },
                follow_redirects=True,
            )
            response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser", from_encoding="windows-1251")
        main_text = soup.find("div", class_="main_text")
        if not main_text:
            logger.warning(f"No main_text div found for spread {spread_key}")
            return None

        raw = main_text.get_text(separator="\n", strip=True)

        # Strip navigation header lines (first few lines are breadcrumbs)
        lines = raw.split("\n")
        content_lines: list[str] = []
        started = False
        for line in lines:
            stripped = line.strip()
            if not started and "Вам выпали карты" in stripped:
                started = True
                continue
            if started:
                content_lines.append(stripped)

        if not content_lines:
            # Fallback: skip first 3 nav lines
            content_lines = lines[3:]

        result = _format_spread_lines(content_lines)
        if not result:
            logger.warning(f"Empty result for spread {spread_key}")
            return None

        return result

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching spread {spread_key} from {url}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error fetching spread {spread_key}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching spread {spread_key}: {e}")
        return None
