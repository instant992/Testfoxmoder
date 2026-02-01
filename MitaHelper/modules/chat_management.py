# -*- coding: utf-8 -*-
"""
Модуль управления чатами - добавление/удаление чатов для управления
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import CallbackContext, CommandHandler
from telegram.error import BadRequest

from MitaHelper import dispatcher, LOGGER, OWNER_ID, SUDO_USERS, BOT_USERNAME
from MitaHelper.modules.database import (
    add_chat,
    remove_chat,
    get_chat,
    is_chat_added,
    get_user_chats,
)


# Время автоудаления сообщения о добавлении (в секундах)
ADDMITA_MSG_DELETE_TIME = 120  # 2 минуты


def delete_addmita_message(context: CallbackContext):
    """Удаляет сообщение о добавлении чата по таймеру"""
    job = context.job
    try:
        context.bot.delete_message(
            chat_id=job.context["chat_id"],
            message_id=job.context["message_id"]
        )
    except:
        pass


def addmita(update: Update, context: CallbackContext):
    """Добавляет чат для управления ботом"""
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    
    # Только в группах
    if chat.type == "private":
        msg.reply_text("❌ Эта команда работает только в группах!")
        return
    
    # Проверяем, является ли пользователь админом чата в Telegram
    try:
        member = chat.get_member(user.id)
        if member.status not in ("administrator", "creator"):
            # Разрешаем также владельцу бота и sudo-юзерам
            if user.id != OWNER_ID and user.id not in SUDO_USERS:
                msg.reply_text("❌ Только администраторы чата могут добавить его для управления!")
                return
    except BadRequest:
        msg.reply_text("❌ Не удалось проверить ваши права.")
        return
    
    # Проверяем, является ли бот админом
    try:
        bot_member = chat.get_member(context.bot.id)
        if bot_member.status != "administrator":
            msg.reply_text(
                "⚠️ Сделайте меня администратором чата для полноценной работы!\n\n"
                "Чат всё равно добавлен, но некоторые функции могут не работать."
            )
    except BadRequest:
        pass
    
    # Добавляем чат
    if is_chat_added(chat.id):
        keyboard = [[
            InlineKeyboardButton("⚙️ Перейти в бота", url=f"https://t.me/{BOT_USERNAME}?start=config")
        ]]
        sent_msg = msg.reply_text(
            f"✅ Чат *{chat.title}* уже добавлен!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Планируем удаление сообщения
        context.job_queue.run_once(
            delete_addmita_message,
            ADDMITA_MSG_DELETE_TIME,
            context={"chat_id": chat.id, "message_id": sent_msg.message_id},
            name=f"delete_addmita_{chat.id}_{sent_msg.message_id}"
        )
    else:
        add_chat(chat.id, chat.title, user.id)
        keyboard = [[
            InlineKeyboardButton("⚙️ Перейти в бота", url=f"https://t.me/{BOT_USERNAME}?start=config")
        ]]
        sent_msg = msg.reply_text(
            f"✅ Чат *{chat.title}* успешно добавлен!\n\n"
            f"🆔 ID: `{chat.id}`\n"
            f"👤 Добавил: {user.first_name}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Планируем удаление сообщения
        context.job_queue.run_once(
            delete_addmita_message,
            ADDMITA_MSG_DELETE_TIME,
            context={"chat_id": chat.id, "message_id": sent_msg.message_id},
            name=f"delete_addmita_{chat.id}_{sent_msg.message_id}"
        )
        LOGGER.info(f"Чат {chat.title} ({chat.id}) добавлен пользователем {user.id}")


def delmita(update: Update, context: CallbackContext):
    """Удаляет чат из управления ботом"""
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    
    # Только в группах
    if chat.type == "private":
        msg.reply_text("❌ Эта команда работает только в группах!")
        return
    
    # Проверяем права
    try:
        member = chat.get_member(user.id)
        if member.status not in ("administrator", "creator"):
            if user.id != OWNER_ID and user.id not in SUDO_USERS:
                msg.reply_text("❌ Только администраторы чата могут удалить его!")
                return
    except BadRequest:
        msg.reply_text("❌ Не удалось проверить ваши права.")
        return
    
    # Удаляем чат
    if not is_chat_added(chat.id):
        msg.reply_text("❌ Этот чат не был добавлен.")
    else:
        remove_chat(chat.id)
        msg.reply_text(
            f"✅ Чат *{chat.title}* удалён из управления ботом.",
            parse_mode=ParseMode.MARKDOWN
        )
        LOGGER.info(f"Чат {chat.title} ({chat.id}) удалён пользователем {user.id}")


def mychats(update: Update, context: CallbackContext):
    """Показывает чаты пользователя"""
    user = update.effective_user
    msg = update.effective_message
    
    chats = get_user_chats(user.id)
    
    if not chats:
        msg.reply_text(
            "📋 У вас нет добавленных чатов.\n\n"
            "Добавьте чат командой /addmita в нужной группе."
        )
        return
    
    text = "📋 *Ваши чаты:*\n\n"
    for i, chat_data in enumerate(chats, 1):
        text += f"{i}. {chat_data['title']}\n"
        text += f"   🆔 `{chat_data['chat_id']}`\n\n"
    
    text += "_Используйте /config для настройки чатов._"
    
    msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# Регистрация обработчиков
ADDMITA_HANDLER = CommandHandler("addmita", addmita, run_async=True)
DELMITA_HANDLER = CommandHandler("delmita", delmita, run_async=True)
MYCHATS_HANDLER = CommandHandler("mychats", mychats, run_async=True)

dispatcher.add_handler(ADDMITA_HANDLER)
dispatcher.add_handler(DELMITA_HANDLER)
dispatcher.add_handler(MYCHATS_HANDLER)


__mod_name__ = "📋 Чаты"

__help__ = """
*Управление чатами:*

• /addmita — добавить этот чат для управления ботом
• /delmita — удалить этот чат из управления
• /mychats — показать ваши чаты

После добавления чата используйте /config в ЛС бота для настройки.
"""
