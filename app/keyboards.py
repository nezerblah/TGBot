from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

ZODIAC_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

SIGN_TITLES = {
    "aries": "Овен",
    "taurus": "Телец",
    "gemini": "Близнецы",
    "cancer": "Рак",
    "leo": "Лев",
    "virgo": "Дева",
    "libra": "Весы",
    "scorpio": "Скорпион",
    "sagittarius": "Стрелец",
    "capricorn": "Козерог",
    "aquarius": "Водолей",
    "pisces": "Рыбы",
}

def signs_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    for s in ZODIAC_SIGNS:
        kb.add(InlineKeyboardButton(text=SIGN_TITLES.get(s, s.title()), callback_data=f"sign:{s}"))
    return kb


def sign_detail_keyboard(sign: str, subscribed: bool = False):
    kb = InlineKeyboardMarkup()
    if subscribed:
        kb.add(InlineKeyboardButton(text="Отписаться", callback_data=f"unsub:{sign}"))
    else:
        kb.add(InlineKeyboardButton(text="Подписаться", callback_data=f"sub:{sign}"))
    kb.add(InlineKeyboardButton(text="Вернуться", callback_data="back:list"))
    return kb


def back_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="Назад", callback_data="back:list"))
    return kb

