# -*- coding: utf-8 -*-
"""
Модуль администрирования - управление чатом
"""

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler
from telegram.utils.helpers import mention_html

from MitaHelper import SUDO_USERS, dispatcher
from MitaHelper.modules.helper_funcs.chat_status import (
    bot_admin,
    can_pin,
    can_promote,
    connection_status,
    user_admin,
)
from MitaHelper.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
)


@bot_admin
@user_admin
def set_sticker(update: Update, context: CallbackContext):
    """Устанавливает стикерпак для группы"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if msg.reply_to_message:
        if msg.reply_to_message.sticker:
            stkr = msg.reply_to_message.sticker.set_name
            try:
                context.bot.set_chat_sticker_set(chat.id, stkr)
                msg.reply_text(
                    f"✅ Стикерпак чата успешно установлен на *{stkr}*!",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except BadRequest as e:
                if "Participants_too_few" in str(e):
                    msg.reply_text(
                        "❌ В группе слишком мало участников для установки стикерпака."
                    )
                else:
                    msg.reply_text(f"❌ Ошибка: {e.message}")
        else:
            msg.reply_text("❌ Ответьте на стикер, чтобы установить его пак.")
    else:
        msg.reply_text("❌ Ответьте на стикер, чтобы установить его пак.")


@bot_admin
@user_admin
def setchatpic(update: Update, context: CallbackContext):
    """Устанавливает фото чата"""
    chat = update.effective_chat
    msg = update.effective_message

    if msg.reply_to_message:
        if msg.reply_to_message.photo:
            pic_id = msg.reply_to_message.photo[-1].file_id
            file = context.bot.get_file(pic_id)
            file.download("chat_photo.jpg")
            with open("chat_photo.jpg", "rb") as f:
                context.bot.set_chat_photo(chat_id=chat.id, photo=f)
            msg.reply_text("✅ Фото чата успешно обновлено!")
        else:
            msg.reply_text("❌ Ответьте на фото, чтобы установить его.")
    else:
        msg.reply_text("❌ Ответьте на фото, чтобы установить его.")


@bot_admin
@user_admin
def rmchatpic(update: Update, context: CallbackContext):
    """Удаляет фото чата"""
    chat = update.effective_chat
    msg = update.effective_message
    
    try:
        context.bot.delete_chat_photo(chat.id)
        msg.reply_text("✅ Фото чата удалено!")
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@user_admin
def setchat_title(update: Update, context: CallbackContext):
    """Устанавливает название чата"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if args:
        title = " ".join(args)
        try:
            context.bot.set_chat_title(chat.id, title)
            msg.reply_text(
                f"✅ Название чата изменено на *{html.escape(title)}*!",
                parse_mode=ParseMode.HTML,
            )
        except BadRequest as e:
            msg.reply_text(f"❌ Ошибка: {e.message}")
    else:
        msg.reply_text("❌ Укажите новое название чата.")


