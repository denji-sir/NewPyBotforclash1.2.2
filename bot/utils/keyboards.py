"""
Утилиты для создания клавиатур
"""

from typing import List, Tuple, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_inline_keyboard(
    buttons: List[List[Tuple[str, str]]], 
    row_width: int = 2
) -> InlineKeyboardMarkup:
    """
    Создать inline клавиатуру
    
    Args:
        buttons: Список списков кнопок [(text, callback_data), ...]
        row_width: Количество кнопок в ряду
        
    Returns:
        InlineKeyboardMarkup: Готовая клавиатура
    """
    keyboard = []
    
    for row in buttons:
        keyboard_row = []
        for text, callback_data in row:
            keyboard_row.append(
                InlineKeyboardButton(text=text, callback_data=callback_data)
            )
        keyboard.append(keyboard_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
