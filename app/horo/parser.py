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

