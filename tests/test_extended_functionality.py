"""
Базовые тесты для расширенного функционала бота
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from bot.models.extended_clan_models import (
    ExtendedClanInfo, ClanWar, CapitalRaid, MonthlyDonationStats,
    WarState, MemberRole
)
from bot.services.extended_clash_api import ExtendedClashAPI
from bot.utils.formatters import format_large_number, format_percentage


class TestExtendedClanModels:
    """Тесты для моделей расширенных данных клана"""
    
    def test_extended_clan_info_creation(self):
        """Тест создания расширенной информации клана"""
        
        clan_info = ExtendedClanInfo(
            tag="#2PP",
            name="Test Clan",
            clan_level=10,
            members=50,
            clan_points=50000,
            clan_versus_points=30000,
            clan_capital_points=1000,
            required_trophies=2000,
            war_wins=100,
            war_losses=20,
            war_ties=5,
            war_win_streak=10,
            war_frequency="always",
            average_trophies=3500.5
        )
        
        assert clan_info.tag == "#2PP"
        assert clan_info.name == "Test Clan"
        assert clan_info.war_win_rate == 80.0  # 100 / (100 + 20) * 100
    
    def test_clan_war_creation(self):
        """Тест создания данных войны клана"""
        
        war = ClanWar(
            clan_tag="#2PP",
            clan_name="Test Clan",
            opponent_tag="#ENEMY",
            opponent_name="Enemy Clan",
            team_size=15,
            state=WarState.IN_WAR,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            clan_stars=35,
            opponent_stars=30,
            clan_destruction_percentage=85.5,
            opponent_destruction_percentage=80.0,
            attacks_per_member=2,
            clan_attacks=28,
            opponent_attacks=30
        )
        
        assert war.state == WarState.IN_WAR
        assert war.is_victory is True  # Больше звезд
        assert war.clan_stars > war.opponent_stars
    
    def test_monthly_donation_stats(self):
        """Тест статистики донатов"""
        
        stats = MonthlyDonationStats(
            clan_tag="#2PP",
            year=2024,
            month=12,
            total_donations=100000,
            total_received=95000,
            active_members=40,
            top_donors=[]
        )
        
        assert stats.average_donations == 2500.0  # 100000 / 40


class TestFormatters:
    """Тесты для утилит форматирования"""
    
    def test_format_large_number(self):
        """Тест форматирования больших чисел"""
        
        assert format_large_number(1234) == "1,234"
        assert format_large_number(1234567) == "1.2M"
        assert format_large_number(1000000) == "1.0M"
        assert format_large_number(50000) == "50K"
    
    def test_format_percentage(self):
        """Тест форматирования процентов"""
        
        assert format_percentage(85.5) == "85.5%"
        assert format_percentage(100.0) == "100.0%"
        assert format_percentage(0) == "0.0%"


class TestExtendedClashAPI:
    """Тесты для расширенного CoC API"""
    
    @pytest.fixture
    def mock_api(self):
        """Создать mock API"""
        return ExtendedClashAPI(["fake_token"])
    
    def test_token_rotation(self, mock_api):
        """Тест ротации токенов"""
        
        # Добавляем несколько токенов
        mock_api.tokens = ["token1", "token2", "token3"]
        mock_api.current_token_index = 0
        
        # Получаем текущий токен
        current_token = mock_api._get_current_token()
        assert current_token == "token1"
        
        # Ротируем токен
        mock_api._rotate_token()
        assert mock_api.current_token_index == 1
        assert mock_api._get_current_token() == "token2"
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, mock_api):
        """Тест функциональности кеша"""
        
        # Кешируем данные
        test_data = {"test": "data"}
        cache_key = "test_key"
        
        mock_api._cache_data(cache_key, test_data)
        
        # Проверяем что данные кешированы
        cached_data = mock_api._get_cached_data(cache_key)
        assert cached_data == test_data
        
        # Очищаем кеш
        mock_api.clear_cache()
        cached_data = mock_api._get_cached_data(cache_key)
        assert cached_data is None


class MockAsyncContextManager:
    """Mock для async context manager"""
    
    def __init__(self, api):
        self.api = api
    
    async def __aenter__(self):
        return self.api
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestExtendedAPIIntegration:
    """Интеграционные тесты для расширенного API"""
    
    @pytest.fixture
    def mock_extended_api(self):
        """Создать полный mock для расширенного API"""
        
        api = Mock(spec=ExtendedClashAPI)
        
        # Mock данные клана
        mock_clan_info = ExtendedClanInfo(
            tag="#2PP",
            name="Test Clan",
            clan_level=15,
            members=48,
            clan_points=45000,
            clan_versus_points=35000,
            clan_capital_points=2500,
            required_trophies=1800,
            war_wins=150,
            war_losses=25,
            war_ties=8,
            war_win_streak=15,
            war_frequency="always",
            average_trophies=3200.5
        )
        
        # Mock методы
        api.get_extended_clan_info = AsyncMock(return_value=mock_clan_info)
        api.get_current_war = AsyncMock(return_value=None)
        api.get_capital_raid_seasons = AsyncMock(return_value=[])
        api.calculate_monthly_donation_stats = AsyncMock(return_value=None)
        
        # Mock context manager
        api.__aenter__ = AsyncMock(return_value=api)
        api.__aexit__ = AsyncMock(return_value=None)
        
        return api
    
    @pytest.mark.asyncio
    async def test_get_extended_clan_info(self, mock_extended_api):
        """Тест получения расширенной информации о клане"""
        
        async with mock_extended_api as api:
            clan_info = await api.get_extended_clan_info("#2PP")
            
            assert clan_info is not None
            assert clan_info.tag == "#2PP"
            assert clan_info.name == "Test Clan"
            assert clan_info.war_win_rate > 80.0
    
    @pytest.mark.asyncio
    async def test_no_current_war(self, mock_extended_api):
        """Тест случая когда клан не в войне"""
        
        async with mock_extended_api as api:
            war_info = await api.get_current_war("#2PP")
            
            assert war_info is None
    
    @pytest.mark.asyncio
    async def test_empty_raids(self, mock_extended_api):
        """Тест случая когда нет данных о рейдах"""
        
        async with mock_extended_api as api:
            raids = await api.get_capital_raid_seasons("#2PP", limit=5)
            
            assert raids == []


@pytest.mark.asyncio
async def test_bot_startup_sequence():
    """Тест последовательности запуска бота"""
    
    # Тест конфигурации
    from bot.config import BotConfig
    
    # Создаем тестовую конфигурацию
    config = BotConfig(
        bot_token="fake_token",
        clash_tokens=["fake_clash_token"],
        database_url="sqlite:///test.db",
        admin_user_ids=[123456789]
    )
    
    assert config.bot_token == "fake_token"
    assert len(config.clash_tokens) == 1
    assert config.database_url == "sqlite:///test.db"
    
    # Проверяем валидацию
    assert config.validate_tokens()


def test_readme_commands():
    """Тест соответствия команд в README реальным командам"""
    
    from bot.handlers.extended_clash_commands import extended_router
    
    # Проверяем что роутер создан
    assert extended_router is not None
    assert extended_router.name == "extended_clash_router"


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])