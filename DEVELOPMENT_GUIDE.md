# 🛠️ Гайд по добавлению новых функций

Этот документ поможет вам добавлять новые функции в бот, соблюдая установленные стандарты кода.

## 📋 Структура проекта

```
main.py
├── Импорты и конфигурация
├── Константы и переменные
├── Вспомогательные функции (_prefix)
├── Функции работы с БД
├── Функции парсинга
├── Команды бота (/command)
├── Обработчики callback (button)
└── Главная функция (main)
```

## 🎯 Принципы разработки

### 1. Используйте вспомогательные функции

❌ **Неправильно:**
```python
async def my_command(update: Update, context: object) -> None:
    try:
        await context.bot.send_message(chat_id, "Hello")
    except Exception as e:
        print(f"Error: {e}")
```

✅ **Правильно:**
```python
async def my_command(update: Update, context: object) -> None:
    success = await _safe_send_message(context, chat_id, "Hello")
    if not success:
        logging.error("Failed to send message")
```

### 2. Валидируйте входные данные

❌ **Неправильно:**
```python
def process_sign(sign_slug: str):
    # Прямое использование
    return zodiac_signs[sign_slug]  # Может упасть!
```

✅ **Правильно:**
```python
def process_sign(sign_slug: str):
    if not _validate_zodiac_slug(sign_slug):
        logging.warning(f"Invalid sign: {sign_slug}")
        return None
    return zodiac_signs[sign_slug]
```

### 3. Логируйте все операции

❌ **Неправильно:**
```python
def subscribe_user(user_id: int, sign: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO subscriptions ...")
```

✅ **Правильно:**
```python
def subscribe_user(user_id: int, sign: str) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO subscriptions ...")
        logging.info(f"User {user_id} subscribed to {sign}")
        return True
    except Exception as e:
        logging.error(f"Subscription failed: {e}")
        return False
```

### 4. Проверяйте размер сообщений

❌ **Неправильно:**
```python
message = f"{title}: {very_long_text}"
await context.bot.send_message(chat_id, message)
```

✅ **Правильно:**
```python
message = f"{title}: {very_long_text}"
message = _truncate_message(message)  # Автоматическая обрезка
await _safe_send_message(context, chat_id, message)
```

## 📝 Примеры добавления функций

### Пример 1: Добавление новой команды

```python
async def my_new_command(update: Update, context: object) -> None:
    """Описание команды."""
    user_id = update.effective_user.id if update.effective_user else update.message.chat_id
    
    try:
        # Ваша логика здесь
        result = some_operation(user_id)
        
        # Отправка результата
        await _safe_send_message(
            context, 
            user_id, 
            f"Result: {result}"
        )
        logging.info(f"Command executed for user {user_id}")
    except Exception as e:
        logging.error(f"Command failed: {e}")
        await _safe_send_message(context, user_id, "Error occurred 😔")
```

Затем добавьте в функцию `main()`:
```python
app.add_handler(CommandHandler("mynewcommand", my_new_command))
```

### Пример 2: Добавление обработки новой кнопки

```python
# В функции button() добавьте после проверки action:

if action == "my_action":
    if not _validate_zodiac_slug(sign_slug):
        await query.answer(text="Invalid sign", show_alert=True)
        return
    
    # Ваша логика
    result = process_something(sign_slug)
    
    # Отправка результата
    await query.answer(text="Success! ✅", show_alert=False)
    success = await _safe_send_message(
        context,
        query.message.chat_id,
        f"Result: {result}"
    )
    
    if success:
        await _safe_delete_message(context, query.message)
```

### Пример 3: Добавление функции работы с БД

```python
def get_user_data(user_id: int) -> dict:
    """Получить данные пользователя из БД."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = cur.fetchone()
            if not row:
                logging.warning(f"User {user_id} not found")
                return {}
            return {"id": row[0], "data": row[1]}
    except Exception as e:
        logging.error(f"Failed to get user data: {e}")
        return {}
```

### Пример 4: Добавление функции парсинга

```python
def parse_new_source(source_slug: str) -> tuple[str, dict]:
    """Получить данные из нового источника."""
    try:
        response = requests.get(f"https://api.example.com/{source_slug}", timeout=15)
        if response.status_code != 200:
            logging.warning(f"API returned {response.status_code}")
            return "Data unavailable 😔", {}
        
        data = response.json()
        # Парсинг данных
        text = data.get("content", "")
        metadata = data.get("meta", {})
        
        if len(text) < 100:
            logging.warning(f"Content too short for {source_slug}")
            return "Content too short 😔", metadata
        
        return text, metadata
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return "Connection error 😔", {}
    except Exception as e:
        logging.error(f"Parsing failed: {e}")
        return "Parsing error 😔", {}
```

## ✅ Чек-лист перед коммитом

Перед тем как закоммитить новую функцию:

- [ ] Функция имеет docstring с описанием
- [ ] Функция валидирует входные данные
- [ ] Все операции БД обернуты в try-except
- [ ] Используются функции `_safe_*()` для отправки/редактирования сообщений
- [ ] Применена функция `_truncate_message()` если отправляется длинный текст
- [ ] Добавлено логирование критических операций
- [ ] Функция возвращает статус успеха если это применимо
- [ ] Нет дублирования кода (извлечено в отдельную функцию если нужно)
- [ ] Тестировано вручную с разными входными данными

## 🐛 Отладка

### Как смотреть логи

Все логи выводятся в консоль в формате:
```
2026-02-15 14:30:45,123 - INFO - БД инициализирована
2026-02-15 14:30:46,456 - WARNING - Не удалось удалить сообщение: ...
2026-02-15 14:30:47,789 - ERROR - Ошибка отправки пользователю 123456: ...
```

### Как добавить свой лог

```python
logging.info("Information message")      # Информационные сообщения
logging.warning("Warning message")       # Предупреждения
logging.error("Error message")          # Ошибки
```

### Как тестировать функцию БД

```python
# Добавьте тестовый код в конце main.py (перед app.run_polling())
if __name__ == '__main__':
    init_db()
    
    # Тестирование
    subscribe_user(123456, 'aries')
    subs = get_user_subscriptions(123456)
    print(f"User subscriptions: {subs}")
    
    # Закомментируйте перед production
    # main()
```

## 🚀 Развертывание на production

1. **Убедитесь в наличии файла .env:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env с реальными значениями
   ```

2. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Тестируйте локально:**
   ```bash
   python main.py
   ```

4. **Развертывание на сервер:**
   ```bash
   # Используйте systemd, docker, или облачный сервис
   # Убедитесь что .env находится в правильном месте
   # Настройте логирование на файл если нужно
   ```

## 📞 Полезные ссылки

- [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Python logging docs](https://docs.python.org/3/library/logging.html)
- [SQLite docs](https://www.sqlite.org/docs.html)

---

**Happy coding! 🚀**

