"""
Простые тесты для проверки системы кланов
"""
import asyncio
import pytest
from pathlib import Path
import tempfile
import os

# Тесты будут работать когда установлены зависимости
try:
    from bot.services.database_init import init_clan_database
    from bot.models.clan_models import ClanData, ClanInfo
    from bot.utils.validators import ClanTagValidator, ValidationHelper
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

# Пропускаем тесты если зависимости не установлены
pytestmark = pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE, 
    reason="Dependencies not installed"
)


class TestClanTagValidator:
    """Тесты валидатора тегов кланов"""
    
    def test_valid_clan_tags(self):
        """Тест валидных тегов"""
        valid_tags = [
            "#2PP0JCCL",
            "#ABC123", 
            "#9RJCUV",
            "#28QG2RR22"
        ]
        
        for tag in valid_tags:
            is_valid, error = ClanTagValidator.validate_clan_tag(tag)
            assert is_valid, f"Tag {tag} should be valid, got error: {error}"
    
    def test_invalid_clan_tags(self):
        """Тест невалидных тегов"""
        invalid_tags = [
            "",  # Пустой
            "#",  # Только решетка
            "ABC123",  # Без решетки
            "#AB",  # Слишком короткий
            "#TOOLONGTAGNAME",  # Слишком длинный
            "#ABC123XYZ456",  # Недопустимые символы
        ]
        
        for tag in invalid_tags:
            is_valid, error = ClanTagValidator.validate_clan_tag(tag)
            assert not is_valid, f"Tag {tag} should be invalid"
            assert error is not None, f"Error message should be provided for {tag}"
    
    def test_normalize_clan_tag(self):
        """Тест нормализации тегов"""
        test_cases = [
            ("2pp0jccl", "#2PP0JCCL"),
            ("#abc123", "#ABC123"),
            ("  #xyz456  ", "#XYZ456"),
            ("9rjcuv", "#9RJCUV"),
        ]
        
        for input_tag, expected in test_cases:
            normalized = ClanTagValidator.normalize_clan_tag(input_tag)
            assert normalized == expected, f"Expected {expected}, got {normalized}"


class TestClanModels:
    """Тесты моделей данных"""
    
    def test_clan_data_from_api_response(self):
        """Тест создания ClanData из ответа API"""
        api_response = {
            'tag': '#2PP0JCCL',
            'name': 'Russians Kings',
            'description': 'Test clan',
            'clanLevel': 15,
            'clanPoints': 45000,
            'members': 47,
            'warWins': 250,
            'warWinStreak': 5,
            'location': {'name': 'Russia'},
            'badgeUrls': {'medium': 'https://example.com/badge.png'}
        }
        
        clan_data = ClanData.from_api_response(api_response)
        
        assert clan_data.tag == '#2PP0JCCL'
        assert clan_data.name == 'Russians Kings'
        assert clan_data.level == 15
        assert clan_data.points == 45000
        assert clan_data.member_count == 47
        assert clan_data.war_wins == 250
        assert clan_data.war_win_streak == 5
        assert clan_data.location == 'Russia'


@pytest.mark.asyncio
class TestDatabase:
    """Тесты базы данных"""
    
    async def test_database_initialization(self):
        """Тест инициализации базы данных"""
        # Создаем временную БД
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Инициализируем БД
            initializer = await init_clan_database(db_path)
            
            # Проверяем целостность
            integrity_ok = await initializer.check_database_integrity()
            assert integrity_ok, "Database integrity check should pass"
            
            # Получаем информацию о БД
            db_info = await initializer.get_database_info()
            assert db_info['database_path'] == db_path
            assert 'tables' in db_info
            assert db_info['tables']['registered_clans'] == 0
            
        finally:
            # Удаляем временную БД
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestValidationHelper:
    """Тесты вспомогательных валидаторов"""
    
    def test_validate_chat_context(self):
        """Тест валидации контекста чата"""
        # Приватный чат (должен быть невалидным)
        is_valid, error = ValidationHelper.validate_chat_context(12345, 67890)
        assert not is_valid
        assert "групповых чатах" in error
        
        # Групповой чат (должен быть валидным)
        is_valid, error = ValidationHelper.validate_chat_context(-12345, 67890)
        assert is_valid
        assert error is None
    
    def test_validate_clan_number(self):
        """Тест валидации номера клана"""
        # Валидный номер
        is_valid, error, number = ValidationHelper.validate_clan_number("2", 5)
        assert is_valid
        assert error is None
        assert number == 2
        
        # Невалидный номер (не число)
        is_valid, error, number = ValidationHelper.validate_clan_number("abc", 5)
        assert not is_valid
        assert "числом" in error
        assert number is None
        
        # Номер вне диапазона
        is_valid, error, number = ValidationHelper.validate_clan_number("10", 5)
        assert not is_valid
        assert "больше 5" in error


def run_basic_tests():
    """Запуск базовых тестов без pytest"""
    print("🧪 Running basic clan system tests...")
    
    # Тест валидатора тегов
    print("✅ Testing clan tag validator...")
    validator = TestClanTagValidator()
    validator.test_valid_clan_tags()
    validator.test_invalid_clan_tags()
    validator.test_normalize_clan_tag()
    
    # Тест моделей
    print("✅ Testing clan models...")
    models_test = TestClanModels()
    models_test.test_clan_data_from_api_response()
    
    # Тест валидации
    print("✅ Testing validation helpers...")
    validation_test = TestValidationHelper()
    validation_test.test_validate_chat_context()
    validation_test.test_validate_clan_number()
    
    print("🎉 All basic tests passed!")


if __name__ == "__main__":
    if DEPENDENCIES_AVAILABLE:
        # Запуск тестов с базы данных требует asyncio
        async def run_async_tests():
            db_test = TestDatabase()
            await db_test.test_database_initialization()
            print("✅ Database tests passed!")
        
        run_basic_tests()
        asyncio.run(run_async_tests())
    else:
        print("⚠️  Dependencies not available, skipping tests")
        print("Install dependencies with: pip install -r requirements.txt")