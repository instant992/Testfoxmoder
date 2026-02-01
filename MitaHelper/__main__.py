# -*- coding: utf-8 -*-
"""
MitaHelper - Главный модуль запуска
"""

import html
import importlib
import json
import re
import time
import traceback
from platform import python_version

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram import __version__ as telever
from telegram.error import (
    BadRequest,
    ChatMigrated,
    NetworkError,
    TelegramError,
    TimedOut,
    Unauthorized,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import escape_markdown

from MitaHelper import (
    BOT_ID,
    BOT_NAME,
    BOT_USERNAME,
    LOGGER,
    OWNER_ID,
    START_IMG,
    SUPPORT_CHAT,
    TOKEN,
    StartTime,
    dispatcher,
    updater,
    SUDO_USERS,
    DEV_USERS,
)
from MitaHelper.modules import ALL_MODULES
from MitaHelper.modules.helper_funcs.chat_status import is_user_admin
from MitaHelper.modules.helper_funcs.misc import paginate_modules


def get_readable_time(seconds: int) -> str:
    """Преобразует секунды в читаемый формат времени"""
    count = 0
    readable_time = ""
    time_list = []
    time_suffix_list = ["сек", "мин", "ч", "дн"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    
    if len(time_list) == 4:
        readable_time += f"{time_list.pop()} "

    time_list.reverse()
    readable_time += " ".join(time_list)

    return readable_time


# ═══════════════════════════════════════════════════════════════
#                        ТЕКСТЫ СООБЩЕНИЙ
# ═══════════════════════════════════════════════════════════════

PM_START_TEXT = """
🤖 *Привет*, {}!

Я *{}* — мощный бот для управления группами Telegram.

➜ Нажмите *Помощь*, чтобы узнать мои команды.
➜ Нажмите *Добавить в группу*, чтобы добавить меня в чат.

📊 *Статистика:*
├ Время работы: `{}`
├ Python: `{}`
└ PTB: `{}`
"""

HELP_STRINGS = """
🔧 *Доступные модули:*

Нажмите на кнопку ниже, чтобы получить информацию о модуле.

📌 *Основные команды:*
• /start - Запустить бота
• /help - Показать это сообщение
• /settings - Настройки чата
"""

# Кнопки главного меню
MAIN_BUTTONS = [
    [
        InlineKeyboardButton(
            text="➕ Добавить в группу",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
        ),
    ],
    [
        InlineKeyboardButton(text="📚 Помощь", callback_data="help_back"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="user_settings"),
    ],
    [
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_"),
        InlineKeyboardButton(text="💬 Поддержка", url=f"https://t.me/{SUPPORT_CHAT}"),
    ],
]

# ═══════════════════════════════════════════════════════════════
#                      ИМПОРТ МОДУЛЕЙ
# ═══════════════════════════════════════════════════════════════

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []
CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module(f"MitaHelper.modules.{module_name}")
    
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception(f"Дублирующееся имя модуля: {imported_module.__mod_name__.lower()}")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


def send_help(chat_id, text, keyboard=None):
    """Отправляет сообщение помощи"""
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )


# ═══════════════════════════════════════════════════════════════
#                         ОБРАБОТЧИКИ
# ═══════════════════════════════════════════════════════════════

def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    args = context.args
    uptime = get_readable_time((time.time() - StartTime))
    
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower() == "config":
                # Перенаправляем на /config
                update.effective_message.reply_text(
                    "⚙️ Открываю панель настроек...\n\n"
                    "Используйте /config для управления чатами."
                )
                return
            elif args[0].lower().startswith("ghelp_"):
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                send_help(
                    update.effective_chat.id,
                    HELPABLE[mod].__help__,
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="◀️ Назад", callback_data="help_back")]]
                    ),
                )
            elif args[0].lower() == "markdownhelp":
                markdown_help_sender(update)
            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))
                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)
        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name),
                    BOT_NAME,
                    uptime,
                    python_version(),
                    telever,
                ),
                reply_markup=InlineKeyboardMarkup(MAIN_BUTTONS),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
    else:
        update.effective_message.reply_text(
            f"🤖 Привет! Я *{BOT_NAME}*\n\n"
            f"⏱ Время работы: `{uptime}`\n\n"
            "Напишите /help для списка команд.",
            parse_mode=ParseMode.MARKDOWN,
        )


def help_button(update: Update, context: CallbackContext):
    """Обработчик кнопок помощи"""
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                f"📖 *Команды модуля* `{HELPABLE[module].__mod_name__}`:\n\n"
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="◀️ Назад", callback_data="help_back")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )

        elif back_match:
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                ),
            )

        query.answer()

    except BadRequest:
        pass


