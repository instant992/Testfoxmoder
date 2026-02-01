# -*- coding: utf-8 -*-
"""
Модуль фильтров - автоматические ответы на ключевые слова
"""

import re
import random
from telegram import ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
)

from MitaHelper import dispatcher, LOGGER
from MitaHelper.modules.helper_funcs.chat_status import user_admin


# Хранилище фильтров
filters_storage = {}

# Загрузка из БД
try:
    from MitaHelper.modules.database import load_filters_settings, save_filters_settings
    _loaded = load_filters_settings()
    if _loaded:
        filters_storage = _loaded
        LOGGER.info(f"Загружены фильтры для {len(filters_storage)} чатов")
except Exception as e:
    LOGGER.warning(f"Не удалось загрузить фильтры: {e}")
    save_filters_settings = None


def _save_filters_to_db():
    """Сохраняет фильтры в БД"""
    if save_filters_settings:
        save_filters_settings(filters_storage)


def get_filter(chat_id, keyword):
    """Получает фильтр по ключевому слову"""
    chat_filters = filters_storage.get(chat_id, {})
    return chat_filters.get(keyword.lower())


def save_filter(chat_id, keyword, content, media_type=None, media_id=None):
    """Сохраняет фильтр"""
    if chat_id not in filters_storage:
        filters_storage[chat_id] = {}
    
    filters_storage[chat_id][keyword.lower()] = {
        "keyword": keyword,
        "content": content,
        "media_type": media_type,
        "media_id": media_id,
    }
    _save_filters_to_db()


def delete_filter(chat_id, keyword):
    """Удаляет фильтр"""
    if chat_id in filters_storage:
        if keyword.lower() in filters_storage[chat_id]:
            del filters_storage[chat_id][keyword.lower()]
            _save_filters_to_db()
            return True
    return False


def get_all_filters(chat_id):
    """Получает все фильтры чата"""
    return filters_storage.get(chat_id, {})


@user_admin
def add_filter(update: Update, context: CallbackContext):
    """Добавляет новый фильтр"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if not args:
        msg.reply_text(
            "❌ Использование: `/filter <слово> <ответ>`\n"
            "Или ответьте на сообщение: `/filter <слово>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    keyword = args[0]
    
    # Получаем контент
    if msg.reply_to_message:
        reply = msg.reply_to_message
        content = reply.text or reply.caption or ""
        
        # Определяем тип медиа
        media_type = None
        media_id = None
        
        if reply.photo:
            media_type = "photo"
            media_id = reply.photo[-1].file_id
        elif reply.video:
            media_type = "video"
            media_id = reply.video.file_id
        elif reply.document:
            media_type = "document"
            media_id = reply.document.file_id
        elif reply.audio:
            media_type = "audio"
            media_id = reply.audio.file_id
        elif reply.sticker:
            media_type = "sticker"
            media_id = reply.sticker.file_id
    else:
        content = " ".join(args[1:])
        media_type = None
        media_id = None
    
    if not content and not media_id:
        msg.reply_text("❌ Укажите ответ на ключевое слово или ответьте на сообщение.")
        return
    
    save_filter(chat.id, keyword, content, media_type, media_id)
    msg.reply_text(f"✅ Фильтр `{keyword}` сохранён!")


@user_admin
def stop_filter(update: Update, context: CallbackContext):
    """Удаляет фильтр"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if not args:
        msg.reply_text("❌ Укажите ключевое слово для удаления.")
        return
    
    keyword = args[0]
    
    if delete_filter(chat.id, keyword):
        msg.reply_text(f"✅ Фильтр `{keyword}` удалён!")
    else:
        msg.reply_text(f"❌ Фильтр `{keyword}` не найден.")


def filters_list(update: Update, context: CallbackContext):
    """Показывает список фильтров"""
    chat = update.effective_chat
    msg = update.effective_message
    
    all_filters = get_all_filters(chat.id)
    
    if not all_filters:
        msg.reply_text("🔍 В этом чате нет фильтров.")
        return
    
    text = f"🔍 *Фильтры в чате* `{chat.title}`:\n\n"
    
    for keyword in sorted(all_filters.keys()):
        text += f"• `{keyword}`\n"
    
    text += f"\n_Всего фильтров: {len(all_filters)}_"
    
    msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def schedule_delete(context: CallbackContext):
    """Удаляет сообщение по расписанию"""
    job = context.job
    chat_id = job.context["chat_id"]
    message_id = job.context["message_id"]
    
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        LOGGER.warning(f"Не удалось удалить сообщение фильтра: {e}")


