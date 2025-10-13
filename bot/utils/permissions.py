"""
Утилиты для проверки прав доступа
"""

import os
from typing import Optional
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, ChatMemberOwner, ChatMemberAdministrator


async def is_admin(user_id: int) -> bool:
    """
    Проверить, является ли пользователь администратором бота
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если администратор
    """
    admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
    if not admin_ids_str:
        return False
    
    admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
    return user_id in admin_ids


async def is_group_admin(
    user_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    bot: Optional[Bot] = None,
    message: Optional[Message] = None
) -> bool:
    """
    Проверить, является ли пользователь администратором группы.
    
    Args:
        user_id: ID пользователя (если передается напрямую)
        chat_id: ID чата (если передается напрямую)
        bot: Экземпляр бота для запроса (если передается напрямую)
        message: Сообщение, из которого можно извлечь все параметры
        
    Returns:
        bool: True если администратор группы
    """
    if message is not None:
        if not message.chat or message.chat.type == 'private':
            return False
        user_id = message.from_user.id if message.from_user else None
        chat_id = message.chat.id
        bot = message.bot
    
    if user_id is None or chat_id is None or bot is None:
        return False
    
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return isinstance(member, (ChatMemberOwner, ChatMemberAdministrator))
    except Exception:
        return False


async def is_group_admin_callback(callback: CallbackQuery) -> bool:
    """
    Проверить, является ли пользователь администратором группы (для callback)
    
    Args:
        callback: Callback query
        
    Returns:
        bool: True если администратор группы
    """
    return await is_group_admin(
        user_id=callback.from_user.id if callback.from_user else None,
        chat_id=callback.message.chat.id if callback.message and callback.message.chat else None,
        bot=callback.bot
    )


async def check_admin_permission(user_id: int, chat_id: int, bot: Bot) -> bool:
    """
    Проверить права администратора
    
    Args:
        user_id: ID пользователя
        chat_id: ID чата
        bot: Экземпляр бота
        
    Returns:
        bool: True если есть права администратора
    """
    # Проверяем глобального админа бота
    if await is_admin(user_id):
        return True
    
    # Проверяем админа группы
    return await is_group_admin(user_id=user_id, chat_id=chat_id, bot=bot)


async def get_user_permissions(user_id: int, chat_id: int, bot: Bot) -> dict:
    """
    Получить права пользователя
    
    Args:
        user_id: ID пользователя
        chat_id: ID чата
        bot: Экземпляр бота
        
    Returns:
        dict: Словарь с правами пользователя
    """
    is_bot_admin = await is_admin(user_id)
    is_chat_admin = await is_group_admin(user_id=user_id, chat_id=chat_id, bot=bot)
    
    return {
        'is_bot_admin': is_bot_admin,
        'is_chat_admin': is_chat_admin,
        'is_admin': is_bot_admin or is_chat_admin,
        'can_manage_users': is_bot_admin or is_chat_admin,
        'can_manage_settings': is_bot_admin or is_chat_admin,
    }
