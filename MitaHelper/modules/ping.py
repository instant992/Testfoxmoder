# -*- coding: utf-8 -*-
"""
Модуль ping - проверка работоспособности бота
"""

import time
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, CommandHandler

from MitaHelper import StartTime, dispatcher


def get_readable_time(seconds: int) -> str:
    """Преобразует секунды в читаемый формат"""
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


def ping(update: Update, context: CallbackContext):
    """Проверяет скорость ответа бота"""
    msg = update.effective_message
    
    start_time = time.time()
    message = msg.reply_text("🏓 Пингую...")
    end_time = time.time()
    
    ping_time = round((end_time - start_time) * 1000, 2)
    uptime = get_readable_time((time.time() - StartTime))
    
    message.edit_text(
        f"🏓 *Понг!*\n\n"
        f"⚡ *Скорость:* `{ping_time} мс`\n"
        f"⏱ *Аптайм:* `{uptime}`",
        parse_mode=ParseMode.MARKDOWN,
    )


def alive(update: Update, context: CallbackContext):
    """Проверяет, работает ли бот"""
    msg = update.effective_message
    uptime = get_readable_time((time.time() - StartTime))
    
    msg.reply_text(
        f"✅ *Бот работает!*\n\n"
        f"⏱ *Время работы:* `{uptime}`",
        parse_mode=ParseMode.MARKDOWN,
    )


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

PING_HANDLER = CommandHandler("ping", ping, run_async=True)
ALIVE_HANDLER = CommandHandler("alive", alive, run_async=True)

dispatcher.add_handler(PING_HANDLER)
dispatcher.add_handler(ALIVE_HANDLER)


__mod_name__ = "🏓 Пинг"

__help__ = """
*Проверка работоспособности:*

🏓 *Команды:*
• /ping или /пинг — проверить скорость ответа
• /alive или /жив — проверить, работает ли бот

📊 *Показывает:*
• Скорость ответа в миллисекундах
• Время работы бота
"""
