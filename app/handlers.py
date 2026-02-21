import asyncio
from collections import OrderedDict
import logging
import os
import time

from aiogram import types
from sqlalchemy import func

from .db import SessionLocal
from .horo.parser import fetch_horoscope
from .joke_parser import fetch_random_joke
from .keyboards import SIGN_TITLES, ZODIAC_SIGNS, joke_subscription_keyboard, sign_detail_keyboard, signs_keyboard
from .models import Subscription, User

logger = logging.getLogger(__name__)

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

_CALLBACK_DEBOUNCE_SECONDS = 1.0
_CALLBACK_CACHE_MAX_SIZE = 5000
_last_callback: OrderedDict[tuple[int, str], float] = OrderedDict()

_VALID_SIGNS = frozenset(ZODIAC_SIGNS)

_JOKE_SUBSCRIBE_TEXT = "Подписаться на шутки"
_JOKE_UNSUBSCRIBE_TEXT = "Отписаться от шуток"


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


def _get_joke_subscription(telegram_id: int) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        return bool(user and user.joke_subscribed)
    finally:
        db.close()


def _set_joke_subscription(telegram_id: int, subscribed: bool) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, joke_subscribed=subscribed)
            db.add(user)
            db.commit()
            return subscribed

        if user.joke_subscribed == subscribed:
            return subscribed

        user.joke_subscribed = subscribed
        db.commit()
        return subscribed
    finally:
        db.close()


async def setup_handlers(bot, update: types.Update):
    """Main dispatcher for handling messages and callbacks"""
    try:
        if update.message:
            msg = update.message
            logger.info(f"Message from {msg.from_user.id}: {msg.text}")
            if msg.text:
                if msg.text == _JOKE_SUBSCRIBE_TEXT:
                    await handle_joke_subscription(bot, msg, True)
                elif msg.text == _JOKE_UNSUBSCRIBE_TEXT:
                    await handle_joke_subscription(bot, msg, False)
                elif msg.text.startswith("/start"):
                    await handle_start(bot, msg)
                elif msg.text.startswith("/list"):
                    await handle_list(bot, msg)
                elif msg.text.startswith("/me"):
                    await handle_me(bot, msg)
                elif msg.text.startswith("/help"):
                    await handle_help(bot, msg)
                elif msg.text.startswith("/joke"):
                    await handle_joke(bot, msg)
                elif msg.text.startswith("/subscribers") and msg.from_user.id == ADMIN_ID:
                    await handle_subscribers(bot, msg)
                elif msg.text.startswith("/send_now") and msg.from_user.id == ADMIN_ID:
                    await handle_send_now(bot, msg)
                else:
                    await bot.send_message(msg.chat.id, "Неизвестная команда. Используйте /list или /start")
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
    except Exception as e:
        logger.error(f"Error in setup_handlers: {e}", exc_info=True)
        raise


async def handle_start(bot, msg: types.Message):
    await asyncio.to_thread(
        _get_or_create_user,
        msg.from_user.id,
        msg.from_user.username,
        msg.from_user.first_name,
        msg.from_user.last_name,
    )
    subscribed = await asyncio.to_thread(_get_joke_subscription, msg.from_user.id)
    text = "Привет! Я бот с гороскопами.\nВыберите знак зодиака или используйте команды из меню."
    await bot.send_message(msg.chat.id, text, reply_markup=joke_subscription_keyboard(subscribed))
    await bot.send_message(msg.chat.id, "Выберите знак зодиака:", reply_markup=signs_keyboard())


async def handle_help(bot, msg: types.Message):
    subscribed = await asyncio.to_thread(_get_joke_subscription, msg.from_user.id)
    text = (
        "Доступные команды:\n"
        "/start — начать работу\n"
        "/list — список знаков\n"
        "/me — мои подписки\n"
        "/joke — случайный анекдот\n"
        "/help — помощь"
    )
    await bot.send_message(msg.chat.id, text, reply_markup=joke_subscription_keyboard(subscribed))


async def handle_joke(bot, msg: types.Message):
    subscribed = await asyncio.to_thread(_get_joke_subscription, msg.from_user.id)
    joke = await fetch_random_joke()
    if joke:
        await bot.send_message(msg.chat.id, f"😂 {joke}", reply_markup=joke_subscription_keyboard(subscribed))
    else:
        await bot.send_message(
            msg.chat.id,
            "Не удалось загрузить анекдот 😢",
            reply_markup=joke_subscription_keyboard(subscribed),
        )


async def handle_list(bot, msg: types.Message):
    subscribed = await asyncio.to_thread(_get_joke_subscription, msg.from_user.id)
    await bot.send_message(msg.chat.id, "Выберите знак:", reply_markup=signs_keyboard())
    await bot.send_message(msg.chat.id, "Меню шуток:", reply_markup=joke_subscription_keyboard(subscribed))


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
    # trigger send
    from .scheduler import send_daily

    await send_daily(bot)
    await bot.send_message(msg.chat.id, "Рассылка отправлена")


async def handle_joke_subscription(bot, msg: types.Message, subscribed: bool):
    await asyncio.to_thread(_set_joke_subscription, msg.from_user.id, subscribed)
    label = "Вы подписались на ежедневные шутки" if subscribed else "Вы отписались от ежедневных шуток"
    await bot.send_message(msg.chat.id, label, reply_markup=joke_subscription_keyboard(subscribed))
