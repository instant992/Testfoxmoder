# -*- coding: utf-8 -*-
"""
Модуль удаления сервисных сообщений Telegram
"""

from telegram import Update
from telegram.ext import (
    CallbackContext,
    MessageHandler,
    Filters,
)

from MitaHelper import dispatcher, LOGGER


def delete_service_message(update: Update, context: CallbackContext):
    """Удаляет сервисные сообщения если включено"""
    chat = update.effective_chat
    msg = update.effective_message
    
    if not msg:
        return
    
    try:
        from MitaHelper.modules.config_panel import get_delete_service_messages
        
        if not get_delete_service_messages(chat.id):
            return
        
        # Для new_chat_members проверяем, включена ли капча
        # Если да - не удаляем, капча сама обработает
        if msg.new_chat_members:
            try:
                from MitaHelper.modules.captcha import get_captcha_settings
                captcha = get_captcha_settings(chat.id)
                if captcha.get("enabled"):
                    return  # Капча сама удалит если нужно
            except:
                pass
        
        msg.delete()
    except Exception as e:
        LOGGER.warning(f"Не удалось удалить сервисное сообщение: {e}")


# Фильтр для всех сервисных сообщений
SERVICE_FILTER = (
    Filters.status_update.new_chat_members |
    Filters.status_update.left_chat_member |
    Filters.status_update.new_chat_title |
    Filters.status_update.new_chat_photo |
    Filters.status_update.delete_chat_photo |
    Filters.status_update.pinned_message |
    Filters.status_update.migrate
)

# Обработчик сервисных сообщений (низкий приоритет - group=100)
service_handler = MessageHandler(
    SERVICE_FILTER,
    delete_service_message,
    run_async=True
)
dispatcher.add_handler(service_handler, group=100)


__mod_name__ = "🧹 Сервисные"

__help__ = """
*Удаление сервисных сообщений:*

Автоматически удаляет системные уведомления Telegram:
• Вступление в группу
• Выход из группы  
• Закрепление сообщений
• Изменение названия/фото группы
• И другие

*Настройка:*
Используйте /config → выберите чат → 🧹 Сервисные
"""
