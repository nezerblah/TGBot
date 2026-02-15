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
    buttons = [
        InlineKeyboardButton(text=SIGN_TITLES.get(s, s.title()), callback_data=f"sign:{s}")
        for s in ZODIAC_SIGNS
    ]
    kb = InlineKeyboardMarkup(row_width=3, inline_keyboard=[buttons])
    return kb


def sign_detail_keyboard(sign: str, subscribed: bool = False):
    buttons = []
    if subscribed:
        buttons.append([InlineKeyboardButton(text="Отписаться", callback_data=f"unsub:{sign}")])
    else:
        buttons.append([InlineKeyboardButton(text="Подписаться", callback_data=f"sub:{sign}")])
    buttons.append([InlineKeyboardButton(text="Вернуться", callback_data="back:list")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb


def back_keyboard():
    buttons = [[InlineKeyboardButton(text="Назад", callback_data="back:list")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb
