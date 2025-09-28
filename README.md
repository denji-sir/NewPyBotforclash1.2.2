# NewPyBot для Clash of Clans v1.2.2

Продвинутый Telegram бот для управления кланами в Clash of Clans с расширенным функционалом для войн, рейдов, ЛВК и детальной аналитики.

## 📋 Описание

Этот бот предназначен для:
- 📊 Мониторинга активности участников клана
- ⚔️ Отслеживания войн клана
- 🏆 Статистики участников
- 📈 Аналитики клана
- 🔔 Уведомлений о важных событиях
- 👥 Управления участниками клана

## 🏗️ Архитектура системы

### Основные компоненты

1. **Telegram Bot Handler** - обработка команд и сообщений
2. **Clash of Clans API Client** - интеграция с официальным API
3. **Database Manager** - управление данными
4. **Scheduler** - автоматические задачи и уведомления
5. **Analytics Module** - анализ статистики
6. **Config Manager** - управление конфигурацией

### Структура проекта

```
NewPyBotforclash1.2.2/
├── bot/                          # Основной код бота
│   ├── __init__.py
│   ├── main.py                   # Точка входа
│   ├── config/                   # Конфигурация
│   │   ├── __init__.py
│   │   ├── settings.py           # Основные настройки
│   │   └── database.py           # Конфигурация БД
│   ├── handlers/                 # Обработчики команд
│   │   ├── __init__.py
│   │   ├── start.py              # Команды старта
│   │   ├── clan.py               # Команды клана
│   │   ├── war.py                # Команды войн
│   │   ├── player.py             # Команды игроков
│   │   └── admin.py              # Админские команды
│   ├── services/                 # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── coc_api.py            # Clash of Clans API
│   │   ├── database.py           # Работа с БД
│   │   ├── scheduler.py          # Планировщик задач
│   │   └── analytics.py          # Аналитика
│   ├── models/                   # Модели данных
│   │   ├── __init__.py
│   │   ├── clan.py               # Модель клана
│   │   ├── player.py             # Модель игрока
│   │   └── war.py                # Модель войны
│   └── utils/                    # Утилиты
│       ├── __init__.py
│       ├── decorators.py         # Декораторы
│       ├── validators.py         # Валидаторы
│       └── formatters.py         # Форматеры сообщений
├── data/                         # Данные
│   ├── database/                 # База данных
│   └── logs/                     # Логи
├── tests/                        # Тесты
│   ├── __init__.py
│   ├── test_handlers/
│   ├── test_services/
│   └── test_models/
├── scripts/                      # Скрипты развертывания
│   ├── setup.py
│   └── migrate.py
├── docs/                         # Документация
│   ├── API.md
│   ├── COMMANDS.md
│   └── DEPLOYMENT.md
├── requirements.txt              # Зависимости
├── .env.example                  # Пример переменных среды
├── .gitignore                    # Git ignore
├── docker-compose.yml            # Docker конфигурация
├── Dockerfile                    # Docker образ
└── LICENSE                       # Лицензия
```

## 📚 Технологический стек

### Основные библиотеки

#### Telegram Bot
- **aiogram 3.x** - Современная асинхронная библиотека для Telegram Bot API
- **aiohttp** - HTTP клиент для асинхронных запросов

#### Clash of Clans API
- **coc.py** - Официальная Python библиотека для Clash of Clans API
- **aiofiles** - Асинхронная работа с файлами

#### База данных
- **SQLAlchemy 2.x** - ORM для работы с БД
- **alembic** - Миграции базы данных
- **asyncpg** - PostgreSQL драйвер (рекомендуется)
- **aiosqlite** - SQLite драйвер (для разработки)

#### Планировщик и задачи
- **APScheduler** - Планировщик задач
- **celery** - Очереди задач (для масштабирования)
- **redis** - Кеширование и брокер сообщений

#### Мониторинг и логирование
- **structlog** - Структурированное логирование
- **prometheus-client** - Метрики
- **sentry-sdk** - Мониторинг ошибок

