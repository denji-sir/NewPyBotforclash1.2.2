# 🏰 Система привязки кланов к боту - Фаза 1

## 🎯 **Цель фазы**

Создать базовую систему регистрации кланов администраторами, которая станет основой для всех последующих функций бота (паспорта, команды, статистика).

---

## 📋 **Техническое задание**

### **Что должно работать после этой фазы:**
✅ Администраторы чатов могут регистрировать кланы  
✅ Бот проверяет существование клана через CoC API  
✅ Кланы сохраняются в SQLite базе данных  
✅ Базовые команды для управления зарегистрированными кланами  
✅ Валидация прав администратора  

---

## 🗄️ **Структура базы данных SQLite**

### **1. Таблица зарегистрированных кланов**
```sql
-- Основная таблица для хранения зарегистрированных кланов
CREATE TABLE registered_clans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Основная информация о клане
    clan_tag TEXT UNIQUE NOT NULL,           -- #2PP0JCCL (уникальный тег клана)
    clan_name TEXT NOT NULL,                 -- Russians Kings
    clan_description TEXT,                   -- Описание клана из CoC
    clan_level INTEGER DEFAULT 1,            -- Уровень клана
    clan_points INTEGER DEFAULT 0,           -- Очки клана
    member_count INTEGER DEFAULT 0,          -- Количество участников
    
    -- Информация о регистрации
    chat_id INTEGER NOT NULL,                -- ID Telegram чата где зарегистрирован
    registered_by INTEGER NOT NULL,          -- user_id администратора
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Настройки и статус
    is_active BOOLEAN DEFAULT TRUE,          -- Активен ли клан
    is_verified BOOLEAN DEFAULT TRUE,        -- Подтвержден ли клан
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Дополнительные данные (JSON для гибкости)
    clan_metadata TEXT DEFAULT '{}',         -- Дополнительная информация в JSON
    
    -- Ограничения и индексы
    UNIQUE(clan_tag),
    INDEX idx_clan_chat (chat_id),
    INDEX idx_clan_active (is_active),
    INDEX idx_clan_tag (clan_tag)
);
```

### **2. Таблица настроек чатов**
```sql
-- Настройки для каждого чата
CREATE TABLE chat_clan_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Основная информация
    chat_id INTEGER UNIQUE NOT NULL,         -- ID Telegram чата
    chat_title TEXT,                         -- Название чата
    
    -- Настройки кланов
    default_clan_id INTEGER,                 -- ID основного клана чата
    max_clans_per_chat INTEGER DEFAULT 10,   -- Максимум кланов на чат
    
    -- Настройки отображения
    show_clan_numbers BOOLEAN DEFAULT TRUE,  -- Показывать номера кланов (1, 2, 3...)
    auto_detect_clan BOOLEAN DEFAULT TRUE,   -- Автоопределение клана по паспорту
    
    -- Разрешения
    admin_only_registration BOOLEAN DEFAULT TRUE, -- Только админы могут регистрировать
    
    -- Временные метки
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (default_clan_id) REFERENCES registered_clans(id),
    
    -- Индексы
    UNIQUE(chat_id)
);
```

### **3. Таблица логов операций**
```sql
-- Логи всех операций с кланами для аудита
CREATE TABLE clan_operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Основная информация
    operation_type TEXT NOT NULL,            -- 'register', 'update', 'deactivate', 'verify'
    clan_id INTEGER,                         -- ID клана (если применимо)
    clan_tag TEXT,                          -- Тег клана
    
    -- Контекст операции
    chat_id INTEGER NOT NULL,               -- В каком чате произошла операция
    user_id INTEGER NOT NULL,               -- Кто выполнил операцию
    username TEXT,                          -- Username пользователя
    
    -- Детали операции
    operation_details TEXT,                 -- JSON с деталями операции
    result TEXT NOT NULL,                   -- 'success', 'error', 'partial'
    error_message TEXT,                     -- Текст ошибки (если есть)
    
    -- Временная метка
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Индексы
    INDEX idx_logs_clan (clan_id),
    INDEX idx_logs_chat (chat_id),
    INDEX idx_logs_user (user_id),
    INDEX idx_logs_operation (operation_type),
    INDEX idx_logs_date (created_at)
);
```

---

