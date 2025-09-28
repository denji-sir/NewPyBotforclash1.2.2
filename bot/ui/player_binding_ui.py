"""
Интерактивные UI компоненты для системы привязки игроков
Фаза 4: Продвинутые интерфейсы с пагинацией и фильтрацией
"""

from typing import List, Dict, Optional, Any, Tuple
import logging
from math import ceil

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..models.passport_models import PlayerBinding, PassportInfo
from ..services.player_search_service import PlayerSearchService
from ..utils.formatting import format_player_info, format_clan_info, truncate_text

logger = logging.getLogger(__name__)


class PlayerBindingUI:
    """Класс для создания интерактивных UI компонентов привязки игроков"""
    
    def __init__(self):
        self.search_service = PlayerSearchService()
    
    def create_binding_menu(self, user_id: int, has_binding: bool = False) -> InlineKeyboardMarkup:
        """
        Создание главного меню привязки игроков
        
        Args:
            user_id: ID пользователя
            has_binding: Есть ли уже привязка у пользователя
            
        Returns:
            InlineKeyboardMarkup с опциями привязки
        """
        builder = InlineKeyboardBuilder()
        
        if has_binding:
            # Меню для пользователей с существующей привязкой
            builder.row(
                InlineKeyboardButton(
                    text="👀 Просмотреть привязку",
                    callback_data=f"view_binding:{user_id}"
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text="🔄 Сменить игрока",
                    callback_data=f"change_player:{user_id}"
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text="❌ Отвязать игрока",
                    callback_data=f"confirm_unbind_menu:{user_id}"
                )
            )
        else:
            # Меню для новой привязки
            builder.row(
                InlineKeyboardButton(
                    text="🏰 Выбрать из клана",
                    callback_data=f"select_from_clan:{user_id}"
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text="🔍 Поиск по имени",
                    callback_data=f"search_by_name:{user_id}"
                ),
                InlineKeyboardButton(
                    text="📝 Ввести тег",
                    callback_data=f"manual_tag_input:{user_id}"
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text="💡 Рекомендации",
                    callback_data=f"binding_recommendations:{user_id}"
                )
            )
        
        # Общие кнопки
        builder.row(
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"cancel_binding:{user_id}"
            )
        )
        
        return builder.as_markup()
    
    def create_clan_members_list(
        self,
        members: List[Dict[str, Any]],
        user_id: int,
        page: int = 0,
        per_page: int = 8,
        filters: Optional[Dict] = None
    ) -> Tuple[InlineKeyboardMarkup, Dict[str, Any]]:
        """
        Создание списка участников клана с пагинацией
        
        Args:
            members: Список участников клана
            user_id: ID пользователя
            page: Текущая страница (начиная с 0)
            per_page: Количество элементов на странице
            filters: Примененные фильтры
            
        Returns:
            Tuple с клавиатурой и информацией о пагинации
        """
        builder = InlineKeyboardBuilder()
        
        # Рассчитываем пагинацию
        total_members = len(members)
        total_pages = ceil(total_members / per_page) if total_members > 0 else 1
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, total_members)
        
        # Добавляем участников на текущей странице
        current_page_members = members[start_idx:end_idx]
        
        for member in current_page_members:
            # Формируем текст кнопки с информацией об участнике
            role_emoji = self._get_role_emoji(member.get('player_role', 'member'))
            trophies = member.get('player_trophies', 0)
            name = truncate_text(member.get('player_name', 'Неизвестно'), 20)
            
            button_text = f"{role_emoji} {name} (💎{trophies:,})"
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"bind_clan_member:{user_id}:{member['player_tag']}"
                )
            )
        
        # Добавляем кнопки пагинации
        if total_pages > 1:
            pagination_buttons = []
            
            if page > 0:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        text="⬅️ Пред.",
                        callback_data=f"clan_members_page:{user_id}:{page-1}"
                    )
                )
            
            pagination_buttons.append(
                InlineKeyboardButton(
                    text=f"📄 {page + 1}/{total_pages}",
                    callback_data=f"clan_members_info:{user_id}"
                )
            )
            
            if page < total_pages - 1:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        text="След. ➡️",
                        callback_data=f"clan_members_page:{user_id}:{page+1}"
                    )
                )
            
            builder.row(*pagination_buttons)
        
        # Добавляем кнопки управления
        management_buttons = [
            InlineKeyboardButton(
                text="🔧 Фильтры",
                callback_data=f"clan_filters:{user_id}"
            ),
            InlineKeyboardButton(
                text="🔍 Поиск",
                callback_data=f"clan_search:{user_id}"
            )
        ]
        builder.row(*management_buttons)
        
        # Кнопка возврата
        builder.row(
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"back_to_binding_options:{user_id}"
            )
        )
        
        # Информация о пагинации
        pagination_info = {
            'current_page': page,
            'total_pages': total_pages,
            'total_members': total_members,
            'showing_from': start_idx + 1 if total_members > 0 else 0,
            'showing_to': end_idx,
            'per_page': per_page,
            'applied_filters': filters or {}
        }
        
        return builder.as_markup(), pagination_info
    
    def create_search_results_keyboard(
        self,
        search_results: Dict[str, Any],
        user_id: int,
        page: int = 0
    ) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры с результатами поиска игроков
        
        Args:
            search_results: Результаты поиска из PlayerSearchService
            user_id: ID пользователя
            page: Текущая страница результатов
            
        Returns:
            InlineKeyboardMarkup с результатами поиска
        """
        builder = InlineKeyboardBuilder()
        
        clan_members = search_results.get('clan_members', [])
        global_results = search_results.get('global_results', [])
        
        # Сначала показываем участников зарегистрированных кланов
        if clan_members:
            builder.row(
                InlineKeyboardButton(
                    text="🏰 Участники зарегистрированных кланов:",
                    callback_data=f"search_info:{user_id}"
                )
            )
            
            for member in clan_members[:5]:  # Показываем первые 5
                name = truncate_text(member.get('player_name', 'Неизвестно'), 18)
                trophies = member.get('player_trophies', 0)
                clan_name = truncate_text(member.get('clan_name', ''), 12)
                
                button_text = f"✅ {name} (💎{trophies:,}) | {clan_name}"
                
                builder.row(
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"bind_search_result:{user_id}:{member['player_tag']}"
                    )
                )
        
        # Затем показываем глобальные результаты
        if global_results:
            if clan_members:  # Добавляем разделитель
                builder.row(
                    InlineKeyboardButton(
                        text="🌍 Другие игроки:",
                        callback_data=f"search_info:{user_id}"
                    )
                )
            
            for result in global_results[:3]:  # Показываем первые 3
                name = truncate_text(result.get('player_name', 'Неизвестно'), 18)
                trophies = result.get('player_trophies', 0)
                
                button_text = f"⚡ {name} (💎{trophies:,})"
                
                builder.row(
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"bind_search_result:{user_id}:{result['player_tag']}"
                    )
                )
        
        # Если результатов много, добавляем кнопку "Показать больше"
        total_results = len(clan_members) + len(global_results)
        if total_results > 8:
            builder.row(
                InlineKeyboardButton(
                    text=f"📋 Показать все ({total_results})",
                    callback_data=f"show_all_search_results:{user_id}:{page}"
                )
            )
        
        # Кнопки управления поиском
        builder.row(
            InlineKeyboardButton(
                text="🔄 Новый поиск",
                callback_data=f"new_search:{user_id}"
            ),
            InlineKeyboardButton(
                text="📝 Ввести тег",
                callback_data=f"manual_tag_input:{user_id}"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🔙 К выбору метода",
                callback_data=f"back_to_binding_options:{user_id}"
            )
        )
        
        return builder.as_markup()
    
    def create_player_validation_keyboard(
        self,
        validation_result: Dict[str, Any],
        user_id: int,
        player_tag: str
    ) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры для подтверждения привязки после валидации
        
        Args:
            validation_result: Результат валидации игрока
            user_id: ID пользователя
            player_tag: Тег игрока
            
        Returns:
            InlineKeyboardMarkup с опциями подтверждения
        """
        builder = InlineKeyboardBuilder()
        
        if validation_result.get('success', False):
            # Игрок прошел валидацию - можно привязывать
            builder.row(
                InlineKeyboardButton(
                    text="✅ Подтвердить привязку",
                    callback_data=f"confirm_bind_player:{user_id}:{player_tag}"
                )
            )
            
            # Дополнительные опции
            builder.row(
                InlineKeyboardButton(
                    text="👀 Детальная информация",
                    callback_data=f"player_detailed_info:{user_id}:{player_tag}"
                )
            )
        else:
            # Ошибка валидации - предлагаем альтернативы
            builder.row(
                InlineKeyboardButton(
                    text="🔄 Попробовать другого игрока",
                    callback_data=f"try_another_player:{user_id}"
                )
            )
            
            builder.row(
                InlineKeyboardButton(
                    text="📝 Исправить тег",
                    callback_data=f"manual_tag_input:{user_id}"
                )
            )
        
        # Общие кнопки
        builder.row(
            InlineKeyboardButton(
                text="🔙 Назад к поиску",
                callback_data=f"back_to_search:{user_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"cancel_binding:{user_id}"
            )
        )
        
        return builder.as_markup()
    
    def create_clan_filters_keyboard(self, user_id: int, current_filters: Dict) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры для настройки фильтров участников клана
        
        Args:
            user_id: ID пользователя
            current_filters: Текущие примененные фильтры
            
        Returns:
            InlineKeyboardMarkup с опциями фильтрации
        """
        builder = InlineKeyboardBuilder()
        
        # Фильтр по кубкам
        trophy_filter = current_filters.get('min_trophies', None)
        trophy_text = f"💎 Кубки (мин: {trophy_filter})" if trophy_filter else "💎 Фильтр по кубкам"
        builder.row(
            InlineKeyboardButton(
                text=trophy_text,
                callback_data=f"filter_trophies:{user_id}"
            )
        )
        
        # Фильтр по ролям
        roles_filter = current_filters.get('roles', [])
        if roles_filter:
            roles_text = f"👤 Роли ({len(roles_filter)} выбрано)"
        else:
            roles_text = "👤 Фильтр по ролям"
        
        builder.row(
            InlineKeyboardButton(
                text=roles_text,
                callback_data=f"filter_roles:{user_id}"
            )
        )
        
        # Фильтр по имени
        name_filter = current_filters.get('name_filter', '')
        if name_filter:
            name_text = f"🔍 Имя: '{name_filter[:10]}...'" if len(name_filter) > 10 else f"🔍 Имя: '{name_filter}'"
        else:
            name_text = "🔍 Поиск по имени"
        
        builder.row(
            InlineKeyboardButton(
                text=name_text,
                callback_data=f"filter_name:{user_id}"
            )
        )
        
        # Управляющие кнопки
        if current_filters:
            builder.row(
                InlineKeyboardButton(
                    text="🗑️ Очистить фильтры",
                    callback_data=f"clear_filters:{user_id}"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="✅ Применить",
                callback_data=f"apply_filters:{user_id}"
            ),
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"back_to_clan_list:{user_id}"
            )
        )
        
        return builder.as_markup()
    
    def create_verification_queue_keyboard(
        self,
        unverified_bindings: List[Dict],
        admin_id: int,
        page: int = 0
    ) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры с очередью неверифицированных привязок
        
        Args:
            unverified_bindings: Список неверифицированных привязок
            admin_id: ID администратора
            page: Текущая страница
            
        Returns:
            InlineKeyboardMarkup с очередью верификации
        """
        builder = InlineKeyboardBuilder()
        
        per_page = 5
        total_pages = ceil(len(unverified_bindings) / per_page) if unverified_bindings else 1
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(unverified_bindings))
        
        current_page_bindings = unverified_bindings[start_idx:end_idx]
        
        for binding in current_page_bindings:
            user_name = truncate_text(binding.get('user_name', 'Неизвестно'), 15)
            player_name = truncate_text(binding.get('player_name', 'Неизвестно'), 15)
            
            button_text = f"✅ {user_name} → {player_name}"
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"verify_binding:{binding['user_id']}:{admin_id}"
                )
            )
        
        # Пагинация для очереди верификации
        if total_pages > 1:
            pagination_buttons = []
            
            if page > 0:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        text="⬅️",
                        callback_data=f"verify_queue_page:{admin_id}:{page-1}"
                    )
                )
            
            pagination_buttons.append(
                InlineKeyboardButton(
                    text=f"{page + 1}/{total_pages}",
                    callback_data=f"verify_queue_info:{admin_id}"
                )
            )
            
            if page < total_pages - 1:
                pagination_buttons.append(
                    InlineKeyboardButton(
                        text="➡️",
                        callback_data=f"verify_queue_page:{admin_id}:{page+1}"
                    )
                )
            
            builder.row(*pagination_buttons)
        
        # Управляющие кнопки
        builder.row(
            InlineKeyboardButton(
                text="✅ Верифицировать всех",
                callback_data=f"verify_all_bindings:{admin_id}"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🔄 Обновить список",
                callback_data=f"refresh_verify_queue:{admin_id}"
            )
        )
        
        return builder.as_markup()
    
    def create_binding_statistics_keyboard(self, user_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры для просмотра статистики привязок
        
        Args:
            user_id: ID пользователя
            is_admin: Является ли пользователь администратором
            
        Returns:
            InlineKeyboardMarkup со статистическими опциями
        """
        builder = InlineKeyboardBuilder()
        
        # Основные статистические кнопки
        builder.row(
            InlineKeyboardButton(
                text="📊 Общая статистика",
                callback_data=f"stats_overview:{user_id}"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🏰 По кланам",
                callback_data=f"stats_by_clans:{user_id}"
            ),
            InlineKeyboardButton(
                text="📈 По времени",
                callback_data=f"stats_by_time:{user_id}"
            )
        )
        
        # Дополнительные опции для администраторов
        if is_admin:
            builder.row(
                InlineKeyboardButton(
                    text="⏳ Очередь верификации",
                    callback_data=f"verification_queue:{user_id}"
                )
            )
            
            builder.row(
                InlineKeyboardButton(
                    text="🔧 Управление привязками",
                    callback_data=f"admin_binding_management:{user_id}"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"refresh_stats:{user_id}"
            )
        )
        
        return builder.as_markup()
    
    def _get_role_emoji(self, role: str) -> str:
        """Получение emoji для роли в клане"""
        role_emojis = {
            'leader': '👑',
            'coLeader': '🔥',
            'elder': '⭐',
            'member': '👤'
        }
        return role_emojis.get(role, '👤')
    
    def format_binding_confirmation_text(
        self,
        validation_result: Dict[str, Any]
    ) -> str:
        """
        Форматирование текста подтверждения привязки
        
        Args:
            validation_result: Результат валидации игрока
            
        Returns:
            Отформатированный текст для сообщения
        """
        if not validation_result.get('success', False):
            return (
                f"❌ **Ошибка валидации игрока**\n\n"
                f"**Ошибка:** {validation_result.get('error', 'Неизвестная ошибка')}\n\n"
                f"**Рекомендации:**\n" + 
                "\n".join([f"• {rec}" for rec in validation_result.get('recommendations', [])])
            )
        
        player_info = validation_result.get('player_info', {})
        clan_analysis = validation_result.get('clan_analysis', {})
        auto_verify = validation_result.get('auto_verify', False)
        
        # Основная информация об игроке
        text = (
            f"🎮 **Подтверждение привязки игрока**\n\n"
            f"👤 **Имя:** `{player_info.get('name', 'Неизвестно')}`\n"
            f"🏷️ **Тег:** `{player_info.get('tag', 'Неизвестно')}`\n"
            f"⭐ **Уровень:** {player_info.get('level', 'N/A')}\n"
            f"🏆 **Кубки:** {player_info.get('trophies', 0):,}\n"
            f"💎 **Лучший результат:** {player_info.get('best_trophies', 0):,}\n\n"
        )
        
        # Информация о клане
        if clan_analysis.get('has_clan', False):
            clan_emoji = "✅" if clan_analysis.get('is_registered_clan', False) else "⚡"
            text += (
                f"🏰 **Клан:** {clan_emoji} {clan_analysis.get('clan_name', 'Неизвестен')}\n"
                f"📊 **Уровень клана:** {clan_analysis.get('clan_level', 'N/A')}\n"
                f"🏆 **Очки клана:** {clan_analysis.get('clan_points', 0):,}\n\n"
            )
        else:
            text += "🏰 **Клан:** Не состоит в клане\n\n"
        
        # Статус верификации
        if auto_verify:
            text += "✅ **Статус:** Будет автоматически верифицирован\n"
        else:
            text += "⏳ **Статус:** Потребуется верификация администратором\n"
        
        # Рекомендации
        recommendations = validation_result.get('recommendations', [])
        if recommendations:
            text += "\n💡 **Рекомендации:**\n"
            text += "\n".join([f"• {rec}" for rec in recommendations])
        
        return text
    
    def format_clan_members_header(
        self,
        clan_name: str,
        pagination_info: Dict[str, Any]
    ) -> str:
        """
        Форматирование заголовка списка участников клана
        
        Args:
            clan_name: Название клана
            pagination_info: Информация о пагинации
            
        Returns:
            Отформатированный заголовок
        """
        showing_from = pagination_info.get('showing_from', 0)
        showing_to = pagination_info.get('showing_to', 0)
        total_members = pagination_info.get('total_members', 0)
        applied_filters = pagination_info.get('applied_filters', {})
        
        text = f"🏰 **Участники клана {clan_name}**\n\n"
        
        if applied_filters:
            text += "🔧 **Применены фильтры:**\n"
            
            if 'min_trophies' in applied_filters:
                text += f"• Кубки: от {applied_filters['min_trophies']:,}\n"
            
            if 'roles' in applied_filters and applied_filters['roles']:
                roles_text = ", ".join(applied_filters['roles'])
                text += f"• Роли: {roles_text}\n"
            
            if 'name_filter' in applied_filters and applied_filters['name_filter']:
                text += f"• Имя содержит: '{applied_filters['name_filter']}'\n"
            
            text += "\n"
        
        text += f"📊 **Показано:** {showing_from}-{showing_to} из {total_members}\n\n"
        text += "Выберите игрока для привязки:"
        
        return text
    
    def format_search_results_header(self, search_results: Dict[str, Any]) -> str:
        """
        Форматирование заголовка результатов поиска
        
        Args:
            search_results: Результаты поиска
            
        Returns:
            Отформатированный заголовок
        """
        query = search_results.get('search_query', '')
        total_found = search_results.get('total_found', 0)
        clan_members_count = len(search_results.get('clan_members', []))
        global_results_count = len(search_results.get('global_results', []))
        
        text = f"🔍 **Результаты поиска: '{query}'**\n\n"
        text += f"📊 **Найдено:** {total_found} игроков\n"
        
        if clan_members_count > 0:
            text += f"🏰 **В зарегистрированных кланах:** {clan_members_count}\n"
        
        if global_results_count > 0:
            text += f"🌍 **Другие игроки:** {global_results_count}\n"
        
        text += "\n"
        
        # Рекомендации по поиску
        recommendations = search_results.get('recommendations', [])
        if recommendations:
            text += "💡 **Рекомендации:**\n"
            for rec in recommendations[:2]:  # Показываем первые 2
                text += f"• {rec}\n"
            text += "\n"
        
        text += "Выберите игрока для привязки:"
        
        return text