# -*- coding: utf-8 -*-
"""
Файловая база данных для хранения данных бота
"""

import json
import os
from threading import RLock
from typing import Dict, List, Optional, Any

from MitaHelper import LOGGER

# Путь к файлу базы данных
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CHATS_FILE = os.path.join(DB_PATH, "chats.json")
USERS_FILE = os.path.join(DB_PATH, "users.json")
SETTINGS_FILE = os.path.join(DB_PATH, "settings.json")

# Блокировки для потокобезопасности
CHATS_LOCK = RLock()
USERS_LOCK = RLock()
SETTINGS_LOCK = RLock()

# Кеш в памяти
_chats_cache: Dict[int, dict] = {}
_users_cache: Dict[int, dict] = {}
_settings_cache: Dict[str, Any] = {}


def _ensure_db_dir():
    """Создаёт директорию для БД если её нет"""
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)


def _load_json(filepath: str) -> dict:
    """Загружает JSON файл"""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        LOGGER.warning(f"Ошибка загрузки {filepath}: {e}")
    return {}


def _save_json(filepath: str, data: dict):
    """Сохраняет данные в JSON файл"""
    _ensure_db_dir()
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.error(f"Ошибка сохранения {filepath}: {e}")


# ═══════════════════════════════════════════════════════════════
#                         ЧАТЫ
# ═══════════════════════════════════════════════════════════════

def load_chats():
    """Загружает чаты из файла"""
    global _chats_cache
    with CHATS_LOCK:
        data = _load_json(CHATS_FILE)
        # Конвертируем ключи обратно в int
        _chats_cache = {int(k): v for k, v in data.items()}
    LOGGER.info(f"Загружено {len(_chats_cache)} чатов из БД")


def save_chats():
    """Сохраняет чаты в файл"""
    with CHATS_LOCK:
        # Конвертируем ключи в str для JSON
        data = {str(k): v for k, v in _chats_cache.items()}
        _save_json(CHATS_FILE, data)


def add_chat(chat_id: int, title: str, added_by: int) -> bool:
    """Добавляет чат в базу"""
    with CHATS_LOCK:
        if chat_id in _chats_cache:
            # Обновляем название
            _chats_cache[chat_id]["title"] = title
        else:
            _chats_cache[chat_id] = {
                "title": title,
                "added_by": added_by,
                "admins": [added_by],  # Добавивший автоматически становится админом бота
            }
        save_chats()
        return True


def remove_chat(chat_id: int) -> bool:
    """Удаляет чат из базы"""
    with CHATS_LOCK:
        if chat_id in _chats_cache:
            del _chats_cache[chat_id]
            save_chats()
            return True
        return False


def get_chat(chat_id: int) -> Optional[dict]:
    """Получает информацию о чате"""
    with CHATS_LOCK:
        return _chats_cache.get(chat_id)


def get_all_chats() -> Dict[int, dict]:
    """Получает все чаты"""
    with CHATS_LOCK:
        return _chats_cache.copy()


def get_user_chats(user_id: int) -> List[dict]:
    """Получает чаты, где пользователь админ бота"""
    with CHATS_LOCK:
        result = []
        for chat_id, data in _chats_cache.items():
            if user_id in data.get("admins", []) or user_id == data.get("added_by"):
                result.append({"chat_id": chat_id, "title": data.get("title", str(chat_id))})
        return result


def is_chat_added(chat_id: int) -> bool:
    """Проверяет, добавлен ли чат"""
    with CHATS_LOCK:
        return chat_id in _chats_cache


def add_chat_admin(chat_id: int, user_id: int) -> bool:
    """Добавляет админа бота в чате"""
    with CHATS_LOCK:
        if chat_id in _chats_cache:
            if "admins" not in _chats_cache[chat_id]:
                _chats_cache[chat_id]["admins"] = []
            if user_id not in _chats_cache[chat_id]["admins"]:
                _chats_cache[chat_id]["admins"].append(user_id)
                save_chats()
            return True
        return False


def remove_chat_admin(chat_id: int, user_id: int) -> bool:
    """Удаляет админа бота в чате"""
    with CHATS_LOCK:
        if chat_id in _chats_cache:
            if user_id in _chats_cache[chat_id].get("admins", []):
                _chats_cache[chat_id]["admins"].remove(user_id)
                save_chats()
                return True
        return False


