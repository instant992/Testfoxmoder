# -*- coding: utf-8 -*-
"""
Вспомогательные функции для проверки статуса в чате
"""

from functools import wraps
from threading import RLock
from time import perf_counter

from cachetools import TTLCache
from telegram import Chat, ChatMember, ParseMode, Update
from telegram.ext import CallbackContext

from MitaHelper import (
    DEV_USERS,
    LOGGER,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    WHITELIST_USERS,
    dispatcher,
)

# Импорт проверки админов бота
try:
    from MitaHelper.modules.bot_admins import is_bot_admin as is_bot_admin_db, has_permission
except ImportError:
    is_bot_admin_db = lambda chat_id, user_id: False
    has_permission = lambda chat_id, user_id, perm: False

# Кэш для администраторов (5 минут)
ADMIN_CACHE = TTLCache(maxsize=512, ttl=300)
THREAD_LOCK = RLock()


def is_whitelist_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Проверяет, есть ли пользователь в белом списке или выше"""
    return any([
        user_id in WHITELIST_USERS,
        user_id in SUPPORT_USERS,
        user_id in SUDO_USERS,
        user_id in DEV_USERS,
        user_id == OWNER_ID,
    ])


def is_support_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Проверяет, является ли пользователь саппортом или выше"""
    return any([
        user_id in SUPPORT_USERS,
        user_id in SUDO_USERS,
        user_id in DEV_USERS,
        user_id == OWNER_ID,
    ])


def is_sudo_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Проверяет, является ли пользователь sudo или выше"""
    return any([
        user_id in SUDO_USERS,
        user_id in DEV_USERS,
        user_id == OWNER_ID,
    ])


def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Проверяет, является ли пользователь админом чата или админом бота"""
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in DEV_USERS
        or user_id == OWNER_ID
        or chat.all_members_are_administrators
        or (member and member.status in ("administrator", "creator"))
    ):
        return True
    
    # Проверяем админов бота (отдельная база)
    if is_bot_admin_db(chat.id, user_id):
        return True

    if not member:
        with THREAD_LOCK:
            admin_list = ADMIN_CACHE.get(chat.id)
            if admin_list is None:
                admin_list = [
                    admin.user.id
                    for admin in chat.get_administrators()
                ]
                ADMIN_CACHE[chat.id] = admin_list

            return user_id in admin_list
    
    return member.status in ("administrator", "creator")


def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    """Проверяет, является ли бот админом чата"""
    if chat.type == "private" or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = chat.get_member(bot_id)

    return bot_member.status in ("administrator", "creator")


def can_delete(func):
    """Декоратор: бот должен иметь право удалять сообщения"""
    @wraps(func)
    def delete_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        
        if chat.type == "private":
            return func(update, context, *args, **kwargs)
        
        try:
            member = chat.get_member(bot.id)
            if member.can_delete_messages:
                return func(update, context, *args, **kwargs)
            else:
                update.effective_message.reply_text(
                    "❌ У меня нет прав на удаление сообщений!"
                )
        except Exception:
            update.effective_message.reply_text(
                "❌ Не могу проверить свои права. Убедитесь, что я админ."
            )
    
    return delete_rights


def can_pin(func):
    """Декоратор: бот должен иметь право закреплять сообщения"""
    @wraps(func)
    def pin_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        
        if chat.type == "private":
            return func(update, context, *args, **kwargs)
        
        try:
            member = chat.get_member(bot.id)
            if member.can_pin_messages:
                return func(update, context, *args, **kwargs)
            else:
                update.effective_message.reply_text(
                    "❌ У меня нет прав на закрепление сообщений!"
                )
        except Exception:
            update.effective_message.reply_text(
                "❌ Не могу проверить свои права. Убедитесь, что я админ."
            )
    
    return pin_rights


