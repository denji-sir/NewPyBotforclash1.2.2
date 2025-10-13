"""
Конфигурация pytest с инициализацией всех сервисов
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Добавляем путь к корневой директории проекта  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Устанавливаем переменные окружения ДО импорта модулей
os.environ['TESTING'] = '1'
os.environ['CLAN_TAG'] = '#TEST123'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['BOT_TOKEN'] = '123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ'  # Фейковый токен для тестов
os.environ['COC_API_TOKEN'] = 'test_coc_token'  # Фейковый токен CoC API


def pytest_configure(config):
    """Вызывается один раз перед началом всех тестов - инициализируем сервисы"""
    
    # Инициализируем Passport DB Service
    try:
        from bot.services import passport_database_service
        passport_database_service.init_passport_db_service(':memory:')
        
        # Патчим функцию get_passport_db_service чтобы всегда возвращать инициализированный сервис
        _original_get = passport_database_service.get_passport_db_service
        
        def get_passport_mock():
            try:
                return _original_get()
            except RuntimeError:
                # Если сервис не инициализирован, создаём мок
                mock = Mock()
                mock.get_passport = AsyncMock(return_value=None)
                mock.get_all_passports_in_chat = AsyncMock(return_value=[])
                mock.get_binding_stats = AsyncMock(return_value={
                    'total_bindings': 0, 'verified_bindings': 0, 'unverified_bindings': 0
                })
                return mock
        
        passport_database_service.get_passport_db_service = get_passport_mock
        print("✓ Passport DB Service initialized")
    except Exception as e:
        print(f"⚠ Warning: Could not init passport DB: {e}")
    
    # Инициализируем Clan DB Service
    try:
        from bot.services import clan_database_service
        clan_database_service.init_clan_db_service(':memory:')
        
        # Патчим функцию get_clan_db_service
        _original_get_clan = clan_database_service.get_clan_db_service
        
        def get_clan_mock():
            try:
                return _original_get_clan()
            except RuntimeError:
                mock = Mock()
                mock.get_clan = AsyncMock(return_value=None)
                mock.get_all_clans = AsyncMock(return_value=[])
                mock.get_clan_by_tag = AsyncMock(return_value=None)
                return mock
        
        clan_database_service.get_clan_db_service = get_clan_mock
        print("✓ Clan DB Service initialized")
    except Exception as e:
        print(f"⚠ Warning: Could not init clan DB: {e}")
    
    # Мокируем CoC API Service
    try:
        from bot.services import coc_api_service
        mock_coc = Mock()
        mock_coc.get_clan = AsyncMock(return_value=None)
        mock_coc.get_player = AsyncMock(return_value=None)
        mock_coc.get_current_war = AsyncMock(return_value=None)
        mock_coc.get_capital_raid_seasons = AsyncMock(return_value={'items': []})
        
        # Устанавливаем мок как синглтон
        coc_api_service._coc_api_service = mock_coc
        
        # Патчим класс CoC API
        patcher = patch('bot.services.coc_api_service.CocApiService', return_value=mock_coc)
        patcher.start()
        print("✓ CoC API Service mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock CoC API: {e}")
    
    # Мокируем ClanDatabaseService класс (чтобы он мог создаваться без аргументов)
    try:
        from bot.services import clan_database_service
        mock_clan_db = Mock()
        mock_clan_db.get_clan = AsyncMock(return_value=None)
        mock_clan_db.get_all_clans = AsyncMock(return_value=[])
        mock_clan_db.get_clan_by_tag = AsyncMock(return_value=None)
        
        # Патчим класс чтобы он возвращал мок
        patcher_clan = patch('bot.services.clan_database_service.ClanDatabaseService', return_value=mock_clan_db)
        patcher_clan.start()
        print("✓ ClanDatabaseService class mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock ClanDatabaseService: {e}")
    
    # Мокируем PassportDatabaseService класс
    try:
        from bot.services import passport_database_service as pds
        mock_pass_db = Mock()
        mock_pass_db.get_passport = AsyncMock(return_value=None)
        mock_pass_db.get_all_passports_in_chat = AsyncMock(return_value=[])
        mock_pass_db.get_binding_stats = AsyncMock(return_value={
            'total_bindings': 0, 'verified_bindings': 0, 'unverified_bindings': 0
        })
        
        # Патчим класс
        patcher_pass = patch('bot.services.passport_database_service.PassportDatabaseService', return_value=mock_pass_db)
        patcher_pass.start()
        print("✓ PassportDatabaseService class mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock PassportDatabaseService: {e}")
    
    # Инициализируем Permission Service
    try:
        from bot.services import permission_service
        # Мокируем permission service
        mock_perm = Mock()
        mock_perm.is_admin = AsyncMock(return_value=True)
        mock_perm.is_group_admin = AsyncMock(return_value=True)
        permission_service._permission_service = mock_perm
        print("✓ Permission Service mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not init permission service: {e}")
    
    # Мокируем PlayerBindingService
    try:
        mock_binding = Mock()
        mock_binding.bind_player = AsyncMock()
        mock_binding.unbind_player = AsyncMock()
        mock_binding.verify_player = AsyncMock()
        
        patcher_binding = patch('bot.services.player_binding_service.PlayerBindingService', return_value=mock_binding)
        patcher_binding.start()
        print("✓ PlayerBindingService mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock PlayerBindingService: {e}")
    
    # Мокируем PassportSystemManager
    try:
        mock_manager = Mock()
        mock_manager.create_passport = AsyncMock()
        mock_manager.update_passport = AsyncMock()
        
        patcher_manager = patch('bot.services.passport_system_manager.PassportSystemManager', return_value=mock_manager)
        patcher_manager.start()
        print("✓ PassportSystemManager mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock PassportSystemManager: {e}")
    
    # Мокируем дополнительные сервисы  
    try:
        mock_achievement = Mock()
        mock_achievement.get_user_achievements = AsyncMock(return_value=[])
        mock_achievement.get_user_stats = AsyncMock(return_value={
            'level': 1, 'experience': 0, 'points': 0, 'completed_count': 0
        })
        mock_achievement.track_achievement_progress = AsyncMock()
        
        patcher_ach1 = patch('bot.services.achievement_service.AchievementService', return_value=mock_achievement)
        patcher_ach2 = patch('bot.handlers.achievement_commands.AchievementService', return_value=mock_achievement)
        patcher_ach3 = patch('bot.handlers.greeting_commands.get_achievement_service', return_value=mock_achievement)
        patcher_ach1.start()
        patcher_ach2.start()
        patcher_ach3.start()
        print("✓ AchievementService mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock AchievementService: {e}")
    
    try:
        mock_notification = Mock()
        mock_notification.set_user_notifications = AsyncMock()
        mock_notification.get_user_notifications = AsyncMock(return_value=True)
        
        patcher_notif1 = patch('bot.services.notification_service.NotificationService', return_value=mock_notification)
        patcher_notif2 = patch('bot.handlers.notification_commands.get_notification_service', return_value=mock_notification)
        patcher_notif1.start()
        patcher_notif2.start()
        print("✓ NotificationService mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock NotificationService: {e}")
    
    try:
        mock_greeting = Mock()
        mock_greeting.get_settings = AsyncMock(return_value=Mock(
            is_enabled=False, greeting_text="Привет!", mention_user=True
        ))
        mock_greeting.update_settings = AsyncMock()
        
        patcher_greet1 = patch('bot.services.greeting_service.GreetingService', return_value=mock_greeting)
        patcher_greet2 = patch('bot.handlers.greeting_commands.get_greeting_service', return_value=mock_greeting)
        patcher_greet1.start()
        patcher_greet2.start()
        print("✓ GreetingService mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock GreetingService: {e}")
    
    try:
        mock_stats = Mock()
        mock_stats.get_top_users = AsyncMock(return_value=[])
        
        patcher_stats = patch('bot.handlers.clan_stats_commands.ChatStatisticsService', return_value=mock_stats)
        patcher_stats.start()
        print("✓ ChatStatisticsService mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock ChatStatisticsService: {e}")
    
    try:
        mock_extended = Mock()
        mock_extended.get_clan = AsyncMock(return_value=None)
        mock_donation = Mock()
        mock_donation.get_top_donors = AsyncMock(return_value=[])
        
        patcher_ext = patch('bot.handlers.extended_clash_commands.get_extended_clash_api', return_value=mock_extended)
        patcher_don = patch('bot.handlers.extended_clash_commands.get_donation_history_service', return_value=mock_donation)
        patcher_coc_ext = patch('bot.handlers.extended_clash_commands.get_coc_api_service', return_value=mock_coc)
        patcher_coc_stats = patch('bot.handlers.clan_stats_commands.get_coc_api_service', return_value=mock_coc)
        patcher_ext.start()
        patcher_don.start()
        patcher_coc_ext.start()
        patcher_coc_stats.start()
        print("✓ Extended services mocked")
    except Exception as e:
        print(f"⚠ Warning: Could not mock extended services: {e}")


@pytest.fixture(autouse=True)
def mock_service_getters():
    """Мокируем геттеры сервисов, которые вызываются при импорте"""
    
    # Создаём моки
    mock_notification = Mock()
    mock_notification.set_user_notifications = AsyncMock()
    mock_notification.get_user_notifications = AsyncMock(return_value=True)
    
    mock_greeting = Mock()
    mock_greeting.get_settings = AsyncMock(return_value=Mock(
        is_enabled=False, greeting_text="Привет!", mention_user=True
    ))
    mock_greeting.update_settings = AsyncMock()
    
    mock_achievement = Mock()
    mock_achievement.get_user_achievements = AsyncMock(return_value=[])
    mock_achievement.get_user_stats = AsyncMock(return_value={
        'level': 1, 'experience': 0, 'points': 0, 'completed_count': 0
    })
    mock_achievement.track_achievement_progress = AsyncMock()
    
    mock_extended = Mock()
    mock_extended.get_clan = AsyncMock(return_value=None)
    
    mock_donation = Mock()
    mock_donation.get_top_donors = AsyncMock(return_value=[])
    
    mock_stats = Mock()
    mock_stats.get_top_users = AsyncMock(return_value=[])
    
    # Возвращаем моки для использования в тестах
    yield {
        'notification': mock_notification,
        'greeting': mock_greeting,
        'achievement': mock_achievement,
        'extended': mock_extended,
        'donation': mock_donation,
        'stats': mock_stats
    }
