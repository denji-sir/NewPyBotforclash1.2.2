"""
Сервис для проверки прав доступа и разрешений
"""
import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import ChatMember
from aiogram.exceptions import TelegramBadRequest

from ..models.clan_models import PermissionDenied
from .clan_database_service import get_clan_db_service

logger = logging.getLogger(__name__)


class PermissionService:
    """Сервис для проверки прав доступа"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db_service = get_clan_db_service()
    
    async def is_chat_admin(self, user_id: int, chat_id: int) -> bool:
        """
        Проверить является ли пользователь администратором чата
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            
        Returns:
            bool: True если администратор
        """
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ['creator', 'administrator']
            
            logger.debug(f"User {user_id} admin status in chat {chat_id}: {is_admin}")
            return is_admin
            
        except TelegramBadRequest as e:
            logger.warning(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking admin status: {e}")
            return False
    
    async def is_chat_creator(self, user_id: int, chat_id: int) -> bool:
        """Проверить является ли пользователь создателем чата"""
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            return member.status == 'creator'
        except Exception:
            return False
    
    async def can_register_clans(self, user_id: int, chat_id: int) -> bool:
        """
        Проверить может ли пользователь регистрировать кланы
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            
        Returns:
            bool: True если может регистрировать
        """
        try:
            # Получаем настройки чата
            settings = await self.db_service.get_chat_settings(chat_id)
            
            if settings.admin_only_registration:
                # Только администраторы могут регистрировать
                return await self.is_chat_admin(user_id, chat_id)
            else:
                # Все участники могут регистрировать
                return True
                
        except Exception as e:
            logger.error(f"Error checking clan registration permission: {e}")
            return False
    
    async def can_manage_clan(self, user_id: int, clan_id: int) -> bool:
        """
        Проверить может ли пользователь управлять кланом
        
        Args:
            user_id: ID пользователя
            clan_id: ID клана
            
        Returns:
            bool: True если может управлять
        """
        try:
            clan = await self.db_service.get_clan_by_id(clan_id)
            if not clan:
                return False
            
            # Администраторы чата могут управлять всеми кланами
            if await self.is_chat_admin(user_id, clan.chat_id):
                return True
            
            # Тот кто зарегистрировал клан может им управлять
            if clan.registered_by == user_id:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking clan management permission: {e}")
            return False
    
    async def can_set_default_clan(self, user_id: int, chat_id: int) -> bool:
        """Проверить может ли пользователь устанавливать основной клан"""
        return await self.is_chat_admin(user_id, chat_id)
    
    async def can_view_clan_info(self, user_id: int, clan_id: int) -> bool:
        """Проверить может ли пользователь просматривать информацию о клане"""
        # Пока что все могут просматривать информацию о кланах
        return True
    
    async def can_update_clan_data(self, user_id: int, clan_id: int) -> bool:
        """Проверить может ли пользователь обновлять данные клана"""
        return await self.can_manage_clan(user_id, clan_id)
    
    async def check_chat_permissions(self, user_id: int, chat_id: int) -> dict:
        """
        Получить все разрешения пользователя в чате
        
        Returns:
            dict: Словарь с разрешениями
        """
        try:
            is_admin = await self.is_chat_admin(user_id, chat_id)
            is_creator = await self.is_chat_creator(user_id, chat_id)
            can_register = await self.can_register_clans(user_id, chat_id)
            can_set_default = await self.can_set_default_clan(user_id, chat_id)
            
            return {
                'is_admin': is_admin,
                'is_creator': is_creator,
                'can_register_clans': can_register,
                'can_set_default_clan': can_set_default,
                'can_view_clan_info': True,  # Все могут просматривать
            }
            
        except Exception as e:
            logger.error(f"Error getting chat permissions: {e}")
            return {
                'is_admin': False,
                'is_creator': False,
                'can_register_clans': False,
                'can_set_default_clan': False,
                'can_view_clan_info': True,
            }
    
    async def require_admin(self, user_id: int, chat_id: int, 
                          operation: str = "this operation") -> None:
        """
        Требовать права администратора (выбросить исключение если нет прав)
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            operation: Название операции для сообщения об ошибке
            
        Raises:
            PermissionDenied: Если нет прав администратора
        """
        if not await self.is_chat_admin(user_id, chat_id):
            raise PermissionDenied(f"Administrator rights required for {operation}")
    
    async def require_clan_registration_permission(self, user_id: int, chat_id: int) -> None:
        """
        Требовать права регистрации кланов
        
        Raises:
            PermissionDenied: Если нет прав регистрации
        """
        if not await self.can_register_clans(user_id, chat_id):
            raise PermissionDenied("You don't have permission to register clans")
    
    async def require_clan_management_permission(self, user_id: int, clan_id: int) -> None:
        """
        Требовать права управления кланом
        
        Raises:
            PermissionDenied: Если нет прав управления
        """
        if not await self.can_manage_clan(user_id, clan_id):
            raise PermissionDenied("You don't have permission to manage this clan")


# Singleton instance  
_permission_service: Optional[PermissionService] = None


def init_permission_service(bot: Bot) -> PermissionService:
    """Инициализировать глобальный сервис разрешений"""
    global _permission_service
    _permission_service = PermissionService(bot)
    return _permission_service


def get_permission_service() -> PermissionService:
    """Получить глобальный сервис разрешений"""
    if _permission_service is None:
        raise RuntimeError("Permission service not initialized. Call init_permission_service() first.")
    return _permission_service