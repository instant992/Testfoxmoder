# -*- coding: utf-8 -*-
"""
Панель конфигурации бота через ЛС
Централизованное управление всеми настройками чатов
"""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
)
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from MitaHelper import dispatcher, OWNER_ID, LOGGER
from MitaHelper.modules.bot_admins import is_bot_admin, get_user_role, get_bot_admins, add_bot_admin, remove_bot_admin, ROLES
from MitaHelper.modules.database import get_user_chats, is_chat_added, get_chat, add_chat_admin, is_chat_admin, reset_all_data

# Импорты настроек из других модулей
try:
    from MitaHelper.modules.welcome import (
        get_welcome_settings, set_welcome_settings,
        get_lockdown_settings, set_lockdown_settings, is_lockdown_enabled
    )
except ImportError:
    get_welcome_settings = None
    set_welcome_settings = None
    get_lockdown_settings = None
    set_lockdown_settings = None
    is_lockdown_enabled = None

try:
    from MitaHelper.modules.captcha import get_captcha_settings, set_captcha_settings, CAPTCHA_MODES
except ImportError:
    get_captcha_settings = None
    set_captcha_settings = None

try:
    from MitaHelper.modules.rules import get_rules, set_rules, clear_rules
except ImportError:
    get_rules = None
    set_rules = None
    clear_rules = None

try:
    from MitaHelper.modules.filters import get_all_filters, save_filter, delete_filter
except ImportError:
    get_all_filters = None
    save_filter = None
    delete_filter = None

try:
    from MitaHelper.modules.notes import get_all_notes, save_note, delete_note, get_note
except ImportError:
    get_all_notes = None
    save_note = None
    delete_note = None
    get_note = None

try:
    from MitaHelper.modules.logs import (
        get_log_settings, set_log_channel, remove_log_channel,
        toggle_log_event, LOG_EVENTS, is_event_enabled
    )
except ImportError:
    get_log_settings = None
    set_log_channel = None
    LOG_EVENTS = {}

try:
    from MitaHelper.modules.media_filters import (
        get_media_filter_settings, set_media_filter_settings,
        toggle_media_filter, toggle_media_filters_enabled,
        set_filter_action, MEDIA_TYPES, FILTER_ACTIONS
    )
except ImportError:
    get_media_filter_settings = None
    set_media_filter_settings = None
    MEDIA_TYPES = {}
    FILTER_ACTIONS = {}

try:
    from MitaHelper.modules.cas_ban import (
        get_cas_settings, set_cas_settings,
        toggle_cas, set_cas_action, toggle_cas_notify,
        CAS_ACTIONS, is_cas_banned
    )
except ImportError:
    get_cas_settings = None
    set_cas_settings = None
    CAS_ACTIONS = {}

# Импорт настроек антиканала
from MitaHelper.modules.database import (
    get_antichannel_settings, set_antichannel_settings,
    toggle_antichannel, is_antichannel_enabled
)


# Состояния для ConversationHandler
(SELECTING_CHAT, SELECTING_MODULE, EDITING_SETTING,
 WAITING_RULES_INPUT, WAITING_WELCOME_INPUT, WAITING_FILTER_KEYWORD, 
 WAITING_FILTER_RESPONSE, WAITING_NOTE_NAME, WAITING_NOTE_CONTENT,
 WAITING_ADMIN_ID, WAITING_MULTI_KEYWORD, WAITING_MULTI_RESPONSES,
 WAITING_LOG_CHANNEL, WAITING_WELCOME_BUTTON, WAITING_NOTE_BUTTON) = range(15)

# Текущее редактирование
user_editing = {}  # {user_id: {"chat_id": ..., "module": ..., "setting": ...}}

# Мультифильтры {chat_id: {keyword: [responses]}}
multi_filters = {}

# Настройки антифлуда
antiflood_settings = {}  # {chat_id: {"enabled": bool, "limit": int, "action": str}}

# Настройки варнов
warns_settings = {}  # {chat_id: {"limit": int, "action": str}}

# Чёрный список
blacklist_settings = {}  # {chat_id: {"enabled": bool, "words": list, "action": str}}

# Автоудаление ответов фильтров {chat_id: minutes} (0 = отключено)
filter_autodelete = {}

# Удаление сервисных сообщений {chat_id: bool}
delete_service_messages = {}

# Загрузка настроек config_panel из БД
try:
    from MitaHelper.modules.database import (
        load_antiflood_settings, save_antiflood_settings,
        load_warns_settings, save_warns_settings,
        load_blacklist_settings, save_blacklist_settings,
        load_multi_filters_settings, save_multi_filters_settings
    )
    # Загрузка antiflood
    _af = load_antiflood_settings()
    if _af:
        antiflood_settings = _af
        LOGGER.info(f"Загружены настройки антифлуда для {len(antiflood_settings)} чатов")
    # Загрузка warns
    _ws = load_warns_settings()
    if _ws:
        warns_settings = _ws
        LOGGER.info(f"Загружены настройки варнов для {len(warns_settings)} чатов")
    # Загрузка blacklist  
    _bl = load_blacklist_settings()
    if _bl:
        blacklist_settings = _bl
        LOGGER.info(f"Загружены настройки ЧС для {len(blacklist_settings)} чатов")
    # Загрузка multi_filters
    _mf = load_multi_filters_settings()
    if _mf:
        multi_filters = _mf
        LOGGER.info(f"Загружены мультифильтры для {len(multi_filters)} чатов")
except Exception as e:
    LOGGER.warning(f"Не удалось загрузить настройки config_panel: {e}")
    save_antiflood_settings = None
    save_warns_settings = None
    save_blacklist_settings = None
    save_multi_filters_settings = None


def _save_antiflood_to_db():
    if save_antiflood_settings:
        save_antiflood_settings(antiflood_settings)

def _save_warns_to_db():
    if save_warns_settings:
        save_warns_settings(warns_settings)

def _save_blacklist_to_db():
    if save_blacklist_settings:
        save_blacklist_settings(blacklist_settings)

def _save_multi_filters_to_db():
    if save_multi_filters_settings:
        save_multi_filters_settings(multi_filters)


def get_filter_autodelete(chat_id):
    """Получает время автоудаления фильтров (в минутах, 0 = отключено)"""
    return filter_autodelete.get(chat_id, 0)

def set_filter_autodelete(chat_id, minutes):
    """Устанавливает время автоудаления фильтров"""
    filter_autodelete[chat_id] = minutes

def get_delete_service_messages(chat_id):
    """Проверяет включено ли удаление сервисных сообщений"""
    return delete_service_messages.get(chat_id, False)

def set_delete_service_messages(chat_id, enabled):
    """Устанавливает удаление сервисных сообщений"""
    delete_service_messages[chat_id] = enabled


def get_antiflood_settings(chat_id):
    return antiflood_settings.get(chat_id, {"enabled": False, "limit": 5, "action": "mute"})

def set_antiflood_settings(chat_id, settings):
    antiflood_settings[chat_id] = settings
    _save_antiflood_to_db()

def get_warns_settings(chat_id):
    return warns_settings.get(chat_id, {"limit": 3, "action": "ban"})

def set_warns_settings(chat_id, settings):
    warns_settings[chat_id] = settings
    _save_warns_to_db()

def get_blacklist_settings(chat_id):
    return blacklist_settings.get(chat_id, {"enabled": False, "words": [], "action": "delete"})

def set_blacklist_settings(chat_id, settings):
    blacklist_settings[chat_id] = settings
    _save_blacklist_to_db()


def get_multi_filters(chat_id):
    """Получает мультифильтры для чата"""
    return multi_filters.get(chat_id, {})

def set_multi_filter(chat_id, keyword, responses):
    """Устанавливает мультифильтр"""
    if chat_id not in multi_filters:
        multi_filters[chat_id] = {}
    multi_filters[chat_id][keyword.lower()] = responses
    _save_multi_filters_to_db()

def delete_multi_filter(chat_id, keyword):
    """Удаляет мультифильтр"""
    if chat_id in multi_filters and keyword.lower() in multi_filters[chat_id]:
        del multi_filters[chat_id][keyword.lower()]
        _save_multi_filters_to_db()


# ═══════════════════════════════════════════════════════════════
#                         ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════

