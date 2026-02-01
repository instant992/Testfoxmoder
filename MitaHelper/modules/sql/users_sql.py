# -*- coding: utf-8 -*-
"""
SQL модуль для работы с пользователями
"""

from threading import RLock
from typing import List, Optional, Tuple

# В реальном боте здесь будет SQLAlchemy
# Пока используем простое хранилище в памяти

USERS_LOCK = RLock()
CHATS_LOCK = RLock()

# Хранилища
users = {}  # {user_id: {"username": ..., "first_name": ...}}
chats = {}  # {chat_id: {"title": ..., "username": ...}}


def ensure_user(user_id: int, username: str = None, first_name: str = None):
    """Добавляет/обновляет пользователя в базе"""
    with USERS_LOCK:
        if user_id not in users:
            users[user_id] = {}
        
        if username:
            users[user_id]["username"] = username
        if first_name:
            users[user_id]["first_name"] = first_name


def ensure_chat(chat_id: int, title: str = None, username: str = None):
    """Добавляет/обновляет чат в базе"""
    with CHATS_LOCK:
        if chat_id not in chats:
            chats[chat_id] = {}
        
        if title:
            chats[chat_id]["title"] = title
        if username:
            chats[chat_id]["username"] = username


def get_userid_by_name(username: str) -> List:
    """Получает ID пользователя по username"""
    username = username.lower()
    
    with USERS_LOCK:
        result = []
        for user_id, data in users.items():
            if data.get("username", "").lower() == username:
                result.append(type("User", (), {"user_id": user_id})())
        return result


def get_user(user_id: int) -> Optional[dict]:
    """Получает данные пользователя"""
    with USERS_LOCK:
        return users.get(user_id)


def get_chat(chat_id: int) -> Optional[dict]:
    """Получает данные чата"""
    with CHATS_LOCK:
        return chats.get(chat_id)


def get_all_users() -> List[dict]:
    """Получает всех пользователей"""
    with USERS_LOCK:
        return list(users.items())


def get_all_chats() -> List[dict]:
    """Получает все чаты"""
    with CHATS_LOCK:
        return list(chats.items())


def num_users() -> int:
    """Возвращает количество пользователей"""
    with USERS_LOCK:
        return len(users)


def num_chats() -> int:
    """Возвращает количество чатов"""
    with CHATS_LOCK:
        return len(chats)


def get_user_com_chats(user_id: int) -> List[int]:
    """Получает общие чаты с пользователем"""
    # В реальном боте это будет запрос к БД
    return []
