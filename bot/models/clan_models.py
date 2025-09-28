"""
Модели данных для системы кланов
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class ClanData:
    """Данные клана из CoC API"""
    tag: str
    name: str
    description: str
    level: int
    points: int
    member_count: int
    war_wins: int = 0
    war_win_streak: int = 0
    location: str = "Unknown"
    badge_url: str = ""
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'ClanData':
        """Создать объект из ответа CoC API"""
        return cls(
            tag=data['tag'],
            name=data['name'],
            description=data.get('description', ''),
            level=data.get('clanLevel', 1),
            points=data.get('clanPoints', 0),
            member_count=data.get('members', 0),
            war_wins=data.get('warWins', 0),
            war_win_streak=data.get('warWinStreak', 0),
            location=data.get('location', {}).get('name', 'Unknown'),
            badge_url=data.get('badgeUrls', {}).get('medium', '')
        )


@dataclass
class ClanInfo:
    """Информация о зарегистрированном клане"""
    id: int
    clan_tag: str
    clan_name: str
    clan_description: Optional[str]
    clan_level: int
    clan_points: int
    member_count: int
    chat_id: int
    registered_by: int
    registered_at: datetime
    is_active: bool
    is_verified: bool
    last_updated: datetime
    clan_metadata: Dict[str, Any]
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'ClanInfo':
        """Создать объект из строки БД"""
        return cls(
            id=row[0],
            clan_tag=row[1],
            clan_name=row[2],
            clan_description=row[3],
            clan_level=row[4],
            clan_points=row[5],
            member_count=row[6],
            chat_id=row[7],
            registered_by=row[8],
            registered_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
            is_active=bool(row[10]),
            is_verified=bool(row[11]),
            last_updated=datetime.fromisoformat(row[12]) if row[12] else datetime.now(),
            clan_metadata=json.loads(row[13]) if row[13] else {}
        )


@dataclass
class ChatClanSettings:
    """Настройки кланов для чата"""
    id: int
    chat_id: int
    chat_title: Optional[str]
    default_clan_id: Optional[int]
    max_clans_per_chat: int
    show_clan_numbers: bool
    auto_detect_clan: bool
    admin_only_registration: bool
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'ChatClanSettings':
        """Создать объект из строки БД"""
        return cls(
            id=row[0],
            chat_id=row[1],
            chat_title=row[2],
            default_clan_id=row[3],
            max_clans_per_chat=row[4],
            show_clan_numbers=bool(row[5]),
            auto_detect_clan=bool(row[6]),
            admin_only_registration=bool(row[7]),
            created_at=datetime.fromisoformat(row[8]) if row[8] else datetime.now(),
            updated_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now()
        )
    
    @classmethod
    def default_for_chat(cls, chat_id: int, chat_title: str = None) -> 'ChatClanSettings':
        """Создать настройки по умолчанию для чата"""
        now = datetime.now()
        return cls(
            id=0,  # Будет установлен при сохранении
            chat_id=chat_id,
            chat_title=chat_title,
            default_clan_id=None,
            max_clans_per_chat=10,
            show_clan_numbers=True,
            auto_detect_clan=True,
            admin_only_registration=True,
            created_at=now,
            updated_at=now
        )


@dataclass
class ClanOperationLog:
    """Лог операции с кланом"""
    id: int
    operation_type: str  # 'register', 'update', 'deactivate', 'verify'
    clan_id: Optional[int]
    clan_tag: Optional[str]
    chat_id: int
    user_id: int
    username: Optional[str]
    operation_details: Dict[str, Any]
    result: str  # 'success', 'error', 'partial'
    error_message: Optional[str]
    created_at: datetime
    
    @classmethod
    def create_log(cls, operation_type: str, chat_id: int, user_id: int,
                   result: str = 'success', clan_id: int = None, clan_tag: str = None,
                   username: str = None, operation_details: Dict[str, Any] = None,
                   error_message: str = None) -> 'ClanOperationLog':
        """Создать новый лог операции"""
        return cls(
            id=0,  # Будет установлен при сохранении
            operation_type=operation_type,
            clan_id=clan_id,
            clan_tag=clan_tag,
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            operation_details=operation_details or {},
            result=result,
            error_message=error_message,
            created_at=datetime.now()
        )


# Исключения
class ClanRegistrationError(Exception):
    """Базовое исключение для ошибок регистрации кланов"""
    pass


class ClanNotFound(ClanRegistrationError):
    """Клан не найден в CoC API"""
    pass


class ClanAlreadyRegistered(ClanRegistrationError):
    """Клан уже зарегистрирован"""
    pass


class ApiError(ClanRegistrationError):
    """Ошибка CoC API"""
    pass


class ApiRateLimited(ApiError):
    """Превышен лимит запросов к API"""
    pass


class DatabaseError(ClanRegistrationError):
    """Ошибка базы данных"""
    pass


class PermissionDenied(ClanRegistrationError):
    """Нет прав для выполнения операции"""
    pass