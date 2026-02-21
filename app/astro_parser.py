"""Parser for tarot spreads from astrocentr.ru."""

import logging
import random
import re
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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


async def fetch_spread(spread_key: str) -> str | None:
    """Fetch a tarot spread result from astrocentr.ru.

    Returns cleaned text with card meanings, or None on error.
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
        content_lines = []
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

        result = _clean_text("\n".join(content_lines))
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
