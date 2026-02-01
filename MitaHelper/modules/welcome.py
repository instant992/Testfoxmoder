# -*- coding: utf-8 -*-
"""
Модуль приветствий - приветствия и прощания
"""

import html
import random
from datetime import datetime

from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from MitaHelper import dispatcher, LOGGER
from MitaHelper.modules.helper_funcs.chat_status import (
    is_user_ban_protected,
    user_admin,
)
from MitaHelper.modules.helper_funcs.topics import get_thread_id

# Импорт логов
try:
    from MitaHelper.modules.logs import log_join, log_leave
except ImportError:
    log_join = None
    log_leave = None


# Стандартные приветствия
DEFAULT_WELCOME = """
👋 <b>Добро пожаловать</b>, {first}!

Добро пожаловать в <b>{chatname}</b>!
"""

DEFAULT_GOODBYE = """
👋 До свидания, {first}!
"""

# Рандомные приветствия
RANDOM_WELCOMES = [
    "👋 Привет, {first}! Добро пожаловать в {chatname}!",
    "🎉 {first} присоединился к чату!",
    "👋 Здравствуй, {first}! Рады тебя видеть!",
    "🌟 Встречайте нового участника: {first}!",
    "✨ {first} теперь с нами!",
    "👋 Добро пожаловать в наш уютный чат, {first}!",
    "🎊 У нас пополнение! Привет, {first}!",
]

# Хранилище настроек
welcome_settings = {}
goodbye_settings = {}
lockdown_settings = {}  # {chat_id: {"enabled": True/False, "reason": "..."}}

# Загрузка настроек из БД
try:
    from MitaHelper.modules.database import load_welcome_settings, save_welcome_settings
    _loaded = load_welcome_settings()
    if _loaded:
        # Разделяем настройки
        for chat_id, data in _loaded.items():
            if "welcome" in data:
                welcome_settings[chat_id] = data["welcome"]
            if "goodbye" in data:
                goodbye_settings[chat_id] = data["goodbye"]
            if "lockdown" in data:
                lockdown_settings[chat_id] = data["lockdown"]
        LOGGER.info(f"Загружены настройки приветствий для {len(welcome_settings)} чатов")
except Exception as e:
    LOGGER.warning(f"Не удалось загрузить настройки приветствий: {e}")
    save_welcome_settings = None


def _save_all_welcome_settings():
    """Сохраняет все настройки приветствий в БД"""
    if save_welcome_settings:
        data = {}
        all_chats = set(welcome_settings.keys()) | set(goodbye_settings.keys()) | set(lockdown_settings.keys())
        for chat_id in all_chats:
            data[chat_id] = {}
            if chat_id in welcome_settings:
                data[chat_id]["welcome"] = welcome_settings[chat_id]
            if chat_id in goodbye_settings:
                data[chat_id]["goodbye"] = goodbye_settings[chat_id]
            if chat_id in lockdown_settings:
                data[chat_id]["lockdown"] = lockdown_settings[chat_id]
        save_welcome_settings(data)


def get_lockdown_settings(chat_id):
    """Получает настройки режима ЧС (lockdown) для чата"""
    return lockdown_settings.get(chat_id, {
        "enabled": False,
        "reason": "Спам-атака",
    })


def set_lockdown_settings(chat_id, settings):
    """Сохраняет настройки режима ЧС"""
    lockdown_settings[chat_id] = settings
    _save_all_welcome_settings()


def is_lockdown_enabled(chat_id):
    """Проверяет, включён ли режим ЧС"""
    return lockdown_settings.get(chat_id, {}).get("enabled", False)


def get_welcome_settings(chat_id):
    """Получает настройки приветствий для чата"""
    return welcome_settings.get(chat_id, {
        "enabled": True,
        "text": DEFAULT_WELCOME,
        "media": None,
        "clean": False,
        "clean_service": False,
        "delete_after": 0,  # 0 = не удалять, иначе секунды
        "buttons": [],  # [{text: "Название", url: "https://..."}, ...]
    })


def set_welcome_settings(chat_id, settings):
    """Сохраняет настройки приветствий для чата"""
    welcome_settings[chat_id] = settings
    _save_all_welcome_settings()