# Импорт настроек пользователей
try:
    from MitaHelper.modules.database import get_delete_mod_commands, set_delete_mod_commands
except ImportError:
    get_delete_mod_commands = None
    set_delete_mod_commands = None


def user_settings_callback(update: Update, context: CallbackContext):
    """Обработчик настроек пользователя в ЛС"""
    query = update.callback_query
    user = update.effective_user
    
    if query.data == "user_settings":
        # Показываем меню настроек
        delete_enabled = get_delete_mod_commands(user.id) if get_delete_mod_commands else False
        delete_status = "✅ Вкл" if delete_enabled else "❌ Выкл"
        
        text = f"""
⚙️ *Ваши настройки*

Здесь вы можете настроить поведение бота для себя.

🗑 *Удалять команды модерации:* {delete_status}
_Если включено, команды типа /mute, /ban, /kick будут автоматически удаляться после выполнения_
"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"🗑 Удалять команды: {delete_status}",
                    callback_data="toggle_delete_cmd"
                )
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_start")
            ]
        ]
        
        query.message.edit_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == "toggle_delete_cmd":
        if set_delete_mod_commands:
            current = get_delete_mod_commands(user.id) if get_delete_mod_commands else False
            set_delete_mod_commands(user.id, not current)
        
        # Обновляем меню
        delete_enabled = get_delete_mod_commands(user.id) if get_delete_mod_commands else False
        delete_status = "✅ Вкл" if delete_enabled else "❌ Выкл"
        
        text = f"""
⚙️ *Ваши настройки*

Здесь вы можете настроить поведение бота для себя.

🗑 *Удалять команды модерации:* {delete_status}
_Если включено, команды типа /mute, /ban, /kick будут автоматически удаляться после выполнения_
"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"🗑 Удалять команды: {delete_status}",
                    callback_data="toggle_delete_cmd"
                )
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_start")
            ]
        ]
        
        query.message.edit_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        query.answer("✅ Настройка изменена!")
        return
    
    query.answer()


def about_callback(update: Update, context: CallbackContext):
    """Обработчик кнопки 'О боте'"""
    query = update.callback_query
    
    if query.data == "about_":
        query.message.edit_text(
            text=f"""
*ℹ️ О боте {BOT_NAME}*

Я — мощный бот для управления группами Telegram.

*🔧 Возможности:*
• Модерация (бан, мут, кик)
• Приветствия и прощания
• Заметки и фильтры
• Правила группы
• Антифлуд и антиспам
• И многое другое!

*📚 Технологии:*
• Python {python_version()}
• python-telegram-bot {telever}

*👨‍💻 Разработка:*
Основан на [FallenRobot](https://github.com/AnonymousX1025/FallenRobot)
Переведён и обновлён для русскоязычных пользователей.
""",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="💬 Поддержка", url=f"https://t.me/{SUPPORT_CHAT}"
                        ),
                    ],
                    [
                        InlineKeyboardButton(text="◀️ Назад", callback_data="back_start"),
                    ],
                ]
            ),
        )
    
    elif query.data == "back_start":
        first_name = update.effective_user.first_name
        uptime = get_readable_time((time.time() - StartTime))
        query.message.edit_text(
            PM_START_TEXT.format(
                escape_markdown(first_name),
                BOT_NAME,
                uptime,
                python_version(),
                telever,
            ),
            reply_markup=InlineKeyboardMarkup(MAIN_BUTTONS),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    
    query.answer()


def get_help(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    chat = update.effective_chat
    args = context.args
    
    if chat.type != "private":
        update.effective_message.reply_text(
            "Напишите мне в личные сообщения для получения списка команд.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="📚 Помощь",
                            url=f"https://t.me/{BOT_USERNAME}?start=help",
                        )
                    ]
                ]
            ),
        )
    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    """Отправляет настройки чата или пользователя"""
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                f"*{mod.__mod_name__}*:\n{mod.__user_settings__(user_id)}"
                for mod in USER_SETTINGS.values()
            )
            dispatcher.bot.send_message(
                user_id,
                "Ваши настройки:\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            dispatcher.bot.send_message(
                user_id,
                "Похоже, нет доступных пользовательских настроек.",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(
                user_id,
                text=f"Какой модуль вы хотите проверить для настроек *{chat_name}*?",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            dispatcher.bot.send_message(
                user_id,
                "Похоже, нет доступных настроек чата.\n"
                "Отправьте это в группу, в которой вы админ!",
                parse_mode=ParseMode.MARKDOWN,
            )


def settings_button(update: Update, context: CallbackContext):
    """Обработчик кнопок настроек"""
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = f"*Настройки {chat.title}* для модуля *{CHAT_SETTINGS[module].__mod_name__}*:\n\n"
            text += CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="◀️ Назад",
                                callback_data=f"stngs_back({chat_id})",
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            query.message.reply_text(
                text="Выберите модуль:",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            query.message.reply_text(
                text="Выберите модуль:",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                text=f"Какой модуль вы хотите проверить для настроек *{chat.title}*?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        query.answer()
        bot.answer_callback_query(query.id)
        query.message.delete()
        
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise


def get_settings(update: Update, context: CallbackContext):
    """Обработчик команды /settings"""
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type != "private":
        if is_user_admin(chat, user.id):
            msg.reply_text(
                "Нажмите кнопку ниже, чтобы получить настройки.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="⚙️ Настройки",
                                url=f"https://t.me/{BOT_USERNAME}?start=stngs_{chat.id}",
                            )
                        ]
                    ]
                ),
            )
        else:
            msg.reply_text("Только админы могут просматривать настройки группы.")
    else:
        send_settings(chat.id, user.id, True)


