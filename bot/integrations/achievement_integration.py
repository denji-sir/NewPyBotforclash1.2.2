"""
Интеграция системы достижений с существующими компонентами бота
Фаза 6: Связывание системы достижений со всеми функциями бота
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..services.achievement_service import AchievementService
from ..services.achievement_event_tracker import (
    achievement_tracker,
    track_message_sent,
    track_passport_created,
    track_player_bound,
    track_player_verified,
    track_clan_joined,
    track_command_used
)
from ..services.user_context_service import UserContextService
from ..middleware.contextual_middleware import ContextualMiddleware

logger = logging.getLogger(__name__)


class AchievementIntegrationManager:
    """
    Менеджер интеграции системы достижений с существующими компонентами
    """
    
    def __init__(self):
        self.achievement_service = AchievementService()
        self.context_service = UserContextService()
        
        # Флаг инициализации
        self._initialized = False
    
    async def initialize(self):
        """Инициализация интеграции"""
        
        if self._initialized:
            return
        
        try:
            # Инициализируем базу данных достижений
            await self.achievement_service.initialize_database()
            
            # Запускаем трекер событий
            await achievement_tracker.start_processing()
            
            # Настраиваем хуки интеграции
            await self._setup_integration_hooks()
            
            self._initialized = True
            logger.info("Интеграция системы достижений успешно инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации интеграции достижений: {e}")
            raise
    
    async def _setup_integration_hooks(self):
        """Настройка хуков интеграции с существующими системами"""
        
        # Здесь можно добавить подписки на события других сервисов
        logger.info("Хуки интеграции настроены")
    
    # Методы для интеграции с системой паспортов
    
    async def on_passport_created(
        self, 
        user_id: int, 
        chat_id: int, 
        passport_data: Dict[str, Any]
    ):
        """Обработка создания паспорта"""
        
        try:
            # Отслеживаем событие создания паспорта
            await track_passport_created(user_id, chat_id, passport_data)
            
            # Синхронизируем статистику пользователя
            await achievement_tracker.sync_user_stats(user_id, chat_id)
            
            logger.info(f"Обработано создание паспорта для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки создания паспорта: {e}")
    
    async def on_passport_updated(
        self, 
        user_id: int, 
        chat_id: int, 
        update_data: Dict[str, Any]
    ):
        """Обработка обновления паспорта"""
        
        try:
            await achievement_tracker.track_event(user_id, chat_id, 'passport_updated', {
                'passport_updated': True,
                'update_fields': list(update_data.keys()),
                'update_date': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Ошибка обработки обновления паспорта: {e}")
    
    # Методы для интеграции с системой привязки игроков
    
    async def on_player_bound(
        self, 
        user_id: int, 
        chat_id: int, 
        player_tag: str, 
        player_name: str,
        player_data: Dict[str, Any]
    ):
        """Обработка привязки игрока"""
        
        try:
            # Отслеживаем привязку
            await track_player_bound(user_id, chat_id, player_tag, player_name)
            
            # Отслеживаем игровую статистику
            if 'trophies' in player_data:
                await achievement_tracker.track_event(user_id, chat_id, 'player_stats_updated', {
                    'trophies': player_data['trophies'],
                    'level': player_data.get('expLevel', 1),
                    'player_tag': player_tag
                })
            
            logger.info(f"Обработана привязка игрока {player_name} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки привязки игрока: {e}")
    
    async def on_player_verified(
        self, 
        user_id: int, 
        chat_id: int, 
        player_tag: str,
        verification_data: Dict[str, Any]
    ):
        """Обработка верификации игрока"""
        
        try:
            # Отслеживаем верификацию
            await track_player_verified(user_id, chat_id, player_tag)
            
            # Дополнительные события верификации
            await achievement_tracker.track_event(user_id, chat_id, 'verification_completed', {
                'player_tag': player_tag,
                'verification_method': verification_data.get('method', 'manual'),
                'verifier_id': verification_data.get('verifier_id'),
                'verification_date': datetime.now().isoformat()
            })
            
            logger.info(f"Обработана верификация игрока {player_tag} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки верификации игрока: {e}")
    
    async def on_player_stats_updated(
        self, 
        user_id: int, 
        chat_id: int, 
        player_tag: str,
        old_stats: Dict[str, Any],
        new_stats: Dict[str, Any]
    ):
        """Обработка обновления статистики игрока"""
        
        try:
            # Сравниваем статистику и отслеживаем изменения
            changes = {}
            
            # Проверяем изменение кубков
            old_trophies = old_stats.get('trophies', 0)
            new_trophies = new_stats.get('trophies', 0)
            
            if new_trophies != old_trophies:
                changes['trophies'] = new_trophies
                changes['trophies_change'] = new_trophies - old_trophies
            
            # Проверяем изменение уровня
            old_level = old_stats.get('expLevel', 1)
            new_level = new_stats.get('expLevel', 1)
            
            if new_level > old_level:
                changes['level_up'] = True
                changes['new_level'] = new_level
                changes['level_change'] = new_level - old_level
            
            # Проверяем достижения атак
            old_attack_wins = old_stats.get('attackWins', 0)
            new_attack_wins = new_stats.get('attackWins', 0)
            
            if new_attack_wins > old_attack_wins:
                changes['attack_wins'] = new_attack_wins - old_attack_wins
            
            # Отслеживаем изменения
            if changes:
                await achievement_tracker.track_event(user_id, chat_id, 'player_stats_updated', {
                    'player_tag': player_tag,
                    **changes,
                    'update_date': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Ошибка обработки обновления статистики игрока: {e}")
    
    # Методы для интеграции с клановой системой
    
    async def on_clan_joined(
        self, 
        user_id: int, 
        chat_id: int, 
        clan_tag: str, 
        clan_name: str,
        membership_data: Dict[str, Any]
    ):
        """Обработка вступления в клан"""
        
        try:
            # Отслеживаем вступление в клан
            await track_clan_joined(user_id, chat_id, clan_tag, clan_name)
            
            # Дополнительная информация о членстве
            role = membership_data.get('role', 'member')
            await achievement_tracker.track_event(user_id, chat_id, 'clan_role_assigned', {
                'clan_tag': clan_tag,
                'clan_name': clan_name,
                'role': role,
                'join_date': datetime.now().isoformat()
            })
            
            logger.info(f"Обработано вступление в клан {clan_name} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки вступления в клан: {e}")
    
    async def on_clan_left(
        self, 
        user_id: int, 
        chat_id: int, 
        clan_tag: str, 
        clan_name: str,
        membership_data: Dict[str, Any]
    ):
        """Обработка выхода из клана"""
        
        try:
            # Подсчитываем длительность членства
            join_date = membership_data.get('join_date')
            membership_duration = 0
            
            if join_date:
                if isinstance(join_date, str):
                    join_datetime = datetime.fromisoformat(join_date)
                else:
                    join_datetime = join_date
                
                membership_duration = (datetime.now() - join_datetime).days
            
            await achievement_tracker.track_event(user_id, chat_id, 'clan_left', {
                'clan_tag': clan_tag,
                'clan_name': clan_name,
                'membership_duration_days': membership_duration,
                'leave_date': datetime.now().isoformat()
            })
            
            logger.info(f"Обработан выход из клана {clan_name} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки выхода из клана: {e}")
    
    async def on_clan_war_participation(
        self, 
        user_id: int, 
        chat_id: int, 
        war_data: Dict[str, Any]
    ):
        """Обработка участия в клановой войне"""
        
        try:
            clan_tag = war_data.get('clan_tag')
            war_type = war_data.get('war_type', 'regular')  # regular, cwl, friendly
            
            # Отслеживаем начало участия в войне
            await achievement_tracker.track_event(user_id, chat_id, 'clan_war_started', {
                'clan_tag': clan_tag,
                'war_type': war_type,
                'war_size': war_data.get('team_size', 0),
                'participation_date': datetime.now().isoformat()
            })
            
            logger.info(f"Обработано участие в войне для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки участия в войне: {e}")
    
    async def on_clan_war_ended(
        self, 
        user_id: int, 
        chat_id: int, 
        war_data: Dict[str, Any],
        player_performance: Dict[str, Any]
    ):
        """Обработка окончания клановой войны"""
        
        try:
            war_result = war_data.get('result')  # 'won', 'lost', 'tie'
            
            # Статистика игрока в войне
            attacks_used = player_performance.get('attacks_used', 0)
            stars_earned = player_performance.get('stars_earned', 0)
            destruction_percentage = player_performance.get('destruction_avg', 0)
            
            await achievement_tracker.track_event(user_id, chat_id, 'clan_war_ended', {
                'clan_tag': war_data.get('clan_tag'),
                'war_result': war_result,
                'attacks_used': attacks_used,
                'stars_earned': stars_earned,
                'destruction_percentage': destruction_percentage,
                'war_end_date': datetime.now().isoformat()
            })
            
            logger.info(f"Обработано окончание войны для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки окончания войны: {e}")
    
    async def on_clan_role_changed(
        self, 
        user_id: int, 
        chat_id: int, 
        clan_tag: str,
        old_role: str,
        new_role: str
    ):
        """Обработка изменения роли в клане"""
        
        try:
            # Отслеживаем повышение/понижение
            is_promotion = self._is_role_promotion(old_role, new_role)
            
            await achievement_tracker.track_event(user_id, chat_id, 'clan_role_changed', {
                'clan_tag': clan_tag,
                'old_role': old_role,
                'new_role': new_role,
                'is_promotion': is_promotion,
                'change_date': datetime.now().isoformat()
            })
            
            # Специальное событие для повышений
            if is_promotion and new_role in ['coLeader', 'leader']:
                await achievement_tracker.track_event(user_id, chat_id, 'user_promoted', {
                    'clan_tag': clan_tag,
                    'new_role': new_role,
                    'promotion_date': datetime.now().isoformat()
                })
            
            logger.info(f"Обработано изменение роли с {old_role} на {new_role} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки изменения роли в клане: {e}")
    
    # Методы для интеграции с контекстуальными командами
    
    async def on_command_used(
        self, 
        user_id: int, 
        chat_id: int, 
        command: str,
        command_data: Dict[str, Any]
    ):
        """Обработка использования команды"""
        
        try:
            # Отслеживаем использование команды
            await track_command_used(user_id, chat_id, command)
            
            # Специальные события для определенных команд
            special_commands = {
                '/achievements': 'achievement_explorer',
                '/my_progress': 'progress_tracker',
                '/smart': 'smart_user',
                '/dashboard': 'power_user',
                '/leaderboard': 'competitive_user'
            }
            
            if command in special_commands:
                await achievement_tracker.track_event(user_id, chat_id, 'special_behavior', {
                    'behavior_type': special_commands[command],
                    'command': command,
                    'usage_date': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Ошибка обработки использования команды {command}: {e}")
    
    async def on_message_sent(
        self, 
        user_id: int, 
        chat_id: int, 
        message_data: Dict[str, Any]
    ):
        """Обработка отправленного сообщения"""
        
        try:
            message_length = len(message_data.get('text', ''))
            
            # Отслеживаем сообщение
            await track_message_sent(user_id, chat_id, message_length)
            
            # Анализируем тип сообщения
            message_type = self._analyze_message_type(message_data)
            
            if message_type:
                await achievement_tracker.track_event(user_id, chat_id, 'message_type_sent', {
                    'message_type': message_type,
                    'message_length': message_length,
                    'send_date': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Ошибка обработки отправленного сообщения: {e}")
    
    # Методы для интеграции с контекстуальными системами
    
    async def on_context_changed(
        self, 
        user_id: int, 
        chat_id: int, 
        old_context: Optional[Dict[str, Any]],
        new_context: Dict[str, Any]
    ):
        """Обработка изменения контекста пользователя"""
        
        try:
            context_changes = {}
            
            if old_context:
                # Анализируем изменения в контексте
                for key in ['context_type', 'activity_level', 'experience_level']:
                    old_value = old_context.get(key)
                    new_value = new_context.get(key)
                    
                    if old_value != new_value:
                        context_changes[f"{key}_changed"] = {
                            'from': old_value,
                            'to': new_value
                        }
            
            if context_changes:
                await achievement_tracker.track_event(user_id, chat_id, 'user_context_changed', {
                    'changes': context_changes,
                    'change_date': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Ошибка обработки изменения контекста: {e}")
    
    # Методы для интеграции с middleware
    
    async def integrate_with_middleware(self, middleware: ContextualMiddleware):
        """Интеграция с контекстуальным middleware"""
        
        try:
            # Можно добавить хуки в middleware для автоматического отслеживания
            logger.info("Интеграция с middleware выполнена")
            
        except Exception as e:
            logger.error(f"Ошибка интеграции с middleware: {e}")
    
    # Утилиты
    
    def _is_role_promotion(self, old_role: str, new_role: str) -> bool:
        """Проверка, является ли изменение роли повышением"""
        
        role_hierarchy = {
            'member': 0,
            'elder': 1,
            'coLeader': 2,
            'leader': 3
        }
        
        old_level = role_hierarchy.get(old_role, 0)
        new_level = role_hierarchy.get(new_role, 0)
        
        return new_level > old_level
    
    def _analyze_message_type(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Анализ типа сообщения"""
        
        text = message_data.get('text', '').lower()
        
        if '?' in text:
            return 'question'
        elif any(word in text for word in ['спасибо', 'благодарю', 'thanks']):
            return 'gratitude'
        elif any(word in text for word in ['помощь', 'help', 'как']):
            return 'help_request'
        elif len(text) > 200:
            return 'long_message'
        
        return None
    
    # Методы для ручного управления
    
    async def force_achievement_check(self, user_id: int, chat_id: int):
        """Принудительная проверка достижений пользователя"""
        
        try:
            await achievement_tracker.trigger_manual_check(user_id, chat_id, "all")
            logger.info(f"Выполнена принудительная проверка достижений для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка принудительной проверки достижений: {e}")
    
    async def sync_all_users(self):
        """Синхронизация достижений для всех пользователей"""
        
        try:
            # Здесь можно добавить массовую синхронизацию
            # Получить всех пользователей из паспортной системы
            # и синхронизировать их достижения
            
            logger.info("Начата синхронизация достижений для всех пользователей")
            
        except Exception as e:
            logger.error(f"Ошибка массовой синхронизации: {e}")


# Создаем глобальный экземпляр менеджера интеграции
achievement_integration = AchievementIntegrationManager()


# Функции-декораторы для автоматической интеграции

def track_achievement_event(event_type: str):
    """Декоратор для автоматического отслеживания событий достижений"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                # Выполняем оригинальную функцию
                result = await func(*args, **kwargs)
                
                # Пытаемся извлечь user_id и chat_id из аргументов
                user_id = kwargs.get('user_id')
                chat_id = kwargs.get('chat_id')
                
                # Если не найдены в kwargs, ищем в args
                if not user_id and len(args) >= 2:
                    user_id, chat_id = args[0], args[1]
                
                if user_id and chat_id:
                    # Отслеживаем событие
                    await achievement_tracker.track_event(user_id, chat_id, event_type, {
                        'function_name': func.__name__,
                        'timestamp': datetime.now().isoformat()
                    })
                
                return result
                
            except Exception as e:
                logger.error(f"Ошибка в декораторе отслеживания событий: {e}")
                # Возвращаем результат оригинальной функции даже при ошибке трекинга
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator