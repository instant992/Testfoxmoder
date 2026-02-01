# -*- coding: utf-8 -*-
"""
Вспомогательные функции для работы с топиками (форумами)
"""

from telegram import Update, Chat, Message


def is_forum(chat: Chat) -> bool:
    """Проверяет, является ли чат форумом с топиками"""
    return getattr(chat, 'is_forum', False)


def get_thread_id(message: Message) -> int:
    """Получает ID топика из сообщения, если чат - форум"""
    if message and hasattr(message, 'message_thread_id'):
        return message.message_thread_id
    return None


def get_thread_id_from_update(update: Update) -> int:
    """Получает ID топика из Update"""
    if update.effective_message:
        return get_thread_id(update.effective_message)
    return None


def send_message_to_thread(bot, chat_id: int, text: str, thread_id: int = None, **kwargs):
    """
    Отправляет сообщение с учётом топика.
    Если thread_id указан - отправляет в топик, иначе - в основной чат.
    """
    if thread_id:
        return bot.send_message(
            chat_id=chat_id,
            text=text,
            message_thread_id=thread_id,
            **kwargs
        )
    else:
        return bot.send_message(
            chat_id=chat_id,
            text=text,
            **kwargs
        )
