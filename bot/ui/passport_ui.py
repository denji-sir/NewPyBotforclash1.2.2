"""
UI компоненты для паспортов
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional, List


class PassportUI:
    """Класс для создания UI элементов паспортов"""
    
    @staticmethod
    def create_passport_keyboard(user_id: int, has_passport: bool = False) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для паспорта
        
        Args:
            user_id: ID пользователя
            has_passport: Есть ли у пользователя паспорт
        
        Returns:
            Клавиатура
        """
        builder = InlineKeyboardBuilder()
        
        if has_passport:
            builder.row(
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"passport:edit:{user_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"passport:delete:{user_id}")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="➕ Создать паспорт", callback_data=f"passport:create:{user_id}")
            )
        
        return builder.as_markup()
    
    @staticmethod
    def create_edit_keyboard(user_id: int) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для редактирования паспорта
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Клавиатура
        """
        builder = InlineKeyboardBuilder()
        
        builder.row(
            InlineKeyboardButton(text="📝 Имя", callback_data=f"passport:edit_name:{user_id}"),
            InlineKeyboardButton(text="🎨 Тема", callback_data=f"passport:edit_theme:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="📖 Био", callback_data=f"passport:edit_bio:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="✅ Готово", callback_data=f"passport:done:{user_id}")
        )
        
        return builder.as_markup()
    
    @staticmethod
    def format_passport_text(passport_data: dict) -> str:
        """
        Форматирует текст паспорта
        
        Args:
            passport_data: Данные паспорта
        
        Returns:
            Отформатированный текст
        """
        text = "📋 **Паспорт игрока**\n\n"
        text += f"👤 Имя: {passport_data.get('name', 'N/A')}\n"
        text += f"🎮 Тег: {passport_data.get('player_tag', 'N/A')}\n"
        
        if passport_data.get('bio'):
            text += f"\n📖 {passport_data['bio']}\n"
        
        return text
    
    @staticmethod
    def create_passport_list_keyboard(passports: List[dict], page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру со списком паспортов
        
        Args:
            passports: Список паспортов
            page: Номер страницы
            per_page: Количество на странице
        
        Returns:
            Клавиатура
        """
        builder = InlineKeyboardBuilder()
        
        start = page * per_page
        end = start + per_page
        page_passports = passports[start:end]
        
        for passport in page_passports:
            builder.row(
                InlineKeyboardButton(
                    text=f"{passport.get('name', 'N/A')} ({passport.get('player_tag', 'N/A')})",
                    callback_data=f"passport:view:{passport.get('user_id')}"
                )
            )
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"passport:list:{page-1}"))
        if end < len(passports):
            nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"passport:list:{page+1}"))
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        return builder.as_markup()
