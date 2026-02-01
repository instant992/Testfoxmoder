#!/bin/bash

# ═══════════════════════════════════════════════════════════════
#                    MitaHelper - Quick Docker Commands
# ═══════════════════════════════════════════════════════════════

# Определяем команду compose
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

case "$1" in
    start)
        echo "🚀 Запуск бота..."
        $COMPOSE up -d
        echo "✅ Бот запущен!"
        ;;
    stop)
        echo "⏹️ Остановка бота..."
        $COMPOSE down
        echo "✅ Бот остановлен!"
        ;;
    restart)
        echo "🔄 Перезапуск бота..."
        $COMPOSE restart
        echo "✅ Бот перезапущен!"
        ;;
    logs)
        echo "📋 Логи бота (Ctrl+C для выхода):"
        $COMPOSE logs -f
        ;;
    rebuild)
        echo "🔧 Пересборка бота..."
        $COMPOSE down
        $COMPOSE build --no-cache
        $COMPOSE up -d
        echo "✅ Бот пересобран и запущен!"
        ;;
    status)
        echo "📊 Статус бота:"
        $COMPOSE ps
        ;;
    shell)
        echo "🐚 Вход в контейнер..."
        docker exec -it mitahelper_bot /bin/bash
        ;;
    update)
        echo "⬆️ Обновление бота..."
        git pull 2>/dev/null || echo "Git не найден, пропускаю pull"
        $COMPOSE down
        $COMPOSE build --no-cache
        $COMPOSE up -d
        echo "✅ Бот обновлён и запущен!"
        ;;
    *)
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║              🤖 MitaHelper Docker Manager                  ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Использование: ./docker-manage.sh [команда]"
        echo ""
        echo "Команды:"
        echo "  start    - Запустить бота"
        echo "  stop     - Остановить бота"
        echo "  restart  - Перезапустить бота"
        echo "  logs     - Показать логи"
        echo "  rebuild  - Пересобрать и запустить"
        echo "  status   - Показать статус"
        echo "  shell    - Войти в контейнер"
        echo "  update   - Обновить из git и перезапустить"
        echo ""
        ;;
esac
