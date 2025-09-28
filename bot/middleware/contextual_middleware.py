"""
Middleware для контекстуального анализа сообщений и команд
Фаза 5: Автоматическое определение контекста и персонализация ответов
"""

from typing import Dict, List, Optional, Any, Callable, Awaitable
import logging
from datetime import datetime
import re

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.dispatcher.event.bases import UNHANDLED

from ..services.user_context_service import UserContextService, UserContext, UserContextType
from ..services.passport_database_service import PassportDatabaseService
from ..utils.analytics import MessageAnalytics

logger = logging.getLogger(__name__)


class ContextualMiddleware(BaseMiddleware):
    """
    Middleware для автоматического определения контекста и персонализации ответов
    """
    
    def __init__(self):
        super().__init__()
        self.context_service = UserContextService()
        self.passport_service = PassportDatabaseService()
        self.analytics = MessageAnalytics()
        
        # Кэш контекстов для быстрого доступа
        self._context_cache: Dict[str, UserContext] = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Основная точка входа middleware"""
        
        try:
            # Определяем тип события
            if isinstance(event, Message):
                await self._process_message(event, data)
            elif isinstance(event, CallbackQuery):
                await self._process_callback_query(event, data)
            
            # Выполняем основной обработчик
            return await handler(event, data)
            
        except Exception as e:
            logger.error(f"Ошибка в ContextualMiddleware: {e}")
            # Продолжаем выполнение даже при ошибках middleware
            return await handler(event, data)
    
    async def _process_message(self, message: Message, data: Dict[str, Any]):
        """Обработка обычных сообщений"""
        
        if not message.from_user or message.from_user.is_bot:
            return
        
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Получаем контекст пользователя
        context = await self._get_cached_context(user_id, chat_id)
        
        # Добавляем контекст в данные для обработчиков
        data['user_context'] = context
        data['contextual_middleware'] = self
        
        # Анализируем сообщение
        message_analysis = await self._analyze_message(message, context)
        data['message_analysis'] = message_analysis
        
        # Обновляем статистику активности
        await self._update_activity_stats(user_id, chat_id, message, context)
        
        # Проверяем, нужны ли контекстуальные подсказки
        suggestions = await self._check_contextual_suggestions(message, context)
        if suggestions:
            data['contextual_suggestions'] = suggestions
    
    async def _process_callback_query(self, callback: CallbackQuery, data: Dict[str, Any]):
        """Обработка callback запросов"""
        
        if not callback.from_user or callback.from_user.is_bot:
            return
        
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else None
        
        if chat_id:
            # Получаем контекст пользователя
            context = await self._get_cached_context(user_id, chat_id)
            
            # Добавляем контекст в данные
            data['user_context'] = context
            data['contextual_middleware'] = self
            
            # Обновляем статистику взаимодействия
            await self._update_interaction_stats(user_id, chat_id, callback.data, context)
    
    async def _get_cached_context(self, user_id: int, chat_id: int) -> UserContext:
        """Получение контекста с кэшированием"""
        cache_key = f"{user_id}_{chat_id}"
        
        # Проверяем кэш
        if cache_key in self._context_cache:
            cached_context = self._context_cache[cache_key]
            # Проверяем, не устарел ли кэш (15 минут)
            time_diff = datetime.now() - (cached_context.last_active_date or datetime.now())
            if time_diff.total_seconds() < 900:  # 15 минут
                return cached_context
        
        # Получаем свежий контекст
        context = await self.context_service.get_user_context(user_id, chat_id)
        
        # Кэшируем результат
        self._context_cache[cache_key] = context
        
        return context
    
    async def _analyze_message(self, message: Message, context: UserContext) -> Dict[str, Any]:
        """Анализ сообщения пользователя"""
        
        analysis = {
            'message_type': 'text',
            'is_command': False,
            'command': None,
            'contains_questions': False,
            'contains_clan_terms': False,
            'contains_game_terms': False,
            'sentiment': 'neutral',
            'topics': [],
            'urgency_level': 'low'
        }
        
        text = message.text or ""
        
        # Определяем тип сообщения
        if message.text and message.text.startswith('/'):
            analysis['is_command'] = True
            analysis['command'] = message.text.split()[0].lower()
        
        # Анализируем содержание
        analysis['contains_questions'] = bool(re.search(r'[?？]|как|что|где|когда|зачем|почему', text, re.IGNORECASE))
        analysis['contains_clan_terms'] = bool(re.search(r'клан|clan|война|war|донат|donation', text, re.IGNORECASE))
        analysis['contains_game_terms'] = bool(re.search(r'кубки|trophies|атака|attack|защита|defense', text, re.IGNORECASE))
        
        # Определяем тематики
        topics = []
        if analysis['contains_clan_terms']:
            topics.append('clan')
        if analysis['contains_game_terms']:
            topics.append('gameplay')
        if analysis['contains_questions']:
            topics.append('help_request')
        
        analysis['topics'] = topics
        
        # Простой анализ тональности
        positive_words = ['спасибо', 'отлично', 'круто', 'хорошо', 'супер', 'класс']
        negative_words = ['плохо', 'не работает', 'ошибка', 'проблема', 'не могу']
        
        text_lower = text.lower()
        if any(word in text_lower for word in positive_words):
            analysis['sentiment'] = 'positive'
        elif any(word in text_lower for word in negative_words):
            analysis['sentiment'] = 'negative'
        
        # Определяем уровень срочности
        urgent_indicators = ['срочно', 'быстро', 'помогите', 'не работает', 'ошибка']
        if any(indicator in text_lower for indicator in urgent_indicators):
            analysis['urgency_level'] = 'high'
        
        return analysis
    
    async def _update_activity_stats(
        self, 
        user_id: int, 
        chat_id: int, 
        message: Message, 
        context: UserContext
    ):
        """Обновление статистики активности пользователя"""
        
        try:
            # Получаем паспорт для обновления статистики
            passport = await self.passport_service.get_passport_by_user(user_id, chat_id)
            
            if passport and passport.stats:
                # Обновляем счетчики
                passport.stats.messages_count += 1
                passport.stats.last_active_date = datetime.now()
                
                # Обновляем дни активности
                today = datetime.now().date()
                if passport.stats.last_active_date.date() != today:
                    passport.stats.days_active += 1
                
                # Сохраняем в базе данных
                await self.passport_service.update_passport_stats(
                    user_id=user_id,
                    chat_id=chat_id,
                    stats_update={
                        'messages_count': passport.stats.messages_count,
                        'last_active_date': passport.stats.last_active_date,
                        'days_active': passport.stats.days_active
                    }
                )
                
                # Обновляем кэшированный контекст
                cache_key = f"{user_id}_{chat_id}"
                if cache_key in self._context_cache:
                    self._context_cache[cache_key].messages_last_week += 1
                
        except Exception as e:
            logger.error(f"Ошибка обновления статистики активности: {e}")
    
    async def _update_interaction_stats(
        self, 
        user_id: int, 
        chat_id: int, 
        callback_data: str, 
        context: UserContext
    ):
        """Обновление статистики взаимодействий через callback"""
        
        try:
            await self.context_service.update_user_interaction(
                user_id=user_id,
                chat_id=chat_id,
                command=f"callback:{callback_data.split(':')[0]}",
                interaction_data={'callback_data': callback_data}
            )
        except Exception as e:
            logger.error(f"Ошибка обновления статистики взаимодействий: {e}")
    
    async def _check_contextual_suggestions(
        self, 
        message: Message, 
        context: UserContext
    ) -> Optional[List[Dict[str, Any]]]:
        """Проверка необходимости контекстуальных подсказок"""
        
        suggestions = []
        text = (message.text or "").lower()
        
        # Предложения для новых пользователей
        if context.context_type == UserContextType.NEW_USER:
            if any(word in text for word in ['помощь', 'что делать', 'как начать']):
                suggestions.append({
                    'type': 'quick_action',
                    'title': '🎯 Начать настройку',
                    'description': 'Создайте паспорт и привяжите игрока',
                    'action': 'welcome_setup'
                })
        
        # Предложения для пользователей без привязки
        elif context.context_type == UserContextType.UNBOUND_USER:
            if any(word in text for word in ['игрок', 'аккаунт', 'привязать']):
                suggestions.append({
                    'type': 'quick_action',
                    'title': '🎮 Привязать игрока',
                    'description': 'Привяжите аккаунт Clash of Clans',
                    'action': 'bind_player'
                })
        
        # Предложения при вопросах о клане
        if any(word in text for word in ['клан', 'clan', 'вступить', 'присоединиться']):
            if not context.is_clan_member:
                suggestions.append({
                    'type': 'information',
                    'title': '🏰 Доступные кланы',
                    'description': 'Посмотрите список кланов для вступления',
                    'action': 'view_clans'
                })
        
        # Предложения при вопросах о статистике
        if any(word in text for word in ['статистика', 'прогресс', 'достижения']):
            if context.has_player_binding and context.is_verified_player:
                suggestions.append({
                    'type': 'feature',
                    'title': '📈 Ваш прогресс',
                    'description': 'Посмотрите детальную статистику',
                    'action': 'my_progress'
                })
        
        # Предложения при упоминании проблем
        if any(word in text for word in ['не работает', 'ошибка', 'проблема', 'помогите']):
            suggestions.append({
                'type': 'help',
                'title': '❓ Контекстуальная помощь',
                'description': 'Получите помощь для вашей ситуации',
                'action': 'context_help'
            })
        
        return suggestions if suggestions else None
    
    async def send_contextual_response(
        self, 
        message: Message, 
        response_type: str, 
        content: Dict[str, Any]
    ):
        """Отправка контекстуального ответа"""
        
        try:
            if response_type == 'suggestion':
                await self._send_suggestion_response(message, content)
            elif response_type == 'tip':
                await self._send_tip_response(message, content)
            elif response_type == 'welcome':
                await self._send_welcome_response(message, content)
                
        except Exception as e:
            logger.error(f"Ошибка отправки контекстуального ответа: {e}")
    
    async def _send_suggestion_response(self, message: Message, content: Dict[str, Any]):
        """Отправка ответа с предложением"""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=content['button_text'],
                callback_data=f"contextual_suggestion:{content['action']}"
            )],
            [InlineKeyboardButton(
                text="❌ Не сейчас",
                callback_data="dismiss_suggestion"
            )]
        ])
        
        await message.reply(
            f"💡 {content['text']}\n\n"
            f"Хотите воспользоваться этим предложением?",
            reply_markup=keyboard
        )
    
    async def _send_tip_response(self, message: Message, content: Dict[str, Any]):
        """Отправка ответа с советом"""
        
        await message.reply(
            f"💡 **Совет:** {content['text']}\n\n"
            f"🔍 Используйте `/smart` для персонализированного меню команд.",
            parse_mode="Markdown"
        )
    
    async def _send_welcome_response(self, message: Message, content: Dict[str, Any]):
        """Отправка приветственного ответа"""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎯 Начать настройку",
                callback_data="contextual_cmd:welcome_setup"
            )],
            [InlineKeyboardButton(
                text="❓ Получить помощь",
                callback_data="contextual_cmd:context_help"
            )]
        ])
        
        await message.reply(
            f"👋 {content['greeting']}\n\n"
            f"{content['description']}\n\n"
            f"С чего хотите начать?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def invalidate_context_cache(self, user_id: int, chat_id: int):
        """Инвалидация кэша контекста пользователя"""
        cache_key = f"{user_id}_{chat_id}"
        if cache_key in self._context_cache:
            del self._context_cache[cache_key]


class SmartResponseGenerator:
    """Генератор умных ответов на основе контекста"""
    
    def __init__(self):
        self.context_service = UserContextService()
    
    async def generate_smart_response(
        self, 
        message: Message, 
        context: UserContext,
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Генерация умного ответа на основе контекста и анализа сообщения
        
        Args:
            message: Сообщение пользователя
            context: Контекст пользователя
            analysis: Результат анализа сообщения
            
        Returns:
            Словарь с данными для ответа или None
        """
        
        # Ответы на вопросы новых пользователей
        if context.context_type == UserContextType.NEW_USER:
            return await self._generate_newbie_response(message, context, analysis)
        
        # Ответы пользователям без привязки
        elif context.context_type == UserContextType.UNBOUND_USER:
            return await self._generate_unbound_response(message, context, analysis)
        
        # Ответы ожидающим верификации
        elif context.context_type == UserContextType.PENDING_VERIFICATION:
            return await self._generate_pending_response(message, context, analysis)
        
        # Ответы верифицированным пользователям
        elif context.context_type == UserContextType.VERIFIED_MEMBER:
            return await self._generate_member_response(message, context, analysis)
        
        return None
    
    async def _generate_newbie_response(
        self, 
        message: Message, 
        context: UserContext, 
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Генерация ответа для новых пользователей"""
        
        text = (message.text or "").lower()
        
        # Вопросы о начале работы
        if analysis['contains_questions'] and any(word in text for word in ['начать', 'делать', 'как']):
            return {
                'type': 'welcome',
                'greeting': 'Добро пожаловать в наш чат!',
                'description': (
                    "Для начала работы вам нужно:\n"
                    "1️⃣ Создать личный паспорт\n"
                    "2️⃣ Привязать игрока Clash of Clans\n"
                    "3️⃣ Выбрать клан для участия"
                )
            }
        
        # Вопросы о командах
        if any(word in text for word in ['команды', 'помощь', 'справка']):
            return {
                'type': 'tip',
                'text': (
                    "Начните с команды /create_passport для создания паспорта. "
                    "После этого используйте /smart для персонализированного меню."
                )
            }
        
        return None
    
    async def _generate_unbound_response(
        self, 
        message: Message, 
        context: UserContext, 
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Генерация ответа для пользователей без привязки"""
        
        text = (message.text or "").lower()
        
        # Вопросы о привязке игрока
        if any(word in text for word in ['игрок', 'аккаунт', 'привязать', 'тег']):
            return {
                'type': 'suggestion',
                'text': (
                    "Я вижу, что у вас еще не привязан игрок Clash of Clans. "
                    "Привязка позволит получить доступ ко всем функциям бота."
                ),
                'button_text': '🎮 Привязать игрока',
                'action': 'bind_player'
            }
        
        return None
    
    async def _generate_pending_response(
        self, 
        message: Message, 
        context: UserContext, 
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Генерация ответа для ожидающих верификации"""
        
        text = (message.text or "").lower()
        
        # Вопросы о верификации
        if any(word in text for word in ['верификация', 'проверка', 'когда', 'долго']):
            days_waiting = 0
            if context.player_binding:
                days_waiting = (datetime.now() - context.player_binding.binding_date).days
            
            if days_waiting < 3:
                message_text = "Ваша привязка в обычной очереди верификации. Обычно это занимает 1-3 дня."
            elif days_waiting < 7:
                message_text = "Ваша привязка ожидает дольше обычного. Рекомендуем быть активнее в чате."
            else:
                message_text = "Ваша привязка ожидает слишком долго. Обратитесь к администратору."
            
            return {
                'type': 'tip',
                'text': message_text
            }
        
        return None
    
    async def _generate_member_response(
        self, 
        message: Message, 
        context: UserContext, 
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Генерация ответа для верифицированных участников"""
        
        # Для верифицированных участников генерируем ответы по темам
        if 'clan' in analysis['topics']:
            return {
                'type': 'suggestion',
                'text': "Вижу, что вы спрашиваете о клановых делах. Хотите посмотреть статистику клана?",
                'button_text': '🏰 Статистика клана',
                'action': 'clan_stats'
            }
        
        if 'gameplay' in analysis['topics']:
            return {
                'type': 'suggestion',
                'text': "Есть вопросы по игре? Могу показать ваш прогресс и дать персональные рекомендации.",
                'button_text': '📈 Мой прогресс',
                'action': 'my_progress'
            }
        
        return None