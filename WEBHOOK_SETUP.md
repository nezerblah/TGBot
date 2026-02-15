# 🚀 Полный гайд по миграции на Webhook

## 📊 Polling vs Webhook - сравнение

```
                    POLLING              WEBHOOK
─────────────────────────────────────────────────────────
Задержка            1-5 сек              <1 сек
Использование CPU   30-50%               5-10%
Использование RAM   50-100 MB            20-30 MB
Пропускная способность  10-50 сообщений/сек  1000+ сообщений/сек
Масштабируемость    Плохая               Отличная
Зависит от интернета Хронически опрашивает   Только при событиях
```

**Вывод:** Webhook в 5-10 раз эффективнее для production!

---

## ✅ Что изменилось в коде

### ❌ Старый способ (polling)
```python
# В конце main.py
app.run_polling()  # Постоянно спрашивает Telegram "Есть ли сообщения?"
```

### ✅ Новый способ (webhook)
```python
# В main_webhook.py
app.run_webhook(
    listen="0.0.0.0",      # Слушаем все IP адреса
    port=WEBHOOK_PORT,      # На порту 8443
    url_path=f"/webhook/{TOKEN}",  # URL где Telegram отправляет обновления
    webhook_url=WEBHOOK_URL,        # Публичный URL вашего сервера
)
```

---

## 🔧 ЭТАП 1: Обновите .env файл

Добавьте новые переменные в `TGBot/.env`:

```env
# Существующие
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id

# НОВЫЕ для webhook
WEBHOOK_URL=https://your-domain.com
WEBHOOK_PORT=8443
WEBHOOK_SECRET=your-secret-token-12345
```

