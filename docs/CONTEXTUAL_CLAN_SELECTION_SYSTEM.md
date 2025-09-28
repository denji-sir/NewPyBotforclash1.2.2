# Система контекстуального выбора кланов NewPyBot v1.2.2

## 🎯 Концепция системы

### Основная идея

**Умный контекстуальный выбор** - система автоматически определяет подходящий клан для каждой команды на основе паспорта пользователя, при этом позволяя легко переключаться между зарегистрированными кланами чата.

### Принципы работы

1. 🎯 **Автоматическое определение** - если у пользователя есть паспорт, показываем статистику его клана
2. 🔢 **Простое переключение** - добавление номера к команде для выбора другого клана  
3. ⚙️ **Настройка по умолчанию** - каждый чат имеет основной клан для неверифицированных пользователей
4. 📋 **Понятная нумерация** - кланы пронумерованы в порядке регистрации
5. 🎨 **Удобный интерфейс** - пользователи всегда видят список доступных кланов

---

## 🏗️ Архитектура системы

### Расширенная схема БД

```sql
-- Настройки кланов для чатов  
CREATE TABLE chat_clan_settings (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    registered_clan_id INTEGER NOT NULL,  -- ID из registered_clans
    clan_number INTEGER NOT NULL,         -- Номер клана в чате (1, 2, 3...)
    is_default BOOLEAN DEFAULT FALSE,     -- Основной клан чата
    display_name VARCHAR(100),            -- Альтернативное название для отображения
    added_at TIMESTAMP DEFAULT NOW(),
    added_by BIGINT NOT NULL,            -- Кто добавил клан в чат
    
    UNIQUE(chat_id, clan_number),        -- Уникальные номера в чате
    UNIQUE(chat_id, registered_clan_id), -- Клан не может быть дважды в одном чате
    FOREIGN KEY (registered_clan_id) REFERENCES registered_clans(id) ON DELETE CASCADE,
    INDEX idx_chat_clans (chat_id, clan_number),
    INDEX idx_default_clan (chat_id, is_default)
);

-- Дополнительная таблица для кеша информации о кланах в чатах
CREATE TABLE chat_clan_cache (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    clan_number INTEGER NOT NULL,
    clan_tag VARCHAR(15) NOT NULL,
    clan_name VARCHAR(100) NOT NULL,
    member_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(chat_id, clan_number),
    INDEX idx_chat_cache (chat_id)
);
```

### Логика определения контекстного клана

```python
class ClanContextManager:
    def __init__(self, db_connection):
        self.db = db_connection
        
    async def resolve_clan_context(self, chat_id: int, user_id: int, 
                                 explicit_number: Optional[int] = None) -> Dict:
        """
        Определение контекстного клана для команды
        
        Приоритеты:
        1. Явно указанный номер клана (explicit_number)
        2. Клан привязанного игрока (если есть паспорт)
        3. Основной клан чата (по умолчанию)
        """
        
        # Получаем список кланов чата
        chat_clans = await self.get_chat_clans(chat_id)
        
        if not chat_clans:
            raise ValueError("В этом чате нет зарегистрированных кланов")
            
        # 1. Явно указанный номер клана
        if explicit_number is not None:
            if explicit_number < 1 or explicit_number > len(chat_clans):
                raise ValueError(f"Некорректный номер клана. Доступны: 1-{len(chat_clans)}")
                
            selected_clan = chat_clans[explicit_number - 1]
            return {
                'clan_tag': selected_clan['clan_tag'],
                'clan_name': selected_clan['clan_name'],
                'selection_method': 'explicit',
                'clan_number': explicit_number,
                'available_clans': chat_clans
            }
        
        # 2. Клан привязанного игрока
        user_clan = await self.get_user_clan_context(user_id, chat_clans)
        if user_clan:
            return user_clan
            
        # 3. Основной клан чата
        default_clan = next((clan for clan in chat_clans if clan['is_default']), chat_clans[0])
        
        return {
            'clan_tag': default_clan['clan_tag'],
            'clan_name': default_clan['clan_name'],
            'selection_method': 'default',
            'clan_number': default_clan['clan_number'],
            'available_clans': chat_clans
        }
    
    async def get_user_clan_context(self, user_id: int, chat_clans: List[Dict]) -> Optional[Dict]:
        """Получить клан пользователя на основе его паспорта"""
        
        # Получаем привязанного игрока
        user_binding = await self.db.fetch_one("""
            SELECT player_tag, clan_tag FROM user_player_bindings 
            WHERE user_id = ? AND is_active = TRUE
        """, (user_id,))
        
        if not user_binding:
            return None
            
        # Ищем клан пользователя среди зарегистрированных в чате
        user_clan_tag = user_binding['clan_tag']
        
        for clan in chat_clans:
            if clan['clan_tag'] == user_clan_tag:
                return {
                    'clan_tag': clan['clan_tag'],
                    'clan_name': clan['clan_name'], 
                    'selection_method': 'user_clan',
                    'clan_number': clan['clan_number'],
                    'available_clans': chat_clans,
                    'user_player_tag': user_binding['player_tag']
                }
        
        return None
    
    async def get_chat_clans(self, chat_id: int) -> List[Dict]:
        """Получить список всех кланов чата"""
        
        return await self.db.fetch_all("""
            SELECT 
                ccs.clan_number,
                ccs.is_default,
                ccs.display_name,
                rc.clan_tag,
                rc.clan_name,
                rc.id as registered_clan_id
            FROM chat_clan_settings ccs
            JOIN registered_clans rc ON ccs.registered_clan_id = rc.id
            WHERE ccs.chat_id = ? AND rc.is_active = TRUE
            ORDER BY ccs.clan_number ASC
        """, (chat_id,))
```

