import asyncio
import datetime
import logging
import os
import time
from collections import OrderedDict

from aiogram import types
from sqlalchemy import func

from .astro_parser import SPREADS, fetch_spread
from .db import SessionLocal
from .horo.parser import fetch_horoscope
from .keyboards import (
    SIGN_TITLES,
    ZODIAC_SIGNS,
    main_menu_keyboard,
    sign_detail_keyboard,
    signs_keyboard,
    spreads_keyboard,
    tarot_open_keyboard,
)
from .models import Subscription, User
from .payments import _activate_premium, _is_premium, send_premium_invoice
from .tarot import draw_random_card

logger = logging.getLogger(__name__)

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

_CALLBACK_DEBOUNCE_SECONDS = 1.0
_CALLBACK_CACHE_MAX_SIZE = 5000
_last_callback: OrderedDict[tuple[int, str], float] = OrderedDict()

_VALID_SIGNS = frozenset(ZODIAC_SIGNS)
_VALID_SPREADS = frozenset(SPREADS.keys())

_TAROT_BUTTON_TEXT = "🔮 Получить предсказание"
_SPREADS_BUTTON_TEXT = "🔮 Выбрать расклад"
_TAROT_DAILY_SUBSCRIBE_TEXT = "🌙 Подписаться на ежедневное предсказание"
_TAROT_DAILY_UNSUBSCRIBE_TEXT = "🌙 Отписаться от ежедневного предсказания"
_PREMIUM_BUTTON_TEXT = "⭐ Premium — безлимит"
_PREMIUM_ACTIVE_TEXT = "⭐ Premium активен ✓"

_TAROT_INTRO = (
    "🔮 <b>Гадание на картах Таро</b>\n\n"
    "Карты не могут ответить «Да» или «Нет», формулируйте вопрос с учётом этого, например:\n"
    "• «Что меня ждёт в ближайшем будущем?»\n"
    "• «Как лучше провести сегодняшний день?»\n"
    "• «Карта дня на сегодня»\n"
    "• «К чему приведут мои действия?»\n\n"
    "В этом гадании используется полная колода Таро из 78 карт, но без перевёрнутых карт. "
    "По правилам гаданий задавать определённый вопрос можно только один раз, "
    "иначе следующие ответы будут неточными. Вместо этого лучше задавать уточняющие вопросы, "
    "чтобы лучше понять ситуацию.\n\n"
    "Помните, карты не определяют ваше будущее, они могут только подсказывать, "
    "предостерегать или предлагать варианты. Судьба всегда в ваших руках, "
    "верьте в лучшее и уверенно идите по жизненному пути.\n\n"
    "✨ Сфокусируйтесь на вашем вопросе, очистите разум и нажмите кнопку <b>«Открыть карту»</b>."
)

_SPREADS_INTRO = (
    "🔮 <b>Расклады Таро</b>\n\n"
    "Выберите один из доступных раскладов:\n\n"
    "🃏 <b>Три карты</b> — расклад на прошлое, настоящее и будущее.\n"
    "Поможет увидеть полную картину ситуации.\n\n"
    "💕 <b>Влюблённые</b> — расклад на отношения.\n"
    "Покажет, кто вы и ваш партнёр в союзе, и чего ожидать.\n\n"
    "✨ Мысленно задайте вопрос и выберите расклад."
)

TELEGRAM_MESSAGE_LIMIT = 4096


def _cleanup_callback_cache(now: float) -> None:
    stale_keys = [key for key, timestamp in _last_callback.items() if now - timestamp >= _CALLBACK_DEBOUNCE_SECONDS]
    for key in stale_keys:
        _last_callback.pop(key, None)

    while len(_last_callback) > _CALLBACK_CACHE_MAX_SIZE:
        _last_callback.popitem(last=False)


def _is_valid_sign(sign: str) -> bool:
    return sign in _VALID_SIGNS