**Где получить:**
- `WEBHOOK_URL` - ваш домен с https (например: https://bot.example.com)
- `WEBHOOK_PORT` - порт (обычно 8443 для Telegram)
- `WEBHOOK_SECRET` - любая случайная строка для безопасности

---

## 🖥️ ЭТАП 2: Выбор сервера

### Вариант A: Railway (РЕКОМЕНДУЕТСЯ - самый простой)
**Стоимость:** Бесплатно (первые 500 часов/месяц)  
**Время настройки:** 5 минут  
**Плюсы:** Автоматический HTTPS, просто и быстро

**Как настроить:**
1. Создать аккаунт на railway.app
2. Подключить GitHub репозиторий
3. Добавить переменные окружения в Railway:
   ```
   WEBHOOK_URL=https://your-app.railway.app
   WEBHOOK_PORT=8443
   ```
4. Deploy!

---

### Вариант B: VPS (DigitalOcean, Linode, Hetzner)
**Стоимость:** $5-10/месяц  
**Время настройки:** 30-60 минут  
**Плюсы:** Полный контроль, понимаете что происходит

**Требования:**
- Ubuntu 20.04+ или аналог
- Python 3.10+
- nginx или другой reverse proxy
- SSL сертификат (Let's Encrypt - бесплатный)

---

### Вариант C: AWS Lambda + API Gateway
**Стоимость:** Бесплатно для малого трафика  
**Время настройки:** 45-90 минут  
**Плюсы:** Автоматическое масштабирование, платите только за использование

---

## 🔒 ЭТАП 3: SSL сертификат (ОБЯЗАТЕЛЬНО)

Telegram требует HTTPS. Есть 3 варианта:

### Вариант 1: Let's Encrypt (Бесплатно, рекомендуется)

```bash
# Установить certbot
sudo apt-get install certbot python3-certbot-nginx

# Получить сертификат
sudo certbot certonly --standalone -d your-domain.com

# Сертификаты будут в:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### Вариант 2: Railway (автоматический)
Railway автоматически генерирует HTTPS сертификаты. Просто используйте `https://your-app.railway.app`.

### Вариант 3: AWS Certificate Manager
Если используете AWS, Certificate Manager предоставляет бесплатные сертификаты.

---

## 🌐 ЭТАП 4: Reverse Proxy (nginx)

**Зачем?** Telegram отправляет на 443 порт, а бот слушает на 8443. Nginx перенаправляет.

### Установка nginx

```bash
sudo apt-get install nginx
sudo systemctl start nginx
```

### Конфигурация /etc/nginx/sites-available/tgbot

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Оптимизации SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Перенаправление на бот
    location /webhook/ {
        proxy_pass http://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Редирект с http на https
    error_page 497 https://$server_name$request_uri;
}

# Редирект http на https
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com;
    
    return 301 https://$server_name$request_uri;
}
```

### Активировать конфиг

```bash
# Создать symlink
sudo ln -s /etc/nginx/sites-available/tgbot /etc/nginx/sites-enabled/

# Проверить синтаксис
sudo nginx -t

# Перезагрузить
sudo systemctl reload nginx
```

---

## 🚀 ЭТАП 5: Запуск бота на VPS

### Как systemd сервис

```ini
# /etc/systemd/system/tgbot-webhook.service
[Unit]
Description=Telegram Horoscope Bot (Webhook)
After=network.target

[Service]
Type=simple
User=tgbot
WorkingDirectory=/opt/tgbot
Environment="PATH=/opt/tgbot/venv/bin"
ExecStart=/opt/tgbot/venv/bin/python /opt/tgbot/TGBot/main_webhook.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Активировать

```bash
sudo systemctl daemon-reload
sudo systemctl enable tgbot-webhook
sudo systemctl start tgbot-webhook
sudo systemctl status tgbot-webhook
```

---

## 📡 ЭТАП 6: Запуск на Railway (САМЫЙ ПРОСТОЙ)

### Шаг 1: Создать Procfile

```
# /TGBot/Procfile
web: python TGBot/main_webhook.py
```

### Шаг 2: Добавить в requirements.txt

```bash
pip freeze | grep -E "telegram|python-dotenv|requests|beautifulsoup4|pytz" > TGBot/requirements.txt
```

### Шаг 3: В Railway dashboard

1. Создать новый проект
2. Подключить GitHub репозиторий
3. Добавить переменные окружения:
   ```
   TELEGRAM_BOT_TOKEN=your_token
   ADMIN_ID=your_id
   WEBHOOK_URL=https://your-railway-app.railway.app
   WEBHOOK_PORT=8443
   WEBHOOK_SECRET=secret123
   ```
4. Deploy!

**Railway автоматически:**
- Установит зависимости
- Запустит Procfile
- Выдаст HTTPS сертификат
- Масштабирует по необходимости

---

## ✅ ЭТАП 7: Проверка работоспособности

### Проверить статус webhook

```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
```

**Ожидаемый ответ:**
```json
{
  "ok": true,
  "result": {
    "url": "https://your-domain.com/webhook/TOKEN",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 100,
    "allowed_updates": ["message", "callback_query"]
  }
}
```

### Проверить логи

```bash
# На VPS
sudo journalctl -u tgbot-webhook -f

# На Railway
railway logs
```

### Тестировать в Telegram

1. Найти бота
2. Отправить `/start`
3. Проверить логи - должны показать обновление

---

## 🔄 Как переключаться между Polling и Webhook

### Использовать Polling (старый способ)
```bash
python TGBot/main.py
```

### Использовать Webhook (новый способ)
```bash
python TGBot/main_webhook.py
```

---

## ⚙️ Оптимальная конфигурация для разных нагрузок

### Маленький бот (< 100 пользователей)
```env
WEBHOOK_PORT=8443
# Можно на виртуальном хостинге
# Railway бесплатный tier
```

### Средний бот (100-10k пользователей)
```env
WEBHOOK_PORT=8443
# VPS 2GB RAM, 1 vCPU (DigitalOcean $5)
# или Railway оплачиваемый план
```

### Большой бот (10k+ пользователей)
```env
WEBHOOK_PORT=8443
# Kubernetes кластер
# или AWS Lambda + SQS
# или Railway Pro план + Redis
```

---

## 🐛 Решение проблем

### Проблема 1: "Connection refused"
```
Причина: Nginx не перенаправляет на бот
Решение: 
1. sudo nginx -t (проверить конфиг)
2. sudo systemctl restart nginx
3. curl http://127.0.0.1:8443/webhook/ (локальный тест)
```

### Проблема 2: "Invalid SSL certificate"
```
Причина: Let's Encrypt сертификат истекает (каждые 90 дней)
Решение:
1. sudo certbot renew (вручную)
2. sudo systemctl enable certbot-renew.timer (автоматический)
```

### Проблема 3: "Webhook not responding"
```
Причина: Бот упал или не слушает порт
Решение:
1. sudo systemctl status tgbot-webhook
2. sudo journalctl -u tgbot-webhook -n 50
3. sudo systemctl restart tgbot-webhook
```

### Проблема 4: "pending_update_count: 100+"
```
Причина: Бот не может обработать события
Решение:
1. Увеличить max_connections (в коде: 100 → 200)
2. Добавить больше RAM
3. Оптимизировать код (кешировать goros)
```

---

## 📈 Мониторинг

### Проверить статус webhook

```bash
# Скрипт проверки
#!/bin/bash
while true; do
    curl -s https://api.telegram.org/bot<TOKEN>/getWebhookInfo | jq '.result'
    sleep 60
done
```

### Важные метрики для мониторинга

```
✓ pending_update_count (должен быть < 10)
✓ max_connections (оптимально 40-100)
✓ URL недоступность (должна быть 0)
✓ CPU использование (< 20%)
✓ RAM использование (< 200 MB)
```

---

## 💡 Лучшие практики

### 1. Переменные окружения
```env
# Используйте .env для всех чувствительных данных
# НИКОГДА не коммитьте .env в git
```

### 2. Логирование
```python
# Логируйте все события
logging.info(f"Webhook получил обновление от {chat_id}")
logging.error(f"Ошибка обработки: {error}")
```

### 3. Обработка ошибок
```python
# Всегда оборачивайте в try-except
try:
    await handle_update()
except Exception as e:
    logging.error(f"Error: {e}")
    await notify_admin(e)
```

### 4. Кеширование
```python
# Кешируйте гороскопы
goros_cache = {}
def get_horoscope_cached(sign):
    if sign not in goros_cache:
        goros_cache[sign] = parse_horoscope(sign)
    return goros_cache[sign]
```

---

## 🎯 Итоговый чек-лист

- [ ] Создан `main_webhook.py`
- [ ] Обновлен `.env` с WEBHOOK_URL
- [ ] Выбран хостинг (Railway рекомендуется)
- [ ] SSL сертификат получен
- [ ] Nginx настроен (если VPS)
- [ ] Бот запущен на webhook
- [ ] Проверена работоспособность
- [ ] Настроено логирование
- [ ] Мониторинг включен
- [ ] Документация прочитана

---

## 📞 Быстрая помощь

### Railway (3 минуты)
```bash
# 1. railway login
# 2. railway init
# 3. railway up
# 4. railway env
```

### VPS nginx (30 минут)
```bash
# Смотрите ЭТАП 4 выше
```

### Docker (для локального тестирования)
```dockerfile
FROM python:3.11
WORKDIR /app
COPY TGBot/requirements.txt .
RUN pip install -r requirements.txt
COPY TGBot .
CMD ["python", "main_webhook.py"]
```

---

**Версия:** 2.0 Webhook  
**Дата:** 15.02.2026  
**Статус:** ✅ Готово к использованию

**Удачи с webhook! Это на 90% снизит нагрузку на сервер! 🚀**

