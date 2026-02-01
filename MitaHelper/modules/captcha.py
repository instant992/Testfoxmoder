# -*- coding: utf-8 -*-
"""
Модуль капчи - проверка новых участников
"""

import random
import time
from datetime import datetime, timedelta
from threading import RLock

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
    JobQueue,
)

from MitaHelper import dispatcher, LOGGER
from MitaHelper.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    user_admin,
)
from MitaHelper.modules.helper_funcs.topics import get_thread_id

# Импорт логов
try:
    from MitaHelper.modules.logs import log_captcha_pass, log_captcha_fail, log_join
except ImportError:
    log_captcha_pass = None
    log_captcha_fail = None
    log_join = None


# Блокировка для потокобезопасности
CAPTCHA_LOCK = RLock()

# Хранилища
captcha_settings = {}  # {chat_id: {"enabled": bool, "timeout": int, "mode": str, "kick_on_fail": bool}}
pending_captcha = {}   # {(chat_id, user_id): {"answer": ..., "message_id": ..., "time": ...}}

# Загрузка настроек из БД
try:
    from MitaHelper.modules.database import load_captcha_settings, save_captcha_settings_db
    _loaded = load_captcha_settings()
    if _loaded:
        captcha_settings = _loaded
        LOGGER.info(f"Загружены настройки капчи для {len(captcha_settings)} чатов")
except Exception as e:
    LOGGER.warning(f"Не удалось загрузить настройки капчи: {e}")
    save_captcha_settings_db = None


def _save_captcha_to_db():
    """Сохраняет настройки капчи в БД"""
    if save_captcha_settings_db:
        save_captcha_settings_db(captcha_settings)


# Режимы капчи
CAPTCHA_MODES = {
    "button": "Кнопка",
    "math": "Математика",
    "text": "Текст",
    "emoji": "Эмодзи",
}