def config_cmd(update: Update, context: CallbackContext):
    """Команда /config - открывает панель настроек"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type != "private":
        update.effective_message.reply_text(
            "⚙️ Настройки доступны только в личных сообщениях.\n"
            "Напишите мне в ЛС: /config"
        )
        return ConversationHandler.END
    
    return show_main_menu(update, context)


def show_main_menu(update: Update, context: CallbackContext):
    """Показывает главное меню настроек"""
    user = update.effective_user
    chats = get_user_chats(user.id)
    
    text = (
        "⚙️ *Панель управления ботом*\n\n"
        "Здесь вы можете настроить бота для ваших чатов.\n\n"
    )
    
    keyboard = []
    
    if chats:
        text += "📋 *Ваши чаты:*\n"
        for chat_data in chats[:10]:
            text += f"• {chat_data['title']}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ {chat_data['title'][:30]}",
                    callback_data=f"cfg_chat_{chat_data['chat_id']}"
                )
            ])
    else:
        text += (
            "❗ *Нет подключённых чатов*\n\n"
            "Используйте команду /addmita в нужном чате,\n"
            "чтобы добавить его для управления."
        )
    
    keyboard.append([
        InlineKeyboardButton("🔄 Обновить", callback_data="cfg_refresh"),
        InlineKeyboardButton("❌ Закрыть", callback_data="cfg_close"),
    ])
    
    # Кнопка сброса только для владельца
    if user.id == OWNER_ID:
        keyboard.append([
            InlineKeyboardButton("🐟 Режим рыбки", callback_data="cfg_reset_bot")
        ])
    
    if update.callback_query:
        try:
            update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except BadRequest:
            pass
    else:
        update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return SELECTING_CHAT


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ ЧАТА
# ═══════════════════════════════════════════════════════════════

def chat_settings_callback(update: Update, context: CallbackContext):
    """Показывает настройки выбранного чата"""
    query = update.callback_query
    user = update.effective_user
    
    chat_id = int(query.data.split("_")[2])
    query.answer()
    
    user_editing[user.id] = {"chat_id": chat_id}
    
    try:
        chat_info = context.bot.get_chat(chat_id)
        chat_title = chat_info.title or str(chat_id)
    except:
        chat_title = str(chat_id)
    
    text = (
        f"⚙️ *Настройки чата:*\n"
        f"📍 {chat_title}\n"
        f"🆔 `{chat_id}`\n\n"
        f"Выберите раздел:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("👋 Приветствия", callback_data=f"cfg_mod_welcome_{chat_id}"),
            InlineKeyboardButton("🔐 Капча", callback_data=f"cfg_mod_captcha_{chat_id}"),
        ],
        [
            InlineKeyboardButton("📝 Фильтры", callback_data=f"cfg_mod_filters_{chat_id}"),
            InlineKeyboardButton("📌 Заметки", callback_data=f"cfg_mod_notes_{chat_id}"),
        ],
        [
            InlineKeyboardButton("📜 Правила", callback_data=f"cfg_mod_rules_{chat_id}"),
            InlineKeyboardButton("⚠️ Варны", callback_data=f"cfg_mod_warns_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🛡 Антифлуд", callback_data=f"cfg_mod_antiflood_{chat_id}"),
            InlineKeyboardButton("🚫 Чёрный список", callback_data=f"cfg_mod_blacklist_{chat_id}"),
        ],
        [
            InlineKeyboardButton("👥 Админы бота", callback_data=f"cfg_mod_admins_{chat_id}"),
            InlineKeyboardButton("🧹 Сервисные", callback_data=f"cfg_mod_service_{chat_id}"),
        ],
        [
            InlineKeyboardButton("📋 Логи", callback_data=f"cfg_mod_logs_{chat_id}"),
            InlineKeyboardButton("🚫 Медиа-фильтры", callback_data=f"cfg_mod_mediafilters_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🛡 CAS Anti-Spam", callback_data=f"cfg_mod_cas_{chat_id}"),
            InlineKeyboardButton("📢 Антиканал", callback_data=f"cfg_mod_antichannel_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ К списку чатов", callback_data="cfg_back_main"),
        ],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return SELECTING_MODULE


# ═══════════════════════════════════════════════════════════════
#                    НАСТРОЙКИ ПРИВЕТСТВИЙ
# ═══════════════════════════════════════════════════════════════

def welcome_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки приветствий"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "welcome"}
    
    if get_welcome_settings:
        settings = get_welcome_settings(chat_id)
    else:
        settings = {"enabled": True, "text": "Привет, {first}!", "delete_after": 0, "buttons": []}
    
    enabled = "✅ Вкл" if settings.get("enabled", True) else "❌ Выкл"
    welcome_text = settings.get('text', 'Не установлено')
    delete_after = settings.get('delete_after', 0)
    buttons = settings.get('buttons', [])
    
    # Проверяем режим ЧС
    lockdown_active = is_lockdown_enabled(chat_id) if is_lockdown_enabled else False
    lockdown_status = "🔒 АКТИВЕН" if lockdown_active else "🔓 Выкл"
    
    # Форматирование времени удаления
    if delete_after == 0:
        delete_text = "Не удалять"
    elif delete_after < 60:
        delete_text = f"{delete_after} сек"
    else:
        delete_text = f"{delete_after // 60} мин"
    
    text = (
        f"👋 *Настройки приветствий*\n\n"
        f"Статус: {enabled}\n"
        f"🗑 Автоудаление: `{delete_text}`\n"
        f"🔒 Режим ЧС: {lockdown_status}\n\n"
        f"📝 *Текущее сообщение:*\n"
        f"`{welcome_text[:200] if welcome_text else 'Не установлено'}`\n\n"
    )
    
    # Показываем кнопки
    if buttons:
        text += f"🔘 *Кнопки ({len(buttons)}):*\n"
        for i, btn in enumerate(buttons, 1):
            text += f"  {i}. [{btn['text']}]({btn['url']})\n"
        text += "\n"
    else:
        text += "🔘 *Кнопки:* нет\n\n"
    
    if lockdown_active:
        text += "⚠️ _Режим ЧС активен! Все новые участники банятся!_\n\n"
    
    text += "_Переменные: {{first}}, {{last}}, {{fullname}}, {{username}}, {{mention}}, {{chatname}}, {{id}}_"
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'❌ Выключить' if settings.get('enabled', True) else '✅ Включить'}",
                callback_data=f"cfg_wel_toggle_{chat_id}"
            ),
            InlineKeyboardButton(
                f"{'🔓 Откл. ЧС' if lockdown_active else '🔒 Вкл. ЧС'}",
                callback_data=f"cfg_lockdown_toggle_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton("✏️ Изменить текст", callback_data=f"cfg_wel_edit_{chat_id}"),
        ],
        [
            InlineKeyboardButton("➕ Добавить кнопку", callback_data=f"cfg_wel_addbtn_{chat_id}"),
        ],
    ]
    
    # Кнопки для удаления существующих
    if buttons:
        del_buttons = []
        for i, btn in enumerate(buttons):
            del_buttons.append(InlineKeyboardButton(
                f"🗑 {btn['text'][:15]}",
                callback_data=f"cfg_wel_delbtn_{i}_{chat_id}"
            ))
        # По 2 в ряд
        for j in range(0, len(del_buttons), 2):
            keyboard.append(del_buttons[j:j+2])
    
    keyboard.extend([
        [
            InlineKeyboardButton("🚫 Не удалять", callback_data=f"cfg_wel_del_0_{chat_id}"),
            InlineKeyboardButton("30с", callback_data=f"cfg_wel_del_30_{chat_id}"),
        ],
        [
            InlineKeyboardButton("1 мин", callback_data=f"cfg_wel_del_60_{chat_id}"),
            InlineKeyboardButton("5 мин", callback_data=f"cfg_wel_del_300_{chat_id}"),
            InlineKeyboardButton("10 мин", callback_data=f"cfg_wel_del_600_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
        ],
    ])
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)
    return EDITING_SETTING


def toggle_welcome(update: Update, context: CallbackContext):
    """Переключает приветствие"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if get_welcome_settings and set_welcome_settings:
        settings = get_welcome_settings(chat_id)
        settings["enabled"] = not settings.get("enabled", True)
        set_welcome_settings(chat_id, settings)
        query.answer(f"✅ Приветствие {'включено' if settings['enabled'] else 'выключено'}")
    else:
        query.answer("❌ Модуль не найден")
    
    return welcome_settings_callback(update, context, chat_id_override=chat_id)


