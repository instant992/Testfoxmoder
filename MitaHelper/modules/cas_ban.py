# -*- coding: utf-8 -*-
"""
Модуль CAS (Combot Anti-Spam) - проверка пользователей на спам
https://cas.chat/
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime

from telegram import Update, ParseMode, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import CallbackContext, MessageHandler, Filters

from MitaHelper import dispatcher, LOGGER


# API CAS
CAS_API_URL = "https://api.cas.chat/check?user_id="

# Путь к файлу с настройками
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CAS_SETTINGS_FILE = os.path.join(DATA_DIR, "cas_settings.json")

# Хранилище настроек
# {chat_id: {"enabled": True, "action": "ban", "notify": True}}
cas_settings = {}


def load_cas_settings():
    """Загружает настройки из файла"""
    global cas_settings
    try:
        if os.path.exists(CAS_SETTINGS_FILE):
            with open(CAS_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cas_settings = {int(k): v for k, v in data.items()}
                LOGGER.info(f"Загружены CAS настройки для {len(cas_settings)} чатов")
    except Exception as e:
        LOGGER.error(f"Ошибка загрузки CAS настроек: {e}")
        cas_settings = {}


def save_cas_settings():
    """Сохраняет настройки в файл"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CAS_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cas_settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.error(f"Ошибка сохранения CAS настроек: {e}")


# Загружаем при импорте
load_cas_settings()


# Действия при обнаружении спамера
CAS_ACTIONS = {
    "ban": "🔨 Бан",
    "kick": "👢 Кик",
    "mute": "🔇 Мут",
}


def get_cas_settings(chat_id: int) -> dict:
    """Получает настройки CAS для чата"""
    default = {
        "enabled": False,
        "action": "ban",
        "notify": True,
    }
    return cas_settings.get(chat_id, default.copy())


def set_cas_settings(chat_id: int, settings: dict):
    """Сохраняет настройки CAS"""
    cas_settings[chat_id] = settings
    save_cas_settings()


def toggle_cas(chat_id: int) -> bool:
    """Включает/выключает CAS. Возвращает новое состояние."""
    settings = get_cas_settings(chat_id)
    settings["enabled"] = not settings.get("enabled", False)
    set_cas_settings(chat_id, settings)
    return settings["enabled"]


def set_cas_action(chat_id: int, action: str):
    """Устанавливает действие при обнаружении спамера"""
    settings = get_cas_settings(chat_id)
    settings["action"] = action
    set_cas_settings(chat_id, settings)


def toggle_cas_notify(chat_id: int) -> bool:
    """Включает/выключает уведомления"""
    settings = get_cas_settings(chat_id)
    settings["notify"] = not settings.get("notify", True)
    set_cas_settings(chat_id, settings)
    return settings["notify"]


def check_cas(user_id: int) -> dict:
    """
    Проверяет пользователя через CAS API
    Возвращает: {"ok": True/False, "result": {...}} или None при ошибке
    """
    try:
        url = f"{CAS_API_URL}{user_id}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data
    except urllib.error.URLError as e:
        LOGGER.warning(f"Ошибка запроса к CAS API: {e}")
    except json.JSONDecodeError:
        LOGGER.warning("Ошибка парсинга ответа CAS API")
    except Exception as e:
        LOGGER.warning(f"Ошибка CAS: {e}")
    return None


def is_cas_banned(user_id: int) -> tuple:
    """
    Проверяет, забанен ли пользователь в CAS
    Возвращает: (is_banned: bool, reason: str or None)
    """
    data = check_cas(user_id)
    if data and data.get("ok"):
        result = data.get("result", {})
        if result:
            # Пользователь в базе CAS
            offenses = result.get("offenses", 0)
            time_added = result.get("time_added")
            return True, f"Offenses: {offenses}"
    return False, None


def check_new_member_cas(update: Update, context: CallbackContext):
    """Проверяет нового участника через CAS"""
    if not update.effective_message:
        return
    
    chat = update.effective_chat
    
    # Только в группах
    if chat.type == "private":
        return
    
    # Получаем настройки
    settings = get_cas_settings(chat.id)
    if not settings.get("enabled", False):
        return
    
    new_members = update.effective_message.new_chat_members
    if not new_members:
        return
    
    action = settings.get("action", "ban")
    notify = settings.get("notify", True)
    
    for member in new_members:
        # Пропускаем ботов (кроме спам-ботов)
        if member.is_bot:
            continue
        
        # Проверяем через CAS
        is_banned, reason = is_cas_banned(member.id)
        
        if is_banned:
            LOGGER.info(f"CAS: Обнаружен спамер {member.id} ({member.first_name}) в чате {chat.id}")
            
            try:
                if action == "ban":
                    context.bot.ban_chat_member(chat.id, member.id)
                    action_text = "забанен"
                elif action == "kick":
                    context.bot.ban_chat_member(chat.id, member.id)
                    context.bot.unban_chat_member(chat.id, member.id)
                    action_text = "кикнут"
                elif action == "mute":
                    context.bot.restrict_chat_member(
                        chat.id,
                        member.id,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    action_text = "замучен"
                else:
                    context.bot.ban_chat_member(chat.id, member.id)
                    action_text = "забанен"
                
                # Уведомление в чат
                if notify:
                    text = (
                        f"🛡 <b>CAS Anti-Spam</b>\n\n"
                        f"👤 Пользователь: {member.first_name}\n"
                        f"🆔 ID: <code>{member.id}</code>\n"
                        f"⚠️ Статус: В базе спамеров CAS\n"
                        f"✅ Действие: {action_text}\n\n"
                        f"<i>Проверить: cas.chat/query?u={member.id}</i>"
                    )
                    context.bot.send_message(
                        chat.id,
                        text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )
                
                # Логируем
                try:
                    from MitaHelper.modules.logs import log_event
                    log_event(
                        context.bot,
                        chat.id,
                        "cas_ban",
                        f"🛡 CAS заблокировал спамера {member.first_name} (ID: {member.id})"
                    )
                except:
                    pass
                    
            except BadRequest as e:
                LOGGER.warning(f"CAS: Не удалось выполнить действие: {e}")


# Регистрация обработчика
CAS_HANDLER = MessageHandler(
    Filters.status_update.new_chat_members,
    check_new_member_cas,
    run_async=True
)

# Добавляем с высоким приоритетом (раньше капчи)
dispatcher.add_handler(CAS_HANDLER, group=1)


__mod_name__ = "🛡 CAS Anti-Spam"

__help__ = """
*CAS (Combot Anti-Spam):*

Автоматическая проверка новых участников через базу спамеров CAS.

*Что такое CAS?*
CAS — это глобальная база данных спамеров Telegram, поддерживаемая сообществом. Если пользователь замечен в спаме в других чатах, он попадает в эту базу.

*Действия при обнаружении:*
• 🔨 Бан — навсегда забанить
• 👢 Кик — выгнать из чата
• 🔇 Мут — запретить писать

*Настройка:*
/config → Выберите чат → 🛡 CAS Anti-Spam

*Проверить пользователя:*
cas.chat/query?u=USER_ID
"""
