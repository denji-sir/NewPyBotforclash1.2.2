"""
Тесты для системы приветствий
"""

import unittest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from bot.models.greeting_models import GreetingSettings, GreetingStats, GREETING_TEMPLATES
from bot.services.greeting_service import GreetingService


class TestGreetingModels(unittest.TestCase):
    """Тесты для моделей приветствий"""
    
    def test_greeting_settings_creation(self):
        """Тест создания настроек приветствия"""
        
        settings = GreetingSettings(chat_id=12345)
        
        self.assertEqual(settings.chat_id, 12345)
        self.assertFalse(settings.is_enabled)
        self.assertIsNone(settings.greeting_text)
        self.assertTrue(settings.mention_user)
        self.assertFalse(settings.show_rules_button)
    
    def test_greeting_settings_update(self):
        """Тест обновления настроек"""
        
        settings = GreetingSettings(chat_id=12345)
        
        settings.update_settings(
            is_enabled=True,
            greeting_text="Привет, {name}!",
            mention_user=False
        )
        
        self.assertTrue(settings.is_enabled)
        self.assertEqual(settings.greeting_text, "Привет, {name}!")
        self.assertFalse(settings.mention_user)
        self.assertIsInstance(settings.updated_date, datetime)
    
    def test_greeting_formatting(self):
        """Тест форматирования приветствия"""
        
        settings = GreetingSettings(
            chat_id=12345,
            greeting_text="Привет, {name}! Добро пожаловать, @{username}!"
        )
        
        formatted = settings.format_greeting_for_user("Иван Петров", "ivan_petrov")
        expected = "Привет, Иван Петров! Добро пожаловать, @ivan_petrov!"
        
        self.assertEqual(formatted, expected)
    
    def test_greeting_formatting_with_mention(self):
        """Тест форматирования с упоминанием"""
        
        settings = GreetingSettings(
            chat_id=12345,
            greeting_text="Добро пожаловать, {mention}!"
        )
        
        formatted = settings.format_greeting_for_user("Иван", "ivan_petrov")
        expected = "Добро пожаловать, @ivan_petrov!"
        
        self.assertEqual(formatted, expected)
    
    def test_greeting_formatting_without_username(self):
        """Тест форматирования без юзернейма"""
        
        settings = GreetingSettings(
            chat_id=12345,
            greeting_text="Привет, {first_name}! Твой {username}"
        )
        
        formatted = settings.format_greeting_for_user("Иван", "")
        expected = "Привет, Иван! Твой юзернейм"
        
        self.assertEqual(formatted, expected)
    
    def test_greeting_stats_creation(self):
        """Тест создания статистики"""
        
        stats = GreetingStats(chat_id=12345)
        
        self.assertEqual(stats.chat_id, 12345)
        self.assertEqual(stats.total_greetings_sent, 0)
        self.assertIsNone(stats.last_greeting_date)
        self.assertEqual(stats.average_new_members_per_day, 0.0)
    
    def test_greeting_stats_increment(self):
        """Тест увеличения счетчика приветствий"""
        
        stats = GreetingStats(chat_id=12345)
        
        stats.increment_greeting_count()
        
        self.assertEqual(stats.total_greetings_sent, 1)
        self.assertIsInstance(stats.last_greeting_date, datetime)
        
        # Повторный инкремент
        stats.increment_greeting_count()
        self.assertEqual(stats.total_greetings_sent, 2)
    
    def test_greeting_templates_exist(self):
        """Тест наличия шаблонов приветствий"""
        
        self.assertIn('friendly', GREETING_TEMPLATES)
        self.assertIn('clan_welcome', GREETING_TEMPLATES)
        self.assertIn('formal', GREETING_TEMPLATES)
        
        # Проверяем, что шаблоны содержат переменные
        for template in GREETING_TEMPLATES.values():
            self.assertIsInstance(template, str)
            self.assertTrue(len(template) > 0)


