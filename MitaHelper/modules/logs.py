# -*- coding: utf-8 -*-
"""
Модуль логирования - отправка логов в отдельный чат
"""

from datetime import datetime
from telegram import ParseMode, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CallbackContext, CommandHandler

from MitaHelper import dispatcher, LOGGER, OWNER_ID, SUDO_USERS


# Хранилище настроек логов {chat_id: {"log_channel": channel_id, "events": [...]}}
log_settings = {}

# Загрузка из БД
try:
    from MitaHelper.modules.database import load_logs_settings, save_logs_settings
    _loaded = load_logs_settings()
    if _loaded:
        log_settings = _loaded
        LOGGER.info(f"Загружены настройки логов для {len(log_settings)} чатов")
except Exception as e:
    LOGGER.warning(f"Не удалось загрузить настройки логов: {e}")
    save_logs_settings = None


def _save_logs_to_db():
    """Сохраняет настройки логов в БД"""
    if save_logs_settings:
        save_logs_settings(log_settings)


# Типы событий для логирования
LOG_EVENTS = {
    "join": "👋 Входы",
    "leave": "🚪 Выходы", 
    "captcha_pass": "✅ Капча пройдена",
    "captcha_fail": "❌ Капча провалена",
    "ban": "🔨 Баны",
    "unban": "🔓 Разбаны",
    "kick": "👢 Кики",
    "mute": "🔇 Муты",
    "unmute": "🔊 Размуты",
    "warn": "⚠️ Варны",
    "filter": "📝 Фильтры",
    "settings": "⚙️ Настройки",
}

DEFAULT_EVENTS = ["join", "captcha_pass", "captcha_fail", "ban", "kick", "mute", "warn"]


def get_log_settings(chat_id: int) -> dict:
    """Получает настройки логов для чата"""
    return log_settings.get(chat_id, {"log_channel": None, "events": DEFAULT_EVENTS.copy()})


def set_log_channel(chat_id: int, log_channel_id: int):
    """Устанавливает канал/чат для логов"""
    if chat_id not in log_settings:
        log_settings[chat_id] = {"log_channel": None, "events": DEFAULT_EVENTS.copy()}
    log_settings[chat_id]["log_channel"] = log_channel_id
    _save_logs_to_db()


def remove_log_channel(chat_id: int):
    """Удаляет канал логов"""
    if chat_id in log_settings:
        log_settings[chat_id]["log_channel"] = None
        _save_logs_to_db()


def toggle_log_event(chat_id: int, event: str) -> bool:
    """Переключает событие для логирования. Возвращает новое состояние."""
    if chat_id not in log_settings:
        log_settings[chat_id] = {"log_channel": None, "events": DEFAULT_EVENTS.copy()}
    
    if event in log_settings[chat_id]["events"]:
        log_settings[chat_id]["events"].remove(event)
        _save_logs_to_db()
        return False
    else:
        log_settings[chat_id]["events"].append(event)
        _save_logs_to_db()
        return True


def is_event_enabled(chat_id: int, event: str) -> bool:
    """Проверяет, включено ли логирование события"""
    settings = get_log_settings(chat_id)
    return event in settings.get("events", [])


