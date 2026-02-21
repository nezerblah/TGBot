from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

ZODIAC_SIGNS = [
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
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
    """Build keyboard with zodiac signs in 3 columns"""
    buttons = []
    for i in range(0, len(ZODIAC_SIGNS), 3):
        row = []
        for sign in ZODIAC_SIGNS[i : i + 3]:
            row.append(InlineKeyboardButton(text=SIGN_TITLES.get(sign, sign.title()), callback_data=f"sign:{sign}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sign_detail_keyboard(sign: str, subscribed: bool = False):
    """Build keyboard for sign detail view"""
    buttons = []
    if subscribed:
        buttons.append([InlineKeyboardButton(text="Отписаться", callback_data=f"unsub:{sign}")])
    else:
        buttons.append([InlineKeyboardButton(text="Подписаться", callback_data=f"sub:{sign}")])
    buttons.append([InlineKeyboardButton(text="Вернуться", callback_data="back:list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_keyboard():
    """Build simple back keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="back:list")]])


def main_menu_keyboard(tarot_daily_subscribed: bool) -> ReplyKeyboardMarkup:
    """Build main reply keyboard with tarot and daily subscription buttons."""
    daily_label = (
        "🌙 Отписаться от ежедневного предсказания" if tarot_daily_subscribed else "🌙 Подписаться на ежедневное предсказание"
    )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔮 Получить предсказание")],
            [KeyboardButton(text=daily_label)],
        ],
        resize_keyboard=True,
    )


def tarot_open_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard with 'Open card' button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🃏 Открыть карту", callback_data="tarot:open")],
        ]
    )