class TestGreetingService(unittest.IsolatedAsyncioTestCase):
    """Тесты для сервиса приветствий"""
    
    async def asyncSetUp(self):
        """Настройка тестов"""
        
        # Создаем временную базу данных
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.service = GreetingService(self.temp_db.name)
        await self.service.initialize_database()
    
    async def asyncTearDown(self):
        """Очистка после тестов"""
        
        # Удаляем временную базу данных
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    async def test_get_default_settings(self):
        """Тест получения настроек по умолчанию"""
        
        settings = await self.service.get_greeting_settings(12345)
        
        self.assertEqual(settings.chat_id, 12345)
        self.assertFalse(settings.is_enabled)
        self.assertIsNone(settings.greeting_text)
    
    async def test_update_greeting_settings(self):
        """Тест обновления настроек приветствия"""
        
        success = await self.service.update_greeting_settings(
            chat_id=12345,
            admin_user_id=67890,
            is_enabled=True,
            greeting_text="Тестовое приветствие"
        )
        
        self.assertTrue(success)
        
        # Проверяем, что настройки сохранились
        settings = await self.service.get_greeting_settings(12345)
        self.assertTrue(settings.is_enabled)
        self.assertEqual(settings.greeting_text, "Тестовое приветствие")
        self.assertEqual(settings.created_by, 67890)
    
    async def test_set_greeting_text(self):
        """Тест установки текста приветствия"""
        
        success = await self.service.set_greeting_text(
            chat_id=12345,
            admin_user_id=67890,
            text="Новый текст приветствия"
        )
        
        self.assertTrue(success)
        
        settings = await self.service.get_greeting_settings(12345)
        self.assertEqual(settings.greeting_text, "Новый текст приветствия")
    
    async def test_toggle_greeting(self):
        """Тест переключения статуса приветствий"""
        
        # Включаем приветствия
        success = await self.service.toggle_greeting(12345, 67890, True)
        self.assertTrue(success)
        
        settings = await self.service.get_greeting_settings(12345)
        self.assertTrue(settings.is_enabled)
        
        # Выключаем приветствия
        success = await self.service.toggle_greeting(12345, 67890, False)
        self.assertTrue(success)
        
        settings = await self.service.get_greeting_settings(12345)
        self.assertFalse(settings.is_enabled)
    
    async def test_handle_new_member_disabled(self):
        """Тест обработки нового участника при выключенных приветствиях"""
        
        # Приветствия выключены по умолчанию
        result = await self.service.handle_new_member(
            chat_id=12345,
            user_id=11111,
            username="test_user",
            first_name="Test"
        )
        
        self.assertIsNone(result)
    
    async def test_handle_new_member_enabled(self):
        """Тест обработки нового участника при включенных приветствиях"""
        
        # Включаем приветствия и устанавливаем текст
        await self.service.update_greeting_settings(
            chat_id=12345,
            admin_user_id=67890,
            is_enabled=True,
            greeting_text="Привет, {first_name}!"
        )
        
        result = await self.service.handle_new_member(
            chat_id=12345,
            user_id=11111,
            username="test_user",
            first_name="Test"
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], "Привет, Test!")
        self.assertTrue(result['mention_user'])
    
    async def test_apply_greeting_template(self):
        """Тест применения шаблона приветствия"""
        
        success = await self.service.apply_greeting_template(
            chat_id=12345,
            admin_user_id=67890,
            template_name="friendly"
        )
        
        self.assertTrue(success)
        
        settings = await self.service.get_greeting_settings(12345)
        self.assertEqual(settings.greeting_text, GREETING_TEMPLATES['friendly'])
    
    async def test_apply_invalid_template(self):
        """Тест применения несуществующего шаблона"""
        
        success = await self.service.apply_greeting_template(
            chat_id=12345,
            admin_user_id=67890,
            template_name="nonexistent"
        )
        
        self.assertFalse(success)
    
    async def test_greeting_stats(self):
        """Тест статистики приветствий"""
        
        # Получаем статистику (должна быть пустая)
        stats = await self.service.get_greeting_stats(12345)
        self.assertEqual(stats.total_greetings_sent, 0)
        
        # Настраиваем приветствия и добавляем нового участника
        await self.service.update_greeting_settings(
            chat_id=12345,
            admin_user_id=67890,
            is_enabled=True,
            greeting_text="Тест"
        )
        
        await self.service.handle_new_member(
            chat_id=12345,
            user_id=11111,
            username="user1",
            first_name="User1"
        )
        
        # Проверяем обновленную статистику
        stats = await self.service.get_greeting_stats(12345)
        self.assertEqual(stats.total_greetings_sent, 1)
        self.assertIsNotNone(stats.last_greeting_date)
    
    async def test_greeting_history(self):
        """Тест истории приветствий"""
        
        # Настраиваем приветствия
        await self.service.update_greeting_settings(
            chat_id=12345,
            admin_user_id=67890,
            is_enabled=True,
            greeting_text="Привет, {first_name}!"
        )
        
        # Добавляем несколько участников
        await self.service.handle_new_member(12345, 11111, "user1", "User1")
        await self.service.handle_new_member(12345, 22222, "user2", "User2")
        
        # Получаем историю
        history = await self.service.get_greeting_history(12345, 10)
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['user_id'], 22222)  # Последний добавленный
        self.assertEqual(history[1]['user_id'], 11111)
    
    async def test_mark_user_responded(self):
        """Тест отметки ответа пользователя"""
        
        # Настраиваем приветствия и добавляем участника
        await self.service.update_greeting_settings(
            chat_id=12345,
            admin_user_id=67890,
            is_enabled=True,
            greeting_text="Тест"
        )
        
        await self.service.handle_new_member(12345, 11111, "user1", "User1")
        
        # Отмечаем ответ
        await self.service.mark_user_responded(12345, 11111)
        
        # Проверяем историю
        history = await self.service.get_greeting_history(12345, 1)
        self.assertTrue(history[0]['user_responded'])
    
    async def test_cache_functionality(self):
        """Тест работы кэша"""
        
        # Первый запрос - загрузка из БД
        settings1 = await self.service.get_greeting_settings(12345)
        
        # Второй запрос - из кэша (должен быть тот же объект)
        settings2 = await self.service.get_greeting_settings(12345)
        
        self.assertEqual(settings1.chat_id, settings2.chat_id)
        
        # Очищаем кэш
        self.service.clear_cache(12345)
        
        # Третий запрос - снова из БД
        settings3 = await self.service.get_greeting_settings(12345)
        self.assertEqual(settings3.chat_id, 12345)