def get_goodbye_settings(chat_id):
    """Получает настройки прощаний для чата"""
    return goodbye_settings.get(chat_id, {
        "enabled": True,
        "text": DEFAULT_GOODBYE,
    })


def format_welcome(text, user, chat):
    """Форматирует текст приветствия с поддержкой HTML"""
    first = html.escape(user.first_name)
    last = html.escape(user.last_name or "")
    fullname = html.escape(f"{user.first_name} {user.last_name}" if user.last_name else user.first_name)
    username = f"@{user.username}" if user.username else mention_html(user.id, first)
    mention = mention_html(user.id, first)
    chatname = html.escape(chat.title)
    user_id = user.id
    
    return text.format(
        first=first,
        last=last,
        fullname=fullname,
        username=username,
        mention=mention,
        chatname=chatname,
        id=user_id,
    )


def new_member(update: Update, context: CallbackContext):
    """Обрабатывает новых участников чата"""
    chat = update.effective_chat
    msg = update.effective_message
    
    settings = get_welcome_settings(chat.id)
    
    if not settings["enabled"]:
        return
    
    # Если включена капча, не отправляем приветствие здесь
    # Приветствие будет после прохождения капчи
    try:
        from MitaHelper.modules.captcha import get_captcha_settings
        captcha_settings = get_captcha_settings(chat.id)
        if captcha_settings.get("enabled", False):
            return
    except ImportError:
        pass
    
    # Удаляем сервисное сообщение если нужно
    if settings.get("clean_service"):
        try:
            msg.delete()
        except BadRequest:
            pass
    
    # Получаем ID топика
    thread_id = get_thread_id(msg)
    
    for new_mem in msg.new_chat_members:
        # Пропускаем ботов
        if new_mem.is_bot:
            continue
        
        # ПРОВЕРКА РЕЖИМА ЧС (LOCKDOWN)
        if is_lockdown_enabled(chat.id):
            lockdown = get_lockdown_settings(chat.id)
            reason = lockdown.get("reason", "Режим ЧС")
            try:
                context.bot.ban_chat_member(chat.id, new_mem.id)
                LOGGER.info(f"[LOCKDOWN] Забанен {new_mem.id} в чате {chat.id}")
            except Exception as e:
                LOGGER.warning(f"[LOCKDOWN] Не удалось забанить {new_mem.id}: {e}")
            continue  # Не отправляем приветствие
        
        # Логируем вход
        if log_join:
            log_join(context.bot, chat, new_mem)
        
        # Пропускаем самого бота
        if new_mem.id == context.bot.id:
            send_kwargs = {
                "chat_id": chat.id,
                "text": "👋 Спасибо, что добавили меня!\n"
                        "Напишите /help для списка команд.",
            }
            if thread_id:
                send_kwargs["message_thread_id"] = thread_id
            context.bot.send_message(**send_kwargs)
            continue
        
        # Форматируем и отправляем приветствие
        welcome_text = format_welcome(settings["text"], new_mem, chat)
        
        # Создаём клавиатуру с кнопками если есть
        reply_markup = None
        buttons = settings.get("buttons", [])
        if buttons:
            keyboard = []
            row = []
            for btn in buttons:
                # Проверяем формат кнопки
                if isinstance(btn, dict) and "text" in btn and "url" in btn:
                    btn_text = btn["text"].strip()
                    btn_url = btn["url"].strip()
                    # Очищаем URL от переносов строк и лишних символов
                    btn_url = btn_url.split('\n')[0].split()[0]
                    # Валидируем URL
                    if btn_url.startswith(("http://", "https://", "tg://")):
                        row.append(InlineKeyboardButton(btn_text, url=btn_url))
                        # По 2 кнопки в ряд
                        if len(row) == 2:
                            keyboard.append(row)
                            row = []
            if row:
                keyboard.append(row)
            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            if settings.get("media"):
                # Отправляем с медиа
                sent_msg = None
            else:
                # Отправляем с учётом топика
                send_kwargs = {
                    "text": welcome_text,
                    "parse_mode": ParseMode.HTML,
                    "disable_web_page_preview": True,
                }
                if reply_markup:
                    send_kwargs["reply_markup"] = reply_markup
                if thread_id:
                    # Для форума используем send_message с thread_id
                    send_kwargs["chat_id"] = chat.id
                    send_kwargs["message_thread_id"] = thread_id
                    sent_msg = context.bot.send_message(**send_kwargs)
                else:
                    sent_msg = msg.reply_text(**send_kwargs)
            
            # Автоудаление приветствия
            delete_after = settings.get("delete_after", 0)
            if delete_after > 0 and sent_msg:
                context.job_queue.run_once(
                    delete_welcome_message,
                    delete_after,
                    context={"chat_id": chat.id, "message_id": sent_msg.message_id},
                    name=f"del_welcome_{sent_msg.message_id}"
                )
                
        except BadRequest as e:
            LOGGER.warning(f"Ошибка отправки приветствия: {e}")
            # Отправляем без форматирования
            msg.reply_text(
                f"👋 Добро пожаловать, {new_mem.first_name}!",
            )