# Эмодзи-капча - наборы картинок и вариантов
EMOJI_CAPTCHA_DATA = {
    "animals": {
        "question": "Какое это животное?",
        "items": [
            {"emoji": "🐶", "answer": "Собака", "wrong": ["Кошка", "Лиса", "Волк"]},
            {"emoji": "🐱", "answer": "Кошка", "wrong": ["Собака", "Тигр", "Лев"]},
            {"emoji": "🐻", "answer": "Медведь", "wrong": ["Собака", "Панда", "Коала"]},
            {"emoji": "🦊", "answer": "Лиса", "wrong": ["Собака", "Волк", "Кошка"]},
            {"emoji": "🐰", "answer": "Кролик", "wrong": ["Мышь", "Хомяк", "Белка"]},
            {"emoji": "🐸", "answer": "Лягушка", "wrong": ["Черепаха", "Крокодил", "Змея"]},
            {"emoji": "🦁", "answer": "Лев", "wrong": ["Тигр", "Кошка", "Пантера"]},
            {"emoji": "🐵", "answer": "Обезьяна", "wrong": ["Человек", "Горилла", "Лемур"]},
            {"emoji": "🐷", "answer": "Свинья", "wrong": ["Корова", "Овца", "Коза"]},
            {"emoji": "🐮", "answer": "Корова", "wrong": ["Бык", "Свинья", "Лошадь"]},
            {"emoji": "🐔", "answer": "Курица", "wrong": ["Утка", "Индейка", "Гусь"]},
            {"emoji": "🦆", "answer": "Утка", "wrong": ["Курица", "Гусь", "Лебедь"]},
            {"emoji": "🦅", "answer": "Орёл", "wrong": ["Сокол", "Ворона", "Голубь"]},
            {"emoji": "🐺", "answer": "Волк", "wrong": ["Собака", "Лиса", "Койот"]},
            {"emoji": "🐴", "answer": "Лошадь", "wrong": ["Осёл", "Зебра", "Корова"]},
        ]
    },
    "food": {
        "question": "Что это за еда?",
        "items": [
            {"emoji": "🍎", "answer": "Яблоко", "wrong": ["Груша", "Персик", "Помидор"]},
            {"emoji": "🍕", "answer": "Пицца", "wrong": ["Бургер", "Хот-дог", "Тако"]},
            {"emoji": "🍔", "answer": "Бургер", "wrong": ["Пицца", "Сэндвич", "Хот-дог"]},
            {"emoji": "🍦", "answer": "Мороженое", "wrong": ["Торт", "Кекс", "Конфета"]},
            {"emoji": "🍩", "answer": "Пончик", "wrong": ["Бублик", "Печенье", "Кекс"]},
            {"emoji": "🍇", "answer": "Виноград", "wrong": ["Черника", "Слива", "Вишня"]},
            {"emoji": "🍓", "answer": "Клубника", "wrong": ["Малина", "Вишня", "Яблоко"]},
            {"emoji": "🥕", "answer": "Морковь", "wrong": ["Огурец", "Свёкла", "Редис"]},
            {"emoji": "🌽", "answer": "Кукуруза", "wrong": ["Пшеница", "Рис", "Горох"]},
            {"emoji": "🍌", "answer": "Банан", "wrong": ["Огурец", "Кабачок", "Дыня"]},
        ]
    },
    "transport": {
        "question": "Что это за транспорт?",
        "items": [
            {"emoji": "🚗", "answer": "Машина", "wrong": ["Автобус", "Грузовик", "Мотоцикл"]},
            {"emoji": "🚌", "answer": "Автобус", "wrong": ["Машина", "Трамвай", "Троллейбус"]},
            {"emoji": "✈️", "answer": "Самолёт", "wrong": ["Вертолёт", "Ракета", "Дрон"]},
            {"emoji": "🚂", "answer": "Поезд", "wrong": ["Трамвай", "Метро", "Автобус"]},
            {"emoji": "🚢", "answer": "Корабль", "wrong": ["Лодка", "Яхта", "Катер"]},
            {"emoji": "🚁", "answer": "Вертолёт", "wrong": ["Самолёт", "Дрон", "Ракета"]},
            {"emoji": "🏍️", "answer": "Мотоцикл", "wrong": ["Велосипед", "Скутер", "Машина"]},
            {"emoji": "🚲", "answer": "Велосипед", "wrong": ["Мотоцикл", "Самокат", "Скутер"]},
            {"emoji": "🚀", "answer": "Ракета", "wrong": ["Самолёт", "Спутник", "Вертолёт"]},
            {"emoji": "⛵", "answer": "Парусник", "wrong": ["Корабль", "Лодка", "Катер"]},
        ]
    },
    "objects": {
        "question": "Что это за предмет?",
        "items": [
            {"emoji": "📱", "answer": "Телефон", "wrong": ["Планшет", "Калькулятор", "Пульт"]},
            {"emoji": "💻", "answer": "Ноутбук", "wrong": ["Планшет", "Телевизор", "Монитор"]},
            {"emoji": "⌚", "answer": "Часы", "wrong": ["Браслет", "Компас", "Таймер"]},
            {"emoji": "📷", "answer": "Фотоаппарат", "wrong": ["Телефон", "Камера", "Бинокль"]},
            {"emoji": "🔑", "answer": "Ключ", "wrong": ["Замок", "Отвёртка", "Гвоздь"]},
            {"emoji": "💡", "answer": "Лампочка", "wrong": ["Свеча", "Фонарик", "Солнце"]},
            {"emoji": "📚", "answer": "Книги", "wrong": ["Тетрадь", "Газета", "Журнал"]},
            {"emoji": "✂️", "answer": "Ножницы", "wrong": ["Нож", "Бритва", "Пила"]},
            {"emoji": "🔨", "answer": "Молоток", "wrong": ["Топор", "Кирка", "Отвёртка"]},
            {"emoji": "⚽", "answer": "Футбольный мяч", "wrong": ["Баскетбольный мяч", "Теннисный мяч", "Волейбольный мяч"]},
        ]
    },
}

# Стандартные настройки
DEFAULT_SETTINGS = {
    "enabled": False,
    "timeout": 120,  # секунд
    "mode": "button",
    "kick_on_fail": True,
    "mute_until_solved": True,
    "newbie_mute": 0,  # Мут после прохождения капчи (0 = выкл, 5/10/15 минут)
}


