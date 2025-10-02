# 📋 Базовая система паспортов для MVP (SQLite)

## 🎯 **Обзор системы**

Упрощенная система паспортов для первой версии бота с ограничением 1-5 кланов на пользователя. Использует SQLite для простоты развертывания и обслуживания.

### **Ключевые особенности MVP:**
- ✅ Максимум 5 кланов в паспорте (вместо неограниченного количества)
- ✅ Простая SQLite база данных
- ✅ Базовая интеграция с достижениями
- ✅ Контекстуальный выбор кланов
- ✅ Упрощенная привязка игроков через выбор из списка

---

## 🗄️ **Структура базы данных SQLite**

### **1. Таблица зарегистрированных кланов**
```sql
CREATE TABLE registered_clans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_tag TEXT UNIQUE NOT NULL,           -- #2PP0JCCL
    clan_name TEXT NOT NULL,                 -- Russians Kings
    chat_id INTEGER NOT NULL,                -- ID Telegram чата
    registered_by INTEGER NOT NULL,          -- user_id регистратора
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,                        -- Описание клана
    
    -- Индексы для быстрого поиска
    UNIQUE(clan_tag),
    INDEX idx_clan_chat (chat_id),
    INDEX idx_clan_active (is_active)
);
```

### **2. Таблица паспортов пользователей**
```sql
CREATE TABLE user_passports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,         -- Telegram user_id
    username TEXT,                           -- @username
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Слоты для кланов (максимум 5)
    clan_1_id INTEGER,                       -- Основной клан (приоритет 1)
    clan_2_id INTEGER,                       -- Второй клан
    clan_3_id INTEGER,                       -- Третий клан
    clan_4_id INTEGER,                       -- Четвертый клан
    clan_5_id INTEGER,                       -- Пятый клан
    
    -- Настройки паспорта
    is_active BOOLEAN DEFAULT TRUE,
    show_achievements BOOLEAN DEFAULT TRUE,   -- Показывать достижения
    notification_level TEXT DEFAULT 'medium', -- low/medium/high
    
    -- Внешние ключи
    FOREIGN KEY (clan_1_id) REFERENCES registered_clans(id),
    FOREIGN KEY (clan_2_id) REFERENCES registered_clans(id),
    FOREIGN KEY (clan_3_id) REFERENCES registered_clans(id),
    FOREIGN KEY (clan_4_id) REFERENCES registered_clans(id),
    FOREIGN KEY (clan_5_id) REFERENCES registered_clans(id),
    
    -- Индексы
    UNIQUE(user_id),
    INDEX idx_passport_active (is_active)
);
```

### **3. Таблица привязки игроков**
```sql
CREATE TABLE user_player_bindings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,                -- Владелец паспорта
    clan_id INTEGER NOT NULL,                -- К какому клану привязан
    player_tag TEXT NOT NULL,                -- #PLAYER123
    player_name TEXT NOT NULL,               -- Имя в игре
    
    -- Статусы
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,       -- Подтвержден админом
    bound_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified_at DATETIME,
    verified_by INTEGER,                     -- user_id админа
    
    -- Приоритет игрока в клане (основной/дополнительный)
    priority INTEGER DEFAULT 1,             -- 1=основной, 2=второстепенный
    
    -- Внешние ключи
    FOREIGN KEY (user_id) REFERENCES user_passports(user_id),
    FOREIGN KEY (clan_id) REFERENCES registered_clans(id),
    FOREIGN KEY (verified_by) REFERENCES user_passports(user_id),
    
    -- Ограничения
    UNIQUE(user_id, clan_id, player_tag),
    INDEX idx_binding_user (user_id),
    INDEX idx_binding_clan (clan_id),
    INDEX idx_binding_player (player_tag),
    INDEX idx_binding_active (is_active)
);
```

### **4. Таблица настроек чатов (контекстуальные кланы)**
```sql
CREATE TABLE chat_clan_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER UNIQUE NOT NULL,         -- ID Telegram чата
    default_clan_id INTEGER,                 -- Основной клан чата
    
    -- Настройки отображения
    show_clan_numbers BOOLEAN DEFAULT TRUE,  -- Показывать номера кланов
    auto_detect_clan BOOLEAN DEFAULT TRUE,   -- Автоопределение клана
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (default_clan_id) REFERENCES registered_clans(id),
    
    -- Индексы
    UNIQUE(chat_id)
);
```

