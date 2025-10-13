"""
Тесты для контекстуальных команд
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aiogram.types import Message, User, Chat


def create_mock_message(text: str, chat_id: int = -1001234567890, user_id: int = 123456789) -> Message:
    """Создает мок сообщения для тестирования"""
    
    user = User(
        id=user_id,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser"
    )
    
    chat = Chat(
        id=chat_id,
        type="supergroup",
        title="Test Chat"
    )
    
    message = Mock(spec=Message)
    message.text = text
    message.from_user = user
    message.chat = chat
    message.message_id = 1
    message.date = Mock()
    message.reply = AsyncMock(return_value=Mock(message_id=2))
    message.answer = AsyncMock(return_value=Mock(message_id=2))
    message.edit_text = AsyncMock()
    message.delete = AsyncMock()
    
    return message


class TestContextualCommands:
    """Тесты контекстуальных команд"""
    
    @pytest.mark.asyncio
    async def test_dashboard_command(self):
        """Тест команды /dashboard"""
        message = create_mock_message("/dashboard")
        
        from bot.handlers.advanced_contextual_commands import cmd_personal_dashboard
        from bot.services.user_context_service import UserContext, UserContextType
        
        user_context = UserContext(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            context_type=UserContextType.NEW_USER,
            has_passport=False
        )
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_passport = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance
            
            await cmd_personal_dashboard(message, user_context)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_recommendations_command(self):
        """Тест команды /recommendations"""
        message = create_mock_message("/recommendations")
        
        from bot.handlers.advanced_contextual_commands import cmd_recommendations
        from bot.services.user_context_service import UserContext, UserContextType
        
        user_context = UserContext(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            context_type=UserContextType.NEW_USER,
            has_passport=False
        )
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_passport = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance
            
            await cmd_recommendations(message, user_context)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_context_help_command(self):
        """Тест команды /context_help"""
        message = create_mock_message("/context_help")
        
        from bot.handlers.advanced_contextual_commands import cmd_contextual_help
        from bot.services.user_context_service import UserContext, UserContextType
        
        user_context = UserContext(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            context_type=UserContextType.NEW_USER,
            has_passport=False
        )
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_passport = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance
            
            await cmd_contextual_help(message, user_context)
            
            assert message.reply.called or message.answer.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