def send_log(
    bot,
    chat_id: int,
    event: str,
    text: str,
    user=None,
    target_user=None,
    extra_info: str = None
):
    """
    Отправляет лог в канал логов.
    
    Args:
        bot: Объект бота
        chat_id: ID чата, для которого отправляется лог
        event: Тип события (join, ban, etc.)
        text: Основной текст лога
        user: Пользователь, совершивший действие (админ)
        target_user: Пользователь, над которым совершено действие
        extra_info: Дополнительная информация
    """
    settings = get_log_settings(chat_id)
    log_channel = settings.get("log_channel")
    
    if not log_channel:
        return
    
    if event not in settings.get("events", []):
        return
    
    # Формируем сообщение лога
    event_emoji = LOG_EVENTS.get(event, "📋").split()[0]
    event_name = LOG_EVENTS.get(event, event)
    
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    log_text = f"{event_emoji} *{event_name}*\n"
    log_text += f"📅 `{now}`\n\n"
    log_text += text
    
    if user:
        user_link = f"[{user.first_name}](tg://user?id={user.id})"
        log_text += f"\n\n👤 Выполнил: {user_link} (`{user.id}`)"
    
    if target_user:
        target_link = f"[{target_user.first_name}](tg://user?id={target_user.id})"
        log_text += f"\n🎯 Цель: {target_link} (`{target_user.id}`)"
    
    if extra_info:
        log_text += f"\n📝 {extra_info}"
    
    try:
        bot.send_message(
            log_channel,
            log_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except (BadRequest, Unauthorized) as e:
        LOGGER.warning(f"Не удалось отправить лог в {log_channel}: {e}")


def log_join(bot, chat, user):
    """Логирует вход пользователя"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"👤 Пользователь: [{user.first_name}](tg://user?id={user.id})\n"
        text += f"🆔 ID: `{user.id}`"
        if user.username:
            text += f"\n📧 Username: @{user.username}"
        
        send_log(bot, chat.id, "join", text, target_user=user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования входа: {e}")


def log_leave(bot, chat, user):
    """Логирует выход пользователя"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"👤 Пользователь: [{user.first_name}](tg://user?id={user.id})\n"
        text += f"🆔 ID: `{user.id}`"
        
        send_log(bot, chat.id, "leave", text, target_user=user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования выхода: {e}")


def log_captcha_pass(bot, chat, user):
    """Логирует успешное прохождение капчи"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"👤 Пользователь: [{user.first_name}](tg://user?id={user.id})\n"
        text += f"🆔 ID: `{user.id}`\n"
        text += f"✅ Капча успешно пройдена"
        
        send_log(bot, chat.id, "captcha_pass", text, target_user=user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования капчи: {e}")


def log_captcha_fail(bot, chat, user, reason="Таймаут"):
    """Логирует провал капчи"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"👤 Пользователь: [{user.first_name}](tg://user?id={user.id})\n"
        text += f"🆔 ID: `{user.id}`\n"
        text += f"❌ Причина: {reason}"
        
        send_log(bot, chat.id, "captcha_fail", text, target_user=user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования провала капчи: {e}")


def log_ban(bot, chat, admin, target_user, reason=None):
    """Логирует бан"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"🔨 Забанен: [{target_user.first_name}](tg://user?id={target_user.id})\n"
        text += f"🆔 ID: `{target_user.id}`"
        if reason:
            text += f"\n📝 Причина: {reason}"
        
        send_log(bot, chat.id, "ban", text, user=admin, target_user=target_user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования бана: {e}")


def log_unban(bot, chat, admin, target_user):
    """Логирует разбан"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"🔓 Разбанен: [{target_user.first_name}](tg://user?id={target_user.id})\n"
        text += f"🆔 ID: `{target_user.id}`"
        
        send_log(bot, chat.id, "unban", text, user=admin, target_user=target_user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования разбана: {e}")


def log_kick(bot, chat, admin, target_user, reason=None):
    """Логирует кик"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"👢 Кикнут: [{target_user.first_name}](tg://user?id={target_user.id})\n"
        text += f"🆔 ID: `{target_user.id}`"
        if reason:
            text += f"\n📝 Причина: {reason}"
        
        send_log(bot, chat.id, "kick", text, user=admin, target_user=target_user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования кика: {e}")


def log_mute(bot, chat, admin, target_user, duration=None, reason=None):
    """Логирует мут"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"🔇 Замучен: [{target_user.first_name}](tg://user?id={target_user.id})\n"
        text += f"🆔 ID: `{target_user.id}`"
        if duration:
            text += f"\n⏱ Длительность: {duration}"
        if reason:
            text += f"\n📝 Причина: {reason}"
        
        send_log(bot, chat.id, "mute", text, user=admin, target_user=target_user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования мута: {e}")


def log_unmute(bot, chat, admin, target_user):
    """Логирует размут"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"🔊 Размучен: [{target_user.first_name}](tg://user?id={target_user.id})\n"
        text += f"🆔 ID: `{target_user.id}`"
        
        send_log(bot, chat.id, "unmute", text, user=admin, target_user=target_user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования размута: {e}")


def log_warn(bot, chat, admin, target_user, reason=None, warn_count=None):
    """Логирует варн"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"⚠️ Варн: [{target_user.first_name}](tg://user?id={target_user.id})\n"
        text += f"🆔 ID: `{target_user.id}`"
        if warn_count:
            text += f"\n📊 Варнов: {warn_count}"
        if reason:
            text += f"\n📝 Причина: {reason}"
        
        send_log(bot, chat.id, "warn", text, user=admin, target_user=target_user)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования варна: {e}")


def log_settings_change(bot, chat, admin, setting_name, new_value):
    """Логирует изменение настроек"""
    try:
        chat_title = chat.title or "Чат"
        text = f"🏠 Чат: *{chat_title}*\n"
        text += f"⚙️ Настройка: *{setting_name}*\n"
        text += f"📝 Новое значение: `{new_value}`"
        
        send_log(bot, chat.id, "settings", text, user=admin)
    except Exception as e:
        LOGGER.warning(f"Ошибка логирования настроек: {e}")


__mod_name__ = "📋 Логи"

__help__ = """
*Система логирования:*

Логи отправляются в указанный чат/канал.

*Логируемые события:*
• 👋 Входы в группу
• 🚪 Выходы из группы
• ✅ Прохождение капчи
• ❌ Провал капчи
• 🔨 Баны
• 👢 Кики
• 🔇 Муты
• ⚠️ Варны

*Настройка:*
/config → Выберите чат → 📋 Логи
"""