### **5. Таблица базовых достижений**
```sql
CREATE TABLE passport_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,                -- Владелец достижения
    achievement_type TEXT NOT NULL,          -- 'activity', 'quality', 'social'
    achievement_name TEXT NOT NULL,          -- 'Новичок', 'Активист', etc.
    achievement_level INTEGER DEFAULT 1,     -- Уровень достижения (1-4)
    
    -- Прогресс
    current_progress INTEGER DEFAULT 0,      -- Текущий прогресс
    required_progress INTEGER NOT NULL,      -- Необходимый прогресс
    is_completed BOOLEAN DEFAULT FALSE,
    
    -- Временные метки
    earned_at DATETIME,                      -- Когда получено
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (user_id) REFERENCES user_passports(user_id),
    
    -- Ограничения
    UNIQUE(user_id, achievement_type, achievement_name),
    INDEX idx_achievements_user (user_id),
    INDEX idx_achievements_type (achievement_type),
    INDEX idx_achievements_completed (is_completed)
);
```

---

## 🚀 **Базовая функциональность**

### **1. Регистрация кланов (Админы)**

**Команда:** `/register_clan`

**Процесс:**
1. Админ вводит команду `/register_clan #CLANTAG`
2. Бот проверяет клан через CoC API
3. Если клан существует - регистрирует в БД
4. Привязывает к текущему чату

**Ограничения MVP:**
- Максимум 10 кланов на чат
- Только администраторы чата могут регистрировать
- Простая проверка без дополнительных подтверждений

### **2. Создание паспорта**

**Команда:** `/create_passport`

**Процесс:**
1. Пользователь создает паспорт командой
2. Система создает запись в `user_passports`
3. Показывает список доступных кланов для выбора
4. Пользователь может добавить до 5 кланов

**Пример интерфейса:**
```
🆕 Создание паспорта

Выберите кланы для добавления в паспорт:
1. 🏰 Russians Kings (#2PP0JCCL)
2. ⚔️ War Eagles (#ABC123)
3. 🛡️ Defenders (#DEF456)

Введите номера через пробел (макс. 5):
> 1 2

✅ Паспорт создан!
📋 Добавлены кланы:
  1️⃣ Russians Kings (основной)
  2️⃣ War Eagles
```

### **3. Привязка игроков**

**Команда:** `/bind_player <номер_клана>`

**Процесс:**
1. Пользователь выбирает клан: `/bind_player 1`
2. Бот получает список игроков клана из CoC API
3. Показывает интерактивные кнопки с именами
4. Пользователь выбирает своего игрока
5. Запись добавляется в `user_player_bindings`

**Пример интерфейса:**
```
🔗 Привязка к клану Russians Kings

Выберите своего игрока из списка:

[🏅 Leader Alex] [⭐ Elder Bob] [👤 Member Charlie]
[🎯 Member Dana] [⚡ Member Eve] [🔥 Member Frank]

Или введите тег игрока: #PLAYER123
```

### **4. Просмотр паспорта**

**Команда:** `/passport [@пользователь]`

**Отображение:**
```
📋 Паспорт: @username

👤 Привязанные игроки:
1️⃣ Russians Kings
   🏅 Alex (#PLAYER1) ✅
   
2️⃣ War Eagles  
   ⭐ Bob (#PLAYER2) ✅

🏆 Достижения:
🥉 Новичок (Активность)
🥈 Собеседник (Социальность)

📊 Краткая статистика:
• Дней в чате: 15
• Команд использовано: 42
• Последняя активность: сегодня
```

---

## ⚙️ **Система контекстуального выбора**

### **Автоматическое определение клана**
```python
# Логика определения контекста
def resolve_clan_context(user_id, chat_id, clan_number=None):
    if clan_number:
        # Пользователь указал номер: /stats 2
        return get_user_clan_by_number(user_id, clan_number)
    
    # Получаем паспорт пользователя
    passport = get_user_passport(user_id)
    if passport and passport.clan_1_id:
        return passport.clan_1_id  # Основной клан
    
    # Fallback на основной клан чата
    chat_settings = get_chat_clan_settings(chat_id)
    if chat_settings and chat_settings.default_clan_id:
        return chat_settings.default_clan_id
    
    return None  # Ошибка: не удалось определить клан
```

