"""
Команды для работы с системой достижений
Фаза 6: Пользовательский интерфейс для достижений и прогресса
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..services.achievement_service import AchievementService
from ..models.achievement_models import (
    AchievementCategory, AchievementDifficulty, AchievementStatus,
    Achievement, UserAchievementProgress, UserProfile
)
from ..services.user_context_service import UserContext
from ..ui.formatting import create_progress_bar

logger = logging.getLogger(__name__)
router = Router()


class AchievementCommands:
    """Обработчики команд для системы достижений"""
    
    def __init__(self):
        self.achievement_service = AchievementService()
    
    async def handle_achievements_list(self, message: Message, user_context: UserContext):
        """Показать список достижений пользователя"""
        
        try:
            # Получаем сводку достижений пользователя
            summary = await self.achievement_service.get_user_achievements_summary(
                user_context.user_id, user_context.chat_id
            )
            
            if not summary:
                await message.answer("❌ Не удалось загрузить ваши достижения. Попробуйте позже.")
                return
            
            # Формируем текст сводки
            profile = summary['profile']
            level_info = summary['level_progress']
            
            text_lines = [
                "🏆 **Ваши достижения**\n",
                f"👤 **Уровень:** {profile.level} ({level_info['progress_percentage']:.0f}% до {level_info['next_level']})",
                f"⭐ **Опыт:** {level_info['current_exp']}/{level_info['needed_exp']} XP",
                f"🎯 **Очки:** {profile.total_points}",
                f"🏅 **Завершено:** {summary['completed_achievements']}/{summary['total_achievements']} достижений",
                f"💎 **Получено наград:** {summary['claimed_achievements']} раз\n"
            ]
            
            # Добавляем прогресс-бар уровня
            level_progress = create_progress_bar(level_info['progress_percentage'])
            text_lines.append(f"📈 {level_progress} {level_info['progress_percentage']:.0f}%\n")
            
            # Статистика по категориям
            if summary['category_statistics']:
                text_lines.append("📊 **По категориям:**")
                
                category_names = {
                    'social': '💬 Социальные',
                    'game_progress': '🎮 Игровой прогресс',
                    'clan_contribution': '🏰 Вклад в клан',
                    'system_mastery': '⚙️ Освоение системы',
                    'leadership': '👑 Лидерство',
                    'special_events': '🎉 Особые события',
                    'milestones': '🎖️ Вехи'
                }
                
                for category, stats in summary['category_statistics'].items():
                    category_name = category_names.get(category, category)
                    completion_rate = (stats['completed'] / stats['total']) * 100 if stats['total'] > 0 else 0
                    text_lines.append(f"   {category_name}: {stats['completed']}/{stats['total']} ({completion_rate:.0f}%)")
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardBuilder()
            
            # Кнопки по категориям
            keyboard.row(
                InlineKeyboardButton(text="💬 Социальные", callback_data="achievements:category:social"),
                InlineKeyboardButton(text="🎮 Игровые", callback_data="achievements:category:game_progress")
            )
            keyboard.row(
                InlineKeyboardButton(text="🏰 Клановые", callback_data="achievements:category:clan_contribution"),
                InlineKeyboardButton(text="⚙️ Система", callback_data="achievements:category:system_mastery")
            )
            keyboard.row(
                InlineKeyboardButton(text="👑 Лидерство", callback_data="achievements:category:leadership"),
                InlineKeyboardButton(text="🎉 События", callback_data="achievements:category:special_events")
            )
            
            # Дополнительные функции
            keyboard.row(
                InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="achievements:leaderboard"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="achievements:refresh")
            )
            
            await message.answer(
                "\n".join(text_lines),
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа списка достижений: {e}")
            await message.answer("❌ Произошла ошибка при загрузке достижений.")
    
    async def handle_achievements_category(self, callback: CallbackQuery, category: str, user_context: UserContext):
        """Показать достижения определенной категории"""
        
        try:
            # Получаем достижения категории
            category_enum = AchievementCategory(category)
            achievements = await self.achievement_service.get_all_achievements(category_enum)
            
            if not achievements:
                await callback.message.edit_text(
                    f"📋 В категории **{category}** пока нет достижений.",
                    parse_mode="Markdown"
                )
                return
            
            # Получаем прогресс пользователя
            user_progress = await self.achievement_service.get_all_user_progress(
                user_context.user_id, user_context.chat_id
            )
            
            # Формируем список достижений
            text_lines = [f"🏆 **Достижения: {self._get_category_name(category)}**\n"]
            
            # Группируем по сложности
            difficulty_groups = {}
            for achievement in achievements:
                difficulty = achievement.difficulty.value
                if difficulty not in difficulty_groups:
                    difficulty_groups[difficulty] = []
                difficulty_groups[difficulty].append(achievement)
            
            # Отображаем по группам сложности
            difficulty_icons = {
                'bronze': '🥉',
                'silver': '🥈', 
                'gold': '🥇',
                'platinum': '💎',
                'diamond': '💠'
            }
            
            for difficulty in ['bronze', 'silver', 'gold', 'platinum', 'diamond']:
                if difficulty in difficulty_groups:
                    text_lines.append(f"\n{difficulty_icons[difficulty]} **{difficulty.upper()}**")
                    
                    for achievement in difficulty_groups[difficulty]:
                        progress = user_progress.get(achievement.achievement_id)
                        status_icon = self._get_status_icon(progress.status if progress else AchievementStatus.LOCKED)
                        
                        progress_text = ""
                        if progress and progress.status == AchievementStatus.IN_PROGRESS:
                            overall_progress = achievement.get_overall_progress()
                            progress_bar = create_progress_bar(overall_progress)
                            progress_text = f" {progress_bar} {overall_progress:.0f}%"
                        
                        text_lines.append(f"{status_icon} {achievement.icon} **{achievement.name}**{progress_text}")
                        text_lines.append(f"   _{achievement.description}_")
                        
                        # Показываем награды
                        if achievement.rewards:
                            rewards_text = ", ".join([f"{reward.icon} {reward.name}" for reward in achievement.rewards[:2]])
                            if len(achievement.rewards) > 2:
                                rewards_text += f" +{len(achievement.rewards) - 2} еще"
                            text_lines.append(f"   🎁 {rewards_text}")
            
            # Создаем клавиатуру для навигации
            keyboard = InlineKeyboardBuilder()
            
            # Кнопки для других категорий
            categories = [
                ("💬", "social", "Социальные"),
                ("🎮", "game_progress", "Игровые"),  
                ("🏰", "clan_contribution", "Клановые"),
                ("⚙️", "system_mastery", "Система"),
                ("👑", "leadership", "Лидерство"),
                ("🎉", "special_events", "События")
            ]
            
            current_row = []
            for icon, cat_key, name in categories:
                if cat_key != category:  # Не показываем текущую категорию
                    current_row.append(InlineKeyboardButton(
                        text=icon, 
                        callback_data=f"achievements:category:{cat_key}"
                    ))
                    
                    if len(current_row) == 3:
                        keyboard.row(*current_row)
                        current_row = []
            
            if current_row:
                keyboard.row(*current_row)
            
            keyboard.row(
                InlineKeyboardButton(text="← Назад к общему списку", callback_data="achievements:back"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"achievements:category:{category}")
            )
            
            await callback.message.edit_text(
                "\n".join(text_lines),
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа категории достижений {category}: {e}")
            await callback.answer("Произошла ошибка при загрузке категории.")
    
    async def handle_achievement_details(self, callback: CallbackQuery, achievement_id: str, user_context: UserContext):
        """Показать детальную информацию о достижении"""
        
        try:
            achievement = await self.achievement_service.get_achievement(achievement_id)
            progress = await self.achievement_service.get_user_progress(
                user_context.user_id, user_context.chat_id, achievement_id
            )
            
            if not achievement:
                await callback.answer("Достижение не найдено.")
                return
            
            # Формируем детальную информацию
            text_lines = [
                f"{achievement.icon} **{achievement.name}**",
                f"_{achievement.description}_\n"
            ]
            
            # Информация о достижении
            difficulty_names = {
                'bronze': '🥉 Бронза',
                'silver': '🥈 Серебро',
                'gold': '🥇 Золото', 
                'platinum': '💎 Платина',
                'diamond': '💠 Алмаз'
            }
            
            text_lines.extend([
                f"📁 **Категория:** {self._get_category_name(achievement.category.value)}",
                f"⭐ **Сложность:** {difficulty_names.get(achievement.difficulty.value, achievement.difficulty.value)}",
                f"🎯 **Статус:** {self._get_status_name(progress.status if progress else AchievementStatus.LOCKED)}\n"
            ])
            
            # Требования
            if achievement.requirements:
                text_lines.append("📋 **Требования:**")
                for i, requirement in enumerate(achievement.requirements, 1):
                    current_value = progress.current_values.get(requirement.requirement_type, 0) if progress else 0
                    requirement.current_value = current_value
                    
                    req_progress = requirement.get_progress_percentage()
                    progress_bar = create_progress_bar(req_progress)
                    
                    req_text = self._format_requirement_text(requirement)
                    text_lines.append(f"   {i}. {req_text}")
                    text_lines.append(f"      {progress_bar} {req_progress:.0f}% ({current_value}/{requirement.target_value})")
                
                text_lines.append("")
            
            # Предварительные условия
            if achievement.prerequisites:
                text_lines.append("🔒 **Предварительные условия:**")
                for prereq_id in achievement.prerequisites:
                    prereq_achievement = await self.achievement_service.get_achievement(prereq_id)
                    prereq_progress = await self.achievement_service.get_user_progress(
                        user_context.user_id, user_context.chat_id, prereq_id
                    )
                    
                    if prereq_achievement:
                        status_icon = self._get_status_icon(prereq_progress.status if prereq_progress else AchievementStatus.LOCKED)
                        text_lines.append(f"   {status_icon} {prereq_achievement.name}")
                
                text_lines.append("")
            
            # Награды
            if achievement.rewards:
                text_lines.append("🎁 **Награды:**")
                for reward in achievement.rewards:
                    reward_text = f"{reward.icon} **{reward.name}**"
                    if reward.value:
                        reward_text += f" (+{reward.value})"
                    text_lines.append(f"   • {reward_text}")
                    if reward.description:
                        text_lines.append(f"     _{reward.description}_")
            
            # Создаем клавиатуру действий
            keyboard = InlineKeyboardBuilder()
            
            # Если достижение завершено, но награды не получены
            if progress and progress.status == AchievementStatus.COMPLETED:
                keyboard.row(InlineKeyboardButton(
                    text="🎁 Получить награды",
                    callback_data=f"achievements:claim:{achievement_id}"
                ))
            
            # Кнопка возврата
            keyboard.row(InlineKeyboardButton(
                text="← Назад",
                callback_data=f"achievements:category:{achievement.category.value}"
            ))
            
            await callback.message.edit_text(
                "\n".join(text_lines),
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа деталей достижения {achievement_id}: {e}")
            await callback.answer("Произошла ошибка при загрузке информации о достижении.")
    
    async def handle_claim_rewards(self, callback: CallbackQuery, achievement_id: str, user_context: UserContext):
        """Получение наград за достижение"""
        
        try:
            success = await self.achievement_service.claim_achievement_rewards(
                user_context.user_id, user_context.chat_id, achievement_id
            )
            
            if success:
                achievement = await self.achievement_service.get_achievement(achievement_id)
                
                # Формируем сообщение о полученных наградах
                text_lines = [
                    f"🎉 **Поздравляем!**",
                    f"Вы получили награды за достижение **{achievement.name}**!\n",
                    "🎁 **Полученные награды:**"
                ]
                
                for reward in achievement.rewards:
                    reward_text = f"{reward.icon} **{reward.name}**"
                    if reward.value:
                        reward_text += f" (+{reward.value})"
                    text_lines.append(f"   • {reward_text}")
                
                # Получаем обновленный профиль
                profile = await self.achievement_service.get_user_profile(
                    user_context.user_id, user_context.chat_id
                )
                
                text_lines.extend([
                    "",
                    f"📊 **Ваш прогресс:**",
                    f"⭐ Уровень: {profile.level}",
                    f"🎯 Очки: {profile.total_points}",
                    f"🏅 Завершенных достижений: {profile.achievements_completed}",
                    f"💎 Полученных наград: {profile.achievements_claimed}"
                ])
                
                keyboard = InlineKeyboardBuilder()
                keyboard.row(InlineKeyboardButton(
                    text="🏆 К списку достижений",
                    callback_data="achievements:back"
                ))
                
                await callback.message.edit_text(
                    "\n".join(text_lines),
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
                
            else:
                await callback.answer("❌ Не удалось получить награды. Проверьте статус достижения.")
                
        except Exception as e:
            logger.error(f"Ошибка получения наград за достижение {achievement_id}: {e}")
            await callback.answer("Произошла ошибка при получении наград.")
    
    async def handle_leaderboard(self, callback: CallbackQuery, category: str = "total_points"):
        """Показать таблицу лидеров"""
        
        try:
            leaderboard = await self.achievement_service.get_leaderboard(category, limit=10)
            
            if not leaderboard:
                await callback.message.edit_text("📊 Таблица лидеров пока пуста.")
                return
            
            # Заголовки категорий
            category_titles = {
                'total_points': '🎯 Лидеры по очкам',
                'level': '⭐ Лидеры по уровню',
                'achievements': '🏅 Лидеры по достижениям'
            }
            
            text_lines = [
                category_titles.get(category, f'🏆 Лидеры: {category}'),
                ""
            ]
            
            # Иконки для топ-3
            rank_icons = {1: '🥇', 2: '🥈', 3: '🥉'}
            
            for entry in leaderboard:
                rank_icon = rank_icons.get(entry.rank, f"{entry.rank}.")
                
                if category == 'total_points':
                    score_text = f"{entry.score:.0f} очков"
                elif category == 'level':
                    score_text = f"{entry.score:.0f} уровень"
                elif category == 'achievements':
                    score_text = f"{entry.score:.0f} достижений"
                else:
                    score_text = f"{entry.score:.0f}"
                
                # Дополнительная информация
                additional = []
                if 'level' in entry.additional_info and category != 'level':
                    additional.append(f"ур.{entry.additional_info['level']}")
                if 'achievements_completed' in entry.additional_info and category != 'achievements':
                    additional.append(f"{entry.additional_info['achievements_completed']}🏅")
                
                additional_text = f" ({', '.join(additional)})" if additional else ""
                
                text_lines.append(f"{rank_icon} **{entry.display_name}** - {score_text}{additional_text}")
            
            # Создаем клавиатуру переключения категорий
            keyboard = InlineKeyboardBuilder()
            
            categories = [
                ('🎯', 'total_points', 'Очки'),
                ('⭐', 'level', 'Уровень'),
                ('🏅', 'achievements', 'Достижения')
            ]
            
            category_buttons = []
            for icon, cat_key, name in categories:
                if cat_key != category:
                    category_buttons.append(InlineKeyboardButton(
                        text=f"{icon} {name}",
                        callback_data=f"achievements:leaderboard:{cat_key}"
                    ))
            
            if len(category_buttons) == 2:
                keyboard.row(*category_buttons)
            elif len(category_buttons) == 1:
                keyboard.row(category_buttons[0])
            
            keyboard.row(
                InlineKeyboardButton(text="← Назад", callback_data="achievements:back"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"achievements:leaderboard:{category}")
            )
            
            await callback.message.edit_text(
                "\n".join(text_lines),
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа таблицы лидеров: {e}")
            await callback.answer("Произошла ошибка при загрузке таблицы лидеров.")
    
    # Вспомогательные методы
    
    def _get_category_name(self, category: str) -> str:
        """Получение читаемого названия категории"""
        
        names = {
            'social': '💬 Социальные',
            'game_progress': '🎮 Игровой прогресс',
            'clan_contribution': '🏰 Вклад в клан',
            'system_mastery': '⚙️ Освоение системы',
            'leadership': '👑 Лидерство',
            'special_events': '🎉 Особые события',
            'milestones': '🎖️ Вехи'
        }
        
        return names.get(category, category)
    
    def _get_status_icon(self, status: AchievementStatus) -> str:
        """Получение иконки статуса"""
        
        icons = {
            AchievementStatus.LOCKED: '🔒',
            AchievementStatus.AVAILABLE: '🔓',
            AchievementStatus.IN_PROGRESS: '⏳',
            AchievementStatus.COMPLETED: '✅',
            AchievementStatus.CLAIMED: '💎'
        }
        
        return icons.get(status, '❓')
    
    def _get_status_name(self, status: AchievementStatus) -> str:
        """Получение названия статуса"""
        
        names = {
            AchievementStatus.LOCKED: '🔒 Заблокировано',
            AchievementStatus.AVAILABLE: '🔓 Доступно',
            AchievementStatus.IN_PROGRESS: '⏳ В процессе',
            AchievementStatus.COMPLETED: '✅ Завершено',
            AchievementStatus.CLAIMED: '💎 Награды получены'
        }
        
        return names.get(status, '❓ Неизвестно')
    
    def _format_requirement_text(self, requirement: AchievementRequirement) -> str:
        """Форматирование текста требования"""
        
        requirement_texts = {
            'messages_count': 'Отправить сообщений',
            'passport_created': 'Создать паспорт',
            'player_bound': 'Привязать игрока',
            'clan_membership': 'Вступить в клан',
            'player_verified': 'Пройти верификацию',
            'trophies': 'Набрать кубков',
            'clan_wars_participated': 'Участвовать в войнах клана',
            'donations_made': 'Сделать донаций'
        }
        
        base_text = requirement_texts.get(requirement.requirement_type, requirement.requirement_type)
        
        if requirement.comparison == "gte":
            return f"{base_text}: {requirement.target_value}+"
        elif requirement.comparison == "eq" and isinstance(requirement.target_value, bool):
            return base_text
        else:
            return f"{base_text}: {requirement.target_value}"


# Регистрация команд
@router.message(Command("achievements", "достижения"))
async def cmd_achievements(message: Message, user_context: UserContext):
    """Команда просмотра достижений"""
    handler = AchievementCommands()
    await handler.handle_achievements_list(message, user_context)


@router.message(Command("my_progress", "прогресс"))
async def cmd_my_progress(message: Message, user_context: UserContext):
    """Команда просмотра личного прогресса"""
    handler = AchievementCommands()
    
    try:
        achievement_service = AchievementService()
        profile = await achievement_service.get_user_profile(user_context.user_id, user_context.chat_id)
        level_info = profile.get_progress_to_next_level()
        
        text_lines = [
            "📊 **Ваш прогресс**\n",
            f"👤 **Уровень:** {profile.level}",
            f"⭐ **Опыт:** {profile.experience_points} XP",
            f"📈 **До следующего уровня:** {level_info['needed_exp'] - level_info['current_exp']} XP",
            f"🎯 **Всего очков:** {profile.total_points}\n"
        ]
        
        # Прогресс-бар
        progress_bar = create_progress_bar(level_info['progress_percentage'])
        text_lines.append(f"📈 {progress_bar} {level_info['progress_percentage']:.0f}%\n")
        
        # Титулы и значки
        if profile.titles:
            text_lines.append(f"🏷️ **Титулы:** {', '.join(list(profile.titles)[:5])}")
        
        if profile.badges:
            text_lines.append(f"🎖️ **Значки:** {len(profile.badges)} получено")
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🏆 Все достижения", callback_data="achievements:back"),
            InlineKeyboardButton(text="🏁 Таблица лидеров", callback_data="achievements:leaderboard:total_points")
        )
        
        await message.answer(
            "\n".join(text_lines),
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка команды прогресса: {e}")
        await message.answer("❌ Не удалось загрузить информацию о прогрессе.")


# Callback обработчики
@router.callback_query(F.data.startswith("achievements:"))
async def handle_achievements_callbacks(callback: CallbackQuery, user_context: UserContext):
    """Обработка колбэков достижений"""
    
    handler = AchievementCommands()
    action_parts = callback.data.split(":")
    
    try:
        if len(action_parts) < 2:
            await callback.answer("Неверный формат команды")
            return
        
        action = action_parts[1]
        
        if action == "back" or action == "refresh":
            # Возврат к главному списку достижений
            await handler.handle_achievements_list(callback.message, user_context)
            
        elif action == "category" and len(action_parts) >= 3:
            # Показ категории достижений
            category = action_parts[2]
            await handler.handle_achievements_category(callback, category, user_context)
            
        elif action == "details" and len(action_parts) >= 3:
            # Детали конкретного достижения  
            achievement_id = action_parts[2]
            await handler.handle_achievement_details(callback, achievement_id, user_context)
            
        elif action == "claim" and len(action_parts) >= 3:
            # Получение наград
            achievement_id = action_parts[2]
            await handler.handle_claim_rewards(callback, achievement_id, user_context)
            
        elif action == "leaderboard":
            # Таблица лидеров
            category = action_parts[2] if len(action_parts) >= 3 else "total_points"
            await handler.handle_leaderboard(callback, category)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка обработки колбэка достижений {callback.data}: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")