---

## 🎮 Примеры команд с контекстным выбором

### Базовые команды статистики

#### `/wars` - Статистика войн
```python
async def cmd_wars(message: Message):
    """Статистика войн с контекстным выбором клана"""
    
    # Парсим аргументы команды
    args = message.text.split()[1:]
    clan_number = None
    
    if args and args[0].isdigit():
        clan_number = int(args[0])
    
    # Определяем контекстный клан
    try:
        clan_context = await clan_manager.resolve_clan_context(
            message.chat.id, 
            message.from_user.id, 
            clan_number
        )
    except ValueError as e:
        await message.reply(str(e))
        return
    
    # Получаем статистику войн для выбранного клана
    wars_data = await get_clan_wars_stats(clan_context['clan_tag'])
    
    # Формируем ответ
    text = f"""
⚔️ **Статистика войн**
🏰 **{clan_context['clan_name']}** (#{clan_context['clan_number']})

📊 **Текущие войны:**
• Активных войн: {wars_data['active_wars']}
• Статус: {wars_data['war_status']}
• До окончания: {wars_data['time_remaining']}

📈 **Общая статистика:**
• Побед: {wars_data['wins']} 
• Поражений: {wars_data['losses']}
• Винрейт: {wars_data['win_rate']:.1f}%

👥 **Участие:**
• Атак сделано: {wars_data['attacks_used']}/{wars_data['attacks_total']}
• Звезд получено: {wars_data['stars_earned']}
• Процент разрушения: {wars_data['destruction_percentage']:.1f}%
"""
    
    # Добавляем информацию о доступных кланах
    if len(clan_context['available_clans']) > 1:
        text += f"\n🔢 **Другие кланы:**\n"
        for clan in clan_context['available_clans']:
            if clan['clan_number'] != clan_context['clan_number']:
                text += f"• {clan['clan_number']}. {clan['clan_name']}\n"
        text += f"\n💡 Используйте `/wars {'{номер}'}` для другого клана"
    
    await message.reply(text, parse_mode='Markdown')
```

