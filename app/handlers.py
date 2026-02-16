from aiogram import types
import logging
from .keyboards import signs_keyboard, sign_detail_keyboard, SIGN_TITLES
from .db import SessionLocal
from .models import User, Subscription
from .horo.parser import fetch_horoscope
from sqlalchemy import func
import os

logger = logging.getLogger(__name__)

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

async def setup_handlers(bot, update: types.Update):
    """Main dispatcher for handling messages and callbacks"""
    try:
        if update.message:
            msg = update.message
            logger.info(f"Message from {msg.from_user.id}: {msg.text}")
            if msg.text:
                if msg.text.startswith('/start'):
                    await handle_start(bot, msg)
                elif msg.text.startswith('/list'):
                    await handle_list(bot, msg)
                elif msg.text.startswith('/me'):
                    await handle_me(bot, msg)
                elif msg.text.startswith('/subscribers') and msg.from_user.id == ADMIN_ID:
                    await handle_subscribers(bot, msg)
                elif msg.text.startswith('/send_now') and msg.from_user.id == ADMIN_ID:
                    await handle_send_now(bot, msg)
                else:
                    await bot.send_message(msg.chat.id, "Неизвестная команда. Используйте /list или /start")
        elif update.callback_query:
            cb = update.callback_query
            logger.info(f"Callback from {cb.from_user.id}: {cb.data}")
            data = cb.data
            if data.startswith('sign:'):
                sign = data.split(':',1)[1]
                await handle_show_sign(bot, cb.message.chat.id, cb.from_user.id, sign, cb.message.message_id, cb.id)
            elif data.startswith('sub:'):
                sign = data.split(':',1)[1]
                await handle_subscribe(bot, cb.message.chat.id, cb.from_user.id, sign, cb.message.message_id, cb.id)
            elif data.startswith('unsub:'):
                sign = data.split(':',1)[1]
                await handle_unsubscribe(bot, cb.message.chat.id, cb.from_user.id, sign, cb.message.message_id, cb.id)
            elif data.startswith('back:'):
                ctx = data.split(':',1)[1]
                if ctx == 'list':
                    await bot.edit_message_text('Выберите знак зодиака:', chat_id=cb.message.chat.id, message_id=cb.message.message_id, reply_markup=signs_keyboard())
                    try:
                        await bot.answer_callback_query(cb.id)
                    except Exception as e:
                        logger.warning(f"Could not answer callback query: {e}")
    except Exception as e:
        logger.error(f"Error in setup_handlers: {e}", exc_info=True)
        raise

async def handle_start(bot, msg: types.Message):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=msg.from_user.id).first()
        if not user:
            user = User(telegram_id=msg.from_user.id, username=msg.from_user.username, first_name=msg.from_user.first_name, last_name=msg.from_user.last_name)
            db.add(user)
            db.commit()
        await bot.send_message(msg.chat.id, "Привет! Выберите знак зодиака:", reply_markup=signs_keyboard())
    finally:
        db.close()

async def handle_list(bot, msg: types.Message):
    await bot.send_message(msg.chat.id, "Выберите знак:", reply_markup=signs_keyboard())

async def handle_me(bot, msg: types.Message):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=msg.from_user.id).first()
        if not user:
            await bot.send_message(msg.chat.id, "Вы не зарегистрированы. Отправьте /start")
            return
        subs = [s.sign for s in user.subscriptions if s.active]
        text = f"Вы подписаны на: {', '.join([SIGN_TITLES.get(s,s) for s in subs]) if subs else 'ничего'}"
        # build keyboard to unsubscribe
        buttons = []
        for s in subs:
            buttons.append([types.InlineKeyboardButton(text=f"Отписаться {SIGN_TITLES.get(s,s)}", callback_data=f"unsub:{s}")])
        if subs:
            buttons.append([types.InlineKeyboardButton(text="Отписаться от всех", callback_data="unsub:all")])
        kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        await bot.send_message(msg.chat.id, text, reply_markup=kb)
    finally:
        db.close()

async def handle_show_sign(bot, chat_id: int, user_id: int, sign: str, message_id: int, callback_id: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=user_id).first()
        subscribed = False
        if user:
            sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign, active=True).first()
            subscribed = bool(sub)
        text = await fetch_horoscope(sign)
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=sign_detail_keyboard(sign, subscribed=subscribed))
    finally:
        db.close()

async def handle_subscribe(bot, chat_id: int, user_id: int, sign: str, message_id: int, callback_id: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            user = User(telegram_id=user_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Check if already subscribed
        sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign).first()
        was_subscribed = sub and sub.active if sub else False

        if not sub:
            sub = Subscription(user_id=user.id, sign=sign, active=True)
            db.add(sub)
        else:
            sub.active = True
        db.commit()

        # Try to answer callback query, but ignore if it's too old
        try:
            await bot.answer_callback_query(callback_id, text=f"Вы подписаны на {sign}")
        except Exception as e:
            logger.warning(f"Could not answer callback query: {e}")

        # Only update keyboard if subscription status actually changed
        if not was_subscribed:
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=sign_detail_keyboard(sign, subscribed=True))
            except Exception as e:
                logger.warning(f"Could not edit message reply markup: {e}")
    finally:
        db.close()

async def handle_unsubscribe(bot, chat_id: int, user_id: int, sign: str, message_id: int, callback_id: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            try:
                await bot.answer_callback_query(callback_id, text="Вы не подписаны")
            except Exception as e:
                logger.warning(f"Could not answer callback query: {e}")
            return
        if sign == 'all':
            db.query(Subscription).filter_by(user_id=user.id).update({'active': False})
            db.commit()
            try:
                await bot.answer_callback_query(callback_id, text="Отписались от всех")
            except Exception as e:
                logger.warning(f"Could not answer callback query: {e}")
            return
        sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign).first()
        if sub and sub.active:
            sub.active = False
            db.commit()
            try:
                await bot.answer_callback_query(callback_id, text=f"Отписались от {sign}")
            except Exception as e:
                logger.warning(f"Could not answer callback query: {e}")
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=sign_detail_keyboard(sign, subscribed=False))
            except Exception as e:
                logger.warning(f"Could not edit message reply markup: {e}")
        else:
            try:
                await bot.answer_callback_query(callback_id, text="Вы не были подписаны")
            except Exception as e:
                logger.warning(f"Could not answer callback query: {e}")
    finally:
        db.close()

async def handle_subscribers(bot, msg: types.Message):
    db = SessionLocal()
    try:
        total = db.query(User).count()
        stats = db.query(Subscription.sign, func.count(Subscription.id)).filter(Subscription.active==True).group_by(Subscription.sign).all()
        lines = [f"Всего пользователей: {total}"]
        for sign, cnt in stats:
            lines.append(f"{sign}: {cnt}")
        await bot.send_message(msg.chat.id, "\n".join(lines))
    finally:
        db.close()

async def handle_send_now(bot, msg: types.Message):
    # trigger send
    from .scheduler import send_daily
    await send_daily(bot)
    await bot.send_message(msg.chat.id, "Рассылка отправлена")
