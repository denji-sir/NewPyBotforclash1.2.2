# Команды бота и система достижений

## 📋 Все команды бота

### 🏠 Основные команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие бота и основная информация |
| `/help` | Справка по командам |

---

### 🏆 Достижения

| Команда | Описание |
|---------|----------|
| `/achievements` или `/ach` | Просмотр всех ваших достижений |
| `/my_progress` или `/progress` | Ваш личный прогресс (уровень, опыт, очки) |

**Интерфейс достижений:**
- 📊 Общая сводка с уровнем и опытом
- 🏅 Статистика по категориям
- 🎯 Интерактивные кнопки для навигации
- 🎁 Получение наград за завершенные достижения
- 🏆 Таблица лидеров

**Категории достижений:**
- 💬 Социальные - за активность в чате
- 🎮 Игровой прогресс - за развитие в игре
- 🏰 Вклад в клан - за помощь клану
- ⚙️ Освоение системы - за использование функций бота
- 👑 Лидерство - за лидерские качества
- 🎉 Особые события - за участие в событиях

**Статусы достижений:**
- 🔒 Заблокировано - нужно выполнить предварительные условия
- 🔓 Доступно - можно начать выполнять
- ⏳ В процессе - выполняется
- ✅ Завершено - готово к получению наград
- 💎 Награды получены

---

### 👤 Паспорта и привязки

| Команда | Описание |
|---------|----------|
| `/create_passport` | Создать свой паспорт игрока |
| `/passport [тег]` | Просмотреть паспорт (свой или другого игрока) |
| `/edit_passport` | Редактировать свой паспорт |
| `/plist` | Список всех паспортов в чате |
| `/dpassport` | Удалить свой паспорт |
| `/bind_player` | Привязать игрока CoC к паспорту |
| `/unbind_player` | Отвязать игрока от паспорта |
| `/verify_player` | Верифицировать привязку (только админы) |
| `/binding_stats` | Статистика привязок в чате |

---

### 🏰 Кланы и войны

| Команда | Описание |
|---------|----------|
| `/clan_extended [тег]` | Расширенная информация о клане |
| `/war [тег]` | Текущая война клана |
| `/raids [тег]` | Капитальные рейды клана |
| `/leaders [тег]` | Список руководителей (глава первый, соруки по алфавиту) |
| `/donations [тег]` | Статистика донатов клана |
| `/top_donors [тег]` | Топ донатеров за месяц |

---

### 🔔 Уведомления

| Команда | Описание |
|---------|----------|
| `/notif_off` | Отключить упоминания в КВ-уведомлениях |
| `/notif_on` | Включить упоминания в КВ-уведомлениях |
| `/notif_status` | Показать текущие настройки уведомлений |

---

### 👋 Приветствия

| Команда | Описание |
|---------|----------|
| `/greeting` | Настройка приветствий в чате |
| `/greeting_on` | Быстро включить приветствия |
| `/greeting_off` | Быстро выключить приветствия |

---

### 📊 Статистика чата

| Команда | Описание |
|---------|----------|
| `/top` | Топ активных участников чата (по сообщениям и символам) |

---

### 🎯 Контекстуальные команды

| Команда | Описание |
|---------|----------|
| `/dashboard` | Персональная панель управления |
| `/recommendations` | Интеллектуальные рекомендации |
| `/context_help` | Контекстуальная помощь |

---

### 👑 Админские команды

| Команда | Описание |
|---------|----------|
| `/apass` | Административное управление привязками |
| `/areport` | Детальный отчет по привязкам |

---

### 🛠️ Служебные

| Команда | Описание |
|---------|----------|
| `/cancel` | Отменить текущее действие |

---

## 🏆 Система достижений

### Как работает

1. **Автоматическое отслеживание** - бот автоматически отслеживает ваши действия
2. **Прогресс в реальном времени** - видите прогресс по каждому достижению
3. **Награды** - получайте очки опыта, титулы, значки
4. **Уровни** - повышайте уровень за накопленный опыт
5. **Таблица лидеров** - соревнуйтесь с другими игроками

### Пример использования

```
/achievements
```

Откроется интерактивное меню:
```
🏆 Ваши достижения

👤 Уровень: 5 (60% до 6)
⭐ Опыт: 1200/2000 XP
🎯 Очки: 450
🏅 Завершено: 12/50 достижений
💎 Получено наград: 10 раз

📈 ████████░░ 60%

📊 По категориям:
   💬 Социальные: 5/10 (50%)
   🎮 Игровой прогресс: 3/15 (20%)
   🏰 Вклад в клан: 4/12 (33%)

[💬 Социальные] [🎮 Игровые]
[🏰 Клановые] [⚙️ Система]
[👑 Лидерство] [🎉 События]
[🏆 Таблица лидеров] [🔄 Обновить]
```

### Создание достижений

**НЕТ специальной панели для создания достижений через чат!**

