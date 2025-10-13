"""
Тесты для команд кланов
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


class TestClanCommands:
    """Тесты команд кланов"""
    
    @pytest.mark.asyncio
    async def test_clan_extended_command(self):
        """Тест команды /clan_extended"""
        message = create_mock_message("/clan_extended #2PP")
        message.get_args = Mock(return_value="#2PP")
        
        from bot.handlers.extended_clash_commands import cmd_clan_extended_info
        
        with patch('bot.handlers.extended_clash_commands.extended_api') as mock_api, \
             patch('bot.handlers.extended_clash_commands.db_service') as mock_db:
            
            # Мок для extended API
            mock_api.get_clan = AsyncMock(return_value=None)
            mock_api.__aenter__ = AsyncMock(return_value=mock_api)
            mock_api.__aexit__ = AsyncMock(return_value=None)
            
            # Мок для DB service
            mock_clan_data = Mock()
            mock_clan_data.clan_tag = "#2PP"
            mock_clan_data.clan_name = "Test Clan"
            mock_db.get_chat_clans = AsyncMock(return_value=[mock_clan_data])
            
            await cmd_clan_extended_info(message, Mock())
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_war_command(self):
        """Тест команды /war"""
        message = create_mock_message("/war #2PP")
        message.get_args = Mock(return_value="#2PP")
        
        from bot.handlers.extended_clash_commands import cmd_current_war
        
        with patch('bot.handlers.extended_clash_commands.extended_api') as mock_api, \
             patch('bot.handlers.extended_clash_commands.db_service') as mock_db, \
             patch('bot.handlers.extended_clash_commands.get_clan_from_args') as mock_get_clan:
            
            # Мок для get_clan_from_args
            mock_clan = Mock()
            mock_clan.clan_tag = "#2PP"
            mock_clan.clan_name = "Test Clan"
            mock_get_clan.return_value = mock_clan
            
            # Мок для extended API
            mock_api.get_current_war = AsyncMock(return_value=None)
            mock_api.__aenter__ = AsyncMock(return_value=mock_api)
            mock_api.__aexit__ = AsyncMock(return_value=None)
            
            await cmd_current_war(message, Mock())
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_raids_command(self):
        """Тест команды /raids"""
        message = create_mock_message("/raids #2PP")
        message.get_args = Mock(return_value="#2PP")
        
        from bot.handlers.extended_clash_commands import cmd_capital_raids
        
        with patch('bot.handlers.extended_clash_commands.extended_api') as mock_api, \
             patch('bot.handlers.extended_clash_commands.db_service') as mock_db, \
             patch('bot.handlers.extended_clash_commands.get_clan_from_args') as mock_get_clan:
            
            # Мок для get_clan_from_args
            mock_clan = Mock()
            mock_clan.clan_tag = "#2PP"
            mock_clan.clan_name = "Test Clan"
            mock_get_clan.return_value = mock_clan
            
            # Мок для extended API
            mock_api.get_capital_raid_seasons = AsyncMock(return_value={'items': []})
            mock_api.__aenter__ = AsyncMock(return_value=mock_api)
            mock_api.__aexit__ = AsyncMock(return_value=None)
            
            await cmd_capital_raids(message, Mock())
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_donations_command(self):
        """Тест команды /donations"""
        message = create_mock_message("/donations #2PP")
        message.get_args = Mock(return_value="#2PP")
        
        from bot.handlers.clan_stats_commands import cmd_clan_donations
        
        with patch('bot.handlers.clan_stats_commands.get_clan_db_service') as mock_db, \
             patch('bot.handlers.clan_stats_commands.ExtendedClashAPI') as mock_api_class:
            
            # Мок для DB
            mock_db_instance = Mock()
            mock_db_instance.get_chat_clans = AsyncMock(return_value=[{'clan_tag': '#2PP'}])
            mock_db.return_value = mock_db_instance
            
            # Мок для API
            mock_api = Mock()
            mock_api.get_clan = AsyncMock(return_value=None)
            mock_api_class.return_value = mock_api
            
            await cmd_clan_donations(message, Mock())
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_leaders_command(self):
        """Тест команды /leaders"""
        message = create_mock_message("/leaders #2PP")
        message.get_args = Mock(return_value="#2PP")
        
        from bot.handlers.clan_stats_commands import cmd_clan_leaders
        
        with patch('bot.handlers.clan_stats_commands.get_clan_db_service') as mock_db, \
             patch('bot.handlers.clan_stats_commands.ExtendedClashAPI') as mock_api_class:
            
            # Мок для DB
            mock_db_instance = Mock()
            mock_db_instance.get_chat_clans = AsyncMock(return_value=[{'clan_tag': '#2PP'}])
            mock_db.return_value = mock_db_instance
            
            # Мок для API
            mock_api = Mock()
            mock_api.get_clan = AsyncMock(return_value=None)
            mock_api_class.return_value = mock_api
            
            await cmd_clan_leaders(message, Mock())
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_top_donors_command(self):
        """Тест команды /top_donors"""
        message = create_mock_message("/top_donors #2PP")
        message.get_args = Mock(return_value="#2PP")
        
        from bot.handlers.extended_clash_commands import cmd_top_donors
        
        with patch('bot.handlers.extended_clash_commands.extended_api') as mock_api, \
             patch('bot.handlers.extended_clash_commands.db_service') as mock_db, \
             patch('bot.handlers.extended_clash_commands.get_clan_from_args') as mock_get_clan, \
             patch('bot.handlers.extended_clash_commands.format_donation_stats') as mock_format:
            
            # Мок для get_clan_from_args
            mock_clan = Mock()
            mock_clan.clan_tag = "#2PP"
            mock_clan.clan_name = "Test Clan"
            mock_get_clan.return_value = mock_clan
            
            # Мок для extended API
            mock_api.calculate_monthly_donation_stats = AsyncMock(return_value={})
            mock_api.__aenter__ = AsyncMock(return_value=mock_api)
            mock_api.__aexit__ = AsyncMock(return_value=None)
            
            # Мок для форматтера
            mock_format.return_value = "📊 Донаты: нет данных"
            
            await cmd_top_donors(message, Mock())
            
            assert message.reply.called or message.answer.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