def markdown_help_sender(update: Update):
    """Отправляет справку по Markdown"""
    update.effective_message.reply_text(
        """
*Справка по Markdown*

Telegram поддерживает следующее форматирование:

• `_курсив_` — _курсив_
• `*жирный*` — *жирный*
• `` `моноширинный` `` — `моноширинный`
• `[текст](URL)` — ссылка

*Специальные placeholder'ы:*
• `{first}` — имя пользователя
• `{last}` — фамилия пользователя
• `{fullname}` — полное имя
• `{username}` — @username
• `{mention}` — упоминание
• `{id}` — ID пользователя
• `{chatname}` — название чата
""",
        parse_mode=ParseMode.MARKDOWN,
    )


def migrate_chats(update: Update, context: CallbackContext):
    """Обрабатывает миграцию чатов"""
    msg = update.effective_message
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info(f"Миграция чата {old_chat} → {new_chat}")
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)


def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок"""
    LOGGER.error(f"Ошибка при обработке обновления: {context.error}")
    
    try:
        raise context.error
    except Unauthorized:
        LOGGER.warning("Unauthorized error")
    except BadRequest as e:
        LOGGER.warning(f"BadRequest: {e}")
    except TimedOut:
        LOGGER.warning("Timeout error")
    except NetworkError:
        LOGGER.warning("Network error")
    except ChatMigrated:
        LOGGER.warning("Chat migrated")
    except TelegramError as e:
        LOGGER.error(f"TelegramError: {e}")


# ═══════════════════════════════════════════════════════════════
#                      ЗАПУСК БОТА
# ═══════════════════════════════════════════════════════════════

def main():
    """Главная функция запуска бота"""
    
    # Отправляем сообщение о запуске в чат поддержки
    if SUPPORT_CHAT:
        try:
            dispatcher.bot.send_message(
                chat_id=f"@{SUPPORT_CHAT}",
                text=f"""
🤖 *{BOT_NAME} запущен!*

📊 *Информация:*
├ Python: `{python_version()}`
└ PTB: `{telever}`

✅ Бот готов к работе!
""",
                parse_mode=ParseMode.MARKDOWN,
            )
        except (Unauthorized, BadRequest) as e:
            LOGGER.warning(f"Не удалось отправить сообщение в чат поддержки: {e}")

    # Регистрация обработчиков
    start_handler = CommandHandler("start", start, run_async=True)
    help_handler = CommandHandler("help", get_help, run_async=True)
    settings_handler = CommandHandler("settings", get_settings, run_async=True)
    
    help_callback_handler = CallbackQueryHandler(
        help_button, pattern=r"help_.*", run_async=True
    )
    settings_callback_handler = CallbackQueryHandler(
        settings_button, pattern=r"stngs_", run_async=True
    )
    about_callback_handler = CallbackQueryHandler(
        about_callback, pattern=r"about_|back_start", run_async=True
    )
    user_settings_handler = CallbackQueryHandler(
        user_settings_callback, pattern=r"user_settings|toggle_delete_cmd", run_async=True
    )
    
    migrate_handler = MessageHandler(
        Filters.status_update.migrate, migrate_chats, run_async=True
    )

    # Добавление обработчиков
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(about_callback_handler)
    dispatcher.add_handler(user_settings_handler)
    dispatcher.add_handler(migrate_handler)
    
    # Обработчик ошибок
    dispatcher.add_error_handler(error_handler)

    LOGGER.info("Запуск polling...")
    updater.start_polling(timeout=15, read_latency=4, drop_pending_updates=True)

    LOGGER.info(f"{BOT_NAME} успешно запущен!")
    
    updater.idle()


if __name__ == "__main__":
    LOGGER.info(f"Загружены модули: {ALL_MODULES}")
    main()
