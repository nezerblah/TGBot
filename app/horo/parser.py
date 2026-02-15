import httpx
from bs4 import BeautifulSoup
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from ..db import SessionLocal
from ..models import CachedHoroscope
import asyncio

BASE_URL = "https://horo.mail.ru"
SIGN_PATH = "/prediction/{sign}/today/"

async def fetch_horoscope(sign: str) -> str:
    # check cache
    db = SessionLocal()
    try:
        msk = ZoneInfo("Europe/Moscow")
        now_msk = datetime.now(msk)
        today_msk = now_msk.date()
        cached = db.query(CachedHoroscope).filter_by(sign=sign, date=today_msk).first()
        if cached:
            return cached.content
    finally:
        db.close()

    url = BASE_URL + SIGN_PATH.format(sign=sign)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0; +https://example.com)"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")
                # Mail.ru horoscopes often under div with class 'article__item' or 'article__summary'
                container = soup.select_one('.article__text') or soup.select_one('.article__item') or soup.select_one('.article__summary')
                if not container:
                    # fallback: take first paragraph
                    p = soup.find('p')
                    text = p.get_text(strip=True) if p else "Не удалось получить текст гороскопа"
                else:
                    text = container.get_text(separator="\n", strip=True)
                # save to cache
                db = SessionLocal()
                try:
                    ch = CachedHoroscope(sign=sign, date=today_msk, content=text)
                    db.add(ch)
                    db.commit()
                finally:
                    db.close()
                return text
            except Exception as e:
                await asyncio.sleep(1 + attempt)
        return "Не удалось получить гороскоп — попробуйте позже."
