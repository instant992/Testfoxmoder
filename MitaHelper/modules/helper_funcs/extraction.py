# -*- coding: utf-8 -*-
"""
Функции для извлечения пользователей и текста
"""

from typing import List, Optional, Tuple

from telegram import Message, MessageEntity
from telegram.error import BadRequest

from MitaHelper import LOGGER


def id_from_reply(message: Message) -> Optional[int]:
    """Получает ID пользователя из ответа на сообщение"""
    prev_message = message.reply_to_message
    if not prev_message:
        return None
    
    user_id = prev_message.from_user.id
    return user_id


def extract_user(message: Message, args: List[str]) -> Optional[int]:
    """Извлекает ID пользователя из сообщения или аргументов"""
    return extract_user_and_text(message, args)[0]


def extract_user_and_text(
    message: Message, args: List[str]
) -> Tuple[Optional[int], Optional[str]]:
    """Извлекает ID пользователя и текст из сообщения"""
    
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    # Если есть ответ на сообщение
    if len(split_text) < 2:
        text = ""
    else:
        text = split_text[1]

    if prev_message:
        user = prev_message.from_user
        if not user:
            # Сообщение от канала
            if prev_message.sender_chat:
                return prev_message.sender_chat.id, text
            return None, None
        return user.id, text

    # Если нет ответа, ищем в аргументах
    if args:
        if args[0].isdigit():
            return int(args[0]), " ".join(args[1:]) if len(args) > 1 else ""
        
        if args[0].startswith("@"):
            user = args[0]
            user_id = get_user_id(user)
            if not user_id:
                message.reply_text(
                    f"❌ Не могу найти пользователя {user}. "
                    "Возможно, он ещё не общался со мной."
                )
                return None, None
            return user_id, " ".join(args[1:]) if len(args) > 1 else ""

        # Пробуем найти упоминание
        if message.entities:
            for ent in message.entities:
                if ent.type == MessageEntity.TEXT_MENTION:
                    return ent.user.id, message.text[ent.offset + ent.length:].strip()
                elif ent.type == MessageEntity.MENTION:
                    user = message.text[ent.offset:ent.offset + ent.length]
                    user_id = get_user_id(user)
                    if not user_id:
                        message.reply_text(
                            f"❌ Не могу найти пользователя {user}."
                        )
                        return None, None
                    return user_id, message.text[ent.offset + ent.length:].strip()

    return None, None


def get_user_id(username: str) -> Optional[int]:
    """Получает ID пользователя по username"""
    from MitaHelper.modules.sql.users_sql import get_userid_by_name
    
    username = username.lstrip("@")
    
    if username.isdigit():
        return int(username)
    
    users = get_userid_by_name(username)
    if users:
        return users[0].user_id
    
    return None


def extract_user_for_moderation(message: Message, args: List[str], bot=None, chat_id: int = None) -> Optional[int]:
    """Извлекает ID пользователя для команд модерации (работает с @username)"""
    
    prev_message = message.reply_to_message
    
    # Если есть ответ на сообщение
    if prev_message:
        user = prev_message.from_user
        if user:
            return user.id
        if prev_message.sender_chat:
            return prev_message.sender_chat.id
        return None
    
    # Если нет ответа, ищем в аргументах
    if args:
        # Если это число - ID
        if args[0].isdigit():
            return int(args[0])
        
        # Если это @username - ищем в базе
        if args[0].startswith("@"):
            user_id = get_user_id(args[0])
            if user_id:
                return user_id
            # Пользователь не найден в базе
            return None
        
        # Пробуем найти упоминание в entities
        if message.entities:
            for ent in message.entities:
                if ent.type == "text_mention":
                    return ent.user.id
                elif ent.type == "mention":
                    username = message.text[ent.offset:ent.offset + ent.length]
                    return get_user_id(username)
    
    return None


def extract_user_and_text_for_moderation(
    message: Message, args: List[str], bot=None, chat_id: int = None
) -> Tuple[Optional[int], Optional[str]]:
    """Извлекает ID пользователя и текст для команд модерации (работает с @username)"""
    
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1) if message.text else []

    # Текст после команды
    if len(split_text) < 2:
        text = ""
    else:
        text = split_text[1]

    # Если есть ответ на сообщение
    if prev_message:
        user = prev_message.from_user
        if user:
            return user.id, text
        if prev_message.sender_chat:
            return prev_message.sender_chat.id, text
        return None, None

    # Если нет ответа, ищем в аргументах
    if args:
        # Если это число - ID
        if args[0].isdigit():
            return int(args[0]), " ".join(args[1:]) if len(args) > 1 else ""
        
        # Если это @username - ищем в базе
        if args[0].startswith("@"):
            user_id = get_user_id(args[0])
            if user_id:
                return user_id, " ".join(args[1:]) if len(args) > 1 else ""
            return None, None
        
        # Пробуем найти упоминание в entities
        if message.entities:
            for ent in message.entities:
                if ent.type == "text_mention":
                    return ent.user.id, message.text[ent.offset + ent.length:].strip()
                elif ent.type == "mention":
                    username = message.text[ent.offset:ent.offset + ent.length]
                    user_id = get_user_id(username)
                    if user_id:
                        return user_id, message.text[ent.offset + ent.length:].strip()

    return None, None


def extract_text(message: Message) -> str:
    """Извлекает текст из сообщения"""
    return (
        message.text
        or message.caption
        or (message.sticker.emoji if message.sticker else "")
    )


def extract_unt_fedban(
    message: Message, args: List[str]
) -> Tuple[Optional[int], Optional[str]]:
    """Извлекает пользователя для федерального бана"""
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    if len(split_text) < 2:
        text = ""
    else:
        text = split_text[1]

    if prev_message:
        user = prev_message.from_user
        if not user:
            if prev_message.sender_chat:
                return prev_message.sender_chat.id, text
            return None, None
        return user.id, text

    if args:
        if args[0].isdigit():
            return int(args[0]), " ".join(args[1:]) if len(args) > 1 else ""
        
        if args[0].startswith("@"):
            user = args[0]
            user_id = get_user_id(user)
            if not user_id:
                return None, None
            return user_id, " ".join(args[1:]) if len(args) > 1 else ""

    return None, None