#### `/raids` - Статистика Capital Raids
```python
async def cmd_raids(message: Message):
    """Статистика Capital Raids с контекстным выбором"""
    
    args = message.text.split()[1:]
    clan_number = None
    
    if args and args[0].isdigit():
        clan_number = int(args[0])
    
    clan_context = await clan_manager.resolve_clan_context(
        message.chat.id, message.from_user.id, clan_number
    )
    
    raids_data = await get_clan_capital_raids_stats(clan_context['clan_tag'])
    
    # Специальное отображение для владельцев паспортов
    personal_stats = ""
    if clan_context.get('user_player_tag'):
        user_raids = await get_player_raids_stats(clan_context['user_player_tag'])
        personal_stats = f"""
👤 **Ваша статистика:**
• Атак использовано: {user_raids['attacks_used']}/6
• Урон нанесен: {user_raids['damage_dealt']:,}
• Место в клане: {user_raids['clan_rank']}
"""
    
    text = f"""
🏛️ **Capital Raids**
🏰 **{clan_context['clan_name']}** (#{clan_context['clan_number']})

📊 **Текущий рейд:**
• Статус: {raids_data['current_status']}
• Районов завершено: {raids_data['districts_completed']}/6
• Общий урон: {raids_data['total_damage']:,}
• Участников: {raids_data['participants']}

🏆 **Результаты:**
• Capital Gold заработано: {raids_data['gold_earned']:,}
• Рейд медали: {raids_data['raid_medals']}
• Место среди противников: {raids_data['leaderboard_position']}

{personal_stats}

💎 **Capital Hall:** Уровень {raids_data['capital_hall_level']}
"""
    
    if len(clan_context['available_clans']) > 1:
        text += f"\n🔢 Другие кланы: "
        other_clans = [str(c['clan_number']) for c in clan_context['available_clans'] 
                      if c['clan_number'] != clan_context['clan_number']]
        text += ", ".join(other_clans)
        text += f" | `/raids {'{номер}'}`"
    
    await message.reply(text, parse_mode='Markdown')
```

### Команды управления

#### `/set_default_clan <номер>` - Установка основного клана
```python
async def cmd_set_default_clan(message: Message):
    """Установка основного клана чата (только для админов)"""
    
    # Проверяем права администратора
    if not await is_chat_admin(message.from_user.id, message.chat.id):
        await message.reply("Только администраторы могут менять основной клан чата")
        return
    
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.reply("Укажите номер клана: `/set_default_clan 2`")
        return
    
    clan_number = int(args[0])
    
    # Получаем кланы чата
    chat_clans = await clan_manager.get_chat_clans(message.chat.id)
    
    if clan_number < 1 or clan_number > len(chat_clans):
        await message.reply(f"Некорректный номер. Доступны: 1-{len(chat_clans)}")
        return
    
    # Обновляем основной клан
    await clan_manager.set_default_clan(message.chat.id, clan_number)
    
    selected_clan = next(c for c in chat_clans if c['clan_number'] == clan_number)
    
    await message.reply(f"""
✅ **Основной клан обновлен**

🏰 **{selected_clan['clan_name']}** теперь клан по умолчанию

💡 Пользователи без паспорта будут видеть статистику этого клана
    """, parse_mode='Markdown')
```

#### `/add_clan_to_chat <тег_клана>` - Добавление клана в чат
```python
async def cmd_add_clan_to_chat(message: Message):
    """Добавление зарегистрированного клана в чат"""
    
    if not await is_chat_admin(message.from_user.id, message.chat.id):
        await message.reply("Только администраторы могут добавлять кланы в чат")
        return
    
    args = message.text.split()[1:]
    if not args:
        await message.reply("Укажите тег клана: `/add_clan_to_chat #ABC123`")
        return
    
    clan_tag = args[0].upper()
    if not clan_tag.startswith('#'):
        clan_tag = '#' + clan_tag
    
    # Проверяем, что клан зарегистрирован
    registered_clan = await get_registered_clan_by_tag(clan_tag)
    if not registered_clan:
        await message.reply(f"Клан {clan_tag} не зарегистрирован в системе")
        return
    
    # Проверяем, что клан не добавлен в чат
    existing_clans = await clan_manager.get_chat_clans(message.chat.id)
    if any(c['clan_tag'] == clan_tag for c in existing_clans):
        await message.reply(f"Клан {clan_tag} уже добавлен в этот чат")
        return
    
    # Добавляем клан в чат
    clan_number = len(existing_clans) + 1
    is_default = len(existing_clans) == 0  # Первый клан - основной
    
    await clan_manager.add_clan_to_chat(
        message.chat.id, 
        registered_clan['id'], 
        clan_number,
        is_default,
        message.from_user.id
    )
    
    await message.reply(f"""
✅ **Клан добавлен в чат**

🏰 **{registered_clan['clan_name']}** ({clan_tag})
🔢 Номер в чате: **{clan_number}**
{'⭐ Основной клан' if is_default else ''}

💡 Теперь пользователи могут использовать:
• `/wars {clan_number}` - статистика войн
• `/raids {clan_number}` - Capital Raids  
• `/members {clan_number}` - участники клана
    """, parse_mode='Markdown')
