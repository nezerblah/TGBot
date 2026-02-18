# Telegram Horoscopes Bot

Telegram бот на FastAPI + aiogram (webhook-only), который парсит гороскопы с horo.mail.ru и рассылает подписчикам.

## Быстрый старт

1. Установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Задайте переменные окружения:

```bash
export BOT_TOKEN="<telegram bot token>"
export WEBHOOK_SECRET="<random secret>"
export ADMIN_ID="<your telegram id>"
export WEBHOOK_URL="https://your-domain/webhook"
```

3. Запустите приложение:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Переменные окружения

Обязательные:

- `BOT_TOKEN`
- `WEBHOOK_SECRET`

Рекомендуемые:

- `ADMIN_ID`
- `WEBHOOK_URL`
- `MAX_UPDATE_AGE_SECONDS` (по умолчанию `300`)
- `DATA_DIR` (директория для SQLite-файла `tg_bot.db`)

Настройка рассылки:

- `SCHEDULER_ENABLED` (`true`/`false`, по умолчанию `false`)
- `SCHEDULER_HOUR_MSK` (по умолчанию `11`)
- `SCHEDULER_MINUTE_MSK` (по умолчанию `0`)

## Архитектура

- Webhook endpoint: `POST /webhook`
- FastAPI приложение: `app/main.py`
- Логика Telegram-обработчиков: `app/handlers.py`
- Парсер гороскопа: `app/horo/parser.py`
- База данных: SQLite через SQLAlchemy (`app/db.py`)
- Планировщик: APScheduler (`app/scheduler.py`)

## Тесты

```bash
pytest -q
```

## Скрипт установки webhook

```bash
python scripts/set_webhook.py
```
