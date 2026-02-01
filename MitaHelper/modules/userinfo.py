# -*- coding: utf-8 -*-
"""
Модуль информации о пользователе
"""

import html
from telegram import ParseMode, Update, MAX_MESSAGE_LENGTH
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler
from telegram.utils.helpers import mention_html

from MitaHelper import (
    DEV_USERS,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    WHITELIST_USERS,
    dispatcher,
)
from MitaHelper.modules.helper_funcs.extraction import extract_user


def get_id(update: Update, context: CallbackContext):
    """Показывает ID пользователя или чата"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    user_id = extract_user(msg, args)
    
    if user_id:
        if msg.reply_to_message and msg.reply_to_message.forward_from:
            # Если это пересланное сообщение
            user1 = msg.reply_to_message.from_user
            user2 = msg.reply_to_message.forward_from
            
            msg.reply_text(
                f"👤 *ID пользователей:*\n\n"
                f"• {html.escape(user1.first_name)}: `{user1.id}`\n"
                f"• {html.escape(user2.first_name)} (оригинал): `{user2.id}`",
                parse_mode=ParseMode.HTML,
            )
        else:
            user = context.bot.get_chat(user_id)
            msg.reply_text(
                f"👤 ID {html.escape(user.first_name)}: `{user.id}`",
                parse_mode=ParseMode.HTML,
            )
    elif chat.type == "private":
        msg.reply_text(f"🆔 Ваш ID: `{chat.id}`", parse_mode=ParseMode.MARKDOWN)
    else:
        msg.reply_text(f"🆔 ID этого чата: `{chat.id}`", parse_mode=ParseMode.MARKDOWN)


def info(update: Update, context: CallbackContext):
    """Показывает информацию о пользователе"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    user_id = extract_user(msg, args)
    
    if not user_id:
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
        else:
            user = msg.from_user
        user_id = user.id
    
    try:
        user = context.bot.get_chat(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return
    
    text = f"👤 *Информация о пользователе*\n\n"
    text += f"🆔 *ID:* `{user.id}`\n"
    text += f"👤 *Имя:* {html.escape(user.first_name)}\n"
    
    if user.last_name:
        text += f"👤 *Фамилия:* {html.escape(user.last_name)}\n"
    
    if user.username:
        text += f"📛 *Username:* @{user.username}\n"
    
    text += f"🔗 *Ссылка:* {mention_html(user.id, 'ссылка')}\n"
    
    # Проверяем привилегии
    if user.id == OWNER_ID:
        text += "\n🌟 *Статус:* Владелец бота"
    elif user.id in DEV_USERS:
        text += "\n⭐ *Статус:* Разработчик"
    elif user.id in SUDO_USERS:
        text += "\n⚡ *Статус:* Sudo пользователь"
    elif user.id in SUPPORT_USERS:
        text += "\n💎 *Статус:* Поддержка"
    elif user.id in WHITELIST_USERS:
        text += "\n✅ *Статус:* Белый список"
    
    # Информация в чате
    if chat.type != "private":
        try:
            member = chat.get_member(user.id)
            if member.status == "creator":
                text += f"\n\n👑 *Роль в чате:* Создатель"
            elif member.status == "administrator":
                text += f"\n\n⭐ *Роль в чате:* Администратор"
                if member.custom_title:
                    text += f"\n📌 *Титул:* {html.escape(member.custom_title)}"
            elif member.status == "member":
                text += f"\n\n👥 *Роль в чате:* Участник"
        except BadRequest:
            pass
    
    # Описание пользователя (bio)
    if user.bio:
        text += f"\n\n📝 *О себе:*\n{html.escape(user.bio)}"
    
    msg.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def stats(update: Update, context: CallbackContext):
    """Показывает статистику бота (только для владельца)"""
    user = update.effective_user
    msg = update.effective_message
    
    if user.id != OWNER_ID and user.id not in DEV_USERS:
        msg.reply_text("❌ Эта команда доступна только для владельца.")
        return
    
    text = "📊 *Статистика бота:*\n\n"
    text += f"👑 Владелец: `{OWNER_ID}`\n"
    text += f"⭐ Разработчиков: `{len(DEV_USERS)}`\n"
    text += f"⚡ Sudo пользователей: `{len(SUDO_USERS)}`\n"
    text += f"💎 Поддержка: `{len(SUPPORT_USERS)}`\n"
    text += f"✅ Белый список: `{len(WHITELIST_USERS)}`\n"
    
    msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

ID_HANDLER = CommandHandler("id", get_id, run_async=True)
INFO_HANDLER = CommandHandler(["info", "user"], info, run_async=True)
STATS_HANDLER = CommandHandler("stats", stats, run_async=True)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(STATS_HANDLER)


__mod_name__ = "ℹ️ Информация"

__help__ = """
*Информация о пользователях:*

ℹ️ *Команды:*
• /id — показать ваш ID или ID чата
• /id `<пользователь>` — показать ID пользователя
• /info или /инфо — информация о вас
• /info `<пользователь>` — информация о пользователе
• /stats — статистика бота (только владелец)

📝 *Отображаемая информация:*
• ID пользователя
• Имя и фамилия
• Username
• Статус в боте (если есть)
• Роль в чате
• Описание профиля
"""