def can_promote(func):
    """Декоратор: бот должен иметь право повышать пользователей"""
    @wraps(func)
    def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        
        if chat.type == "private":
            return func(update, context, *args, **kwargs)
        
        try:
            member = chat.get_member(bot.id)
            if member.can_promote_members:
                return func(update, context, *args, **kwargs)
            else:
                update.effective_message.reply_text(
                    "❌ У меня нет прав на управление админами!"
                )
        except Exception:
            update.effective_message.reply_text(
                "❌ Не могу проверить свои права. Убедитесь, что я админ."
            )
    
    return promote_rights


def can_restrict(func):
    """Декоратор: бот должен иметь право ограничивать пользователей"""
    @wraps(func)
    def restrict_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        
        if chat.type == "private":
            return func(update, context, *args, **kwargs)
        
        try:
            member = chat.get_member(bot.id)
            if member.can_restrict_members:
                return func(update, context, *args, **kwargs)
            else:
                update.effective_message.reply_text(
                    "❌ У меня нет прав на бан/мут пользователей!"
                )
        except Exception:
            update.effective_message.reply_text(
                "❌ Не могу проверить свои права. Убедитесь, что я админ."
            )
    
    return restrict_rights


def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Проверяет, защищён ли пользователь от бана"""
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in DEV_USERS
        or user_id in WHITELIST_USERS
        or user_id == OWNER_ID
        or chat.all_members_are_administrators
    ):
        return True

    if not member:
        member = chat.get_member(user_id)

    return member.status in ("administrator", "creator")


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    """Проверяет, есть ли пользователь в чате"""
    member = chat.get_member(user_id)
    return member.status not in ("left", "kicked")


# ═══════════════════════════════════════════════════════════════
#                        ДЕКОРАТОРЫ
# ═══════════════════════════════════════════════════════════════

def bot_admin(func):
    """Декоратор: бот должен быть админом"""
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title
        
        if update_chat_title == message_chat_title:
            if not is_bot_admin(chat, bot.id):
                update.effective_message.reply_text(
                    "❌ Я не админ в этом чате! Сделайте меня админом."
                )
                return
        return func(update, context, *args, **kwargs)
    
    return is_admin


def user_admin(func):
    """Декоратор: пользователь должен быть админом"""
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat
        
        if user and is_user_admin(chat, user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except Exception:
                pass
        else:
            update.effective_message.reply_text(
                "❌ У вас недостаточно прав для выполнения этой команды."
            )
    
    return is_admin


def user_admin_no_reply(func):
    """Декоратор: пользователь должен быть админом (без ответа)"""
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        
        if user and is_user_admin(chat, user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
    
    return is_admin


def user_not_admin(func):
    """Декоратор: пользователь НЕ должен быть админом"""
    @wraps(func)
    def is_not_admin(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        
        if user and not is_user_admin(chat, user.id):
            return func(update, context, *args, **kwargs)
    
    return is_not_admin


def dev_plus(func):
    """Декоратор: только для разработчиков"""
    @wraps(func)
    def is_dev_plus(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        
        if user.id in DEV_USERS or user.id == OWNER_ID:
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        else:
            update.effective_message.reply_text(
                "❌ Эта команда доступна только для разработчиков."
            )
    
    return is_dev_plus


def sudo_plus(func):
    """Декоратор: только для sudo пользователей"""
    @wraps(func)
    def is_sudo_plus(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        
        if user and is_sudo_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        else:
            update.effective_message.reply_text(
                "❌ Эта команда доступна только для sudo пользователей."
            )
    
    return is_sudo_plus


def whitelist_plus(func):
    """Декоратор: только для пользователей из белого списка"""
    @wraps(func)
    def is_whitelist_plus(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        
        if user and is_whitelist_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        else:
            update.effective_message.reply_text(
                "❌ У вас недостаточно прав для этой команды."
            )
    
    return is_whitelist_plus


def connection_status(func):
    """Декоратор: проверка статуса подключения"""
    @wraps(func)
    def connected_status(update: Update, context: CallbackContext, *args, **kwargs):
        return func(update, context, *args, **kwargs)
    
    return connected_status


# Удаление команд после выполнения
from MitaHelper.config import Config
DEL_CMDS = getattr(Config, 'DEL_CMDS', False)
