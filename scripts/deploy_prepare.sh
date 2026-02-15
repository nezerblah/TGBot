#!/bin/bash

# Автоматизированный скрипт для подготовки деплоя на Railway
# Использование: ./deploy_prepare.sh

set -e  # Выход при первой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Логирование
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Подготовка проекта к деплою на Railway.com         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Проверка системных требований
log_info "Проверка системных требований..."

# Проверка Git
if ! command -v git &> /dev/null; then
    log_error "Git не установлен. Пожалуйста, установите Git."
    exit 1
fi
log_success "Git установлен"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    log_error "Python3 не установлен. Пожалуйста, установите Python 3.9+"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_success "Python $PYTHON_VERSION установлен"

echo ""

# 2. Проверка структуры проекта
log_info "Проверка структуры проекта..."

REQUIRED_FILES=(
    "requirements.txt"
    "Procfile"
    "app/main.py"
    "app/bot.py"
    "app/db.py"
    "app/webhook.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_success "Найден: $file"
    else
        log_error "Не найден: $file"
        exit 1
    fi
done

echo ""

# 3. Проверка .env.example
log_info "Проверка .env.example..."
if [ -f ".env.example" ]; then
    log_success ".env.example найден"
else
    log_warn ".env.example не найден. Создание шаблона..."
    cat > .env.example << 'EOF'
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_ID=your_admin_telegram_id_here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/tg_bot

# Webhook Configuration
WEBHOOK_SECRET=your_webhook_secret_here
WEBHOOK_URL=https://your-railway-app.up.railway.app/webhook/secret

# Environment
ENVIRONMENT=production
EOF
    log_success ".env.example создан"
fi

echo ""

# 4. Проверка .gitignore
log_info "Проверка .gitignore..."
if [ -f ".gitignore" ]; then
    if grep -q "\.env" .gitignore; then
        log_success ".env в .gitignore"
    else
        log_warn ".env не в .gitignore. Добавляю..."
        echo ".env" >> .gitignore
        log_success "Добавлено .env в .gitignore"
    fi
else
    log_warn ".gitignore не найден. Создание..."
    cat > .gitignore << 'EOF'
# Environment
.env
.env.local

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv
venv/

# Database
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/
*.swp

# Testing
.pytest_cache/
.coverage
EOF
    log_success ".gitignore создан"
fi

echo ""

# 5. Проверка Git репозитория
log_info "Проверка Git репозитория..."

if [ -d ".git" ]; then
    log_success "Git репозиторий инициализирован"

    # Проверка ремоута
    if git remote get-url origin &> /dev/null; then
        REMOTE=$(git remote get-url origin)
        log_success "Удаленный репозиторий: $REMOTE"
    else
        log_warn "Удаленный репозиторий не установлен"
        log_info "Установите репозиторий командой:"
        echo "  git remote add origin https://github.com/YOUR_USERNAME/TGBot.git"
    fi
else
    log_info "Инициализация Git репозитория..."
    git init
    git add .
    git commit -m "Initial commit: Telegram Horoscopes Bot"
    log_success "Git репозиторий инициализирован"

    log_warn "Необходимо добавить удаленный репозиторий:"
    log_info "Используйте команду:"
    echo "  git remote add origin https://github.com/YOUR_USERNAME/TGBot.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
fi

echo ""

# 6. Проверка зависимостей
log_info "Проверка requirements.txt..."

REQUIRED_PACKAGES=(
    "fastapi"
    "uvicorn"
    "aiogram"
    "SQLAlchemy"
    "python-dotenv"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if grep -q "$package" requirements.txt; then
        log_success "Найден: $package"
    else
        log_warn "Не найден: $package"
    fi
done

echo ""

# 7. Проверка Railway специфичных файлов
log_info "Проверка Railway конфигурации..."

if [ -f "Procfile" ]; then
    if grep -q "uvicorn" Procfile; then
        log_success "Procfile правильно настроен"
    else
        log_warn "Procfile может быть не оптимален для Railway"
    fi
else
    log_error "Procfile не найден"
fi

if [ -f "runtime.txt" ]; then
    log_success "runtime.txt найден"
else
    log_info "Создание runtime.txt..."
    echo "python-3.11.7" > runtime.txt
    log_success "runtime.txt создан"
fi

if [ -f "railway.toml" ]; then
    log_success "railway.toml найден"
else
    log_info "Создание railway.toml..."
    cat > railway.toml << 'EOF'
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
EOF
    log_success "railway.toml создан"
fi

echo ""

# 8. Итоговый отчет
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Статус подготовки                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

log_success "✅ Все проверки пройдены!"
echo ""

log_info "Следующие шаги:"
echo "  1. Загрузить изменения на GitHub:"
echo "     git add ."
echo "     git commit -m 'Prepare for Railway deployment'"
echo "     git push"
echo ""
echo "  2. Перейти на https://railway.app"
echo "  3. Создать новый проект → Deploy from GitHub"
echo "  4. Выбрать репозиторий TGBot"
echo ""
echo "  5. Добавить переменные окружения:"
echo "     - BOT_TOKEN"
echo "     - ADMIN_ID"
echo "     - WEBHOOK_SECRET"
echo "     - ENVIRONMENT"
echo ""
echo "  6. Добавить PostgreSQL сервис"
echo ""
echo "  7. Когда приложение развернется, установить вебхук:"
echo "     railway run python scripts/set_webhook.py"
echo ""
echo "  📖 Подробную инструкцию смотрите в DEPLOYMENT_CHECKLIST.md"
echo ""

# 9. Вывести информацию о версиях
echo -e "${BLUE}Информация о системе:${NC}"
echo "  OS: $(uname -s)"
echo "  Python: $PYTHON_VERSION"
echo "  Git: $(git --version | cut -d ' ' -f 3)"
echo ""

log_success "Подготовка завершена! 🚀"

