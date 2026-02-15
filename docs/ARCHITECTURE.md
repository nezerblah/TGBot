# Архитектура приложения

## 🏗️ Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Users                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ (Отправляют сообщения)
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Telegram Bot API (Webhook)                      │
│  https://tg-bot-xxx.up.railway.app/webhook/{secret}         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ (POST запрос с Update)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   FastAPI приложение                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ webhook.py: GET /webhook/{secret}                   │   │
│  │ - Проверка secret_token                             │   │
│  │ - Парсинг Update JSON                               │   │
│  │ - Передача в обработчик                             │   │
│  └────────────────┬─────────────────────────────────────┘   │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐   │
│  │ handlers.py: setup_handlers(bot, update)             │   │
│  │ - Маршрутизация команд                               │   │
│  │ - Обработка сообщений                                │   │
│  │ - Вызов нужного хендлера                             │   │
│  └────────────────┬─────────────────────────────────────┘   │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐   │
│  │ db.py + models.py: SQLAlchemy                        │   │
│  │ - Сохранение пользователей                           │   │
│  │ - Управление подписками                              │   │
│  │ - Запросы к БД                                       │   │
│  └────────────────┬─────────────────────────────────────┘   │
│                   │                                          │
└────────────────────┼──────────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────────┐
│             PostgreSQL Database (Railway)                      │
│  - users (id, telegram_id, username, date_joined)             │
│  - subscriptions (id, user_id, sign, active, date_created)    │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│               APScheduler (Планировщик)                       │
│ Каждый день в 11:00 МСК:                                      │
│ 1. Запрашивает подписчиков по знакам зодиака                  │
│ 2. Парсит гороскопы через horo/parser.py                      │
│ 3. Отправляет сообщения через bot.send_message()             │
│ 4. Обрабатывает ошибки (забаненные пользователи)              │
└───────────────────────────────────────────────────────────────┘
```

## 📚 Компоненты

### 1. **WebHook Endpoint** (`webhook.py`)

```python
POST /webhook/{secret}
```

- Получает обновления от Telegram
- Проверяет `X-Telegram-Bot-Api-Secret-Token`
- Парсит JSON и создает Update объект
- Передает в `process_update()`

**Безопасность:**
- Проверка `secret` в URL
- Проверка `secret_token` в заголовке
- Защита от несанкционированного доступа

### 2. **Bot Core** (`bot.py`)

```python
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
```

- Инициализирует бота с токеном
- `process_update()` - основной обработчик апдейтов
- Не использует polling, только WebHook

### 3. **Handlers** (`handlers.py`)

Обрабатывает команды:
- `/start` - регистрация пользователя
- `/stop` - отписка
- `/sign` - выбор знака зодиака
- Текстовые сообщения - выбор знака по тексту

**Особенности:**
- Асинхронная обработка
- Сохранение данных в БД
- Отправка ответных сообщений

### 4. **Database Layer** (`db.py` + `models.py`)

**Модели:**
```
User
├── id (Primary Key)
├── telegram_id (уникальный)
├── username
└── date_joined

Subscription
├── id (Primary Key)
├── user_id (Foreign Key → User)
├── sign (знак зодиака)
├── active (активна ли подписка)
└── date_created
```

**Функции:**
- Создание/обновление пользователей
- Управление подписками
- Запросы для планировщика

### 5. **Scheduler** (`scheduler.py`)

**Работает в фоновом режиме:**

```
Каждый день в 11:00 МСК:

1. get_db() → открыть сессию БД
2. query(Subscription).distinct(sign) → получить знаки
3. for each sign:
   - fetch_horoscope(sign) → парсить гороскоп
   - query(Subscription).filter(sign) → найти подписчиков
   - for each subscriber:
     - bot.send_message(telegram_id, text) → отправить
     - on error: pass (пользователь забанил бота)
```

**Особенности:**
- Использует AsyncIOScheduler
- Timezone: Europe/Moscow
- Обработка исключений (не прерывает работу)

### 6. **Horoscope Parser** (`horo/parser.py`)

**Функция:** `fetch_horoscope(sign: str) → str`

- Запрашивает https://horo.mail.ru/{sign}/
- Парсит HTML с BeautifulSoup4
- Возвращает текст гороскопа
- Кэширует результат (опционально)

**Знаки:** aries, taurus, gemini, cancer, leo, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces

### 7. **Main Application** (`main.py`)

```python
app = FastAPI()
app.include_router(webhook_router)

@app.on_event("startup")
async def startup_event():
    setup_scheduler(bot)  # Запуск планировщика при старте
```

**Функции:**
- Регистрация роутов
- Инициализация таблиц БД
- Запуск планировщика
- Health check (`GET /`)

## 🔄 Flow диаграмма

### Обработка сообщения пользователя:

```
1. Пользователь → Telegram: "/start"
                      ↓
2. Telegram → Webhook: POST /webhook/secret
                      ↓
3. webhook.py: Проверка secret и заголовков
                      ↓
4. bot.py: process_update(update_dict)
                      ↓
5. handlers.py: setup_handlers(bot, update)
                      ↓
6. Command matcher: Это "/start"?
                      ↓
7. Handler: start_command(message)
                      ↓
8. db.py: get_or_create_user(telegram_id)
                      ↓
9. bot.send_message(chat_id, "Добро пожаловать!")
                      ↓
10. Telegram → Пользователь: "Добро пожаловать!"
```

### Отправка гороскопа по расписанию:

```
Каждый день в 11:00 МСК:
1. APScheduler запускает send_daily()
                      ↓
2. get_db() → SessionLocal()
                      ↓
3. query(Subscription).filter(active=True).distinct(sign)
                      ↓
4. for sign in signs:
     fetch_horoscope(sign) → "Сегодня удачный день..."
                      ↓
     query(Subscription).filter(sign=sign, active=True)
                      ↓
     for subscriber in subscribers:
       bot.send_message(telegram_id, horoscope_text)
                      ↓
5. Пользователь получает гороскоп в Telegram
```

## 🔐 Безопасность

### WebHook Security:
- ✅ Secret в URL пути
- ✅ Secret Token в заголовке `X-Telegram-Bot-Api-Secret-Token`
- ✅ Проверка обоих значений
- ✅ 403 Forbidden если не совпадает

### Database Security:
- ✅ Параметризованные запросы (SQLAlchemy)
- ✅ Защита от SQL injection
- ✅ Сессионное управление ошибками

### Token Security:
- ✅ BOT_TOKEN в переменных окружения
- ✅ Не коммичится в Git
- ✅ Защита на уровне Railway

## 📊 Масштабируемость

### Текущее решение:
- ✅ Асинхронная обработка (FastAPI + asyncio)
- ✅ Один инстанс приложения
- ✅ SQLite для разработки, PostgreSQL для production
- ✅ Встроенный планировщик (APScheduler)

### Для масштабирования:
- Несколько инстансов приложения (Railway)
- Redis для распределенного кэша
- Celery вместо встроенного scheduler
- Message Queue (RabbitMQ) для асинхронных задач

## 🚀 Оптимизация

### Текущее:
- Кэширование гороскопов (можно добавить)
- Batch запросы к БД
- Асинхронная отправка сообщений

### Возможные улучшения:
- Redis кэш для гороскопов
- Пулинг соединений с БД
- Rate limiting для WebHook
- Retry логика для отправки сообщений
- Monitoring с Prometheus/Grafana

---

**Архитектура оптимизирована для:**
- ✅ Production deployment
- ✅ Масштабируемость
- ✅ Надежность
- ✅ Безопасность

