# 🏰 Статус системы работы с кланами

## ✅ Что реализовано

### Регистрация и управление кланами
- ✅ `/register_clan #CLANTAG` - регистрация клана администраторами
- ✅ `/clan_list` - список всех кланов чата
- ✅ `/clan_info <номер>` - информация о клане по номеру
- ✅ `/set_default_clan <номер>` - установка основного клана
- ✅ Автоматическое определение первого клана как основного
- ✅ Хранение кланов в БД с привязкой к чату

### Команды статистики (работают только с основным кланом)
- ✅ `/war` - текущая война основного клана
- ✅ `/raids` - рейды основного клана  
- ✅ `/leadership` - руководство основного клана
- ✅ `/top_donors` - топ донатеров основного клана
- ✅ `/cwl` - ЛВК основного клана

---

## ❌ Что НЕ работает (требует доработки)

### Доступ к статистике других кланов
- ❌ `/war 2` - война клана №2 (не реализовано)
- ❌ `/raids 3` - рейды клана №3 (не реализовано)
- ❌ `/leadership wa` - руководство по первым буквам (не реализовано)
- ❌ Парсинг номера/букв клана в командах

---

## 🔧 Что нужно добавить

### Функция парсинга клана из аргументов

```python
async def get_clan_from_args(chat_id: int, args: str = None) -> Optional[ClanInfo]:
    """
    Получить клан по аргументу команды
    
    Args:
        chat_id: ID чата
        args: Аргумент команды (номер или первые буквы)
        
    Returns:
        ClanInfo или None
    """
    clans = await db_service.get_chat_clans(chat_id)
    
    if not clans:
        return None
    
    # Если аргумент не указан - возвращаем основной клан
    if not args:
        settings = await db_service.get_chat_settings(chat_id)
        if settings.default_clan_id:
            return await db_service.get_clan_by_id(settings.default_clan_id)
        return clans[0]  # Первый клан
    
    # Проверяем, является ли аргумент номером
    if args.isdigit():
        clan_number = int(args)
        if 1 <= clan_number <= len(clans):
            return clans[clan_number - 1]
    
    # Проверяем по первым буквам названия
    args_lower = args.lower()
    for clan in clans:
        if clan.clan_name.lower().startswith(args_lower):
            return clan
    
    return None
```

### Обновить команды

Нужно обновить файл `bot/handlers/extended_clash_commands.py`:

**Команды для обновления:**
1. `cmd_current_war` - `/war [номер|буквы]`
2. `cmd_capital_raids` - `/raids [номер|буквы]`
3. `cmd_leadership` - `/leadership [номер|буквы]`
4. `cmd_top_donors` - `/top_donors [номер|буквы]`

**Пример обновления:**
```python
@extended_router.message(Command("war"))
async def cmd_current_war(message: Message, command: CommandObject):
    """Текущая война клана"""
    
    # Получаем клан по аргументу (номер/буквы) или основной
    clan = await get_clan_from_args(message.chat.id, command.args)
    
    if not clan:
        await message.reply(
            "❌ Клан не найден!\n\n"
            "Используйте:\n"
            "• `/war` - основной клан\n"
            "• `/war 2` - клан №2\n"
            "• `/war wa` - клан по первым буквам\n"
            "• `/clan_list` - список кланов"
        )
        return
    
    clan_tag = clan.clan_tag
    
    # Далее код как раньше...
```

---

## 📊 Приоритет задачи

**Приоритет: ВЫСОКИЙ**

Это критичная функция для работы с несколькими кланами. Без неё пользователи не могут просматривать статистику кланов 2, 3, 4, 5.

**Время на реализацию:** 2-3 часа

**Файлы для изменения:**
- `bot/handlers/extended_clash_commands.py` (основной)
- `bot/utils/clan_helpers.py` (добавить функцию парсинга)

---

## ✅ После реализации будет работать

- `/war` → война основного клана
- `/war 2` → война клана №2
- `/war 3` → война клана №3
- `/raids wa` → рейды клана "Warriors"
- `/leadership ru` → руководство клана "Russian"
- `/top_donors 1` → донаты клана №1

**Полное соответствие требованиям чек-листа!**