def get_chat_admins(chat_id: int) -> List[int]:
    """Получает список админов бота в чате"""
    with CHATS_LOCK:
        if chat_id in _chats_cache:
            return _chats_cache[chat_id].get("admins", []).copy()
        return []


def is_chat_admin(chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь админом бота в чате"""
    with CHATS_LOCK:
        if chat_id in _chats_cache:
            return user_id in _chats_cache[chat_id].get("admins", [])
        return False


# ═══════════════════════════════════════════════════════════════
#                         ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════

def load_users():
    """Загружает пользователей из файла"""
    global _users_cache
    with USERS_LOCK:
        data = _load_json(USERS_FILE)
        _users_cache = {int(k): v for k, v in data.items()}
    LOGGER.info(f"Загружено {len(_users_cache)} пользователей из БД")


def save_users():
    """Сохраняет пользователей в файл"""
    with USERS_LOCK:
        data = {str(k): v for k, v in _users_cache.items()}
        _save_json(USERS_FILE, data)


def ensure_user(user_id: int, username: str = None, first_name: str = None):
    """Добавляет/обновляет пользователя"""
    with USERS_LOCK:
        if user_id not in _users_cache:
            _users_cache[user_id] = {}
        
        if username:
            _users_cache[user_id]["username"] = username.lower()
        if first_name:
            _users_cache[user_id]["first_name"] = first_name
        
        # Сохраняем каждые N пользователей или при первом добавлении
        if len(_users_cache) % 100 == 0:
            save_users()


def get_user_by_username(username: str) -> Optional[int]:
    """Получает ID пользователя по username"""
    username = username.lower().lstrip("@")
    with USERS_LOCK:
        for user_id, data in _users_cache.items():
            if data.get("username", "").lower() == username:
                return user_id
    return None


def get_user(user_id: int) -> Optional[dict]:
    """Получает данные пользователя"""
    with USERS_LOCK:
        return _users_cache.get(user_id)


# ═══════════════════════════════════════════════════════════════
#                         НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════

# Пути к файлам настроек модулей
WELCOME_SETTINGS_FILE = os.path.join(DB_PATH, "welcome_settings.json")
CAPTCHA_SETTINGS_FILE = os.path.join(DB_PATH, "captcha_settings.json")
RULES_FILE = os.path.join(DB_PATH, "rules.json")
NOTES_FILE = os.path.join(DB_PATH, "notes.json")
FILTERS_FILE = os.path.join(DB_PATH, "filters.json")
LOGS_SETTINGS_FILE = os.path.join(DB_PATH, "logs_settings.json")
MEDIA_FILTERS_FILE = os.path.join(DB_PATH, "media_filters.json")
CAS_SETTINGS_FILE = os.path.join(DB_PATH, "cas_settings.json")
ANTIFLOOD_FILE = os.path.join(DB_PATH, "antiflood.json")
WARNS_FILE = os.path.join(DB_PATH, "warns.json")
BLACKLIST_FILE = os.path.join(DB_PATH, "blacklist.json")
USER_SETTINGS_FILE = os.path.join(DB_PATH, "user_settings.json")
MULTI_FILTERS_FILE = os.path.join(DB_PATH, "multi_filters.json")
ANTICHANNEL_FILE = os.path.join(DB_PATH, "antichannel.json")


def load_settings():
    """Загружает настройки из файла"""
    global _settings_cache
    with SETTINGS_LOCK:
        _settings_cache = _load_json(SETTINGS_FILE)
    LOGGER.info("Настройки загружены из БД")


def save_settings():
    """Сохраняет настройки в файл"""
    with SETTINGS_LOCK:
        _save_json(SETTINGS_FILE, _settings_cache)


def get_setting(chat_id: int, key: str, default=None):
    """Получает настройку чата"""
    with SETTINGS_LOCK:
        chat_key = str(chat_id)
        if chat_key in _settings_cache:
            return _settings_cache[chat_key].get(key, default)
        return default


def set_setting(chat_id: int, key: str, value):
    """Устанавливает настройку чата"""
    with SETTINGS_LOCK:
        chat_key = str(chat_id)
        if chat_key not in _settings_cache:
            _settings_cache[chat_key] = {}
        _settings_cache[chat_key][key] = value
        save_settings()


def get_all_chat_settings(chat_id: int) -> dict:
    """Получает все настройки чата"""
    with SETTINGS_LOCK:
        return _settings_cache.get(str(chat_id), {}).copy()


# ═══════════════════════════════════════════════════════════════
#                    ФУНКЦИИ ДЛЯ МОДУЛЕЙ
# ═══════════════════════════════════════════════════════════════

def load_module_settings(filepath: str) -> dict:
    """Загружает настройки модуля из файла"""
    data = _load_json(filepath)
    # Конвертируем ключи в int где возможно
    result = {}
    for k, v in data.items():
        try:
            result[int(k)] = v
        except ValueError:
            result[k] = v
    return result


def save_module_settings(filepath: str, data: dict):
    """Сохраняет настройки модуля в файл"""
    # Конвертируем ключи в str для JSON
    json_data = {str(k): v for k, v in data.items()}
    _save_json(filepath, json_data)


# Функции для welcome
def load_welcome_settings() -> dict:
    return load_module_settings(WELCOME_SETTINGS_FILE)

def save_welcome_settings(data: dict):
    save_module_settings(WELCOME_SETTINGS_FILE, data)


# Функции для captcha
def load_captcha_settings() -> dict:
    return load_module_settings(CAPTCHA_SETTINGS_FILE)

def save_captcha_settings_db(data: dict):
    save_module_settings(CAPTCHA_SETTINGS_FILE, data)


# Функции для rules
def load_rules_settings() -> dict:
    return load_module_settings(RULES_FILE)

def save_rules_settings(data: dict):
    save_module_settings(RULES_FILE, data)


# Функции для notes
def load_notes_settings() -> dict:
    return load_module_settings(NOTES_FILE)

def save_notes_settings(data: dict):
    save_module_settings(NOTES_FILE, data)


# Функции для filters
def load_filters_settings() -> dict:
    return load_module_settings(FILTERS_FILE)

def save_filters_settings(data: dict):
    save_module_settings(FILTERS_FILE, data)


# Функции для logs
def load_logs_settings() -> dict:
    return load_module_settings(LOGS_SETTINGS_FILE)

def save_logs_settings(data: dict):
    save_module_settings(LOGS_SETTINGS_FILE, data)


# Функции для media_filters
def load_media_filters_settings() -> dict:
    return load_module_settings(MEDIA_FILTERS_FILE)

def save_media_filters_settings(data: dict):
    save_module_settings(MEDIA_FILTERS_FILE, data)


# Функции для CAS
def load_cas_settings() -> dict:
    return load_module_settings(CAS_SETTINGS_FILE)

def save_cas_settings_db(data: dict):
    save_module_settings(CAS_SETTINGS_FILE, data)


# Функции для antiflood
def load_antiflood_settings() -> dict:
    return load_module_settings(ANTIFLOOD_FILE)

def save_antiflood_settings(data: dict):
    save_module_settings(ANTIFLOOD_FILE, data)


# Функции для warns
def load_warns_settings() -> dict:
    return load_module_settings(WARNS_FILE)

def save_warns_settings(data: dict):
    save_module_settings(WARNS_FILE, data)


# Функции для blacklist
def load_blacklist_settings() -> dict:
    return load_module_settings(BLACKLIST_FILE)

def save_blacklist_settings(data: dict):
    save_module_settings(BLACKLIST_FILE, data)


# Функции для multi_filters (мультифильтры)
def load_multi_filters_settings() -> dict:
    return load_module_settings(MULTI_FILTERS_FILE)

def save_multi_filters_settings(data: dict):
    save_module_settings(MULTI_FILTERS_FILE, data)


# Функции для antichannel (антиканал)
def load_antichannel_settings() -> dict:
    return load_module_settings(ANTICHANNEL_FILE)

def save_antichannel_settings(data: dict):
    save_module_settings(ANTICHANNEL_FILE, data)

def get_antichannel_settings(chat_id: int) -> dict:
    """Получает настройки антиканала для чата"""
    data = load_antichannel_settings()
    return data.get(chat_id, {"enabled": False})

def set_antichannel_settings(chat_id: int, settings: dict):
    """Сохраняет настройки антиканала для чата"""
    data = load_antichannel_settings()
    data[chat_id] = settings
    save_antichannel_settings(data)

def toggle_antichannel(chat_id: int) -> bool:
    """Переключает антиканал и возвращает новое состояние"""
    settings = get_antichannel_settings(chat_id)
    new_state = not settings.get("enabled", False)
    settings["enabled"] = new_state
    set_antichannel_settings(chat_id, settings)
    return new_state

def is_antichannel_enabled(chat_id: int) -> bool:
    """Проверяет, включён ли антиканал"""
    settings = get_antichannel_settings(chat_id)
    return settings.get("enabled", False)


# ═══════════════════════════════════════════════════════════════
#                    ПОЛЬЗОВАТЕЛЬСКИЕ НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════

_user_settings_cache: Dict[int, dict] = {}
USER_SETTINGS_LOCK = RLock()

def load_user_settings() -> dict:
    """Загружает пользовательские настройки"""
    global _user_settings_cache
    with USER_SETTINGS_LOCK:
        data = _load_json(USER_SETTINGS_FILE)
        _user_settings_cache = {int(k): v for k, v in data.items()}
    return _user_settings_cache

def save_user_settings_db():
    """Сохраняет пользовательские настройки"""
    with USER_SETTINGS_LOCK:
        data = {str(k): v for k, v in _user_settings_cache.items()}
        _save_json(USER_SETTINGS_FILE, data)

def get_user_setting(user_id: int, key: str, default=None):
    """Получает настройку пользователя"""
    with USER_SETTINGS_LOCK:
        if user_id not in _user_settings_cache:
            return default
        return _user_settings_cache[user_id].get(key, default)

def set_user_setting(user_id: int, key: str, value):
    """Устанавливает настройку пользователя"""
    with USER_SETTINGS_LOCK:
        if user_id not in _user_settings_cache:
            _user_settings_cache[user_id] = {}
        _user_settings_cache[user_id][key] = value
        save_user_settings_db()

def get_delete_mod_commands(user_id: int) -> bool:
    """Проверяет, нужно ли удалять команды модерации для пользователя"""
    return get_user_setting(user_id, "delete_mod_commands", False)

def set_delete_mod_commands(user_id: int, enabled: bool):
    """Устанавливает удаление команд модерации для пользователя"""
    set_user_setting(user_id, "delete_mod_commands", enabled)


# ═══════════════════════════════════════════════════════════════
#                      ПОЛНЫЙ СБРОС ДАННЫХ
# ═══════════════════════════════════════════════════════════════

def reset_all_data():
    """
    Полностью сбрасывает все данные бота.
    Удаляет все JSON файлы из папки data/.
    НЕ затрагивает .env файл.
    """
    global _chats_cache, _users_cache, _settings_cache, _user_settings_cache
    
    import glob
    
    # Очищаем кеши
    with CHATS_LOCK:
        _chats_cache = {}
    with USERS_LOCK:
        _users_cache = {}
    with SETTINGS_LOCK:
        _settings_cache = {}
    with USER_SETTINGS_LOCK:
        _user_settings_cache = {}
    
    # Удаляем все JSON файлы в папке data
    deleted_files = []
    try:
        if os.path.exists(DB_PATH):
            json_files = glob.glob(os.path.join(DB_PATH, "*.json"))
            for filepath in json_files:
                try:
                    os.remove(filepath)
                    deleted_files.append(os.path.basename(filepath))
                    LOGGER.info(f"Удалён файл: {filepath}")
                except Exception as e:
                    LOGGER.error(f"Ошибка удаления {filepath}: {e}")
    except Exception as e:
        LOGGER.error(f"Ошибка при сбросе данных: {e}")
        return False, str(e)
    
    LOGGER.warning("ПОЛНЫЙ СБРОС ДАННЫХ ВЫПОЛНЕН!")
    return True, deleted_files


# ═══════════════════════════════════════════════════════════════
#                         ИНИЦИАЛИЗАЦИЯ
# ═══════════════════════════════════════════════════════════════

def init_database():
    """Инициализирует базу данных"""
    _ensure_db_dir()
    load_chats()
    load_users()
    load_settings()
    load_user_settings()
    LOGGER.info("База данных инициализирована")


# Автоматическая инициализация при импорте
init_database()
