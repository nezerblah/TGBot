# ⚡ Шпаргалка TGBot - Краткий справочник

## 🚀 Быстрый запуск (3 минуты)

```bash
# Создать и активировать окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r TGBot/requirements.txt

# Заполнить конфигурацию
cp TGBot/.env.example TGBot/.env
nano TGBot/.env

# Запустить бота
python TGBot/main.py
```

---

## 📱 Команды бота

```
/start      - Подписка на гороскопы
/list       - Просмотр гороскопа на сегодня
/mysubs     - Мои подписки
/send_today - Запустить рассылку (админ)
/subscribers - Список подписчиков (админ)
```

---

## 🔧 Основные функции в main.py

### Работа с БД
```python
subscribe_user(user_id, 'aries')        # Подписать
unsubscribe_user(user_id, 'aries')      # Отписать
get_user_subscriptions(user_id)         # Получить подписки
get_subscribers()                        # Получить подписчиков
```

### Безопасные операции
```python
_safe_send_message(context, chat_id, text)      # Отправить
_safe_edit_message(query, text, markup)         # Отредактировать
_safe_delete_message(context, message)          # Удалить
```

### Утилиты
```python
_validate_zodiac_slug('aries')          # Проверить знак
_truncate_message(text)                 # Обрезать >4000 символов
_format_horoscope_message(name, text)   # Форматировать
parse_horoscope('aries')                # Получить гороскоп
```

---

## 📊 Структура БД

```sql
-- Таблица подписок
subscriptions
├── user_id INTEGER      -- ID пользователя
└── zodiac_slug TEXT     -- Знак зодиака

-- Примеры знаков:
aries, taurus, gemini, cancer, leo, virgo,
libra, scorpio, sagittarius, capricorn, aquarius, pisces
```

---

## 🔐 Конфигурация (.env)

```env
# Токен бота (получить у @BotFather)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# ID админа (получить у @userinfobot)
ADMIN_ID=123456789
```

---

## 📝 Логирование

```python
import logging

logging.info("Информация")      # INFO
logging.warning("Предупреждение")   # WARNING
logging.error("Ошибка")         # ERROR

# Формат: 2026-02-15 14:30:45,123 - LEVEL - Message
```

**Уровни логирования:**
- `INFO` - нормальные события ✅
- `WARNING` - что-то странное ⚠️
- `ERROR` - серьезная проблема ❌

---

## 🎯 Добавление новой команды

```python
async def my_command(update: Update, context: object) -> None:
    """Описание команды."""
    user_id = update.effective_user.id
    
    try:
        # Ваш код здесь
        await _safe_send_message(context, user_id, "Привет!")
        logging.info(f"Command executed for {user_id}")
    except Exception as e:
        logging.error(f"Error: {e}")
        await _safe_send_message(context, user_id, "Ошибка 😔")

# В main():
app.add_handler(CommandHandler("mycommand", my_command))
```

---

## 🔘 Добавление новой кнопки

```python
# В функции button():
if action == "my_action":
    if not _validate_zodiac_slug(sign_slug):
        await query.answer(text="Invalid sign", show_alert=True)
        return
    
    await query.answer(text="Success! ✅", show_alert=False)
    await _safe_send_message(context, chat_id, f"Result!")
```

---

## 💾 Добавление функции БД

```python
def my_db_function(user_id: int) -> bool:
    """Описание функции."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Ваш SQL здесь
            conn.execute("INSERT INTO ...")
        logging.info(f"Operation success for {user_id}")
        return True
    except Exception as e:
        logging.error(f"DB Error: {e}")
        return False
```

---

## 🐛 Отладка

### Посмотреть логи
```bash
# В консоли во время запуска видны логи
python TGBot/main.py
```

### Добавить debug лог
```python
logging.info(f"Debug: variable={my_var}")  # Вставить где нужно
```