def get_captcha_settings(chat_id):
    """Получает настройки капчи для чата"""
    return captcha_settings.get(chat_id, DEFAULT_SETTINGS.copy())


def set_captcha_settings(chat_id, settings):
    """Устанавливает настройки капчи"""
    captcha_settings[chat_id] = settings
    _save_captcha_to_db()


def generate_math_captcha():
    """Генерирует математическую капчу"""
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    op = random.choice(["+", "-", "×"])
    
    if op == "+":
        answer = a + b
    elif op == "-":
        # Убедимся, что ответ положительный
        if a < b:
            a, b = b, a
        answer = a - b
    else:  # ×
        answer = a * b
    
    question = f"{a} {op} {b} = ?"
    return question, answer


def generate_text_captcha():
    """Генерирует текстовую капчу с кнопками"""
    # Слова и их варианты
    word_sets = [
        {"correct": "привет", "wrong": ["пока", "здравствуй", "прощай"]},
        {"correct": "собака", "wrong": ["кошка", "мышка", "птица"]},
        {"correct": "солнце", "wrong": ["луна", "звезда", "облако"]},
        {"correct": "вода", "wrong": ["огонь", "земля", "воздух"]},
        {"correct": "дом", "wrong": ["окно", "дверь", "крыша"]},
        {"correct": "книга", "wrong": ["ручка", "тетрадь", "стол"]},
        {"correct": "красный", "wrong": ["синий", "зелёный", "жёлтый"]},
        {"correct": "большой", "wrong": ["маленький", "средний", "огромный"]},
        {"correct": "быстро", "wrong": ["медленно", "тихо", "громко"]},
        {"correct": "весна", "wrong": ["лето", "осень", "зима"]},
    ]
    
    word_data = random.choice(word_sets)
    correct = word_data["correct"]
    wrong = word_data["wrong"]
    
    options = [correct] + wrong
    random.shuffle(options)
    
    return correct, options


def generate_button_options(correct_answer, is_math=True):
    """Генерирует варианты ответов для кнопок"""
    options = [correct_answer]
    
    if is_math:
        # Генерируем неправильные числовые ответы
        while len(options) < 4:
            wrong = correct_answer + random.randint(-5, 5)
            if wrong != correct_answer and wrong >= 0 and wrong not in options:
                options.append(wrong)
    else:
        # Для текстовой капчи - другие слова
        words = ["да", "нет", "ок", "отмена", "пропустить", "выход"]
        while len(options) < 4:
            wrong = random.choice(words)
            if wrong != correct_answer and wrong not in options:
                options.append(wrong)
    
    random.shuffle(options)
    return options


def generate_emoji_captcha():
    """Генерирует эмодзи-капчу"""
    # Выбираем случайную категорию
    category = random.choice(list(EMOJI_CAPTCHA_DATA.keys()))
    data = EMOJI_CAPTCHA_DATA[category]
    
    # Выбираем случайный элемент из категории
    item = random.choice(data["items"])
    
    emoji = item["emoji"]
    question = data["question"]
    correct_answer = item["answer"]
    wrong_answers = item["wrong"]
    
    # Формируем варианты ответов
    options = [correct_answer] + wrong_answers[:3]
    random.shuffle(options)
    
    return emoji, question, correct_answer, options


