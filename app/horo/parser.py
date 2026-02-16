import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import asyncio
from ..db import SessionLocal
from ..models import CachedHoroscope

logger = logging.getLogger(__name__)

BASE_URL = "https://horo.mail.ru"
SIGN_PATH = "/prediction/{sign}/today/"

def extract_ratings(soup) -> dict:
    """Extract ratings (stars) for Finance, Health, Love from the page"""
    ratings = {
        "Финансы": "❓",
        "Здоровье": "❓",
        "Любовь": "❓"
    }

    try:
        # Look for all rating/score elements
        # Mail.ru uses different structures, try multiple approaches

        # Approach 1: Find divs/sections with rating information
        all_text_elements = soup.find_all(['div', 'span', 'p', 'li'])

        for elem in all_text_elements:
            text = elem.get_text(strip=True)

            # Check if this element contains finance rating
            if any(keyword in text.lower() for keyword in ['финансы', 'деньги', 'money']):
                # Look for numbers in nearby elements
                rating = _extract_number_from_context(elem)
                if rating:
                    ratings["Финансы"] = "⭐" * rating

            # Check for health rating
            if any(keyword in text.lower() for keyword in ['здоровье', 'здоровья', 'health']):
                rating = _extract_number_from_context(elem)
                if rating:
                    ratings["Здоровье"] = "⭐" * rating

            # Check for love rating
            if any(keyword in text.lower() for keyword in ['любовь', 'любви', 'romance', 'love']):
                rating = _extract_number_from_context(elem)
                if rating:
                    ratings["Любовь"] = "⭐" * rating

        # Approach 2: Look specifically in structured data or common classes
        rating_containers = soup.find_all(['div', 'span'], class_=lambda x: x and any(cls in (x.lower() if x else '') for cls in ['rating', 'score', 'stars', 'mark']))

        for container in rating_containers:
            parent_text = container.find_parent(['div', 'li', 'section'])
            if parent_text:
                parent_text_str = parent_text.get_text(strip=True).lower()
                rating = _extract_number_from_context(container)

                if rating and rating > 0:
                    if 'финанс' in parent_text_str:
                        ratings["Финансы"] = "⭐" * rating
                    elif 'здоров' in parent_text_str:
                        ratings["Здоровье"] = "⭐" * rating
                    elif 'любов' in parent_text_str:
                        ratings["Любовь"] = "⭐" * rating

    except Exception as e:
        logger.warning(f"Error extracting ratings: {e}")

    return ratings

def _extract_number_from_context(elem) -> int:
    """Extract a number (1-5) from element and its siblings"""
    if not elem:
        return 0

    try:
        # Check current element
        text = elem.get_text(strip=True)
        number = _parse_number_from_text(text)
        if 1 <= number <= 5:
            return number

        # Check next sibling
        if elem.next_sibling:
            if isinstance(elem.next_sibling, str):
                number = _parse_number_from_text(elem.next_sibling)
            else:
                number = _parse_number_from_text(elem.next_sibling.get_text(strip=True))
            if 1 <= number <= 5:
                return number

        # Check parent's children
        parent = elem.find_parent(['div', 'li', 'section'])
        if parent:
            # Look for rating badges or indicators near the label
            for child in parent.find_all(['span', 'div', 'em', 'strong']):
                text = child.get_text(strip=True)
                number = _parse_number_from_text(text)
                if 1 <= number <= 5:
                    return number

        # Check data attributes
        for attr in ['data-rating', 'data-score', 'data-stars']:
            value = elem.get(attr)
            if value:
                number = _parse_number_from_text(value)
                if 1 <= number <= 5:
                    return number

    except Exception as e:
        logger.debug(f"Error extracting number from context: {e}")

    return 0

def _parse_number_from_text(text: str) -> int:
    """Parse a single digit number from text"""
    if not text:
        return 0

    try:
        import re
        # Find first number in text
        numbers = re.findall(r'\d', str(text))
        if numbers:
            return int(numbers[0])
    except:
        pass

    return 0


async def fetch_horoscope(sign: str) -> str:
    """Fetch horoscope for a given zodiac sign with ratings, with caching"""
    # check cache
    db = SessionLocal()
    try:
        msk = ZoneInfo("Europe/Moscow")
        now_msk = datetime.now(msk)
        today_msk = now_msk.date()
        cached = db.query(CachedHoroscope).filter_by(sign=sign, date=today_msk).first()
        if cached:
            logger.info(f"Using cached horoscope for {sign}")
            return cached.content
    except Exception as e:
        logger.warning(f"Error checking cache: {e}")
    finally:
        db.close()

    url = BASE_URL + SIGN_PATH.format(sign=sign)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0; +https://example.com)"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(3):
            try:
                logger.info(f"Fetching horoscope for {sign}, attempt {attempt + 1}")
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")

                # Extract main horoscope text
                container = soup.select_one('.article__text') or soup.select_one('.article__item') or soup.select_one('.article__summary')
                if not container:
                    p = soup.find('p')
                    text = p.get_text(strip=True) if p else "Не удалось получить текст гороскопа"
                else:
                    text = container.get_text(separator="\n", strip=True)

                # Extract ratings
                ratings = extract_ratings(soup)
                logger.info(f"Extracted ratings for {sign}: {ratings}")

                # Format output with ratings
                output = f"🌟 {text}\n\n"
                output += "━━━━━━━━━━━━━━━━━━━━━━\n"
                output += f"💰 Финансы: {ratings['Финансы']}\n"
                output += f"💪 Здоровье: {ratings['Здоровье']}\n"
                output += f"💗 Любовь: {ratings['Любовь']}\n"
                output += "━━━━━━━━━━━━━━━━━━━━━━"

                # save to cache
                db = SessionLocal()
                try:
                    msk = ZoneInfo("Europe/Moscow")
                    now_msk = datetime.now(msk)
                    today_msk = now_msk.date()
                    ch = CachedHoroscope(sign=sign, date=today_msk, content=output)
                    db.add(ch)
                    db.commit()
                    logger.info(f"Cached horoscope for {sign}")
                except Exception as e:
                    logger.warning(f"Failed to cache horoscope: {e}")
                finally:
                    db.close()

                return output
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {sign}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1 + attempt)

        return "Не удалось получить гороскоп — попробуйте позже."