def toggle_lockdown(update: Update, context: CallbackContext):
    """Переключает режим ЧС"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if get_lockdown_settings and set_lockdown_settings:
        settings = get_lockdown_settings(chat_id)
        settings["enabled"] = not settings.get("enabled", False)
        set_lockdown_settings(chat_id, settings)
        
        if settings["enabled"]:
            query.answer("🔒 Режим ЧС АКТИВИРОВАН! Все новые участники будут забанены!", show_alert=True)
        else:
            query.answer("🔓 Режим ЧС отключён")
    else:
        query.answer("❌ Модуль не найден")
    
    return welcome_settings_callback(update, context, chat_id_override=chat_id)


def welcome_edit_callback(update: Update, context: CallbackContext):
    """Начинает редактирование текста приветствия"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "welcome", "action": "edit"}
    
    text = (
        "✏️ <b>Редактирование приветствия</b>\n\n"
        "Отправьте новый текст приветствия.\n\n"
        "<b>📝 Переменные:</b>\n"
        "• <code>{first}</code> — имя\n"
        "• <code>{last}</code> — фамилия\n"
        "• <code>{fullname}</code> — полное имя\n"
        "• <code>{username}</code> — @username\n"
        "• <code>{mention}</code> — упоминание\n"
        "• <code>{chatname}</code> — название чата\n"
        "• <code>{id}</code> — ID пользователя\n\n"
        "<b>✨ Форматирование:</b>\n"
        "• <code>&lt;b&gt;жирный&lt;/b&gt;</code> → <b>жирный</b>\n"
        "• <code>&lt;i&gt;курсив&lt;/i&gt;</code> → <i>курсив</i>\n"
        "• <code>&lt;u&gt;подчёркнутый&lt;/u&gt;</code> → <u>подчёркнутый</u>\n"
        "• <code>&lt;s&gt;зачёркнутый&lt;/s&gt;</code> → <s>зачёркнутый</s>\n"
        "• <code>&lt;code&gt;код&lt;/code&gt;</code> → <code>код</code>\n"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"cfg_mod_welcome_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_WELCOME_INPUT


def process_welcome_input(update: Update, context: CallbackContext):
    """Обрабатывает ввод текста приветствия"""
    user = update.effective_user
    text = update.effective_message.text
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    
    if not chat_id:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    if get_welcome_settings and set_welcome_settings:
        settings = get_welcome_settings(chat_id)
        settings["text"] = text
        set_welcome_settings(chat_id, settings)
        
        keyboard = [[InlineKeyboardButton("👋 К настройкам приветствия", callback_data=f"cfg_mod_welcome_{chat_id}")]]
        update.effective_message.reply_text(
            "✅ Текст приветствия обновлён!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        update.effective_message.reply_text("❌ Модуль приветствий не найден")
    
    return EDITING_SETTING


def welcome_delete_after_callback(update: Update, context: CallbackContext):
    """Устанавливает время автоудаления приветствия"""
    query = update.callback_query
    parts = query.data.split("_")
    seconds = int(parts[3])
    chat_id = int(parts[4])
    
    if get_welcome_settings and set_welcome_settings:
        settings = get_welcome_settings(chat_id)
        settings["delete_after"] = seconds
        set_welcome_settings(chat_id, settings)
        
        if seconds == 0:
            query.answer("✅ Автоудаление выключено")
        elif seconds < 60:
            query.answer(f"✅ Удаление через {seconds} сек")
        else:
            query.answer(f"✅ Удаление через {seconds // 60} мин")
    else:
        query.answer("❌ Модуль не найден")
    
    return welcome_settings_callback(update, context, chat_id_override=chat_id)


def welcome_add_button_callback(update: Update, context: CallbackContext):
    """Начинает добавление кнопки к приветствию"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "welcome", "action": "add_button"}
    
    text = (
        "🔘 *Добавление кнопки*\n\n"
        "Отправьте кнопку в формате:\n"
        "`Текст кнопки | https://ссылка`\n\n"
        "*Примеры:*\n"
        "• `Оффтоп чат | https://t.me/offtopchat`\n"
        "• `Правила | https://t.me/rules`\n"
        "• `Наш канал | https://t.me/channel`\n\n"
        "_Можно добавить до 10 кнопок_"
    )
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"cfg_mod_welcome_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_WELCOME_BUTTON


def process_welcome_button(update: Update, context: CallbackContext):
    """Обрабатывает ввод кнопки для приветствия"""
    user = update.effective_user
    msg = update.effective_message
    
    if user.id not in user_editing:
        return SELECTING_CHAT
    
    edit_data = user_editing[user.id]
    chat_id = edit_data.get("chat_id")
    
    # Парсим формат: Текст | URL
    text = msg.text.strip()
    
    # Берём только первую строку если пользователь отправил несколько
    text = text.split('\n')[0].strip()
    
    if "|" not in text:
        msg.reply_text(
            "❌ Неверный формат!\n\n"
            "Используйте: `Текст кнопки | https://ссылка`",
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_WELCOME_BUTTON
    
    parts = text.split("|", 1)
    btn_text = parts[0].strip()
    btn_url = parts[1].strip()
    
    # Очищаем URL от пробелов и лишних символов
    btn_url = btn_url.split()[0] if btn_url else ""
    
    # Проверяем URL
    if not btn_url.startswith(("http://", "https://", "tg://")):
        msg.reply_text(
            "❌ Ссылка должна начинаться с http://, https:// или tg://",
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_WELCOME_BUTTON
    
    # Проверяем текст
    if len(btn_text) > 64:
        msg.reply_text("❌ Текст кнопки слишком длинный (макс. 64 символа)")
        return WAITING_WELCOME_BUTTON
    
    if len(btn_text) < 1:
        msg.reply_text("❌ Текст кнопки не может быть пустым")
        return WAITING_WELCOME_BUTTON
    
    # Добавляем кнопку
    if get_welcome_settings and set_welcome_settings:
        settings = get_welcome_settings(chat_id)
        if "buttons" not in settings:
            settings["buttons"] = []
        
        if len(settings["buttons"]) >= 10:
            msg.reply_text("❌ Достигнут лимит кнопок (максимум 10)")
            return WAITING_WELCOME_BUTTON
        
        settings["buttons"].append({"text": btn_text, "url": btn_url})
        set_welcome_settings(chat_id, settings)
        
        msg.reply_text(f"✅ Кнопка *{btn_text}* добавлена!", parse_mode=ParseMode.MARKDOWN)
    else:
        msg.reply_text("❌ Ошибка сохранения")
    
    del user_editing[user.id]
    
    # Возвращаемся к настройкам
    keyboard = [[InlineKeyboardButton("👋 К настройкам приветствия", callback_data=f"cfg_mod_welcome_{chat_id}")]]
    msg.reply_text("Нажмите кнопку для продолжения:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    return EDITING_SETTING


def welcome_delete_button_callback(update: Update, context: CallbackContext):
    """Удаляет кнопку из приветствия"""
    query = update.callback_query
    parts = query.data.split("_")
    # cfg_wel_delbtn_{index}_{chat_id}
    btn_index = int(parts[3])
    chat_id = int(parts[4])
    
    if get_welcome_settings and set_welcome_settings:
        settings = get_welcome_settings(chat_id)
        buttons = settings.get("buttons", [])
        
        if 0 <= btn_index < len(buttons):
            removed = buttons.pop(btn_index)
            settings["buttons"] = buttons
            set_welcome_settings(chat_id, settings)
            query.answer(f"✅ Кнопка '{removed['text']}' удалена")
        else:
            query.answer("❌ Кнопка не найдена")
    else:
        query.answer("❌ Ошибка")
    
    return welcome_settings_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ КАПЧИ
# ═══════════════════════════════════════════════════════════════

def captcha_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки капчи"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    if get_captcha_settings:
        settings = get_captcha_settings(chat_id)
    else:
        settings = {"enabled": False, "mode": "button", "timeout": 120, "newbie_mute": 0}
    
    enabled = "✅ Вкл" if settings.get("enabled") else "❌ Выкл"
    mode = settings.get("mode", "button")
    mode_name = {"button": "🔘 Кнопка", "math": "🔢 Математика", "text": "📝 Текст", "emoji": "🖼 Эмодзи"}.get(mode, mode)
    newbie_mute = settings.get("newbie_mute", 0)
    newbie_mute_text = f"{newbie_mute} мин" if newbie_mute > 0 else "Выкл"
    
    text = (
        f"🔐 *Настройки капчи*\n\n"
        f"Статус: {enabled}\n"
        f"Режим: {mode_name}\n"
        f"Таймаут: `{settings.get('timeout', 120)}` сек\n"
        f"🔇 Мут новичков: `{newbie_mute_text}`\n\n"
        f"_Мут новичков — после прохождения капчи пользователь не сможет писать указанное время._"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'❌ Выключить' if settings.get('enabled') else '✅ Включить'}",
                callback_data=f"cfg_cap_toggle_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton("🔘 Кнопка", callback_data=f"cfg_cap_mode_button_{chat_id}"),
            InlineKeyboardButton("🔢 Математика", callback_data=f"cfg_cap_mode_math_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🖼 Эмодзи", callback_data=f"cfg_cap_mode_emoji_{chat_id}"),
            InlineKeyboardButton("📝 Текст", callback_data=f"cfg_cap_mode_text_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⏱ 60с", callback_data=f"cfg_cap_timeout_60_{chat_id}"),
            InlineKeyboardButton("⏱ 120с", callback_data=f"cfg_cap_timeout_120_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔇 Выкл", callback_data=f"cfg_cap_newbie_0_{chat_id}"),
            InlineKeyboardButton("🔇 5м", callback_data=f"cfg_cap_newbie_5_{chat_id}"),
            InlineKeyboardButton("🔇 10м", callback_data=f"cfg_cap_newbie_10_{chat_id}"),
            InlineKeyboardButton("🔇 15м", callback_data=f"cfg_cap_newbie_15_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
        ],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def toggle_captcha(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if get_captcha_settings and set_captcha_settings:
        settings = get_captcha_settings(chat_id)
        settings["enabled"] = not settings.get("enabled", False)
        set_captcha_settings(chat_id, settings)
        query.answer(f"✅ Капча {'включена' if settings['enabled'] else 'выключена'}")
    else:
        query.answer("❌ Модуль не найден")
    
    return captcha_settings_callback(update, context, chat_id_override=chat_id)


def set_captcha_mode(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    mode = parts[3]
    chat_id = int(parts[4])
    
    if get_captcha_settings and set_captcha_settings:
        settings = get_captcha_settings(chat_id)
        settings["mode"] = mode
        set_captcha_settings(chat_id, settings)
        query.answer(f"✅ Режим: {mode}")
    
    return captcha_settings_callback(update, context, chat_id_override=chat_id)


def set_captcha_timeout(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    timeout = int(parts[3])
    chat_id = int(parts[4])
    
    if get_captcha_settings and set_captcha_settings:
        settings = get_captcha_settings(chat_id)
        settings["timeout"] = timeout
        set_captcha_settings(chat_id, settings)
        query.answer(f"✅ Таймаут: {timeout}с")
    
    return captcha_settings_callback(update, context, chat_id_override=chat_id)


def set_newbie_mute(update: Update, context: CallbackContext):
    """Устанавливает время мута новичков после капчи"""
    query = update.callback_query
    parts = query.data.split("_")
    mute_time = int(parts[3])  # 0, 5, 10, 15
    chat_id = int(parts[4])
    
    if get_captcha_settings and set_captcha_settings:
        settings = get_captcha_settings(chat_id)
        settings["newbie_mute"] = mute_time
        set_captcha_settings(chat_id, settings)
        if mute_time > 0:
            query.answer(f"✅ Мут новичков: {mute_time} минут")
        else:
            query.answer("✅ Мут новичков выключен")
    else:
        query.answer("❌ Модуль не найден")
    
    return captcha_settings_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ ПРАВИЛ
# ═══════════════════════════════════════════════════════════════

def rules_settings_callback(update: Update, context: CallbackContext):
    """Настройки правил"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "rules"}
    
    if get_rules:
        rules = get_rules(chat_id)
    else:
        rules = None
    
    if rules:
        text = f"📜 *Правила чата*\n\n{rules[:500]}"
        if len(rules) > 500:
            text += "\n\n_(показано 500 символов)_"
    else:
        text = "📜 *Правила чата*\n\n_Правила не установлены_"
    
    keyboard = [
        [
            InlineKeyboardButton("✏️ Изменить правила", callback_data=f"cfg_rules_edit_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🗑 Удалить правила", callback_data=f"cfg_rules_clear_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
        ],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def rules_edit_callback(update: Update, context: CallbackContext):
    """Начинает редактирование правил"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "rules", "action": "edit"}
    
    text = "📜 *Редактирование правил*\n\nОтправьте новые правила текстовым сообщением:"
    keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"cfg_mod_rules_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_RULES_INPUT


def process_rules_input(update: Update, context: CallbackContext):
    """Обрабатывает ввод правил"""
    user = update.effective_user
    text = update.effective_message.text
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    
    if not chat_id:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    if set_rules:
        set_rules(chat_id, text)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад к приветствию", callback_data=f"cfg_mod_welcome_{chat_id}")]
        ])
        update.effective_message.reply_text(
            "✅ Правила чата обновлены!",
            reply_markup=keyboard
        )
    else:
        update.effective_message.reply_text("❌ Модуль правил не найден")
    
    return EDITING_SETTING


def rules_clear_callback(update: Update, context: CallbackContext):
    """Очищает правила"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if clear_rules:
        clear_rules(chat_id)
        query.answer("✅ Правила удалены")
    else:
        query.answer("❌ Модуль не найден")
    
    return rules_settings_callback(update, context)


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ ФИЛЬТРОВ
# ═══════════════════════════════════════════════════════════════

def filters_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки фильтров"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "filters"}
    
    if get_all_filters:
        filters = get_all_filters(chat_id)
        count = len(filters) if filters else 0
    else:
        filters = {}
        count = 0
    
    text = f"📝 *Фильтры чата*\n\nВсего фильтров: `{count}`\n\n"
    
    keyboard = []
    
    if filters:
        text += "*Список (нажмите для удаления):*\n"
        # Показываем фильтры как кнопки для удаления
        row = []
        for i, keyword in enumerate(list(filters.keys())[:12]):
            row.append(InlineKeyboardButton(
                f"🗑 {keyword[:15]}",
                callback_data=f"cfg_flt_del_{keyword[:20]}_{chat_id}"
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
    
    # Показываем мультифильтры с кнопками удаления
    chat_multi = multi_filters.get(chat_id, {})
    if chat_multi:
        text += "\n\n*🎲 Мультифильтры (нажмите для удаления):*\n"
        mrow = []
        for kw, responses in list(chat_multi.items())[:8]:
            text += f"• `{kw}` — {len(responses)} вариантов\n"
            mrow.append(InlineKeyboardButton(
                f"🗑 {kw[:15]}",
                callback_data=f"cfg_mflt_del_{kw[:20]}_{chat_id}"
            ))
            if len(mrow) == 2:
                keyboard.append(mrow)
                mrow = []
        if mrow:
            keyboard.append(mrow)
    
    if not filters and not chat_multi:
        text += "_Фильтры не настроены_"
    
    # Показываем текущую настройку автоудаления
    autodel = get_filter_autodelete(chat_id)
    autodel_text = f"{autodel} мин" if autodel > 0 else "выкл"
    text += f"\n\n⏱ *Автоудаление ответов:* `{autodel_text}`"
    text += "\n\n_Фильтр срабатывает когда кто-то пишет ключевое слово_"
    
    keyboard.append([
        InlineKeyboardButton("➕ Фильтр", callback_data=f"cfg_flt_add_{chat_id}"),
        InlineKeyboardButton("🎲 Мультифильтр", callback_data=f"cfg_mflt_add_{chat_id}"),
    ])
    keyboard.append([
        InlineKeyboardButton(f"⏱ Автоудаление: {autodel_text}", callback_data=f"cfg_flt_autodel_{chat_id}"),
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
    ])
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def filter_autodelete_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Показывает меню выбора времени автоудаления"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    current = get_filter_autodelete(chat_id)
    
    text = (
        "⏱ *Автоудаление ответов фильтров*\n\n"
        "Выберите через сколько минут удалять ответы бота на фильтры:\n\n"
        f"Текущее значение: `{current} мин`" if current > 0 else 
        "⏱ *Автоудаление ответов фильтров*\n\n"
        "Выберите через сколько минут удалять ответы бота на фильтры:\n\n"
        "Текущее значение: `выключено`"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("❌ Выкл" + (" ✓" if current == 0 else ""), callback_data=f"cfg_flt_adel_0_{chat_id}"),
            InlineKeyboardButton("5 мин" + (" ✓" if current == 5 else ""), callback_data=f"cfg_flt_adel_5_{chat_id}"),
        ],
        [
            InlineKeyboardButton("30 мин" + (" ✓" if current == 30 else ""), callback_data=f"cfg_flt_adel_30_{chat_id}"),
            InlineKeyboardButton("60 мин" + (" ✓" if current == 60 else ""), callback_data=f"cfg_flt_adel_60_{chat_id}"),
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_mod_filters_{chat_id}")],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def filter_autodelete_set_callback(update: Update, context: CallbackContext):
    """Устанавливает время автоудаления"""
    query = update.callback_query
    
    # Формат: cfg_flt_adel_{minutes}_{chat_id}
    parts = query.data.split("_")
    minutes = int(parts[3])
    chat_id = int(parts[4])
    
    set_filter_autodelete(chat_id, minutes)
    
    if minutes > 0:
        query.answer(f"✅ Ответы фильтров будут удаляться через {minutes} мин")
    else:
        query.answer("✅ Автоудаление выключено")
    
    return filter_autodelete_callback(update, context, chat_id_override=chat_id)


def filter_add_callback(update: Update, context: CallbackContext):
    """Начинает добавление фильтра"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "filters", "action": "add"}
    
    text = (
        "➕ *Добавление фильтра*\n\n"
        "Отправьте *ключевое слово* для фильтра:\n\n"
        "_Например: привет_"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"cfg_mod_filters_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_FILTER_KEYWORD


def process_filter_keyword(update: Update, context: CallbackContext):
    """Обрабатывает ввод ключевого слова фильтра"""
    user = update.effective_user
    keyword = update.effective_message.text.strip().lower()
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    
    if not chat_id:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    # Сохраняем ключевое слово и ждём ответ
    user_editing[user.id]["keyword"] = keyword
    
    update.effective_message.reply_text(
        f"✅ Ключевое слово: `{keyword}`\n\n"
        f"Теперь отправьте *ответ* — что бот будет отправлять:\n\n"
        f"• Текст\n"
        f"• GIF (анимацию)\n"
        f"• Стикер",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_FILTER_RESPONSE


def process_filter_response(update: Update, context: CallbackContext):
    """Обрабатывает ввод ответа фильтра (текст, GIF, стикер)"""
    user = update.effective_user
    msg = update.effective_message
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    keyword = editing.get("keyword")
    
    if not chat_id or not keyword:
        msg.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    # Определяем тип контента
    content = ""
    media_type = None
    media_id = None
    
    if msg.text:
        content = msg.text
    elif msg.animation:  # GIF
        media_type = "animation"
        media_id = msg.animation.file_id
        content = msg.caption or ""
    elif msg.sticker:
        media_type = "sticker"
        media_id = msg.sticker.file_id
    elif msg.photo:
        media_type = "photo"
        media_id = msg.photo[-1].file_id
        content = msg.caption or ""
    elif msg.video:
        media_type = "video"
        media_id = msg.video.file_id
        content = msg.caption or ""
    elif msg.document:
        media_type = "document"
        media_id = msg.document.file_id
        content = msg.caption or ""
    
    if not content and not media_id:
        msg.reply_text("❌ Отправьте текст, GIF или стикер.")
        return WAITING_FILTER_RESPONSE
    
    if save_filter:
        save_filter(chat_id, keyword, content, media_type, media_id)
        
        type_text = ""
        if media_type == "animation":
            type_text = " (GIF)"
        elif media_type == "sticker":
            type_text = " (стикер)"
        elif media_type == "photo":
            type_text = " (фото)"
        elif media_type == "video":
            type_text = " (видео)"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад к фильтрам", callback_data=f"cfg_mod_filters_{chat_id}")]
        ])
        msg.reply_text(
            f"✅ Фильтр `{keyword}`{type_text} добавлен!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        msg.reply_text("❌ Модуль фильтров не найден")
    
    return EDITING_SETTING


def filter_delete_callback(update: Update, context: CallbackContext):
    """Удаляет фильтр"""
    query = update.callback_query
    parts = query.data.split("_")
    # cfg_flt_del_{keyword}_{chat_id}
    keyword = parts[3]
    chat_id = int(parts[4])
    
    if delete_filter:
        if delete_filter(chat_id, keyword):
            query.answer(f"✅ Фильтр '{keyword}' удалён")
        else:
            query.answer("❌ Фильтр не найден")
    else:
        query.answer("❌ Модуль не найден")
    
    return filters_settings_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      МУЛЬТИФИЛЬТРЫ
# ═══════════════════════════════════════════════════════════════

def multi_filter_add_callback(update: Update, context: CallbackContext):
    """Начинает добавление мультифильтра"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {
        "chat_id": chat_id, 
        "module": "multifilter", 
        "action": "add",
        "responses": []
    }
    
    text = (
        "🎲 *Добавление мультифильтра*\n\n"
        "Мультифильтр отправляет *случайный* ответ из нескольких.\n\n"
        "Отправьте *ключевое слово*:\n\n"
        "_Например: лол_"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"cfg_mod_filters_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_MULTI_KEYWORD


def process_multi_keyword(update: Update, context: CallbackContext):
    """Обрабатывает ключевое слово мультифильтра"""
    user = update.effective_user
    keyword = update.effective_message.text.strip().lower()
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    
    if not chat_id:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    user_editing[user.id]["keyword"] = keyword
    user_editing[user.id]["responses"] = []
    
    update.effective_message.reply_text(
        f"✅ Ключевое слово: `{keyword}`\n\n"
        f"Теперь отправляйте *стикеры* или *GIF* по одному.\n"
        f"Добавлено: 0\n\n"
        f"Когда закончите, нажмите кнопку *Готово*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Готово", callback_data=f"cfg_mflt_done_{chat_id}")
        ]])
    )
    return WAITING_MULTI_RESPONSES


def process_multi_response(update: Update, context: CallbackContext):
    """Добавляет ответ в мультифильтр"""
    user = update.effective_user
    msg = update.effective_message
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    keyword = editing.get("keyword")
    
    if not chat_id or not keyword:
        msg.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    # Определяем тип контента
    response = None
    
    if msg.sticker:
        response = {"type": "sticker", "file_id": msg.sticker.file_id}
    elif msg.animation:
        response = {"type": "animation", "file_id": msg.animation.file_id, "caption": msg.caption or ""}
    elif msg.photo:
        response = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""}
    elif msg.text:
        response = {"type": "text", "content": msg.text}
    
    if not response:
        msg.reply_text("❌ Отправьте стикер, GIF, фото или текст.")
        return WAITING_MULTI_RESPONSES
    
    # Добавляем ответ
    if "responses" not in user_editing[user.id]:
        user_editing[user.id]["responses"] = []
    user_editing[user.id]["responses"].append(response)
    
    count = len(user_editing[user.id]["responses"])
    
    msg.reply_text(
        f"✅ Добавлено! Всего: *{count}*\n\n"
        f"Отправьте ещё или нажмите *Готово*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Готово", callback_data=f"cfg_mflt_done_{chat_id}")
        ]])
    )
    return WAITING_MULTI_RESPONSES


