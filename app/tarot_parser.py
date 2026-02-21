import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TAROT_URL = "https://horo.mail.ru/divination/tarot/"


async def fetch_tarot_reading() -> str | None:
    """Fetch a tarot card reading from horo.mail.ru"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(TAROT_URL, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract card name
        card_name = ""
        title_el = soup.select_one("h2, .article__title, [data-qa='Title']")
        if title_el:
            card_name = title_el.get_text(strip=True)

        # Extract reading text from article blocks
        paragraphs = []
        for block in soup.select("div[article-item-type='html']"):
            for p in block.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    paragraphs.append(text)

        if not paragraphs:
            # Fallback: try broader selectors
            for p in soup.select("article p, .article__text p, .article__item p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    paragraphs.append(text)

        if not paragraphs:
            logger.warning("Could not parse tarot reading")
            return None

        reading = "\n\n".join(paragraphs)

        # Truncate if too long for Telegram
        if len(reading) > 3500:
            reading = reading[:3500].rsplit(" ", 1)[0] + "..."

        result = "🔮 *Расклад Таро*"
        if card_name:
            result += f"\n\n🃏 {card_name}"
        result += f"\n\n{reading}"
        return result

    except Exception as e:
        logger.error(f"Error fetching tarot reading: {e}", exc_info=True)
        return None
