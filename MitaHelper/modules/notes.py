# -*- coding: utf-8 -*-
"""
Модуль заметок - сохранение и получение заметок с поддержкой кнопок
"""

import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)

from MitaHelper import dispatcher, LOGGER
from MitaHelper.modules.helper_funcs.chat_status import user_admin


# Хранилище заметок
notes_storage = {}

# Загрузка из БД
try:
    from MitaHelper.modules.database import load_notes_settings, save_notes_settings
    _loaded = load_notes_settings()
    if _loaded:
        notes_storage = _loaded
        LOGGER.info(f"Загружены заметки для {len(notes_storage)} чатов")
except Exception as e:
    LOGGER.warning(f"Не удалось загрузить заметки: {e}")
    save_notes_settings = None


def _save_notes_to_db():
    """Сохраняет заметки в БД"""
    if save_notes_settings:
        save_notes_settings(notes_storage)


def parse_note_buttons(text):
    """
    Парсит текст заметки и извлекает кнопки.
    Формат кнопок: [текст кнопки](url)
    Возвращает: (очищенный_текст, список_кнопок)
    """
    buttons = []
    # Паттерн для кнопок: [текст](url)
    button_pattern = r'\[([^\]]+)\]\((https?://[^\s\)]+|tg://[^\s\)]+)\)'
    
    # Находим все кнопки
    matches = re.findall(button_pattern, text)
    for btn_text, btn_url in matches:
        buttons.append({
            "text": btn_text.strip(),
            "url": btn_url.strip()
        })
    
    # Удаляем кнопки из текста
    clean_text = re.sub(button_pattern, '', text).strip()
    # Убираем лишние пустые строки
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    
    return clean_text, buttons


def build_note_keyboard(buttons):
    """Создаёт клавиатуру из списка кнопок"""
    if not buttons:
        return None
    
    keyboard = []
    row = []
    for btn in buttons:
        if isinstance(btn, dict) and "text" in btn and "url" in btn:
            btn_text = btn["text"].strip()
            btn_url = btn["url"].strip()
            # Валидируем URL
            if btn_url.startswith(("http://", "https://", "tg://")):
                row.append(InlineKeyboardButton(btn_text, url=btn_url))
                # По 2 кнопки в ряд
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def get_note(chat_id, note_name):
    """Получает заметку по имени"""
    chat_notes = notes_storage.get(chat_id, {})
    return chat_notes.get(note_name.lower())


def save_note(chat_id, note_name, content, media_type=None, media_id=None, buttons=None):
    """Сохраняет заметку с опциональными кнопками"""
    if chat_id not in notes_storage:
        notes_storage[chat_id] = {}
    
    # Если кнопки не переданы, парсим их из текста
    if buttons is None and content:
        content, buttons = parse_note_buttons(content)
    
    notes_storage[chat_id][note_name.lower()] = {
        "name": note_name,
        "content": content,
        "media_type": media_type,
        "media_id": media_id,
        "buttons": buttons or [],
    }
    _save_notes_to_db()


def delete_note(chat_id, note_name):
    """Удаляет заметку"""
    if chat_id in notes_storage:
        if note_name.lower() in notes_storage[chat_id]:
            del notes_storage[chat_id][note_name.lower()]
            _save_notes_to_db()
            return True
    return False


def get_all_notes(chat_id):
    """Получает все заметки чата"""
    return notes_storage.get(chat_id, {})


