"""
Утилиты для форматирования данных в сообщениях
"""

from typing import Union, Dict, Any, List
from datetime import datetime


def format_war_info(war_data: Dict[str, Any]) -> str:
    """
    Форматирует информацию о текущей или прошлой войне клана.
    """
    if not war_data or 'state' not in war_data:
        return "Нет данных о войне."

    state = war_data['state']
    clan_name = war_data.get('clan', {}).get('name', 'Ваш клан')
    opponent_name = war_data.get('opponent', {}).get('name', 'Соперник')

    text = f"⚔️ **Война кланов: {clan_name} vs {opponent_name}**\n\n"

    if state == 'inWar':
        end_time = datetime.fromisoformat(war_data['endTime']).strftime('%H:%M %d.%m')
        text += f"**Статус:** В бою! 💥 (до {end_time})\n"
    elif state == 'warEnded':
        result = war_data.get('result', 'unknown')
        result_text = {"win": "Победа ✅", "lose": "Поражение ❌", "tie": "Ничья 🤝"}.get(result, "Завершена")
        text += f"**Статус:** Война окончена! Результат: **{result_text}**\n"
    else:
        text += f"**Статус:** {state}\n"

    clan_stars = war_data.get('clan', {}).get('stars', 0)
    opponent_stars = war_data.get('opponent', {}).get('stars', 0)
    clan_destruction = war_data.get('clan', {}).get('destructionPercentage', 0)
    opponent_destruction = war_data.get('opponent', {}).get('destructionPercentage', 0)

    text += f"⭐ **{clan_stars}** | {clan_destruction:.2f}%  -  {opponent_destruction:.2f}% | **{opponent_stars}** ⭐\n\n"
    
    # Лучшие атаки
    clan_attacks = sorted([m for m in war_data.get('clan', {}).get('members', []) if m.get('attacks')], key=lambda x: -x['attacks'][0]['stars'] if x.get('attacks') else 0)
    if clan_attacks:
        text += "**🔥 Лучшие атаки:**\n"
        for member in clan_attacks[:3]:
            if member.get('attacks'):
                attack = member['attacks'][0]
                stars = '⭐' * attack['stars'] + '⚫' * (3 - attack['stars'])
                text += f"- {member['name']}: {stars} ({attack['destructionPercentage']}%)\n"

    return text

def format_raid_info(raid_log: List[Dict[str, Any]], clan_tag: str) -> str:
    """
    Форматирует информацию о последнем рейде столицы.
    """
    if not raid_log:
        return "Нет данных о рейдах столицы."

    latest_raid = raid_log[0]
    start_time = datetime.fromisoformat(latest_raid['startTime']).strftime('%d.%m.%Y')
    total_loot = latest_raid.get('capitalTotalLoot', 0)

    text = f"⚔️ **Рейд столицы от {start_time}**\n\n"
    text += f"**Всего добыто:** {total_loot:,} 💎\n"
    text += f"**Проведено атак:** {latest_raid.get('totalAttacks', 0)}\n"
    text += f"**Уничтожено районов:** {latest_raid.get('districtsDestroyed', 0)}\n\n"

    # Топ участники
    members = sorted(latest_raid.get('members', []), key=lambda x: -x.get('capitalResourcesLooted', 0))
    if members:
        text += "**🏆 Топ участники:**\n"
        for member in members[:5]:
            loot = member.get('capitalResourcesLooted', 0)
            text += f"- {member['name']}: {loot:,} 💎\n"

    return text

def format_cwl_info(cwl_data: Dict[str, Any], clan_tag: str) -> str:
    """
    Форматирует информацию о текущей или последней КВЛ.
    """
    if not cwl_data or 'state' not in cwl_data:
        return "Нет данных о Лиге Войн Кланов."

    state = cwl_data['state']
    season = cwl_data.get('season', 'N/A')

    text = f"🏆 **Лига Войн Кланов (Сезон: {season})**\n\n"

    if state == 'inWar':
        text += "**Статус:** В бою! 🔥\n"
    elif state == 'ended':
        text += "**Статус:** Завершена ✅\n"
    else:
        text += f"**Статус:** {state}\n"

    # Информация о раундах
    rounds = cwl_data.get('rounds', [])
    if rounds:
        text += f"**Всего раундов:** {len(rounds)}\n"
        current_round_index = next((i for i, r in enumerate(rounds) if r['warTags'][0] != '#0'), -1)
        if current_round_index != -1:
            text += f"**Текущий раунд:** {current_round_index + 1}\n"

    # Информация о кланах в группе
    clans = cwl_data.get('clans', [])
    if clans:
        text += "\n**Участники группы:**\n"
        for clan in clans:
            clan_name = clan.get('name', 'Неизвестный клан')
            stars = 0
            # Найдем информацию о звездах для этого клана
            for r in rounds:
                for tag in r['warTags']:
                    # Логика для определения звезд (упрощенная)
                    pass # Тут нужна более сложная логика для парсинга войн
            text += f"- {clan_name}\n"

    return text


from typing import Union


