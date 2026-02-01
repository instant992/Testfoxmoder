# -*- coding: utf-8 -*-
"""
Модуль отслеживания пользователей - сохраняет username -> user_id mapping
"""

from telegram import Update
from telegram.ext import (
    CallbackContext,
    MessageHandler,
    Filters,
)

from MitaHelper import dispatcher, LOGGER
from MitaHelper.modules.sql.users_sql import ensure_user, ensure_chat


def track_user(update: Update, context: CallbackContext):
    """Отслеживает пользователей и сохраняет их в базу"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    
    # Сохраняем пользователя
    if user:
        ensure_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
    
    # Сохраняем чат
    if chat and chat.type != "private":
        ensure_chat(
            chat_id=chat.id,
            title=chat.title,
            username=chat.username
        )
    
    # Если есть reply - сохраняем и того пользователя
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        reply_user = msg.reply_to_message.from_user
        ensure_user(
            user_id=reply_user.id,
            username=reply_user.username,
            first_name=reply_user.first_name
        )
    
    # Если есть forward - сохраняем отправителя
    if msg and msg.forward_from:
        ensure_user(
            user_id=msg.forward_from.id,
            username=msg.forward_from.username,
            first_name=msg.forward_from.first_name
        )


def track_new_members(update: Update, context: CallbackContext):
    """Отслеживает новых участников чата"""
    msg = update.effective_message
    
    if msg and msg.new_chat_members:
        for member in msg.new_chat_members:
            if not member.is_bot:
                ensure_user(
                    user_id=member.id,
                    username=member.username,
                    first_name=member.first_name
                )


# Обработчик всех сообщений (самый низкий приоритет)
track_handler = MessageHandler(
    Filters.all & ~Filters.command,
    track_user,
    run_async=True
)
dispatcher.add_handler(track_handler, group=999)

# Обработчик новых участников
new_members_handler = MessageHandler(
    Filters.status_update.new_chat_members,
    track_new_members,
    run_async=True
)
dispatcher.add_handler(new_members_handler, group=998)


__mod_name__ = "👥 Трекинг"
