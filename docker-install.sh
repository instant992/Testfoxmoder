#!/bin/bash

# ═══════════════════════════════════════════════════════════════
#                    MitaHelper - Auto Install & Run
#                    Автоматическая установка в Docker
# ═══════════════════════════════════════════════════════════════

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║               🤖 MitaHelper Bot Installer                  ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Функция для вывода статуса
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# ═══════════════════════════════════════════════════════════════
#                      ПРОВЕРКА DOCKER
# ═══════════════════════════════════════════════════════════════

echo ""
print_info "Проверка Docker..."

if ! command -v docker &> /dev/null; then
    print_warning "Docker не установлен. Устанавливаю..."
    
    # Определяем ОС
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        print_error "Не удалось определить ОС"
        exit 1
    fi
    
    case $OS in
        ubuntu|debian)
            print_info "Обнаружена система: $OS"
            
            # Удаляем старые версии
            sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
            
            # Устанавливаем зависимости
            sudo apt-get update
            sudo apt-get install -y \
                ca-certificates \
                curl \
                gnupg \
                lsb-release
            
            # Добавляем GPG ключ Docker
            sudo mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            
            # Добавляем репозиторий
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
              $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # Устанавливаем Docker
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            
            # Добавляем пользователя в группу docker
            sudo usermod -aG docker $USER
            
            print_status "Docker установлен!"
            ;;
        centos|rhel|fedora)
            print_info "Обнаружена система: $OS"
            
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo systemctl start docker
            sudo systemctl enable docker
            sudo usermod -aG docker $USER
            
            print_status "Docker установлен!"
            ;;
        *)
            print_error "Неподдерживаемая ОС: $OS"
            print_info "Установите Docker вручную: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac
else
    print_status "Docker уже установлен"
fi

# Проверяем Docker Compose
if ! docker compose version &> /dev/null; then
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose не найден. Устанавливаю..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        print_status "Docker Compose установлен!"
    fi
fi

# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКА .ENV
# ═══════════════════════════════════════════════════════════════

echo ""
print_info "Проверка конфигурации..."

if [ ! -f .env ]; then
    print_warning "Файл .env не найден. Создаю..."
    
    echo ""
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║              Настройка бота                                ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Запрашиваем токен
    read -p "🔑 Введите токен бота (от @BotFather): " BOT_TOKEN
    
    if [ -z "$BOT_TOKEN" ]; then
        print_error "Токен не может быть пустым!"
        exit 1
    fi
    
    # Запрашиваем Owner ID
    read -p "👤 Введите ваш Telegram ID (Owner ID): " OWNER_ID
    
    if [ -z "$OWNER_ID" ]; then
        print_error "Owner ID не может быть пустым!"
        exit 1
    fi
    
    # Запрашиваем имя бота
    read -p "📝 Введите имя бота [MitaHelper]: " BOT_NAME
    BOT_NAME=${BOT_NAME:-MitaHelper}
    
    # Запрашиваем username бота
    read -p "🏷️ Введите username бота (без @): " BOT_USERNAME
    
    if [ -z "$BOT_USERNAME" ]; then
        print_error "Username бота не может быть пустым!"
        exit 1
    fi
    
    # Создаём .env файл
    cat > .env << EOF
# ═══════════════════════════════════════════════════════════════
#                    MitaHelper - Конфигурация
# ═══════════════════════════════════════════════════════════════

# Токен бота от @BotFather
BOT_TOKEN=${BOT_TOKEN}

# Ваш Telegram ID (владелец бота)
OWNER_ID=${OWNER_ID}

# Имя бота
BOT_NAME=${BOT_NAME}

# Username бота (без @)
BOT_USERNAME=${BOT_USERNAME}

# Sudo пользователи (ID через пробел)
SUDO_USERS=

# Dev пользователи (ID через пробел)
DEV_USERS=

# Чат поддержки (username без @)
SUPPORT_CHAT=
EOF
    
    print_status "Файл .env создан!"
else
    print_status "Файл .env найден"
fi

# ═══════════════════════════════════════════════════════════════
#                      СОЗДАНИЕ ДИРЕКТОРИЙ
# ═══════════════════════════════════════════════════════════════

echo ""
print_info "Создание директорий..."

mkdir -p MitaHelper/data
print_status "Директория data создана"

# ═══════════════════════════════════════════════════════════════
#                      СБОРКА И ЗАПУСК
# ═══════════════════════════════════════════════════════════════

echo ""
print_info "Сборка Docker образа..."

# Используем docker compose (новая версия) или docker-compose (старая)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Останавливаем если уже запущен
$COMPOSE_CMD down 2>/dev/null || true

# Собираем образ
$COMPOSE_CMD build --no-cache

print_status "Docker образ собран!"

echo ""
print_info "Запуск бота..."

# Запускаем в фоне
$COMPOSE_CMD up -d

print_status "Бот запущен!"

# ═══════════════════════════════════════════════════════════════
#                      ГОТОВО
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║           ✅ MitaHelper успешно установлен!                ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BLUE}Полезные команды:${NC}"
echo ""
echo "  📋 Просмотр логов:"
echo "     $COMPOSE_CMD logs -f"
echo ""
echo "  🔄 Перезапуск бота:"
echo "     $COMPOSE_CMD restart"
echo ""
echo "  ⏹️ Остановка бота:"
echo "     $COMPOSE_CMD down"
echo ""
echo "  🔧 Пересборка после изменений:"
echo "     $COMPOSE_CMD up -d --build"
echo ""
echo "  📊 Статус контейнера:"
echo "     $COMPOSE_CMD ps"
echo ""

# Показываем логи
echo -e "${YELLOW}Показываю логи бота (Ctrl+C для выхода):${NC}"
echo ""
sleep 2
$COMPOSE_CMD logs -f
