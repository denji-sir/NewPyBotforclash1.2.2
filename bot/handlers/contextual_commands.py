"""
Система персонализированных и контекстуальных команд
Фаза 5: Адаптивные команды на основе контекста пользователя
"""

from typing import Dict, List, Optional, Any, Callable
import logging
from datetime import datetime
from dataclasses import dataclass

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..services.user_context_service import UserContextService, UserContext, UserContextType, ActivityLevel, ExperienceLevel
from ..services.passport_database_service import PassportDatabaseService
from ..services.clan_database_service import ClanDatabaseService
from ..utils.formatting import format_user_greeting, format_contextual_help

router = Router()
logger = logging.getLogger(__name__)


@dataclass
class ContextualCommand:
    """Контекстуальная команда с условиями показа"""
    
    command: str
    title: str
    description: str
    icon: str
    
    # Условия показа
    required_context_types: List[UserContextType] = None
    min_activity_level: ActivityLevel = None
    min_experience_level: ExperienceLevel = None
    requires_admin: bool = False
    requires_clan_membership: bool = False
    requires_player_binding: bool = False
    
    # Персонализация
    priority: int = 0
    category: str = "general"


class ContextualCommandSystem:
    """Система контекстуальных команд"""
    
    def __init__(self):
        self.context_service = UserContextService()
        self.passport_service = PassportDatabaseService()
        self.clan_service = ClanDatabaseService()
        
        # Регистр контекстуальных команд
        self.commands_registry = self._initialize_commands_registry()
    
    def _initialize_commands_registry(self) -> Dict[str, ContextualCommand]:
        """Инициализация реестра контекстуальных команд"""
        
        return {
            # Команды для новых пользователей
            'welcome_setup': ContextualCommand(
                command='welcome_setup',
                title='🎉 Добро пожаловать!',
                description='Настройка аккаунта для новых пользователей',
                icon='🎉',
                required_context_types=[UserContextType.NEW_USER],
                priority=10,
                category='onboarding'
            ),
            
            'create_passport_guided': ContextualCommand(
                command='create_passport_guided',
                title='📋 Создать паспорт',
                description='Пошаговое создание паспорта с подсказками',
                icon='📋',
                required_context_types=[UserContextType.NEW_USER],
                priority=9,
                category='onboarding'
            ),
            
            # Команды для пользователей без привязки
            'binding_assistant': ContextualCommand(
                command='binding_assistant',
                title='🎮 Помощник привязки',
                description='Интерактивный помощник по привязке игрока',
                icon='🎮',
                required_context_types=[UserContextType.UNBOUND_USER],
                priority=8,
                category='binding'
            ),
            
            'quick_clan_join': ContextualCommand(
                command='quick_clan_join',
                title='🏰 Быстрое вступление в клан',
                description='Подбор клана и быстрое вступление',
                icon='🏰',
                required_context_types=[UserContextType.UNBOUND_USER, UserContextType.EXTERNAL_PLAYER],
                priority=7,
                category='clan'
            ),
            
            # Команды для ожидающих верификации
            'verification_status': ContextualCommand(
                command='verification_status',
                title='⏳ Статус верификации',
                description='Проверка статуса верификации и помощь',
                icon='⏳',
                required_context_types=[UserContextType.PENDING_VERIFICATION],
                priority=8,
                category='verification'
            ),
            
            'speed_up_verification': ContextualCommand(
                command='speed_up_verification',
                title='🚀 Ускорить верификацию',
                description='Советы по ускорению процесса верификации',
                icon='🚀',
                required_context_types=[UserContextType.PENDING_VERIFICATION],
                priority=7,
                category='verification'
            ),
            
            # Команды для верифицированных пользователей
            'my_progress': ContextualCommand(
                command='my_progress',
                title='📈 Мой прогресс',
                description='Персональная статистика и достижения',
                icon='📈',
                requires_player_binding=True,
                min_activity_level=ActivityLevel.LOW,
                priority=6,
                category='progress'
            ),
            
            'clan_activities': ContextualCommand(
                command='clan_activities',
                title='🎯 Активности клана',
                description='Текущие события и задачи клана',
                icon='🎯',
                requires_clan_membership=True,
                priority=5,
                category='clan'
            ),
            
            'personalized_tips': ContextualCommand(
                command='personalized_tips',
                title='💡 Персональные советы',
                description='Советы по улучшению игры на основе вашего стиля',
                icon='💡',
                requires_player_binding=True,
                min_experience_level=ExperienceLevel.NOVICE,
                priority=4,
                category='tips'
            ),
            
            # Команды для лидеров и старейшин
            'leadership_tools': ContextualCommand(
                command='leadership_tools',
                title='👑 Инструменты лидера',
                description='Расширенные инструменты управления кланом',
                icon='👑',
                required_context_types=[UserContextType.CLAN_LEADER, UserContextType.CLAN_COLEADER, UserContextType.CLAN_ELDER],
                priority=9,
                category='leadership'
            ),
            
            'member_mentoring': ContextualCommand(
                command='member_mentoring',
                title='🎓 Наставничество',
                description='Инструменты для помощи новым участникам',
                icon='🎓',
                required_context_types=[UserContextType.CLAN_ELDER, UserContextType.CLAN_COLEADER, UserContextType.CLAN_LEADER],
                min_activity_level=ActivityLevel.MEDIUM,
                priority=6,
                category='leadership'
            ),
            
            # Команды для администраторов
            'admin_dashboard': ContextualCommand(
                command='admin_dashboard',
                title='🔧 Админ-панель',
                description='Полная административная панель чата',
                icon='🔧',
                requires_admin=True,
                priority=10,
                category='admin'
            ),
            
            'chat_analytics': ContextualCommand(
                command='chat_analytics',
                title='📊 Аналитика чата',
                description='Детальная статистика и аналитика чата',
                icon='📊',
                requires_admin=True,
                priority=8,
                category='admin'
            ),
            
            # Команды по уровню активности
            'activity_boost': ContextualCommand(
                command='activity_boost',
                title='⚡ Повысить активность',
                description='Советы по увеличению активности в чате и игре',
                icon='⚡',
                min_activity_level=ActivityLevel.VERY_LOW,
                priority=3,
                category='engagement'
            ),
            
            'advanced_strategies': ContextualCommand(
                command='advanced_strategies',
                title='🧠 Продвинутые стратегии',
                description='Сложные тактики и стратегии для опытных игроков',
                icon='🧠',
                min_experience_level=ExperienceLevel.ADVANCED,
                min_activity_level=ActivityLevel.HIGH,
                priority=5,
                category='advanced'
            )
        }
    
    async def get_contextual_commands(self, context: UserContext) -> List[ContextualCommand]:
        """
        Получение контекстуальных команд для пользователя
        
        Args:
            context: Контекст пользователя
            
        Returns:
            Список подходящих команд, отсортированный по приоритету
        """
        available_commands = []
        
        for command_data in self.commands_registry.values():
            if await self._check_command_availability(command_data, context):
                available_commands.append(command_data)
        
        # Сортируем по приоритету (убывание)
        available_commands.sort(key=lambda x: x.priority, reverse=True)
        
        return available_commands
    
    async def _check_command_availability(
        self, 
        command: ContextualCommand, 
        context: UserContext
    ) -> bool:
        """Проверка доступности команды для пользователя"""
        
        # Проверяем тип контекста
        if command.required_context_types:
            if context.context_type not in command.required_context_types:
                return False
        
        # Проверяем административные права
        if command.requires_admin and not context.is_chat_admin:
            return False
        
        # Проверяем членство в клане
        if command.requires_clan_membership and not context.is_clan_member:
            return False
        
        # Проверяем привязку игрока
        if command.requires_player_binding and not context.has_player_binding:
            return False
        
        # Проверяем уровень активности
        if command.min_activity_level:
            activity_levels = [ActivityLevel.VERY_LOW, ActivityLevel.LOW, ActivityLevel.MEDIUM, ActivityLevel.HIGH, ActivityLevel.VERY_HIGH]
            if activity_levels.index(context.activity_level) < activity_levels.index(command.min_activity_level):
                return False
        
        # Проверяем уровень опыта
        if command.min_experience_level:
            experience_levels = [ExperienceLevel.BEGINNER, ExperienceLevel.NOVICE, ExperienceLevel.INTERMEDIATE, ExperienceLevel.ADVANCED, ExperienceLevel.EXPERT]
            if experience_levels.index(context.experience_level) < experience_levels.index(command.min_experience_level):
                return False
        
        return True
    
    def create_contextual_keyboard(
        self, 
        commands: List[ContextualCommand], 
        user_id: int,
        max_commands: int = 8
    ) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры с контекстуальными командами
        
        Args:
            commands: Список команд
            user_id: ID пользователя
            max_commands: Максимальное количество команд на клавиатуре
            
        Returns:
            InlineKeyboardMarkup с контекстуальными командами
        """
        builder = InlineKeyboardBuilder()
        
        # Группируем команды по категориям
        categories = {}
        for command in commands[:max_commands]:
            if command.category not in categories:
                categories[command.category] = []
            categories[command.category].append(command)
        
        # Добавляем команды по категориям
        for category, category_commands in categories.items():
            # Добавляем разделитель категории (если команд много)
            if len(categories) > 1 and len(category_commands) > 1:
                category_names = {
                    'onboarding': '🎯 Начало работы',
                    'binding': '🎮 Привязка игрока',
                    'verification': '✅ Верификация',
                    'clan': '🏰 Клан',
                    'progress': '📈 Прогресс',
                    'leadership': '👑 Лидерство',
                    'admin': '🔧 Администрирование',
                    'tips': '💡 Советы',
                    'advanced': '🧠 Продвинутое',
                    'engagement': '⚡ Активность',
                    'general': '📋 Общее'
                }
                
                category_title = category_names.get(category, f'📋 {category.title()}')
                builder.row(InlineKeyboardButton(
                    text=category_title,
                    callback_data=f"category_info:{category}"
                ))
            
            # Добавляем команды категории
            for command in category_commands:
                builder.row(InlineKeyboardButton(
                    text=f"{command.icon} {command.title}",
                    callback_data=f"contextual_cmd:{user_id}:{command.command}"
                ))
        
        # Добавляем кнопку "Показать все команды"
        if len(commands) > max_commands:
            builder.row(InlineKeyboardButton(
                text=f"📋 Показать все ({len(commands)})",
                callback_data=f"show_all_contextual:{user_id}"
            ))
        
        # Добавляем кнопку обновления
        builder.row(InlineKeyboardButton(
            text="🔄 Обновить рекомендации",
            callback_data=f"refresh_contextual:{user_id}"
        ))
        
        return builder.as_markup()


# Инициализация системы
contextual_system = ContextualCommandSystem()


@router.message(Command("smart"))
async def smart_command_menu(message: Message):
    """
    Интеллектуальное меню команд на основе контекста пользователя
    Usage: /smart
    """
    try:
        # Получаем контекст пользователя
        context = await contextual_system.context_service.get_user_context(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        # Получаем контекстуальные команды
        commands = await contextual_system.get_contextual_commands(context)
        
        # Создаем персонализированное приветствие
        greeting = _format_personalized_greeting(context)
        
        # Создаем клавиатуру
        keyboard = contextual_system.create_contextual_keyboard(
            commands, message.from_user.id
        )
        
        # Формируем текст сообщения
        message_text = (
            f"{greeting}\n\n"
            f"🎯 **Рекомендации на основе вашего профиля:**\n"
        )
        
        # Добавляем персональные советы
        if context.personalized_tips:
            message_text += "\n💡 **Персональные советы:**\n"
            for tip in context.personalized_tips[:3]:  # Показываем первые 3
                message_text += f"• {tip}\n"
            message_text += "\n"
        
        message_text += "Выберите действие:"
        
        await message.reply(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Обновляем статистику взаимодействия
        await contextual_system.context_service.update_user_interaction(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            command="smart",
            interaction_data={'commands_shown': len(commands)}
        )
        
    except Exception as e:
        logger.error(f"Ошибка в smart_command_menu: {e}")
        await message.reply(
            "❌ Произошла ошибка при загрузке персонализированного меню.\n"
            "Попробуйте еще раз через несколько секунд."
        )


@router.callback_query(F.data.startswith("contextual_cmd:"))
async def handle_contextual_command(callback: CallbackQuery):
    """Обработка контекстуальных команд"""
    try:
        _, user_id_str, command = callback.data.split(":", 2)
        user_id = int(user_id_str)
        
        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Получаем контекст пользователя
        context = await contextual_system.context_service.get_user_context(
            user_id=user_id,
            chat_id=callback.message.chat.id
        )
        
        # Выполняем соответствующую команду
        await _execute_contextual_command(callback, command, context)
        
        # Обновляем статистику
        await contextual_system.context_service.update_user_interaction(
            user_id=user_id,
            chat_id=callback.message.chat.id,
            command=command,
            interaction_data={'source': 'contextual_menu'}
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_contextual_command: {e}")
        await callback.answer("❌ Произошла ошибка при выполнении команды", show_alert=True)


@router.message(Command("my_status"))
async def my_status_command(message: Message):
    """
    Персональный статус пользователя с контекстуальной информацией
    Usage: /my_status
    """
    try:
        # Получаем контекст пользователя
        context = await contextual_system.context_service.get_user_context(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        # Форматируем статус
        status_text = _format_user_status(context)
        
        # Создаем клавиатуру с быстрыми действиями
        keyboard = _create_quick_actions_keyboard(context, message.from_user.id)
        
        await message.reply(
            status_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в my_status_command: {e}")
        await message.reply(
            "❌ Не удалось загрузить ваш статус. Попробуйте позже."
        )


@router.message(Command("context_help"))
async def context_help_command(message: Message):
    """
    Контекстуальная помощь на основе ситуации пользователя
    Usage: /context_help
    """
    try:
        # Получаем контекст пользователя
        context = await contextual_system.context_service.get_user_context(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        # Генерируем контекстуальную помощь
        help_text = _generate_contextual_help(context)
        
        # Создаем клавиатуру с полезными ссылками
        keyboard = _create_help_keyboard(context, message.from_user.id)
        
        await message.reply(
            help_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в context_help_command: {e}")
        await message.reply(
            "❌ Не удалось загрузить контекстуальную помощь. Попробуйте /help для общей справки."
        )


# Вспомогательные функции

def _format_personalized_greeting(context: UserContext) -> str:
    """Форматирование персонализированного приветствия"""
    
    greetings = {
        UserContextType.NEW_USER: f"👋 Добро пожаловать! Давайте настроим ваш аккаунт.",
        UserContextType.UNBOUND_USER: f"🎮 Привет! Время привязать игрока CoC к вашему паспорту.",
        UserContextType.PENDING_VERIFICATION: f"⏳ Здравствуйте! Ваша привязка ожидает верификации.",
        UserContextType.VERIFIED_MEMBER: f"✅ Приветствую, {_get_player_name(context)}! Вы верифицированный участник.",
        UserContextType.CLAN_LEADER: f"👑 Здравствуйте, лидер! Управляйте своим кланом эффективно.",
        UserContextType.CLAN_COLEADER: f"🔥 Привет, со-лидер! Помогите развивать клан.",
        UserContextType.CLAN_ELDER: f"⭐ Здравствуйте, старейшина! Направляйте участников клана.",
        UserContextType.EXTERNAL_PLAYER: f"🌍 Приветствую! Рассмотрите вступление в наш клан.",
        UserContextType.INACTIVE_USER: f"😴 Давно не виделись! Что нового в игре?",
        UserContextType.ADMIN_USER: f"🔧 Здравствуйте, администратор! Все системы под контролем."
    }
    
    base_greeting = greetings.get(context.context_type, "👋 Здравствуйте!")
    
    # Добавляем информацию об активности
    if context.activity_level == ActivityLevel.VERY_HIGH:
        base_greeting += " 🌟"
    elif context.activity_level == ActivityLevel.VERY_LOW:
        base_greeting += " 💤"
        
    return base_greeting


def _get_player_name(context: UserContext) -> str:
    """Получение имени игрока из контекста"""
    if context.player_binding:
        return context.player_binding.player_name
    elif context.passport_info:
        return context.passport_info.display_name
    else:
        return "игрок"


async def _execute_contextual_command(callback: CallbackQuery, command: str, context: UserContext):
    """Выполнение контекстуальной команды"""
    
    command_handlers = {
        'welcome_setup': _handle_welcome_setup,
        'create_passport_guided': _handle_create_passport_guided,
        'binding_assistant': _handle_binding_assistant,
        'verification_status': _handle_verification_status,
        'my_progress': _handle_my_progress,
        'clan_activities': _handle_clan_activities,
        'leadership_tools': _handle_leadership_tools,
        'admin_dashboard': _handle_admin_dashboard,
        # ... другие обработчики
    }
    
    handler = command_handlers.get(command)
    if handler:
        await handler(callback, context)
    else:
        await callback.message.edit_text(
            f"🚧 Команда '{command}' находится в разработке.\n"
            f"Скоро она станет доступна!"
        )


async def _handle_welcome_setup(callback: CallbackQuery, context: UserContext):
    """Обработчик приветственной настройки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Создать паспорт", callback_data=f"create_passport:{callback.from_user.id}")],
        [InlineKeyboardButton(text="🏰 Посмотреть кланы", callback_data=f"view_clans:{callback.from_user.id}")],
        [InlineKeyboardButton(text="❓ Получить помощь", callback_data=f"get_help:{callback.from_user.id}")]
    ])
    
    await callback.message.edit_text(
        "🎉 **Добро пожаловать в наш чат!**\n\n"
        "Для начала работы вам нужно:\n"
        "1️⃣ Создать личный паспорт\n"
        "2️⃣ Привязать игрока Clash of Clans\n"
        "3️⃣ Выбрать клан для участия\n\n"
        "С чего хотите начать?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def _handle_verification_status(callback: CallbackQuery, context: UserContext):
    """Обработчик статуса верификации"""
    if context.player_binding:
        binding = context.player_binding
        days_waiting = (datetime.now() - binding.binding_date).days
        
        status_text = (
            f"⏳ **Статус верификации вашей привязки**\n\n"
            f"🎮 **Игрок:** {binding.player_name} ({binding.player_tag})\n"
            f"📅 **Дата привязки:** {binding.binding_date.strftime('%d.%m.%Y')}\n"
            f"⏰ **Ожидание:** {days_waiting} дней\n\n"
        )
        
        if days_waiting < 3:
            status_text += "✅ **Статус:** В обычной очереди верификации"
        elif days_waiting < 7:
            status_text += "⚠️ **Статус:** Ожидание дольше обычного"
        else:
            status_text += "🚨 **Статус:** Длительное ожидание - обратитесь к админу"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Связаться с админом", callback_data=f"contact_admin:{callback.from_user.id}")],
            [InlineKeyboardButton(text="🏰 Активности клана", callback_data=f"clan_activities:{callback.from_user.id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"refresh_contextual:{callback.from_user.id}")]
        ])
        
        await callback.message.edit_text(status_text, reply_markup=keyboard, parse_mode="Markdown")


def _format_user_status(context: UserContext) -> str:
    """Форматирование статуса пользователя"""
    
    # Базовая информация
    status_text = f"👤 **Ваш статус в чате**\n\n"
    
    # Тип контекста
    context_names = {
        UserContextType.NEW_USER: "🆕 Новый пользователь",
        UserContextType.UNBOUND_USER: "📝 Пользователь с паспортом",
        UserContextType.PENDING_VERIFICATION: "⏳ Ожидает верификации",
        UserContextType.VERIFIED_MEMBER: "✅ Верифицированный участник",
        UserContextType.CLAN_LEADER: "👑 Лидер клана",
        UserContextType.CLAN_COLEADER: "🔥 Со-лидер клана",
        UserContextType.CLAN_ELDER: "⭐ Старейшина клана",
        UserContextType.EXTERNAL_PLAYER: "🌍 Внешний игрок",
        UserContextType.INACTIVE_USER: "😴 Неактивный пользователь",
        UserContextType.ADMIN_USER: "🔧 Администратор"
    }
    
    status_text += f"📊 **Роль:** {context_names.get(context.context_type, 'Неопределенная')}\n"
    
    # Информация о паспорте
    if context.has_passport:
        status_text += f"📋 **Паспорт:** Создан ✅\n"
        
        if context.has_player_binding:
            binding = context.player_binding
            verify_status = "✅ Верифицирован" if context.is_verified_player else "⏳ Ожидает верификации"
            status_text += f"🎮 **Привязка:** {binding.player_name} ({verify_status})\n"
            status_text += f"💎 **Кубки:** {context.player_trophies:,}\n"
        else:
            status_text += f"🎮 **Привязка:** Не привязан ❌\n"
    else:
        status_text += f"📋 **Паспорт:** Не создан ❌\n"
    
    # Информация о клане
    if context.is_clan_member and context.clan_info:
        clan_name = context.clan_info['clan_name']
        role = context.clan_role or 'участник'
        status_text += f"🏰 **Клан:** {clan_name} ({role})\n"
    else:
        status_text += f"🏰 **Клан:** Не состоит ❌\n"
    
    # Уровень активности
    activity_names = {
        ActivityLevel.VERY_LOW: "😴 Очень низкая",
        ActivityLevel.LOW: "🙂 Низкая", 
        ActivityLevel.MEDIUM: "😊 Средняя",
        ActivityLevel.HIGH: "🔥 Высокая",
        ActivityLevel.VERY_HIGH: "🌟 Очень высокая"
    }
    status_text += f"📈 **Активность:** {activity_names.get(context.activity_level, 'Неопределенная')}\n"
    
    # Уровень опыта
    experience_names = {
        ExperienceLevel.BEGINNER: "🌱 Новичок",
        ExperienceLevel.NOVICE: "📚 Изучающий",
        ExperienceLevel.INTERMEDIATE: "⚙️ Средний уровень", 
        ExperienceLevel.ADVANCED: "🏆 Продвинутый",
        ExperienceLevel.EXPERT: "🎯 Эксперт"
    }
    status_text += f"🎮 **Уровень в игре:** {experience_names.get(context.experience_level, 'Неопределенный')}\n"
    
    return status_text


def _create_quick_actions_keyboard(context: UserContext, user_id: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры с быстрыми действиями"""
    builder = InlineKeyboardBuilder()
    
    # Действия в зависимости от контекста
    if context.context_type == UserContextType.NEW_USER:
        builder.row(InlineKeyboardButton(text="📋 Создать паспорт", callback_data=f"create_passport:{user_id}"))
    elif context.context_type == UserContextType.UNBOUND_USER:
        builder.row(InlineKeyboardButton(text="🎮 Привязать игрока", callback_data=f"bind_player:{user_id}"))
    elif context.has_player_binding:
        builder.row(InlineKeyboardButton(text="📈 Мой прогресс", callback_data=f"my_progress:{user_id}"))
    
    if context.is_clan_member:
        builder.row(InlineKeyboardButton(text="🏰 Клан", callback_data=f"clan_info:{user_id}"))
    
    builder.row(InlineKeyboardButton(text="🎯 Умное меню", callback_data=f"smart_menu:{user_id}"))
    
    return builder.as_markup()


def _generate_contextual_help(context: UserContext) -> str:
    """Генерация контекстуальной помощи"""
    
    help_text = "❓ **Контекстуальная помощь**\n\n"
    
    # Помощь в зависимости от типа контекста
    if context.context_type == UserContextType.NEW_USER:
        help_text += (
            "🎯 **Начало работы:**\n"
            "• Используйте `/create_passport` для создания паспорта\n"
            "• Изучите доступные кланы командой `/clan_list`\n"
            "• Получите общую помощь командой `/help`\n\n"
        )
    elif context.context_type == UserContextType.UNBOUND_USER:
        help_text += (
            "🎮 **Привязка игрока:**\n"
            "• Используйте `/bind_player` для привязки игрока CoC\n" 
            "• Найдите игрока по тегу или выберите из клана\n"
            "• После привязки дождитесь верификации администратором\n\n"
        )
    elif context.context_type == UserContextType.PENDING_VERIFICATION:
        help_text += (
            "⏳ **Ускорение верификации:**\n"
            "• Будьте активны в чате клана\n"
            "• Убедитесь, что ваш игрок состоит в зарегистрированном клане\n"
            "• При долгом ожидании обратитесь к администратору\n\n"
        )
    elif context.context_type in [UserContextType.VERIFIED_MEMBER, UserContextType.CLAN_ELDER, UserContextType.CLAN_COLEADER, UserContextType.CLAN_LEADER]:
        help_text += (
            "🏆 **Возможности участника:**\n"
            "• Просматривайте статистику клана командой `/clan_stats`\n"
            "• Отслеживайте свой прогресс командой `/my_progress`\n"
            "• Участвуйте в клановых событиях и активностях\n\n"
        )
    
    # Общие советы
    help_text += (
        "💡 **Полезные команды:**\n"
        "• `/smart` - персонализированное меню команд\n"
        "• `/my_status` - ваш текущий статус и информация\n"
        "• `/context_help` - помощь с учетом вашей ситуации\n"
    )
    
    return help_text


def _create_help_keyboard(context: UserContext, user_id: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры помощи"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📋 Общая помощь", callback_data=f"general_help:{user_id}"))
    builder.row(InlineKeyboardButton(text="🎯 Умное меню", callback_data=f"smart_menu:{user_id}"))
    
    if context.is_chat_admin:
        builder.row(InlineKeyboardButton(text="🔧 Помощь админу", callback_data=f"admin_help:{user_id}"))
    
    return builder.as_markup()