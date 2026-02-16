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

        found_elements = []

        for elem in all_elements:
            elem_text = elem.get_text(strip=True).lower()

            # Check if this element contains one of our categories
            if 'финанс' in elem_text or 'здоров' in elem_text or 'любов' in elem_text:
                if len(elem_text) < 200:  # Should be short - just category name + stars
                    found_elements.append({
                        'text': elem_text,
                        'html': str(elem)[:500],
                        'tag': elem.name,
                        'classes': elem.get('class', [])
                    })

        logger.info(f"Found {len(found_elements)} elements with category names")
        for i, el in enumerate(found_elements):
            logger.info(f"Element {i}: text='{el['text'][:80]}' | tag={el['tag']} | classes={el['classes']}")
            logger.info(f"  HTML: {el['html']}")

        # Now try to extract ratings from found elements
        for elem_data in found_elements:
            # Find the actual element again from soup
            for elem in soup.find_all(['div', 'span', 'p', 'li', 'dd', 'dt']):
                if elem.get_text(strip=True).lower() == elem_data['text']:
                    logger.info(f"Processing: {elem_data['text'][:50]}")

                    # Try multiple strategies to find stars

                    # Strategy 1: Look in the element itself
                    star_count = _count_star_icons(elem)
                    logger.info(f"  Strategy 1 (element itself): {star_count} stars")

                    # Strategy 2: Look in next sibling
                    if star_count == 0 and elem.next_sibling:
                        next_elem = elem.next_sibling
                        if hasattr(next_elem, 'find_all'):
                            star_count = _count_star_icons(next_elem)
                            logger.info(f"  Strategy 2 (next sibling): {star_count} stars")

                    # Strategy 3: Look in parent's children
                    if star_count == 0:
                        parent = elem.find_parent(['div', 'li', 'section', 'dd'])
                        if parent:
                            star_count = _count_star_icons(parent)
                            logger.info(f"  Strategy 3 (parent element): {star_count} stars")

                    # Strategy 4: Count direct <img> tags anywhere in parent
                    if star_count == 0:
                        parent = elem.find_parent(['div', 'li', 'section', 'dd'])
                        if parent:
                            imgs = parent.find_all('img')
                            star_count = len(imgs)
                            logger.info(f"  Strategy 4 (all img tags): {star_count} images")
                            for img in imgs:
                                logger.info(f"    - img src: {img.get('src', 'no src')}")

                    if star_count > 0:
                        if 'финанс' in elem_data['text']:
                            ratings["Финансы"] = "⭐" * star_count
                            logger.info(f"✓ Set Finance: {star_count} stars")
                        elif 'здоров' in elem_data['text']:
                            ratings["Здоровье"] = "⭐" * star_count
                            logger.info(f"✓ Set Health: {star_count} stars")
                        elif 'любов' in elem_data['text']:
                            ratings["Любовь"] = "⭐" * star_count
                            logger.info(f"✓ Set Love: {star_count} stars")

                    break

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

        # Method 1: Count img elements
        imgs = elem.find_all('img', recursive=True)
        logger.debug(f"Found {len(imgs)} img elements")
        for img in imgs:
            src = img.get('src', '').lower()
            alt = img.get('alt', '').lower()
            logger.debug(f"  IMG: src='{src}' alt='{alt}'")

            # Count any img as potential star if parent mentions star/rating
            star_count += 1

        # Method 2: Count svg elements
        svgs = elem.find_all('svg', recursive=True)
        logger.debug(f"Found {len(svgs)} svg elements")
        for svg in svgs:
            classes = ' '.join(svg.get('class', [])).lower()
            logger.debug(f"  SVG: class='{classes}'")
            star_count += 1

        # Method 3: Count span/i elements with star classes
        stars_by_class = elem.find_all(['span', 'i'], class_=lambda x: x and ('star' in x.lower() or 'icon' in x.lower()))
        logger.debug(f"Found {len(stars_by_class)} elements with star/icon class")
        star_count += len(stars_by_class)

        logger.info(f"Total icons counted: {star_count}")
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