@bot_admin
@can_restrict
def new_member_captcha(update: Update, context: CallbackContext):
    """Обрабатывает новых участников с капчей"""
    chat = update.effective_chat
    msg = update.effective_message
    
    settings = get_captcha_settings(chat.id)
    
    if not settings["enabled"]:
        return
    
    for new_mem in msg.new_chat_members:
        # Пропускаем ботов и самого бота
        if new_mem.is_bot or new_mem.id == context.bot.id:
            continue
        
        user_id = new_mem.id
        user_name = new_mem.first_name
        
        # Мутим пользователя до прохождения капчи
        if settings["mute_until_solved"]:
            try:
                context.bot.restrict_chat_member(
                    chat.id,
                    user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                )
            except BadRequest as e:
                LOGGER.warning(f"Не удалось замутить: {e}")
        
        # Генерируем капчу в зависимости от режима
        mode = settings["mode"]
        
        if mode == "math":
            question, answer = generate_math_captcha()
            options = generate_button_options(answer, is_math=True)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        str(opt),
                        callback_data=f"captcha_{user_id}_{opt}"
                    )
                    for opt in options[:2]
                ],
                [
                    InlineKeyboardButton(
                        str(opt),
                        callback_data=f"captcha_{user_id}_{opt}"
                    )
                    for opt in options[2:]
                ],
            ]
            
            text = (
                f"👋 Привет, *{user_name}*!\n\n"
                f"🔐 Для подтверждения, что вы не бот, решите пример:\n\n"
                f"*{question}*\n\n"
                f"⏱ У вас {settings['timeout']} секунд."
            )
            
        elif mode == "text":
            answer, options = generate_text_captcha()
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        opt,
                        callback_data=f"captcha_{user_id}_{opt}"
                    )
                    for opt in options[:2]
                ],
                [
                    InlineKeyboardButton(
                        opt,
                        callback_data=f"captcha_{user_id}_{opt}"
                    )
                    for opt in options[2:]
                ],
            ]
            
            text = (
                f"👋 Привет, *{user_name}*!\n\n"
                f"🔐 Выберите слово:\n\n"
                f"*{answer}*\n\n"
                f"⏱ У вас {settings['timeout']} секунд."
            )
        
        elif mode == "emoji":
            emoji, question, answer, options = generate_emoji_captcha()
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        opt,
                        callback_data=f"captcha_{user_id}_{opt}"
                    )
                    for opt in options[:2]
                ],
                [
                    InlineKeyboardButton(
                        opt,
                        callback_data=f"captcha_{user_id}_{opt}"
                    )
                    for opt in options[2:]
                ],
            ]
            
            text = (
                f"👋 Привет, *{user_name}*!\n\n"
                f"🔐 {question}\n\n"
                f"{emoji}\n\n"
                f"⏱ У вас {settings['timeout']} секунд."
            )
            
        else:  # button
            answer = "human"
            
            keyboard = [[
                InlineKeyboardButton(
                    "✅ Я не бот",
                    callback_data=f"captcha_{user_id}_human"
                )
            ]]
            
            text = (
                f"👋 Привет, *{user_name}*!\n\n"
                f"🔐 Пожалуйста, нажмите кнопку ниже, чтобы подтвердить, что вы не бот.\n\n"
                f"⏱ У вас {settings['timeout']} секунд."
            )
        
        # Получаем ID топика если чат - форум
        thread_id = get_thread_id(msg)
        
        # Отправляем сообщение с капчей (не reply, т.к. сервисное сообщение может удалиться)
        try:
            send_kwargs = {
                "chat_id": chat.id,
                "text": text,
                "parse_mode": ParseMode.MARKDOWN,
                "reply_markup": InlineKeyboardMarkup(keyboard),
            }
            if thread_id:
                send_kwargs["message_thread_id"] = thread_id
            
            captcha_msg = context.bot.send_message(**send_kwargs)
            
            # Удаляем сервисное сообщение о входе
            try:
                msg.delete()
            except:
                pass
            
            # Сохраняем информацию о капче
            with CAPTCHA_LOCK:
                pending_captcha[(chat.id, user_id)] = {
                    "answer": str(answer),
                    "message_id": captcha_msg.message_id,
                    "time": time.time(),
                    "mode": mode,
                    "thread_id": thread_id,  # Сохраняем топик
                }
            
            # Планируем таймаут
            context.job_queue.run_once(
                captcha_timeout,
                settings["timeout"],
                context=(chat.id, user_id),
                name=f"captcha_timeout_{chat.id}_{user_id}",
            )
            
        except BadRequest as e:
            LOGGER.warning(f"Ошибка отправки капчи: {e}")


def delete_welcome_after_captcha(context: CallbackContext):
    """Удаляет приветственное сообщение после капчи по таймеру"""
    job_data = context.job.context
    try:
        context.bot.delete_message(job_data["chat_id"], job_data["message_id"])
    except BadRequest:
        pass