#### Дополнительные утилиты
- **pydantic** - Валидация данных
- **python-dotenv** - Управление переменными среды
- **matplotlib/plotly** - Графики и визуализация
- **pandas** - Анализ данных

### Системные требования

- **Python 3.11+**
- **PostgreSQL 14+** (или SQLite для разработки)
- **Redis 6+** (для кеширования)
- **Docker & Docker Compose** (опционально)

## ⚙️ Конфигурация (.env файл)

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_IDS=123456789,987654321

# Clash of Clans API
COC_API_TOKEN=your_coc_api_token_here
COC_CLAN_TAG=#YOURCLAN

# База данных
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cocbot
# Для разработки можно использовать SQLite:
# DATABASE_URL=sqlite+aiosqlite:///./data/database/bot.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Логирование
LOG_LEVEL=INFO
LOG_FILE=./data/logs/bot.log

# Планировщик
SCHEDULER_TIMEZONE=Europe/Moscow
UPDATE_INTERVAL_MINUTES=30

# Мониторинг
SENTRY_DSN=your_sentry_dsn_here
ENABLE_METRICS=true
METRICS_PORT=8000

# Дополнительные настройки
DEBUG=false
MAX_RETRIES=3
REQUEST_TIMEOUT=30
```

## 🚀 Основные функции

### 📊 Мониторинг клана
- Автоматическое обновление информации о клане
- Отслеживание изменений в составе
- Мониторинг донатов и активности

### ⚔️ Управление войнами
- Уведомления о начале/окончании войн
- Статистика атак участников
- Анализ эффективности войн

### 👥 Управление участниками
- Добавление/удаление участников из отслеживания
- Система ролей и разрешений
- Автоматические предупреждения за неактивность

### 📈 Аналитика
- Графики прогресса участников
- Статистика донатов по периодам
- Сравнительный анализ войн

## 🔧 Команды бота

### Общие команды
- `/start` - Начать работу с ботом
- `/help` - Справка по командам
- `/status` - Статус бота и соединения с API

### Команды клана
- `/clan` - Информация о клане
- `/members` - Список участников клана
- `/donations` - Статистика донатов
- `/wars` - Текущие войны

### Команды игрока
- `/player <tag>` - Информация об игроке
- `/link <tag>` - Привязать свой аккаунт
- `/unlink` - Отвязать аккаунт

### Админские команды
- `/admin` - Панель администратора
- `/settings` - Настройки бота
- `/logs` - Просмотр логов
- `/backup` - Создать резервную копию

## 🐳 Развертывание

### Docker (Рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/denji-sir/NewPyBotforclash1.2.2.git
cd NewPyBotforclash1.2.2

# Скопировать конфигурацию
cp .env.example .env
# Отредактировать .env файл

# Запустить через Docker Compose
docker-compose up -d
```

### Ручная установка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt

# Настроить базу данных
alembic upgrade head

# Запустить бота
python bot/main.py
```

## 📝 API интеграции

### Clash of Clans API
- Получение токена: https://developer.clashofclans.com/
- Документация API: https://developer.clashofclans.com/#/documentation

### Telegram Bot API
- Создание бота: @BotFather в Telegram
- Документация: https://core.telegram.org/bots/api

## 🔒 Безопасность

- Все токены хранятся в переменных среды
- Валидация входных данных
- Rate limiting для API запросов
- Логирование всех действий
- Разделение прав доступа

## 📊 Мониторинг и метрики

- Логирование всех операций
- Метрики производительности (Prometheus)
- Мониторинг ошибок (Sentry)
- Health checks для Docker

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/

# Покрытие кода
pytest --cov=bot tests/

# Линтинг
flake8 bot/
black bot/
```

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 👥 Участие в разработке

1. Fork репозиторий
2. Создайте ветку для фичи (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📞 Контакты

- GitHub: [denji-sir](https://github.com/denji-sir)
- Telegram: @your_username

---

**Версия:** 1.2.2  
**Последнее обновление:** Сентябрь 2025