@bot_admin
@user_admin
def setdesc(update: Update, context: CallbackContext):
    """Устанавливает описание чата"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    if args:
        desc = " ".join(args)
        if len(desc) > 255:
            msg.reply_text("❌ Описание должно быть не длиннее 255 символов.")
            return
        try:
            context.bot.set_chat_description(chat.id, desc)
            msg.reply_text("✅ Описание чата успешно обновлено!")
        except BadRequest as e:
            msg.reply_text(f"❌ Ошибка: {e.message}")
    else:
        msg.reply_text("❌ Укажите новое описание чата.")


@bot_admin
@can_promote
@user_admin
def promote(update: Update, context: CallbackContext):
    """Повышает пользователя до администратора"""
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    user_id = extract_user(msg, args)
    
    if not user_id:
        msg.reply_text(
            "❌ Укажите пользователя (ID, @username или ответьте на сообщение)."
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return

    if user_member.status in ("administrator", "creator"):
        msg.reply_text("❌ Этот пользователь уже администратор!")
        return

    if user_id == context.bot.id:
        msg.reply_text("❌ Я не могу повысить себя!")
        return

    try:
        context.bot.promote_chat_member(
            chat.id,
            user_id,
            can_change_info=True,
            can_post_messages=True,
            can_edit_messages=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_manage_chat=True,
            can_manage_video_chats=True,
        )
        msg.reply_text(
            f"✅ {mention_html(user_member.user.id, user_member.user.first_name)} "
            "повышен до администратора!",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        if "User_not_mutual_contact" in str(e):
            msg.reply_text("❌ Я не могу повысить пользователя, который не в чате.")
        else:
            msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_promote
@user_admin
def demote(update: Update, context: CallbackContext):
    """Понижает администратора"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args

    user_id = extract_user(msg, args)
    
    if not user_id:
        msg.reply_text(
            "❌ Укажите пользователя (ID, @username или ответьте на сообщение)."
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except BadRequest:
        msg.reply_text("❌ Пользователь не найден.")
        return

    if user_member.status == "creator":
        msg.reply_text("❌ Нельзя понизить создателя чата!")
        return

    if user_member.status != "administrator":
        msg.reply_text("❌ Этот пользователь не администратор!")
        return

    if user_id == context.bot.id:
        msg.reply_text("❌ Я не могу понизить себя!")
        return

    try:
        context.bot.promote_chat_member(
            chat.id,
            user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
        )
        msg.reply_text(
            f"✅ {mention_html(user_member.user.id, user_member.user.first_name)} "
            "понижен!",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@user_admin
def set_title(update: Update, context: CallbackContext):
    """Устанавливает титул администратора"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args

    user_id, title = extract_user_and_text(msg, args)
    
    if not user_id:
        msg.reply_text("❌ Укажите пользователя.")
        return

    if not title:
        msg.reply_text("❌ Укажите титул.")
        return

    if len(title) > 16:
        msg.reply_text("❌ Титул должен быть не длиннее 16 символов.")
        return

    try:
        context.bot.set_chat_administrator_custom_title(chat.id, user_id, title)
        msg.reply_text(
            f"✅ Титул администратора изменён на *{html.escape(title)}*!",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        if "not an administrator" in str(e).lower():
            msg.reply_text("❌ Пользователь не администратор.")
        else:
            msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_pin
@user_admin
def pin(update: Update, context: CallbackContext):
    """Закрепляет сообщение"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args

    if not msg.reply_to_message:
        msg.reply_text("❌ Ответьте на сообщение, чтобы закрепить его.")
        return

    disable_notification = "silent" in args or "тихо" in args

    try:
        context.bot.pin_chat_message(
            chat.id,
            msg.reply_to_message.message_id,
            disable_notification=disable_notification,
        )
        msg.reply_text("✅ Сообщение закреплено!")
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_pin
@user_admin
def unpin(update: Update, context: CallbackContext):
    """Открепляет сообщение"""
    chat = update.effective_chat
    msg = update.effective_message

    try:
        context.bot.unpin_chat_message(chat.id)
        msg.reply_text("✅ Сообщение откреплено!")
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@can_pin
@user_admin
def unpinall(update: Update, context: CallbackContext):
    """Открепляет все сообщения"""
    chat = update.effective_chat
    msg = update.effective_message

    try:
        context.bot.unpin_all_chat_messages(chat.id)
        msg.reply_text("✅ Все сообщения откреплены!")
    except BadRequest as e:
        msg.reply_text(f"❌ Ошибка: {e.message}")


@bot_admin
@user_admin
def invite(update: Update, context: CallbackContext):
    """Получает ссылку-приглашение"""
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == "private":
        msg.reply_text("❌ Эта команда работает только в группах.")
        return

    if chat.username:
        msg.reply_text(f"🔗 Ссылка на чат: https://t.me/{chat.username}")
    else:
        try:
            link = context.bot.export_chat_invite_link(chat.id)
            msg.reply_text(f"🔗 Ссылка-приглашение:\n{link}")
        except BadRequest as e:
            msg.reply_text(f"❌ Ошибка: {e.message}")


def adminlist(update: Update, context: CallbackContext):
    """Показывает список администраторов"""
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == "private":
        msg.reply_text("❌ Эта команда работает только в группах.")
        return

    try:
        administrators = chat.get_administrators()
    except BadRequest:
        msg.reply_text("❌ Не удалось получить список администраторов.")
        return

    text = f"👥 *Администраторы чата* `{chat.title}`:\n\n"
    
    # Сначала создатели
    for admin in administrators:
        if admin.status == "creator":
            text += f"👑 {mention_html(admin.user.id, admin.user.first_name)}\n"

    # Затем обычные админы
    for admin in administrators:
        if admin.status == "administrator":
            text += f"⭐ {mention_html(admin.user.id, admin.user.first_name)}"
            if admin.custom_title:
                text += f" | `{admin.custom_title}`"
            text += "\n"

    msg.reply_text(text, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

SET_STICKER_HANDLER = CommandHandler("setsticker", set_sticker, run_async=True)
SET_PIC_HANDLER = CommandHandler("setgpic", setchatpic, run_async=True)
RM_PIC_HANDLER = CommandHandler("delgpic", rmchatpic, run_async=True)
SET_TITLE_HANDLER = CommandHandler("setgtitle", setchat_title, run_async=True)
SET_DESC_HANDLER = CommandHandler("setdesc", setdesc, run_async=True)
PROMOTE_HANDLER = CommandHandler("promote", promote, run_async=True)
DEMOTE_HANDLER = CommandHandler("demote", demote, run_async=True)
ADMIN_TITLE_HANDLER = CommandHandler("settitle", set_title, run_async=True)
PIN_HANDLER = CommandHandler("pin", pin, run_async=True)
UNPIN_HANDLER = CommandHandler("unpin", unpin, run_async=True)
UNPINALL_HANDLER = CommandHandler("unpinall", unpinall, run_async=True)
INVITE_HANDLER = CommandHandler("invite", invite, run_async=True)
ADMINLIST_HANDLER = CommandHandler("adminlist", adminlist, run_async=True)

dispatcher.add_handler(SET_STICKER_HANDLER)
dispatcher.add_handler(SET_PIC_HANDLER)
dispatcher.add_handler(RM_PIC_HANDLER)
dispatcher.add_handler(SET_TITLE_HANDLER)
dispatcher.add_handler(SET_DESC_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(ADMIN_TITLE_HANDLER)
dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(UNPINALL_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)


__mod_name__ = "👑 Админ"

__help__ = """
*Команды администрирования:*

📌 *Управление администраторами:*
• /promote или /повысить `<пользователь>` — повысить до админа
• /demote или /понизить `<пользователь>` — понизить админа
• /settitle `<пользователь>` `<титул>` — установить титул админа
• /adminlist или /админы — список администраторов

📌 *Управление сообщениями:*
• /pin или /закрепить — закрепить сообщение (ответом)
• /unpin или /открепить — открепить сообщение
• /unpinall — открепить все сообщения

📌 *Настройки чата:*
• /setgtitle `<название>` — изменить название чата
• /setdesc `<описание>` — изменить описание чата
• /setgpic — установить фото чата (ответом на фото)
• /delgpic — удалить фото чата
• /setsticker — установить стикерпак чата

📌 *Прочее:*
• /invite или /ссылка — получить ссылку-приглашение
"""
