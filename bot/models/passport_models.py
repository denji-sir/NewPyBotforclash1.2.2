"""
Модели данных для системы паспортов игроков
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PassportStatus(Enum):
    """Статусы паспорта"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    BLOCKED = "blocked"


class PassportTheme(Enum):
    """Темы оформления паспорта"""
    DEFAULT = "default"
    DARK = "dark"
    CLAN = "clan"
    ACHIEVEMENTS = "achievements"
    MINIMALIST = "minimalist"


@dataclass
class PassportSettings:
    """Настройки паспорта"""
    theme: PassportTheme = PassportTheme.DEFAULT
    show_achievements: bool = True
    show_stats: bool = True
    show_clan_info: bool = True
    show_activity: bool = True
    privacy_level: int = 1  # 1-публичный, 2-друзья, 3-приватный
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PassportSettings':
        """Создание из словаря"""
        return cls(
            theme=PassportTheme(data.get('theme', 'default')),
            show_achievements=data.get('show_achievements', True),
            show_stats=data.get('show_stats', True),
            show_clan_info=data.get('show_clan_info', True),
            show_activity=data.get('show_activity', True),
            privacy_level=data.get('privacy_level', 1)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'theme': self.theme.value,
            'show_achievements': self.show_achievements,
            'show_stats': self.show_stats,
            'show_clan_info': self.show_clan_info,
            'show_activity': self.show_activity,
            'privacy_level': self.privacy_level
        }


@dataclass
class PassportStats:
    """Статистика паспорта"""
    messages_count: int = 0
    commands_used: int = 0
    days_active: int = 0
    clans_joined: int = 0
    achievements_count: int = 0
    last_activity: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PassportStats':
        """Создание из словаря"""
        last_activity = None
        if data.get('last_activity'):
            if isinstance(data['last_activity'], str):
                last_activity = datetime.fromisoformat(data['last_activity'])
            else:
                last_activity = data['last_activity']
        
        return cls(
            messages_count=data.get('messages_count', 0),
            commands_used=data.get('commands_used', 0),
            days_active=data.get('days_active', 0),
            clans_joined=data.get('clans_joined', 0),
            achievements_count=data.get('achievements_count', 0),
            last_activity=last_activity
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'messages_count': self.messages_count,
            'commands_used': self.commands_used,
            'days_active': self.days_active,
            'clans_joined': self.clans_joined,
            'achievements_count': self.achievements_count,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }


@dataclass 
class PlayerBinding:
    """Привязка игрока CoC к паспорту"""
    player_tag: str
    player_name: str
    clan_tag: Optional[str] = None
    clan_name: Optional[str] = None
    verified: bool = False
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerBinding':
        """Создание из словаря"""
        verified_at = None
        if data.get('verified_at'):
            if isinstance(data['verified_at'], str):
                verified_at = datetime.fromisoformat(data['verified_at'])
            else:
                verified_at = data['verified_at']
        
        return cls(
            player_tag=data['player_tag'],
            player_name=data['player_name'],
            clan_tag=data.get('clan_tag'),
            clan_name=data.get('clan_name'),
            verified=data.get('verified', False),
            verified_by=data.get('verified_by'),
            verified_at=verified_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'player_tag': self.player_tag,
            'player_name': self.player_name,
            'clan_tag': self.clan_tag,
            'clan_name': self.clan_name,
            'verified': self.verified,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None
        }