def captcha_timeout(context: CallbackContext):
    """Обработчик таймаута капчи"""
    chat_id, user_id = context.job.context
    
    with CAPTCHA_LOCK:
        captcha_data = pending_captcha.pop((chat_id, user_id), None)
    
    if not captcha_data:
        return
    
    settings = get_captcha_settings(chat_id)
    
    try:
        # Удаляем сообщение с капчей
        context.bot.delete_message(chat_id, captcha_data["message_id"])
    except BadRequest:
        pass
    
    # Получаем сохранённый thread_id
    thread_id = captcha_data.get("thread_id") if captcha_data else None
    
    if settings["kick_on_fail"]:
        try:
            # Кикаем пользователя
            context.bot.ban_chat_member(chat_id, user_id)
            context.bot.unban_chat_member(chat_id, user_id)
            
            # Логируем провал капчи
            if log_captcha_fail:
                try:
                    chat = context.bot.get_chat(chat_id)
                    user = type('User', (), {'id': user_id, 'first_name': 'Пользователь'})()
                    log_captcha_fail(context.bot, chat, user, "Таймаут")
                except:
                    pass
            
            send_kwargs = {"chat_id": chat_id, "text": f"⏰ Пользователь не прошёл капчу вовремя и был удалён."}
            if thread_id:
                send_kwargs["message_thread_id"] = thread_id
            context.bot.send_message(**send_kwargs)
        except BadRequest as e:
            LOGGER.warning(f"Не удалось кикнуть: {e}")
    else:
        # Просто оставляем замученным
        try:
            send_kwargs = {"chat_id": chat_id, "text": f"⏰ Пользователь не прошёл капчу. Он остаётся в муте."}
            if thread_id:
                send_kwargs["message_thread_id"] = thread_id
            context.bot.send_message(**send_kwargs)
        except BadRequest:
            pass