def get(update: Update, context: CallbackContext):
    """Получает заметку по команде #имя или /get имя"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if msg.text.startswith("#"):
        # Формат #имя_заметки
        note_name = msg.text[1:].split()[0]
    elif args:
        note_name = args[0]
    else:
        msg.reply_text("❌ Укажите имя заметки.")
        return
    
    note = get_note(chat.id, note_name)
    
    if not note:
        msg.reply_text(f"❌ Заметка `{note_name}` не найдена.")
        return
    
    # Создаём клавиатуру с кнопками если есть
    reply_markup = build_note_keyboard(note.get("buttons", []))
    
    # Отправляем заметку
    try:
        if note["media_type"] == "photo":
            msg.reply_photo(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "video":
            msg.reply_video(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "document":
            msg.reply_document(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "audio":
            msg.reply_audio(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "voice":
            msg.reply_voice(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "sticker":
            msg.reply_sticker(note["media_id"])
        else:
            msg.reply_text(
                note["content"],
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )
    except BadRequest as e:
        LOGGER.warning(f"Ошибка отправки заметки: {e}")
        msg.reply_text(note["content"], reply_markup=reply_markup)


@user_admin
def save(update: Update, context: CallbackContext):
    """Сохраняет новую заметку"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if not args:
        msg.reply_text(
            "❌ Использование: `/save <имя> <текст>`\n"
            "Или ответьте на сообщение: `/save <имя>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    note_name = args[0]
    
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
        elif reply.voice:
            media_type = "voice"
            media_id = reply.voice.file_id
        elif reply.sticker:
            media_type = "sticker"
            media_id = reply.sticker.file_id
    else:
        content = " ".join(args[1:])
        media_type = None
        media_id = None
    
    if not content and not media_id:
        msg.reply_text("❌ Укажите текст заметки или ответьте на сообщение.")
        return
    
    save_note(chat.id, note_name, content, media_type, media_id)
    msg.reply_text(f"✅ Заметка `{note_name}` сохранена!\nПолучить: `#{note_name}`")


@user_admin
def clear(update: Update, context: CallbackContext):
    """Удаляет заметку"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if not args:
        msg.reply_text("❌ Укажите имя заметки для удаления.")
        return
    
    note_name = args[0]
    
    if delete_note(chat.id, note_name):
        msg.reply_text(f"✅ Заметка `{note_name}` удалена!")
    else:
        msg.reply_text(f"❌ Заметка `{note_name}` не найдена.")


def notes_list(update: Update, context: CallbackContext):
    """Показывает список заметок"""
    chat = update.effective_chat
    msg = update.effective_message
    
    all_notes = get_all_notes(chat.id)
    
    if not all_notes:
        msg.reply_text("📝 В этом чате нет заметок.")
        return
    
    text = f"📝 *Заметки в чате* `{chat.title}`:\n\n"
    
    for note_name in sorted(all_notes.keys()):
        text += f"• `#{note_name}`\n"
    
    text += f"\n_Всего заметок: {len(all_notes)}_"
    
    msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def hash_get(update: Update, context: CallbackContext):
    """Обрабатывает сообщения с #имя_заметки"""
    msg = update.effective_message
    chat = update.effective_chat
    
    # Извлекаем имя заметки из хэштега
    match = re.match(r"^#(\w+)", msg.text)
    if not match:
        return
    
    note_name = match.group(1)
    note = get_note(chat.id, note_name)
    
    if not note:
        return
    
    # Создаём клавиатуру с кнопками если есть
    reply_markup = build_note_keyboard(note.get("buttons", []))
    
    # Отправляем заметку
    try:
        if note["media_type"] == "photo":
            msg.reply_photo(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "video":
            msg.reply_video(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "document":
            msg.reply_document(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "audio":
            msg.reply_audio(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "voice":
            msg.reply_voice(
                note["media_id"], 
                caption=note["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif note["media_type"] == "sticker":
            msg.reply_sticker(note["media_id"])
        else:
            msg.reply_text(
                note["content"],
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )
    except BadRequest as e:
        LOGGER.warning(f"Ошибка отправки заметки: {e}")
        msg.reply_text(note["content"], reply_markup=reply_markup)


@user_admin
def clear_all_notes(update: Update, context: CallbackContext):
    """Удаляет все заметки чата"""
    chat = update.effective_chat
    msg = update.effective_message
    
    if chat.id in notes_storage:
        count = len(notes_storage[chat.id])
        notes_storage[chat.id] = {}
        msg.reply_text(f"✅ Удалено {count} заметок!")
    else:
        msg.reply_text("📝 В этом чате нет заметок.")


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

GET_HANDLER = CommandHandler("get", get, run_async=True)
SAVE_HANDLER = CommandHandler("save", save, run_async=True)
CLEAR_HANDLER = CommandHandler("clear", clear, run_async=True)
NOTES_HANDLER = CommandHandler(["notes", "saved"], notes_list, run_async=True)
CLEARALL_HANDLER = CommandHandler("clearall", clear_all_notes, run_async=True)
HASH_HANDLER = MessageHandler(
    Filters.regex(r"^#\w+") & Filters.chat_type.groups, 
    hash_get, 
    run_async=True
)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(CLEAR_HANDLER)
dispatcher.add_handler(NOTES_HANDLER)
dispatcher.add_handler(CLEARALL_HANDLER)
dispatcher.add_handler(HASH_HANDLER)


__mod_name__ = "📝 Заметки"

__help__ = """
*Система заметок:*

📝 *Основные команды:*
• /save `<имя>` `<текст>` — сохранить заметку
• /save `<имя>` (ответом) — сохранить сообщение как заметку
• /get `<имя>` или `#имя` — получить заметку
• /notes или /заметки — список всех заметок
• /clear `<имя>` — удалить заметку
• /clearall — удалить все заметки

📎 *Поддерживаемые типы:*
• Текст (с Markdown)
• Фото, Видео, Документы
• Аудио, Голосовые сообщения
• Стикеры

🔘 *Кнопки со ссылками:*
Добавьте кнопки в формате Markdown:
`[Текст кнопки](https://ссылка.com)`

📝 *Примеры:*
• `/save правила Правила чата: ...`
• `/save инфо` (ответом на сообщение)
• `#правила` — быстрый вызов заметки

*Пример с кнопкой:*
`/save канал Наш канал с новостями! [Подписаться](https://t.me/channel)`
"""
