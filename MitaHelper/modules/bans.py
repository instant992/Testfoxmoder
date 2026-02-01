# -*- coding: utf-8 -*-
"""
Модуль банов - бан, кик, мут пользователей
"""

import html
from datetime import datetime, timedelta

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Filters
from telegram.utils.helpers import mention_html

from MitaHelper import LOGGER, OWNER_ID, SUDO_USERS, dispatcher
from MitaHelper.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    is_user_ban_protected,
    user_admin,
)
from MitaHelper.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
    extract_user_for_moderation,
    extract_user_and_text_for_moderation,
)

# Импорт логов
try:
    from MitaHelper.modules.logs import log_ban, log_unban, log_kick, log_mute, log_unmute
except ImportError:
    log_ban = None
    log_unban = None
    log_kick = None
    log_mute = None
    log_unmute = None

# Импорт настроек удаления команд
try:
    from MitaHelper.modules.database import get_delete_mod_commands
except ImportError:
    get_delete_mod_commands = None


# Время автоудаления сообщений о наказании (в секундах)
PUNISHMENT_MSG_DELETE_TIME = 120  # 2 минуты


def try_delete_command(msg, user_id):
    """Пытается удалить команду модерации если включено"""
    if get_delete_mod_commands and get_delete_mod_commands(user_id):
        try:
            msg.delete()
        except:
            pass


def delete_punishment_message(context: CallbackContext):
    """Удаляет сообщение о наказании по таймеру"""
    job = context.job
    try:
        context.bot.delete_message(
            chat_id=job.context["chat_id"],
            message_id=job.context["message_id"]
        )
    except:
        pass


def get_undo_keyboard(action: str, user_id: int, chat_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой отмены наказания"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "↩️ Снять наказание",
            callback_data=f"undo_{action}_{user_id}_{chat_id}"
        )]
    ])


def schedule_message_deletion(context: CallbackContext, chat_id: int, message_id: int):
    """Планирует удаление сообщения через заданное время"""
    context.job_queue.run_once(
        delete_punishment_message,
        PUNISHMENT_MSG_DELETE_TIME,
        context={"chat_id": chat_id, "message_id": message_id},
        name=f"delete_punishment_{chat_id}_{message_id}"
    )


def parse_time(time_val: str) -> timedelta:
    """Парсит строку времени в timedelta"""
    if not time_val:
        return None
    
    time_val = time_val.lower()
    
    if time_val.endswith(("s", "с", "сек")):
        return timedelta(seconds=int(time_val[:-1].strip()))
    elif time_val.endswith(("m", "м", "мин")):
        return timedelta(minutes=int(time_val[:-1].strip()))
    elif time_val.endswith(("h", "ч", "час")):
        return timedelta(hours=int(time_val[:-1].strip()))
    elif time_val.endswith(("d", "д", "дн", "день", "дней")):
        for suffix in ("дней", "день", "дн", "д", "d"):
            if time_val.endswith(suffix):
                return timedelta(days=int(time_val[:-len(suffix)].strip()))
    
    return None