### **Команды с контекстом**
- `/stats` - статистика основного клана пользователя
- `/stats 2` - статистика второго клана в паспорте
- `/wars` - войны основного клана
- `/wars 3` - войны третьего клана
- `/clan_info` - информация об основном клане

---

## 🎖️ **Базовая интеграция достижений**

### **Достижения для MVP:**
1. **По активности:**
   - 🥉 Новичок (1 день в чате)
   - 🥈 Активист (7 дней активности)
   - 🥇 Ветеран (30 дней активности)

2. **По использованию команд:**
   - 📱 Исследователь (10 команд)
   - 🎯 Знаток (50 команд)
   - 🏆 Эксперт (100 команд)

3. **По социальности:**
   - 💬 Собеседник (10 сообщений)
   - 🤝 Коннектор (помощь новичкам)

### **Простая логика начисления:**
- Проверка раз в день через cron job
- Обновление счетчиков в `passport_achievements`
- Уведомление при получении нового достижения

---

## 📝 **Основные команды MVP**

### **Администраторские команды:**
- `/register_clan <тег>` - регистрация клана
- `/set_default_clan <номер>` - установить основной клан чата
- `/verify_player <@user>` - подтвердить привязку игрока
- `/clan_list` - список зарегистрированных кланов

### **Пользовательские команды:**
- `/create_passport` - создать паспорт
- `/passport [@user]` - посмотреть паспорт
- `/bind_player <номер_клана>` - привязать игрока
- `/my_clans` - список моих кланов
- `/stats [номер]` - статистика клана
- `/achievements` или `/ach` - мои достижения

### **Информационные команды:**
- `/help_passport` - помощь по паспортам
- `/clan_info [номер]` - информация о клане
- `/who_is <тег_игрока>` - найти владельца игрока

---

## ⚠️ **Ограничения MVP**

### **Функциональные ограничения:**
- Максимум 5 кланов на пользователя
- Простая привязка через выбор из списка
- Базовые достижения (без сложной логики)
- Только SQLite (без Redis кеширования)

### **Технические упрощения:**
- Без сложной системы уведомлений
- Минимальная валидация данных
- Простые SQL запросы без оптимизации
- Отсутствие фоновых задач для синхронизации

### **UX упрощения:**
- Нет редактирования паспорта (только пересоздание)
- Простые текстовые сообщения вместо богатого форматирования
- Минимальная обработка ошибок

---

## 🎯 **План поэтапного внедрения**

### **Неделя 1: Основа**
- Создание схемы БД SQLite
- Базовые модели и сервисы
- Команда регистрации кланов

### **Неделя 2: Паспорта**
- Создание и просмотр паспортов
- Добавление кланов в паспорт
- Базовый интерфейс

### **Неделя 3: Привязка игроков**
- Получение списка игроков из CoC API
- Интерфейс выбора игрока
- Сохранение привязок

### **Неделя 4: Контекстуальные команды**
- Middleware для определения контекста
- Команды с автоматическим выбором клана
- Настройки чатов

### **Неделя 5: Базовые достижения**
- Простые счетчики активности
- Начисление достижений
- Отображение в паспорте

### **Неделя 6: Тестирование и доработка**
- Исправление багов
- Оптимизация запросов
- Подготовка к продакшену

---

## 📊 **Критерии успеха MVP**

### **Пользовательские метрики:**
- ✅ 90%+ команд работают с правильным контекстом клана
- ✅ Время создания паспорта < 2 минут
- ✅ Успешная привязка игроков без ошибок
- ✅ Корректное отображение достижений

### **Технические метрики:**
- ✅ Время ответа команд < 3 секунд
- ✅ 0 критических ошибок БД
- ✅ Стабильность работы 99%+
- ✅ Корректная работа с CoC API

### **Бизнес метрики:**
- 📈 50%+ пользователей создают паспорта
- 📈 Увеличение активности в чатах на 30%
- 📈 Снижение вопросов "как посмотреть статистику" на 70%