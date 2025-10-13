"""
Тесты для команд приветствий
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aiogram.types import Message, User, Chat


def create_mock_message(text: str, chat_id: int = -1001234567890, user_id: int = 123456789, chat_type: str = "supergroup") -> Message:
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
        type=chat_type,
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


class TestGreetingCommands:
    """Тесты команд приветствий"""
    
    @pytest.mark.asyncio
    async def test_greeting_command(self):
        """Тест команды /greeting"""
        message = create_mock_message("/greeting", chat_type="supergroup")
        mock_state = AsyncMock()
        
        from bot.handlers.greeting_commands import cmd_greeting
        
        with patch('bot.handlers.greeting_commands.get_greeting_service') as mock_service, \
             patch('bot.handlers.greeting_commands.is_group_admin') as mock_is_admin:
            
            # Мок для проверки админа
            mock_is_admin.return_value = True
            
            mock_instance = Mock()
            mock_instance.get_settings = AsyncMock(return_value=Mock(
                is_enabled=False,
                greeting_text=None,
                mention_user=True
            ))
            mock_service.return_value = mock_instance
            
            await cmd_greeting(message, mock_state)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_greeting_on_command(self):
        """Тест команды /greeting_on"""
        message = create_mock_message("/greeting_on", chat_type="supergroup")
        
        from bot.handlers.greeting_commands import cmd_greeting_on
        
        with patch('bot.handlers.greeting_commands.get_greeting_service') as mock_service, \
             patch('bot.handlers.greeting_commands.is_group_admin') as mock_is_admin:
            
            # Мок для проверки админа
            mock_is_admin.return_value = True
            
            mock_instance = Mock()
            mock_instance.update_settings = AsyncMock()
            mock_service.return_value = mock_instance
            
            await cmd_greeting_on(message)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_greeting_off_command(self):
        """Тест команды /greeting_off"""
        message = create_mock_message("/greeting_off", chat_type="supergroup")
        
        from bot.handlers.greeting_commands import cmd_greeting_off
        
        with patch('bot.handlers.greeting_commands.get_greeting_service') as mock_service, \
             patch('bot.handlers.greeting_commands.is_group_admin') as mock_is_admin:
            
            # Мок для проверки админа
            mock_is_admin.return_value = True
            
            mock_instance = Mock()
            mock_instance.update_settings = AsyncMock()
            mock_service.return_value = mock_instance
            
            await cmd_greeting_off(message)
            
            assert message.reply.called or message.answer.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