## ⚙️ **Основные команды**

### **1. Регистрация клана - `/register_clan`**

**Синтаксис:** `/register_clan #CLANTAG [описание]`

**Пример использования:**
```
/register_clan #2PP0JCCL Основной клан нашего сообщества
```

**Алгоритм работы:**
```python
async def register_clan_command(message: Message, command: CommandObject):
    # 1. Проверка прав администратора
    if not await is_chat_admin(message.from_user.id, message.chat.id):
        return await message.reply("❌ Только администраторы могут регистрировать кланы")
    
    # 2. Парсинг аргументов
    clan_tag = command.args.split()[0] if command.args else None
    description = " ".join(command.args.split()[1:]) if len(command.args.split()) > 1 else None
    
    # 3. Валидация тега клана
    if not clan_tag or not clan_tag.startswith('#'):
        return await message.reply("❌ Укажите корректный тег клана: /register_clan #CLANTAG")
    
    # 4. Проверка лимитов
    clan_count = await get_chat_clan_count(message.chat.id)
    if clan_count >= 10:  # Лимит на чат
        return await message.reply("❌ Достигнут лимит кланов для этого чата (10)")
    
    # 5. Проверка существования в CoC API
    try:
        clan_data = await coc_api.get_clan(clan_tag)
    except ClanNotFound:
        return await message.reply(f"❌ Клан {clan_tag} не найден в Clash of Clans")
    except ApiError as e:
        return await message.reply(f"❌ Ошибка CoC API: {e}")
    
    # 6. Проверка что клан уже не зарегистрирован
    if await is_clan_registered(clan_tag):
        existing_chat = await get_clan_chat(clan_tag)
        return await message.reply(f"❌ Клан {clan_tag} уже зарегистрирован в чате {existing_chat}")
    
    # 7. Сохранение в базу данных
    try:
        clan_id = await register_clan_in_db(
            clan_tag=clan_tag,
            clan_data=clan_data,
            chat_id=message.chat.id,
            registered_by=message.from_user.id,
            description=description
        )
        
        # 8. Логирование операции
        await log_clan_operation(
            operation_type='register',
            clan_id=clan_id,
            clan_tag=clan_tag,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            username=message.from_user.username,
            result='success'
        )
        
        # 9. Успешный ответ
        await message.reply(
            f"✅ Клан успешно зарегистрирован!\n\n"
            f"🏰 {clan_data.name} ({clan_tag})\n"
            f"📊 Уровень: {clan_data.level}\n"
            f"👥 Участников: {len(clan_data.members)}/{clan_data.member_count}\n"
            f"🏆 Очки: {clan_data.points:,}\n\n"
            f"Теперь участники могут создавать паспорта с этим кланом!"
        )
        
    except DatabaseError as e:
        await log_clan_operation(
            operation_type='register',
            clan_tag=clan_tag,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            result='error',
            error_message=str(e)
        )
        await message.reply(f"❌ Ошибка базы данных: {e}")
```

### **2. Список кланов - `/clan_list`**

**Алгоритм работы:**
```python
async def clan_list_command(message: Message):
    clans = await get_chat_clans(message.chat.id, active_only=True)
    
    if not clans:
        return await message.reply(
            "📝 В этом чате нет зарегистрированных кланов.\n\n"
            "Администраторы могут добавить клан командой:\n"
            "/register_clan #CLANTAG"
        )
    
    # Формирование списка
    text = "🏰 **Зарегистрированные кланы:**\n\n"
    
    for i, clan in enumerate(clans, 1):
        status_emoji = "✅" if clan.is_active else "⏸️"
        default_mark = "⭐" if clan.id == await get_default_clan_id(message.chat.id) else ""
        
        text += (
            f"{i}. {status_emoji} **{clan.clan_name}** {default_mark}\n"
            f"   🏷️ {clan.clan_tag}\n"
            f"   📊 Уровень {clan.clan_level} | 👥 {clan.member_count} участников\n"
            f"   📅 Добавлен {format_date(clan.registered_at)}\n\n"
        )
    
    text += (
        f"📊 **Всего кланов:** {len(clans)}/10\n\n"
        f"💡 **Команды:**\n"
        f"• `/clan_info <номер>` - подробная информация\n"
        f"• `/set_default_clan <номер>` - установить основной\n"
        f"• `/update_clan <номер>` - обновить данные"
    )
    
    await message.reply(text, parse_mode='Markdown')
```