@dataclass
class PassportInfo:
    """Основная информация паспорта"""
    id: Optional[int] = None
    user_id: int = 0
    chat_id: int = 0
    username: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Основные данные
    status: PassportStatus = PassportStatus.ACTIVE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Привязка к клану
    preferred_clan_id: Optional[int] = None
    preferred_clan_tag: Optional[str] = None
    preferred_clan_name: Optional[str] = None
    
    # Привязка игрока CoC
    player_binding: Optional[PlayerBinding] = None
    
    # Настройки и статистика
    settings: PassportSettings = field(default_factory=PassportSettings)
    stats: PassportStats = field(default_factory=PassportStats)
    
    # Дополнительные данные
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_db_row(cls, row) -> 'PassportInfo':
        """Создание из строки БД"""
        import json
        
        # Парсим JSON поля
        settings_data = json.loads(row[12] or '{}')
        stats_data = json.loads(row[13] or '{}')
        metadata = json.loads(row[14] or '{}')
        player_binding_data = json.loads(row[15] or 'null')
        
        # Преобразуем даты
        created_at = datetime.fromisoformat(row[7]) if row[7] else None
        updated_at = datetime.fromisoformat(row[8]) if row[8] else None
        
        # Создаем объекты
        settings = PassportSettings.from_dict(settings_data)
        stats = PassportStats.from_dict(stats_data)
        player_binding = PlayerBinding.from_dict(player_binding_data) if player_binding_data else None
        
        return cls(
            id=row[0],
            user_id=row[1],
            chat_id=row[2],
            username=row[3],
            display_name=row[4],
            bio=row[5],
            avatar_url=row[6],
            created_at=created_at,
            updated_at=updated_at,
            status=PassportStatus(row[9]) if row[9] else PassportStatus.ACTIVE,
            preferred_clan_id=row[10],
            preferred_clan_tag=row[11],
            preferred_clan_name=row[16],
            settings=settings,
            stats=stats,
            metadata=metadata,
            player_binding=player_binding
        )
    
    def to_db_values(self) -> tuple:
        """Преобразование для вставки в БД"""
        import json
        
        return (
            self.user_id,
            self.chat_id,
            self.username,
            self.display_name,
            self.bio,
            self.avatar_url,
            self.created_at.isoformat() if self.created_at else datetime.now().isoformat(),
            self.updated_at.isoformat() if self.updated_at else datetime.now().isoformat(),
            self.status.value,
            self.preferred_clan_id,
            self.preferred_clan_tag,
            json.dumps(self.settings.to_dict()),
            json.dumps(self.stats.to_dict()),
            json.dumps(self.metadata),
            json.dumps(self.player_binding.to_dict() if self.player_binding else None)
        )


@dataclass
class PassportOperationLog:
    """Лог операций с паспортами"""
    id: Optional[int] = None
    passport_id: int = 0
    operation_type: str = ""  # create, update, delete, bind_player, etc.
    user_id: int = 0
    username: Optional[str] = None
    operation_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    result: str = ""  # success, error, pending
    error_message: Optional[str] = None
    
    @classmethod
    def create_log(cls, operation_type: str, passport_id: int, user_id: int,
                   username: Optional[str] = None, operation_details: Optional[Dict[str, Any]] = None,
                   result: str = "success", error_message: Optional[str] = None) -> 'PassportOperationLog':
        """Создание записи лога"""
        return cls(
            passport_id=passport_id,
            operation_type=operation_type,
            user_id=user_id,
            username=username,
            operation_details=operation_details or {},
            timestamp=datetime.now(),
            result=result,
            error_message=error_message
        )
    
    @classmethod
    def from_db_row(cls, row) -> 'PassportOperationLog':
        """Создание из строки БД"""
        import json
        
        return cls(
            id=row[0],
            passport_id=row[1],
            operation_type=row[2],
            user_id=row[3],
            username=row[4],
            operation_details=json.loads(row[5] or '{}'),
            timestamp=datetime.fromisoformat(row[6]) if row[6] else None,
            result=row[7],
            error_message=row[8]
        )


# Исключения для системы паспортов
class PassportError(Exception):
    """Базовая ошибка системы паспортов"""
    pass

class PassportNotFound(PassportError):
    """Паспорт не найден"""
    pass

class PassportAlreadyExists(PassportError):
    """Паспорт уже существует"""
    pass

class PassportAccessDenied(PassportError):
    """Нет доступа к паспорту"""
    pass

class PassportValidationError(PassportError):
    """Ошибка валидации данных паспорта"""
    pass

class PlayerBindingError(PassportError):
    """Ошибка привязки игрока"""
    pass