def delete_welcome_message(context: CallbackContext):
    """Удаляет приветственное сообщение по таймеру"""
    job_data = context.job.context
    try:
        context.bot.delete_message(job_data["chat_id"], job_data["message_id"])
    except BadRequest:
        pass


def left_member(update: Update, context: CallbackContext):
    """Обрабатывает ушедших участников"""
    chat = update.effective_chat
    left_user = update.effective_message.left_chat_member
    
    # Логируем выход
    if log_leave and left_user:
        log_leave(context.bot, chat, left_user)
    
    # Прощания отключены
    pass


@user_admin
def welcome(update: Update, context: CallbackContext):
    """Команда /welcome - показать/изменить приветствие"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if not args:
        settings = get_welcome_settings(chat.id)
        status = "✅ Включено" if settings["enabled"] else "❌ Выключено"
        
        msg.reply_text(
            f"*Настройки приветствия:*\n\n"
            f"Статус: {status}\n\n"
            f"*Текущий текст:*\n{settings['text']}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    if args[0].lower() in ("on", "yes", "вкл", "да"):
        if chat.id not in welcome_settings:
            welcome_settings[chat.id] = get_welcome_settings(chat.id)
        welcome_settings[chat.id]["enabled"] = True
        msg.reply_text("✅ Приветствия включены!")
        
    elif args[0].lower() in ("off", "no", "выкл", "нет"):
        if chat.id not in welcome_settings:
            welcome_settings[chat.id] = get_welcome_settings(chat.id)
        welcome_settings[chat.id]["enabled"] = False
        msg.reply_text("❌ Приветствия выключены!")


@user_admin
def set_welcome(update: Update, context: CallbackContext):
    """Устанавливает текст приветствия"""
    chat = update.effective_chat
    msg = update.effective_message
    
    # Получаем текст
    if msg.reply_to_message:
        text = msg.reply_to_message.text or msg.reply_to_message.caption
    else:
        text = msg.text.split(None, 1)
        text = text[1] if len(text) > 1 else None
    
    if not text:
        msg.reply_text(
            "❌ Укажите текст приветствия или ответьте на сообщение.\n\n"
            "*Доступные переменные:*\n"
            "• `{first}` — имя\n"
            "• `{last}` — фамилия\n"
            "• `{fullname}` — полное имя\n"
            "• `{username}` — @username\n"
            "• `{mention}` — упоминание\n"
            "• `{chatname}` — название чата\n"
            "• `{id}` — ID пользователя",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    if chat.id not in welcome_settings:
        welcome_settings[chat.id] = get_welcome_settings(chat.id)
    
    welcome_settings[chat.id]["text"] = text
    msg.reply_text("✅ Приветствие установлено!")


@user_admin
def reset_welcome(update: Update, context: CallbackContext):
    """Сбрасывает приветствие на стандартное"""
    chat = update.effective_chat
    msg = update.effective_message
    
    if chat.id in welcome_settings:
        welcome_settings[chat.id]["text"] = DEFAULT_WELCOME
    
    msg.reply_text("✅ Приветствие сброшено на стандартное!")


@user_admin
def goodbye(update: Update, context: CallbackContext):
    """Команда /goodbye - показать/изменить прощание"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if not args:
        settings = get_goodbye_settings(chat.id)
        status = "✅ Включено" if settings["enabled"] else "❌ Выключено"
        
        msg.reply_text(
            f"*Настройки прощания:*\n\n"
            f"Статус: {status}\n\n"
            f"*Текущий текст:*\n{settings['text']}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    if args[0].lower() in ("on", "yes", "вкл", "да"):
        if chat.id not in goodbye_settings:
            goodbye_settings[chat.id] = get_goodbye_settings(chat.id)
        goodbye_settings[chat.id]["enabled"] = True
        msg.reply_text("✅ Прощания включены!")
        
    elif args[0].lower() in ("off", "no", "выкл", "нет"):
        if chat.id not in goodbye_settings:
            goodbye_settings[chat.id] = get_goodbye_settings(chat.id)
        goodbye_settings[chat.id]["enabled"] = False
        msg.reply_text("❌ Прощания выключены!")


@user_admin
def set_goodbye(update: Update, context: CallbackContext):
    """Устанавливает текст прощания"""
    chat = update.effective_chat
    msg = update.effective_message
    
    if msg.reply_to_message:
        text = msg.reply_to_message.text or msg.reply_to_message.caption
    else:
        text = msg.text.split(None, 1)
        text = text[1] if len(text) > 1 else None
    
    if not text:
        msg.reply_text("❌ Укажите текст прощания.")
        return
    
    if chat.id not in goodbye_settings:
        goodbye_settings[chat.id] = get_goodbye_settings(chat.id)
    
    goodbye_settings[chat.id]["text"] = text
    msg.reply_text("✅ Прощание установлено!")


@user_admin
def cleanservice(update: Update, context: CallbackContext):
    """Включает/выключает удаление сервисных сообщений"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if not args:
        settings = get_welcome_settings(chat.id)
        status = "✅ Включено" if settings.get("clean_service") else "❌ Выключено"
        msg.reply_text(f"Удаление сервисных сообщений: {status}")
        return
    
    if args[0].lower() in ("on", "yes", "вкл", "да"):
        if chat.id not in welcome_settings:
            welcome_settings[chat.id] = get_welcome_settings(chat.id)
        welcome_settings[chat.id]["clean_service"] = True
        msg.reply_text("✅ Буду удалять сервисные сообщения!")
        
    elif args[0].lower() in ("off", "no", "выкл", "нет"):
        if chat.id not in welcome_settings:
            welcome_settings[chat.id] = get_welcome_settings(chat.id)
        welcome_settings[chat.id]["clean_service"] = False
        msg.reply_text("❌ Не буду удалять сервисные сообщения.")


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

NEW_MEMBER_HANDLER = MessageHandler(
    Filters.status_update.new_chat_members, new_member, run_async=True
)
LEFT_MEMBER_HANDLER = MessageHandler(
    Filters.status_update.left_chat_member, left_member, run_async=True
)
WELCOME_HANDLER = CommandHandler("welcome", welcome, run_async=True)
SET_WELCOME_HANDLER = CommandHandler("setwelcome", set_welcome, run_async=True)
RESET_WELCOME_HANDLER = CommandHandler("resetwelcome", reset_welcome, run_async=True)
GOODBYE_HANDLER = CommandHandler("goodbye", goodbye, run_async=True)
SET_GOODBYE_HANDLER = CommandHandler("setgoodbye", set_goodbye, run_async=True)
CLEANSERVICE_HANDLER = CommandHandler("cleanservice", cleanservice, run_async=True)

dispatcher.add_handler(NEW_MEMBER_HANDLER)
dispatcher.add_handler(LEFT_MEMBER_HANDLER)
dispatcher.add_handler(WELCOME_HANDLER)
dispatcher.add_handler(SET_WELCOME_HANDLER)
dispatcher.add_handler(RESET_WELCOME_HANDLER)
dispatcher.add_handler(GOODBYE_HANDLER)
dispatcher.add_handler(SET_GOODBYE_HANDLER)
dispatcher.add_handler(CLEANSERVICE_HANDLER)


# ═══════════════════════════════════════════════════════════════
#                      РЕЖИМ ЧС (LOCKDOWN)
# ═══════════════════════════════════════════════════════════════

@user_admin
def lockdown_cmd(update: Update, context: CallbackContext):
    """Включает режим ЧС - все новые участники банятся"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    reason = " ".join(args) if args else "Спам-атака"
    
    settings = get_lockdown_settings(chat.id)
    settings["enabled"] = True
    settings["reason"] = reason
    set_lockdown_settings(chat.id, settings)
    
    msg.reply_text(
        f"🔒 *РЕЖИМ ЧС АКТИВИРОВАН*\n\n"
        f"⚠️ Все новые участники будут *автоматически забанены*!\n\n"
        f"📝 Причина: `{reason}`\n\n"
        f"Для отключения используйте /unlock",
        parse_mode=ParseMode.MARKDOWN
    )
    LOGGER.info(f"[LOCKDOWN] Включён в чате {chat.id} ({chat.title})")


@user_admin
def unlock_cmd(update: Update, context: CallbackContext):
    """Выключает режим ЧС"""
    chat = update.effective_chat
    msg = update.effective_message
    
    settings = get_lockdown_settings(chat.id)
    
    if not settings.get("enabled", False):
        msg.reply_text("ℹ️ Режим ЧС не был активирован.")
        return
    
    settings["enabled"] = False
    set_lockdown_settings(chat.id, settings)
    
    msg.reply_text(
        "🔓 *Режим ЧС отключён*\n\n"
        "✅ Новые участники больше не будут автоматически баниться.",
        parse_mode=ParseMode.MARKDOWN
    )
    LOGGER.info(f"[LOCKDOWN] Выключен в чате {chat.id} ({chat.title})")


@user_admin
def lockdown_status_cmd(update: Update, context: CallbackContext):
    """Показывает статус режима ЧС"""
    chat = update.effective_chat
    msg = update.effective_message
    
    settings = get_lockdown_settings(chat.id)
    enabled = settings.get("enabled", False)
    
    if enabled:
        reason = settings.get("reason", "Не указана")
        msg.reply_text(
            f"🔒 *Режим ЧС: АКТИВЕН*\n\n"
            f"📝 Причина: `{reason}`\n\n"
            f"⚠️ Все новые участники банятся автоматически.\n"
            f"Для отключения: /unlock",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        msg.reply_text(
            "🔓 *Режим ЧС: выключен*\n\n"
            "Для включения: /lockdown [причина]",
            parse_mode=ParseMode.MARKDOWN
        )


LOCKDOWN_HANDLER = CommandHandler("lockdown", lockdown_cmd, filters=Filters.chat_type.groups, run_async=True)
UNLOCK_HANDLER = CommandHandler("unlock", unlock_cmd, filters=Filters.chat_type.groups, run_async=True)
LOCKSTATUS_HANDLER = CommandHandler("lockstatus", lockdown_status_cmd, filters=Filters.chat_type.groups, run_async=True)

dispatcher.add_handler(LOCKDOWN_HANDLER)
dispatcher.add_handler(UNLOCK_HANDLER)
dispatcher.add_handler(LOCKSTATUS_HANDLER)


__mod_name__ = "👋 Приветствия"

__help__ = """
*Настройка приветствий и прощаний:*

👋 *Приветствия:*
• /welcome — показать настройки приветствия
• /welcome `on/off` — включить/выключить
• /setwelcome `<текст>` — установить текст
• /resetwelcome — сбросить на стандартное

👋 *Прощания:*
• /goodbye — показать настройки прощания
• /goodbye `on/off` — включить/выключить
• /setgoodbye `<текст>` — установить текст

🧹 *Очистка:*
• /cleanservice `on/off` — удалять сервисные сообщения

🔒 *Режим ЧС (защита от спам-атак):*
• /lockdown [причина] — включить режим ЧС
• /unlock — выключить режим ЧС
• /lockstatus — статус режима

_При включённом режиме ЧС все новые участники автоматически банятся!_

📝 *Переменные для текста:*
• `{first}` — имя пользователя
• `{last}` — фамилия
• `{fullname}` — полное имя
• `{username}` — @username
• `{mention}` — упоминание (кликабельное)
• `{chatname}` — название чата
• `{id}` — ID пользователя

✨ *Форматирование (HTML):*
• `<b>жирный</b>` — *жирный*
• `<i>курсив</i>` — _курсив_
• `<u>подчёркнутый</u>` — подчёркнутый
• `<s>зачёркнутый</s>` — зачёркнутый
• `<code>код</code>` — `код`
• `<a href="URL">текст</a>` — ссылка

*Пример:*
`/setwelcome <b>Привет</b>, {first}! Добро пожаловать в <i>{chatname}</i>!`
"""
