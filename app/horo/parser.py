import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import asyncio
import re
from ..db import SessionLocal
from ..models import CachedHoroscope

logger = logging.getLogger(__name__)

BASE_URL = "https://horo.mail.ru"
SIGN_PATH = "/prediction/{sign}/today/"

def extract_ratings(soup) -> dict:
    """Extract star ratings from star icons at the bottom of horoscope page"""
    ratings = {
        "Финансы": "❓",
        "Здоровье": "❓",
        "Любовь": "❓"
    }

    try:
        logger.info("=== STARTING RATINGS EXTRACTION ===")

        # Find all text that contains our category names
        all_elements = soup.find_all(['div', 'span', 'p', 'li', 'dd', 'dt'])

        for elem in all_elements:
            elem_text = elem.get_text(strip=True).lower()

            # Check if this element contains one of our categories
            if 'финанс' in elem_text or 'здоров' in elem_text or 'любов' in elem_text:
                if len(elem_text) < 100:  # Should be short - just category name + stars
                    logger.info(f"Found element: {elem_text}")

                    # Count star IMAGES in this element and nearby
                    parent = elem.find_parent(['div', 'li', 'dd', 'section'])
                    if parent is None:
                        parent = elem

                    # Count all IMG and SVG elements with 'star' in them
                    star_count = _count_star_icons(parent)
                    logger.info(f"Star count: {star_count}")

                    if star_count > 0:
                        if 'финанс' in elem_text:
                            ratings["Финансы"] = "⭐" * star_count
                            logger.info(f"✓ Set Finance: {star_count} stars")
                        elif 'здоров' in elem_text:
                            ratings["Здоровье"] = "⭐" * star_count
                            logger.info(f"✓ Set Health: {star_count} stars")
                        elif 'любов' in elem_text:
                            ratings["Любовь"] = "⭐" * star_count
                            logger.info(f"✓ Set Love: {star_count} stars")

        logger.info(f"=== FINAL RATINGS: {ratings} ===")

    except Exception as e:
        logger.error(f"Error extracting ratings: {e}", exc_info=True)

    return ratings

def _count_star_icons(elem) -> int:
    """Count star icon images in an element"""
    if not elem:
        return 0

    try:
        star_count = 0

        # Method 1: Count img elements with 'star' in src attribute
        for img in elem.find_all('img'):
            src = img.get('src', '').lower()
            alt = img.get('alt', '').lower()

            # Check if this looks like a star image
            if 'star' in src or '★' in alt or 'звез' in alt:
                star_count += 1
                logger.debug(f"Found star img: src={src}, alt={alt}")

        # Method 2: Count svg elements with 'star' in class or id
        for svg in elem.find_all('svg'):
            classes = ' '.join(svg.get('class', [])).lower()
            svg_id = svg.get('id', '').lower()

            if 'star' in classes or 'star' in svg_id:
                star_count += 1
                logger.debug(f"Found star svg: class={classes}, id={svg_id}")

        # Method 3: Count span/div elements that look like stars (sometimes they use pseudo-elements or backgrounds)
        for elem_child in elem.find_all(['span', 'i'], class_=lambda x: x and 'star' in x.lower()):
            star_count += 1
            logger.debug(f"Found star element: {elem_child.get('class', [])}")

        logger.info(f"Total stars counted: {star_count}")
        return star_count

    except Exception as e:
        logger.error(f"Error counting star icons: {e}")
        return 0


async def fetch_horoscope(sign: str) -> str:
    """Fetch horoscope for a given zodiac sign with ratings"""
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0"
    }

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

