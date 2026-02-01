# -*- coding: utf-8 -*-
"""
Конфигурация MitaHelper
Заполните все необходимые поля перед запуском бота.
"""

import os
from pathlib import Path

# Загружаем переменные из .env файла
from dotenv import load_dotenv

# Ищем .env в корне проекта
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Основная конфигурация бота"""
    
    # ═══════════════════════════════════════════════════════════════
    #                     ОБЯЗАТЕЛЬНЫЕ НАСТРОЙКИ
    # ═══════════════════════════════════════════════════════════════
    
    # Токен бота - получить у @BotFather
    TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # ID владельца бота (ваш Telegram ID)
    OWNER_ID = int(os.environ.get("OWNER_ID", 0))
    
    # URL базы данных PostgreSQL
    # Получить бесплатно: https://elephantsql.com или https://railway.app
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    
    # URI MongoDB
    # Получить бесплатно: https://cloud.mongodb.com
    MONGO_DB_URI = os.environ.get("MONGO_DB_URI", "")
    
    # ═══════════════════════════════════════════════════════════════
    #                   ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
    # ═══════════════════════════════════════════════════════════════
    
    # Username группы поддержки (без @)
    SUPPORT_CHAT = os.environ.get("SUPPORT_CHAT", "")
    
    # ID канала для логов событий
    EVENT_LOGS = os.environ.get("EVENT_LOGS", None)
    
    # Изображение при запуске бота (URL)
    START_IMG = os.environ.get(
        "START_IMG", 
        "https://telegra.ph/file/40eb1ed850cdea274693e.jpg"
    )
    
    # Количество воркеров (потоков)
    WORKERS = int(os.environ.get("WORKERS", 8))
    
    # ═══════════════════════════════════════════════════════════════
    #                  ПРИВИЛЕГИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ
    # ═══════════════════════════════════════════════════════════════
    
    # Sudo пользователи (полный доступ) - список ID через пробел
    SUDO_USERS = [int(x) for x in os.environ.get("SUDO_USERS", "").split() if x]
    
    # Разработчики бота
    DEV_USERS = [int(x) for x in os.environ.get("DEV_USERS", "").split() if x]
    
    # Пользователи поддержки
    SUPPORT_USERS = [int(x) for x in os.environ.get("SUPPORT_USERS", "").split() if x]
    
    # Белый список пользователей
    WHITELIST_USERS = [int(x) for x in os.environ.get("WHITELIST_USERS", "").split() if x]
    
    # ═══════════════════════════════════════════════════════════════
    #                      НАСТРОЙКИ МОДУЛЕЙ
    # ═══════════════════════════════════════════════════════════════
    
    # Модули для загрузки (пустой список = все модули)
    LOAD = os.environ.get("LOAD", "").split()
    
    # Модули для исключения из загрузки
    NO_LOAD = os.environ.get("NO_LOAD", "").split()
    
    # Удалять команды после выполнения
    DEL_CMDS = bool(os.environ.get("DEL_CMDS", False))
    
    # Строгий глобальный бан
    STRICT_GBAN = bool(os.environ.get("STRICT_GBAN", True))
    
    # ═══════════════════════════════════════════════════════════════
    #                        API КЛЮЧИ
    # ═══════════════════════════════════════════════════════════════
    
    # API ключ для конвертации валют (https://www.alphavantage.co/support/#api-key)
    CASH_API_KEY = os.environ.get("CASH_API_KEY", "")
    
    # API ключ для времени
    TIME_API_KEY = os.environ.get("TIME_API_KEY", "")
    
    # Показывать фото профиля в /info
    INFOPIC = bool(os.environ.get("INFOPIC", True))
