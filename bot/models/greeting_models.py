"""
Модель данных для системы приветствия новых участников
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class GreetingSettings:
    """Настройки приветствия для чата"""
    
    chat_id: int
    is_enabled: bool = False
    greeting_text: Optional[str] = None
    welcome_sticker: Optional[str] = None
    delete_after_seconds: Optional[int] = None  # Удалить сообщение через N секунд
    mention_user: bool = True  # Упоминать пользователя в приветствии
    show_rules_button: bool = False  # Показывать кнопку с правилами
    rules_text: Optional[str] = None
    created_by: Optional[int] = None  # ID админа, создавшего настройки
    created_date: datetime = None
    updated_date: datetime = None
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()
        if self.updated_date is None:
            self.updated_date = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сохранения в БД"""
        return {
            'chat_id': self.chat_id,
            'is_enabled': self.is_enabled,
            'greeting_text': self.greeting_text,
            'welcome_sticker': self.welcome_sticker,
            'delete_after_seconds': self.delete_after_seconds,
            'mention_user': self.mention_user,
            'show_rules_button': self.show_rules_button,
            'rules_text': self.rules_text,
            'created_by': self.created_by,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GreetingSettings':
        """Создание объекта из словаря"""
        return cls(
            chat_id=data['chat_id'],
            is_enabled=data.get('is_enabled', False),
            greeting_text=data.get('greeting_text'),
            welcome_sticker=data.get('welcome_sticker'),
            delete_after_seconds=data.get('delete_after_seconds'),
            mention_user=data.get('mention_user', True),
            show_rules_button=data.get('show_rules_button', False),
            rules_text=data.get('rules_text'),
            created_by=data.get('created_by'),
            created_date=datetime.fromisoformat(data['created_date']) if data.get('created_date') else None,
            updated_date=datetime.fromisoformat(data['updated_date']) if data.get('updated_date') else None
        )
    
    def format_greeting_for_user(self, user_first_name: str, username: str = None) -> str:
        """Форматирование приветствия для конкретного пользователя"""
        
        if not self.greeting_text:
            # Дефолтное приветствие
            mention = f"@{username}" if username else user_first_name
            return f"👋 Добро пожаловать в наш чат, {mention}!"
        
        # Заменяем плейсхолдеры в тексте
        formatted_text = self.greeting_text
        
        # Доступные плейсхолдеры:
        placeholders = {
            '{name}': user_first_name,
            '{username}': f"@{username}" if username else user_first_name,
            '{mention}': f"@{username}" if username else user_first_name,
            '{first_name}': user_first_name
        }
        
        for placeholder, value in placeholders.items():
            formatted_text = formatted_text.replace(placeholder, value)
        
        return formatted_text
    
    def update_settings(self, **kwargs):
        """Обновление настроек"""
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_date = datetime.now()


@dataclass
class GreetingStats:
    """Статистика системы приветствия"""
    
    chat_id: int
    total_greetings_sent: int = 0
    last_greeting_date: Optional[datetime] = None
    average_new_members_per_day: float = 0.0
    most_active_day: Optional[str] = None  # День недели
    greeting_effectiveness: float = 0.0  # Процент пользователей, ответивших на приветствие
    
    def increment_greeting_count(self):
        """Увеличить счетчик отправленных приветствий"""
        self.total_greetings_sent += 1
        self.last_greeting_date = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'chat_id': self.chat_id,
            'total_greetings_sent': self.total_greetings_sent,
            'last_greeting_date': self.last_greeting_date.isoformat() if self.last_greeting_date else None,
            'average_new_members_per_day': self.average_new_members_per_day,
            'most_active_day': self.most_active_day,
            'greeting_effectiveness': self.greeting_effectiveness
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GreetingStats':
        """Создание из словаря"""
        return cls(
            chat_id=data['chat_id'],
            total_greetings_sent=data.get('total_greetings_sent', 0),
            last_greeting_date=datetime.fromisoformat(data['last_greeting_date']) if data.get('last_greeting_date') else None,
            average_new_members_per_day=data.get('average_new_members_per_day', 0.0),
            most_active_day=data.get('most_active_day'),
            greeting_effectiveness=data.get('greeting_effectiveness', 0.0)
        )


# Предопределенные шаблоны приветствий
GREETING_TEMPLATES = {
    'friendly': '👋 Привет, {name}! Добро пожаловать в наш уютный чат! Надеемся, тебе здесь понравится! 😊',
    
    'clan_welcome': '🏰 Добро пожаловать в клан, {name}! Мы рады видеть тебя в наших рядах. Готов к великим сражениям? ⚔️',
    
    'formal': '👋 Добро пожаловать в наш чат, {name}. Пожалуйста, ознакомьтесь с правилами и не стесняйтесь задавать вопросы.',
    
    'gaming': '🎮 Йо, {name}! Добро пожаловать в нашу игровую тусовку! Готов к эпическим батлам в Clash of Clans? 🔥',
    
    'helpful': '👋 Привет, {name}! Добро пожаловать! Если у тебя есть вопросы о Clash of Clans или нужна помощь - обращайся! 💪',
    
    'community': '🌟 Добро пожаловать в наше сообщество, {name}! Здесь ты найдешь друзей, советы и много интересного! Приятного общения! 💬'
}