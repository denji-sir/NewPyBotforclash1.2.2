"""
Дополнительные контекстуальные команды и обработчики
Фаза 5: Расширенные возможности контекстуального управления
"""

from typing import Dict, List, Optional, Any, Union
import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..services.user_context_service import UserContextService, UserContext, UserContextType, ActivityLevel, ExperienceLevel
from ..services.passport_database_service import PassportDatabaseService
from ..services.clan_database_service import ClanDatabaseService
from ..services.extended_clash_api import ExtendedClashAPI
from ..utils.formatting import create_progress_bar, format_player_info, format_clan_info
from ..handlers.contextual_commands import ContextualCommandSystem

logger = logging.getLogger(__name__)
router = Router()


class ContextualStates(StatesGroup):
    """Состояния для контекстуальных диалогов"""
    waiting_for_goal = State()
    waiting_for_feedback = State()
    waiting_for_custom_action = State()


class AdvancedContextualHandlers:
    """Расширенные обработчики контекстуальных команд"""
    
    def __init__(self):
        self.context_service = UserContextService()
        self.passport_service = PassportDatabaseService()
        self.clan_service = ClanDatabaseService()
        self.clash_api = ExtendedClashAPI([])
        self.command_system = ContextualCommandSystem()
    
    async def handle_personal_dashboard(self, message: Message, context: UserContext):
        """Персональная панель управления"""
        
        dashboard_items = await self._build_personal_dashboard(context)
        
        keyboard = InlineKeyboardBuilder()
        
        for item in dashboard_items:
            keyboard.row(InlineKeyboardButton(
                text=item['title'],
                callback_data=f"dashboard:{item['action']}"
            ))
        
        # Добавляем кнопки настроек и помощи
        keyboard.row(
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="dashboard:settings"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="dashboard:help")
        )
        
        profile_text = await self._generate_dashboard_text(context)
        
        await message.answer(
            f"🎯 **Ваша персональная панель**\n\n{profile_text}",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    
    async def handle_intelligent_recommendations(self, message: Message, context: UserContext):
        """Интеллектуальные рекомендации"""
        
        recommendations = await self._generate_personalized_recommendations(context)
        
        if not recommendations:
            await message.answer(
                "✨ На данный момент у меня нет специальных рекомендаций для вас.\n"
                "Продолжайте активно участвовать в жизни чата!"
            )
            return
        
        keyboard = InlineKeyboardBuilder()
        
        for i, rec in enumerate(recommendations[:5]):  # Максимум 5 рекомендаций
            keyboard.row(InlineKeyboardButton(
                text=f"{rec['icon']} {rec['title']}",
                callback_data=f"recommend:{rec['action']}"
            ))
        
        keyboard.row(InlineKeyboardButton(
            text="🔄 Обновить рекомендации",
            callback_data="recommend:refresh"
        ))
        
        recommendation_text = self._format_recommendations(recommendations)
        
        await message.answer(
            f"💡 **Персональные рекомендации**\n\n{recommendation_text}",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    
    async def handle_progress_tracking(self, message: Message, context: UserContext):
        """Отслеживание прогресса пользователя"""
        
        if not context.has_player_binding:
            await message.answer(
                "🎮 Для отслеживания прогресса необходимо привязать игрока.\n"
                "Используйте команду /bind_player"
            )
            return
        
        progress_data = await self._calculate_user_progress(context)
        progress_text = await self._format_progress_report(progress_data, context)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="📈 Детальная статистика", callback_data="progress:details"),
            InlineKeyboardButton(text="🎯 Установить цель", callback_data="progress:set_goal")
        )
        keyboard.row(
            InlineKeyboardButton(text="🏆 Достижения", callback_data="progress:achievements"),
            InlineKeyboardButton(text="📊 Сравнить с кланом", callback_data="progress:compare")
        )
        
        await message.answer(
            progress_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    
    async def handle_contextual_help(self, message: Message, context: UserContext):
        """Контекстуальная помощь"""
        
        help_sections = await self._generate_contextual_help(context)
        
        keyboard = InlineKeyboardBuilder()
        
        for section in help_sections:
            keyboard.row(InlineKeyboardButton(
                text=f"{section['icon']} {section['title']}",
                callback_data=f"help:{section['key']}"
            ))
        
        keyboard.row(InlineKeyboardButton(
            text="📋 Все команды",
            callback_data="help:all_commands"
        ))
        
        help_intro = self._generate_help_intro(context)
        
        await message.answer(
            f"❓ **Персональная помощь**\n\n{help_intro}",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    
    async def handle_smart_notifications(self, message: Message, context: UserContext):
        """Умные уведомления и напоминания"""
        
        notifications = await self._check_smart_notifications(context)
        
        if not notifications:
            await message.answer(
                "🔔 У вас нет новых уведомлений.\n"
                "Настройте персональные напоминания в настройках!"
            )
            return
        
        keyboard = InlineKeyboardBuilder()
        
        for notification in notifications:
            keyboard.row(InlineKeyboardButton(
                text=f"✅ {notification['action_text']}",
                callback_data=f"notify_action:{notification['action']}"
            ))
        
        keyboard.row(
            InlineKeyboardButton(text="⚙️ Настроить уведомления", callback_data="notifications:settings"),
            InlineKeyboardButton(text="🔕 Отключить все", callback_data="notifications:disable")
        )
        
        notification_text = self._format_notifications(notifications)
        
        await message.answer(
            f"🔔 **Ваши уведомления**\n\n{notification_text}",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    
    # Вспомогательные методы
    
    async def _build_personal_dashboard(self, context: UserContext) -> List[Dict[str, str]]:
        """Построение персональной панели"""
        
        items = []
        
        # Базовые элементы для всех пользователей
        items.append({
            'title': '👤 Мой профиль',
            'action': 'profile',
            'description': 'Просмотр и редактирование профиля'
        })
        
        # Элементы для пользователей с привязкой
        if context.has_player_binding:
            items.append({
                'title': '📊 Моя статистика',
                'action': 'stats',
                'description': 'Игровая статистика и прогресс'
            })
            
            items.append({
                'title': '🎯 Мои цели',
                'action': 'goals',
                'description': 'Персональные цели и достижения'
            })
        
        # Элементы для участников клана
        if context.is_clan_member:
            items.append({
                'title': '🏰 Мой клан',
                'action': 'clan_info',
                'description': 'Информация и статистика клана'
            })
            
            items.append({
                'title': '⚔️ Клановые войны',
                'action': 'clan_wars',
                'description': 'Участие в клановых войнах'
            })
        
        # Элементы для лидеров
        if context.context_type == UserContextType.CLAN_LEADER:
            items.append({
                'title': '👑 Управление кланом',
                'action': 'leadership',
                'description': 'Инструменты лидера клана'
            })
        
        # Элементы для администраторов
        if context.context_type == UserContextType.ADMIN_USER:
            items.append({
                'title': '⚡ Администрирование',
                'action': 'admin_panel',
                'description': 'Административная панель'
            })
        
        return items
    
    async def _generate_dashboard_text(self, context: UserContext) -> str:
        """Генерация текста для панели управления"""
        
        lines = []
        
        # Приветствие
        greeting = self._get_contextual_greeting(context)
        lines.append(greeting)
        
        # Статус пользователя
        status_line = f"**Статус:** {self._get_user_status_text(context)}"
        lines.append(status_line)
        
        # Активность
        if context.activity_level == ActivityLevel.HIGH:
            lines.append("🔥 **Активность:** Очень высокая")
        elif context.activity_level == ActivityLevel.MEDIUM:
            lines.append("📈 **Активность:** Средняя")
        else:
            lines.append("😴 **Активность:** Низкая")
        
        # Прогресс
        if context.has_player_binding and context.is_verified_player:
            lines.append(f"🎮 **Игрок:** {context.player_binding.player_name}")
            if context.is_clan_member:
                lines.append(f"🏰 **Клан:** {context.clan_membership.clan_name}")
        
        return "\n".join(lines)
    
    async def _generate_personalized_recommendations(self, context: UserContext) -> List[Dict[str, str]]:
        """Генерация персонализированных рекомендаций"""
        
        recommendations = []
        
        # Рекомендации для новых пользователей
        if context.context_type == UserContextType.NEW_USER:
            recommendations.extend([
                {
                    'icon': '🎯',
                    'title': 'Создайте паспорт',
                    'description': 'Первый шаг к использованию всех функций бота',
                    'action': 'create_passport',
                    'priority': 10
                },
                {
                    'icon': '📖',
                    'title': 'Изучите возможности',
                    'description': 'Познакомьтесь с функциями бота',
                    'action': 'tutorial',
                    'priority': 8
                }
            ])
        
        # Рекомендации для пользователей без привязки
        elif context.context_type == UserContextType.UNBOUND_USER:
            recommendations.extend([
                {
                    'icon': '🎮',
                    'title': 'Привяжите игрока',
                    'description': 'Получите доступ к игровой статистике',
                    'action': 'bind_player',
                    'priority': 10
                },
                {
                    'icon': '🏰',
                    'title': 'Выберите клан',
                    'description': 'Присоединитесь к одному из наших кланов',
                    'action': 'choose_clan',
                    'priority': 7
                }
            ])
        
        # Рекомендации для активных пользователей
        elif context.activity_level == ActivityLevel.HIGH:
            recommendations.extend([
                {
                    'icon': '🏆',
                    'title': 'Установите новую цель',
                    'description': 'Поставьте амбициозную цель для развития',
                    'action': 'set_goal',
                    'priority': 8
                },
                {
                    'icon': '👑',
                    'title': 'Станьте ментором',
                    'description': 'Помогайте новым участникам',
                    'action': 'become_mentor',
                    'priority': 6
                }
            ])
        
        # Рекомендации для малоактивных пользователей
        elif context.activity_level == ActivityLevel.LOW:
            recommendations.extend([
                {
                    'icon': '💬',
                    'title': 'Участвуйте в обсуждениях',
                    'description': 'Общайтесь с участниками сообщества',
                    'action': 'engage_chat',
                    'priority': 7
                },
                {
                    'icon': '🎯',
                    'title': 'Обновите цели',
                    'description': 'Пересмотрите свои игровые цели',
                    'action': 'update_goals',
                    'priority': 6
                }
            ])
        
        # Сортируем по приоритету
        recommendations.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return recommendations
    
    def _format_recommendations(self, recommendations: List[Dict[str, str]]) -> str:
        """Форматирование рекомендаций для отображения"""
        
        if not recommendations:
            return "Нет доступных рекомендаций."
        
        lines = []
        for i, rec in enumerate(recommendations[:3], 1):  # Показываем только топ-3
            lines.append(f"{i}️⃣ **{rec['title']}**")
            lines.append(f"   {rec['description']}")
            lines.append("")
        
        return "\n".join(lines)
    
    async def _calculate_user_progress(self, context: UserContext) -> Dict[str, Any]:
        """Расчет прогресса пользователя"""
        
        progress = {
            'profile_completion': 0,
            'activity_score': 0,
            'game_progress': 0,
            'clan_contribution': 0,
            'overall_score': 0,
            'level': 'Новичок',
            'next_level': 'Участник',
            'progress_to_next': 0
        }
        
        # Завершенность профиля
        completion_score = 0
        if context.has_passport:
            completion_score += 30
        if context.has_player_binding:
            completion_score += 40
        if context.is_verified_player:
            completion_score += 20
        if context.is_clan_member:
            completion_score += 10
        
        progress['profile_completion'] = min(completion_score, 100)
        
        # Активность
        activity_score = min(context.messages_last_week * 2, 100)
        progress['activity_score'] = activity_score
        
        # Игровой прогресс (если есть привязка)
        if context.player_binding and context.is_verified_player:
            # Здесь можно добавить анализ игровой статистики
            progress['game_progress'] = 75  # Заглушка
        
        # Вклад в клан
        if context.is_clan_member:
            # Анализ участия в клановых активностях
            progress['clan_contribution'] = 60  # Заглушка
        
        # Общий счет
        progress['overall_score'] = int(
            (progress['profile_completion'] * 0.3 +
             progress['activity_score'] * 0.3 +
             progress['game_progress'] * 0.2 +
             progress['clan_contribution'] * 0.2)
        )
        
        # Определение уровня
        if progress['overall_score'] >= 80:
            progress['level'] = 'Эксперт'
            progress['next_level'] = 'Мастер'
        elif progress['overall_score'] >= 60:
            progress['level'] = 'Опытный'
            progress['next_level'] = 'Эксперт'
        elif progress['overall_score'] >= 40:
            progress['level'] = 'Участник'
            progress['next_level'] = 'Опытный'
        else:
            progress['level'] = 'Новичок'
            progress['next_level'] = 'Участник'
        
        return progress
    
    async def _format_progress_report(self, progress: Dict[str, Any], context: UserContext) -> str:
        """Форматирование отчета о прогрессе"""
        
        lines = [
            f"📊 **Отчет о вашем прогрессе**\n",
            f"🎯 **Текущий уровень:** {progress['level']}",
            f"⬆️ **Следующий уровень:** {progress['next_level']}",
            f"📈 **Общий прогресс:** {progress['overall_score']}/100\n"
        ]
        
        # Детализация по категориям
        lines.extend([
            "**Детализация:**",
            f"👤 Профиль: {create_progress_bar(progress['profile_completion'])} {progress['profile_completion']}%",
            f"💬 Активность: {create_progress_bar(progress['activity_score'])} {progress['activity_score']}%"
        ])
        
        if context.has_player_binding:
            lines.append(f"🎮 Игра: {create_progress_bar(progress['game_progress'])} {progress['game_progress']}%")
        
        if context.is_clan_member:
            lines.append(f"🏰 Клан: {create_progress_bar(progress['clan_contribution'])} {progress['clan_contribution']}%")
        
        return "\n".join(lines)
    
    async def _generate_contextual_help(self, context: UserContext) -> List[Dict[str, str]]:
        """Генерация контекстуальной помощи"""
        
        help_sections = []
        
        # Базовая помощь для всех
        help_sections.append({
            'key': 'basics',
            'title': 'Основы работы',
            'icon': '📚',
            'description': 'Основные команды и принципы работы'
        })
        
        # Помощь по профилю
        if not context.has_passport:
            help_sections.append({
                'key': 'passport',
                'title': 'Создание паспорта',
                'icon': '🎯',
                'description': 'Как создать и настроить паспорт'
            })
        
        # Помощь по привязке игрока
        if not context.has_player_binding:
            help_sections.append({
                'key': 'binding',
                'title': 'Привязка игрока',
                'icon': '🎮',
                'description': 'Как привязать аккаунт Clash of Clans'
            })
        
        # Помощь по клану
        if not context.is_clan_member:
            help_sections.append({
                'key': 'clans',
                'title': 'Кланы и участие',
                'icon': '🏰',
                'description': 'Информация о кланах и вступлении'
            })
        
        # Помощь для участников клана
        if context.is_clan_member:
            help_sections.append({
                'key': 'clan_activities',
                'title': 'Клановые активности',
                'icon': '⚔️',
                'description': 'Войны, турниры и события'
            })
        
        # Помощь для лидеров
        if context.context_type == UserContextType.CLAN_LEADER:
            help_sections.append({
                'key': 'leadership',
                'title': 'Управление кланом',
                'icon': '👑',
                'description': 'Инструменты лидера клана'
            })
        
        return help_sections
    
    def _generate_help_intro(self, context: UserContext) -> str:
        """Генерация вступления для помощи"""
        
        if context.context_type == UserContextType.NEW_USER:
            return (
                "Добро пожаловать! Я помогу вам разобраться с возможностями бота. "
                "Выберите интересующую вас тему:"
            )
        elif context.context_type == UserContextType.UNBOUND_USER:
            return (
                "Вы уже создали паспорт - отлично! Теперь изучите дополнительные "
                "возможности бота:"
            )
        else:
            return (
                "Выберите раздел помощи, который вас интересует. Помощь адаптирована "
                "под ваш текущий статус в системе:"
            )
    
    async def _check_smart_notifications(self, context: UserContext) -> List[Dict[str, str]]:
        """Проверка умных уведомлений"""
        
        notifications = []
        
        # Уведомления для новых пользователей
        if context.context_type == UserContextType.NEW_USER:
            days_since_join = (datetime.now() - context.registration_date).days if context.registration_date else 0
            
            if days_since_join >= 1:
                notifications.append({
                    'type': 'reminder',
                    'title': 'Завершите настройку профиля',
                    'message': 'Создайте паспорт чтобы получить доступ ко всем функциям',
                    'action': 'create_passport',
                    'action_text': 'Создать паспорт',
                    'priority': 10
                })
        
        # Уведомления для пользователей без верификации
        elif context.context_type == UserContextType.PENDING_VERIFICATION:
            if context.player_binding:
                days_waiting = (datetime.now() - context.player_binding.binding_date).days
                
                if days_waiting >= 3:
                    notifications.append({
                        'type': 'info',
                        'title': 'Ускорьте верификацию',
                        'message': 'Будьте активнее в чате для ускорения верификации',
                        'action': 'verification_tips',
                        'action_text': 'Узнать как ускорить',
                        'priority': 8
                    })
        
        # Уведомления о неактивности
        if context.activity_level == ActivityLevel.LOW and context.messages_last_week < 5:
            notifications.append({
                'type': 'engagement',
                'title': 'Мы скучаем по вам!',
                'message': 'Посмотрите что нового в ваших кланах',
                'action': 'clan_updates',
                'action_text': 'Посмотреть обновления',
                'priority': 6
            })
        
        return notifications
    
    def _format_notifications(self, notifications: List[Dict[str, str]]) -> str:
        """Форматирование уведомлений"""
        
        if not notifications:
            return "У вас нет новых уведомлений."
        
        lines = []
        for i, notification in enumerate(notifications, 1):
            icon = "🔔" if notification['type'] == 'reminder' else "ℹ️" if notification['type'] == 'info' else "💬"
            lines.append(f"{icon} **{notification['title']}**")
            lines.append(f"   {notification['message']}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_contextual_greeting(self, context: UserContext) -> str:
        """Получение контекстуального приветствия"""
        
        if context.context_type == UserContextType.NEW_USER:
            return "👋 Добро пожаловать в наше сообщество!"
        elif context.context_type == UserContextType.CLAN_LEADER:
            return "👑 Добро пожаловать, лидер!"
        elif context.context_type == UserContextType.ADMIN_USER:
            return "⚡ Добро пожаловать, администратор!"
        elif context.is_clan_member:
            return f"🏰 Добро пожаловать, {context.clan_membership.clan_name}!"
        else:
            return "👤 Добро пожаловать!"
    
    def _get_user_status_text(self, context: UserContext) -> str:
        """Получение текста статуса пользователя"""
        
        if context.context_type == UserContextType.NEW_USER:
            return "Новый пользователь"
        elif context.context_type == UserContextType.UNBOUND_USER:
            return "Пользователь без привязки"
        elif context.context_type == UserContextType.PENDING_VERIFICATION:
            return "Ожидает верификации"
        elif context.context_type == UserContextType.VERIFIED_MEMBER:
            return "Верифицированный участник"
        elif context.context_type == UserContextType.CLAN_LEADER:
            return "Лидер клана"
        elif context.context_type == UserContextType.ADMIN_USER:
            return "Администратор"
        else:
            return "Участник"


# Регистрация команд
@router.message(Command("dashboard"))
async def cmd_personal_dashboard(message: Message, user_context: UserContext):
    """Персональная панель управления"""
    handler = AdvancedContextualHandlers()
    await handler.handle_personal_dashboard(message, user_context)


@router.message(Command("recommendations", "recommend"))
async def cmd_recommendations(message: Message, user_context: UserContext):
    """Интеллектуальные рекомендации"""
    handler = AdvancedContextualHandlers()
    await handler.handle_intelligent_recommendations(message, user_context)


@router.message(Command("progress"))
async def cmd_progress_tracking(message: Message, user_context: UserContext):
    """Отслеживание прогресса"""
    handler = AdvancedContextualHandlers()
    await handler.handle_progress_tracking(message, user_context)


@router.message(Command("context_help", "chelp"))
async def cmd_contextual_help(message: Message, user_context: UserContext):
    """Контекстуальная помощь"""
    handler = AdvancedContextualHandlers()
    await handler.handle_contextual_help(message, user_context)


@router.message(Command("notifications", "notify"))
async def cmd_smart_notifications(message: Message, user_context: UserContext):
    """Умные уведомления"""
    handler = AdvancedContextualHandlers()
    await handler.handle_smart_notifications(message, user_context)


# Callback обработчики для панели управления
@router.callback_query(F.data.startswith("dashboard:"))
async def handle_dashboard_callbacks(callback: CallbackQuery, user_context: UserContext):
    """Обработка колбэков панели управления"""
    
    action = callback.data.split(":", 1)[1]
    
    try:
        if action == "profile":
            # Показать профиль пользователя
            profile_text = format_user_profile(user_context)
            await callback.message.edit_text(
                f"👤 **Ваш профиль**\n\n{profile_text}",
                parse_mode="Markdown"
            )
        
        elif action == "stats" and user_context.has_player_binding:
            # Показать игровую статистику
            await callback.message.edit_text(
                "📊 **Ваша игровая статистика**\n\n"
                "Загружаю данные из Clash of Clans...",
                parse_mode="Markdown"
            )
            # Здесь можно добавить загрузку реальной статистики
        
        elif action == "goals":
            # Показать цели пользователя
            await callback.message.edit_text(
                "🎯 **Ваши цели**\n\n"
                "Функция находится в разработке.",
                parse_mode="Markdown"
            )
        
        elif action == "clan_info" and user_context.is_clan_member:
            # Показать информацию о клане
            clan_text = format_clan_info(user_context.clan_membership)
            await callback.message.edit_text(
                f"🏰 **Информация о клане**\n\n{clan_text}",
                parse_mode="Markdown"
            )
        
        elif action == "settings":
            # Показать настройки
            settings_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:notifications")],
                [InlineKeyboardButton(text="🎨 Интерфейс", callback_data="settings:interface")],
                [InlineKeyboardButton(text="🔐 Приватность", callback_data="settings:privacy")],
                [InlineKeyboardButton(text="← Назад", callback_data="dashboard:main")]
            ])
            
            await callback.message.edit_text(
                "⚙️ **Настройки**\n\n"
                "Выберите категорию настроек:",
                reply_markup=settings_keyboard,
                parse_mode="Markdown"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике панели управления: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")


# Callback обработчики для рекомендаций
@router.callback_query(F.data.startswith("recommend:"))
async def handle_recommendation_callbacks(callback: CallbackQuery, user_context: UserContext):
    """Обработка колбэков рекомендаций"""
    
    action = callback.data.split(":", 1)[1]
    
    try:
        if action == "create_passport":
            await callback.message.edit_text(
                "🎯 **Создание паспорта**\n\n"
                "Используйте команду /create_passport чтобы начать.",
                parse_mode="Markdown"
            )
        
        elif action == "bind_player":
            await callback.message.edit_text(
                "🎮 **Привязка игрока**\n\n"
                "Используйте команду /bind_player чтобы привязать аккаунт.",
                parse_mode="Markdown"
            )
        
        elif action == "refresh":
            # Обновить рекомендации
            handler = AdvancedContextualHandlers()
            await handler.handle_intelligent_recommendations(callback.message, user_context)
            await callback.message.delete()
            return
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике рекомендаций: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")