# -*- coding: utf-8 -*-
"""
MitaHelper - Телеграм бот для управления группами
Основан на FallenRobot, переведён на русский и обновлён.

MIT License
"""

import logging
import os
import sys
import time

import telegram.ext as tg

# Время запуска бота
StartTime = time.time()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt", encoding='utf-8'), logging.StreamHandler()],
    level=logging.INFO,
)

# Уменьшаем уровень логов для сторонних библиотек
logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)

# Проверка версии Python (минимум 3.9)
if sys.version_info < (3, 9):
    LOGGER.error(
        "Требуется Python версии 3.9 или выше! Бот остановлен."
    )
    sys.exit(1)

# Загрузка конфигурации из переменных окружения или config.py
try:
    from MitaHelper.config import Config
except ImportError:
    LOGGER.error("Не найден файл конфигурации config.py")
    sys.exit(1)

# Основные настройки
TOKEN = Config.TOKEN
OWNER_ID = Config.OWNER_ID

# База данных
DATABASE_URL = Config.DATABASE_URL
MONGO_DB_URI = Config.MONGO_DB_URI

# Дополнительные настройки
SUPPORT_CHAT = getattr(Config, 'SUPPORT_CHAT', None)
EVENT_LOGS = getattr(Config, 'EVENT_LOGS', None)
START_IMG = getattr(Config, 'START_IMG', None)

# Количество воркеров
WORKERS = getattr(Config, 'WORKERS', 8)

# Пользователи с привилегиями
OWNER_ID = Config.OWNER_ID

# Sudo пользователи (администраторы бота)
try:
    SUDO_USERS = set(int(x) for x in getattr(Config, 'SUDO_USERS', []) if x)
except (ValueError, TypeError):
    SUDO_USERS = set()

# Разработчики бота
try:
    DEV_USERS = set(int(x) for x in getattr(Config, 'DEV_USERS', []) if x)
except (ValueError, TypeError):
    DEV_USERS = set()

# Привилегированные пользователи
try:
    SUPPORT_USERS = set(int(x) for x in getattr(Config, 'SUPPORT_USERS', []) if x)
except (ValueError, TypeError):
    SUPPORT_USERS = set()

# Белый список пользователей
try:
    WHITELIST_USERS = set(int(x) for x in getattr(Config, 'WHITELIST_USERS', []) if x)
except (ValueError, TypeError):
    WHITELIST_USERS = set()

# Добавляем владельца во все списки
SUDO_USERS.add(OWNER_ID)
DEV_USERS.add(OWNER_ID)

# Загрузка/исключение модулей
LOAD = getattr(Config, 'LOAD', [])
NO_LOAD = getattr(Config, 'NO_LOAD', [])

# Инициализация бота
LOGGER.info("Инициализация Telegram бота...")

# PTB Updater
updater = tg.Updater(TOKEN, workers=WORKERS, use_context=True)
dispatcher = updater.dispatcher

# Получаем информацию о боте
LOGGER.info("Получение информации о боте...")
try:
    BOT_ID = dispatcher.bot.id
    BOT_NAME = dispatcher.bot.first_name
    BOT_USERNAME = dispatcher.bot.username
except Exception as e:
    LOGGER.error(f"Ошибка получения информации о боте: {e}")
    BOT_ID = None
    BOT_NAME = "MitaHelper"
    BOT_USERNAME = None

# Списки пользователей как list для совместимости
SUDO_USERS = list(SUDO_USERS) + list(DEV_USERS)
DEV_USERS = list(DEV_USERS)
SUPPORT_USERS = list(SUPPORT_USERS)
WHITELIST_USERS = list(WHITELIST_USERS)

LOGGER.info("Инициализация MitaHelper завершена!")