Достижения создаются **программно** в коде:

#### Способ 1: Через `SYSTEM_ACHIEVEMENTS` в `achievement_models.py`

```python
# В файле bot/models/achievement_models.py
SYSTEM_ACHIEVEMENTS = [
    {
        'achievement_id': 'first_message',
        'name': 'Первое слово',
        'description': 'Отправьте первое сообщение в чате',
        'category': AchievementCategory.SOCIAL,
        'difficulty': AchievementDifficulty.BRONZE,
        'icon': '💬',
        'points': 10,
        'max_progress': 1,
        'requirements': [
            {
                'requirement_type': 'messages_count',
                'target_value': 1,
                'comparison': 'gte'
            }
        ],
        'rewards': [
            {
                'reward_type': RewardType.EXPERIENCE,
                'value': 50,
                'name': 'Опыт',
                'icon': '⭐'
            }
        ]
    },
    # ... другие достижения
]
```

#### Способ 2: Через `AchievementService`

```python
from bot.services.achievement_service import AchievementService

service = AchievementService()

# Создать достижение
achievement = Achievement(
    achievement_id='custom_achievement',
    name='Мое достижение',
    description='Описание достижения',
    category=AchievementCategory.GAME_PROGRESS,
    difficulty=AchievementDifficulty.GOLD,
    icon='🎯',
    points=100,
    requirements=[
        AchievementRequirement(
            requirement_type='trophies',
            target_value=3000,
            comparison='gte'
        )
    ],
    rewards=[
        AchievementReward(
            reward_type=RewardType.EXPERIENCE,
            value=200,
            name='Опыт',
            icon='⭐'
        )
    ]
)

# Сохранить в БД
await service.create_or_update_achievement(achievement)
```

### Типы требований

```python
'messages_count'           # Количество сообщений
'passport_created'         # Создан паспорт
'player_bound'             # Привязан игрок
'clan_membership'          # Членство в клане
'player_verified'          # Игрок верифицирован
'trophies'                 # Количество кубков
'clan_wars_participated'   # Участие в КВ
'donations_made'           # Сделано донаций
```

### Типы наград

```python
RewardType.EXPERIENCE      # Опыт (XP)
RewardType.POINTS          # Очки
RewardType.TITLE           # Титул
RewardType.BADGE           # Значок
RewardType.SPECIAL         # Особая награда
```

---

## 🎮 Как работают команды

### 1. Регистрация команд

Команды регистрируются через роутеры в `bot/handlers/`:

```python
from aiogram import Router
from aiogram.filters import Command

router = Router()

@router.message(Command("mycommand"))
async def my_command_handler(message: Message):
    await message.reply("Привет!")
```

### 2. Подключение роутеров

В `bot/main.py` роутеры подключаются к диспетчеру:

```python
from .handlers import greeting_router
from .handlers.notification_commands import notification_router

self.dp.include_router(greeting_router)
self.dp.include_router(notification_router)
```

### 3. Интерактивные кнопки

Команды используют inline-кнопки для навигации:

```python
from aiogram.utils.keyboard import InlineKeyboardBuilder

keyboard = InlineKeyboardBuilder()
keyboard.row(
    InlineKeyboardButton(text="Кнопка 1", callback_data="action:data1"),
    InlineKeyboardButton(text="Кнопка 2", callback_data="action:data2")
)

await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())
```

### 4. Обработка callback'ов

```python
@router.callback_query(F.data.startswith("action:"))
async def handle_callback(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    # Обработка действия
    await callback.answer()
```

---

## 📝 Добавление новой команды

### Шаг 1: Создать обработчик

```python
# В файле bot/handlers/my_commands.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("mycommand"))
async def cmd_mycommand(message: Message):
    await message.reply("Моя команда работает!")
```

### Шаг 2: Подключить роутер

```python
# В файле bot/main.py
from .handlers.my_commands import router as my_router

self.dp.include_router(my_router)
```

### Шаг 3: Готово!

Команда `/mycommand` теперь доступна в боте.

---

## 🔍 Где найти код команд

- **Основные команды**: `bot/handlers/greeting_commands.py`
- **Достижения**: `bot/handlers/achievement_commands.py`
- **Паспорта**: `bot/handlers/passport_commands.py`
- **Привязки**: `bot/handlers/player_binding_commands.py`
- **Кланы**: `bot/handlers/extended_clash_commands.py`
- **Уведомления**: `bot/handlers/notification_commands.py`
- **Админские**: `bot/handlers/admin_binding_commands.py`

---

## ✅ Итого

- ✅ **Достижения создаются программно**, не через чат
- ✅ **6 системных достижений** уже созданы автоматически
- ✅ **Команды работают** через роутеры и обработчики
- ✅ **Интерактивный интерфейс** с кнопками и callback'ами
- ✅ **Автоматическое отслеживание** прогресса
- ✅ **Полная документация** в коде
