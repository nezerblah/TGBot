import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

JOKE_URL = "https://nekdo.ru/random/"
TIMEOUT = 10.0


async def fetch_random_joke() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(JOKE_URL, follow_redirects=True)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        joke_container = soup.find("div", class_="joke")
        if not joke_container:
            joke_container = soup.find("article")

        if joke_container:
            joke_text = joke_container.get_text(strip=True)
            if joke_text:
                return joke_text

        return None
    except asyncio.TimeoutError:
        logger.error("Timeout fetching joke from nekdo.ru")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error fetching joke: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching joke: {e}")
        return None