def _is_duplicate_callback(user_id: int, data: str) -> bool:
    key = (user_id, data)
    now = time.monotonic()
    _cleanup_callback_cache(now)

    last = _last_callback.get(key)
    if last and now - last < _CALLBACK_DEBOUNCE_SECONDS:
        return True

    _last_callback[key] = now
    _last_callback.move_to_end(key)
    return False


def _get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> tuple[User, bool]:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        created = False
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created = True
        return user, created
    finally:
        db.close()


def _get_user_subscriptions(telegram_id: int) -> list[str]:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return []
        return [subscription.sign for subscription in user.subscriptions if subscription.active]
    finally:
        db.close()


def _is_subscribed(telegram_id: int, sign: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return False
        sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign, active=True).first()
        return bool(sub)
    finally:
        db.close()


def _subscribe_user(telegram_id: int, sign: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign).first()
        was_subscribed = bool(sub and sub.active)

        if not sub:
            db.add(Subscription(user_id=user.id, sign=sign, active=True))
        else:
            sub.active = True

        db.commit()
        return not was_subscribed
    finally:
        db.close()


def _unsubscribe_user(telegram_id: int, sign: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return False

        if sign == "all":
            db.query(Subscription).filter_by(user_id=user.id).update({"active": False})
            db.commit()
            return True

        sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign).first()
        if not sub or not sub.active:
            return False

        sub.active = False
        db.commit()
        return True
    finally:
        db.close()


def _get_subscribers_stats() -> tuple[int, list[tuple[str, int]]]:
    db = SessionLocal()
    try:
        active_users = (
            db.query(func.count(func.distinct(Subscription.user_id))).filter(Subscription.active).scalar() or 0
        )

        stats = (
            db.query(Subscription.sign, func.count(Subscription.id))
            .filter(Subscription.active)
            .group_by(Subscription.sign)
            .all()
        )
        return active_users, stats
    finally:
        db.close()


def _get_tarot_daily_subscription(telegram_id: int) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        return bool(user and user.tarot_daily_subscribed)
    finally:
        db.close()


def _set_tarot_daily_subscription(telegram_id: int, subscribed: bool) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, tarot_daily_subscribed=subscribed)
            db.add(user)
            db.commit()
            return subscribed

        if user.tarot_daily_subscribed == subscribed:
            return subscribed

        user.tarot_daily_subscribed = subscribed
        db.commit()
        return subscribed
    finally:
        db.close()


def _check_and_increment_tarot_limit(telegram_id: int) -> tuple[bool, int]:
    """Check weekly tarot limit and increment counter. Returns (allowed, remaining)."""
    if _is_premium(telegram_id):
        return True, 999

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        today = datetime.date.today()
        current_week_start = today - datetime.timedelta(days=today.weekday())

        if user.tarot_week_start != current_week_start:
            user.tarot_weekly_count = 0
            user.tarot_week_start = current_week_start

        if user.tarot_weekly_count >= 10:
            db.commit()
            return False, 0

        user.tarot_weekly_count += 1
        db.commit()
        remaining = 10 - user.tarot_weekly_count
        return True, remaining
    finally:
        db.close()