@bot_admin
@can_restrict
@user_admin
def ban(update: Update, context: CallbackContext):
    """Банит пользователя в чате"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    user_id, reason = extract_user_and_text_for_moderation(msg, args, context.bot, chat.id)
    
    if not user_id:
        msg.reply_text(
            "❌ Укажите пользователя (ID, @username или ответьте на сообщение)."
        )
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return

    if user_id == context.bot.id:
        msg.reply_text("❌ Я не буду банить себя!")
        return

    if is_user_ban_protected(chat, user_id, member):
        msg.reply_text("❌ Этого пользователя нельзя забанить!")
        return

    if is_user_admin(chat, user_id):
        msg.reply_text("❌ Нельзя забанить администратора!")
        return

    try:
        context.bot.ban_chat_member(chat.id, user_id)
        
        # Логируем бан
        if log_ban:
            log_ban(context.bot, chat, user, member.user, reason)
        
        text = f"🚫 <b>Пользователь забанен!</b>\n\n"
        text += f"👤 Пользователь: {mention_html(member.user.id, member.user.first_name)}\n"
        text += f"👮 Администратор: {mention_html(user.id, user.first_name)}"
        
        if reason:
            text += f"\n📝 Причина: {html.escape(reason)}"
        
        keyboard = get_undo_keyboard("ban", user_id, chat.id)
        sent_msg = msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
        # Планируем удаление сообщения
        schedule_message_deletion(context, chat.id, sent_msg.message_id)
        
        # Удаляем команду ПОСЛЕ ответа
        try_delete_command(msg, user.id)
        
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_restrict
@user_admin
def tempban(update: Update, context: CallbackContext):
    """Временно банит пользователя"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    user_id, text = extract_user_and_text_for_moderation(msg, args, context.bot, chat.id)
    
    if not user_id:
        msg.reply_text("❌ Укажите пользователя.")
        return

    # Парсим время и причину
    parts = text.split(None, 1) if text else []
    time_val = parts[0] if parts else None
    reason = parts[1] if len(parts) > 1 else None

    if not time_val:
        msg.reply_text("❌ Укажите время бана (например: 1h, 1д, 30m).")
        return

    ban_time = parse_time(time_val)
    if not ban_time:
        msg.reply_text("❌ Неверный формат времени. Используйте: 30m, 1h, 1d")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return

    if is_user_ban_protected(chat, user_id, member):
        msg.reply_text("❌ Этого пользователя нельзя забанить!")
        return

    until_date = datetime.utcnow() + ban_time

    try:
        context.bot.ban_chat_member(chat.id, user_id, until_date=until_date)
        
        text = f"⏰ <b>Временный бан!</b>\n\n"
        text += f"👤 Пользователь: {mention_html(member.user.id, member.user.first_name)}\n"
        text += f"👮 Администратор: {mention_html(user.id, user.first_name)}\n"
        text += f"⏱ Срок: {time_val}"
        
        if reason:
            text += f"\n📝 Причина: {html.escape(reason)}"
        
        keyboard = get_undo_keyboard("ban", user_id, chat.id)
        sent_msg = msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
        # Планируем удаление сообщения
        schedule_message_deletion(context, chat.id, sent_msg.message_id)
        
        # Удаляем команду ПОСЛЕ ответа
        try_delete_command(msg, user.id)
        
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_restrict
@user_admin
def unban(update: Update, context: CallbackContext):
    """Разбанивает пользователя"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    user_id = extract_user_for_moderation(msg, args, context.bot, chat.id)
    
    if not user_id:
        msg.reply_text(
            "❌ Пользователь не найден.\n\n"
            "*Использование:*\n"
            "• Ответьте на сообщение пользователя\n"
            "• `/unban 123456789` (по ID)\n"
            "• `/unban @username` (если писал в чате)",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        context.bot.unban_chat_member(chat.id, user_id)
        
        # Логируем разбан
        if log_unban:
            try:
                target = context.bot.get_chat(user_id)
                log_unban(context.bot, chat, user, target)
            except:
                pass
        
        msg.reply_text(f"✅ Пользователь разбанен!")
        
        # Удаляем команду ПОСЛЕ ответа
        try_delete_command(msg, user.id)
        
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_restrict
@user_admin
def kick(update: Update, context: CallbackContext):
    """Кикает пользователя из чата"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    user_id, reason = extract_user_and_text_for_moderation(msg, args, context.bot, chat.id)
    
    if not user_id:
        msg.reply_text("❌ Укажите пользователя.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return

    if user_id == context.bot.id:
        msg.reply_text("❌ Я не буду кикать себя!")
        return

    if is_user_ban_protected(chat, user_id, member):
        msg.reply_text("❌ Этого пользователя нельзя кикнуть!")
        return

    try:
        context.bot.ban_chat_member(chat.id, user_id)
        context.bot.unban_chat_member(chat.id, user_id)
        
        # Логируем кик
        if log_kick:
            log_kick(context.bot, chat, user, member.user, reason)
        
        text = f"👢 <b>Пользователь кикнут!</b>\n\n"
        text += f"👤 Пользователь: {mention_html(member.user.id, member.user.first_name)}\n"
        text += f"👮 Администратор: {mention_html(user.id, user.first_name)}"
        
        if reason:
            text += f"\n📝 Причина: {html.escape(reason)}"
        
        # Для кика нет кнопки отмены (пользователь уже может вернуться)
        sent_msg = msg.reply_text(text, parse_mode=ParseMode.HTML)
        
        # Планируем удаление сообщения
        schedule_message_deletion(context, chat.id, sent_msg.message_id)
        
        # Удаляем команду ПОСЛЕ ответа
        try_delete_command(msg, user.id)
        
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_restrict
@user_admin
def mute(update: Update, context: CallbackContext):
    """Мутит пользователя (запрет на отправку сообщений)"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    user_id, text = extract_user_and_text_for_moderation(msg, args, context.bot, chat.id)
    
    if not user_id:
        msg.reply_text(
            "❌ Укажите пользователя.\n\n"
            "*Использование:*\n"
            "• `/mute @username` — мут навсегда\n"
            "• `/mute @username 1h` — мут на 1 час\n"
            "• `/mute @username 30m спам` — мут на 30 минут с причиной\n"
            "• `/mute 123456789 1d` — мут по ID на 1 день",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return

    if user_id == context.bot.id:
        msg.reply_text("❌ Я не буду мутить себя!")
        return

    if is_user_admin(chat, user_id):
        msg.reply_text("❌ Нельзя замутить администратора!")
        return

    # Парсим время и причину
    time_val = None
    reason = None
    until_date = None
    time_display = "навсегда"
    
    if text:
        parts = text.split(None, 1)
        # Пробуем распарсить первую часть как время
        possible_time = parse_time(parts[0]) if parts else None
        
        if possible_time:
            time_val = parts[0]
            until_date = datetime.utcnow() + possible_time
            time_display = time_val
            reason = parts[1] if len(parts) > 1 else None
        else:
            # Первая часть - не время, значит всё это причина
            reason = text

    try:
        context.bot.restrict_chat_member(
            chat.id,
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
        
        # Логируем мут
        if log_mute:
            log_mute(context.bot, chat, user, member.user, time_display, reason)
        
        if until_date:
            text = f"⏰ <b>Временный мут!</b>\n\n"
        else:
            text = f"🔇 <b>Пользователь замучен!</b>\n\n"
        
        text += f"👤 Пользователь: {mention_html(member.user.id, member.user.first_name)}\n"
        text += f"👮 Администратор: {mention_html(user.id, user.first_name)}\n"
        text += f"⏱ Срок: {time_display}"
        
        if reason:
            text += f"\n📝 Причина: {html.escape(reason)}"
        
        keyboard = get_undo_keyboard("mute", user_id, chat.id)
        sent_msg = msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
        # Планируем удаление сообщения
        schedule_message_deletion(context, chat.id, sent_msg.message_id)
        
        # Удаляем команду ПОСЛЕ ответа
        try_delete_command(msg, user.id)
        
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_restrict
@user_admin
def tempmute(update: Update, context: CallbackContext):
    """Временно мутит пользователя"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    user_id, text = extract_user_and_text_for_moderation(msg, args, context.bot, chat.id)
    
    if not user_id:
        msg.reply_text("❌ Укажите пользователя.")
        return

    # Парсим время и причину
    parts = text.split(None, 1) if text else []
    time_val = parts[0] if parts else None
    reason = parts[1] if len(parts) > 1 else None

    if not time_val:
        msg.reply_text("❌ Укажите время мута (например: 1h, 1д, 30m).")
        return

    mute_time = parse_time(time_val)
    if not mute_time:
        msg.reply_text("❌ Неверный формат времени. Используйте: 30m, 1h, 1d")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return

    if is_user_admin(chat, user_id):
        msg.reply_text("❌ Нельзя замутить администратора!")
        return

    until_date = datetime.utcnow() + mute_time

    try:
        context.bot.restrict_chat_member(
            chat.id,
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
        
        text = f"⏰ <b>Временный мут!</b>\n\n"
        text += f"👤 Пользователь: {mention_html(member.user.id, member.user.first_name)}\n"
        text += f"👮 Администратор: {mention_html(user.id, user.first_name)}\n"
        text += f"⏱ Срок: {time_val}"
        
        if reason:
            text += f"\n📝 Причина: {html.escape(reason)}"
        
        keyboard = get_undo_keyboard("mute", user_id, chat.id)
        sent_msg = msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
        # Планируем удаление сообщения
        schedule_message_deletion(context, chat.id, sent_msg.message_id)
        
        # Удаляем команду ПОСЛЕ ответа
        try_delete_command(msg, user.id)
        
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_restrict
@user_admin
def unmute(update: Update, context: CallbackContext):
    """Снимает мут с пользователя"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args

    user_id = extract_user_for_moderation(msg, args, context.bot, chat.id)
    
    if not user_id:
        msg.reply_text(
            "❌ Пользователь не найден.\n\n"
            "*Использование:*\n"
            "• Ответьте на сообщение пользователя\n"
            "• `/unmute 123456789` (по ID)\n"
            "• `/unmute @username` (если писал в чате)",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        context.bot.restrict_chat_member(
            chat.id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
            ),
        )
        
        # Логируем размут
        if log_unmute:
            try:
                target = context.bot.get_chat(user_id)
                log_unmute(context.bot, chat, update.effective_user, target)
            except:
                pass
        
        msg.reply_text("✅ Мут снят!")
        
        # Удаляем команду ПОСЛЕ ответа
        try_delete_command(msg, update.effective_user.id)
        
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


# ═══════════════════════════════════════════════════════════════
#                      ОБРАБОТЧИК КНОПКИ ОТМЕНЫ
# ═══════════════════════════════════════════════════════════════

def undo_punishment_callback(update: Update, context: CallbackContext):
    """Обработчик кнопки снятия наказания"""
    query = update.callback_query
    user = update.effective_user
    
    # Парсим данные: undo_action_userid_chatid
    try:
        parts = query.data.split("_")
        action = parts[1]  # ban или mute
        target_user_id = int(parts[2])
        chat_id = int(parts[3])
    except (IndexError, ValueError):
        query.answer("❌ Ошибка данных", show_alert=True)
        return
    
    # Проверяем, что пользователь - админ в этом чате
    try:
        chat = context.bot.get_chat(chat_id)
        if not is_user_admin(chat, user.id):
            query.answer("❌ Только администраторы могут снимать наказания!", show_alert=True)
            return
    except BadRequest:
        query.answer("❌ Чат не найден", show_alert=True)
        return
    
    try:
        if action == "ban":
            # Разбаниваем
            context.bot.unban_chat_member(chat_id, target_user_id)
            
            # Логируем
            if log_unban:
                try:
                    target = context.bot.get_chat(target_user_id)
                    log_unban(context.bot, chat, user, target)
                except:
                    pass
            
            query.answer("✅ Пользователь разбанен!")
            
            # Обновляем сообщение
            try:
                target_info = context.bot.get_chat(target_user_id)
                target_name = target_info.first_name
            except:
                target_name = str(target_user_id)
            
            query.message.edit_text(
                f"✅ <b>Наказание снято</b>\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"👮 Снял: {mention_html(user.id, user.first_name)}",
                parse_mode=ParseMode.HTML
            )
            
        elif action == "mute":
            # Снимаем мут
            context.bot.restrict_chat_member(
                chat_id,
                target_user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_change_info=False,
                    can_invite_users=True,
                    can_pin_messages=False,
                ),
            )
            
            # Логируем
            if log_unmute:
                try:
                    target = context.bot.get_chat(target_user_id)
                    log_unmute(context.bot, chat, user, target)
                except:
                    pass
            
            query.answer("✅ Мут снят!")
            
            # Обновляем сообщение
            try:
                target_info = context.bot.get_chat(target_user_id)
                target_name = target_info.first_name
            except:
                target_name = str(target_user_id)
            
            query.message.edit_text(
                f"✅ <b>Мут снят</b>\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"👮 Снял: {mention_html(user.id, user.first_name)}",
                parse_mode=ParseMode.HTML
            )
            
    except BadRequest as e:
        query.answer(f"❌ Ошибка: {e.message}", show_alert=True)


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

BAN_HANDLER = CommandHandler("ban", ban, run_async=True)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], tempban, run_async=True)
UNBAN_HANDLER = CommandHandler("unban", unban, run_async=True)
KICK_HANDLER = CommandHandler("kick", kick, run_async=True)
MUTE_HANDLER = CommandHandler("mute", mute, run_async=True)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], tempmute, run_async=True)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, run_async=True)
UNDO_HANDLER = CallbackQueryHandler(undo_punishment_callback, pattern=r"^undo_", run_async=True)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(UNDO_HANDLER)


__mod_name__ = "🔨 Баны"

__help__ = """
*Команды модерации:*

🚫 *Баны:*
• /ban `<@username или ID>` `[причина]` — забанить навсегда
• /tban `<@username или ID>` `<время>` `[причина]` — временный бан
• /unban `<@username или ID>` — разбанить
• /kick `<@username или ID>` `[причина]` — кикнуть

🔇 *Мут:*
• /mute `<@username или ID>` `[время]` `[причина]` — замутить
• /unmute `<@username или ID>` — снять мут

⏱ *Форматы времени:*
• `30s` или `30с` — 30 секунд
• `30m` или `30м` — 30 минут
• `1h` или `1ч` — 1 час
• `1d` или `1д` — 1 день

📝 *Примеры:*
• `/ban @username спам` — бан навсегда
• `/ban 123456789 реклама` — бан по ID
• `/tban @username 1h флуд` — бан на 1 час
• `/mute @username` — мут навсегда
• `/mute @username 30m` — мут на 30 минут
• `/mute 123456789 1h спам` — мут по ID на 1 час с причиной
• `/unmute @username` — снять мут
• `/unban 123456789` — разбан по ID
"""