def captcha_callback(update: Update, context: CallbackContext):
    """Обработчик ответа на капчу"""
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    
    # Парсим данные callback
    data = query.data.split("_")
    if len(data) < 3:
        query.answer("❌ Ошибка")
        return
    
    target_user_id = int(data[1])
    user_answer = "_".join(data[2:])
    
    # Проверяем, что отвечает именно тот пользователь
    if user.id != target_user_id:
        query.answer("❌ Эта капча не для вас!", show_alert=True)
        return
    
    with CAPTCHA_LOCK:
        captcha_data = pending_captcha.get((chat.id, user.id))
    
    if not captcha_data:
        query.answer("❌ Капча устарела")
        try:
            query.message.delete()
        except BadRequest:
            pass
        return
    
    correct_answer = captcha_data["answer"]
    
    # Проверяем ответ
    if user_answer == correct_answer or user_answer in ("human", "verify"):
        # Капча пройдена!
        with CAPTCHA_LOCK:
            pending_captcha.pop((chat.id, user.id), None)
        
        # Отменяем таймаут
        jobs = context.job_queue.get_jobs_by_name(f"captcha_timeout_{chat.id}_{user.id}")
        for job in jobs:
            job.schedule_removal()
        
        # Снимаем мут
        try:
            context.bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_invite_users=True,
                ),
            )
        except BadRequest as e:
            LOGGER.warning(f"Не удалось снять мут: {e}")
        
        query.answer("✅ Капча пройдена!")
        
        # Логируем успешное прохождение капчи
        if log_captcha_pass:
            log_captcha_pass(context.bot, chat, user)
        
        # Удаляем сообщение с капчей
        try:
            query.message.delete()
        except BadRequest:
            pass
        
        # Получаем сохранённый thread_id
        thread_id = captcha_data.get("thread_id")
        
        # Проверяем настройку мута новичков
        settings = get_captcha_settings(chat.id)
        newbie_mute = settings.get("newbie_mute", 0)
        
        if newbie_mute > 0:
            # Применяем мут на указанное время
            try:
                until_date = datetime.utcnow() + timedelta(minutes=newbie_mute)
                context.bot.restrict_chat_member(
                    chat.id,
                    user.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_polls=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                        can_invite_users=True,
                    ),
                    until_date=until_date,
                )
                LOGGER.info(f"Новичок {user.id} замучен на {newbie_mute} минут в чате {chat.id}")
            except BadRequest as e:
                LOGGER.warning(f"Не удалось замутить новичка: {e}")
        
        # Отправляем приветствие из настроек welcome
        try:
            from MitaHelper.modules.welcome import get_welcome_settings, format_welcome
            welcome_settings = get_welcome_settings(chat.id)
            
            if welcome_settings.get("enabled", True):
                welcome_text = format_welcome(welcome_settings["text"], user, chat)
                
                # Создаём клавиатуру с кнопками если есть
                reply_markup = None
                buttons = welcome_settings.get("buttons", [])
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
                                if len(row) == 2:
                                    keyboard.append(row)
                                    row = []
                    if row:
                        keyboard.append(row)
                    if keyboard:
                        reply_markup = InlineKeyboardMarkup(keyboard)
                
                send_kwargs = {
                    "chat_id": chat.id,
                    "text": welcome_text,
                    "parse_mode": ParseMode.HTML,
                    "disable_web_page_preview": True,
                }
                if reply_markup:
                    send_kwargs["reply_markup"] = reply_markup
                if thread_id:
                    send_kwargs["message_thread_id"] = thread_id
                sent_msg = context.bot.send_message(**send_kwargs)
                
                # Автоудаление приветствия
                delete_after = welcome_settings.get("delete_after", 0)
                if delete_after > 0 and sent_msg:
                    context.job_queue.run_once(
                        delete_welcome_after_captcha,
                        delete_after,
                        context={"chat_id": chat.id, "message_id": sent_msg.message_id},
                        name=f"del_welcome_{sent_msg.message_id}"
                    )
            else:
                # Если приветствие выключено, просто сообщаем о прохождении капчи
                mute_text = f"\n\n🔇 _Вы сможете писать через {newbie_mute} мин._" if newbie_mute > 0 else ""
                send_kwargs = {
                    "chat_id": chat.id,
                    "text": f"✅ *{user.first_name}* прошёл проверку!{mute_text}",
                    "parse_mode": ParseMode.MARKDOWN,
                }
                if thread_id:
                    send_kwargs["message_thread_id"] = thread_id
                context.bot.send_message(**send_kwargs)
        except Exception as e:
            LOGGER.warning(f"Ошибка отправки приветствия после капчи: {e}")
            try:
                mute_text = f"\n\n🔇 _Вы сможете писать через {newbie_mute} мин._" if newbie_mute > 0 else ""
                send_kwargs = {
                    "chat_id": chat.id,
                    "text": f"✅ *{user.first_name}* прошёл проверку!\n\nДобро пожаловать! 👋{mute_text}",
                    "parse_mode": ParseMode.MARKDOWN,
                }
                if thread_id:
                    send_kwargs["message_thread_id"] = thread_id
                context.bot.send_message(**send_kwargs)
            except BadRequest:
                pass
        
    else:
        # Неправильный ответ
        query.answer("❌ Неправильно! Попробуйте ещё раз.", show_alert=True)


