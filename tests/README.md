# Тесты команд бота

## Быстрый запуск

```bash
# Активировать виртуальное окружение
source .venv/bin/activate

# Запустить все тесты
pytest tests/ -v

# Запустить конкретный тестовый файл
pytest tests/test_all_commands.py -v

# Запустить конкретный тест
pytest tests/test_all_commands.py::TestBasicCommands::test_commands_command -v

# С покрытием кода
pytest tests/ --cov=bot --cov-report=html
```

## Структура тестов

### test_all_commands.py
Основные команды бота:
- Базовые команды (`/start`, `/commands`, `/cancel`)
- Достижения (`/achievements`, `/my_progress`)
- Паспорта (`/passport`, `/plist`)
- Привязки (`/bind_player`, `/binding_stats`)
- Уведомления (`/notif_off`, `/notif_on`, `/notif_status`)
- Статистика (`/top`)

### test_clan_commands.py
Команды для работы с кланами:
- `/clan_extended` - Расширенная информация
- `/war` - Текущая война
- `/raids` - Капитальные рейды
- `/donations` - Статистика донатов
- `/leaders` - Руководители клана
- `/top_donors` - Топ донатеров

### test_greeting_commands.py
Команды приветствий:
- `/greeting` - Настройка приветствий
- `/greeting_on` - Включить
- `/greeting_off` - Выключить

### test_contextual_commands.py
Контекстуальные команды:
- `/dashboard` - Персональная панель
- `/recommendations` - Рекомендации
- `/context_help` - Помощь

## Статус тестов

✅ **Работают:**
- `/commands` - Список всех команд
- `/cancel` - Отмена текущего действия

⚠️ **Требуют доработки:**
- Остальные тесты требуют настройки моков для БД и API

## Добавление новых тестов

```python
import pytest
from unittest.mock import AsyncMock, Mock, patch

class TestMyCommand:
    """Тесты для моей команды"""
    
    @pytest.mark.asyncio
    async def test_my_command(self):
        """Тест команды /my_command"""
        message = create_mock_message("/my_command")
        
        from bot.handlers.my_handler import cmd_my_command
        
        with patch('bot.handlers.my_handler.get_service') as mock_service:
            mock_instance = Mock()
            mock_instance.do_something = AsyncMock(return_value="result")
            mock_service.return_value = mock_instance
            
            await cmd_my_command(message)
            
            assert message.reply.called or message.answer.called
```

## Полезные команды

```bash
# Запустить только неудавшиеся тесты
pytest --lf

# Запустить с подробным выводом
pytest -vv

# Остановиться на первой ошибке
pytest -x

# Показать локальные переменные при ошибке
pytest -l

# Запустить в параллель (требует pytest-xdist)
pytest -n auto
```