```

---

## 📋 Система отображения списка кланов

### Информационные команды

#### `/clans` - Список кланов чата
```python
async def cmd_clans(message: Message):
    """Показать все кланы, подключенные к чату"""
    
    chat_clans = await clan_manager.get_chat_clans(message.chat.id)
    
    if not chat_clans:
        await message.reply("""
❌ **В этом чате нет подключенных кланов**

👑 Администраторы могут добавить кланы:
• `/add_clan_to_chat #TAG` - добавить клан
• `/register_clan #TAG` - зарегистрировать новый клан
        """)
        return
    
    # Получаем статистику каждого клана
    clan_stats = []
    for clan in chat_clans:
        stats = await get_basic_clan_stats(clan['clan_tag'])
        clan_stats.append({**clan, **stats})
    
    text = f"🏰 **Кланы чата** ({len(chat_clans)})\n\n"
    
    for clan in clan_stats:
        default_marker = "⭐ " if clan['is_default'] else ""
        text += f"""
{default_marker}**{clan['clan_number']}. {clan['clan_name']}**
• Тег: `{clan['clan_tag']}`
• Участников: {clan['member_count']}/50
• Очков: {clan['clan_points']:,}
• Лига: {clan['war_league']}
"""
    
    text += f"""
💡 **Как использовать:**
• `/wars` - статистика войн основного клана
• `/wars 2` - статистика войн клана №2
• `/raids 3` - Capital Raids клана №3

🎯 **Автоматический выбор:**
Если у вас есть паспорт, бот автоматически покажет статистику вашего клана
    """
    
    await message.reply(text, parse_mode='Markdown')
```

### Интеграция с системой паспортов

#### Обновление команд паспорта
```python
async def cmd_my_passport(message: Message):
    """Показать паспорт с информацией о контексте"""
    
    user_id = message.from_user.id
    passport = await get_user_passport(user_id)
    
    if not passport:
        await message.reply("У вас нет паспорта. Создать: /create_passport")
        return
    
    # Получаем информацию о привязанном игроке
    binding = await get_user_binding(user_id)
    
    text = f"""
📋 **Мой паспорт**
👤 **{binding['player_name']}** ✅ (`{binding['player_tag']}`)
🏰 Клан: **{binding['clan_name']}** (`{binding['clan_tag']}`)

🎯 **Автоматический контекст:**
Когда вы используете команды статистики без номера клана, 
бот автоматически покажет данные вашего клана.

📊 **Доступные команды:**
• `/my_profile` - мой профиль игрока
• `/my_progress` - мой прогресс
• `/wars` - войны моего клана
• `/raids` - рейды моего клана

🔢 **Другие кланы чата:**
Добавьте номер к команде для просмотра других кланов
Например: `/wars 2`, `/raids 3`
"""
    
    # Показываем доступные кланы в текущем чате
    chat_clans = await clan_manager.get_chat_clans(message.chat.id)
    if len(chat_clans) > 1:
        text += f"\n🏰 **Кланы в этом чате:**\n"
        for clan in chat_clans:
            marker = "👤" if clan['clan_tag'] == binding['clan_tag'] else "🔢"
            text += f"{marker} {clan['clan_number']}. {clan['clan_name']}\n"
    
    await message.reply(text, parse_mode='Markdown')
