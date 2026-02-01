# -*- coding: utf-8 -*-
"""
Модуль медиа-фильтров - запрет различных типов контента
"""

import json
import os
from telegram import Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
)

from MitaHelper import dispatcher, LOGGER
from MitaHelper.modules.helper_funcs.chat_status import user_admin, bot_admin, can_delete


# Путь к файлу с настройками
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MEDIA_FILTERS_FILE = os.path.join(DATA_DIR, "media_filters.json")

# Хранилище настроек медиа-фильтров
# {chat_id: {"voice": True, "video_note": True, "sticker": False, ...}}
media_filter_settings = {}


def load_media_filter_settings():
    """Загружает настройки из файла"""
    global media_filter_settings
    try:
        if os.path.exists(MEDIA_FILTERS_FILE):
            with open(MEDIA_FILTERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Преобразуем строковые ключи обратно в int
                media_filter_settings = {int(k): v for k, v in data.items()}
                LOGGER.info(f"Загружены настройки медиа-фильтров для {len(media_filter_settings)} чатов")
    except Exception as e:
        LOGGER.error(f"Ошибка загрузки медиа-фильтров: {e}")
        media_filter_settings = {}


def save_media_filter_settings():
    """Сохраняет настройки в файл"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(MEDIA_FILTERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(media_filter_settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.error(f"Ошибка сохранения медиа-фильтров: {e}")


# Загружаем при импорте
load_media_filter_settings()

# Типы медиа для фильтрации
MEDIA_TYPES = {
    "voice": {
        "name": "🎤 Голосовые",
        "description": "Голосовые сообщения",
        "filter": Filters.voice,
    },
    "video_note": {
        "name": "🔵 Видеокружки",
        "description": "Круглые видеосообщения",
        "filter": Filters.video_note,
    },
    "sticker": {
        "name": "😀 Стикеры",
        "description": "Стикеры и анимированные стикеры",
        "filter": Filters.sticker,
    },
    "animation": {
        "name": "🎬 GIF",
        "description": "GIF анимации",
        "filter": Filters.animation,
    },
    "photo": {
        "name": "🖼 Фото",
        "description": "Фотографии",
        "filter": Filters.photo,
    },
    "video": {
        "name": "🎥 Видео",
        "description": "Видеофайлы",
        "filter": Filters.video,
    },
    "document": {
        "name": "📎 Файлы",
        "description": "Документы и файлы",
        "filter": Filters.document,
    },
    "audio": {
        "name": "🎵 Аудио",
        "description": "Аудиофайлы и музыка",
        "filter": Filters.audio,
    },
    "forward": {
        "name": "↩️ Пересланные",
        "description": "Пересланные сообщения",
        "filter": Filters.forwarded,
    },
    "url": {
        "name": "🔗 Ссылки",
        "description": "Сообщения со ссылками",
        "filter": Filters.entity("url") | Filters.entity("text_link"),
    },
    "contact": {
        "name": "👤 Контакты",
        "description": "Контакты",
        "filter": Filters.contact,
    },
    "location": {
        "name": "📍 Локации",
        "description": "Геолокации",
        "filter": Filters.location,
    },
    "poll": {
        "name": "📊 Опросы",
        "description": "Опросы",
        "filter": Filters.poll,
    },
    "game": {
        "name": "🎮 Игры",
        "description": "Игры",
        "filter": Filters.game,
    },
    "inline": {
        "name": "🤖 Inline-боты",
        "description": "Сообщения от inline-ботов",
        "filter": None,  # Проверяется вручную через msg.via_bot
    },
}

# Действия при нарушении
FILTER_ACTIONS = {
    "delete": "🗑 Удалить",
    "warn": "⚠️ Варн",
    "mute": "🔇 Мут 1ч",
    "kick": "👢 Кик",
}


def get_media_filter_settings(chat_id: int) -> dict:
    """Получает настройки медиа-фильтров для чата"""
    default = {
        "enabled": False,
        "filters": {},  # {media_type: True/False}
        "action": "delete",
        "warn_text": "⚠️ {mention}, в этом чате запрещены {type}!",
    }
    return media_filter_settings.get(chat_id, default.copy())


def set_media_filter_settings(chat_id: int, settings: dict):
    """Сохраняет настройки медиа-фильтров"""
    media_filter_settings[chat_id] = settings
    save_media_filter_settings()


def is_media_filtered(chat_id: int, media_type: str) -> bool:
    """Проверяет, запрещён ли данный тип медиа"""
    settings = get_media_filter_settings(chat_id)
    if not settings.get("enabled", False):
        return False
    return settings.get("filters", {}).get(media_type, False)


def toggle_media_filter(chat_id: int, media_type: str) -> bool:
    """Переключает фильтр для типа медиа. Возвращает новое состояние."""
    settings = get_media_filter_settings(chat_id)
    if "filters" not in settings:
        settings["filters"] = {}
    
    current = settings["filters"].get(media_type, False)
    settings["filters"][media_type] = not current
    set_media_filter_settings(chat_id, settings)
    
    return not current


def toggle_media_filters_enabled(chat_id: int) -> bool:
    """Включает/выключает все медиа-фильтры"""
    settings = get_media_filter_settings(chat_id)
    settings["enabled"] = not settings.get("enabled", False)
    set_media_filter_settings(chat_id, settings)
    return settings["enabled"]


def set_filter_action(chat_id: int, action: str):
    """Устанавливает действие при нарушении"""
    settings = get_media_filter_settings(chat_id)
    settings["action"] = action
    set_media_filter_settings(chat_id, settings)


def check_media_filter(update: Update, context: CallbackContext):
    """Проверяет сообщение на запрещённые медиа"""
    if not update.effective_message:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    
    # Только в группах
    if chat.type == "private":
        return
    
    # Пропускаем админов
    try:
        member = chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return
    except:
        pass
    
    settings = get_media_filter_settings(chat.id)
    
    if not settings.get("enabled", False):
        return
    
    filters = settings.get("filters", {})
    action = settings.get("action", "delete")
    
    # Проверяем каждый тип медиа
    violated_type = None
    
    for media_type, is_blocked in filters.items():
        if not is_blocked:
            continue
        
        media_info = MEDIA_TYPES.get(media_type)
        if not media_info:
            continue
        
        # Проверяем, соответствует ли сообщение фильтру
        media_filter = media_info.get("filter")
        matched = False
        
        # Если есть фильтр - используем его
        if media_filter is not None:
            try:
                matched = media_filter.check_update(update)
            except:
                pass
        
        # Альтернативная/ручная проверка
        if not matched:
            if media_type == "voice" and msg.voice:
                matched = True
            elif media_type == "video_note" and msg.video_note:
                matched = True
            elif media_type == "sticker" and msg.sticker:
                matched = True
            elif media_type == "animation" and msg.animation:
                matched = True
            elif media_type == "photo" and msg.photo:
                matched = True
            elif media_type == "video" and msg.video:
                matched = True
            elif media_type == "document" and msg.document and not msg.animation:
                matched = True
            elif media_type == "audio" and msg.audio:
                matched = True
            elif media_type == "forward" and msg.forward_date:
                matched = True
            elif media_type == "contact" and msg.contact:
                matched = True
            elif media_type == "location" and (msg.location or msg.venue):
                matched = True
            elif media_type == "poll" and msg.poll:
                matched = True
            elif media_type == "game" and msg.game:
                matched = True
            elif media_type == "inline" and msg.via_bot:
                matched = True
            elif media_type == "url" and msg.entities:
                for ent in msg.entities:
                    if ent.type in ("url", "text_link"):
                        matched = True
                        break
        
        if matched:
            violated_type = media_type
            break
    
    if not violated_type:
        return
    
    # Выполняем действие
    type_name = MEDIA_TYPES[violated_type]["name"]
    
    # Удаляем сообщение
    try:
        msg.delete()
    except BadRequest:
        pass
    
    # Дополнительное действие
    if action == "warn":
        try:
            from MitaHelper.modules.warns import warn_user
            warn_user(chat.id, user.id, f"Запрещённый контент: {type_name}")
        except:
            pass
        
        try:
            context.bot.send_message(
                chat.id,
                f"⚠️ {user.first_name}, в этом чате запрещены {type_name.lower()}!\nВам выдан варн.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    elif action == "mute":
        try:
            from datetime import datetime, timedelta
            from telegram import ChatPermissions
            
            until_date = datetime.utcnow() + timedelta(hours=1)
            context.bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            context.bot.send_message(
                chat.id,
                f"🔇 {user.first_name} замучен на 1 час за {type_name.lower()}!",
            )
        except BadRequest as e:
            LOGGER.warning(f"Не удалось замутить: {e}")
    
    elif action == "kick":
        try:
            context.bot.ban_chat_member(chat.id, user.id)
            context.bot.unban_chat_member(chat.id, user.id)
            context.bot.send_message(
                chat.id,
                f"👢 {user.first_name} кикнут за {type_name.lower()}!",
            )
        except BadRequest as e:
            LOGGER.warning(f"Не удалось кикнуть: {e}")
    
    else:  # delete only
        pass  # Сообщение уже удалено


# Регистрация обработчика для всех типов медиа
MEDIA_FILTER_HANDLER = MessageHandler(
    Filters.chat_type.groups & (
        Filters.voice | Filters.video_note | Filters.sticker | 
        Filters.animation | Filters.photo | Filters.video |
        Filters.document | Filters.audio | Filters.forwarded |
        Filters.contact | Filters.location | Filters.poll |
        Filters.game |
        Filters.entity("url") | Filters.entity("text_link")
    ),
    check_media_filter,
    run_async=True
)

dispatcher.add_handler(MEDIA_FILTER_HANDLER, group=5)


__mod_name__ = "🚫 Медиа-фильтры"

__help__ = """
*Медиа-фильтры:*

Запрет определённых типов контента в чате.

*Можно запретить:*
• 🎤 Голосовые сообщения
• 🔵 Видеокружки
• 😀 Стикеры
• 🎬 GIF анимации
• 🖼 Фотографии
• 🎥 Видео
• 📎 Документы/файлы
• 🎵 Аудио/музыка
• ↩️ Пересланные сообщения
• 🔗 Ссылки
• 👤 Контакты
• 📍 Геолокации
• 📊 Опросы
• 🎮 Игры
• 🤖 Inline-боты

*Действия при нарушении:*
• Удалить сообщение
• Удалить + Варн
• Удалить + Мут на 1 час
• Удалить + Кик

*Настройка:*
/config → Выберите чат → 🚫 Медиа-фильтры
"""
