"""
Система автоматического отслеживания событий для достижений
Фаза 6: Интеграция с существующими системами для автоматического прогресса
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import json

from ..services.achievement_service import AchievementService
from ..services.user_context_service import UserContextService
from ..services.passport_database_service import PassportDatabaseService
from ..services.clan_database_service import ClanDatabaseService

logger = logging.getLogger(__name__)


class AchievementEventTracker:
    """
    Центральная система отслеживания событий для достижений
    """
    
    def __init__(self):
        self.achievement_service = AchievementService()
        self.context_service = UserContextService()
        self.passport_service = PassportDatabaseService()
        self.clan_service = ClanDatabaseService()
        
        # Очередь событий для обработки
        self._event_queue: asyncio.Queue = asyncio.Queue()
        
        # Флаг работы обработчика
        self._processing = False
        
        # Обработчики событий по типам
        self._event_handlers: Dict[str, Callable] = {
            'message_sent': self._handle_message_sent,
            'passport_created': self._handle_passport_created,
            'passport_updated': self._handle_passport_updated,
            'player_bound': self._handle_player_bound,
            'player_verified': self._handle_player_verified,
            'clan_joined': self._handle_clan_joined,
            'clan_left': self._handle_clan_left,
            'clan_war_started': self._handle_clan_war_started,
            'clan_war_ended': self._handle_clan_war_ended,
            'player_stats_updated': self._handle_player_stats_updated,
            'user_promoted': self._handle_user_promoted,
            'special_command_used': self._handle_special_command_used,
            'daily_activity': self._handle_daily_activity,
            'weekly_summary': self._handle_weekly_summary
        }
        
        # Кэш для предотвращения дублирования событий
        self._recent_events: Dict[str, datetime] = {}
    
    async def start_processing(self):
        """Запуск обработки событий"""
        
        if self._processing:
            logger.warning("Обработчик событий уже запущен")
            return
        
        self._processing = True
        logger.info("Запуск системы отслеживания достижений")
        
        # Запускаем фоновую задачу обработки
        asyncio.create_task(self._process_events())
        
        # Запускаем периодические задачи
        asyncio.create_task(self._periodic_tasks())
    
    async def stop_processing(self):
        """Остановка обработки событий"""
        
        self._processing = False
        logger.info("Остановка системы отслеживания достижений")
    
    async def track_event(
        self, 
        user_id: int, 
        chat_id: int, 
        event_type: str, 
        event_data: Dict[str, Any]
    ):
        """
        Добавление события в очередь обработки
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            event_type: Тип события
            event_data: Данные события
        """
        
        # Проверяем дублирование событий
        event_key = f"{user_id}_{chat_id}_{event_type}_{hash(json.dumps(event_data, sort_keys=True))}"
        
        if event_key in self._recent_events:
            time_diff = (datetime.now() - self._recent_events[event_key]).total_seconds()
            if time_diff < 1:  # Игнорируем события чаще раза в секунду
                return
        
        self._recent_events[event_key] = datetime.now()
        
        # Добавляем в очередь
        await self._event_queue.put({
            'user_id': user_id,
            'chat_id': chat_id,
            'event_type': event_type,
            'event_data': event_data,
            'timestamp': datetime.now()
        })
        
        logger.debug(f"Событие добавлено в очередь: {event_type} для пользователя {user_id}")
    
    async def _process_events(self):
        """Основной цикл обработки событий"""
        
        while self._processing:
            try:
                # Ждем события из очереди (с таймаутом)
                try:
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Обрабатываем событие
                await self._handle_event(event)
                
                # Отмечаем задачу как выполненную
                self._event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Ошибка обработки события: {e}")
                await asyncio.sleep(1)
    
    async def _handle_event(self, event: Dict[str, Any]):
        """Обработка отдельного события"""
        
        try:
            event_type = event['event_type']
            user_id = event['user_id']
            chat_id = event['chat_id']
            event_data = event['event_data']
            
            logger.debug(f"Обработка события {event_type} для пользователя {user_id}")
            
            # Проверяем наличие обработчика
            if event_type in self._event_handlers:
                # Вызываем специфичный обработчик
                await self._event_handlers[event_type](user_id, chat_id, event_data)
            
            # Всегда обновляем прогресс достижений
            completed_achievements = await self.achievement_service.update_user_progress(
                user_id, chat_id, event_type, event_data
            )
            
            # Если есть завершенные достижения, уведомляем пользователя
            if completed_achievements:
                await self._notify_achievements_completed(user_id, chat_id, completed_achievements)
                
        except Exception as e:
            logger.error(f"Ошибка обработки события {event.get('event_type', 'unknown')}: {e}")
    
    # Обработчики специфичных событий
    
    async def _handle_message_sent(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка отправленного сообщения"""
        
        # Увеличиваем счетчик сообщений
        event_data['messages_count'] = event_data.get('messages_count', 1)
        
        # Обновляем статистику в паспорте
        try:
            passport = await self.passport_service.get_passport_by_user(user_id, chat_id)
            if passport and passport.stats:
                passport.stats.messages_count += 1
                passport.stats.last_active_date = datetime.now()
                
                await self.passport_service.update_passport_stats(
                    user_id, chat_id, {
                        'messages_count': passport.stats.messages_count,
                        'last_active_date': passport.stats.last_active_date
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка обновления статистики сообщений: {e}")
    
    async def _handle_passport_created(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка создания паспорта"""
        
        event_data['passport_created'] = True
        
        # Проверяем, есть ли у пользователя профиль достижений
        profile = await self.achievement_service.get_user_profile(user_id, chat_id)
        if profile.total_points == 0:
            # Первый раз в системе - добавляем стартовые очки
            profile.add_points(25)
            await self.achievement_service._save_user_profile(profile)
    
    async def _handle_passport_updated(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка обновления паспорта"""
        
        # Можно добавить достижения за активное обновление профиля
        updates_count = event_data.get('updates_count', 1)
        event_data['passport_updates'] = updates_count
    
    async def _handle_player_bound(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка привязки игрока"""
        
        event_data['player_bound'] = True
        
        # Добавляем информацию об игроке для других достижений
        player_tag = event_data.get('player_tag')
        if player_tag:
            # Здесь можно добавить загрузку статистики игрока из CoC API
            # и использовать её для инициализации достижений
            pass
    
    async def _handle_player_verified(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка верификации игрока"""
        
        event_data['player_verified'] = True
        
        # Бонусные очки за верификацию
        profile = await self.achievement_service.get_user_profile(user_id, chat_id)
        profile.add_points(50)
        await self.achievement_service._save_user_profile(profile)
    
    async def _handle_clan_joined(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка вступления в клан"""
        
        event_data['clan_membership'] = True
        
        clan_name = event_data.get('clan_name', 'Unknown')
        logger.info(f"Пользователь {user_id} присоединился к клану {clan_name}")
    
    async def _handle_clan_left(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка выхода из клана"""
        
        event_data['clan_membership'] = False
        
        # Можно добавить достижения за "верность клану" если пользователь был долго
        clan_membership_duration = event_data.get('membership_duration_days', 0)
        if clan_membership_duration >= 30:
            event_data['loyal_member'] = True
    
    async def _handle_clan_war_started(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка начала клановой войны"""
        
        event_data['clan_war_participation'] = True
        
        # Участие в войне добавляет к счетчику
        current_wars = event_data.get('clan_wars_participated', 0)
        event_data['clan_wars_participated'] = current_wars + 1
    
    async def _handle_clan_war_ended(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка окончания клановой войны"""
        
        war_result = event_data.get('war_result')  # 'won', 'lost', 'tie'
        
        if war_result == 'won':
            event_data['clan_wars_won'] = event_data.get('clan_wars_won', 0) + 1
        
        # Статистика атак
        attacks_used = event_data.get('attacks_used', 0)
        stars_earned = event_data.get('stars_earned', 0)
        
        if attacks_used > 0:
            event_data['war_attacks_made'] = event_data.get('war_attacks_made', 0) + attacks_used
            event_data['war_stars_earned'] = event_data.get('war_stars_earned', 0) + stars_earned
    
    async def _handle_player_stats_updated(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка обновления игровой статистики"""
        
        # Обновляем достижения, связанные с игровым прогрессом
        trophies = event_data.get('trophies')
        if trophies:
            event_data['trophies'] = trophies
        
        level = event_data.get('level')
        if level:
            event_data['player_level'] = level
        
        # Проверяем достижения по кубкам
        trophy_milestones = [1000, 2000, 3000, 4000, 5000]
        for milestone in trophy_milestones:
            if trophies and trophies >= milestone:
                event_data[f'trophies_{milestone}'] = True
    
    async def _handle_user_promoted(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка повышения пользователя"""
        
        new_role = event_data.get('new_role')
        
        # Достижения за лидерские роли
        if new_role in ['co-leader', 'leader']:
            event_data['leadership_role'] = True
            
            # Бонусные очки за лидерство
            bonus_points = 100 if new_role == 'leader' else 50
            profile = await self.achievement_service.get_user_profile(user_id, chat_id)
            profile.add_points(bonus_points)
            await self.achievement_service._save_user_profile(profile)
    
    async def _handle_special_command_used(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка использования специальных команд"""
        
        command = event_data.get('command')
        
        # Счетчики использования команд
        commands_used = event_data.get('commands_used', 0)
        event_data['commands_used'] = commands_used + 1
        
        # Достижения за использование специфичных команд
        if command in ['/help', '/smart', '/achievements']:
            event_data['help_seeker'] = True
        elif command in ['/bind_player', '/verify_player']:
            event_data['system_explorer'] = True
    
    async def _handle_daily_activity(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка ежедневной активности"""
        
        # Подсчет дней активности
        active_days = event_data.get('active_days', 0)
        event_data['active_days'] = active_days + 1
        
        # Достижения за последовательную активность
        streak_days = event_data.get('activity_streak', 1)
        if streak_days >= 7:
            event_data['week_streak'] = True
        if streak_days >= 30:
            event_data['month_streak'] = True
    
    async def _handle_weekly_summary(self, user_id: int, chat_id: int, event_data: Dict[str, Any]):
        """Обработка недельной сводки"""
        
        # Агрегированная статистика за неделю
        messages_this_week = event_data.get('messages_this_week', 0)
        
        # Достижения за недельную активность
        if messages_this_week >= 50:
            event_data['weekly_chatter'] = True
        if messages_this_week >= 100:
            event_data['weekly_super_active'] = True
    
    # Вспомогательные методы
    
    async def _notify_achievements_completed(
        self, 
        user_id: int, 
        chat_id: int, 
        achievements: List['Achievement']
    ):
        """Уведомление о завершенных достижениях"""
        
        try:
            # Здесь можно отправить сообщение пользователю о завершенных достижениях
            # Для этого нужен доступ к bot instance
            
            for achievement in achievements:
                logger.info(f"🏆 Пользователь {user_id} завершил достижение: {achievement.name}")
                
                # Можно добавить в очередь уведомлений для отправки через бота
                await self.track_event(user_id, chat_id, 'achievement_completed', {
                    'achievement_id': achievement.achievement_id,
                    'achievement_name': achievement.name
                })
                
        except Exception as e:
            logger.error(f"Ошибка уведомления о достижениях: {e}")
    
    async def _periodic_tasks(self):
        """Периодические задачи для системы достижений"""
        
        while self._processing:
            try:
                # Выполняем задачи каждые 5 минут
                await asyncio.sleep(300)
                
                # Очистка кэша недавних событий (старше 1 минуты)
                current_time = datetime.now()
                expired_keys = [
                    key for key, timestamp in self._recent_events.items()
                    if (current_time - timestamp).total_seconds() > 60
                ]
                
                for key in expired_keys:
                    del self._recent_events[key]
                
                # Ежедневные проверки активности
                await self._check_daily_activities()
                
            except Exception as e:
                logger.error(f"Ошибка в периодических задачах: {e}")
                await asyncio.sleep(60)
    
    async def _check_daily_activities(self):
        """Проверка ежедневной активности пользователей"""
        
        try:
            # Здесь можно реализовать логику проверки активности
            # Например, проверить кто был активен сегодня и начислить достижения
            
            logger.debug("Выполнена проверка ежедневной активности")
            
        except Exception as e:
            logger.error(f"Ошибка проверки ежедневной активности: {e}")
    
    # Публичные методы для интеграции
    
    async def sync_user_stats(self, user_id: int, chat_id: int):
        """Синхронизация статистики пользователя с системой достижений"""
        
        try:
            # Получаем статистику из паспорта
            passport = await self.passport_service.get_passport_by_user(user_id, chat_id)
            
            if passport and passport.stats:
                # Отслеживаем базовые события на основе существующих данных
                await self.track_event(user_id, chat_id, 'message_sent', {
                    'messages_count': passport.stats.messages_count
                })
                
                # Синхронизируем создание паспорта
                await self.track_event(user_id, chat_id, 'passport_created', {
                    'passport_created': True,
                    'creation_date': passport.created_date.isoformat()
                })
            
            # Получаем информацию о привязке игрока
            # Здесь можно добавить синхронизацию с player_binding_service
            
            # Получаем информацию о членстве в клане
            # Здесь можно добавить синхронизацию с clan_service
            
            logger.info(f"Синхронизирована статистика для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации статистики пользователя {user_id}: {e}")
    
    async def trigger_manual_check(self, user_id: int, chat_id: int, check_type: str = "all"):
        """Принудительная проверка достижений пользователя"""
        
        try:
            if check_type == "all" or check_type == "social":
                # Проверяем социальные достижения
                await self.sync_user_stats(user_id, chat_id)
            
            if check_type == "all" or check_type == "game":
                # Проверяем игровые достижения
                await self.track_event(user_id, chat_id, 'manual_game_check', {
                    'check_timestamp': datetime.now().isoformat()
                })
            
            if check_type == "all" or check_type == "clan":
                # Проверяем клановые достижения
                await self.track_event(user_id, chat_id, 'manual_clan_check', {
                    'check_timestamp': datetime.now().isoformat()
                })
            
            logger.info(f"Выполнена принудительная проверка {check_type} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка принудительной проверки достижений: {e}")


# Создаем глобальный экземпляр трекера
achievement_tracker = AchievementEventTracker()


# Функции-хелперы для интеграции с другими системами

async def track_message_sent(user_id: int, chat_id: int, message_length: int = 0):
    """Отслеживание отправленного сообщения"""
    await achievement_tracker.track_event(user_id, chat_id, 'message_sent', {
        'messages_count': 1,
        'message_length': message_length,
        'timestamp': datetime.now().isoformat()
    })


async def track_passport_created(user_id: int, chat_id: int, passport_data: Dict[str, Any]):
    """Отслеживание создания паспорта"""
    await achievement_tracker.track_event(user_id, chat_id, 'passport_created', {
        'passport_created': True,
        'creation_date': datetime.now().isoformat(),
        **passport_data
    })


async def track_player_bound(user_id: int, chat_id: int, player_tag: str, player_name: str):
    """Отслеживание привязки игрока"""
    await achievement_tracker.track_event(user_id, chat_id, 'player_bound', {
        'player_bound': True,
        'player_tag': player_tag,
        'player_name': player_name,
        'binding_date': datetime.now().isoformat()
    })


async def track_player_verified(user_id: int, chat_id: int, player_tag: str):
    """Отслеживание верификации игрока"""
    await achievement_tracker.track_event(user_id, chat_id, 'player_verified', {
        'player_verified': True,
        'player_tag': player_tag,
        'verification_date': datetime.now().isoformat()
    })


async def track_clan_joined(user_id: int, chat_id: int, clan_tag: str, clan_name: str):
    """Отслеживание вступления в клан"""
    await achievement_tracker.track_event(user_id, chat_id, 'clan_joined', {
        'clan_membership': True,
        'clan_tag': clan_tag,
        'clan_name': clan_name,
        'join_date': datetime.now().isoformat()
    })


async def track_command_used(user_id: int, chat_id: int, command: str):
    """Отслеживание использования команды"""
    await achievement_tracker.track_event(user_id, chat_id, 'special_command_used', {
        'command': command,
        'usage_date': datetime.now().isoformat()
    })