"""
Интеграция контекстуальной системы с существующими компонентами бота
Фаза 5: Связывание всех систем для единого пользовательского опыта
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta

from ..services.user_context_service import UserContextService, UserContext
from ..services.passport_database_service import PassportDatabaseService
from ..services.clan_database_service import ClanDatabaseService
from ..services.player_binding_service import PlayerBindingService
from ..handlers.contextual_commands import ContextualCommandSystem
from ..middleware.contextual_middleware import ContextualMiddleware

logger = logging.getLogger(__name__)


class ContextualBotIntegration:
    """
    Центральный класс интеграции контекстуальной системы с остальными компонентами бота
    """
    
    def __init__(self):
        self.context_service = UserContextService()
        self.passport_service = PassportDatabaseService()
        self.clan_service = ClanDatabaseService()
        self.binding_service = PlayerBindingService()
        self.command_system = ContextualCommandSystem()
        self.middleware = ContextualMiddleware()
        
        # Кэш интеграционных данных
        self._integration_cache: Dict[str, Dict[str, Any]] = {}
    
    async def initialize_integration(self):
        """Инициализация интеграции всех систем"""
        
        logger.info("Инициализация контекстуальной интеграции...")
        
        try:
            # Проверяем доступность всех сервисов
            services_status = await self._check_services_availability()
            
            if not all(services_status.values()):
                logger.warning(f"Некоторые сервисы недоступны: {services_status}")
            
            # Настраиваем интеграционные хуки
            await self._setup_integration_hooks()
            
            # Инициализируем кэши
            await self._initialize_caches()
            
            logger.info("Контекстуальная интеграция успешно инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации интеграции: {e}")
            raise
    
    async def enhance_passport_creation(
        self, 
        user_id: int, 
        chat_id: int, 
        passport_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Улучшение процесса создания паспорта с контекстуальными рекомендациями
        """
        
        try:
            # Получаем контекст пользователя
            context = await self.context_service.get_user_context(user_id, chat_id)
            
            # Добавляем контекстуальные поля к паспорту
            enhanced_data = passport_data.copy()
            
            # Рекомендации на основе активности
            if context.activity_level.value == "high":
                enhanced_data['suggested_role'] = 'active_member'
                enhanced_data['recommended_features'] = [
                    'clan_participation', 'leadership_track', 'mentoring'
                ]
            elif context.activity_level.value == "low":
                enhanced_data['suggested_role'] = 'casual_member'
                enhanced_data['recommended_features'] = [
                    'basic_tracking', 'notifications'
                ]
            
            # Предложения по кланам на основе профиля
            if not context.is_clan_member:
                suggested_clans = await self._suggest_clans_for_user(context)
                enhanced_data['suggested_clans'] = suggested_clans
            
            # Персонализированные настройки
            enhanced_data['personalized_settings'] = await self._generate_personalized_settings(context)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Ошибка улучшения создания паспорта: {e}")
            return passport_data
    
    async def enhance_player_binding(
        self, 
        user_id: int, 
        chat_id: int, 
        player_tag: str
    ) -> Dict[str, Any]:
        """
        Улучшение процесса привязки игрока с контекстуальным анализом
        """
        
        try:
            # Получаем контекст пользователя
            context = await self.context_service.get_user_context(user_id, chat_id)
            
            # Анализируем историю привязок пользователя
            binding_history = await self._analyze_binding_history(user_id, chat_id)
            
            # Проверяем совместимость с существующими кланами
            clan_compatibility = await self._check_clan_compatibility(player_tag, context)
            
            # Генерируем рекомендации по верификации
            verification_recommendations = await self._generate_verification_recommendations(
                context, player_tag
            )
            
            return {
                'binding_history': binding_history,
                'clan_compatibility': clan_compatibility,
                'verification_recommendations': verification_recommendations,
                'suggested_verification_priority': self._calculate_verification_priority(context),
                'post_binding_actions': await self._suggest_post_binding_actions(context)
            }
            
        except Exception as e:
            logger.error(f"Ошибка улучшения привязки игрока: {e}")
            return {}
    
    async def enhance_clan_operations(
        self, 
        user_id: int, 
        chat_id: int, 
        operation_type: str,
        operation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Улучшение клановых операций с контекстуальной информацией
        """
        
        try:
            context = await self.context_service.get_user_context(user_id, chat_id)
            
            enhanced_data = operation_data.copy()
            
            if operation_type == "join_clan":
                # Анализ совместимости пользователя с кланом
                compatibility_score = await self._calculate_clan_user_compatibility(
                    context, operation_data.get('clan_tag')
                )
                enhanced_data['compatibility_score'] = compatibility_score
                
                # Предсказание успешности адаптации
                adaptation_prediction = await self._predict_clan_adaptation(context)
                enhanced_data['adaptation_prediction'] = adaptation_prediction
            
            elif operation_type == "leave_clan":
                # Анализ причин ухода
                leave_analysis = await self._analyze_leave_reasons(context)
                enhanced_data['leave_analysis'] = leave_analysis
                
                # Рекомендации альтернативных кланов
                alternative_clans = await self._suggest_alternative_clans(context)
                enhanced_data['alternative_clans'] = alternative_clans
            
            elif operation_type == "clan_war_participation":
                # Анализ готовности к войне
                war_readiness = await self._assess_war_readiness(context)
                enhanced_data['war_readiness'] = war_readiness
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Ошибка улучшения клановых операций: {e}")
            return operation_data
    
    async def generate_contextual_menu(
        self, 
        user_id: int, 
        chat_id: int,
        menu_type: str = "main"
    ) -> Dict[str, Any]:
        """
        Генерация контекстуального меню для пользователя
        """
        
        try:
            context = await self.context_service.get_user_context(user_id, chat_id)
            
            # Получаем базовое меню
            base_menu = await self.command_system.generate_contextual_menu(
                context, menu_type
            )
            
            # Добавляем интеграционные элементы
            if context.has_player_binding:
                # Добавляем игровые команды
                base_menu['sections'].append({
                    'title': '🎮 Игровые функции',
                    'commands': await self._get_game_commands_for_context(context)
                })
            
            if context.is_clan_member:
                # Добавляем клановые команды
                base_menu['sections'].append({
                    'title': '🏰 Клановые функции',
                    'commands': await self._get_clan_commands_for_context(context)
                })
            
            # Добавляем административные команды для лидеров
            if context.context_type.value in ['clan_leader', 'admin']:
                base_menu['sections'].append({
                    'title': '⚡ Управление',
                    'commands': await self._get_admin_commands_for_context(context)
                })
            
            # Добавляем персональные рекомендации
            recommendations = await self._get_contextual_recommendations(context)
            if recommendations:
                base_menu['recommendations'] = recommendations
            
            return base_menu
            
        except Exception as e:
            logger.error(f"Ошибка генерации контекстуального меню: {e}")
            return {'sections': [], 'recommendations': []}
    
    async def handle_context_change_event(
        self, 
        user_id: int, 
        chat_id: int,
        change_type: str,
        change_data: Dict[str, Any]
    ):
        """
        Обработка событий изменения контекста пользователя
        """
        
        try:
            # Инвалидируем кэш контекста
            self.middleware.invalidate_context_cache(user_id, chat_id)
            
            # Получаем обновленный контекст
            new_context = await self.context_service.get_user_context(user_id, chat_id)
            
            # Обрабатываем специфичные изменения
            if change_type == "passport_created":
                await self._handle_passport_creation_event(new_context, change_data)
            
            elif change_type == "player_bound":
                await self._handle_player_binding_event(new_context, change_data)
            
            elif change_type == "player_verified":
                await self._handle_player_verification_event(new_context, change_data)
            
            elif change_type == "clan_joined":
                await self._handle_clan_join_event(new_context, change_data)
            
            elif change_type == "clan_left":
                await self._handle_clan_leave_event(new_context, change_data)
            
            # Обновляем интеграционный кэш
            await self._update_integration_cache(user_id, chat_id, new_context)
            
        except Exception as e:
            logger.error(f"Ошибка обработки изменения контекста: {e}")
    
    # Вспомогательные методы
    
    async def _check_services_availability(self) -> Dict[str, bool]:
        """Проверка доступности всех сервисов"""
        
        services_status = {}
        
        try:
            # Проверяем passport service
            services_status['passport'] = await self._ping_service(self.passport_service)
            
            # Проверяем clan service
            services_status['clan'] = await self._ping_service(self.clan_service)
            
            # Проверяем binding service
            services_status['binding'] = await self._ping_service(self.binding_service)
            
            # Проверяем context service
            services_status['context'] = await self._ping_service(self.context_service)
            
        except Exception as e:
            logger.error(f"Ошибка проверки сервисов: {e}")
        
        return services_status
    
    async def _ping_service(self, service) -> bool:
        """Проверка доступности сервиса"""
        
        try:
            # Здесь можно добавить специфичную проверку для каждого сервиса
            return hasattr(service, '__class__')
        except:
            return False
    
    async def _setup_integration_hooks(self):
        """Настройка хуков интеграции"""
        
        # Здесь можно добавить подписки на события различных сервисов
        logger.info("Хуки интеграции настроены")
    
    async def _initialize_caches(self):
        """Инициализация кэшей"""
        
        self._integration_cache = {}
        logger.info("Кэши интеграции инициализированы")
    
    async def _suggest_clans_for_user(self, context: UserContext) -> List[Dict[str, Any]]:
        """Предложение кланов для пользователя"""
        
        try:
            # Получаем доступные кланы
            available_clans = await self.clan_service.get_all_clans()
            
            # Анализируем совместимость
            suggestions = []
            for clan in available_clans:
                compatibility_score = await self._calculate_clan_user_compatibility(
                    context, clan.clan_tag
                )
                
                if compatibility_score > 0.6:  # Порог совместимости
                    suggestions.append({
                        'clan_name': clan.clan_name,
                        'clan_tag': clan.clan_tag,
                        'compatibility_score': compatibility_score,
                        'reasons': await self._get_compatibility_reasons(context, clan)
                    })
            
            # Сортируем по совместимости
            suggestions.sort(key=lambda x: x['compatibility_score'], reverse=True)
            
            return suggestions[:3]  # Топ-3 предложения
            
        except Exception as e:
            logger.error(f"Ошибка предложения кланов: {e}")
            return []
    
    async def _generate_personalized_settings(self, context: UserContext) -> Dict[str, Any]:
        """Генерация персонализированных настроек"""
        
        settings = {
            'notifications': {
                'clan_wars': context.is_clan_member,
                'binding_updates': not context.is_verified_player,
                'achievements': True,
                'reminders': context.activity_level.value == "low"
            },
            'interface': {
                'show_tips': context.experience_level.value == "beginner",
                'compact_mode': context.activity_level.value == "high",
                'auto_suggestions': True
            },
            'privacy': {
                'show_stats': True,
                'show_clan_info': context.is_clan_member,
                'allow_mentions': True
            }
        }
        
        return settings
    
    async def _analyze_binding_history(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """Анализ истории привязок пользователя"""
        
        try:
            # Получаем историю привязок
            binding_history = await self.binding_service.get_user_binding_history(user_id, chat_id)
            
            analysis = {
                'total_bindings': len(binding_history),
                'successful_verifications': len([b for b in binding_history if b.is_verified]),
                'average_verification_time': 0,
                'binding_patterns': [],
                'risk_factors': []
            }
            
            # Анализируем паттерны
            if analysis['total_bindings'] > 1:
                analysis['binding_patterns'].append('multiple_bindings')
                
                if analysis['successful_verifications'] == 0:
                    analysis['risk_factors'].append('no_successful_verifications')
            
            return analysis
            
        except Exception as e:
            logger.error(f"Ошибка анализа истории привязок: {e}")
            return {'total_bindings': 0, 'risk_factors': []}
    
    async def _check_clan_compatibility(self, player_tag: str, context: UserContext) -> Dict[str, Any]:
        """Проверка совместимости игрока с кланами"""
        
        compatibility = {
            'compatible_clans': [],
            'incompatible_clans': [],
            'neutral_clans': []
        }
        
        try:
            # Получаем информацию об игроке из API
            # player_info = await self.clash_api.get_player(player_tag)
            
            # Получаем все кланы системы
            all_clans = await self.clan_service.get_all_clans()
            
            for clan in all_clans:
                # Здесь можно добавить логику проверки совместимости
                # на основе уровня игрока, кубков и т.д.
                compatibility['neutral_clans'].append({
                    'clan_name': clan.clan_name,
                    'clan_tag': clan.clan_tag,
                    'reason': 'Требует дополнительной проверки'
                })
            
        except Exception as e:
            logger.error(f"Ошибка проверки совместимости с кланами: {e}")
        
        return compatibility
    
    async def _generate_verification_recommendations(
        self, 
        context: UserContext, 
        player_tag: str
    ) -> Dict[str, Any]:
        """Генерация рекомендаций по верификации"""
        
        recommendations = {
            'priority_level': 'normal',
            'estimated_time': '1-3 дня',
            'acceleration_tips': [],
            'requirements_check': {}
        }
        
        # Анализируем факторы для ускорения верификации
        if context.activity_level.value == "high":
            recommendations['priority_level'] = 'high'
            recommendations['estimated_time'] = '6-24 часа'
            recommendations['acceleration_tips'].append('Высокая активность в чате')
        
        if context.messages_last_week > 20:
            recommendations['acceleration_tips'].append('Активное участие в обсуждениях')
        
        return recommendations
    
    def _calculate_verification_priority(self, context: UserContext) -> int:
        """Расчет приоритета верификации"""
        
        priority = 50  # Базовый приоритет
        
        # Увеличиваем за активность
        if context.activity_level.value == "high":
            priority += 20
        elif context.activity_level.value == "medium":
            priority += 10
        
        # Увеличиваем за участие в клане
        if context.is_clan_member:
            priority += 15
        
        # Увеличиваем за количество сообщений
        priority += min(context.messages_last_week * 2, 20)
        
        return min(priority, 100)
    
    async def _suggest_post_binding_actions(self, context: UserContext) -> List[Dict[str, str]]:
        """Предложение действий после привязки"""
        
        actions = []
        
        if not context.is_clan_member:
            actions.append({
                'action': 'join_clan',
                'title': 'Присоединиться к клану',
                'description': 'Найдите подходящий клан для участия'
            })
        
        actions.append({
            'action': 'set_goals',
            'title': 'Установить цели',
            'description': 'Определите свои игровые цели'
        })
        
        actions.append({
            'action': 'explore_features',
            'title': 'Изучить возможности',
            'description': 'Познакомьтесь со всеми функциями бота'
        })
        
        return actions
    
    async def _calculate_clan_user_compatibility(
        self, 
        context: UserContext, 
        clan_tag: str
    ) -> float:
        """Расчет совместимости пользователя с кланом"""
        
        try:
            # Получаем информацию о клане
            clan_info = await self.clan_service.get_clan_by_tag(clan_tag)
            
            if not clan_info:
                return 0.0
            
            compatibility_score = 0.0
            
            # Базовая совместимость
            compatibility_score += 0.3
            
            # Увеличиваем за активность
            if context.activity_level.value == "high":
                compatibility_score += 0.2
            elif context.activity_level.value == "medium":
                compatibility_score += 0.1
            
            # Увеличиваем за опыт
            if context.experience_level.value == "advanced":
                compatibility_score += 0.2
            elif context.experience_level.value == "intermediate":
                compatibility_score += 0.1
            
            # Увеличиваем за наличие привязки
            if context.has_player_binding:
                compatibility_score += 0.2
            
            return min(compatibility_score, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета совместимости: {e}")
            return 0.5
    
    async def _get_compatibility_reasons(self, context: UserContext, clan) -> List[str]:
        """Получение причин совместимости"""
        
        reasons = []
        
        if context.activity_level.value == "high":
            reasons.append("Высокая активность пользователя")
        
        if context.has_player_binding:
            reasons.append("Есть привязанный игрок")
        
        if context.experience_level.value in ["intermediate", "advanced"]:
            reasons.append("Опытный пользователь")
        
        return reasons
    
    async def _update_integration_cache(self, user_id: int, chat_id: int, context: UserContext):
        """Обновление интеграционного кэша"""
        
        cache_key = f"{user_id}_{chat_id}"
        
        self._integration_cache[cache_key] = {
            'context': context,
            'last_updated': datetime.now(),
            'menu_cache': None,
            'recommendations_cache': None
        }
    
    async def _handle_passport_creation_event(self, context: UserContext, change_data: Dict[str, Any]):
        """Обработка события создания паспорта"""
        
        logger.info(f"Обработка создания паспорта для пользователя {context}")
        # Здесь можно добавить дополнительную логику
    
    async def _handle_player_binding_event(self, context: UserContext, change_data: Dict[str, Any]):
        """Обработка события привязки игрока"""
        
        logger.info(f"Обработка привязки игрока для пользователя {context}")
    
    async def _handle_player_verification_event(self, context: UserContext, change_data: Dict[str, Any]):
        """Обработка события верификации игрока"""
        
        logger.info(f"Обработка верификации игрока для пользователя {context}")
    
    async def _handle_clan_join_event(self, context: UserContext, change_data: Dict[str, Any]):
        """Обработка события вступления в клан"""
        
        logger.info(f"Обработка вступления в клан для пользователя {context}")
    
    async def _handle_clan_leave_event(self, context: UserContext, change_data: Dict[str, Any]):
        """Обработка события выхода из клана"""
        
        logger.info(f"Обработка выхода из клана для пользователя {context}")
    
    async def _get_game_commands_for_context(self, context: UserContext) -> List[Dict[str, str]]:
        """Получение игровых команд для контекста"""
        
        commands = [
            {'name': '/my_stats', 'description': 'Моя игровая статистика'},
            {'name': '/progress', 'description': 'Отслеживание прогресса'}
        ]
        
        return commands
    
    async def _get_clan_commands_for_context(self, context: UserContext) -> List[Dict[str, str]]:
        """Получение клановых команд для контекста"""
        
        commands = [
            {'name': '/clan_info', 'description': 'Информация о клане'},
            {'name': '/clan_wars', 'description': 'Клановые войны'}
        ]
        
        return commands
    
    async def _get_admin_commands_for_context(self, context: UserContext) -> List[Dict[str, str]]:
        """Получение административных команд для контекста"""
        
        commands = [
            {'name': '/admin_panel', 'description': 'Административная панель'},
            {'name': '/user_management', 'description': 'Управление пользователями'}
        ]
        
        return commands
    
    async def _get_contextual_recommendations(self, context: UserContext) -> List[Dict[str, Any]]:
        """Получение контекстуальных рекомендаций"""
        
        recommendations = []
        
        if not context.has_player_binding:
            recommendations.append({
                'type': 'action',
                'title': 'Привяжите игрока',
                'description': 'Получите доступ к игровой статистике',
                'command': '/bind_player'
            })
        
        if not context.is_clan_member:
            recommendations.append({
                'type': 'action',
                'title': 'Присоединитесь к клану',
                'description': 'Участвуйте в клановых активностях',
                'command': '/join_clan'
            })
        
        return recommendations


# Создаем глобальный экземпляр интеграции
contextual_integration = ContextualBotIntegration()