"""
Утилиты для форматирования текста
"""

from typing import Optional


def format_user_mention(user_id: int, username: Optional[str] = None, first_name: Optional[str] = None) -> str:
    """
    Форматирует упоминание пользователя
    
    Args:
        user_id: ID пользователя
        username: Username пользователя (опционально)
        first_name: Имя пользователя (опционально)
    
    Returns:
        Отформатированное упоминание
    """
    if username:
        return f"@{username}"
    elif first_name:
        return f"[{first_name}](tg://user?id={user_id})"
    else:
        return f"[Пользователь](tg://user?id={user_id})"


def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы Markdown
    
    Args:
        text: Исходный текст
    
    Returns:
        Экранированный текст
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_number(num: int) -> str:
    """
    Форматирует число с разделителями тысяч
    
    Args:
        num: Число для форматирования
    
    Returns:
        Отформатированное число
    """
    return f"{num:,}".replace(",", " ")


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Форматирует процент
    
    Args:
        value: Значение (0-100)
        decimals: Количество знаков после запятой
    
    Returns:
        Отформатированный процент
    """
    return f"{value:.{decimals}f}%"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
    
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_war_info(war_data: dict) -> str:
    """
    Форматирует информацию о войне клана
    
    Args:
        war_data: Данные о войне
    
    Returns:
        Отформатированная информация о войне
    """
    if not war_data:
        return "❌ Нет данных о войне"
    
    state = war_data.get('state', 'unknown')
    clan = war_data.get('clan', {})
    opponent = war_data.get('opponent', {})
    
    text = f"⚔️ **Клановая война**\n\n"
    text += f"📊 Статус: {state}\n"
    text += f"🏰 {clan.get('name', 'N/A')}: {clan.get('stars', 0)}⭐ ({clan.get('attacks', 0)} атак)\n"
    text += f"🏰 {opponent.get('name', 'N/A')}: {opponent.get('stars', 0)}⭐ ({opponent.get('attacks', 0)} атак)\n"
    
    return text


def format_raid_info(raid_data: dict) -> str:
    """
    Форматирует информацию о капитальных рейдах
    
    Args:
        raid_data: Данные о рейдах
    
    Returns:
        Отформатированная информация о рейдах
    """
    if not raid_data:
        return "❌ Нет данных о рейдах"
    
    text = f"🏛️ **Капитальные рейды**\n\n"
    
    if 'items' in raid_data and raid_data['items']:
        latest = raid_data['items'][0]
        text += f"📊 Последний рейд:\n"
        text += f"⚔️ Атак: {latest.get('totalAttacks', 0)}\n"
        text += f"🏆 Награблено: {format_number(latest.get('capitalTotalLoot', 0))}\n"
    else:
        text += "Нет данных о рейдах"
    
    return text


def format_cwl_info(cwl_data: dict) -> str:
    """
    Форматирует информацию о Лиге Войн Кланов
    
    Args:
        cwl_data: Данные о ЛВК
    
    Returns:
        Отформатированная информация о ЛВК
    """
    if not cwl_data:
        return "❌ Нет данных о ЛВК"
    
    text = f"🏆 **Лига Войн Кланов**\n\n"
    text += f"📊 Сезон: {cwl_data.get('season', 'N/A')}\n"
    text += f"🎖️ Лига: {cwl_data.get('league', 'N/A')}\n"
    
    return text