```

---

## 🔧 Техническая реализация

### Middleware для обработки команд

```python
class ClanContextMiddleware:
    """Middleware для автоматического определения контекста клана"""
    
    def __init__(self, clan_manager: ClanContextManager):
        self.clan_manager = clan_manager
        
    async def __call__(self, handler, event: Message, data: Dict):
        """Обрабатываем команды с контекстом клана"""
        
        # Список команд, которые поддерживают контекст клана
        clan_context_commands = [
            'wars', 'raids', 'members', 'donations', 'clan_stats', 
            'war_log', 'capital_log', 'top_players'
        ]
        
        command = event.text.split()[0][1:] if event.text.startswith('/') else None
        
        if command in clan_context_commands:
            try:
                # Парсим номер клана из аргументов
                args = event.text.split()[1:]
                explicit_number = None
                
                if args and args[0].isdigit():
                    explicit_number = int(args[0])
                    # Удаляем номер из аргументов для дальнейшей обработки
                    event.text = ' '.join([event.text.split()[0]] + args[1:])
                
                # Определяем контекст клана
                clan_context = await self.clan_manager.resolve_clan_context(
                    event.chat.id, 
                    event.from_user.id, 
                    explicit_number
                )
                
                # Добавляем контекст в data для использования в handler'е
                data['clan_context'] = clan_context
                
            except ValueError as e:
                await event.reply(str(e))
                return
        
        # Продолжаем обработку
        return await handler(event, data)
```

### Кеширование данных кланов

```python
class ClanCacheManager:
    """Управление кешем данных кланов для быстрого доступа"""
    
    def __init__(self, redis_client, db_connection):
        self.redis = redis_client
        self.db = db_connection
        
    async def get_cached_clan_info(self, chat_id: int) -> List[Dict]:
        """Получить кешированную информацию о кланах чата"""
        
        cache_key = f"chat_clans:{chat_id}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # Если нет в кеше, загружаем из БД
        clan_data = await self._load_clan_data_from_db(chat_id)
        
        # Кешируем на 1 час
        await self.redis.setex(
            cache_key, 
            3600, 
            json.dumps(clan_data, default=str)
        )
        
        return clan_data
    
    async def _load_clan_data_from_db(self, chat_id: int) -> List[Dict]:
        """Загрузить данные кланов из БД с актуальной информацией"""
        
        chat_clans = await self.db.fetch_all("""
            SELECT 
                ccs.clan_number,
                ccs.is_default,
                rc.clan_tag,
                rc.clan_name,
                rc.last_updated
            FROM chat_clan_settings ccs
            JOIN registered_clans rc ON ccs.registered_clan_id = rc.id
            WHERE ccs.chat_id = ? AND rc.is_active = TRUE
            ORDER BY ccs.clan_number ASC
        """, (chat_id,))
        
        # Обогащаем данными из API (если нужно обновить)
        enriched_clans = []
        for clan in chat_clans:
            # Проверяем, нужно ли обновить данные клана
            if self._needs_update(clan['last_updated']):
                fresh_data = await self._fetch_clan_from_api(clan['clan_tag'])
                if fresh_data:
                    await self._update_clan_in_db(clan['clan_tag'], fresh_data)
                    enriched_clans.append({**clan, **fresh_data})
                else:
                    enriched_clans.append(clan)
            else:
                enriched_clans.append(clan)
                
        return enriched_clans
    
    def _needs_update(self, last_updated: datetime) -> bool:
        """Проверить, нужно ли обновлять данные клана"""
        return datetime.now() - last_updated > timedelta(hours=6)
```

---

## 🎯 Преимущества системы

### Для пользователей
- 🎯 **Умное поведение** - не нужно каждый раз указывать свой клан
- 🔢 **Простое переключение** - легко посмотреть статистику других кланов
- 📱 **Интуитивность** - система работает логично и предсказуемо
- 🎨 **Информативность** - всегда видно, какой клан выбран

### Для администраторов
- ⚙️ **Гибкая настройка** - можно настроить основной клан чата
- 📊 **Контроль** - администраторы управляют списком кланов
- 🔧 **Простое управление** - добавление/удаление кланов через команды

### Для системы
- 🚀 **Производительность** - кеширование данных кланов
- 📈 **Масштабируемость** - поддержка множества кланов в чате  
- 🔄 **Интеграция** - естественная работа с паспортами и метриками
- ⚡ **Отказоустойчивость** - graceful fallback на основной клан

Эта система делает взаимодействие с ботом намного удобнее и интуитивнее! 🚀