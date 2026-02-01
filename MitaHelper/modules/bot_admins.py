# -*- coding: utf-8 -*-
"""
Модуль управления админами бота
Отдельная база админов, не зависящая от админов Telegram-чата
"""

from threading import RLock
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, CommandHandler

from MitaHelper import dispatcher, OWNER_ID, DEV_USERS, SUDO_USERS, LOGGER


# Блокировка для потокобезопасности
ADMIN_LOCK = RLock()

# База админов бота: {chat_id: {user_id: {"role": str, "added_by": int, "permissions": list}}}
bot_admins_db = {}

# Роли админов бота
ROLES = {
    "owner": "👑 Владелец",
    "admin": "⭐ Админ бота",
    "moderator": "🛡 Модератор",
}

# Права по ролям
ROLE_PERMISSIONS = {
    "owner": ["all"],
    "admin": ["welcome", "captcha", "filters", "notes", "rules", "bans", "mutes", "warns"],
    "moderator": ["bans", "mutes", "warns"],
}


def get_bot_admins(chat_id: int) -> dict:
    """Получает список админов бота для чата"""
    return bot_admins_db.get(chat_id, {})


def is_bot_admin(chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь админом бота"""
    # Глобальные админы
    if user_id in (OWNER_ID,) or user_id in DEV_USERS or user_id in SUDO_USERS:
        return True
    
    admins = get_bot_admins(chat_id)
    return user_id in admins


def get_user_role(chat_id: int, user_id: int) -> str:
    """Получает роль пользователя"""
    if user_id == OWNER_ID:
        return "owner"
    if user_id in DEV_USERS or user_id in SUDO_USERS:
        return "admin"
    
    admins = get_bot_admins(chat_id)
    if user_id in admins:
        return admins[user_id].get("role", "moderator")
    return None


def has_permission(chat_id: int, user_id: int, permission: str) -> bool:
    """Проверяет, есть ли у пользователя определённое право"""
    role = get_user_role(chat_id, user_id)
    if not role:
        return False
    
    perms = ROLE_PERMISSIONS.get(role, [])
    return "all" in perms or permission in perms


def add_bot_admin(chat_id: int, user_id: int, role: str, added_by: int) -> bool:
    """Добавляет админа бота"""
    if role not in ROLES:
        return False
    
    with ADMIN_LOCK:
        if chat_id not in bot_admins_db:
            bot_admins_db[chat_id] = {}
        
        bot_admins_db[chat_id][user_id] = {
            "role": role,
            "added_by": added_by,
            "permissions": ROLE_PERMISSIONS.get(role, []),
        }
    
    return True


def remove_bot_admin(chat_id: int, user_id: int) -> bool:
    """Удаляет админа бота"""
    with ADMIN_LOCK:
        if chat_id in bot_admins_db and user_id in bot_admins_db[chat_id]:
            del bot_admins_db[chat_id][user_id]
            return True
    return False


def set_admin_role(chat_id: int, user_id: int, role: str) -> bool:
    """Изменяет роль админа"""
    if role not in ROLES:
        return False
    
    with ADMIN_LOCK:
        if chat_id in bot_admins_db and user_id in bot_admins_db[chat_id]:
            bot_admins_db[chat_id][user_id]["role"] = role
            bot_admins_db[chat_id][user_id]["permissions"] = ROLE_PERMISSIONS.get(role, [])
            return True
    return False


# ═══════════════════════════════════════════════════════════════
#                           КОМАНДЫ
# ═══════════════════════════════════════════════════════════════

def botadmins_cmd(update: Update, context: CallbackContext):
    """Показывает список админов бота для чата"""
    msg = update.effective_message
    user = update.effective_user
    args = context.args
    
    if not args:
        msg.reply_text(
            "❌ Укажите ID чата.\n"
            "Использование: `/botadmins <chat_id>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    try:
        chat_id = int(args[0])
    except ValueError:
        msg.reply_text("❌ Неверный ID чата.")
        return
    
    # Проверяем права
    if not is_bot_admin(chat_id, user.id) and user.id != OWNER_ID:
        msg.reply_text("❌ У вас нет прав для просмотра админов этого чата.")
        return
    
    admins = get_bot_admins(chat_id)
    
    if not admins:
        msg.reply_text(f"📋 В чате `{chat_id}` нет назначенных админов бота.", parse_mode=ParseMode.MARKDOWN)
        return
    
    text = f"👥 *Админы бота для чата* `{chat_id}`:\n\n"
    
    for admin_id, data in admins.items():
        role_name = ROLES.get(data["role"], data["role"])
        text += f"• `{admin_id}` — {role_name}\n"
    
    msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def addbotadmin_cmd(update: Update, context: CallbackContext):
    """Добавляет админа бота"""
    msg = update.effective_message
    user = update.effective_user
    args = context.args
    
    if len(args) < 2:
        msg.reply_text(
            "❌ Использование:\n"
            "`/addbotadmin <chat_id> <user_id> [role]`\n\n"
            "Роли: `admin`, `moderator`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    try:
        chat_id = int(args[0])
        target_id = int(args[1])
        role = args[2] if len(args) > 2 else "moderator"
    except ValueError:
        msg.reply_text("❌ Неверный ID.")
        return
    
    # Только владелец чата или глобальный админ может добавлять
    user_role = get_user_role(chat_id, user.id)
    if user_role not in ("owner", "admin") and user.id != OWNER_ID:
        msg.reply_text("❌ Только владельцы и админы могут добавлять других админов.")
        return
    
    # Модератор не может добавлять админов
    if role == "admin" and user_role == "moderator":
        msg.reply_text("❌ Модераторы не могут назначать админов.")
        return
    
    if add_bot_admin(chat_id, target_id, role, user.id):
        role_name = ROLES.get(role, role)
        msg.reply_text(
            f"✅ Пользователь `{target_id}` назначен {role_name} для чата `{chat_id}`.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        msg.reply_text("❌ Не удалось добавить админа. Проверьте роль.")


def rembotadmin_cmd(update: Update, context: CallbackContext):
    """Удаляет админа бота"""
    msg = update.effective_message
    user = update.effective_user
    args = context.args
    
    if len(args) < 2:
        msg.reply_text(
            "❌ Использование: `/rembotadmin <chat_id> <user_id>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    try:
        chat_id = int(args[0])
        target_id = int(args[1])
    except ValueError:
        msg.reply_text("❌ Неверный ID.")
        return
    
    # Проверяем права
    user_role = get_user_role(chat_id, user.id)
    if user_role not in ("owner", "admin") and user.id != OWNER_ID:
        msg.reply_text("❌ Недостаточно прав.")
        return
    
    if remove_bot_admin(chat_id, target_id):
        msg.reply_text(f"✅ Админ `{target_id}` удалён из чата `{chat_id}`.", parse_mode=ParseMode.MARKDOWN)
    else:
        msg.reply_text("❌ Админ не найден.")


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

dispatcher.add_handler(CommandHandler("botadmins", botadmins_cmd, run_async=True))
dispatcher.add_handler(CommandHandler("addbotadmin", addbotadmin_cmd, run_async=True))
dispatcher.add_handler(CommandHandler("rembotadmin", rembotadmin_cmd, run_async=True))


__mod_name__ = "👥 Админы бота"

__help__ = """
*Управление админами бота:*

Админы бота — отдельная система, не зависящая от админов Telegram-чата.
Это позволяет давать права на управление ботом без прав в самом чате.

👑 *Роли:*
• `owner` — полные права
• `admin` — все настройки бота
• `moderator` — только баны/муты/варны

📋 *Команды:*
• `/botadmins <chat_id>` — список админов
• `/addbotadmin <chat_id> <user_id> [role]` — добавить
• `/rembotadmin <chat_id> <user_id>` — удалить

*Пример:*
```
/addbotadmin -100123456789 987654321 admin
```
"""