def multi_filter_done_callback(update: Update, context: CallbackContext):
    """Завершает добавление мультифильтра"""
    query = update.callback_query
    user = update.effective_user
    chat_id = int(query.data.split("_")[3])
    
    editing = user_editing.get(user.id, {})
    keyword = editing.get("keyword")
    responses = editing.get("responses", [])
    
    if not keyword or len(responses) < 2:
        query.answer("❌ Добавьте минимум 2 ответа!")
        return WAITING_MULTI_RESPONSES
    
    # Сохраняем мультифильтр через функцию (с сохранением в БД)
    set_multi_filter(chat_id, keyword, responses)
    
    query.answer(f"✅ Мультифильтр '{keyword}' сохранён!")
    
    # Очищаем
    user_editing.pop(user.id, None)
    
    return filters_settings_callback(update, context, chat_id_override=chat_id)


def multi_filter_delete_callback(update: Update, context: CallbackContext):
    """Удаляет мультифильтр"""
    query = update.callback_query
    
    # Формат: cfg_mflt_del_{keyword}_{chat_id}
    parts = query.data.split("_")
    chat_id = int(parts[-1])
    keyword = "_".join(parts[3:-1])  # keyword может содержать _
    
    # Удаляем через функцию (с сохранением в БД)
    delete_multi_filter(chat_id, keyword)
    query.answer(f"✅ Мультифильтр '{keyword}' удалён!")
    
    return filters_settings_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ ЗАМЕТОК
# ═══════════════════════════════════════════════════════════════

