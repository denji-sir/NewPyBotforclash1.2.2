"""
Комплексные тесты для всех команд бота
Проверяет, что все команды работают и дают ответ
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiogram.types import Message, User, Chat

import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


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


class TestBasicCommands:
    """Тесты основных команд"""
    
    @pytest.mark.asyncio
    async def test_start_command(self):
        """Тест команды /start"""
        message = create_mock_message("/start")
        
        from bot.handlers.greeting_commands import cmd_start
        
        await cmd_start(message)
        
        assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_commands_command(self):
        """Тест команды /commands"""
        message = create_mock_message("/commands")
        
        from bot.handlers.greeting_commands import cmd_commands
        
        await cmd_commands(message)
        
        assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_cancel_command(self):
        """Тест команды /cancel"""
        message = create_mock_message("/cancel")
        mock_state = AsyncMock()
        mock_state.clear = AsyncMock()
        
        from bot.handlers.greeting_commands import cmd_cancel
        
        await cmd_cancel(message, mock_state)
        
        assert mock_state.clear.called
        assert message.reply.called or message.answer.called


class TestAchievementCommands:
    """Тесты команд достижений"""
    
    @pytest.mark.asyncio
    async def test_achievements_command(self):
        """Тест команды /achievements"""
        message = create_mock_message("/achievements")
        
        from bot.handlers.achievement_commands import cmd_achievements
        from bot.services.user_context_service import UserContext, UserContextType
        
        user_context = UserContext(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            context_type=UserContextType.NEW_USER,
            has_passport=False
        )
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_passport_service, \
             patch('bot.handlers.achievement_commands.AchievementService') as mock_service:
            
            # Мок для passport service
            mock_passport_instance = Mock()
            mock_passport_instance.get_passport = AsyncMock(return_value=None)
            mock_passport_service.return_value = mock_passport_instance
            
            mock_instance = Mock()
            mock_instance.get_user_achievements = AsyncMock(return_value=[])
            mock_instance.get_user_stats = AsyncMock(return_value={
                'level': 1,
                'experience': 0,
                'points': 0,
                'completed_count': 0
            })
            mock_service.return_value = mock_instance
            
            await cmd_achievements(message, user_context)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_my_progress_command(self):
        """Тест команды /my_progress"""
        message = create_mock_message("/my_progress")
        
        from bot.handlers.achievement_commands import cmd_my_progress
        from bot.services.user_context_service import UserContext, UserContextType
        
        user_context = UserContext(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            context_type=UserContextType.NEW_USER,
            has_passport=False
        )
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_passport_service, \
             patch('bot.handlers.achievement_commands.AchievementService') as mock_service:
            
            # Мок для passport service
            mock_passport_instance = Mock()
            mock_passport_instance.get_passport = AsyncMock(return_value=None)
            mock_passport_service.return_value = mock_passport_instance
            
            mock_instance = Mock()
            mock_instance.get_user_stats = AsyncMock(return_value={
                'level': 1,
                'experience': 0,
                'points': 0
            })
            mock_service.return_value = mock_instance
            
            await cmd_my_progress(message, user_context)
            
            assert message.reply.called or message.answer.called


class TestPassportCommands:
    """Тесты команд паспортов"""
    
    @pytest.mark.asyncio
    async def test_passport_command(self):
        """Тест команды /passport"""
        message = create_mock_message("/passport")
        message.get_args = Mock(return_value="")
        
        from bot.handlers.passport_commands import passport_command
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_passport = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance
            
            await passport_command(message, Mock())
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_plist_command(self):
        """Тест команды /plist"""
        message = create_mock_message("/plist")
        
        from bot.handlers.passport_commands import passport_list_command
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_all_passports_in_chat = AsyncMock(return_value=[])
            mock_service.return_value = mock_instance
            
            await passport_list_command(message)
            
            assert message.reply.called or message.answer.called


class TestBindingCommands:
    """Тесты команд привязки игроков"""
    
    @pytest.mark.asyncio
    async def test_bind_player_command(self):
        """Тест команды /bind_player"""
        message = create_mock_message("/bind_player")
        
        from bot.handlers.player_binding_commands import bind_player_command
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_passport = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance
            
            await bind_player_command(message)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_binding_stats_command(self):
        """Тест команды /binding_stats"""
        message = create_mock_message("/binding_stats")
        
        from bot.handlers.player_binding_commands import binding_stats_command
        
        with patch('bot.services.passport_database_service.get_passport_db_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_binding_stats = AsyncMock(return_value={
                'total_bindings': 0,
                'verified_bindings': 0,
                'unverified_bindings': 0
            })
            mock_service.return_value = mock_instance
            
            await binding_stats_command(message)
            
            assert message.reply.called or message.answer.called


class TestNotificationCommands:
    """Тесты команд уведомлений"""
    
    @pytest.mark.asyncio
    async def test_notif_off_command(self):
        """Тест команды /notif_off"""
        message = create_mock_message("/notif_off")
        
        from bot.handlers.notification_commands import cmd_notif_off
        
        with patch('bot.handlers.notification_commands.get_war_notification_service') as mock_service:
            
            mock_instance = Mock()
            mock_instance.set_user_notification_settings = AsyncMock(return_value=True)
            mock_instance.db_path = ':memory:'
            mock_service.return_value = mock_instance
            
            await cmd_notif_off(message)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_notif_on_command(self):
        """Тест команды /notif_on"""
        message = create_mock_message("/notif_on")
        
        from bot.handlers.notification_commands import cmd_notif_on
        
        with patch('bot.handlers.notification_commands.get_war_notification_service') as mock_service:
            
            mock_instance = Mock()
            mock_instance.set_user_notification_settings = AsyncMock(return_value=True)
            mock_instance.db_path = ':memory:'
            mock_service.return_value = mock_instance
            
            await cmd_notif_on(message)
            
            assert message.reply.called or message.answer.called
    
    @pytest.mark.asyncio
    async def test_notif_status_command(self):
        """Тест команды /notif_status"""
        message = create_mock_message("/notif_status")
        
        from bot.handlers.notification_commands import cmd_notif_status
        
        with patch('bot.handlers.notification_commands.get_war_notification_service') as mock_service, \
             patch('aiosqlite.connect') as mock_connect:
            
            # Мок для war notification service
            mock_instance = Mock()
            mock_instance.db_path = ':memory:'
            mock_service.return_value = mock_instance
            
            # Мок для aiosqlite
            mock_db = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=(True, True))
            mock_db.execute = AsyncMock(return_value=mock_cursor)
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_connect.return_value = mock_db
            
            await cmd_notif_status(message)
            
            assert message.reply.called or message.answer.called


class TestChatStatsCommands:
    """Тесты команд статистики чата"""
    
    @pytest.mark.asyncio
    async def test_top_command(self):
        """Тест команды /top"""
        message = create_mock_message("/top")
        
        from bot.handlers.clan_stats_commands import cmd_chat_top
        
        with patch('bot.services.clan_database_service.get_clan_db_service') as mock_clan_service, \
             patch('aiosqlite.connect') as mock_connect:
            
            # Мок для clan service
            mock_clan_instance = Mock()
            mock_clan_instance.db_path = ':memory:'
            mock_clan_service.return_value = mock_clan_instance
            
            # Мок для aiosqlite - пустая статистика
            mock_db = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall = AsyncMock(return_value=[])  # Нет данных
            mock_db.execute = AsyncMock(return_value=mock_cursor)
            mock_db.commit = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_connect.return_value = mock_db
            
            await cmd_chat_top(message)
            
            assert message.reply.called or message.answer.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
