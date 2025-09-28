"""
Утилиты для форматирования данных в сообщениях
"""

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