def notes_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки заметок"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "notes"}
    
    if get_all_notes:
        notes = get_all_notes(chat_id)
        count = len(notes) if notes else 0
    else:
        notes = {}
        count = 0
    
    text = f"📌 *Заметки чата*\n\nВсего заметок: `{count}`\n\n"
    
    keyboard = []
    
    if notes:
        text += "*Список (нажмите для просмотра/удаления):*\n"
        row = []
        for i, name in enumerate(list(notes.keys())[:12]):
            row.append(InlineKeyboardButton(
                f"#{name[:15]}",
                callback_data=f"cfg_note_view_{name[:20]}_{chat_id}"
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
    else:
        text += "_Заметки не созданы_"
    
    text += "\n\n_Заметку можно вызвать командой #имя или /get имя_"
    
    keyboard.append([
        InlineKeyboardButton("➕ Добавить заметку", callback_data=f"cfg_note_add_{chat_id}"),
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
    ])
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def note_view_callback(update: Update, context: CallbackContext):
    """Просмотр заметки"""
    query = update.callback_query
    parts = query.data.split("_")
    note_name = parts[3]
    chat_id = int(parts[4])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "notes", "note_name": note_name}
    
    if get_note:
        note = get_note(chat_id, note_name)
        if note:
            content = note.get("content", "")[:300]
            buttons = note.get("buttons", [])
            text = (
                f"📌 *Заметка:* `#{note_name}`\n\n"
                f"*Содержимое:*\n{content}"
            )
            if len(note.get("content", "")) > 300:
                text += "\n\n_(показано 300 символов)_"
            
            # Показываем кнопки если есть
            if buttons:
                text += f"\n\n🔘 *Кнопки ({len(buttons)}):*"
                for btn in buttons:
                    text += f"\n• [{btn.get('text', '?')}]({btn.get('url', '')})"
            else:
                text += "\n\n_🔘 Кнопок нет_"
        else:
            text = f"❌ Заметка `#{note_name}` не найдена"
            buttons = []
    else:
        text = "❌ Модуль заметок не найден"
        buttons = []
    
    keyboard = [
        [
            InlineKeyboardButton("🔘 Кнопки", callback_data=f"cfg_note_btns_{note_name}_{chat_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"cfg_note_del_{note_name}_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад к списку", callback_data=f"cfg_mod_notes_{chat_id}"),
        ],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)
    return EDITING_SETTING


def note_add_callback(update: Update, context: CallbackContext):
    """Начинает добавление заметки"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "notes", "action": "add"}
    
    text = (
        "➕ *Добавление заметки*\n\n"
        "Отправьте *имя* для заметки (одно слово):\n\n"
        "_Например: правила_"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"cfg_mod_notes_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_NOTE_NAME


def process_note_name(update: Update, context: CallbackContext):
    """Обрабатывает ввод имени заметки"""
    user = update.effective_user
    name = update.effective_message.text.strip().lower().split()[0]  # Берём только первое слово
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    
    if not chat_id:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    user_editing[user.id]["note_name"] = name
    
    update.effective_message.reply_text(
        f"✅ Имя заметки: `#{name}`\n\n"
        f"Теперь отправьте *содержимое* заметки:",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_NOTE_CONTENT


def process_note_content(update: Update, context: CallbackContext):
    """Обрабатывает ввод содержимого заметки"""
    user = update.effective_user
    content = update.effective_message.text
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    note_name = editing.get("note_name")
    
    if not chat_id or not note_name:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    if save_note:
        save_note(chat_id, note_name, content)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад к заметкам", callback_data=f"cfg_mod_notes_{chat_id}")]
        ])
        update.effective_message.reply_text(
            f"✅ Заметка `#{note_name}` сохранена!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        update.effective_message.reply_text("❌ Модуль заметок не найден")
    
    return EDITING_SETTING


def note_delete_callback(update: Update, context: CallbackContext):
    """Удаляет заметку"""
    query = update.callback_query
    parts = query.data.split("_")
    note_name = parts[3]
    chat_id = int(parts[4])
    
    if delete_note:
        if delete_note(chat_id, note_name):
            query.answer(f"✅ Заметка '#{note_name}' удалена")
        else:
            query.answer("❌ Заметка не найдена")
    else:
        query.answer("❌ Модуль не найден")
    
    return notes_settings_callback(update, context, chat_id_override=chat_id)


def note_buttons_callback(update: Update, context: CallbackContext):
    """Управление кнопками заметки"""
    query = update.callback_query
    parts = query.data.split("_")
    note_name = parts[3]
    chat_id = int(parts[4])
    query.answer()
    
    user_editing[update.effective_user.id] = {
        "chat_id": chat_id, 
        "module": "notes", 
        "note_name": note_name,
        "action": "buttons"
    }
    
    buttons = []
    if get_note:
        note = get_note(chat_id, note_name)
        if note:
            buttons = note.get("buttons", [])
    
    text = f"🔘 *Кнопки заметки* `#{note_name}`\n\n"
    
    keyboard = []
    
    if buttons:
        text += "*Текущие кнопки:*\n"
        for i, btn in enumerate(buttons):
            text += f"{i+1}. [{btn.get('text', '?')}]({btn.get('url', '')})\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑 {btn.get('text', '?')[:20]}",
                    callback_data=f"cfg_note_btndel_{note_name}_{i}_{chat_id}"
                )
            ])
    else:
        text += "_Кнопок пока нет_"
    
    text += "\n\n➕ Чтобы добавить кнопку, отправьте текст в формате:\n`Текст кнопки | https://ссылка`"
    
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад к заметке", callback_data=f"cfg_note_view_{note_name}_{chat_id}"),
    ])
    
    query.edit_message_text(
        text, 
        parse_mode=ParseMode.MARKDOWN, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )
    return WAITING_NOTE_BUTTON


def process_note_button(update: Update, context: CallbackContext):
    """Обрабатывает добавление кнопки к заметке"""
    user = update.effective_user
    text = update.effective_message.text.strip()
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    note_name = editing.get("note_name")
    
    if not chat_id or not note_name:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    # Парсим формат: Текст | URL
    if "|" not in text:
        update.effective_message.reply_text(
            "❌ Неверный формат. Используйте:\n`Текст кнопки | https://ссылка`",
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_NOTE_BUTTON
    
    parts = text.split("|", 1)
    btn_text = parts[0].strip()
    btn_url = parts[1].strip()
    
    # Валидация URL
    if not btn_url.startswith(("http://", "https://", "tg://")):
        update.effective_message.reply_text(
            "❌ URL должен начинаться с http://, https:// или tg://",
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_NOTE_BUTTON
    
    if not btn_text:
        update.effective_message.reply_text("❌ Текст кнопки не может быть пустым")
        return WAITING_NOTE_BUTTON
    
    # Добавляем кнопку к заметке
    if get_note and save_note:
        note = get_note(chat_id, note_name)
        if note:
            buttons = note.get("buttons", [])
            buttons.append({"text": btn_text, "url": btn_url})
            # Сохраняем с обновлёнными кнопками
            save_note(
                chat_id, 
                note_name, 
                note.get("content", ""),
                note.get("media_type"),
                note.get("media_id"),
                buttons
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔘 К кнопкам", callback_data=f"cfg_note_btns_{note_name}_{chat_id}")],
                [InlineKeyboardButton("◀️ К заметке", callback_data=f"cfg_note_view_{note_name}_{chat_id}")]
            ])
            update.effective_message.reply_text(
                f"✅ Кнопка добавлена!\n\n[{btn_text}]({btn_url})",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            return EDITING_SETTING
    
    update.effective_message.reply_text("❌ Ошибка при сохранении")
    return EDITING_SETTING


def note_button_delete_callback(update: Update, context: CallbackContext):
    """Удаляет кнопку из заметки"""
    query = update.callback_query
    parts = query.data.split("_")
    note_name = parts[3]
    btn_index = int(parts[4])
    chat_id = int(parts[5])
    
    if get_note and save_note:
        note = get_note(chat_id, note_name)
        if note:
            buttons = note.get("buttons", [])
            if 0 <= btn_index < len(buttons):
                removed = buttons.pop(btn_index)
                save_note(
                    chat_id,
                    note_name,
                    note.get("content", ""),
                    note.get("media_type"),
                    note.get("media_id"),
                    buttons
                )
                query.answer(f"✅ Кнопка '{removed.get('text', '')}' удалена")
            else:
                query.answer("❌ Кнопка не найдена")
        else:
            query.answer("❌ Заметка не найдена")
    else:
        query.answer("❌ Модуль не найден")
    
    # Возвращаемся к управлению кнопками
    return note_buttons_callback(update, context)


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ ВАРНОВ
# ═══════════════════════════════════════════════════════════════

def warns_settings_callback(update: Update, context: CallbackContext):
    """Настройки варнов"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    settings = get_warns_settings(chat_id)
    limit = settings.get("limit", 3)
    action = settings.get("action", "ban")
    
    action_text = {"ban": "🔨 Бан", "kick": "👢 Кик", "mute": "🔇 Мут"}.get(action, action)
    
    text = (
        f"⚠️ *Настройки предупреждений*\n\n"
        f"Лимит варнов: `{limit}`\n"
        f"Действие: {action_text}\n\n"
        f"При достижении лимита будет применено действие."
    )
    
    keyboard = [
        [
            InlineKeyboardButton(f"Лимит: {limit}", callback_data="cfg_noop"),
        ],
        [
            InlineKeyboardButton("➖", callback_data=f"cfg_warns_limit_dec_{chat_id}"),
            InlineKeyboardButton("➕", callback_data=f"cfg_warns_limit_inc_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔨 Бан", callback_data=f"cfg_warns_action_ban_{chat_id}"),
            InlineKeyboardButton("👢 Кик", callback_data=f"cfg_warns_action_kick_{chat_id}"),
            InlineKeyboardButton("🔇 Мут", callback_data=f"cfg_warns_action_mute_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
        ],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def warns_limit_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[3]  # inc или dec
    chat_id = int(parts[4])
    
    settings = get_warns_settings(chat_id)
    limit = settings.get("limit", 3)
    
    if action == "inc" and limit < 10:
        limit += 1
    elif action == "dec" and limit > 1:
        limit -= 1
    
    settings["limit"] = limit
    set_warns_settings(chat_id, settings)
    query.answer(f"Лимит: {limit}")
    
    return warns_settings_callback(update, context)


def warns_action_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[3]  # ban, kick, mute
    chat_id = int(parts[4])
    
    settings = get_warns_settings(chat_id)
    settings["action"] = action
    set_warns_settings(chat_id, settings)
    query.answer(f"✅ Действие: {action}")
    
    return warns_settings_callback(update, context)


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ АНТИФЛУДА
# ═══════════════════════════════════════════════════════════════

def antiflood_settings_callback(update: Update, context: CallbackContext):
    """Настройки антифлуда"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    settings = get_antiflood_settings(chat_id)
    enabled = settings.get("enabled", False)
    limit = settings.get("limit", 5)
    action = settings.get("action", "mute")
    
    status = "✅ Вкл" if enabled else "❌ Выкл"
    action_text = {"ban": "🔨 Бан", "kick": "👢 Кик", "mute": "🔇 Мут"}.get(action, action)
    
    text = (
        f"🛡 *Настройки антифлуда*\n\n"
        f"Статус: {status}\n"
        f"Лимит сообщений: `{limit}`\n"
        f"Действие: {action_text}\n\n"
        f"Если пользователь отправит больше {limit} сообщений подряд, "
        f"к нему будет применено действие."
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'❌ Выключить' if enabled else '✅ Включить'}",
                callback_data=f"cfg_flood_toggle_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(f"Лимит: {limit}", callback_data="cfg_noop"),
        ],
        [
            InlineKeyboardButton("➖", callback_data=f"cfg_flood_limit_dec_{chat_id}"),
            InlineKeyboardButton("➕", callback_data=f"cfg_flood_limit_inc_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔨 Бан", callback_data=f"cfg_flood_action_ban_{chat_id}"),
            InlineKeyboardButton("👢 Кик", callback_data=f"cfg_flood_action_kick_{chat_id}"),
            InlineKeyboardButton("🔇 Мут", callback_data=f"cfg_flood_action_mute_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
        ],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def antiflood_toggle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    settings = get_antiflood_settings(chat_id)
    settings["enabled"] = not settings.get("enabled", False)
    set_antiflood_settings(chat_id, settings)
    query.answer(f"✅ Антифлуд {'включён' if settings['enabled'] else 'выключен'}")
    
    return antiflood_settings_callback(update, context)


def antiflood_limit_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[3]
    chat_id = int(parts[4])
    
    settings = get_antiflood_settings(chat_id)
    limit = settings.get("limit", 5)
    
    if action == "inc" and limit < 20:
        limit += 1
    elif action == "dec" and limit > 2:
        limit -= 1
    
    settings["limit"] = limit
    set_antiflood_settings(chat_id, settings)
    query.answer(f"Лимит: {limit}")
    
    return antiflood_settings_callback(update, context)


def antiflood_action_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[3]
    chat_id = int(parts[4])
    
    settings = get_antiflood_settings(chat_id)
    settings["action"] = action
    set_antiflood_settings(chat_id, settings)
    query.answer(f"✅ Действие: {action}")
    
    return antiflood_settings_callback(update, context)


# ═══════════════════════════════════════════════════════════════
#                      СЕРВИСНЫЕ СООБЩЕНИЯ
# ═══════════════════════════════════════════════════════════════

def service_settings_callback(update: Update, context: CallbackContext):
    """Настройки удаления сервисных сообщений"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    enabled = get_delete_service_messages(chat_id)
    status = "✅ Вкл" if enabled else "❌ Выкл"
    
    text = (
        "🧹 *Удаление сервисных сообщений*\n\n"
        f"Статус: `{status}`\n\n"
        "Автоматически удаляет системные сообщения Telegram:\n"
        "• Вступление в группу\n"
        "• Выход из группы\n"
        "• Закрепление сообщений\n"
        "• Изменение названия/фото группы\n"
        "• Приглашение пользователей\n"
        "• И другие сервисные уведомления"
    )
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'🔴 Выключить' if enabled else '🟢 Включить'}",
            callback_data=f"cfg_srv_toggle_{chat_id}"
        )],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}")],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def service_toggle_callback(update: Update, context: CallbackContext):
    """Переключает удаление сервисных сообщений"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    current = get_delete_service_messages(chat_id)
    set_delete_service_messages(chat_id, not current)
    
    if not current:
        query.answer("✅ Удаление сервисных сообщений включено")
    else:
        query.answer("❌ Удаление сервисных сообщений выключено")
    
    # Обновляем меню
    return service_settings_callback(update, context)


# ═══════════════════════════════════════════════════════════════
#                      НАСТРОЙКИ ЛОГОВ
# ═══════════════════════════════════════════════════════════════

def logs_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки логирования"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    if not get_log_settings:
        query.edit_message_text(
            "❌ Модуль логов не загружен.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}")
            ]])
        )
        return EDITING_SETTING
    
    settings = get_log_settings(chat_id)
    log_channel = settings.get("log_channel")
    events = settings.get("events", [])
    
    if log_channel:
        try:
            channel_info = context.bot.get_chat(log_channel)
            channel_name = channel_info.title or str(log_channel)
        except:
            channel_name = str(log_channel)
        channel_status = f"📢 `{channel_name}`"
    else:
        channel_status = "❌ Не настроен"
    
    text = (
        f"📋 *Настройки логирования*\n\n"
        f"Канал логов: {channel_status}\n\n"
        f"*Логируемые события:*\n"
    )
    
    for event_key, event_name in LOG_EVENTS.items():
        status = "✅" if event_key in events else "❌"
        text += f"{status} {event_name}\n"
    
    keyboard = [
        [InlineKeyboardButton(
            "📢 Указать канал логов" if not log_channel else "📢 Изменить канал",
            callback_data=f"cfg_log_setchan_{chat_id}"
        )],
    ]
    
    if log_channel:
        keyboard.append([InlineKeyboardButton(
            "🗑 Удалить канал логов",
            callback_data=f"cfg_log_delchan_{chat_id}"
        )])
    
    # Кнопки для переключения событий (по 2 в ряд)
    event_buttons = []
    for event_key, event_name in LOG_EVENTS.items():
        status = "✅" if event_key in events else "❌"
        event_buttons.append(InlineKeyboardButton(
            f"{status} {event_name.split()[1] if len(event_name.split()) > 1 else event_name}",
            callback_data=f"cfg_log_ev_{event_key}_{chat_id}"
        ))
    
    # Группируем по 2 кнопки
    for i in range(0, len(event_buttons), 2):
        keyboard.append(event_buttons[i:i+2])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}")])
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def logs_set_channel_callback(update: Update, context: CallbackContext):
    """Запрос на ввод ID канала логов"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "logs", "action": "set_channel"}
    
    text = (
        "📢 *Укажите канал для логов*\n\n"
        "Отправьте ID канала или группы, куда будут приходить логи.\n\n"
        "💡 Как узнать ID:\n"
        "1. Добавьте бота в канал/группу\n"
        "2. Перешлите любое сообщение оттуда боту @userinfobot\n"
        "3. Или используйте /addmita в том чате\n\n"
        "⚠️ Бот должен быть админом канала!"
    )
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"cfg_mod_logs_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_LOG_CHANNEL