@user_admin
def captcha_cmd(update: Update, context: CallbackContext):
    """Команда /captcha - управление капчей"""
    chat = update.effective_chat
    msg = update.effective_message
    args = context.args
    
    settings = get_captcha_settings(chat.id)
    
    if not args:
        # Показываем текущие настройки
        status = "✅ Включена" if settings["enabled"] else "❌ Выключена"
        mode_name = CAPTCHA_MODES.get(settings["mode"], settings["mode"])
        kick = "Да" if settings["kick_on_fail"] else "Нет"
        
        msg.reply_text(
            f"🔐 *Настройки капчи:*\n\n"
            f"Статус: {status}\n"
            f"Режим: `{mode_name}`\n"
            f"Таймаут: `{settings['timeout']}` сек\n"
            f"Кик при неудаче: `{kick}`\n\n"
            f"*Команды:*\n"
            f"• `/captcha on/off` — вкл/выкл\n"
            f"• `/captcha mode <button/math/text>` — режим\n"
            f"• `/captcha timeout <сек>` — таймаут\n"
            f"• `/captcha kick on/off` — кик при неудаче",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    cmd = args[0].lower()
    
    if cmd in ("on", "вкл", "yes", "да"):
        settings["enabled"] = True
        set_captcha_settings(chat.id, settings)
        msg.reply_text("✅ Капча включена!")
        
    elif cmd in ("off", "выкл", "no", "нет"):
        settings["enabled"] = False
        set_captcha_settings(chat.id, settings)
        msg.reply_text("❌ Капча выключена!")
        
    elif cmd == "mode" and len(args) > 1:
        mode = args[1].lower()
        if mode in CAPTCHA_MODES:
            settings["mode"] = mode
            set_captcha_settings(chat.id, settings)
            msg.reply_text(f"✅ Режим капчи: `{CAPTCHA_MODES[mode]}`", parse_mode=ParseMode.MARKDOWN)
        else:
            msg.reply_text(
                f"❌ Доступные режимы:\n"
                f"• `button` — нажать кнопку\n"
                f"• `math` — решить пример\n"
                f"• `text` — ввести слово",
                parse_mode=ParseMode.MARKDOWN,
            )
            
    elif cmd == "timeout" and len(args) > 1:
        try:
            timeout = int(args[1])
            if 30 <= timeout <= 600:
                settings["timeout"] = timeout
                set_captcha_settings(chat.id, settings)
                msg.reply_text(f"✅ Таймаут: `{timeout}` секунд", parse_mode=ParseMode.MARKDOWN)
            else:
                msg.reply_text("❌ Таймаут должен быть от 30 до 600 секунд.")
        except ValueError:
            msg.reply_text("❌ Укажите число секунд.")
            
    elif cmd == "kick" and len(args) > 1:
        if args[1].lower() in ("on", "вкл", "yes", "да"):
            settings["kick_on_fail"] = True
            set_captcha_settings(chat.id, settings)
            msg.reply_text("✅ Кик при неудаче включён.")
        else:
            settings["kick_on_fail"] = False
            set_captcha_settings(chat.id, settings)
            msg.reply_text("❌ Кик при неудаче выключен.")
    else:
        msg.reply_text("❌ Неизвестная команда. Используйте /captcha для справки.")


# ═══════════════════════════════════════════════════════════════
#                      РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ═══════════════════════════════════════════════════════════════

CAPTCHA_HANDLER = CommandHandler("captcha", captcha_cmd, run_async=True)
NEW_MEMBER_CAPTCHA_HANDLER = MessageHandler(
    Filters.status_update.new_chat_members, 
    new_member_captcha, 
    run_async=True
)
CAPTCHA_CALLBACK_HANDLER = CallbackQueryHandler(
    captcha_callback, 
    pattern=r"^captcha_", 
    run_async=True
)

dispatcher.add_handler(CAPTCHA_HANDLER)
dispatcher.add_handler(NEW_MEMBER_CAPTCHA_HANDLER, group=1)
dispatcher.add_handler(CAPTCHA_CALLBACK_HANDLER)


__mod_name__ = "🔐 Капча"

__help__ = """
*Защита от ботов с помощью капчи:*

🔐 *Основные команды:*
• /captcha — показать настройки
• /captcha `on/off` — включить/выключить

⚙️ *Настройка:*
• /captcha mode `<режим>` — режим капчи
• /captcha timeout `<сек>` — время на ответ (30-600)
• /captcha kick `on/off` — кикать при неудаче

📋 *Режимы капчи:*
• `button` — нажать кнопку "Я не бот"
• `math` — решить простой пример (2+3=?)
• `text` — ввести показанное слово

🛡 *Как работает:*
1. Новый участник получает капчу
2. До прохождения он замучен
3. Если не прошёл за N секунд — кик
4. При успехе — мут снимается

*Пример настройки:*
```
/captcha on
/captcha mode math
/captcha timeout 60
/captcha kick on
```
"""