def format_large_number(number: Union[int, float]) -> str:
    """
    Форматировать большие числа в читабельный вид
    
    Args:
        number: Число для форматирования
        
    Returns:
        str: Отформатированное число
        
    Examples:
        >>> format_large_number(1234)
        '1,234'
        >>> format_large_number(1234567)
        '1,234,567'
        >>> format_large_number(1000000)
        '1.0M'
        >>> format_large_number(1500000)
        '1.5M'
    """
    if number is None:
        return "0"
    
    number = int(number)
    
    # Для очень больших чисел используем сокращения
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    elif number >= 100_000:
        return f"{number / 1_000:.0f}K"
    elif number >= 10_000:
        return f"{number / 1_000:.1f}K"
    else:
        # Для чисел меньше 10K просто добавляем запятые
        return f"{number:,}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Форматировать процентное значение
    
    Args:
        value: Значение (0-100)
        decimals: Количество знаков после запятой
        
    Returns:
        str: Отформатированный процент
    """
    if value is None:
        return "0%"
    
    return f"{value:.{decimals}f}%"


def format_duration(seconds: int) -> str:
    """
    Форматировать продолжительность в читабельный вид
    
    Args:
        seconds: Продолжительность в секундах
        
    Returns:
        str: Отформатированная продолжительность
        
    Examples:
        >>> format_duration(3661)
        '1ч 1м'
        >>> format_duration(86400)
        '1д'
    """
    if seconds < 60:
        return f"{seconds}с"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}м"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        if remaining_minutes > 0:
            return f"{hours}ч {remaining_minutes}м"
        return f"{hours}ч"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    if remaining_hours > 0:
        return f"{days}д {remaining_hours}ч"
    return f"{days}д"


def format_trophy_range(min_trophies: int, max_trophies: int) -> str:
    """
    Форматировать диапазон кубков
    
    Args:
        min_trophies: Минимальные кубки
        max_trophies: Максимальные кубки
        
    Returns:
        str: Отформатированный диапазон
    """
    if min_trophies == max_trophies:
        return format_large_number(min_trophies)
    
    return f"{format_large_number(min_trophies)} - {format_large_number(max_trophies)}"


def format_war_size(team_size: int) -> str:
    """
    Форматировать размер войны
    
    Args:
        team_size: Размер команды
        
    Returns:
        str: Отформатированный размер войны
    """
    return f"{team_size} vs {team_size}"


def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    Обрезать текст до указанной длины с добавлением многоточия
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        
    Returns:
        str: Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def format_clan_role(role: str) -> str:
    """
    Форматировать роль в клане на русском
    
    Args:
        role: Роль в клане (английская)
        
    Returns:
        str: Роль на русском с эмодзи
    """
    role_map = {
        "leader": "👑 Лидер",
        "coLeader": "🔱 Со-лидер", 
        "admin": "⭐ Старейшина",
        "member": "👤 Участник"
    }
    
    return role_map.get(role, f"❓ {role}")


def format_league(league_name: str) -> str:
    """
    Форматировать название лиги
    
    Args:
        league_name: Название лиги
        
    Returns:
        str: Отформатированное название лиги
    """
    if not league_name:
        return "Без лиги"
    
    # Добавляем эмодзи для популярных лиг
    league_emojis = {
        "Unranked": "⚪",
        "Bronze": "🥉",
        "Silver": "🥈", 
        "Gold": "🥇",
        "Crystal": "💎",
        "Master": "👑",
        "Champion": "🏆",
        "Titan": "⚡",
        "Legend": "🌟"
    }
    
    for key, emoji in league_emojis.items():
        if key.lower() in league_name.lower():
            return f"{emoji} {league_name}"
    
    return league_name


def format_war_result(is_victory: bool = None) -> str:
    """
    Форматировать результат войны
    
    Args:
        is_victory: True для победы, False для поражения, None для ничьи
        
    Returns:
        str: Отформатированный результат
    """
    if is_victory is True:
        return "✅ Победа"
    elif is_victory is False:
        return "❌ Поражение"
    else:
        return "🤝 Ничья"


def format_build_hall_level(level: int) -> str:
    """
    Форматировать уровень ТХ
    
    Args:
        level: Уровень ТХ
        
    Returns:
        str: Отформатированный уровень ТХ
    """
    if level <= 0:
        return "❓ ТХ?"
    
    return f"🏠 ТХ{level}"


def escape_markdown(text: str) -> str:
    """
    Экранировать специальные символы для Markdown
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Экранированный текст
    """
    if not text:
        return ""
    
    # Символы, которые нужно экранировать в Markdown
    special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def safe_format_name(name: str) -> str:
    """
    Безопасно отформатировать имя игрока/клана для Markdown
    
    Args:
        name: Имя
        
    Returns:
        str: Безопасное имя для Markdown
    """
    if not name:
        return "???"
    
    # Убираем или заменяем проблемные символы
    # Оставляем только буквы, цифры, пробелы и некоторые символы
    safe_name = ""
    for char in name:
        if char.isalnum() or char in " -_.":
            safe_name += char
        else:
            safe_name += "_"
    
    return safe_name.strip()


def format_list_with_numbers(items: list, max_items: int = 10) -> str:
    """
    Форматировать список с нумерацией
    
    Args:
        items: Список элементов
        max_items: Максимальное количество элементов для отображения
        
    Returns:
        str: Отформатированный список
    """
    if not items:
        return "Список пуст"
    
    result = ""
    for i, item in enumerate(items[:max_items], 1):
        result += f"{i}. {item}\n"
    
    if len(items) > max_items:
        result += f"... и еще {len(items) - max_items}"
    
    return result.strip()


def format_time_ago(timestamp) -> str:
    """
    Форматировать время "назад"
    
    Args:
        timestamp: Временная метка (datetime объект)
        
    Returns:
        str: Время в формате "X назад"
    """
    if not timestamp:
        return "Никогда"
    
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        # Если timezone не указан, предполагаем UTC
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    
    diff = now - timestamp
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    if days > 0:
        return f"{days}д назад"
    elif hours > 0:
        return f"{hours}ч назад"
    elif minutes > 0:
        return f"{minutes}м назад"
    else:
        return "Только что"


def format_user_mention(user) -> str:
    """
    Форматировать упоминание пользователя
    
    Args:
        user: Объект пользователя Telegram
        
    Returns:
        str: Отформатированное упоминание
    """
    if not user:
        return "Пользователь"
    
    if user.username:
        return f"@{user.username}"
    
    name = user.first_name or ""
    if user.last_name:
        name += f" {user.last_name}"
    
    return name.strip() or "Пользователь"


def format_player_info(player_data: Dict[str, Any]) -> str:
    """
    Форматировать информацию об игроке
    
    Args:
        player_data: Данные игрока из API
        
    Returns:
        str: Отформатированная информация об игроке
    """
    if not player_data:
        return "❌ Нет данных об игроке"
    
    text = f"👤 **{player_data.get('name', 'N/A')}**\n"
    text += f"🏷️ Тег: `{player_data.get('tag', 'N/A')}`\n"
    text += f"{format_build_hall_level(player_data.get('townHallLevel', 0))}\n"
    text += f"🏆 Кубки: {format_large_number(player_data.get('trophies', 0))}\n"
    
    if 'clan' in player_data:
        clan = player_data['clan']
        text += f"\n🏰 Клан: {clan.get('name', 'N/A')}\n"
        text += f"📊 Роль: {format_clan_role(clan.get('role', 'member'))}\n"
    
    return text


def format_clan_info(clan_data: Dict[str, Any]) -> str:
    """
    Форматирует информацию о клане
    """
    if not clan_data:
        return "Информация о клане недоступна"
    
    return f"""