def process_log_channel_input(update: Update, context: CallbackContext):
    """Обрабатывает ввод ID канала логов"""
    user = update.effective_user
    msg = update.effective_message
    
    if user.id not in user_editing:
        return SELECTING_CHAT
    
    edit_data = user_editing[user.id]
    chat_id = edit_data.get("chat_id")
    
    try:
        log_channel_id = int(msg.text.strip())
        
        # Проверяем, может ли бот отправлять сообщения в канал
        try:
            test_msg = context.bot.send_message(
                log_channel_id,
                "✅ Канал логов успешно подключён!",
                parse_mode=ParseMode.MARKDOWN
            )
            # Удаляем тестовое сообщение
            try:
                test_msg.delete()
            except:
                pass
        except Exception as e:
            msg.reply_text(
                f"❌ Не удалось отправить сообщение в канал.\n\n"
                f"Убедитесь, что:\n"
                f"• ID указан верно\n"
                f"• Бот добавлен в канал\n"
                f"• Бот является админом канала\n\n"
                f"Ошибка: `{e}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return WAITING_LOG_CHANNEL
        
        # Сохраняем канал
        set_log_channel(chat_id, log_channel_id)
        
        msg.reply_text(
            f"✅ Канал логов установлен!\n\n"
            f"ID: `{log_channel_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Возвращаемся к настройкам логов
        del user_editing[user.id]
        
        # Отправляем новое меню
        keyboard = [[InlineKeyboardButton("📋 К настройкам логов", callback_data=f"cfg_mod_logs_{chat_id}")]]
        msg.reply_text("Нажмите кнопку для продолжения:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        return EDITING_SETTING
        
    except ValueError:
        msg.reply_text("❌ Неверный формат. Отправьте числовой ID канала.")
        return WAITING_LOG_CHANNEL


def logs_delete_channel_callback(update: Update, context: CallbackContext):
    """Удаляет канал логов"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if remove_log_channel:
        remove_log_channel(chat_id)
        query.answer("✅ Канал логов удалён")
    else:
        query.answer("❌ Ошибка")
    
    return logs_settings_callback(update, context, chat_id_override=chat_id)


def logs_toggle_event_callback(update: Update, context: CallbackContext):
    """Переключает логирование события"""
    query = update.callback_query
    parts = query.data.split("_")
    # cfg_log_ev_{event}_{chat_id}
    event = parts[3]
    chat_id = int(parts[4])
    
    if toggle_log_event:
        new_state = toggle_log_event(chat_id, event)
        event_name = LOG_EVENTS.get(event, event)
        if new_state:
            query.answer(f"✅ {event_name} включено")
        else:
            query.answer(f"❌ {event_name} выключено")
    else:
        query.answer("❌ Ошибка")
    
    return logs_settings_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                     МЕДИА-ФИЛЬТРЫ
# ═══════════════════════════════════════════════════════════════

def media_filters_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки медиа-фильтров"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "media_filters"}
    
    if get_media_filter_settings:
        settings = get_media_filter_settings(chat_id)
        enabled = settings.get("enabled", False)
        filters = settings.get("filters", {})
        action = settings.get("action", "delete")
    else:
        enabled = False
        filters = {}
        action = "delete"
    
    status = "✅ Вкл" if enabled else "❌ Выкл"
    action_text = FILTER_ACTIONS.get(action, action) if FILTER_ACTIONS else action
    
    # Подсчёт активных фильтров
    active_count = sum(1 for v in filters.values() if v)
    total_count = len(MEDIA_TYPES) if MEDIA_TYPES else 0
    
    text = (
        f"🚫 *Медиа-фильтры*\n\n"
        f"Статус: {status}\n"
        f"Действие: {action_text}\n"
        f"Активных фильтров: `{active_count}/{total_count}`\n\n"
        f"_Настройте запрет на отправку различных типов контента._"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'✅' if enabled else '❌'} Вкл/Выкл",
                callback_data=f"cfg_mf_toggle_{chat_id}"
            ),
            InlineKeyboardButton(
                "⚡ Действие",
                callback_data=f"cfg_mf_action_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton("📋 Типы контента", callback_data=f"cfg_mf_types_{chat_id}"),
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}")],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def media_filters_types_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Показывает список типов контента для фильтрации"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    if get_media_filter_settings:
        settings = get_media_filter_settings(chat_id)
        filters = settings.get("filters", {})
    else:
        filters = {}
    
    text = (
        f"📋 *Типы контента*\n\n"
        f"Выберите типы контента, которые нужно запретить:\n"
        f"✅ = разрешено, 🚫 = запрещено"
    )
    
    keyboard = []
    row = []
    
    if MEDIA_TYPES:
        for media_type, info in MEDIA_TYPES.items():
            is_blocked = filters.get(media_type, False)
            icon = "🚫" if is_blocked else "✅"
            name = info["name"]
            
            row.append(
                InlineKeyboardButton(
                    f"{icon} {name}",
                    callback_data=f"cfg_mf_t_{media_type}_{chat_id}"
                )
            )
            
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_mod_mediafilters_{chat_id}")])
    
    try:
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest:
        pass  # Message not modified
    return EDITING_SETTING


def media_filter_toggle_callback(update: Update, context: CallbackContext):
    """Включает/выключает медиа-фильтры"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if toggle_media_filters_enabled:
        new_state = toggle_media_filters_enabled(chat_id)
        if new_state:
            query.answer("✅ Медиа-фильтры включены")
        else:
            query.answer("❌ Медиа-фильтры выключены")
    else:
        query.answer("❌ Ошибка")
    
    return media_filters_settings_callback(update, context, chat_id_override=chat_id)


def media_filter_type_toggle_callback(update: Update, context: CallbackContext):
    """Переключает фильтр для конкретного типа медиа"""
    query = update.callback_query
    # cfg_mf_t_{media_type}_{chat_id}
    # media_type может содержать _, поэтому берём chat_id с конца
    data = query.data
    # Убираем префикс cfg_mf_t_
    rest = data[9:]  # после "cfg_mf_t_" (9 символов)
    # chat_id - последняя часть после _
    last_underscore = rest.rfind("_")
    media_type = rest[:last_underscore]
    chat_id = int(rest[last_underscore + 1:])
    
    if toggle_media_filter:
        new_state = toggle_media_filter(chat_id, media_type)
        type_name = MEDIA_TYPES.get(media_type, {}).get("name", media_type) if MEDIA_TYPES else media_type
        if new_state:
            query.answer(f"🚫 {type_name} запрещены")
        else:
            query.answer(f"✅ {type_name} разрешены")
    else:
        query.answer("❌ Ошибка")
    
    return media_filters_types_callback(update, context, chat_id_override=chat_id)


def media_filter_action_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Показывает меню выбора действия"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    if get_media_filter_settings:
        settings = get_media_filter_settings(chat_id)
        current_action = settings.get("action", "delete")
    else:
        current_action = "delete"
    
    text = (
        f"⚡ *Действие при нарушении*\n\n"
        f"Текущее: {FILTER_ACTIONS.get(current_action, current_action) if FILTER_ACTIONS else current_action}\n\n"
        f"Выберите действие:"
    )
    
    keyboard = []
    
    if FILTER_ACTIONS:
        for action, name in FILTER_ACTIONS.items():
            icon = "✅ " if action == current_action else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon}{name}",
                    callback_data=f"cfg_mf_setact_{action}_{chat_id}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_mod_mediafilters_{chat_id}")])
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def media_filter_set_action_callback(update: Update, context: CallbackContext):
    """Устанавливает действие для медиа-фильтров"""
    query = update.callback_query
    parts = query.data.split("_")
    # cfg_mf_setact_{action}_{chat_id}
    action = parts[3]
    chat_id = int(parts[4])
    
    if set_filter_action:
        set_filter_action(chat_id, action)
        action_name = FILTER_ACTIONS.get(action, action) if FILTER_ACTIONS else action
        query.answer(f"✅ Действие: {action_name}")
    else:
        query.answer("❌ Ошибка")
    
    return media_filter_action_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      CAS ANTI-SPAM
# ═══════════════════════════════════════════════════════════════

def cas_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки CAS Anti-Spam"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "cas"}
    
    if get_cas_settings:
        settings = get_cas_settings(chat_id)
        enabled = settings.get("enabled", False)
        action = settings.get("action", "ban")
        notify = settings.get("notify", True)
    else:
        enabled = False
        action = "ban"
        notify = True
    
    status = "✅ Вкл" if enabled else "❌ Выкл"
    action_text = CAS_ACTIONS.get(action, action) if CAS_ACTIONS else action
    notify_text = "✅ Да" if notify else "❌ Нет"
    
    text = (
        f"🛡 *CAS Anti-Spam*\n\n"
        f"Статус: {status}\n"
        f"Действие: {action_text}\n"
        f"Уведомления: {notify_text}\n\n"
        f"_CAS (Combot Anti-Spam) — глобальная база спамеров Telegram._\n"
        f"_При входе нового участника бот проверит его в базе CAS._"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'❌ Выключить' if enabled else '✅ Включить'}",
                callback_data=f"cfg_cas_toggle_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton("⚡ Действие", callback_data=f"cfg_cas_action_{chat_id}"),
            InlineKeyboardButton(
                f"🔔 Уведомления: {'Вкл' if notify else 'Выкл'}",
                callback_data=f"cfg_cas_notify_{chat_id}"
            ),
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}")],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def cas_toggle_callback(update: Update, context: CallbackContext):
    """Включает/выключает CAS"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if toggle_cas:
        new_state = toggle_cas(chat_id)
        if new_state:
            query.answer("✅ CAS Anti-Spam включён")
        else:
            query.answer("❌ CAS Anti-Spam выключен")
    else:
        query.answer("❌ Модуль CAS не загружен")
    
    return cas_settings_callback(update, context, chat_id_override=chat_id)


def cas_notify_callback(update: Update, context: CallbackContext):
    """Переключает уведомления CAS"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    if toggle_cas_notify:
        new_state = toggle_cas_notify(chat_id)
        if new_state:
            query.answer("✅ Уведомления включены")
        else:
            query.answer("❌ Уведомления выключены")
    else:
        query.answer("❌ Ошибка")
    
    return cas_settings_callback(update, context, chat_id_override=chat_id)


def cas_action_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Показывает меню выбора действия CAS"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    
    if get_cas_settings:
        settings = get_cas_settings(chat_id)
        current_action = settings.get("action", "ban")
    else:
        current_action = "ban"
    
    text = (
        f"⚡ *Действие при обнаружении спамера*\n\n"
        f"Текущее: {CAS_ACTIONS.get(current_action, current_action) if CAS_ACTIONS else current_action}\n\n"
        f"Выберите действие:"
    )
    
    keyboard = []
    
    if CAS_ACTIONS:
        for action, name in CAS_ACTIONS.items():
            icon = "✅ " if action == current_action else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon}{name}",
                    callback_data=f"cfg_cas_setact_{action}_{chat_id}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_mod_cas_{chat_id}")])
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def cas_set_action_callback(update: Update, context: CallbackContext):
    """Устанавливает действие для CAS"""
    query = update.callback_query
    parts = query.data.split("_")
    # cfg_cas_setact_{action}_{chat_id}
    action = parts[3]
    chat_id = int(parts[4])
    
    if set_cas_action:
        set_cas_action(chat_id, action)
        action_name = CAS_ACTIONS.get(action, action) if CAS_ACTIONS else action
        query.answer(f"✅ Действие: {action_name}")
    else:
        query.answer("❌ Ошибка")
    
    return cas_action_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      АНТИКАНАЛ
# ═══════════════════════════════════════════════════════════════

def antichannel_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Настройки антиканала"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
        query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "antichannel"}
    
    settings = get_antichannel_settings(chat_id)
    enabled = settings.get("enabled", False)
    
    status = "✅ Вкл" if enabled else "❌ Выкл"
    
    text = (
        f"📢 *Антиканал*\n\n"
        f"Статус: {status}\n\n"
        f"_Эта функция удаляет сообщения от пользователей,_\n"
        f"_которые пишут от имени канала (анонимно)._\n\n"
        f"_Полезно для защиты от спама и рекламы через каналы._"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'❌ Выключить' if enabled else '✅ Включить'}",
                callback_data=f"cfg_achan_toggle_{chat_id}"
            ),
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}")],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def antichannel_toggle_callback(update: Update, context: CallbackContext):
    """Включает/выключает антиканал"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    new_state = toggle_antichannel(chat_id)
    if new_state:
        query.answer("✅ Антиканал включён")
    else:
        query.answer("❌ Антиканал выключен")
    
    return antichannel_settings_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      ЧЁРНЫЙ СПИСОК
# ═══════════════════════════════════════════════════════════════

def blacklist_settings_callback(update: Update, context: CallbackContext):
    """Настройки чёрного списка"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    settings = get_blacklist_settings(chat_id)
    enabled = settings.get("enabled", False)
    words = settings.get("words", [])
    action = settings.get("action", "delete")
    
    status = "✅ Вкл" if enabled else "❌ Выкл"
    action_text = {"delete": "🗑 Удалить", "warn": "⚠️ Варн", "mute": "🔇 Мут", "ban": "🔨 Бан"}.get(action, action)
    
    text = (
        f"🚫 *Чёрный список слов*\n\n"
        f"Статус: {status}\n"
        f"Действие: {action_text}\n"
        f"Слов в списке: `{len(words)}`\n\n"
    )
    
    if words:
        text += "*Список:*\n"
        for w in words[:10]:
            text += f"• `{w}`\n"
        if len(words) > 10:
            text += f"\n_...и ещё {len(words) - 10}_"
    else:
        text += "_Список пуст_\n\n"
        text += "Добавьте слово командой:\n`/addblacklist <слово>`"
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'❌ Выключить' if enabled else '✅ Включить'}",
                callback_data=f"cfg_bl_toggle_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton("🗑 Удалить", callback_data=f"cfg_bl_action_delete_{chat_id}"),
            InlineKeyboardButton("⚠️ Варн", callback_data=f"cfg_bl_action_warn_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔇 Мут", callback_data=f"cfg_bl_action_mute_{chat_id}"),
            InlineKeyboardButton("🔨 Бан", callback_data=f"cfg_bl_action_ban_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
        ],
    ]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def blacklist_toggle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    
    settings = get_blacklist_settings(chat_id)
    settings["enabled"] = not settings.get("enabled", False)
    set_blacklist_settings(chat_id, settings)
    query.answer(f"✅ Чёрный список {'включён' if settings['enabled'] else 'выключен'}")
    
    return blacklist_settings_callback(update, context)


