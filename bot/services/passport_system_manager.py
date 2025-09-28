"""
Менеджер системы паспортов
Координирует работу всех компонентов системы паспортов
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.passport_models import (
    PassportInfo, PassportOperationLog, PassportStatus, PassportSettings,
    PassportStats, PlayerBinding, PassportNotFound, PassportAlreadyExists
)
from ..services.passport_database_service import get_passport_db_service
from ..services.clan_database_service import get_clan_db_service
from ..services.coc_api_service import get_coc_api_service

logger = logging.getLogger(__name__)


class PassportSystemManager:
    """Центральный менеджер для управления системой паспортов"""
    
    def __init__(self):
        self.passport_service = get_passport_db_service()
        self.clan_service = get_clan_db_service()
        self.coc_api_service = get_coc_api_service()
    
    async def create_passport_with_validation(self, user_id: int, chat_id: int, 
                                            username: Optional[str] = None,
                                            display_name: Optional[str] = None,
                                            preferred_clan_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Создание паспорта с валидацией и интеграцией
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            username: Имя пользователя
            display_name: Отображаемое имя
            preferred_clan_id: ID предпочитаемого клана
            
        Returns:
            Dict[str, Any]: Результат создания
        """
        try:
            # 1. Проверяем существование паспорта
            existing = await self.passport_service.get_passport_by_user(user_id, chat_id)
            if existing:
                return {
                    'success': False,
                    'error': 'Паспорт уже существует',
                    'error_code': 'PASSPORT_EXISTS'
                }
            
            # 2. Валидируем клан если указан
            if preferred_clan_id:
                clan = await self.clan_service.get_clan_by_id(preferred_clan_id)
                if not clan or clan.chat_id != chat_id:
                    return {
                        'success': False,
                        'error': 'Указанный клан не найден или недоступен',
                        'error_code': 'INVALID_CLAN'
                    }
            
            # 3. Валидируем display_name
            if display_name and len(display_name) > 50:
                return {
                    'success': False,
                    'error': 'Имя слишком длинное (максимум 50 символов)',
                    'error_code': 'NAME_TOO_LONG'
                }
            
            # 4. Создаем паспорт
            passport = await self.passport_service.create_passport(
                user_id=user_id,
                chat_id=chat_id,
                username=username,
                display_name=display_name or username,
                preferred_clan_id=preferred_clan_id
            )
            
            # 5. Инициализируем базовую статистику
            await self.update_passport_stats(passport.id, {
                'messages_count': 0,
                'commands_used': 1,  # Команда создания паспорта
                'days_active': 1,
                'last_activity': datetime.now()
            })
            
            # 6. Логируем создание
            log_entry = PassportOperationLog.create_log(
                operation_type='create',
                passport_id=passport.id,
                user_id=user_id,
                username=username,
                operation_details={
                    'display_name': display_name,
                    'preferred_clan_id': preferred_clan_id
                }
            )
            await self.passport_service.log_operation(log_entry)
            
            return {
                'success': True,
                'passport': passport,
                'message': 'Паспорт успешно создан'
            }
            
        except PassportAlreadyExists:
            return {
                'success': False,
                'error': 'Паспорт уже существует',
                'error_code': 'PASSPORT_EXISTS'
            }
        except Exception as e:
            logger.error(f"Error creating passport for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def bind_player_to_passport(self, passport_id: int, player_tag: str, 
                                    verified_by: Optional[int] = None) -> Dict[str, Any]:
        """
        Привязка игрока CoC к паспорту
        
        Args:
            passport_id: ID паспорта
            player_tag: Тег игрока CoC
            verified_by: ID верификатора (администратора)
            
        Returns:
            Dict[str, Any]: Результат привязки
        """
        try:
            # 1. Получаем паспорт
            passport = await self.passport_service.get_passport_by_id(passport_id)
            if not passport:
                return {
                    'success': False,
                    'error': 'Паспорт не найден',
                    'error_code': 'PASSPORT_NOT_FOUND'
                }
            
            # 2. Получаем данные игрока из CoC API
            async with self.coc_api_service:
                player_data = await self.coc_api_service.get_player(player_tag)
            
            if not player_data:
                return {
                    'success': False,
                    'error': 'Игрок не найден в Clash of Clans',
                    'error_code': 'PLAYER_NOT_FOUND'
                }
            
            # 3. Создаем привязку
            player_binding = PlayerBinding(
                player_tag=player_data.tag,
                player_name=player_data.name,
                clan_tag=getattr(player_data, 'clan_tag', None),
                clan_name=getattr(player_data, 'clan_name', None),
                verified=verified_by is not None,
                verified_by=verified_by,
                verified_at=datetime.now() if verified_by else None
            )
            
            # 4. Обновляем паспорт
            success = await self.passport_service.update_passport(
                passport_id, player_binding=player_binding
            )
            
            if not success:
                return {
                    'success': False,
                    'error': 'Ошибка сохранения привязки',
                    'error_code': 'SAVE_ERROR'
                }
            
            # 5. Логируем операцию
            log_entry = PassportOperationLog.create_log(
                operation_type='bind_player',
                passport_id=passport_id,
                user_id=passport.user_id,
                username=passport.username,
                operation_details={
                    'player_tag': player_tag,
                    'player_name': player_data.name,
                    'verified': player_binding.verified,
                    'verified_by': verified_by
                }
            )
            await self.passport_service.log_operation(log_entry)
            
            return {
                'success': True,
                'player_binding': player_binding,
                'message': 'Игрок успешно привязан к паспорту'
            }
            
        except Exception as e:
            logger.error(f"Error binding player {player_tag} to passport {passport_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    async def update_passport_stats(self, passport_id: int, stats_update: Dict[str, Any]) -> bool:
        """
        Обновление статистики паспорта
        
        Args:
            passport_id: ID паспорта
            stats_update: Данные для обновления статистики
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            passport = await self.passport_service.get_passport_by_id(passport_id)
            if not passport:
                return False
            
            # Обновляем статистику
            current_stats = passport.stats
            
            # Инкрементальные обновления
            if 'messages_count' in stats_update:
                current_stats.messages_count += stats_update['messages_count']
            
            if 'commands_used' in stats_update:
                current_stats.commands_used += stats_update['commands_used']
            
            # Прямые обновления
            if 'days_active' in stats_update:
                current_stats.days_active = max(current_stats.days_active, stats_update['days_active'])
            
            if 'last_activity' in stats_update:
                current_stats.last_activity = stats_update['last_activity']
            
            # Сохраняем
            return await self.passport_service.update_passport(
                passport_id, stats=current_stats
            )
            
        except Exception as e:
            logger.error(f"Error updating passport stats {passport_id}: {e}")
            return False
    
    async def get_passport_with_clan_integration(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение паспорта с интеграцией данных клана
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            
        Returns:
            Optional[Dict[str, Any]]: Интегрированные данные паспорта
        """
        try:
            passport = await self.passport_service.get_passport_by_user(user_id, chat_id)
            if not passport:
                return None
            
            result = {
                'passport': passport,
                'clan_data': None,
                'player_data': None,
                'recommendations': []
            }
            
            # Получаем данные клана если есть
            if passport.preferred_clan_id:
                clan = await self.clan_service.get_clan_by_id(passport.preferred_clan_id)
                result['clan_data'] = clan
            
            # Получаем данные игрока если есть привязка
            if passport.player_binding:
                try:
                    async with self.coc_api_service:
                        player_data = await self.coc_api_service.get_player(
                            passport.player_binding.player_tag
                        )
                        result['player_data'] = player_data
                except Exception as e:
                    logger.warning(f"Failed to fetch player data: {e}")
            
            # Генерируем рекомендации
            result['recommendations'] = await self._generate_passport_recommendations(passport)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting integrated passport for user {user_id}: {e}")
            return None
    
    async def get_chat_passport_analytics(self, chat_id: int) -> Dict[str, Any]:
        """
        Получение аналитики паспортов для чата
        
        Args:
            chat_id: ID чата
            
        Returns:
            Dict[str, Any]: Аналитические данные
        """
        try:
            # Получаем все паспорта
            passports = await self.passport_service.get_chat_passports(chat_id)
            
            if not passports:
                return {
                    'total_passports': 0,
                    'completion_stats': {},
                    'activity_stats': {},
                    'clan_distribution': {}
                }
            
            # Анализируем завершенность
            bound_passports = [p for p in passports if p.player_binding]
            clan_bound = [p for p in passports if p.preferred_clan_id]
            
            # Статистика активности
            total_messages = sum(p.stats.messages_count for p in passports)
            total_commands = sum(p.stats.commands_used for p in passports)
            
            # Распределение по кланам
            clan_distribution = {}
            for passport in passports:
                if passport.preferred_clan_name:
                    clan_name = passport.preferred_clan_name
                    clan_distribution[clan_name] = clan_distribution.get(clan_name, 0) + 1
            
            return {
                'total_passports': len(passports),
                'completion_stats': {
                    'bound_players': len(bound_passports),
                    'clan_bound': len(clan_bound),
                    'completion_rate': (len(bound_passports) / len(passports)) * 100 if passports else 0
                },
                'activity_stats': {
                    'total_messages': total_messages,
                    'total_commands': total_commands,
                    'avg_messages_per_passport': total_messages / len(passports) if passports else 0,
                    'avg_commands_per_passport': total_commands / len(passports) if passports else 0
                },
                'clan_distribution': clan_distribution,
                'active_passports': len([p for p in passports if p.status == PassportStatus.ACTIVE])
            }
            
        except Exception as e:
            logger.error(f"Error getting passport analytics for chat {chat_id}: {e}")
            return {'error': str(e)}
    
    async def _generate_passport_recommendations(self, passport: PassportInfo) -> List[str]:
        """Генерация рекомендаций для паспорта"""
        recommendations = []
        
        try:
            # Рекомендации по привязке игрока
            if not passport.player_binding:
                recommendations.append("🎮 Привяжите своего игрока CoC командой /bind_player <тег>")
            elif not passport.player_binding.verified:
                recommendations.append("✅ Попросите администратора верифицировать вашего игрока")
            
            # Рекомендации по клану
            if not passport.preferred_clan_id:
                recommendations.append("🏰 Выберите предпочитаемый клан в настройках паспорта")
            
            # Рекомендации по активности
            if passport.stats.messages_count < 10:
                recommendations.append("💬 Будьте активнее в чате для повышения рейтинга")
            
            if passport.stats.commands_used < 5:
                recommendations.append("🤖 Изучите доступные команды бота")
            
            # Рекомендации по настройкам
            if passport.settings.privacy_level == 1 and not passport.bio:
                recommendations.append("📝 Добавьте информацию о себе в биографию")
            
            return recommendations[:5]  # Максимум 5 рекомендаций
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []


# Глобальная функция получения менеджера
def get_passport_system_manager() -> PassportSystemManager:
    """Получение экземпляра менеджера системы паспортов"""
    return PassportSystemManager()