# Telegram Horoscopes Bot 🤖

Telegram бот на FastAPI + aiogram, который парсит гороскопы с horo.mail.ru и отправляет их подписчикам в 11:00 по МСК.

**Архитектура:** WebHook (не polling), асинхронная обработка, APScheduler для расписания, SQLite база данных

## 🚀 Быстрый старт

### Локальная разработка

1. **Установите зависимости:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Создайте `.env` файл:**
```bash
cp .env.example .env
# Заполните значения BOT_TOKEN, ADMIN_ID, WEBHOOK_SECRET
```

3. **Запустите приложение:**
```bash
uvicorn app.main:app --reload
```

Приложение будет доступно на `http://localhost:8000`
БД автоматически создастся в `tg_bot.db`

### 🚂 Деплой на Railway.com

1. **Убедитесь, что все изменения сохранены:**
```bash
git status
git add .
git commit -m "Fix bot implementation with SQLite"
git push origin main
```

2. **На railway.app:**
   - Создайте новый проект
   - Выберите GitHub репозиторий
   - Railway автоматически обнаружит `Procfile` и развернёт приложение

3. **Установите переменные окружения:**
   - BOT_TOKEN: Токен вашего бота
   - WEBHOOK_SECRET: Секретный ключ (используйте что-то сложное)
   - ADMIN_ID: Ваш Telegram ID (для админ команд)

4. **Настройте webhook:**
   - Используйте скрипт `scripts/set_webhook.py`
   - Или выполните HTTP запрос:
   ```bash
   curl -X POST \
     https://api.telegram.org/bot{BOT_TOKEN}/setWebhook \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://your-railway-app.up.railway.app/webhook",
       "secret_token": "your-webhook-secret"
     }'
   ```# 5. bash scripts/setup_webhook.sh
```

## 📋 Структура проекта

```
app/
├── bot.py           # aiogram бот и обработка апдейтов
├── handlers.py      # обработчики команд и сообщений
├── scheduler.py     # APScheduler для отправки гороскопов
├── db.py            # SQLAlchemy конфигурация
├── models.py        # модели БД (User, Subscription)
├── keyboards.py     # Telegram клавиатуры
├── webhook.py       # FastAPI эндпоинт для вебхука
├── main.py          # FastAPI приложение
└── horo/
    └── parser.py    # парсер гороскопов с horo.mail.ru

scripts/
└── set_webhook.py   # скрипт регистрации вебхука

requirements.txt     # зависимости проекта
Procfile            # инструкции для Railway
```

## 🔧 Переменные окружения

```env
BOT_TOKEN              # от @BotFather в Telegram
ADMIN_ID               # ваш Telegram ID
DATABASE_URL           # PostgreSQL на Railway (автоматически)
WEBHOOK_SECRET         # случайная строка для безопасности
WEBHOOK_URL            # https://ваш-домен.up.railway.app/webhook/secret
ENVIRONMENT            # production/development
```

## 📦 Зависимости

- **FastAPI 0.95.2** - веб-фреймворк
- **aiogram 3.0.0b7** - Telegram бот API
- **SQLAlchemy 1.4.49** - ORM для БД
- **APScheduler 3.10.1** - планировщик задач
- **BeautifulSoup4 4.12.2** - парсинг HTML

## 🧪 Тестирование

```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=app

# Конкретный тест
pytest tests/test_parser.py
```

## 📖 Документация

Полная документация по деплою на Railway находится в папке [`docs/`](./docs/README.md):

- 📌 **[START_HERE.md](./docs/START_HERE.md)** - выберите ваш уровень
- 📚 **[DEPLOYMENT_CHECKLIST.md](./docs/DEPLOYMENT_CHECKLIST.md)** - полный гайд
- ⚡ **[DEPLOYMENT_CHEATSHEET.md](./docs/DEPLOYMENT_CHEATSHEET.md)** - краткий гайд
- 🏗️ **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - архитектура приложения

## 🔧 Управление на Railway

```bash
# Просмотр логов
railway logs

# Переменные окружения
railway variables

# Установка вебхука
bash scripts/setup_webhook.sh

# Подготовка проекта к деплою
bash scripts/deploy_prepare.sh
```

## 🆘 Решение проблем

**Бот не отвечает:** Проверьте что вебхук зарегистрирован
```bash
bash scripts/setup_webhook.sh
```

**Ошибки БД:** Проверьте `DATABASE_URL` в переменных окружения
```bash
railway variables | grep DATABASE_URL
```

**Все не работает:** Смотрите полные гайды в папке [`docs/`](./docs/README.md)

## 📚 Полезные ссылки

- [Railway документация](https://docs.railway.app/)
- [Telegram Bot API](https://core.telegram.org/bots)
- [aiogram документация](https://docs.aiogram.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)

## 📝 Лицензия

[MIT License](LICENSE)

---

**Готовы к деплою?** → Откройте [`docs/START_HERE.md`](./docs/START_HERE.md) 🚀