class TestGreetingIntegration(unittest.IsolatedAsyncioTestCase):
    """Тесты для интеграции системы приветствий"""
    
    async def asyncSetUp(self):
        """Настройка тестов интеграции"""
        
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Мокаем бота
        self.mock_bot = Mock()
        
        # Создаем сервис с временной БД
        from bot.services.greeting_service import greeting_service
        greeting_service.db_path = self.temp_db.name
        await greeting_service.initialize_database()
        
        # Импортируем интеграцию после настройки сервиса
        from bot.integrations.greeting_integration import greeting_integration
        self.integration = greeting_integration
    
    async def asyncTearDown(self):
        """Очистка после тестов интеграции"""
        
        if hasattr(self, 'integration'):
            await self.integration.shutdown()
        
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    async def test_integration_initialization(self):
        """Тест инициализации интеграции"""
        
        await self.integration.initialize(self.mock_bot)
        
        # Проверяем, что фоновые задачи запущены
        self.assertIsNotNone(self.integration._deletion_processor_task)
        self.assertIsNotNone(self.integration._cleanup_task)
    
    async def test_get_chat_greeting_info(self):
        """Тест получения информации о приветствиях чата"""
        
        info = await self.integration.get_chat_greeting_info(12345)
        
        self.assertIn('enabled', info)
        self.assertIn('has_text', info)
        self.assertIn('total_greetings', info)
        self.assertFalse(info['enabled'])  # По умолчанию выключено
    
    async def test_preview_greeting(self):
        """Тест предварительного просмотра приветствия"""
        
        from bot.services.greeting_service import greeting_service
        
        # Устанавливаем текст приветствия
        await greeting_service.set_greeting_text(
            chat_id=12345,
            admin_user_id=67890,
            text="Привет, {first_name}!"
        )
        
        preview = await self.integration.preview_greeting(12345, "Тест", "test_user")
        
        self.assertEqual(preview, "Привет, Тест!")
    
    async def test_bulk_enable_greetings(self):
        """Тест массового включения приветствий"""
        
        chat_ids = [12345, 23456, 34567]
        
        results = await self.integration.bulk_enable_greetings(chat_ids, 67890)
        
        self.assertIn('success', results)
        self.assertIn('failed', results)
        self.assertEqual(len(results['success']), 3)
        self.assertEqual(len(results['failed']), 0)


class TestGreetingCommands(unittest.IsolatedAsyncioTestCase):
    """Тесты для команд приветствий"""
    
    async def asyncSetUp(self):
        """Настройка тестов команд"""
        
        # Мокаем необходимые объекты
        self.mock_message = Mock()
        self.mock_message.chat.id = 12345
        self.mock_message.chat.type = 'supergroup'
        self.mock_message.from_user.id = 67890
        self.mock_message.reply = AsyncMock()
        
        self.mock_callback = Mock()
        self.mock_callback.message.chat.id = 12345
        self.mock_callback.from_user.id = 67890
        self.mock_callback.answer = AsyncMock()
        self.mock_callback.message.edit_text = AsyncMock()
        
        # Мокаем проверку прав администратора
        self.admin_patcher = patch('bot.handlers.greeting_commands.is_group_admin')
        self.mock_admin_check = self.admin_patcher.start()
        self.mock_admin_check.return_value = True
        
        # Создаем временную БД
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        from bot.services.greeting_service import greeting_service
        greeting_service.db_path = self.temp_db.name
        await greeting_service.initialize_database()
    
    async def asyncTearDown(self):
        """Очистка после тестов команд"""
        
        self.admin_patcher.stop()
        
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    async def test_greeting_command_access_check(self):
        """Тест проверки доступа к командам"""
        
        # Тест с правами администратора уже настроен в setUp
        # Проверяем, что команда выполняется
        from bot.handlers.greeting_commands import cmd_greeting
        
        await cmd_greeting(self.mock_message, Mock())
        
        # Проверяем, что ответ был отправлен
        self.mock_message.reply.assert_called_once()


def run_all_tests():
    """Запуск всех тестов системы приветствий"""
    
    # Создаем test suite
    test_suite = unittest.TestSuite()
    
    # Добавляем тесты моделей
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGreetingModels))
    
    # Добавляем тесты сервиса
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGreetingService))
    
    # Добавляем тесты интеграции
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGreetingIntegration))
    
    # Добавляем тесты команд
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGreetingCommands))
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # Запускаем тесты
    success = run_all_tests()
    
    if success:
        print("\n✅ Все тесты системы приветствий прошли успешно!")
    else:
        print("\n❌ Некоторые тесты провалились!")
        exit(1)