# 📚 Ресурсы и ссылки для деплоя

## 📖 Документация по деплою (в этом проекте)

| Файл | Назначение | Время | Уровень |
|------|-----------|-------|--------|
| [`DEPLOYMENT_README.md`](./DEPLOYMENT_README.md) | 📌 **Начните отсюда** - обзор всех гайдов | 5 мин | Начинающий |
| [`DEPLOYMENT_CHECKLIST.md`](./DEPLOYMENT_CHECKLIST.md) | Полная пошаговая инструкция | 20-30 мин | Начинающий |
| [`DEPLOYMENT_RAILWAY_QUICK.md`](./DEPLOYMENT_RAILWAY_QUICK.md) | Краткая версия (TL;DR) | 5-10 мин | Опытный |
| [`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) | Детальное руководство со всеми деталями | 15-20 мин | Опытный |
| [`DEPLOYMENT_CHEATSHEET.md`](./DEPLOYMENT_CHEATSHEET.md) | Шпаргалка с командами | 3-5 мин | Опытный |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Архитектура приложения | 10 мин | Все |

## 🛠️ Служебные скрипты

```bash
# Подготовка проекта к деплою
bash deploy_prepare.sh

# Установка вебхука (после развертывания)
bash setup_webhook.sh

# Установка и тестирование локально
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 🌐 Официальные сайты

| Сервис | URL | Функция |
|--------|-----|---------|
| **Railway.app** | https://railway.app | Хостинг приложения |
| **Railway Docs** | https://docs.railway.app | Документация Railway |
| **Railway CLI** | https://docs.railway.app/reference/cli-api | Команды CLI |
| **GitHub** | https://github.com | Хранилище кода |

## 📡 Telegram API и боты

| Ресурс | URL | Назначение |
|--------|-----|-----------|
| **Telegram Bot API** | https://core.telegram.org/bots/api | Документация |
| **Bot Father** | https://t.me/botfather | Создание/управление ботами |
| **userinfobot** | https://t.me/userinfobot | Узнать свой Telegram ID |
| **Telegram Bots Channel** | https://t.me/botfather | Новости о ботах |

## 💻 Технологии в проекте

| Технология | Версия | Сайт | Документация |
|-----------|--------|------|-------------|
| **Python** | 3.9+ | https://python.org | https://docs.python.org |
| **FastAPI** | 0.95.2 | https://fastapi.tiangolo.com | https://fastapi.tiangolo.com/docs |
| **Uvicorn** | 0.22.0 | https://www.uvicorn.org | https://www.uvicorn.org |
| **aiogram** | 3.0.0b7 | https://github.com/aiogram | https://docs.aiogram.dev |
| **SQLAlchemy** | 1.4.49 | https://sqlalchemy.org | https://docs.sqlalchemy.org |
| **Alembic** | 1.11.1 | https://alembic.sqlalchemy.org | https://alembic.sqlalchemy.org |
| **APScheduler** | 3.10.1 | https://apscheduler.readthedocs.io | https://apscheduler.readthedocs.io |
| **BeautifulSoup4** | 4.12.2 | https://www.crummy.com/software/BeautifulSoup | https://www.crummy.com/software/BeautifulSoup/bs4/doc |
| **PostgreSQL** | Latest | https://postgresql.org | https://postgresql.org/docs |

## 🎓 Обучающие ресурсы

### FastAPI
- [FastAPI в 100 строк](https://fastapi.tiangolo.com/deployment/)
- [Асинхронность в Python](https://docs.python.org/3/library/asyncio.html)
- [Pydantic для валидации](https://pydantic-docs.helpmanual.io)

### Telegram Bots
- [Создание своего первого бота](https://core.telegram.org/bots/tutorial)
- [Webhook vs Polling](https://core.telegram.org/bots/faq#webhooks)
- [Безопасность вебхука](https://core.telegram.org/bots/api#setwebhook)

### aiogram
- [aiogram документация](https://docs.aiogram.dev/)
- [aiogram примеры](https://github.com/aiogram/aiogram/tree/dev-3.x/examples)
- [Диспетчеризация команд](https://docs.aiogram.dev/dispatching/router/)

### SQLAlchemy & Alembic
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Миграции с Alembic](https://alembic.sqlalchemy.org/en/latest/)
- [Relationships в SQLAlchemy](https://docs.sqlalchemy.org/en/14/orm/relationships.html)

### Railway
- [Railway Getting Started](https://docs.railway.app/guides/variables)
- [Деплой Python приложения](https://docs.railway.app/guides/python)
- [Управление БД](https://docs.railway.app/databases)

## 🔧 Утилиты и инструменты

```bash
# Установка Railway CLI
npm install -g @railway/cli
# или
brew install railway

# Генерация случайного SECRET
openssl rand -hex 16

# Проверка версий
python3 --version
pip list
railway --version
git --version
```

## 📊 Полезные команды

### Git
```bash
git init
git add .
git commit -m "message"
git push origin main
git log --oneline
```

### Python & pip
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.txt
python3 -c "import sys; print(sys.version)"
```

### Railway CLI
```bash
railway login
railway init
railway link
railway run command
railway logs
railway variables
railway status
```

### FastAPI & Uvicorn
```bash
uvicorn app.main:app --reload
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### PostgreSQL
```bash
psql postgresql://user:password@host:5432/dbname
# Команды в psql:
\dt                 # Список таблиц
\d table_name       # Описание таблицы
SELECT * FROM users;
```

## 🐛 Решение проблем

### Railway документация по проблемам
- [FAQ](https://docs.railway.app/databases/troubleshooting)
- [Troubleshooting](https://docs.railway.app/troubleshooting/help)
- [Pricing & Limits](https://railway.app/pricing)

### Telegram Bot API проблемы
- [BotFather Commands](https://core.telegram.org/bots#botfather)
- [Webhook Security](https://core.telegram.org/bots/api#setwebhook)
- [API Errors](https://core.telegram.org/bots/api#making-requests)

### Python асинхронность
- [asyncio Tutorial](https://docs.python.org/3/library/asyncio-task.html)
- [async/await](https://docs.python.org/3/library/asyncio-task.html#coroutines)

## 📞 Получение помощи

### Официальные каналы
- Railway Support: https://railway.app/support
- Telegram Bot API: https://t.me/botfather
- GitHub Issues: https://github.com/aiogram/aiogram/issues

### Сообщества
- **Telegram для Python разработчиков**: https://t.me/pythondevru (русскоязычный)
- **Stack Overflow**: https://stackoverflow.com (используйте теги: fastapi, telegram-bot, railway)
- **GitHub Discussions**: https://github.com/aiogram/aiogram/discussions

### Документация на русском
- [Python.org (RU)](https://python.readthedocs.io/ru/latest/)
- [FastAPI (RU переводы)](https://github.com/tiangolo/fastapi/discussions/9721)

## 🎯 Чек-лист перед началом

- [ ] Python 3.9+ установлен
- [ ] Git установлен
- [ ] GitHub аккаунт создан
- [ ] Railway аккаунт создан
- [ ] Telegram Bot Token получен от @BotFather
- [ ] Ваш Telegram ID известен (от @userinfobot)
- [ ] Код проекта готов (не содержит .env файлов)

## 📈 Масштабирование (для будущего)

### Кэширование
- [Redis на Railway](https://docs.railway.app/databases/redis)
- [FastAPI caching](https://github.com/long2ice/fastapi-cache2)

### Асинхронные задачи
- [Celery documentation](https://docs.celeryproject.io)
- [RQ (Redis Queue)](https://python-rq.org)

### Мониторинг
- [Sentry.io](https://sentry.io)
- [Prometheus](https://prometheus.io)
- [Grafana](https://grafana.com)

### Логирование
- [Python logging](https://docs.python.org/3/library/logging.html)
- [ELK Stack](https://www.elastic.co/what-is/elk-stack)

## 💡 Лучшие практики

1. **Безопасность:**
   - Никогда не коммичьте .env
   - Используйте сложные пароли/секреты
   - Регулярно обновляйте зависимости

2. **Код:**
   - Используйте type hints
   - Пишите тесты
   - Документируйте код

3. **Деплой:**
   - Тестируйте локально перед пушем
   - Используйте staging среду
   - Мониторьте логи в production

4. **Производительность:**
   - Кэшируйте часто запрашиваемые данные
   - Используйте connection pooling
   - Оптимизируйте запросы к БД

## 🚀 Следующие шаги после деплоя

1. ✅ Настроить мониторинг (Sentry)
2. ✅ Добавить логирование
3. ✅ Настроить автотесты (pytest)
4. ✅ Использовать CI/CD (GitHub Actions)
5. ✅ Добавить документацию API (Swagger из FastAPI)
6. ✅ Настроить backup БД
7. ✅ Добавить rate limiting
8. ✅ Реализовать кэширование

---

**Все ресурсы готовы! Начните с [`DEPLOYMENT_README.md`](./DEPLOYMENT_README.md)**

_Последнее обновление: 2026-02-16_