def blacklist_action_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[3]
    chat_id = int(parts[4])
    
    settings = get_blacklist_settings(chat_id)
    settings["action"] = action
    set_blacklist_settings(chat_id, settings)
    query.answer(f"✅ Действие: {action}")
    
    return blacklist_settings_callback(update, context)


# ═══════════════════════════════════════════════════════════════
#                      АДМИНЫ БОТА
# ═══════════════════════════════════════════════════════════════

def admins_settings_callback(update: Update, context: CallbackContext, chat_id_override=None):
    """Управление админами бота"""
    query = update.callback_query
    
    if chat_id_override:
        chat_id = chat_id_override
    else:
        chat_id = int(query.data.split("_")[3])
    
    query.answer()
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "admins"}
    
    admins = get_bot_admins(chat_id)
    
    text = f"👥 *Админы бота*\n\nВсего: `{len(admins)}`\n\n"
    
    keyboard = []
    
    if admins:
        text += "*Список (нажмите для удаления):*\n"
        for admin_id, data in list(admins.items())[:10]:
            role = data.get("role", "moderator")
            role_emoji = {"owner": "👑", "admin": "⭐", "moderator": "🛡"}.get(role, "👤")
            role_name = ROLES.get(role, role)
            text += f"• {role_emoji} `{admin_id}` — {role_name}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑 Удалить {admin_id}",
                    callback_data=f"cfg_adm_del_{admin_id}_{chat_id}"
                )
            ])
    else:
        text += "_Нет админов_"
    
    text += (
        "\n\n*Роли:*\n"
        "👑 Owner — полный доступ\n"
        "⭐ Admin — все настройки\n"
        "🛡 Moderator — баны/муты/варны"
    )
    
    keyboard.append([
        InlineKeyboardButton("➕ Добавить админа", callback_data=f"cfg_adm_add_{chat_id}"),
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data=f"cfg_chat_{chat_id}"),
    ])
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITING_SETTING


