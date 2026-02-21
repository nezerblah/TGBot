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
    """Build compact main reply keyboard (3 rows, no scrolling)."""
    daily_label = "🌙 Ежедневная карта ✓" if tarot_daily_subscribed else "🌙 Ежедневная карта"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔮 Предсказание"), KeyboardButton(text="🔮 Расклады")],
            [KeyboardButton(text=daily_label)],
            [KeyboardButton(text="⭐ Подписки и тарифы")],
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


def spreads_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard with available tarot spreads."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🃏 Три карты (прошлое·настоящее·будущее)", callback_data="spread:three_cards")],
            [InlineKeyboardButton(text="💕 Влюблённые (расклад на отношения)", callback_data="spread:lovers")],
        ]
    )


def spread_paywall_keyboard(spread_key: str) -> InlineKeyboardMarkup:
    """Build inline keyboard for spread paywall (Premium+ or single purchase)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Оформить Premium+ (100 ⭐)", callback_data="buy:premium_plus")],
            [InlineKeyboardButton(text="🎴 Купить этот расклад (15 ⭐)", callback_data=f"buy:spread:{spread_key}")],
        ]
    )


def premium_info_keyboard(premium_active: bool, plus_active: bool) -> InlineKeyboardMarkup:
    """Build inline keyboard for premium info page."""
    buttons = []
    if not premium_active:
        buttons.append([InlineKeyboardButton(text="🔮 Купить Premium (10 ⭐)", callback_data="buy:premium")])
    if not plus_active:
        buttons.append([InlineKeyboardButton(text="💎 Купить Premium+ (100 ⭐)", callback_data="buy:premium_plus")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
