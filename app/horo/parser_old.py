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
    """Extract star ratings (1-5) for Finance, Health, Love from the bottom of horoscope"""
    ratings = {
        "Финансы": "❓",
        "Здоровье": "❓",
        "Любовь": "❓"
    }

    try:
        # Mail.ru horoscopes have ratings usually in a specific section
        # Look for rating elements - they're typically in containers at the bottom

        # Strategy 1: Look for elements with SVG/IMG stars (most reliable)
        # Strategy 2: Look for numerical ratings (1-5)
        # Strategy 3: Look for specific rating classes/structures

        # Find all potential rating containers
        # Usually they have "rating", "mark", "score" in class or contain star images

        all_elements = soup.find_all(['div', 'section', 'article'])

        for elem in all_elements:
            elem_text = elem.get_text(strip=True).lower()
            elem_html = elem.get('class', [])
            elem_classes = ' '.join(elem_html) if isinstance(elem_html, list) else str(elem_html)

            # Skip if this looks like main article content (too long)
            if len(elem_text) > 500:
                continue

            # Check if this might be a rating section
            is_rating_section = any(word in elem_classes.lower() for word in ['rating', 'mark', 'score', 'rate'])

            if is_rating_section or ('финансы' in elem_text and 'здоровье' in elem_text and 'любовь' in elem_text):
                # This looks like a rating container!
                # Extract individual ratings

                # Look for child elements
                rating_items = elem.find_all(['div', 'span', 'li', 'dd'])

                for item in rating_items:
                    item_text = item.get_text(strip=True)

                    # Count star elements (img, svg, or other star indicators)
                    stars = _count_stars_in_element(item)

                    if stars == 0:
                        # Try to find numbers
                        stars = _extract_rating_number(item_text)

                    if stars > 0:
                        # Determine which category this is
                        if 'финанс' in item_text.lower():
                            ratings["Финансы"] = "⭐" * stars
                            logger.info(f"Found Finance rating: {stars}")
                        elif 'здоров' in item_text.lower():
                            ratings["Здоровье"] = "⭐" * stars
                            logger.info(f"Found Health rating: {stars}")
                        elif 'любов' in item_text.lower():
                            ratings["Любовь"] = "⭐" * stars
                            logger.info(f"Found Love rating: {stars}")

    except Exception as e:
        logger.warning(f"Error extracting ratings: {e}", exc_info=True)

    return ratings

def _count_stars_in_element(elem) -> int:
    """Count star images/elements in given element"""
    if not elem:
        return 0

    try:
        star_count = 0

        # Look for img tags with 'star' in src
        for img in elem.find_all('img'):
            src = img.get('src', '').lower()
            alt = img.get('alt', '').lower()
            title = img.get('title', '').lower()

            if 'star' in src or 'звез' in alt or 'star' in title:
                star_count += 1

        # Look for svg elements
        for svg in elem.find_all('svg'):
            classes = ' '.join(svg.get('class', []))
            if 'star' in classes.lower():
                star_count += 1

        # Look for elements with star emoji or unicode
        text = elem.get_text()
        if '⭐' in text:
            star_count = text.count('⭐')
        elif '★' in text:
            star_count = text.count('★')

        return star_count

    except Exception as e:
        logger.debug(f"Error counting stars: {e}")
        return 0

def _extract_rating_number(text: str) -> int:
    """Extract rating number (1-5) from text"""
    if not text:
        return 0

    try:
        import re

        # Look for patterns like "4/5", "4 из 5", "рейтинг: 4" и т.д.
        patterns = [
            r'(\d)/5',           # X/5
            r'(\d)\s*из\s*5',    # X из 5
            r'(\d)\s*\*',        # X*
            r':\s*(\d)\s*(?:звез|star)',  # : X звезд/stars
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                if 1 <= num <= 5:
                    return num

        # Simple fallback: just find any digit 1-5
        digits = re.findall(r'\d', text)
        for digit_str in digits:
            num = int(digit_str)
            if 1 <= num <= 5:
                return num

    except Exception as e:
        logger.debug(f"Error extracting rating number: {e}")

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
