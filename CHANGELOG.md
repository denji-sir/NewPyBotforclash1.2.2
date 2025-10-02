# Changelog

Все значимые изменения в этом проекте будут документированы в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-12-28

### Изменено

#### Бэкенд
- Обновлены названия команд для улучшения пользовательского опыта:
  - `/passport_list` → `/plist` - краткий список паспортов
  - `/delete_passport` → `/dpassport` - удаление паспорта
  - `/admin_bindings` → `/apass` - административное управление привязками
  - `/binding_report` → `/areport` - отчет по привязкам
  - `/achievements` теперь поддерживает алиас `/ach`
  - `/my_progress` теперь доступен как `/progress`

#### Документация
- Обновлена документация в папке `docs/` с новыми названиями команд
- Обновлены файлы `COMMAND_OUTPUTS.md` и `COMMANDS_LIST.md`
- Исправлены ссылки на команды во всех документах

## [1.0.0] - 2024-12-28

### Добавлено

#### Бэкенд
- Полная структура Clash of Clans бота с модульной архитектурой
- Система кланов с регистрацией и управлением (`bot/services/clan_system_manager.py`)
- Интеграция с Clash of Clans API (`bot/services/extended_clash_api.py`)
- Система паспортов игроков (`bot/services/passport_system_manager.py`)
- Система достижений с отслеживанием событий (`bot/services/achievement_service.py`)
- Система приветствий с настраиваемыми шаблонами (`bot/services/greeting_service.py`)
- Сервисы для работы с базой данных (`bot/services/clan_database_service.py`)
- Система привязки игроков (`bot/services/player_binding_service.py`)
- Поиск игроков (`bot/services/player_search_service.py`)
- Контекстные сервисы пользователей (`bot/services/user_context_service.py`)
- Система разрешений (`bot/services/permission_service.py`)

#### Фронтенд
- UI компоненты для привязки игроков (`bot/ui/player_binding_ui.py`)
- Обработчики команд в модульной структуре (`bot/handlers/`)
- Middleware для обработки запросов (`bot/middleware/`)

#### Тесты
- Базовые тесты для системы кланов (`tests/test_clan_system.py`)
- Тесты расширенной функциональности (`tests/test_extended_functionality.py`)
- Тесты системы приветствий (`tests/test_greeting_system.py`)
- Структура тестов для handlers, models и services

### Конфигурация
- Настройка проекта через `.env` файлы
- Конфигурация бота (`bot/config.py`)
- Зависимости проекта (`requirements.txt`)
- Правильно настроенный `.gitignore` для Python проектов
- Точки входа: `main.py` и `run.py`

### Документация
- Полная документация всех систем в папке `docs/`
- Руководства по быстрому старту (`docs/QUICK_START.md`)
- Документация по API Clash of Clans (`docs/CLASH_OF_CLANS_API.md`)
- Описание всех фаз разработки
- Примеры использования (`examples/clan_system_example.py`)

### Модели данных
- Модели кланов (`bot/models/clan_models.py`)
- Модели достижений (`bot/models/achievement_models.py`)
- Модели приветствий (`bot/models/greeting_models.py`)
- Модели паспортной системы (`bot/models/passport_models.py`)
- Расширенные модели кланов (`bot/models/extended_clan_models.py`)

### Утилиты
- Форматтеры данных (`bot/utils/formatters.py`)
- Валидаторы (`bot/utils/validators.py`)
- Помощники для работы с кланами (`bot/utils/clan_helpers.py`)
- Менеджер анализа кланов (`bot/utils/clan_analysis_manager.py`)

### Инфраструктура
- Виртуальное окружение Python 3.12
- Настройка зависимостей без конфликтов хешей
- Исправление импортов в модульной структуре
- Настройка pytest для тестирования

## Технические детали

### Исправленные проблемы
- Исправлены ошибки импорта в `bot/__init__.py`
- Создан корректный `bot/services/__init__.py` с правильными импортами
- Обновлены зависимости в `requirements.txt` без хешей для совместимости
- Настроено виртуальное окружение с Python 3.12

### Архитектурные решения
- Модульная структура с разделением на services, handlers, models, utils
- Использование async/await для асинхронных операций
- Интеграция с aiogram для Telegram бота
- Поддержка SQLAlchemy для работы с базой данных
- Использование aiohttp для HTTP запросов к API

### Зависимости
- aiogram==3.15.0 - Telegram Bot API
- aiohttp==3.11.10 - HTTP клиент
- coc.py==3.9.1 - Clash of Clans API
- SQLAlchemy==2.0.36 - ORM для базы данных
- asyncpg==0.30.0 - PostgreSQL драйвер
- pytest==8.3.4 - Тестирование
- aiofiles==24.1.0 - Асинхронная работа с файлами