def admin_add_callback(update: Update, context: CallbackContext):
    """Начинает добавление админа"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    query.answer()
    
    user_editing[update.effective_user.id] = {"chat_id": chat_id, "module": "admins", "action": "add"}
    
    text = (
        "➕ *Добавление админа бота*\n\n"
        "Отправьте *ID пользователя* которого хотите добавить:\n\n"
        "_Узнать ID можно через @userinfobot_"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Отмена", callback_data=f"cfg_mod_admins_{chat_id}")]]
    
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_ADMIN_ID


def process_admin_id(update: Update, context: CallbackContext):
    """Обрабатывает ввод ID админа"""
    user = update.effective_user
    text = update.effective_message.text.strip()
    
    editing = user_editing.get(user.id, {})
    chat_id = editing.get("chat_id")
    
    if not chat_id:
        update.effective_message.reply_text("❌ Ошибка. Используйте /config")
        return SELECTING_CHAT
    
    try:
        admin_id = int(text)
    except ValueError:
        update.effective_message.reply_text("❌ Неверный формат. Отправьте числовой ID.")
        return WAITING_ADMIN_ID
    
    # Сохраняем ID и показываем выбор роли
    user_editing[user.id]["admin_id"] = admin_id
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 Owner", callback_data=f"cfg_adm_role_owner_{admin_id}_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⭐ Admin", callback_data=f"cfg_adm_role_admin_{admin_id}_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🛡 Moderator", callback_data=f"cfg_adm_role_moderator_{admin_id}_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Отмена", callback_data=f"cfg_mod_admins_{chat_id}"),
        ],
    ])
    
    update.effective_message.reply_text(
        f"👤 *ID:* `{admin_id}`\n\n"
        f"Выберите *роль* для этого админа:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )
    return EDITING_SETTING


def admin_role_callback(update: Update, context: CallbackContext):
    """Устанавливает роль админа"""
    query = update.callback_query
    user = update.effective_user
    parts = query.data.split("_")
    # cfg_adm_role_{role}_{admin_id}_{chat_id}
    role = parts[3]
    admin_id = int(parts[4])
    chat_id = int(parts[5])
    
    if add_bot_admin:
        add_bot_admin(chat_id, admin_id, role, user.id)
        role_name = ROLES.get(role, role)
        query.answer(f"✅ Админ {admin_id} добавлен как {role_name}")
    else:
        query.answer("❌ Ошибка")
    
    return admins_settings_callback(update, context, chat_id_override=chat_id)


def admin_delete_callback(update: Update, context: CallbackContext):
    """Удаляет админа"""
    query = update.callback_query
    parts = query.data.split("_")
    # cfg_adm_del_{admin_id}_{chat_id}
    admin_id = int(parts[3])
    chat_id = int(parts[4])
    
    if remove_bot_admin:
        if remove_bot_admin(chat_id, admin_id):
            query.answer(f"✅ Админ {admin_id} удалён")
        else:
            query.answer("❌ Админ не найден")
    else:
        query.answer("❌ Ошибка")
    
    return admins_settings_callback(update, context, chat_id_override=chat_id)


# ═══════════════════════════════════════════════════════════════
#                      ОБЩИЕ CALLBACKS
# ═══════════════════════════════════════════════════════════════

def back_to_main(update: Update, context: CallbackContext):
    update.callback_query.answer()
    return show_main_menu(update, context)


def refresh_callback(update: Update, context: CallbackContext):
    update.callback_query.answer("🔄 Обновлено!")
    return show_main_menu(update, context)


def close_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    try:
        query.message.delete()
    except BadRequest:
        query.edit_message_text("✅ Панель закрыта.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
#                      ПОЛНЫЙ СБРОС БОТА
# ═══════════════════════════════════════════════════════════════

def reset_bot_callback(update: Update, context: CallbackContext):
    """Показывает подтверждение сброса бота"""
    query = update.callback_query
    user = update.effective_user
    
    # Проверка что это владелец
    if user.id != OWNER_ID:
        query.answer("❌ Только владелец бота может выполнить сброс!", show_alert=True)
        return SELECTING_CHAT
    
    query.answer()
    
    text = (
        "⚠️ *ВНИМАНИЕ! ПОЛНЫЙ СБРОС БОТА*\n\n"
        "Это действие удалит ВСЕ данные бота:\n"
        "• 📋 Все сохранённые чаты\n"
        "• 👥 Всех пользователей\n"
        "• ⚙️ Все настройки (приветствия, капча, фильтры...)\n"
        "• 📝 Все заметки и правила\n"
        "• 📋 Все логи\n\n"
        "❗ Файл `.env` НЕ будет затронут.\n\n"
        "🔴 *Это действие НЕЛЬЗЯ отменить!*\n\n"
        "Вы уверены?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, сбросить всё", callback_data="cfg_reset_confirm"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cfg_refresh"),
        ],
    ]
    
    query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SELECTING_CHAT


def reset_confirm_callback(update: Update, context: CallbackContext):
    """Выполняет полный сброс бота"""
    query = update.callback_query
    user = update.effective_user
    
    # Повторная проверка что это владелец
    if user.id != OWNER_ID:
        query.answer("❌ Только владелец бота может выполнить сброс!", show_alert=True)
        return SELECTING_CHAT
    
    query.answer("⏳ Выполняется сброс...")
    
    # Выполняем сброс
    success, result = reset_all_data()
    
    if success:
        deleted_files = result
        files_text = "\n".join([f"• {f}" for f in deleted_files]) if deleted_files else "Нет файлов"
        
        text = (
            "✅ *СБРОС ВЫПОЛНЕН УСПЕШНО!*\n\n"
            f"🗑 Удалённые файлы:\n{files_text}\n\n"
            "Бот сброшен до начального состояния.\n"
            "Все чаты нужно добавить заново через /addmita"
        )
        
        LOGGER.warning(f"ПОЛНЫЙ СБРОС БОТА выполнен пользователем {user.id} ({user.first_name})")
    else:
        text = (
            "❌ *ОШИБКА ПРИ СБРОСЕ!*\n\n"
            f"Причина: {result}\n\n"
            "Попробуйте позже или удалите файлы вручную из папки `data/`"
        )
    
    keyboard = [[
        InlineKeyboardButton("🏠 В главное меню", callback_data="cfg_refresh"),
    ]]
    
    query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SELECTING_CHAT


def noop_callback(update: Update, context: CallbackContext):
    """Пустой callback"""
    update.callback_query.answer()
    return EDITING_SETTING


def cancel_cmd(update: Update, context: CallbackContext):
    update.effective_message.reply_text("❌ Действие отменено.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

config_conversation = ConversationHandler(
    entry_points=[
        CommandHandler(["config", "settings"], config_cmd),
    ],
    states={
        SELECTING_CHAT: [
            CallbackQueryHandler(chat_settings_callback, pattern=r"^cfg_chat_-?\d+$"),
            CallbackQueryHandler(refresh_callback, pattern=r"^cfg_refresh$"),
            CallbackQueryHandler(close_callback, pattern=r"^cfg_close$"),
            CallbackQueryHandler(reset_bot_callback, pattern=r"^cfg_reset_bot$"),
            CallbackQueryHandler(reset_confirm_callback, pattern=r"^cfg_reset_confirm$"),
        ],
        SELECTING_MODULE: [
            CallbackQueryHandler(welcome_settings_callback, pattern=r"^cfg_mod_welcome_-?\d+$"),
            CallbackQueryHandler(captcha_settings_callback, pattern=r"^cfg_mod_captcha_-?\d+$"),
            CallbackQueryHandler(rules_settings_callback, pattern=r"^cfg_mod_rules_-?\d+$"),
            CallbackQueryHandler(filters_settings_callback, pattern=r"^cfg_mod_filters_-?\d+$"),
            CallbackQueryHandler(notes_settings_callback, pattern=r"^cfg_mod_notes_-?\d+$"),
            CallbackQueryHandler(warns_settings_callback, pattern=r"^cfg_mod_warns_-?\d+$"),
            CallbackQueryHandler(antiflood_settings_callback, pattern=r"^cfg_mod_antiflood_-?\d+$"),
            CallbackQueryHandler(blacklist_settings_callback, pattern=r"^cfg_mod_blacklist_-?\d+$"),
            CallbackQueryHandler(admins_settings_callback, pattern=r"^cfg_mod_admins_-?\d+$"),
            CallbackQueryHandler(service_settings_callback, pattern=r"^cfg_mod_service_-?\d+$"),
            CallbackQueryHandler(logs_settings_callback, pattern=r"^cfg_mod_logs_-?\d+$"),
            CallbackQueryHandler(media_filters_settings_callback, pattern=r"^cfg_mod_mediafilters_-?\d+$"),
            CallbackQueryHandler(cas_settings_callback, pattern=r"^cfg_mod_cas_-?\d+$"),
            CallbackQueryHandler(antichannel_settings_callback, pattern=r"^cfg_mod_antichannel_-?\d+$"),
            CallbackQueryHandler(back_to_main, pattern=r"^cfg_back_main$"),
        ],
        EDITING_SETTING: [
            # Приветствия
            CallbackQueryHandler(toggle_welcome, pattern=r"^cfg_wel_toggle_-?\d+$"),
            CallbackQueryHandler(toggle_lockdown, pattern=r"^cfg_lockdown_toggle_-?\d+$"),
            CallbackQueryHandler(welcome_edit_callback, pattern=r"^cfg_wel_edit_-?\d+$"),
            CallbackQueryHandler(welcome_delete_after_callback, pattern=r"^cfg_wel_del_\d+_-?\d+$"),
            CallbackQueryHandler(welcome_add_button_callback, pattern=r"^cfg_wel_addbtn_-?\d+$"),
            CallbackQueryHandler(welcome_delete_button_callback, pattern=r"^cfg_wel_delbtn_\d+_-?\d+$"),
            # Капча
            CallbackQueryHandler(toggle_captcha, pattern=r"^cfg_cap_toggle_-?\d+$"),
            CallbackQueryHandler(set_captcha_mode, pattern=r"^cfg_cap_mode_\w+_-?\d+$"),
            CallbackQueryHandler(set_captcha_timeout, pattern=r"^cfg_cap_timeout_\d+_-?\d+$"),
            CallbackQueryHandler(set_newbie_mute, pattern=r"^cfg_cap_newbie_\d+_-?\d+$"),
            # Правила
            CallbackQueryHandler(rules_edit_callback, pattern=r"^cfg_rules_edit_-?\d+$"),
            CallbackQueryHandler(rules_clear_callback, pattern=r"^cfg_rules_clear_-?\d+$"),
            # Фильтры
            CallbackQueryHandler(filter_add_callback, pattern=r"^cfg_flt_add_-?\d+$"),
            CallbackQueryHandler(filter_delete_callback, pattern=r"^cfg_flt_del_.+_-?\d+$"),
            CallbackQueryHandler(filter_autodelete_callback, pattern=r"^cfg_flt_autodel_-?\d+$"),
            CallbackQueryHandler(filter_autodelete_set_callback, pattern=r"^cfg_flt_adel_\d+_-?\d+$"),
            # Мультифильтры
            CallbackQueryHandler(multi_filter_add_callback, pattern=r"^cfg_mflt_add_-?\d+$"),
            CallbackQueryHandler(multi_filter_done_callback, pattern=r"^cfg_mflt_done_-?\d+$"),
            CallbackQueryHandler(multi_filter_delete_callback, pattern=r"^cfg_mflt_del_.+_-?\d+$"),
            # Заметки
            CallbackQueryHandler(note_add_callback, pattern=r"^cfg_note_add_-?\d+$"),
            CallbackQueryHandler(note_view_callback, pattern=r"^cfg_note_view_.+_-?\d+$"),
            CallbackQueryHandler(note_delete_callback, pattern=r"^cfg_note_del_.+_-?\d+$"),
            CallbackQueryHandler(note_buttons_callback, pattern=r"^cfg_note_btns_.+_-?\d+$"),
            CallbackQueryHandler(note_button_delete_callback, pattern=r"^cfg_note_btndel_.+_\d+_-?\d+$"),
            # Админы
            CallbackQueryHandler(admin_add_callback, pattern=r"^cfg_adm_add_-?\d+$"),
            CallbackQueryHandler(admin_delete_callback, pattern=r"^cfg_adm_del_\d+_-?\d+$"),
            CallbackQueryHandler(admin_role_callback, pattern=r"^cfg_adm_role_\w+_\d+_-?\d+$"),
            # Варны
            CallbackQueryHandler(warns_limit_callback, pattern=r"^cfg_warns_limit_(inc|dec)_-?\d+$"),
            CallbackQueryHandler(warns_action_callback, pattern=r"^cfg_warns_action_\w+_-?\d+$"),
            # Антифлуд
            CallbackQueryHandler(antiflood_toggle_callback, pattern=r"^cfg_flood_toggle_-?\d+$"),
            CallbackQueryHandler(antiflood_limit_callback, pattern=r"^cfg_flood_limit_(inc|dec)_-?\d+$"),
            CallbackQueryHandler(antiflood_action_callback, pattern=r"^cfg_flood_action_\w+_-?\d+$"),
            # Чёрный список
            CallbackQueryHandler(blacklist_toggle_callback, pattern=r"^cfg_bl_toggle_-?\d+$"),
            CallbackQueryHandler(blacklist_action_callback, pattern=r"^cfg_bl_action_\w+_-?\d+$"),
            # Сервисные сообщения
            CallbackQueryHandler(service_toggle_callback, pattern=r"^cfg_srv_toggle_-?\d+$"),
            # Логи
            CallbackQueryHandler(logs_settings_callback, pattern=r"^cfg_mod_logs_-?\d+$"),
            CallbackQueryHandler(logs_set_channel_callback, pattern=r"^cfg_log_setchan_-?\d+$"),
            CallbackQueryHandler(logs_delete_channel_callback, pattern=r"^cfg_log_delchan_-?\d+$"),
            CallbackQueryHandler(logs_toggle_event_callback, pattern=r"^cfg_log_ev_\w+_-?\d+$"),
            # Медиа-фильтры
            CallbackQueryHandler(media_filters_settings_callback, pattern=r"^cfg_mod_mediafilters_-?\d+$"),
            CallbackQueryHandler(media_filter_toggle_callback, pattern=r"^cfg_mf_toggle_-?\d+$"),
            CallbackQueryHandler(media_filters_types_callback, pattern=r"^cfg_mf_types_-?\d+$"),
            CallbackQueryHandler(media_filter_type_toggle_callback, pattern=r"^cfg_mf_t_\w+_-?\d+$"),
            CallbackQueryHandler(media_filter_action_callback, pattern=r"^cfg_mf_action_-?\d+$"),
            CallbackQueryHandler(media_filter_set_action_callback, pattern=r"^cfg_mf_setact_\w+_-?\d+$"),
            # CAS Anti-Spam
            CallbackQueryHandler(cas_settings_callback, pattern=r"^cfg_mod_cas_-?\d+$"),
            CallbackQueryHandler(cas_toggle_callback, pattern=r"^cfg_cas_toggle_-?\d+$"),
            CallbackQueryHandler(cas_notify_callback, pattern=r"^cfg_cas_notify_-?\d+$"),
            CallbackQueryHandler(cas_action_callback, pattern=r"^cfg_cas_action_-?\d+$"),
            CallbackQueryHandler(cas_set_action_callback, pattern=r"^cfg_cas_setact_\w+_-?\d+$"),
            # Антиканал
            CallbackQueryHandler(antichannel_settings_callback, pattern=r"^cfg_mod_antichannel_-?\d+$"),
            CallbackQueryHandler(antichannel_toggle_callback, pattern=r"^cfg_achan_toggle_-?\d+$"),
            # Навигация
            CallbackQueryHandler(noop_callback, pattern=r"^cfg_noop$"),
            CallbackQueryHandler(chat_settings_callback, pattern=r"^cfg_chat_-?\d+$"),
            CallbackQueryHandler(welcome_settings_callback, pattern=r"^cfg_mod_welcome_-?\d+$"),
            CallbackQueryHandler(captcha_settings_callback, pattern=r"^cfg_mod_captcha_-?\d+$"),
            CallbackQueryHandler(rules_settings_callback, pattern=r"^cfg_mod_rules_-?\d+$"),
            CallbackQueryHandler(filters_settings_callback, pattern=r"^cfg_mod_filters_-?\d+$"),
            CallbackQueryHandler(notes_settings_callback, pattern=r"^cfg_mod_notes_-?\d+$"),
            CallbackQueryHandler(warns_settings_callback, pattern=r"^cfg_mod_warns_-?\d+$"),
            CallbackQueryHandler(antiflood_settings_callback, pattern=r"^cfg_mod_antiflood_-?\d+$"),
            CallbackQueryHandler(blacklist_settings_callback, pattern=r"^cfg_mod_blacklist_-?\d+$"),
            CallbackQueryHandler(admins_settings_callback, pattern=r"^cfg_mod_admins_-?\d+$"),
            CallbackQueryHandler(back_to_main, pattern=r"^cfg_back_main$"),
        ],
        WAITING_RULES_INPUT: [
            MessageHandler(Filters.text & ~Filters.command, process_rules_input),
            CallbackQueryHandler(rules_settings_callback, pattern=r"^cfg_mod_rules_-?\d+$"),
        ],
        WAITING_WELCOME_INPUT: [
            MessageHandler(Filters.text & ~Filters.command, process_welcome_input),
            CallbackQueryHandler(welcome_settings_callback, pattern=r"^cfg_mod_welcome_-?\d+$"),
        ],
        WAITING_FILTER_KEYWORD: [
            MessageHandler(Filters.text & ~Filters.command, process_filter_keyword),
            CallbackQueryHandler(filters_settings_callback, pattern=r"^cfg_mod_filters_-?\d+$"),
        ],
        WAITING_FILTER_RESPONSE: [
            MessageHandler(
                (Filters.text | Filters.animation | Filters.sticker | Filters.photo | Filters.video | Filters.document) & ~Filters.command,
                process_filter_response
            ),
            CallbackQueryHandler(filters_settings_callback, pattern=r"^cfg_mod_filters_-?\d+$"),
        ],
        WAITING_NOTE_NAME: [
            MessageHandler(Filters.text & ~Filters.command, process_note_name),
            CallbackQueryHandler(notes_settings_callback, pattern=r"^cfg_mod_notes_-?\d+$"),
        ],
        WAITING_NOTE_CONTENT: [
            MessageHandler(Filters.text & ~Filters.command, process_note_content),
            CallbackQueryHandler(notes_settings_callback, pattern=r"^cfg_mod_notes_-?\d+$"),
        ],
        WAITING_ADMIN_ID: [
            MessageHandler(Filters.text & ~Filters.command, process_admin_id),
            CallbackQueryHandler(admin_role_callback, pattern=r"^cfg_adm_role_\w+_\d+_-?\d+$"),
            CallbackQueryHandler(admins_settings_callback, pattern=r"^cfg_mod_admins_-?\d+$"),
        ],
        WAITING_MULTI_KEYWORD: [
            MessageHandler(Filters.text & ~Filters.command, process_multi_keyword),
            CallbackQueryHandler(filters_settings_callback, pattern=r"^cfg_mod_filters_-?\d+$"),
        ],
        WAITING_MULTI_RESPONSES: [
            MessageHandler(
                (Filters.text | Filters.animation | Filters.sticker | Filters.photo) & ~Filters.command,
                process_multi_response
            ),
            CallbackQueryHandler(multi_filter_done_callback, pattern=r"^cfg_mflt_done_-?\d+$"),
            CallbackQueryHandler(filters_settings_callback, pattern=r"^cfg_mod_filters_-?\d+$"),
        ],
        WAITING_LOG_CHANNEL: [
            MessageHandler(Filters.text & ~Filters.command, process_log_channel_input),
            CallbackQueryHandler(logs_settings_callback, pattern=r"^cfg_mod_logs_-?\d+$"),
        ],
        WAITING_WELCOME_BUTTON: [
            MessageHandler(Filters.text & ~Filters.command, process_welcome_button),
            CallbackQueryHandler(welcome_settings_callback, pattern=r"^cfg_mod_welcome_-?\d+$"),
        ],
        WAITING_NOTE_BUTTON: [
            MessageHandler(Filters.text & ~Filters.command, process_note_button),
            CallbackQueryHandler(note_buttons_callback, pattern=r"^cfg_note_btns_.+_-?\d+$"),
            CallbackQueryHandler(note_view_callback, pattern=r"^cfg_note_view_.+_-?\d+$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_cmd),
        CommandHandler("config", config_cmd),
    ],
    per_user=True,
    per_chat=True,
    per_message=False,
    allow_reentry=True,
)

dispatcher.add_handler(config_conversation)


__mod_name__ = "⚙️ Настройки"

__help__ = """
*Централизованная панель настроек:*

Команда /config открывает панель управления в ЛС.

📋 *Доступные настройки:*
• 👋 Приветствия — вкл/выкл
• 🔐 Капча — режим, таймаут
• 📜 Правила — редактирование
• 📝 Фильтры — просмотр
• 📌 Заметки — просмотр
• ⚠️ Варны — лимит, действие
• 🛡 Антифлуд — лимит, действие
• 🚫 Чёрный список — действие
• 👥 Админы бота — просмотр
"""
