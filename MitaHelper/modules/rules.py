# -*- coding: utf-8 -*-
"""
Модуль правил чата
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler

from MitaHelper import dispatcher, LOGGER
from MitaHelper.modules.helper_funcs.chat_status import user_admin


# Хранилище правил
rules_storage = {}

# Загрузка из БД
try:
    from MitaHelper.modules.database import load_rules_settings, save_rules_settings
    _loaded = load_rules_settings()
    if _loaded:
        rules_storage = _loaded
        LOGGER.info(f"Загружены правила для {len(rules_storage)} чатов")
except Exception as e:
    LOGGER.warning(f"Не удалось загрузить правила: {e}")
    save_rules_settings = None


def _save_rules_to_db():
    """Сохраняет правила в БД"""
    if save_rules_settings:
        save_rules_settings(rules_storage)


def get_rules(chat_id):
    """Получает правила чата"""
    return rules_storage.get(chat_id, None)


def set_rules(chat_id, rules_text):
    """Устанавливает правила чата"""
    rules_storage[chat_id] = rules_text
    _save_rules_to_db()


def clear_rules(chat_id):
    """Удаляет правила чата"""
    if chat_id in rules_storage:
        del rules_storage[chat_id]
        _save_rules_to_db()


def rules(update: Update, context: CallbackContext):
    """Показывает правила чата"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        # Проверяем, есть ли аргумент с ID чата
        args = context.args
        if args and args[0].lstrip("-").isdigit():
            chat_id = int(args[0])
            try:
                chat_info = context.bot.get_chat(chat_id)
                rules_text = get_rules(chat_id)
                if rules_text:
                    msg.reply_text(
                        f"📜 *Правила чата* `{chat_info.title}`:\n\n{rules_text}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    msg.reply_text("❌ В этом чате не установлены правила.")
            except BadRequest:
                msg.reply_text("❌ Чат не найден.")
        else:
            msg.reply_text("❌ Используйте эту команду в группе.")
        return
    
    rules_text = get_rules(chat.id)
    
    if rules_text:
        msg.reply_text(
            f"📜 *Правила чата* `{chat.title}`:\n\n{rules_text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Закрыть", callback_data="close_menu")]
            ]),
        )
    else:
        msg.reply_text(
            "📜 В этом чате не установлены правила.\n"
            "Администраторы могут установить их командой /setrules"
        )


@user_admin
def setrules(update: Update, context: CallbackContext):
    """Устанавливает правила чата"""
    chat = update.effective_chat
    msg = update.effective_message
    
    # Получаем текст правил
    if msg.reply_to_message:
        rules_text = msg.reply_to_message.text or msg.reply_to_message.caption
    else:
        text = msg.text.split(None, 1)
        rules_text = text[1] if len(text) > 1 else None
    
    if not rules_text:
        msg.reply_text(
            "❌ Укажите правила чата.\n\n"
            "*Использование:*\n"
            "• `/setrules <текст правил>`\n"
            "• Ответьте на сообщение: `/setrules`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    set_rules(chat.id, rules_text)
    msg.reply_text("✅ Правила чата установлены!")


@user_admin
def clearrules(update: Update, context: CallbackContext):
    """Удаляет правила чата"""
    chat = update.effective_chat
    msg = update.effective_message
    
    clear_rules(chat.id)
    msg.reply_text("✅ Правила чата удалены!")


def rules_button(update: Update, context: CallbackContext):
    """Отправляет правила в личные сообщения"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    
    rules_text = get_rules(chat.id)
    
    if not rules_text:
        msg.reply_text("📜 В этом чате не установлены правила.")
        return
    
    msg.reply_text(
        "Нажмите кнопку ниже, чтобы прочитать правила.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📜 Правила",
                    url=f"https://t.me/{context.bot.username}?start=rules_{chat.id}",
                )
            ]
        ]),
    )


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

RULES_HANDLER = CommandHandler("rules", rules, run_async=True)
SETRULES_HANDLER = CommandHandler("setrules", setrules, run_async=True)
CLEARRULES_HANDLER = CommandHandler("clearrules", clearrules, run_async=True)

dispatcher.add_handler(RULES_HANDLER)
dispatcher.add_handler(SETRULES_HANDLER)
dispatcher.add_handler(CLEARRULES_HANDLER)


__mod_name__ = "📜 Правила"

__help__ = """
*Правила чата:*

📜 *Команды:*
• /rules или /правила — показать правила
• /setrules `<текст>` — установить правила (админ)
• /clearrules — удалить правила (админ)

📝 *Форматирование:*
Правила поддерживают Markdown:
• `*жирный*`
• `_курсив_`
• `` `код` ``
• `[ссылка](URL)`

*Пример:*
```
/setrules
📜 *Правила чата*

1. Уважайте друг друга
2. Без спама и рекламы
3. Пишите по-русски
```
"""
