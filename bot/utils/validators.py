"""
Утилиты для валидации и проверок
"""
import re
from typing import Optional, Tuple


class ClanTagValidator:
    """Валидатор тегов кланов"""
    
    # Регулярное выражение для валидного тега клана
    CLAN_TAG_PATTERN = re.compile(r'^#?[0289PYLQGRJCUV]{3,10}$')
    
    @classmethod
    def validate_clan_tag(cls, clan_tag: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация тега клана
        
        Args:
            clan_tag: Тег клана для проверки
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not clan_tag:
            return False, "Тег клана не может быть пустым"
        
        # Убираем пробелы
        clan_tag = clan_tag.strip()
        
        if len(clan_tag) < 4:
            return False, "Тег клана слишком короткий (минимум 4 символа с #)"
        
        if len(clan_tag) > 11:
            return False, "Тег клана слишком длинный (максимум 10 символов без #)"
        
        if not clan_tag.startswith('#'):
            return False, "Тег клана должен начинаться с символа #"
        
        # Проверяем символы (CoC использует специальный набор символов)
        if not cls.CLAN_TAG_PATTERN.match(clan_tag.upper()):
            return False, "Тег содержит недопустимые символы"
        
        return True, None
    
    @classmethod
    def normalize_clan_tag(cls, clan_tag: str) -> str:
        """
        Нормализация тега клана
        
        Args:
            clan_tag: Исходный тег
            
        Returns:
            str: Нормализованный тег в верхнем регистре с #
        """
        if not clan_tag:
            return ""
        
        clan_tag = clan_tag.strip().upper()
        
        if not clan_tag.startswith('#'):
            clan_tag = '#' + clan_tag
        
        return clan_tag
    
    @classmethod
    def is_valid_clan_tag(cls, clan_tag: str) -> bool:
        """
        Быстрая проверка валидности тега
        
        Args:
            clan_tag: Тег для проверки
            
        Returns:
            bool: True если тег валидный
        """
        is_valid, _ = cls.validate_clan_tag(clan_tag)
        return is_valid


class CommandArgumentParser:
    """Парсер аргументов команд"""
    
    @staticmethod
    def parse_register_clan_args(args_str: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Парсинг аргументов команды /register_clan
        
        Args:
            args_str: Строка аргументов
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (clan_tag, description)
        """
        if not args_str:
            return None, None
        
        parts = args_str.strip().split()
        
        if not parts:
            return None, None
        
        clan_tag = parts[0]
        description = " ".join(parts[1:]) if len(parts) > 1 else None
        
        return clan_tag, description
    
    @staticmethod
    def parse_clan_selector(args_str: str) -> Tuple[Optional[str], bool]:
        """
        Парсинг селектора клана (номер или тег)
        
        Args:
            args_str: Строка с селектором
            
        Returns:
            Tuple[Optional[str], bool]: (selector, is_number)
        """
        if not args_str:
            return None, False
        
        selector = args_str.strip()
        
        # Проверяем является ли число
        try:
            int(selector)
            return selector, True
        except ValueError:
            return selector, False


class TextFormatter:
    """Форматтер текста для сообщений"""
    
    @staticmethod
    def format_number(number: int) -> str:
        """Форматирование числа с разделителями"""
        return f"{number:,}".replace(",", " ")
    
    @staticmethod
    def format_clan_name_with_tag(clan_name: str, clan_tag: str) -> str:
        """Форматирование названия клана с тегом"""
        return f"{clan_name} `{clan_tag}`"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Обрезка текста с добавлением суффикса"""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Экранирование специальных символов Markdown"""
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    @staticmethod
    def format_error_message(error: str, context: str = None) -> str:
        """Форматирование сообщения об ошибке"""
        message = f"❌ **Ошибка**\n\n{error}"
        
        if context:
            message += f"\n\n**Контекст:** {context}"
        
        return message
    
    @staticmethod
    def format_success_message(message: str, details: str = None) -> str:
        """Форматирование сообщения об успехе"""
        formatted = f"✅ **{message}**"
        
        if details:
            formatted += f"\n\n{details}"
        
        return formatted


class ValidationHelper:
    """Вспомогательный класс для валидации"""
    
    @staticmethod
    def validate_chat_context(chat_id: int, user_id: int) -> Tuple[bool, Optional[str]]:
        """Валидация контекста чата"""
        if chat_id > 0:
            return False, "Команда работает только в групповых чатах"
        
        if not user_id:
            return False, "Не удалось определить пользователя"
        
        return True, None
    
    @staticmethod
    def validate_clan_number(number_str: str, max_clans: int) -> Tuple[bool, Optional[str], Optional[int]]:
        """Валидация номера клана"""
        try:
            number = int(number_str)
        except ValueError:
            return False, "Номер клана должен быть числом", None
        
        if number < 1:
            return False, "Номер клана должен быть больше 0", None
        
        if number > max_clans:
            return False, f"Номер клана не может быть больше {max_clans}", None
        
        return True, None, number
    
    @staticmethod
    def validate_description(description: str, max_length: int = 200) -> Tuple[bool, Optional[str]]:
        """Валидация описания клана"""
        if not description:
            return True, None  # Описание опциональное
        
        if len(description) > max_length:
            return False, f"Описание слишком длинное (максимум {max_length} символов)"
        
        # Проверяем на недопустимые символы или паттерны
        forbidden_patterns = ['http://', 'https://', '@', 't.me']
        
        description_lower = description.lower()
        for pattern in forbidden_patterns:
            if pattern in description_lower:
                return False, f"Описание не должно содержать ссылки или упоминания"
        
        return True, None


# Константы для валидации
class ValidationConstants:
    """Константы для валидации"""
    
    MAX_CLAN_DESCRIPTION_LENGTH = 200
    MAX_CLANS_PER_CHAT = 10
    MIN_CLAN_TAG_LENGTH = 4
    MAX_CLAN_TAG_LENGTH = 11
    
    # Лимиты для CoC API
    COC_API_RATE_LIMIT = 35  # запросов в секунду
    COC_API_TIMEOUT = 30  # секунд
    
    # Лимиты сообщений
    TELEGRAM_MESSAGE_MAX_LENGTH = 4096
    TELEGRAM_INLINE_QUERY_MAX_LENGTH = 256


# Удобные функции для использования в коде
def validate_clan_tag(clan_tag: str) -> Tuple[bool, Optional[str]]:
    """Валидация тега клана"""
    return ClanTagValidator.validate_clan_tag(clan_tag)

def normalize_clan_tag(clan_tag: str) -> str:
    """Нормализация тега клана"""
    return ClanTagValidator.normalize_clan_tag(clan_tag)

def format_number(number: int) -> str:
    """Форматирование числа"""
    return TextFormatter.format_number(number)

def format_clan_name_with_tag(name: str, tag: str) -> str:
    """Форматирование названия клана с тегом"""
    return TextFormatter.format_clan_name_with_tag(name, tag)

def format_error(error: str, context: str = None) -> str:
    """Форматирование ошибки"""
    return TextFormatter.format_error_message(error, context)

def format_success(message: str, details: str = None) -> str:
    """Форматирование успеха"""
    return TextFormatter.format_success_message(message, details)


# Дополнительные функции форматирования
def format_date(timestamp):
    """Форматирует дату для отображения"""
    from datetime import datetime
    
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return timestamp
    
    if isinstance(timestamp, datetime):
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        diff = now - timestamp
        
        if diff.days > 30:
            months = diff.days // 30
            return f"{months} мес. назад"
        elif diff.days > 0:
            return f"{diff.days} дн. назад"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"
    
    return str(timestamp)


def format_percentage(value: float, total: float) -> str:
    """Форматирует процентное соотношение"""
    if total == 0:
        return "0%"
    
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"


def format_role_emoji(role: str) -> str:
    """Возвращает эмодзи для роли"""
    role_emojis = {
        'leader': '👑',
        'coLeader': '🌟',
        'admin': '⭐',
        'member': '👤'
    }
    return role_emojis.get(role, '👤')


def format_role_name(role: str) -> str:
    """Возвращает русское название роли"""
    role_names = {
        'leader': 'Лидер',
        'coLeader': 'Со-лидер',
        'admin': 'Старейшина',
        'member': 'Участник'
    }
    return role_names.get(role, 'Участник')


def validate_player_tag(player_tag: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация тега игрока (использует ту же логику что и для клана)
    
    Args:
        player_tag: Тег игрока для проверки
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not player_tag:
        return False, "Тег игрока не может быть пустым"
    
    # Убираем пробелы
    player_tag = player_tag.strip()
    
    if len(player_tag) < 4:
        return False, "Тег игрока слишком короткий (минимум 4 символа с #)"
    
    if len(player_tag) > 11:
        return False, "Тег игрока слишком длинный (максимум 10 символов без #)"
    
    if not player_tag.startswith('#'):
        return False, "Тег игрока должен начинаться с символа #"
    
    # Проверяем символы (CoC использует специальный набор символов)
    pattern = re.compile(r'^#?[0289PYLQGRJCUV]{3,10}$')
    if not pattern.match(player_tag.upper()):
        return False, "Тег содержит недопустимые символы"
    
    return True, None


def normalize_player_tag(player_tag: str) -> str:
    """
    Нормализация тега игрока
    
    Args:
        player_tag: Исходный тег
        
    Returns:
        str: Нормализованный тег в верхнем регистре с #
    """
    if not player_tag:
        return ""
    
    player_tag = player_tag.strip().upper()
    
    if not player_tag.startswith('#'):
        player_tag = '#' + player_tag
    
    return player_tag