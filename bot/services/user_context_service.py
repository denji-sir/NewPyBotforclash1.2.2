"""
Система определения и анализа контекста пользователя
Фаза 5: Контекстуально-зависимые команды с персонализацией
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..services.passport_database_service import get_passport_db_service
from ..services.clan_database_service import get_clan_db_service
from ..services.coc_api_service import get_coc_api_service
from ..models.passport_models import PassportInfo, PlayerBinding
from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)


class UserContextType(Enum):
    """Типы контекста пользователя"""
    NEW_USER = "new_user"                    # Новый пользователь без паспорта
    UNBOUND_USER = "unbound_user"            # Есть паспорт, но нет привязки игрока
    PENDING_VERIFICATION = "pending_verification"  # Привязка ожидает верификации
    VERIFIED_MEMBER = "verified_member"       # Верифицированный член клана
    CLAN_LEADER = "clan_leader"              # Лидер клана
    CLAN_COLEADER = "clan_coleader"          # Со-лидер клана
    CLAN_ELDER = "clan_elder"                # Старейшина клана
    EXTERNAL_PLAYER = "external_player"      # Игрок не из зарегистрированного клана
    INACTIVE_USER = "inactive_user"          # Неактивный пользователь
    ADMIN_USER = "admin_user"                # Администратор чата


class ActivityLevel(Enum):
    """Уровни активности пользователя"""
    VERY_LOW = "very_low"      # < 10 сообщений за неделю
    LOW = "low"                # 10-50 сообщений за неделю
    MEDIUM = "medium"          # 50-200 сообщений за неделю
    HIGH = "high"              # 200-500 сообщений за неделю
    VERY_HIGH = "very_high"    # > 500 сообщений за неделю


class ExperienceLevel(Enum):
    """Уровни опыта в Clash of Clans"""
    BEGINNER = "beginner"      # < 1000 кубков
    NOVICE = "novice"          # 1000-2000 кубков
    INTERMEDIATE = "intermediate"  # 2000-4000 кубков
    ADVANCED = "advanced"      # 4000-6000 кубков
    EXPERT = "expert"          # 6000+ кубков


@dataclass
class UserContext:
    """Полный контекст пользователя для персонализации"""
    
    # Основная информация
    user_id: int
    chat_id: int
    context_type: UserContextType
    
    # Паспорт и привязка
    has_passport: bool
    passport_info: Optional[PassportInfo] = None
    has_player_binding: bool = False
    player_binding: Optional[PlayerBinding] = None
    
    # Клан и роль
    is_clan_member: bool = False
    clan_info: Optional[Dict] = None
    clan_role: Optional[str] = None
    
    # Активность и опыт
    activity_level: ActivityLevel = ActivityLevel.VERY_LOW
    experience_level: ExperienceLevel = ExperienceLevel.BEGINNER
    
    # Статистика активности
    messages_last_week: int = 0
    commands_used_count: int = 0
    last_active_date: Optional[datetime] = None
    days_since_registration: int = 0
    
    # Игровая статистика (если есть привязка)
    player_trophies: int = 0
    player_level: int = 0
    player_clan_name: Optional[str] = None
    
    # Права и роли
    is_chat_admin: bool = False
    is_verified_player: bool = False
    
    # Персонализация
    preferred_commands: List[str] = None
    interaction_patterns: Dict[str, Any] = None
    
    # Рекомендации
    suggested_actions: List[str] = None
    personalized_tips: List[str] = None


class UserContextService:
    """Сервис для определения и анализа контекста пользователя"""
    
    def __init__(self):
        self.passport_service = get_passport_db_service()
        self.clan_service = get_clan_db_service()
        self.coc_api = get_coc_api_service()
        self.cache = CacheManager()
        
        # Кэш контекстов пользователей
        self._context_cache: Dict[str, UserContext] = {}
        self._cache_ttl = timedelta(minutes=15)  # TTL кэша контекста
    
    async def get_user_context(
        self, 
        user_id: int, 
        chat_id: int,
        refresh_cache: bool = False
    ) -> UserContext:
        """
        Получение полного контекста пользователя
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            refresh_cache: Принудительное обновление кэша
            
        Returns:
            UserContext с полной информацией о пользователе
        """
        try:
            cache_key = f"context_{user_id}_{chat_id}"
            
            # Проверяем кэш
            if not refresh_cache and cache_key in self._context_cache:
                cached_context = self._context_cache[cache_key]
                if datetime.now() - cached_context.last_active_date < self._cache_ttl:
                    return cached_context
            
            # Создаем базовый контекст
            context = UserContext(
                user_id=user_id,
                chat_id=chat_id,
                context_type=UserContextType.NEW_USER
            )
            
            # Получаем паспорт пользователя
            passport = await self.passport_service.get_passport_by_user(user_id, chat_id)
            
            if passport:
                context.has_passport = True
                context.passport_info = passport
                
                # Анализируем привязку игрока
                await self._analyze_player_binding(context, passport)
                
                # Анализируем активность пользователя
                await self._analyze_user_activity(context, passport)
                
                # Определяем роль в клане
                await self._analyze_clan_membership(context, passport)
                
                # Определяем уровень опыта
                await self._analyze_experience_level(context, passport)
            
            # Проверяем административные права
            await self._check_admin_rights(context)
            
            # Определяем тип контекста
            context.context_type = self._determine_context_type(context)
            
            # Генерируем персонализированные рекомендации
            await self._generate_personalized_suggestions(context)
            
            # Кэшируем результат
            context.last_active_date = datetime.now()
            self._context_cache[cache_key] = context
            
            return context
            
        except Exception as e:
            logger.error(f"Ошибка получения контекста пользователя {user_id}: {e}")
            # Возвращаем минимальный контекст при ошибке
            return UserContext(
                user_id=user_id,
                chat_id=chat_id,
                context_type=UserContextType.NEW_USER,
                has_passport=False,
                last_active_date=datetime.now()
            )
    
    async def _analyze_player_binding(self, context: UserContext, passport: PassportInfo):
        """Анализ привязки игрока"""
        if passport.player_binding:
            context.has_player_binding = True
            context.player_binding = passport.player_binding
            context.is_verified_player = passport.player_binding.is_verified
            
            # Игровая статистика
            context.player_trophies = passport.player_binding.player_trophies
            context.player_clan_name = passport.player_binding.player_clan_name
            
            # Получаем актуальную информацию об игроке
            try:
                player_info = await self.coc_api.get_player(passport.player_binding.player_tag)
                if player_info:
                    context.player_level = player_info.get('expLevel', 0)
                    context.player_trophies = player_info.get('trophies', context.player_trophies)
            except Exception as e:
                logger.warning(f"Не удалось получить актуальную информацию об игроке: {e}")
    
    async def _analyze_user_activity(self, context: UserContext, passport: PassportInfo):
        """Анализ активности пользователя"""
        if passport.stats:
            context.messages_last_week = self._calculate_recent_messages(passport.stats)
            context.commands_used_count = passport.stats.commands_count
            context.days_since_registration = (datetime.now() - passport.created_at).days
            
            # Определяем уровень активности
            context.activity_level = self._determine_activity_level(context.messages_last_week)
    
    async def _analyze_clan_membership(self, context: UserContext, passport: PassportInfo):
        """Анализ членства в клане"""
        if passport.preferred_clan_id:
            # Получаем информацию о клане
            clan = await self.clan_service.get_clan_by_id(passport.preferred_clan_id)
            
            if clan:
                context.is_clan_member = True
                context.clan_info = {
                    'clan_id': clan.id,
                    'clan_name': clan.clan_name,
                    'clan_tag': clan.clan_tag,
                    'clan_level': clan.clan_level
                }
                
                # Определяем роль в клане, если есть привязка игрока
                if context.has_player_binding and context.player_binding:
                    context.clan_role = await self._get_player_clan_role(
                        context.player_binding.player_tag,
                        clan.clan_tag
                    )
    
    async def _analyze_experience_level(self, context: UserContext, passport: PassportInfo):
        """Определение уровня опыта в игре"""
        if context.player_trophies > 0:
            if context.player_trophies < 1000:
                context.experience_level = ExperienceLevel.BEGINNER
            elif context.player_trophies < 2000:
                context.experience_level = ExperienceLevel.NOVICE
            elif context.player_trophies < 4000:
                context.experience_level = ExperienceLevel.INTERMEDIATE
            elif context.player_trophies < 6000:
                context.experience_level = ExperienceLevel.ADVANCED
            else:
                context.experience_level = ExperienceLevel.EXPERT
    
    async def _check_admin_rights(self, context: UserContext):
        """Проверка административных прав"""
        try:
            from ..utils.permissions import check_admin_permission
            context.is_chat_admin = await check_admin_permission(
                context.user_id, 
                context.chat_id
            )
        except Exception as e:
            logger.warning(f"Не удалось проверить административные права: {e}")
            context.is_chat_admin = False
    
    def _determine_context_type(self, context: UserContext) -> UserContextType:
        """Определение типа контекста пользователя"""
        
        # Администратор имеет приоритет
        if context.is_chat_admin:
            return UserContextType.ADMIN_USER
        
        # Новый пользователь без паспорта
        if not context.has_passport:
            return UserContextType.NEW_USER
        
        # Пользователь без привязки игрока
        if not context.has_player_binding:
            return UserContextType.UNBOUND_USER
        
        # Неактивный пользователь
        if context.activity_level == ActivityLevel.VERY_LOW and context.days_since_registration > 30:
            return UserContextType.INACTIVE_USER
        
        # Ожидает верификации
        if not context.is_verified_player:
            return UserContextType.PENDING_VERIFICATION
        
        # Игрок не из зарегистрированного клана
        if not context.is_clan_member:
            return UserContextType.EXTERNAL_PLAYER
        
        # Роли в клане
        if context.clan_role == 'leader':
            return UserContextType.CLAN_LEADER
        elif context.clan_role == 'coLeader':
            return UserContextType.CLAN_COLEADER
        elif context.clan_role == 'elder':
            return UserContextType.CLAN_ELDER
        else:
            return UserContextType.VERIFIED_MEMBER
    
    def _determine_activity_level(self, messages_count: int) -> ActivityLevel:
        """Определение уровня активности по количеству сообщений"""
        if messages_count < 10:
            return ActivityLevel.VERY_LOW
        elif messages_count < 50:
            return ActivityLevel.LOW
        elif messages_count < 200:
            return ActivityLevel.MEDIUM
        elif messages_count < 500:
            return ActivityLevel.HIGH
        else:
            return ActivityLevel.VERY_HIGH
    
    def _calculate_recent_messages(self, stats) -> int:
        """Расчет количества сообщений за последнюю неделю"""
        # Простая оценка на основе общей активности
        # В реальной реализации здесь будет анализ временных меток
        total_messages = stats.messages_count
        days_active = max(1, stats.days_active)
        
        # Оценка недельной активности
        daily_average = total_messages / days_active
        weekly_estimate = int(daily_average * 7)
        
        return weekly_estimate
    
    async def _get_player_clan_role(self, player_tag: str, clan_tag: str) -> Optional[str]:
        """Получение роли игрока в клане"""
        try:
            clan_members = await self.coc_api.get_clan_members(clan_tag)
            
            if clan_members:
                for member in clan_members:
                    if member.get('tag') == player_tag:
                        return member.get('role', 'member')
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения роли игрока в клане: {e}")
            return None
    
    async def _generate_personalized_suggestions(self, context: UserContext):
        """Генерация персонализированных предложений и советов"""
        suggestions = []
        tips = []
        
        # Предложения для новых пользователей
        if context.context_type == UserContextType.NEW_USER:
            suggestions.extend([
                "create_passport",
                "view_clans",
                "help_getting_started"
            ])
            tips.extend([
                "💡 Создайте паспорт командой /create_passport",
                "🏰 Посмотрите доступные кланы командой /clan_list", 
                "❓ Получите помощь командой /help"
            ])
        
        # Предложения для пользователей без привязки
        elif context.context_type == UserContextType.UNBOUND_USER:
            suggestions.extend([
                "bind_player",
                "edit_passport",
                "view_binding_help"
            ])
            tips.extend([
                "🎮 Привяжите игрока CoC командой /bind_player",
                "⚙️ Настройте паспорт командой /edit_passport",
                "🏰 Выберите предпочитаемый клан в настройках"
            ])
        
        # Предложения для ожидающих верификации
        elif context.context_type == UserContextType.PENDING_VERIFICATION:
            suggestions.extend([
                "view_verification_status",
                "contact_admin",
                "clan_activities"
            ])
            tips.extend([
                "⏳ Ваша привязка ожидает верификации администратором",
                "📞 Обратитесь к администратору для ускорения процесса",
                "🏰 Участвуйте в активностях клана для быстрой верификации"
            ])
        
        # Предложения для верифицированных членов
        elif context.context_type == UserContextType.VERIFIED_MEMBER:
            suggestions.extend([
                "clan_stats",
                "player_progress",
                "clan_events"
            ])
            
            # Персонализация по уровню активности
            if context.activity_level in [ActivityLevel.LOW, ActivityLevel.VERY_LOW]:
                tips.extend([
                    "💬 Будьте активнее в чате для получения советов",
                    "🏆 Участвуйте в клановых войнах и событиях"
                ])
            else:
                tips.extend([
                    "🌟 Отличная активность! Продолжайте в том же духе",
                    "🏆 Рассмотрите возможность помощи новичкам"
                ])
        
        # Предложения для лидеров кланов
        elif context.context_type in [UserContextType.CLAN_LEADER, UserContextType.CLAN_COLEADER]:
            suggestions.extend([
                "admin_clan_tools",
                "member_management",
                "clan_analytics",
                "recruitment_tools"
            ])
            tips.extend([
                "👑 Используйте административные инструменты клана",
                "📊 Отслеживайте статистику участников",
                "🎯 Планируйте стратегии и события клана"
            ])
        
        # Предложения для старейшин
        elif context.context_type == UserContextType.CLAN_ELDER:
            suggestions.extend([
                "mentor_new_members",
                "clan_coordination",
                "war_strategies"
            ])
            tips.extend([
                "⭐ Помогайте новым участникам клана",
                "🎯 Координируйте клановые активности",
                "⚔️ Делитесь стратегиями войн"
            ])
        
        # Персонализация по опыту в игре
        if context.experience_level == ExperienceLevel.BEGINNER:
            tips.append("🎮 Изучите основы игры и стратегии развития")
        elif context.experience_level == ExperienceLevel.EXPERT:
            tips.append("🏆 Ваш высокий уровень - пример для других!")
        
        context.suggested_actions = suggestions
        context.personalized_tips = tips
    
    async def update_user_interaction(
        self, 
        user_id: int, 
        chat_id: int, 
        command: str, 
        interaction_data: Dict[str, Any]
    ):
        """
        Обновление данных о взаимодействии пользователя
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            command: Использованная команда
            interaction_data: Дополнительные данные о взаимодействии
        """
        try:
            cache_key = f"context_{user_id}_{chat_id}"
            
            # Обновляем кэшированный контекст
            if cache_key in self._context_cache:
                context = self._context_cache[cache_key]
                
                # Обновляем статистику команд
                if not context.preferred_commands:
                    context.preferred_commands = []
                
                if command not in context.preferred_commands:
                    context.preferred_commands.append(command)
                
                # Обновляем паттерны взаимодействия
                if not context.interaction_patterns:
                    context.interaction_patterns = {}
                
                context.interaction_patterns[command] = {
                    'last_used': datetime.now(),
                    'usage_count': context.interaction_patterns.get(command, {}).get('usage_count', 0) + 1,
                    'data': interaction_data
                }
                
                context.last_active_date = datetime.now()
            
            # Обновляем статистику в паспорте
            await self._update_passport_stats(user_id, chat_id, command)
            
        except Exception as e:
            logger.error(f"Ошибка обновления взаимодействия пользователя: {e}")
    
    async def _update_passport_stats(self, user_id: int, chat_id: int, command: str):
        """Обновление статистики в паспорте пользователя"""
        try:
            passport = await self.passport_service.get_passport_by_user(user_id, chat_id)
            
            if passport and passport.stats:
                # Увеличиваем счетчик команд
                passport.stats.commands_count += 1
                passport.stats.last_command_date = datetime.now()
                
                # Обновляем в базе данных
                await self.passport_service.update_passport_stats(
                    user_id=user_id,
                    chat_id=chat_id,
                    stats_update={
                        'commands_count': passport.stats.commands_count,
                        'last_command_date': passport.stats.last_command_date
                    }
                )
                
        except Exception as e:
            logger.error(f"Ошибка обновления статистики паспорта: {e}")
    
    def get_context_summary(self, context: UserContext) -> Dict[str, Any]:
        """
        Получение краткой сводки контекста для отладки
        
        Args:
            context: Контекст пользователя
            
        Returns:
            Словарь с ключевой информацией о контексте
        """
        return {
            'user_id': context.user_id,
            'context_type': context.context_type.value,
            'has_passport': context.has_passport,
            'has_player_binding': context.has_player_binding,
            'is_verified': context.is_verified_player,
            'is_clan_member': context.is_clan_member,
            'clan_role': context.clan_role,
            'activity_level': context.activity_level.value,
            'experience_level': context.experience_level.value,
            'is_admin': context.is_chat_admin,
            'suggestions_count': len(context.suggested_actions) if context.suggested_actions else 0,
            'tips_count': len(context.personalized_tips) if context.personalized_tips else 0
        }