🏰 **{clan_data.get('name', 'N/A')}**
🏷 Тег: {clan_data.get('tag', 'N/A')}
📊 Уровень: {clan_data.get('clanLevel', 0)}
👥 Участники: {clan_data.get('members', 0)}/50
🏆 Трофеи: {clan_data.get('clanPoints', 0)}
    """.strip()


def format_binding_stats(stats: dict) -> str:
    """Форматирует статистику привязок"""
    if not stats:
        return "Нет данных о привязках"
    
    return f"""
📊 Статистика привязок:
• Всего: {stats.get('total_bindings', 0)}
• Подтверждённых: {stats.get('verified_bindings', 0)}
• Неподтверждённых: {stats.get('unverified_bindings', 0)}
    """.strip()


def format_admin_report(report: dict) -> str:
    """Форматирует административный отчёт"""
    if not report:
        return "Нет данных для отчёта"
    
    lines = ["📋 Административный отчёт"]
    
    if 'users' in report:
        lines.append(f"👥 Пользователей: {report['users']}")
    if 'bindings' in report:
        lines.append(f"🔗 Привязок: {report['bindings']}")
    if 'verified' in report:
        lines.append(f"✅ Подтверждено: {report['verified']}")
    
    return "\n".join(lines)


def format_user_greeting(user_data: dict) -> str:
    """Форматирует приветствие пользователя"""
    if not user_data:
        return "Привет! 👋"
    
    name = user_data.get('first_name', 'друг')
    return f"Привет, {name}! 👋"


def format_contextual_help(context: dict = None) -> str:
    """Форматирует контекстную справку"""
    return """
📖 **Справка по командам**

Основные команды:
• /start - Начать работу с ботом
• /commands - Список всех команд
• /help - Помощь

Паспорта:
• /passport - Посмотреть свой паспорт
• /plist - Список всех паспортов

Привязки:
• /bind_player - Привязать игрока
• /binding_stats - Статистика привязок
    """.strip()


def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """
    Создаёт визуальный прогресс-бар
    
    Args:
        current: Текущее значение
        total: Максимальное значение
        length: Длина прогресс-бара в символах
        
    Returns:
        str: Текстовый прогресс-бар
    """
    if total == 0:
        return "░" * length
    
    filled = int((current / total) * length)
    filled = max(0, min(filled, length))
    
    bar = "█" * filled + "░" * (length - filled)
    percentage = int((current / total) * 100)
    
    return f"{bar} {percentage}%"
