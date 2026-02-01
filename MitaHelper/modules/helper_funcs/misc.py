# -*- coding: utf-8 -*-
"""
Вспомогательные функции
"""

from typing import Dict, List

from telegram import InlineKeyboardButton, MAX_MESSAGE_LENGTH, ParseMode
from telegram.error import TelegramError

from MitaHelper import NO_LOAD


class EqInlineKeyboardButton(InlineKeyboardButton):
    """Кнопка с поддержкой сравнения"""
    def __eq__(self, other):
        return self.text == other.text

    def __lt__(self, other):
        return self.text < other.text

    def __gt__(self, other):
        return self.text > other.text


def split_message(msg: str) -> List[str]:
    """Разбивает длинное сообщение на части"""
    if len(msg) < MAX_MESSAGE_LENGTH:
        return [msg]

    lines = msg.splitlines(True)
    small_msg = ""
    result = []
    
    for line in lines:
        if len(small_msg) + len(line) < MAX_MESSAGE_LENGTH:
            small_msg += line
        else:
            result.append(small_msg)
            small_msg = line
    else:
        result.append(small_msg)

    return result


def paginate_modules(page_n: int, module_dict: Dict, prefix: str, chat=None) -> List:
    """Создаёт пагинацию для модулей"""
    if not chat:
        modules = sorted(
            [
                EqInlineKeyboardButton(
                    x.__mod_name__,
                    callback_data=f"{prefix}_module({x.__mod_name__.lower()})",
                )
                for x in module_dict.values()
            ]
        )
    else:
        modules = sorted(
            [
                EqInlineKeyboardButton(
                    x.__mod_name__,
                    callback_data=f"{prefix}_module({chat},{x.__mod_name__.lower()})",
                )
                for x in module_dict.values()
            ]
        )

    # Группируем по 3 кнопки в ряд
    pairs = [modules[i:i + 3] for i in range(0, len(modules), 3)]
    
    # Вычисляем количество страниц
    max_num_pages = len(pairs) // 7 + (1 if len(pairs) % 7 else 0)
    
    # Модули для текущей страницы
    modulo_page = page_n % max_num_pages if max_num_pages else 0
    
    # Кнопки навигации
    if len(pairs) > 7:
        pairs = pairs[modulo_page * 7: (modulo_page + 1) * 7]
        pairs.append(
            [
                EqInlineKeyboardButton(
                    "◀️", callback_data=f"{prefix}_prev({modulo_page})"
                ),
                EqInlineKeyboardButton(
                    f"{modulo_page + 1}/{max_num_pages}",
                    callback_data="none"
                ),
                EqInlineKeyboardButton(
                    "▶️", callback_data=f"{prefix}_next({modulo_page})"
                ),
            ]
        )
        
    # Кнопка закрытия
    pairs.append([EqInlineKeyboardButton("❌ Закрыть", callback_data="close_menu")])

    return pairs


def build_keyboard(buttons):
    """Создаёт клавиатуру из списка кнопок"""
    keyb = []
    for btn in buttons:
        if btn.same_line and keyb:
            keyb[-1].append(InlineKeyboardButton(btn.name, url=btn.url))
        else:
            keyb.append([InlineKeyboardButton(btn.name, url=btn.url)])

    return keyb


def revert_buttons(buttons):
    """Преобразует кнопки обратно в текст"""
    res = ""
    for btn in buttons:
        if btn.same_line:
            res += f"\n[{btn.name}](buttonurl://{btn.url}:same)"
        else:
            res += f"\n[{btn.name}](buttonurl://{btn.url})"

    return res


def is_module_loaded(name: str) -> bool:
    """Проверяет, загружен ли модуль"""
    return name not in NO_LOAD