def reply_filter(update: Update, context: CallbackContext):
    """Обрабатывает сообщения и отвечает на фильтры"""
    chat = update.effective_chat
    msg = update.effective_message
    
    if not msg.text:
        return
    
    text_lower = msg.text.lower()
    
    # Получаем время автоудаления
    try:
        from MitaHelper.modules.config_panel import get_filter_autodelete
        autodelete_minutes = get_filter_autodelete(chat.id)
    except ImportError:
        autodelete_minutes = 0
    
    sent_msg = None
    
    # Сначала проверяем мультифильтры
    try:
        from MitaHelper.modules.config_panel import get_multi_filters
        multi = get_multi_filters(chat.id)
        
        for keyword, responses in multi.items():
            pattern = r'(?:^|[^\w])' + re.escape(keyword) + r'(?:[^\w]|$)'
            if re.search(pattern, text_lower):
                # Выбираем случайный ответ
                response = random.choice(responses)
                try:
                    if response["type"] == "sticker":
                        sent_msg = msg.reply_sticker(response["file_id"])
                    elif response["type"] == "animation":
                        sent_msg = msg.reply_animation(response["file_id"], caption=response.get("caption") or None)
                    elif response["type"] == "photo":
                        sent_msg = msg.reply_photo(response["file_id"], caption=response.get("caption") or None)
                    elif response["type"] == "text":
                        sent_msg = msg.reply_text(response["content"])
                    
                    # Планируем удаление
                    if sent_msg and autodelete_minutes > 0:
                        context.job_queue.run_once(
                            schedule_delete,
                            autodelete_minutes * 60,
                            context={"chat_id": chat.id, "message_id": sent_msg.message_id}
                        )
                except BadRequest as e:
                    LOGGER.warning(f"Ошибка отправки мультифильтра: {e}")
                return
    except ImportError:
        pass
    
    # Затем обычные фильтры
    all_filters = get_all_filters(chat.id)
    if not all_filters:
        return
    
    for keyword, filt in all_filters.items():
        # Проверяем, содержит ли сообщение ключевое слово
        pattern = r'(?:^|[^\w])' + re.escape(keyword) + r'(?:[^\w]|$)'
        if re.search(pattern, text_lower):
            try:
                if filt["media_type"] == "animation":
                    sent_msg = msg.reply_animation(filt["media_id"], caption=filt["content"] or None)
                elif filt["media_type"] == "photo":
                    sent_msg = msg.reply_photo(filt["media_id"], caption=filt["content"] or None)
                elif filt["media_type"] == "video":
                    sent_msg = msg.reply_video(filt["media_id"], caption=filt["content"] or None)
                elif filt["media_type"] == "document":
                    sent_msg = msg.reply_document(filt["media_id"], caption=filt["content"] or None)
                elif filt["media_type"] == "audio":
                    sent_msg = msg.reply_audio(filt["media_id"], caption=filt["content"] or None)
                elif filt["media_type"] == "sticker":
                    sent_msg = msg.reply_sticker(filt["media_id"])
                else:
                    sent_msg = msg.reply_text(
                        filt["content"],
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                    )
                
                # Планируем удаление
                if sent_msg and autodelete_minutes > 0:
                    context.job_queue.run_once(
                        schedule_delete,
                        autodelete_minutes * 60,
                        context={"chat_id": chat.id, "message_id": sent_msg.message_id}
                    )
            except BadRequest as e:
                LOGGER.warning(f"Ошибка отправки фильтра: {e}")
            
            # Срабатывает только первый фильтр
            return


@user_admin
def clear_all_filters(update: Update, context: CallbackContext):
    """Удаляет все фильтры чата"""
    chat = update.effective_chat
    msg = update.effective_message
    
    if chat.id in filters_storage:
        count = len(filters_storage[chat.id])
        filters_storage[chat.id] = {}
        msg.reply_text(f"✅ Удалено {count} фильтров!")
    else:
        msg.reply_text("🔍 В этом чате нет фильтров.")


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

FILTER_HANDLER = CommandHandler("filter", add_filter, run_async=True)
STOP_HANDLER = CommandHandler(["stop", "removefilter"], stop_filter, run_async=True)
LIST_HANDLER = CommandHandler("filters", filters_list, run_async=True)
CLEARALL_HANDLER = CommandHandler("stopall", clear_all_filters, run_async=True)
REPLY_HANDLER = MessageHandler(
    Filters.text & Filters.chat_type.groups & ~Filters.command, 
    reply_filter, 
    run_async=True
)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CLEARALL_HANDLER)
dispatcher.add_handler(REPLY_HANDLER, group=69)


__mod_name__ = "🔍 Фильтры"

__help__ = """
*Автоматические ответы на ключевые слова:*

🔍 *Команды:*
• /filter `<слово>` `<ответ>` — добавить фильтр
• /filter `<слово>` (ответом) — добавить фильтр
• /filters или /фильтры — список фильтров
• /stop `<слово>` — удалить фильтр
• /stopall — удалить все фильтры

📎 *Поддерживаемые типы:*
• Текст (с Markdown)
• Фото
• Видео
• Документы
• Стикеры

📝 *Примеры:*
• `/filter привет Привет! Как дела?`
• `/filter помощь` (ответом на сообщение с инструкцией)

*Как работает:*
Когда кто-то напишет сообщение, содержащее ключевое слово, бот автоматически ответит заданным сообщением.
"""
