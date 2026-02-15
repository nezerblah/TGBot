from aiogram import types
from .keyboards import signs_keyboard, sign_detail_keyboard, SIGN_TITLES
from .db import SessionLocal
from .models import User, Subscription
from .horo.parser import fetch_horoscope
from sqlalchemy import func
import os

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

async def setup_handlers(bot, update: types.Update):
    # Very small dispatcher: handle messages and callbacks
    if update.message:
        msg = update.message
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
        kb = types.InlineKeyboardMarkup()
        for s in subs:
            kb.add(types.InlineKeyboardButton(text=f"Отписаться {SIGN_TITLES.get(s,s)}", callback_data=f"unsub:{s}"))
        if subs:
            kb.add(types.InlineKeyboardButton(text="Отписаться от всех", callback_data="unsub:all"))
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
        sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign).first()
        if not sub:
            sub = Subscription(user_id=user.id, sign=sign, active=True)
            db.add(sub)
        else:
            sub.active = True
        db.commit()
        await bot.answer_callback_query(callback_id, text=f"Вы подписаны на {sign}")
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=sign_detail_keyboard(sign, subscribed=True))
    finally:
        db.close()

async def handle_unsubscribe(bot, chat_id: int, user_id: int, sign: str, message_id: int, callback_id: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            await bot.answer_callback_query(callback_id, text="Вы не подписаны")
            return
        if sign == 'all':
            db.query(Subscription).filter_by(user_id=user.id).update({'active': False})
            db.commit()
            await bot.answer_callback_query(callback_id, text="Отписались от всех")
            return
        sub = db.query(Subscription).filter_by(user_id=user.id, sign=sign).first()
        if sub:
            sub.active = False
            db.commit()
            await bot.answer_callback_query(callback_id, text=f"Отписались от {sign}")
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=sign_detail_keyboard(sign, subscribed=False))
        else:
            await bot.answer_callback_query(callback_id, text="Вы не были подписаны")
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
