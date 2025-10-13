"""
Middleware для автоматической проверки rate limiting
Блокирует спамеров до выполнения команд
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from ..services.rate_limit_service import get_rate_limit_service

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для защиты от спама командами
    
    Автоматически проверяет каждую команду на спам
    и блокирует пользователей при злоупотреблении
    """
    
    def __init__(self):
        """Инициализация middleware"""
        super().__init__()
        self.rate_limit_service = None
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка каждого сообщения
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Сообщение от пользователя
            data: Данные контекста
            
        Returns:
            Результат обработки или None если заблокирован
        """
        # Инициализируем сервис при первом вызове
        if self.rate_limit_service is None:
            try:
                self.rate_limit_service = get_rate_limit_service()
            except RuntimeError:
                # Сервис не инициализирован - пропускаем проверку
                return await handler(event, data)
        
        # Проверяем только команды (начинаются с /)
        if not event.text or not event.text.startswith('/'):
            return await handler(event, data)
        
        # Извлекаем команду
        command = event.text.split()[0][1:]  # Убираем /
        if '@' in command:
            command = command.split('@')[0]  # Убираем @bot_username
        
        # Игнорируем служебные команды
        ignored_commands = {'start', 'help'}
        if command in ignored_commands:
            return await handler(event, data)
        
        user_id = event.from_user.id
        chat_id = event.chat.id
        
        # Проверяем rate limit
        allowed, block_message = await self.rate_limit_service.check_rate_limit(
            user_id=user_id,
            chat_id=chat_id,
            command=command
        )
        
        if not allowed:
            # Пользователь заблокирован - отправляем сообщение
            await event.answer(
                block_message,
                parse_mode="Markdown"
            )
            logger.warning(
                f"🚫 Blocked command /{command} from user {user_id} in chat {chat_id}"
            )
            # НЕ вызываем handler - команда не выполняется
            return None
        
        # Разрешено - продолжаем обработку
        return await handler(event, data)
