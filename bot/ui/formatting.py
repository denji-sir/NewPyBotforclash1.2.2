"""
UI форматирование - прогресс-бары и визуальные элементы
"""


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


def format_percentage(current: int, total: int) -> str:
    """
    Форматирует процент выполнения
    
    Args:
        current: Текущее значение
        total: Максимальное значение
        
    Returns:
        str: Процент в виде строки
    """
    if total == 0:
        return "0%"
    
    percentage = int((current / total) * 100)
    return f"{percentage}%"


def format_duration(seconds: int) -> str:
    """
    Форматирует длительность в человеко-читаемый вид
    
    Args:
        seconds: Количество секунд
        
    Returns:
        str: Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds}с"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}м"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}ч"
    else:
        days = seconds // 86400
        return f"{days}д"
