"""
Система привязки игроков CoC к паспортам
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.passport_models import PlayerBinding, PassportOperationLog
from ..models.clan_models import ClanNotFound, ApiError
from ..services.passport_database_service import get_passport_db_service
from ..services.coc_api_service import get_coc_api_service
from ..services.permission_service import get_permission_service
from ..utils.validators import ClanTagValidator, format_number

logger = logging.getLogger(__name__)


class PlayerBindingService:
    """Сервис для привязки игроков CoC к паспортам"""
    
    def __init__(self):
        self.passport_service = get_passport_db_service()
        self.coc_api_service = get_coc_api_service()
        self.permission_service = get_permission_service()
    
    async def bind_player_to_passport(self, passport_id: int, player_tag: str, 
                                    auto_verify: bool = False, verified_by: Optional[int] = None) -> Dict[str, Any]:
        """
        Привязка игрока к паспорту
        
        Args:
            passport_id: ID паспорта
            player_tag: Тег игрока CoC
            auto_verify: Автоматическая верификация
            verified_by: ID верификатора
            
        Returns:
            Dict[str, Any]: Результат привязки
        """
        try:
            # Нормализуем тег игрока
            normalized_tag = ClanTagValidator.normalize_clan_tag(player_tag)
            
            # Валидируем тег
            is_valid, error = ClanTagValidator.validate_clan_tag(normalized_tag)
            if not is_valid:
                return {
                    'success': False,
                    'error': f'Некорректный тег игрока: {error}',
                    'error_code': 'INVALID_TAG'
                }
            
            # Получаем паспорт
            passport = await self.passport_service.get_passport_by_id(passport_id)
            if not passport:
                return {
                    'success': False,
                    'error': 'Паспорт не найден',
                    'error_code': 'PASSPORT_NOT_FOUND'
                }
            
            # Проверяем, не привязан ли уже игрок
            if passport.player_binding and passport.player_binding.player_tag == normalized_tag:
                return {
                    'success': False,
                    'error': 'Этот игрок уже привязан к паспорту',
                    'error_code': 'ALREADY_BOUND'
                }
            
            # Получаем данные игрока из CoC API
            async with self.coc_api_service:
                player_data = await self.coc_api_service.get_player(normalized_tag)
            
            if not player_data:
                return {
                    'success': False,
                    'error': 'Игрок не найден в Clash of Clans',
                    'error_code': 'PLAYER_NOT_FOUND'
                }
            
            # Получаем данные клана игрока если есть
            clan_tag = None
            clan_name = None
            
            if hasattr(player_data, 'clan') and player_data.clan:
                clan_tag = getattr(player_data.clan, 'tag', None)
                clan_name = getattr(player_data.clan, 'name', None)
            
            # Создаем привязку
            player_binding = PlayerBinding(
                player_tag=player_data.tag,
                player_name=player_data.name,
                clan_tag=clan_tag,
                clan_name=clan_name,
                verified=auto_verify or (verified_by is not None),
                verified_by=verified_by,
                verified_at=datetime.now() if (auto_verify or verified_by) else None
            )
            
            # Обновляем паспорт
            success = await self.passport_service.update_passport(
                passport_id, player_binding=player_binding
            )
            
            if not success:
                return {
                    'success': False,
                    'error': 'Ошибка сохранения привязки',
                    'error_code': 'SAVE_ERROR'
                }
            
            # Логируем операцию
            log_entry = PassportOperationLog.create_log(
                operation_type='bind_player',
                passport_id=passport_id,
                user_id=passport.user_id,
                username=passport.username,
                operation_details={
                    'player_tag': normalized_tag,
                    'player_name': player_data.name,
                    'clan_tag': clan_tag,
                    'clan_name': clan_name,
                    'verified': player_binding.verified,
                    'verified_by': verified_by
                }
            )
            await self.passport_service.log_operation(log_entry)
            
            return {
                'success': True,
                'player_binding': player_binding,
                'player_data': player_data,
                'message': 'Игрок успешно привязан к паспорту'
            }
            
        except ClanNotFound:
            return {
                'success': False,
                'error': 'Игрок не найден в Clash of Clans',
                'error_code': 'PLAYER_NOT_FOUND'
            }
        except ApiError as e:
            return {
                'success': False,
                'error': f'Ошибка CoC API: {e}',
                'error_code': 'API_ERROR'
            }
        except Exception as e:
            logger.error(f"Error binding player {player_tag} to passport {passport_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def verify_player_binding(self, passport_id: int, verified_by: int, 
                                  chat_id: int) -> Dict[str, Any]:
        """
        Верификация привязки игрока администратором
        
        Args:
            passport_id: ID паспорта
            verified_by: ID верификатора
            chat_id: ID чата
            
        Returns:
            Dict[str, Any]: Результат верификации
        """
        try:
            # Проверяем права администратора
            try:
                await self.permission_service.require_admin(verified_by, chat_id, "player verification")
            except Exception:
                return {
                    'success': False,
                    'error': 'Недостаточно прав для верификации',
                    'error_code': 'ACCESS_DENIED'
                }
            
            # Получаем паспорт
            passport = await self.passport_service.get_passport_by_id(passport_id)
            if not passport:
                return {
                    'success': False,
                    'error': 'Паспорт не найден',
                    'error_code': 'PASSPORT_NOT_FOUND'
                }
            
            # Проверяем наличие привязки
            if not passport.player_binding:
                return {
                    'success': False,
                    'error': 'К паспорту не привязан игрок',
                    'error_code': 'NO_BINDING'
                }
            
            # Проверяем, не верифицирована ли уже привязка
            if passport.player_binding.verified:
                return {
                    'success': False,
                    'error': 'Привязка уже верифицирована',
                    'error_code': 'ALREADY_VERIFIED'
                }
            
            # Обновляем привязку
            updated_binding = passport.player_binding
            updated_binding.verified = True
            updated_binding.verified_by = verified_by
            updated_binding.verified_at = datetime.now()
            
            success = await self.passport_service.update_passport(
                passport_id, player_binding=updated_binding
            )
            
            if not success:
                return {
                    'success': False,
                    'error': 'Ошибка сохранения верификации',
                    'error_code': 'SAVE_ERROR'
                }
            
            # Логируем верификацию
            log_entry = PassportOperationLog.create_log(
                operation_type='verify_player',
                passport_id=passport_id,
                user_id=verified_by,
                operation_details={
                    'verified_player_tag': updated_binding.player_tag,
                    'verified_player_name': updated_binding.player_name
                }
            )
            await self.passport_service.log_operation(log_entry)
            
            return {
                'success': True,
                'message': 'Привязка игрока верифицирована',
                'verified_binding': updated_binding
            }
            
        except Exception as e:
            logger.error(f"Error verifying player binding for passport {passport_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def unbind_player_from_passport(self, passport_id: int, user_id: int) -> Dict[str, Any]:
        """
        Отвязка игрока от паспорта
        
        Args:
            passport_id: ID паспорта
            user_id: ID пользователя (должен быть владельцем)
            
        Returns:
            Dict[str, Any]: Результат отвязки
        """
        try:
            # Получаем паспорт
            passport = await self.passport_service.get_passport_by_id(passport_id)
            if not passport:
                return {
                    'success': False,
                    'error': 'Паспорт не найден',
                    'error_code': 'PASSPORT_NOT_FOUND'
                }
            
            # Проверяем права (только владелец может отвязать)
            if passport.user_id != user_id:
                return {
                    'success': False,
                    'error': 'Только владелец может отвязать игрока',
                    'error_code': 'ACCESS_DENIED'
                }
            
            # Проверяем наличие привязки
            if not passport.player_binding:
                return {
                    'success': False,
                    'error': 'К паспорту не привязан игрок',
                    'error_code': 'NO_BINDING'
                }
            
            # Сохраняем данные для лога
            old_binding = passport.player_binding
            
            # Обновляем паспорт (убираем привязку)
            success = await self.passport_service.update_passport(
                passport_id, player_binding=None
            )
            
            if not success:
                return {
                    'success': False,
                    'error': 'Ошибка сохранения изменений',
                    'error_code': 'SAVE_ERROR'
                }
            
            # Логируем отвязку
            log_entry = PassportOperationLog.create_log(
                operation_type='unbind_player',
                passport_id=passport_id,
                user_id=user_id,
                username=passport.username,
                operation_details={
                    'unbound_player_tag': old_binding.player_tag,
                    'unbound_player_name': old_binding.player_name
                }
            )
            await self.passport_service.log_operation(log_entry)
            
            return {
                'success': True,
                'message': 'Игрок отвязан от паспорта',
                'unbound_binding': old_binding
            }
            
        except Exception as e:
            logger.error(f"Error unbinding player from passport {passport_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def get_clan_members_for_binding(self, clan_tag: str) -> Dict[str, Any]:
        """
        Получение участников клана для привязки
        
        Args:
            clan_tag: Тег клана
            
        Returns:
            Dict[str, Any]: Список участников клана
        """
        try:
            # Нормализуем тег клана
            normalized_tag = ClanTagValidator.normalize_clan_tag(clan_tag)
            
            # Валидируем тег
            is_valid, error = ClanTagValidator.validate_clan_tag(normalized_tag)
            if not is_valid:
                return {
                    'success': False,
                    'error': f'Некорректный тег клана: {error}',
                    'error_code': 'INVALID_TAG'
                }
            
            # Получаем участников из CoC API
            async with self.coc_api_service:
                members = await self.coc_api_service.get_clan_members(normalized_tag)
            
            if not members:
                return {
                    'success': False,
                    'error': 'Клан не найден или пуст',
                    'error_code': 'CLAN_NOT_FOUND'
                }
            
            # Сортируем участников по роли и донатам
            role_order = {'leader': 0, 'coLeader': 1, 'admin': 2, 'member': 3}
            members.sort(key=lambda x: (
                role_order.get(x.get('role', 'member'), 4),
                -x.get('donations', 0)
            ))
            
            # Форматируем для отображения
            formatted_members = []
            for member in members:
                formatted_members.append({
                    'tag': member.get('tag', ''),
                    'name': member.get('name', 'Unknown'),
                    'role': member.get('role', 'member'),
                    'level': member.get('expLevel', 0),
                    'donations': member.get('donations', 0),
                    'received': member.get('donationsReceived', 0)
                })
            
            return {
                'success': True,
                'members': formatted_members,
                'clan_tag': normalized_tag,
                'total_members': len(formatted_members)
            }
            
        except ClanNotFound:
            return {
                'success': False,
                'error': 'Клан не найден в Clash of Clans',
                'error_code': 'CLAN_NOT_FOUND'
            }
        except ApiError as e:
            return {
                'success': False,
                'error': f'Ошибка CoC API: {e}',
                'error_code': 'API_ERROR'
            }
        except Exception as e:
            logger.error(f"Error getting clan members for {clan_tag}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def search_player_by_name(self, player_name: str, limit: int = 10) -> Dict[str, Any]:
        """
        Поиск игроков по имени (ограниченный функционал)
        
        Args:
            player_name: Имя игрока для поиска
            limit: Максимальное количество результатов
            
        Returns:
            Dict[str, Any]: Результаты поиска
        """
        try:
            # В CoC API нет прямого поиска по имени игроков
            # Это заглушка для будущей реализации через другие методы
            
            return {
                'success': False,
                'error': 'Поиск по имени игрока пока не поддерживается',
                'error_code': 'NOT_SUPPORTED',
                'suggestion': 'Используйте точный тег игрока для привязки'
            }
            
        except Exception as e:
            logger.error(f"Error searching player by name {player_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def get_binding_statistics(self, chat_id: int) -> Dict[str, Any]:
        """
        Статистика привязок игроков в чате
        
        Args:
            chat_id: ID чата
            
        Returns:
            Dict[str, Any]: Статистика привязок
        """
        try:
            # Получаем все паспорта чата
            passports = await self.passport_service.get_chat_passports(chat_id)
            
            if not passports:
                return {
                    'total_passports': 0,
                    'bound_passports': 0,
                    'verified_bindings': 0,
                    'pending_verifications': 0,
                    'completion_rate': 0
                }
            
            # Анализируем привязки
            bound_passports = [p for p in passports if p.player_binding]
            verified_bindings = [p for p in bound_passports if p.player_binding.verified]
            pending_verifications = [p for p in bound_passports if not p.player_binding.verified]
            
            # Распределение по кланам
            clan_distribution = {}
            for passport in bound_passports:
                if passport.player_binding.clan_name:
                    clan_name = passport.player_binding.clan_name
                    clan_distribution[clan_name] = clan_distribution.get(clan_name, 0) + 1
            
            return {
                'total_passports': len(passports),
                'bound_passports': len(bound_passports),
                'verified_bindings': len(verified_bindings),
                'pending_verifications': len(pending_verifications),
                'completion_rate': (len(bound_passports) / len(passports)) * 100 if passports else 0,
                'verification_rate': (len(verified_bindings) / len(bound_passports)) * 100 if bound_passports else 0,
                'clan_distribution': clan_distribution
            }
            
        except Exception as e:
            logger.error(f"Error getting binding statistics for chat {chat_id}: {e}")
            return {'error': str(e)}


# Глобальная функция получения сервиса
def get_player_binding_service() -> PlayerBindingService:
    """Получение экземпляра сервиса привязки игроков"""
    return PlayerBindingService()