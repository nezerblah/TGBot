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
        # Try different selectors for rating elements
        # Mail.ru might use different structures
        rating_elements = soup.find_all('div', class_=lambda x: x and 'rating' in x.lower())

        if not rating_elements:
            # Alternative: look for span with stars
            rating_elements = soup.find_all('span', class_=lambda x: x and ('star' in x.lower() or 'rate' in x.lower()))

        # Try to find rating containers with specific patterns
        for elem in soup.find_all(['div', 'span']):
            text = elem.get_text(strip=True)
            parent = elem.find_parent(['div', 'li', 'section'])

            # Look for Finance, Health, Love labels with ratings nearby
            if 'Финансы' in text or 'финансы' in text:
                stars = _extract_stars_from_parent(parent)
                if stars:
                    ratings["Финансы"] = stars
            elif 'Здоровье' in text or 'здоровье' in text:
                stars = _extract_stars_from_parent(parent)
                if stars:
                    ratings["Здоровье"] = stars
            elif 'Любовь' in text or 'любовь' in text:
                stars = _extract_stars_from_parent(parent)
                if stars:
                    ratings["Любовь"] = stars

    except Exception as e:
        logger.warning(f"Error extracting ratings: {e}")

    return ratings

def _extract_stars_from_parent(parent) -> str:
    """Extract star rating from parent element"""
    if not parent:
        return None

    try:
        # Look for star elements (img, svg, or unicode stars)
        star_count = 0

        # Method 1: Count img/svg elements with 'star' in src/class
        for img in parent.find_all(['img', 'svg']):
            src = img.get('src', '').lower()
            cls = img.get('class', [])
            if isinstance(cls, list):
                cls = ' '.join(cls).lower()
            if 'star' in src or 'star' in cls:
                star_count += 1

        if star_count > 0:
            return "⭐" * star_count

        # Method 2: Look for data attributes with rating
        for elem in parent.find_all(['div', 'span']):
            data_rating = elem.get('data-rating')
            if data_rating:
                try:
                    rating = int(float(data_rating))
                    return "⭐" * rating
                except:
                    pass

            # Check for title or aria-label with rating number
            title = elem.get('title', '').strip()
            if title and any(c.isdigit() for c in title):
                for char in title:
                    if char.isdigit():
                        try:
                            rating = int(char)
                            if 1 <= rating <= 5:
                                return "⭐" * rating
                        except:
                            pass

        # Method 3: Parse text for numbers
        text = parent.get_text()
        import re
        numbers = re.findall(r'\d', text)
        if numbers:
            rating = int(numbers[0])
            if 1 <= rating <= 5:
                return "⭐" * rating

    except Exception as e:
        logger.warning(f"Error extracting stars: {e}")

    return None

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

                # Format output with ratings
                output = f"🌟 {text}\n\n"
                output += "━━━━━━━━━━━━━━━━━\n"
                output += f"💰 Финансы: {ratings['Финансы']}\n"
                output += f"💪 Здоровье: {ratings['Здоровье']}\n"
                output += f"💗 Любовь: {ratings['Любовь']}"

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