### **3. Информация о клане - `/clan_info`**

**Синтаксис:** `/clan_info [номер|тег]`

**Примеры:**
```
/clan_info 1           # Первый клан из списка
/clan_info #2PP0JCCL   # По тегу клана
/clan_info             # Основной клан чата
```

### **4. Установка основного клана - `/set_default_clan`**

**Синтаксис:** `/set_default_clan <номер>`

**Пример:** `/set_default_clan 2`

### **5. Обновление данных клана - `/update_clan`**

**Синтаксис:** `/update_clan <номер>`

Обновляет информацию о клане из CoC API (название, уровень, количество участников и т.д.)

---

## 🔧 **Технические компоненты**

### **1. CoC API интеграция**

```python
class CocApiService:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.rate_limiter = AsyncRateLimiter(35, 1)  # 35 req/sec
    
    async def get_clan(self, clan_tag: str) -> ClanData:
        """Получить информацию о клане из CoC API"""
        async with self.rate_limiter:
            try:
                # Нормализация тега (убрать # если есть, добавить если нет)
                normalized_tag = clan_tag.replace('#', '')
                
                # Выполнение запроса
                response = await self.make_api_request(f'/clans/%23{normalized_tag}')
                
                return ClanData(
                    tag=response['tag'],
                    name=response['name'],
                    description=response.get('description', ''),
                    level=response.get('clanLevel', 1),
                    points=response.get('clanPoints', 0),
                    member_count=response.get('members', 0),
                    war_wins=response.get('warWins', 0),
                    war_win_streak=response.get('warWinStreak', 0),
                    location=response.get('location', {}).get('name', 'Unknown'),
                    badge_url=response.get('badgeUrls', {}).get('medium', '')
                )
                
            except aiohttp.ClientResponseError as e:
                if e.status == 404:
                    raise ClanNotFound(f"Клан {clan_tag} не найден")
                elif e.status == 429:
                    await self.rotate_api_key()
                    raise ApiRateLimited("Превышен лимит запросов к API")
                else:
                    raise ApiError(f"Ошибка API: {e.status}")
    
    async def rotate_api_key(self):
        """Ротация API ключей при превышении лимита"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Rotated to API key index: {self.current_key_index}")
```

### **2. База данных сервис**

```python
class ClanDatabaseService:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def register_clan(self, clan_data: ClanData, chat_id: int, 
                          registered_by: int, description: str = None) -> int:
        """Регистрация клана в базе данных"""
        
        async with aiosqlite.connect(self.db_path) as db:
            # Проверка существования клана
            existing = await db.fetchone(
                "SELECT id FROM registered_clans WHERE clan_tag = ?",
                (clan_data.tag,)
            )
            
            if existing:
                raise ClanAlreadyRegistered(f"Клан {clan_data.tag} уже зарегистрирован")
            
            # Вставка данных
            cursor = await db.execute("""
                INSERT INTO registered_clans (
                    clan_tag, clan_name, clan_description, clan_level,
                    clan_points, member_count, chat_id, registered_by,
                    clan_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clan_data.tag,
                clan_data.name,
                description or clan_data.description,
                clan_data.level,
                clan_data.points,
                clan_data.member_count,
                chat_id,
                registered_by,
                json.dumps({
                    'war_wins': clan_data.war_wins,
                    'war_win_streak': clan_data.war_win_streak,
                    'location': clan_data.location,
                    'badge_url': clan_data.badge_url
                })
            ))
            
            await db.commit()
            return cursor.lastrowid
    
    async def get_chat_clans(self, chat_id: int, active_only: bool = True) -> List[ClanInfo]:
        """Получить все кланы чата"""
        
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT id, clan_tag, clan_name, clan_level, member_count,
                       is_active, registered_at, clan_metadata
                FROM registered_clans 
                WHERE chat_id = ?
            """
            params = [chat_id]
            
            if active_only:
                query += " AND is_active = 1"
            
            query += " ORDER BY registered_at"
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            return [ClanInfo.from_db_row(row) for row in rows]
    
    async def update_clan_data(self, clan_id: int, clan_data: ClanData):
        """Обновление данных клана из CoC API"""
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE registered_clans SET
                    clan_name = ?,
                    clan_level = ?,
                    clan_points = ?,
                    member_count = ?,
                    last_updated = CURRENT_TIMESTAMP,
                    clan_metadata = ?
                WHERE id = ?
            """, (
                clan_data.name,
                clan_data.level,
                clan_data.points,
                clan_data.member_count,
                json.dumps({
                    'war_wins': clan_data.war_wins,
                    'war_win_streak': clan_data.war_win_streak,
                    'location': clan_data.location,
                    'badge_url': clan_data.badge_url
                }),
                clan_id
            ))
            
            await db.commit()
```