### Протестировать функцию
```python
# В конце main.py (перед app.run_polling())
from TGBot.main import get_user_subscriptions
print(get_user_subscriptions(123456))
```

---

## ⏰ Изменить время рассылки

```python
# В main.py найти:
job_time = time(hour=16, minute=15, second=0, tzinfo=msk_tz)

# Изменить часы и минуты:
job_time = time(hour=12, minute=30, second=0, tzinfo=msk_tz)
```

---

## 🚀 Развертывание

### Railway (рекомендуется)
```
1. Создать аккаунт на railway.app
2. Подключить GitHub репозиторий
3. Добавить переменные окружения:
   TELEGRAM_BOT_TOKEN=...
   ADMIN_ID=...
4. Deploy!
```

### VPS (Ubuntu)
```bash
# Создать systemd сервис
sudo nano /etc/systemd/system/tgbot.service

# Содержимое файла:
[Unit]
Description=Telegram Horoscope Bot
After=network.target

[Service]
Type=simple
User=username
WorkingDirectory=/path/to/TGBot
ExecStart=/path/to/venv/bin/python /path/to/TGBot/main.py
Restart=always

[Install]
WantedBy=multi-user.target

# Запустить:
sudo systemctl enable tgbot
sudo systemctl start tgbot
sudo systemctl status tgbot
```

---

## 📚 Документация

| Файл | Для кого |
|------|----------|
| **QUICKSTART.md** | Быстрый старт (30 мин) |
| **README.md** | Основная информация |
| **DEVELOPMENT_GUIDE.md** | Разработчики |
| **FAQ.md** | Помощь и проблемы |
| **DOCUMENTATION.md** | Полная архитектура |

---

## 🆘 Частые проблемы

### "ModuleNotFoundError: No module named 'telegram'"
```bash
pip install -r requirements.txt
```

### "TELEGRAM_BOT_TOKEN not set"
```bash
cp TGBot/.env.example TGBot/.env
# Отредактировать .env с реальными значениями
```

### "database is locked"
```bash
# Перезапустить бота
# Только один процесс должен работать с БД
```

### Бот не отвечает
```
1. Проверить токен в .env
2. Проверить интернет подключение
3. Посмотреть логи в консоли
4. Перезапустить бота
```

---

## ✅ Чек-лист перед деплоем

- [ ] .env файл создан с реальными значениями
- [ ] `python TGBot/main.py` запускается без ошибок
- [ ] Тестировано в Telegram (/start работает)
- [ ] Логирование видимо (при запуске видны INFO логи)
- [ ] Рассылка протестирована (/send_today работает)
- [ ] Нет критических ERROR логов
- [ ] requirements.txt установлены
- [ ] .env НЕ добавлен в git (используйте .env.example)

---

## 🎯 Полезные команды

```bash
# Активировать окружение
source venv/bin/activate

# Установить пакет
pip install package_name

# Выбросить все пакеты в requirements.txt
pip freeze > requirements.txt

# Запустить с логированием в файл
python TGBot/main.py >> bot.log 2>&1

# Остановить процесс
Ctrl+C

# Найти процесс Python
ps aux | grep python

# Убить процесс
kill -9 <pid>
```

---

## 📞 Ссылки

- [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [@BotFather](https://t.me/BotFather) - создание ботов
- [@userinfobot](https://t.me/userinfobot) - получить ID

---

## 🚀 Быстрые советы

1. **Сохраняйте .env в .gitignore** - не коммитьте токены!
2. **Используйте логирование** - помогает отладить
3. **Тестируйте локально** - перед деплоем
4. **Читайте документацию** - в проекте 1800+ строк
5. **Добавляйте комментарии** - помогает другим разработчикам

---

```
⚡ Шпаргалка готова!
Используйте её как справочник.
Для деталей смотрите полную документацию в проекте.
```

**Версия:** 2.0  
**Последнее обновление:** 15.02.2026  
**Статус:** ✅ Актуально

