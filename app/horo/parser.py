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

# Telegram message limit is 4096 characters
TELEGRAM_MESSAGE_LIMIT = 4096
# Reserve space for ratings section (approximately 200 chars)
RATINGS_RESERVE = 200

def truncate_text(text: str, max_length: int = TELEGRAM_MESSAGE_LIMIT - RATINGS_RESERVE) -> str:
    """Truncate text to fit within Telegram limits"""
    if len(text) <= max_length:
        return text

    # Truncate at word boundary
    truncated = text[:max_length]

    # Find last space to avoid cutting in the middle of a word
    last_space = truncated.rfind('\n\n')
    if last_space > max_length - 100:  # If there's a paragraph break close to the limit
        truncated = truncated[:last_space]
    else:
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]

    truncated = truncated.rstrip() + '...'
    logger.info(f"Truncated text from {len(text)} to {len(truncated)} chars")
    return truncated


def extract_ratings(soup) -> dict:
    """Extract star ratings from horo.mail.ru using aria-label attribute"""
    ratings = {
        "Финансы": "❓",
        "Здоровье": "❓",
        "Любовь": "❓"
    }

    try:
        logger.info("=== STARTING RATINGS EXTRACTION ===")

        # Find all <a> tags with category names
        all_links = soup.find_all('a')
        logger.info(f"Found {len(all_links)} links")

        for link in all_links:
            link_text = link.get_text(strip=True).lower()

            # Check if this is a category link
            if 'финанс' in link_text or 'здоров' in link_text or 'любов' in link_text:
                logger.info(f"Found category link: {link_text}")

                # The next sibling should be the <ul> with stars
                next_elem = link.find_next('ul')

                if next_elem:
                    # Check aria-label attribute which contains "X из 5"
                    aria_label = next_elem.get('aria-label', '')
                    logger.info(f"aria-label: {aria_label}")

                    # Extract number from aria-label (e.g., "5 из 5" -> 5)
                    import re
                    match = re.search(r'(\d+)\s*из\s*5', aria_label)
                    if match:
                        star_count = int(match.group(1))
                        logger.info(f"Extracted from aria-label: {star_count} stars")

                        if 'финанс' in link_text:
                            ratings["Финансы"] = "⭐" * star_count
                            logger.info(f"✓ Set Finance: {star_count}")
                        elif 'здоров' in link_text:
                            ratings["Здоровье"] = "⭐" * star_count
                            logger.info(f"✓ Set Health: {star_count}")
                        elif 'любов' in link_text:
                            ratings["Любовь"] = "⭐" * star_count
                            logger.info(f"✓ Set Love: {star_count}")
                    else:
                        # Fallback: count <li> elements which represent individual stars
                        li_count = len(next_elem.find_all('li'))
                        logger.info(f"Fallback: counting li elements: {li_count}")

                        if li_count > 0:
                            if 'финанс' in link_text:
                                ratings["Финансы"] = "⭐" * li_count
                                logger.info(f"✓ Set Finance: {li_count}")
                            elif 'здоров' in link_text:
                                ratings["Здоровье"] = "⭐" * li_count
                                logger.info(f"✓ Set Health: {li_count}")
                            elif 'любов' in link_text:
                                ratings["Любовь"] = "⭐" * li_count
                                logger.info(f"✓ Set Love: {li_count}")

        logger.info(f"=== FINAL RATINGS: {ratings} ===")

    except Exception as e:
        logger.error(f"Error extracting ratings: {e}", exc_info=True)

    return ratings


def extract_horoscope_text(soup) -> str:
    """Extract only the main horoscope text block from the page"""

    logger.info("=== EXTRACTING HOROSCOPE TEXT ===")

    # Priority: Try to find the main horoscope content block
    # Mail.ru usually has the main horoscope in a specific container
    possible_containers = [
        # Most specific selectors first
        soup.select_one('[data-qa="horoscope-text"]'),
        soup.select_one('.article__text'),
        soup.select_one('.prediction'),
        soup.select_one('[data-qa="article-text"]'),
        # Find article tag
        soup.find('article'),
        # Find main tag
        soup.find('main'),
    ]

    container = None
    for possible in possible_containers:
        if possible:
            text = possible.get_text(strip=True)
            if len(text) > 100:  # Must have substantial content
                container = possible
                logger.info(f"Found container with {len(text)} characters")
                break

    if not container:
        logger.warning("No container found with standard selectors")
        return "Не удалось получить текст гороскопа"

    # Now extract only paragraphs that are direct children of the container
    # This avoids getting nav, footer, sidebar text
    paragraphs = []

    for elem in container.find_all('p', recursive=False):
        text = elem.get_text(strip=True)
        if len(text) > 30:  # Skip very short paragraphs (likely not content)
            paragraphs.append(text)
            logger.info(f"Found paragraph: {text[:80]}...")

    # If we found direct p tags, use them
    if paragraphs:
        full_text = '\n\n'.join(paragraphs)
        logger.info(f"Extracted {len(paragraphs)} paragraphs, total {len(full_text)} chars")
        return full_text

    # Fallback: look for div children with text
    divs = []
    for elem in container.find_all('div', recursive=False):
        text = elem.get_text(strip=True)
        if len(text) > 50:  # Reasonable size
            divs.append(text)
            logger.info(f"Found div: {text[:80]}...")

    if divs:
        full_text = '\n\n'.join(divs)
        logger.info(f"Extracted {len(divs)} divs, total {len(full_text)} chars")
        return full_text

    # Last fallback: get all text from container but try to exclude common non-content elements
    # Get all children and filter by text content
    text_parts = []
    for child in container.children:
        if isinstance(child, str):
            text = child.strip()
            if text and len(text) > 50:
                text_parts.append(text)
        elif hasattr(child, 'name') and child.name in ['p', 'div', 'span']:
            text = child.get_text(strip=True)
            if text and len(text) > 50:
                text_parts.append(text)

    if text_parts:
        full_text = '\n\n'.join(text_parts)
        logger.info(f"Extracted {len(text_parts)} text parts, total {len(full_text)} chars")
        return full_text

    logger.warning("Could not extract any meaningful text")
    return "Не удалось получить текст гороскопа"


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

                # Extract full horoscope text
                text = extract_horoscope_text(soup)

                # Truncate text to fit Telegram limits
                text = truncate_text(text)

                # Extract ratings
                ratings = extract_ratings(soup)

                # Format output with ratings
                output = f"🌟 {text}\n\n"
                output += "━━━━━━━━━━━━━━━━━━━━━━\n"
                output += f"💰 Финансы: {ratings['Финансы']}\n"
                output += f"💪 Здоровье: {ratings['Здоровье']}\n"
                output += f"💗 Любовь: {ratings['Любовь']}\n"
                output += "━━━━━━━━━━━━━━━━━━━━━━"

                # Double check that message fits Telegram limits
                if len(output) > TELEGRAM_MESSAGE_LIMIT:
                    logger.warning(f"Message still too long ({len(output)} chars), truncating more aggressively")
                    text = truncate_text(text, TELEGRAM_MESSAGE_LIMIT - RATINGS_RESERVE - 200)
                    output = f"🌟 {text}\n\n"
                    output += "━━━━━━━━━━━━━━━━━━━━━━\n"
                    output += f"💰 Финансы: {ratings['Финансы']}\n"
                    output += f"💪 Здоровье: {ratings['Здоровье']}\n"
                    output += f"💗 Любовь: {ratings['Любовь']}\n"
                    output += "━━━━━━━━━━━━━━━━━━━━━━"

                logger.info(f"Final message length: {len(output)} chars")

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