### **3. Валидация и права доступа**

```python
class PermissionService:
    async def is_chat_admin(self, user_id: int, chat_id: int) -> bool:
        """Проверка является ли пользователь администратором чата"""
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            return member.status in ['creator', 'administrator']
        except Exception:
            return False
    
    async def can_register_clans(self, user_id: int, chat_id: int) -> bool:
        """Может ли пользователь регистрировать кланы"""
        # Проверяем настройки чата
        settings = await self.get_chat_settings(chat_id)
        
        if settings.admin_only_registration:
            return await self.is_chat_admin(user_id, chat_id)
        else:
            return True  # Все участники могут регистрировать
    
    async def can_manage_clan(self, user_id: int, clan_id: int) -> bool:
        """Может ли пользователь управлять кланом"""
        clan = await self.get_clan_by_id(clan_id)
        
        # Администраторы чата могут управлять всеми кланами
        if await self.is_chat_admin(user_id, clan.chat_id):
            return True
        
        # Тот кто зарегистрировал клан может им управлять
        if clan.registered_by == user_id:
            return True
        
        return False
```

---

## 🧪 **План тестирования**

### **1. Юнит-тесты**
- ✅ Валидация тегов кланов
- ✅ Парсинг команд
- ✅ База данных операции
- ✅ CoC API интеграция
- ✅ Проверка прав доступа

### **2. Интеграционные тесты**
- ✅ Регистрация клана end-to-end
- ✅ Обработка ошибок CoC API
- ✅ Лимиты и ограничения
- ✅ Команды управления кланами

### **3. Ручное тестирование**
```
Сценарий 1: Регистрация клана админом
1. Админ вводит /register_clan #2PP0JCCL
2. Бот проверяет права → OK
3. Бот обращается к CoC API → OK
4. Бот сохраняет в БД → OK
5. Бот отвечает успехом → OK

Сценарий 2: Попытка регистрации не-админом
1. Пользователь вводит /register_clan #ABC123
2. Бот проверяет права → FAIL
3. Бот отвечает ошибкой прав доступа → OK

Сценарий 3: Регистрация несуществующего клана
1. Админ вводит /register_clan #INVALID
2. Бот проверяет права → OK  
3. Бот обращается к CoC API → 404 Error
4. Бот отвечает "клан не найден" → OK
```

---

## 📊 **Критерии готовности**

### **Обязательные функции:**
- [x] Команда `/register_clan` работает корректно
- [x] Интеграция с CoC API для проверки кланов
- [x] Сохранение в SQLite базу данных
- [x] Валидация прав администратора
- [x] Команда `/clan_list` показывает зарегистрированные кланы
- [x] Команда `/clan_info` показывает детальную информацию
- [x] Логирование всех операций
- [x] Обработка основных ошибок

### **Показатели производительности:**
- Время ответа команд < 5 секунд
- Выдерживание лимитов CoC API (35 req/sec)
- 0 критических ошибок базы данных
- Корректная обработка 95% запросов

### **Готовность к следующей фазе:**
- Минимум 3 клана успешно зарегистрированы в тестовом чате
- Все основные команды работают без ошибок
- База данных стабильна и содержит корректные данные
- Документация обновлена

---

## 🚀 **Следующие шаги**

После завершения этой фазы переходим к:

**Фаза 2:** Базовые команды для работы с кланами  
**Фаза 3:** Система создания паспортов  
**Фаза 4:** Привязка игроков к паспортам  
**Фаза 5:** Контекстуальная система команд  

Система привязки кланов - это фундамент, на котором будут строиться все остальные функции бота!