def _get_user_menu_state(telegram_id: int) -> tuple[bool, bool]:
    """Return (tarot_daily_subscribed, is_premium) for menu rendering."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return False, False
        daily = bool(user.tarot_daily_subscribed)
        now = datetime.datetime.now(datetime.timezone.utc)
        if user.premium_until and user.premium_until.tzinfo is None:
            now = now.replace(tzinfo=None)
        premium = bool(user.premium_until and user.premium_until > now)
        return daily, premium
    finally:
        db.close()


async def setup_handlers(bot, update: types.Update):
    """Main dispatcher for handling messages and callbacks"""
    try:
        if update.message:
            msg = update.message
            # Handle successful payment first
            if msg.successful_payment:
                await handle_successful_payment(bot, msg)
                return

            logger.info(f"Message from {msg.from_user.id}: {msg.text}")
            if msg.text:
                if msg.text == _TAROT_DAILY_SUBSCRIBE_TEXT:
                    await handle_tarot_daily_subscription(bot, msg, True)
                elif msg.text == _TAROT_DAILY_UNSUBSCRIBE_TEXT:
                    await handle_tarot_daily_subscription(bot, msg, False)
                elif msg.text == _PREMIUM_BUTTON_TEXT:
                    await handle_premium_info(bot, msg)
                elif msg.text == _PREMIUM_ACTIVE_TEXT:
                    await handle_premium_info(bot, msg)
                elif msg.text == _SPREADS_BUTTON_TEXT:
                    await handle_spreads_menu(bot, msg)
                elif msg.text.startswith("/start"):
                    await handle_start(bot, msg)
                elif msg.text.startswith("/list"):
                    await handle_list(bot, msg)
                elif msg.text.startswith("/me"):
                    await handle_me(bot, msg)
                elif msg.text.startswith("/help"):
                    await handle_help(bot, msg)
                elif msg.text.startswith("/tarot"):
                    await handle_tarot_intro(bot, msg)
                elif msg.text == _TAROT_BUTTON_TEXT:
                    await handle_tarot_intro(bot, msg)
                elif msg.text.startswith("/subscribers") and msg.from_user.id == ADMIN_ID:
                    await handle_subscribers(bot, msg)
                elif msg.text.startswith("/send_now") and msg.from_user.id == ADMIN_ID:
                    await handle_send_now(bot, msg)
                else:
                    await bot.send_message(msg.chat.id, "Неизвестная команда. Используйте /list или /start")
        elif update.pre_checkout_query:
            await handle_pre_checkout(bot, update.pre_checkout_query)
        elif update.callback_query:
            cb = update.callback_query
            logger.info(f"Callback from {cb.from_user.id}: {cb.data}")
            if _is_duplicate_callback(cb.from_user.id, cb.data):
                try:
                    await bot.answer_callback_query(cb.id)
                except Exception:
                    pass
                return
            data = cb.data
            if data.startswith("sign:"):
                sign = data.split(":", 1)[1]
                if not _is_valid_sign(sign):
                    await bot.answer_callback_query(cb.id, text="Некорректный знак")
                    return
                await handle_show_sign(bot, cb.message.chat.id, cb.from_user.id, sign, cb.message.message_id, cb.id)
            elif data.startswith("sub:"):
                sign = data.split(":", 1)[1]
                if not _is_valid_sign(sign):
                    await bot.answer_callback_query(cb.id, text="Некорректный знак")
                    return
                await handle_subscribe(bot, cb.message.chat.id, cb.from_user.id, sign, cb.message.message_id, cb.id)
            elif data.startswith("unsub:"):
                sign = data.split(":", 1)[1]
                if sign != "all" and not _is_valid_sign(sign):
                    await bot.answer_callback_query(cb.id, text="Некорректный знак")
                    return
                await handle_unsubscribe(bot, cb.message.chat.id, cb.from_user.id, sign, cb.message.message_id, cb.id)
            elif data.startswith("back:"):
                ctx = data.split(":", 1)[1]
                if ctx == "list":
                    await bot.edit_message_text(
                        "Выберите знак зодиака:",
                        chat_id=cb.message.chat.id,
                        message_id=cb.message.message_id,
                        reply_markup=signs_keyboard(),
                    )
                    try:
                        await bot.answer_callback_query(cb.id)
                    except Exception as e:
                        logger.warning(f"Could not answer callback query: {e}")
            elif data == "tarot:open":
                await handle_tarot_open(bot, cb)
            elif data.startswith("spread:"):
                await handle_spread_result(bot, cb)
    except Exception as e:
        logger.error(f"Error in setup_handlers: {e}", exc_info=True)
        raise


async def _send_menu(bot, chat_id: int, telegram_id: int) -> None:
    """Helper to send the main menu keyboard with correct state."""
    daily, premium = await asyncio.to_thread(_get_user_menu_state, telegram_id)
    await bot.send_message(chat_id, "Меню:", reply_markup=main_menu_keyboard(daily, premium))


async def handle_start(bot, msg: types.Message):
    await asyncio.to_thread(
        _get_or_create_user,
        msg.from_user.id,
        msg.from_user.username,
        msg.from_user.first_name,
        msg.from_user.last_name,
    )
    daily, premium = await asyncio.to_thread(_get_user_menu_state, msg.from_user.id)
    text = "Привет! Я бот с гороскопами и раскладами Таро.\nВыберите знак зодиака или используйте команды из меню."
    await bot.send_message(msg.chat.id, text, reply_markup=main_menu_keyboard(daily, premium))
    await bot.send_message(msg.chat.id, "Выберите знак зодиака:", reply_markup=signs_keyboard())


async def handle_help(bot, msg: types.Message):
    daily, premium = await asyncio.to_thread(_get_user_menu_state, msg.from_user.id)
    text = (
        "Доступные команды:\n"
        "/start — начать работу\n"
        "/list — список знаков\n"
        "/me — мои подписки\n"
        "/tarot — 🔮 предсказание Таро\n"
        "/help — помощь\n\n"
        "🔮 Кнопка «Выбрать расклад» — развёрнутые расклады Таро\n"
        "🌙 Кнопка «Подписаться на ежедневное предсказание» — карта Таро каждое утро в 10:00 МСК\n"
        "⭐ Premium — безлимитные предсказания за 99 руб/мес"
    )
    await bot.send_message(msg.chat.id, text, reply_markup=main_menu_keyboard(daily, premium))


async def handle_list(bot, msg: types.Message):
    await bot.send_message(msg.chat.id, "Выберите знак:", reply_markup=signs_keyboard())
    await _send_menu(bot, msg.chat.id, msg.from_user.id)


async def handle_me(bot, msg: types.Message):
    subs = await asyncio.to_thread(_get_user_subscriptions, msg.from_user.id)
    if not subs:
        await bot.send_message(msg.chat.id, "Вы не подписаны ни на один знак. Используйте /list")
        return

    text = f"Вы подписаны на: {', '.join([SIGN_TITLES.get(s, s) for s in subs])}"
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"Отписаться {SIGN_TITLES.get(sign, sign)}",
                callback_data=f"unsub:{sign}",
            )
        ]
        for sign in subs
    ]
    buttons.append([types.InlineKeyboardButton(text="Отписаться от всех", callback_data="unsub:all")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(msg.chat.id, text, reply_markup=kb)


async def handle_show_sign(bot, chat_id: int, user_id: int, sign: str, message_id: int, callback_id: str):
    subscribed = await asyncio.to_thread(_is_subscribed, user_id, sign)
    text = await fetch_horoscope(sign)
    await bot.edit_message_text(
        text,
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=sign_detail_keyboard(sign, subscribed=subscribed),
    )


async def handle_subscribe(bot, chat_id: int, user_id: int, sign: str, message_id: int, callback_id: str):
    was_updated = await asyncio.to_thread(_subscribe_user, user_id, sign)

    try:
        await bot.answer_callback_query(callback_id, text=f"Вы подписаны на {SIGN_TITLES.get(sign, sign)}")
    except Exception as e:
        logger.warning(f"Could not answer callback query: {e}")

    if was_updated:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=sign_detail_keyboard(sign, subscribed=True),
            )
        except Exception as e:
            logger.warning(f"Could not edit message reply markup: {e}")


async def handle_unsubscribe(bot, chat_id: int, user_id: int, sign: str, message_id: int, callback_id: str):
    unsubscribed = await asyncio.to_thread(_unsubscribe_user, user_id, sign)
    if not unsubscribed:
        try:
            await bot.answer_callback_query(callback_id, text="Вы не были подписаны")
        except Exception as e:
            logger.warning(f"Could not answer callback query: {e}")
        return

    answer_text = "Отписались от всех" if sign == "all" else f"Отписались от {SIGN_TITLES.get(sign, sign)}"
    try:
        await bot.answer_callback_query(callback_id, text=answer_text)
    except Exception as e:
        logger.warning(f"Could not answer callback query: {e}")

    if sign != "all":
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=sign_detail_keyboard(sign, subscribed=False),
            )
        except Exception as e:
            logger.warning(f"Could not edit message reply markup: {e}")


async def handle_subscribers(bot, msg: types.Message):
    active_users, stats = await asyncio.to_thread(_get_subscribers_stats)
    lines = [f"Активных пользователей: {active_users}"]
    lines.append(f"Всего активных подписок: {sum(cnt for _, cnt in stats)}")
    lines.append("")
    for sign, cnt in sorted(stats, key=lambda item: item[1], reverse=True):
        lines.append(f"{SIGN_TITLES.get(sign, sign.title())}: {cnt}")

    await bot.send_message(msg.chat.id, "\n".join(lines))


async def handle_send_now(bot, msg: types.Message):
    from .scheduler import send_daily

    await send_daily(bot)
    await bot.send_message(msg.chat.id, "Рассылка отправлена")


async def handle_tarot_intro(bot, msg: types.Message):
    """Send tarot intro message with 'Open card' button."""
    await bot.send_message(msg.chat.id, _TAROT_INTRO, reply_markup=tarot_open_keyboard(), parse_mode="HTML")


async def handle_tarot_open(bot, cb: types.CallbackQuery):
    """Draw a random tarot card and send it to the user."""
    try:
        await bot.answer_callback_query(cb.id, text="🃏 Открываю карту...")
    except Exception as e:
        logger.warning(f"Could not answer tarot callback: {e}")

    allowed, remaining = await asyncio.to_thread(_check_and_increment_tarot_limit, cb.from_user.id)
    if not allowed:
        await bot.send_message(
            cb.message.chat.id,
            "⛔ Вы исчерпали лимит раскладов на эту неделю (10/10).\nЛимит обновится в понедельник.\n\n"
            "⭐ Оформите Premium для безлимитных предсказаний!",
        )
        return

    card = draw_random_card()
    limit_line = "" if remaining == 999 else f"\n\n📊 Осталось раскладов на этой неделе: {remaining}"
    caption = (
        f"🃏 <b>{card['name']}</b> ({card['name_en']})\n"
        f"Аркан: {card['number']}\n\n"
        f"{card['meaning']}{limit_line}"
    )

    try:
        await bot.send_photo(cb.message.chat.id, photo=card["image"], caption=caption, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to send tarot photo, sending text only: {e}")
        await bot.send_message(cb.message.chat.id, caption, parse_mode="HTML")

    try:
        await bot.edit_message_reply_markup(
            chat_id=cb.message.chat.id,
            message_id=cb.message.message_id,
            reply_markup=None,
        )
    except Exception as e:
        logger.warning(f"Could not remove tarot keyboard: {e}")


async def handle_tarot_daily_subscription(bot, msg: types.Message, subscribed: bool):
    """Toggle daily tarot subscription for a user."""
    await asyncio.to_thread(_set_tarot_daily_subscription, msg.from_user.id, subscribed)
    is_premium = await asyncio.to_thread(_is_premium, msg.from_user.id)
    if subscribed:
        label = "🌙 Вы подписались на ежедневное предсказание Таро. Карта будет приходить каждое утро в 10:00 МСК."
    else:
        label = "🌙 Вы отписались от ежедневного предсказания Таро."
    await bot.send_message(msg.chat.id, label, reply_markup=main_menu_keyboard(subscribed, is_premium))


async def handle_premium_info(bot, msg: types.Message):
    """Show premium status or send invoice."""
    is_premium = await asyncio.to_thread(_is_premium, msg.from_user.id)
    if is_premium:
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(telegram_id=msg.from_user.id).first()
            until = user.premium_until.strftime("%d.%m.%Y") if user and user.premium_until else "—"
        finally:
            db.close()
        await bot.send_message(
            msg.chat.id,
            f"⭐ <b>Premium активен</b>\n\nБезлимитные предсказания до: <b>{until}</b>",
            parse_mode="HTML",
        )
    else:
        text = (
            "⭐ <b>Premium подписка</b>\n\n"
            "🔓 Безлимитные предсказания Таро\n"
            "🔓 Все расклады без ограничений\n"
            "💰 Стоимость: 50 ⭐ Telegram Stars (~99 руб)\n"
            "📅 Срок: 30 дней\n\n"
            "Нажмите кнопку оплаты ниже:"
        )
        await bot.send_message(msg.chat.id, text, parse_mode="HTML")
        await send_premium_invoice(bot, msg.chat.id)


async def handle_pre_checkout(bot, query: types.PreCheckoutQuery):
    """Answer pre-checkout query — always approve."""
    try:
        await bot.answer_pre_checkout_query(query.id, ok=True)
    except Exception as e:
        logger.error(f"Failed to answer pre-checkout query: {e}")


async def handle_successful_payment(bot, msg: types.Message):
    """Handle successful Telegram Stars payment."""
    logger.info(f"Successful payment from {msg.from_user.id}: {msg.successful_payment.total_amount} XTR")
    expiry = await asyncio.to_thread(_activate_premium, msg.from_user.id)
    until = expiry.strftime("%d.%m.%Y")
    daily, _ = await asyncio.to_thread(_get_user_menu_state, msg.from_user.id)
    await bot.send_message(
        msg.chat.id,
        f"✅ <b>Premium активирован!</b>\n\n"
        f"Безлимитные предсказания Таро до: <b>{until}</b>\n"
        f"Спасибо за поддержку! 🙏",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(daily, True),
    )


async def handle_spreads_menu(bot, msg: types.Message):
    """Show available tarot spreads menu."""
    await bot.send_message(msg.chat.id, _SPREADS_INTRO, reply_markup=spreads_keyboard(), parse_mode="HTML")


async def handle_spread_result(bot, cb: types.CallbackQuery):
    """Fetch and send a tarot spread result."""
    spread_key = cb.data.split(":", 1)[1]
    if spread_key not in _VALID_SPREADS:
        try:
            await bot.answer_callback_query(cb.id, text="Неизвестный расклад")
        except Exception:
            pass
        return

    try:
        await bot.answer_callback_query(cb.id, text="🃏 Тяну карты...")
    except Exception as e:
        logger.warning(f"Could not answer spread callback: {e}")

    allowed, remaining = await asyncio.to_thread(_check_and_increment_tarot_limit, cb.from_user.id)
    if not allowed:
        await bot.send_message(
            cb.message.chat.id,
            "⛔ Вы исчерпали лимит раскладов на эту неделю (10/10).\nЛимит обновится в понедельник.\n\n"
            "⭐ Оформите Premium для безлимитных предсказаний!",
        )
        return

    spread = SPREADS[spread_key]
    result = await fetch_spread(spread_key)

    if not result:
        await bot.send_message(
            cb.message.chat.id,
            "😔 Не удалось получить расклад, попробуйте позже.",
        )
        return

    limit_line = "" if remaining == 999 else f"\n\n📊 Осталось раскладов на этой неделе: {remaining}"
    text = f"{spread['title']}\n{spread['description']}\n\n{result}{limit_line}"

    # Truncate if exceeds Telegram limit
    if len(text) > TELEGRAM_MESSAGE_LIMIT:
        text = text[: TELEGRAM_MESSAGE_LIMIT - 3] + "..."

    await bot.send_message(cb.message.chat.id, text)

    try:
        await bot.edit_message_reply_markup(
            chat_id=cb.message.chat.id,
            message_id=cb.message.message_id,
            reply_markup=None,
        )
    except Exception as e:
        logger.warning(f"Could not remove spread keyboard: {e}")
