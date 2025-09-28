"""
Модели данных для системы достижений и прогресса
Фаза 6: Комплексная система мотивации и отслеживания прогресса
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import json

class AchievementCategory(Enum):
    """Категории достижений"""
    SOCIAL = "social"              # Социальные достижения (активность в чате, помощь другим)
    GAME_PROGRESS = "game_progress"  # Игровой прогресс (кубки, уровень, атаки)
    CLAN_CONTRIBUTION = "clan_contribution"  # Вклад в клан (участие в войнах, донаты)
    SYSTEM_MASTERY = "system_mastery"  # Освоение системы бота (создание паспорта, привязки)
    LEADERSHIP = "leadership"      # Лидерские достижения (управление кланом, менторство)
    SPECIAL_EVENTS = "special_events"  # Специальные события и праздники
    MILESTONES = "milestones"     # Важные вехи и юбилеи


class AchievementDifficulty(Enum):
    """Сложность достижения"""
    BRONZE = "bronze"     # Легкие достижения для начинающих
    SILVER = "silver"     # Средние достижения для активных пользователей  
    GOLD = "gold"         # Сложные достижения для опытных участников
    PLATINUM = "platinum" # Очень сложные достижения для экспертов
    DIAMOND = "diamond"   # Эксклюзивные достижения для избранных


class AchievementStatus(Enum):
    """Статус достижения"""
    LOCKED = "locked"         # Заблокировано (условия не выполнены)
    AVAILABLE = "available"   # Доступно для выполнения
    IN_PROGRESS = "in_progress"  # В процессе выполнения
    COMPLETED = "completed"   # Завершено
    CLAIMED = "claimed"       # Награда получена


class RewardType(Enum):
    """Типы наград"""
    TITLE = "title"           # Специальный титул/звание
    BADGE = "badge"           # Значок в профиле
    POINTS = "points"         # Очки опыта/рейтинга
    PRIVILEGE = "privilege"   # Специальные привилегии
    COSMETIC = "cosmetic"     # Косметические улучшения
    ACCESS = "access"         # Доступ к функциям


@dataclass
class AchievementReward:
    """Награда за достижение"""
    reward_type: RewardType
    reward_id: str
    name: str
    description: str
    value: Any = None  # Значение награды (например, количество очков)
    icon: str = "🏆"
    is_permanent: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сериализации"""
        return {
            'reward_type': self.reward_type.value,
            'reward_id': self.reward_id,
            'name': self.name,
            'description': self.description,
            'value': self.value,
            'icon': self.icon,
            'is_permanent': self.is_permanent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AchievementReward':
        """Создание из словаря"""
        return cls(
            reward_type=RewardType(data['reward_type']),
            reward_id=data['reward_id'],
            name=data['name'],
            description=data['description'],
            value=data.get('value'),
            icon=data.get('icon', '🏆'),
            is_permanent=data.get('is_permanent', True)
        )


@dataclass
class AchievementRequirement:
    """Требование для достижения"""
    requirement_type: str  # Тип требования (messages_count, clan_wars_won, etc.)
    target_value: Any      # Целевое значение
    current_value: Any = 0 # Текущее значение
    comparison: str = "gte"  # Тип сравнения (gte, eq, lt, etc.)
    
    def is_completed(self) -> bool:
        """Проверка выполнения требования"""
        if self.comparison == "gte":
            return self.current_value >= self.target_value
        elif self.comparison == "eq":
            return self.current_value == self.target_value
        elif self.comparison == "lt":
            return self.current_value < self.target_value
        elif self.comparison == "lte":
            return self.current_value <= self.target_value
        elif self.comparison == "gt":
            return self.current_value > self.target_value
        return False
    
    def get_progress_percentage(self) -> float:
        """Получение процента выполнения"""
        if self.comparison in ["eq", "lt", "lte", "gt"]:
            return 100.0 if self.is_completed() else 0.0
        
        try:
            if isinstance(self.target_value, (int, float)) and self.target_value > 0:
                progress = min(self.current_value / self.target_value * 100, 100)
                return max(progress, 0)
        except (TypeError, ZeroDivisionError):
            pass
        
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'requirement_type': self.requirement_type,
            'target_value': self.target_value,
            'current_value': self.current_value,
            'comparison': self.comparison
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AchievementRequirement':
        """Создание из словаря"""
        return cls(
            requirement_type=data['requirement_type'],
            target_value=data['target_value'],
            current_value=data.get('current_value', 0),
            comparison=data.get('comparison', 'gte')
        )


@dataclass
class Achievement:
    """Модель достижения"""
    achievement_id: str
    name: str
    description: str
    category: AchievementCategory
    difficulty: AchievementDifficulty
    requirements: List[AchievementRequirement]
    rewards: List[AchievementReward]
    icon: str = "🏆"
    hidden: bool = False  # Скрытое достижение
    prerequisites: List[str] = field(default_factory=list)  # ID предварительных достижений
    max_progress: int = 100
    
    def get_overall_progress(self) -> float:
        """Получение общего прогресса достижения"""
        if not self.requirements:
            return 100.0
        
        total_progress = sum(req.get_progress_percentage() for req in self.requirements)
        return total_progress / len(self.requirements)
    
    def is_completed(self) -> bool:
        """Проверка завершенности достижения"""
        return all(req.is_completed() for req in self.requirements)
    
    def get_status_description(self) -> str:
        """Получение описания статуса"""
        progress = self.get_overall_progress()
        
        if progress == 100:
            return "Завершено!"
        elif progress > 0:
            return f"В процессе ({progress:.0f}%)"
        else:
            return "Не начато"
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сериализации"""
        return {
            'achievement_id': self.achievement_id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'difficulty': self.difficulty.value,
            'requirements': [req.to_dict() for req in self.requirements],
            'rewards': [reward.to_dict() for reward in self.rewards],
            'icon': self.icon,
            'hidden': self.hidden,
            'prerequisites': self.prerequisites,
            'max_progress': self.max_progress
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Achievement':
        """Создание из словаря"""
        return cls(
            achievement_id=data['achievement_id'],
            name=data['name'],
            description=data['description'],
            category=AchievementCategory(data['category']),
            difficulty=AchievementDifficulty(data['difficulty']),
            requirements=[AchievementRequirement.from_dict(req) for req in data.get('requirements', [])],
            rewards=[AchievementReward.from_dict(reward) for reward in data.get('rewards', [])],
            icon=data.get('icon', '🏆'),
            hidden=data.get('hidden', False),
            prerequisites=data.get('prerequisites', []),
            max_progress=data.get('max_progress', 100)
        )


@dataclass
class UserAchievementProgress:
    """Прогресс пользователя по достижению"""
    user_id: int
    chat_id: int
    achievement_id: str
    status: AchievementStatus
    progress_percentage: float = 0.0
    started_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    claimed_date: Optional[datetime] = None
    current_values: Dict[str, Any] = field(default_factory=dict)  # Текущие значения требований
    
    def update_progress(self, requirement_type: str, value: Any):
        """Обновление прогресса по требованию"""
        self.current_values[requirement_type] = value
        
        # Если прогресс только начинается
        if self.status == AchievementStatus.LOCKED and value > 0:
            self.status = AchievementStatus.IN_PROGRESS
            self.started_date = datetime.now()
    
    def complete_achievement(self):
        """Завершение достижения"""
        self.status = AchievementStatus.COMPLETED
        self.completed_date = datetime.now()
        self.progress_percentage = 100.0
    
    def claim_rewards(self):
        """Получение наград"""
        if self.status == AchievementStatus.COMPLETED:
            self.status = AchievementStatus.CLAIMED
            self.claimed_date = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'achievement_id': self.achievement_id,
            'status': self.status.value,
            'progress_percentage': self.progress_percentage,
            'started_date': self.started_date.isoformat() if self.started_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'claimed_date': self.claimed_date.isoformat() if self.claimed_date else None,
            'current_values': self.current_values
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserAchievementProgress':
        """Создание из словаря"""
        return cls(
            user_id=data['user_id'],
            chat_id=data['chat_id'],
            achievement_id=data['achievement_id'],
            status=AchievementStatus(data['status']),
            progress_percentage=data.get('progress_percentage', 0.0),
            started_date=datetime.fromisoformat(data['started_date']) if data.get('started_date') else None,
            completed_date=datetime.fromisoformat(data['completed_date']) if data.get('completed_date') else None,
            claimed_date=datetime.fromisoformat(data['claimed_date']) if data.get('claimed_date') else None,
            current_values=data.get('current_values', {})
        )


@dataclass  
class UserProfile:
    """Расширенный профиль пользователя с достижениями"""
    user_id: int
    chat_id: int
    total_points: int = 0
    level: int = 1
    experience_points: int = 0
    titles: Set[str] = field(default_factory=set)
    badges: Set[str] = field(default_factory=set)
    privileges: Set[str] = field(default_factory=set)
    achievements_completed: int = 0
    achievements_claimed: int = 0
    join_date: datetime = field(default_factory=datetime.now)
    last_achievement_date: Optional[datetime] = None
    
    def add_points(self, points: int):
        """Добавление очков опыта"""
        self.experience_points += points
        self.total_points += points
        self._check_level_up()
    
    def _check_level_up(self):
        """Проверка повышения уровня"""
        required_exp = self._calculate_required_experience(self.level + 1)
        
        while self.experience_points >= required_exp:
            self.level += 1
            required_exp = self._calculate_required_experience(self.level + 1)
    
    def _calculate_required_experience(self, level: int) -> int:
        """Расчет требуемого опыта для уровня"""
        # Формула прогрессии: каждый уровень требует больше опыта
        return int(100 * (level ** 1.5))
    
    def get_progress_to_next_level(self) -> Dict[str, Any]:
        """Получение прогресса до следующего уровня"""
        current_level_exp = self._calculate_required_experience(self.level)
        next_level_exp = self._calculate_required_experience(self.level + 1)
        
        exp_for_current_level = self.experience_points - current_level_exp
        exp_needed_for_next = next_level_exp - current_level_exp
        
        progress_percentage = (exp_for_current_level / exp_needed_for_next) * 100
        
        return {
            'current_level': self.level,
            'next_level': self.level + 1,
            'current_exp': exp_for_current_level,
            'needed_exp': exp_needed_for_next,
            'progress_percentage': min(progress_percentage, 100),
            'total_exp': self.experience_points
        }
    
    def add_title(self, title: str):
        """Добавление титула"""
        self.titles.add(title)
    
    def add_badge(self, badge: str):
        """Добавление значка"""
        self.badges.add(badge)
    
    def add_privilege(self, privilege: str):
        """Добавление привилегии"""
        self.privileges.add(privilege)
    
    def has_privilege(self, privilege: str) -> bool:
        """Проверка наличия привилегии"""
        return privilege in self.privileges
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'total_points': self.total_points,
            'level': self.level,
            'experience_points': self.experience_points,
            'titles': list(self.titles),
            'badges': list(self.badges),
            'privileges': list(self.privileges),
            'achievements_completed': self.achievements_completed,
            'achievements_claimed': self.achievements_claimed,
            'join_date': self.join_date.isoformat(),
            'last_achievement_date': self.last_achievement_date.isoformat() if self.last_achievement_date else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Создание из словаря"""
        return cls(
            user_id=data['user_id'],
            chat_id=data['chat_id'],
            total_points=data.get('total_points', 0),
            level=data.get('level', 1),
            experience_points=data.get('experience_points', 0),
            titles=set(data.get('titles', [])),
            badges=set(data.get('badges', [])),
            privileges=set(data.get('privileges', [])),
            achievements_completed=data.get('achievements_completed', 0),
            achievements_claimed=data.get('achievements_claimed', 0),
            join_date=datetime.fromisoformat(data['join_date']) if data.get('join_date') else datetime.now(),
            last_achievement_date=datetime.fromisoformat(data['last_achievement_date']) if data.get('last_achievement_date') else None
        )


@dataclass
class LeaderboardEntry:
    """Запись в таблице лидеров"""
    user_id: int
    chat_id: int
    username: str
    display_name: str
    score: float
    rank: int
    category: str  # Категория лидерборда
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'username': self.username,
            'display_name': self.display_name,
            'score': self.score,
            'rank': self.rank,
            'category': self.category,
            'additional_info': self.additional_info
        }


# Предопределенные достижения системы
SYSTEM_ACHIEVEMENTS = {
    # Социальные достижения
    "first_message": Achievement(
        achievement_id="first_message",
        name="Первые шаги",
        description="Отправьте первое сообщение в чат",
        category=AchievementCategory.SOCIAL,
        difficulty=AchievementDifficulty.BRONZE,
        requirements=[
            AchievementRequirement("messages_count", 1)
        ],
        rewards=[
            AchievementReward(RewardType.POINTS, "welcome_points", "Приветственные очки", "Очки за первое сообщение", 10),
            AchievementReward(RewardType.TITLE, "newcomer", "Новичок", "Титул для новых участников", icon="🌱")
        ],
        icon="💬"
    ),
    
    "active_chatter": Achievement(
        achievement_id="active_chatter",
        name="Активный болтун",
        description="Отправьте 100 сообщений в чат",
        category=AchievementCategory.SOCIAL,
        difficulty=AchievementDifficulty.SILVER,
        requirements=[
            AchievementRequirement("messages_count", 100)
        ],
        rewards=[
            AchievementReward(RewardType.POINTS, "active_points", "Очки активности", "За активное общение", 50),
            AchievementReward(RewardType.BADGE, "chatter_badge", "Значок болтуна", "За активность в чате", icon="💬")
        ],
        icon="🗣️"
    ),
    
    # Достижения системы
    "passport_created": Achievement(
        achievement_id="passport_created",
        name="Оформление документов",
        description="Создайте свой паспорт в системе",
        category=AchievementCategory.SYSTEM_MASTERY,
        difficulty=AchievementDifficulty.BRONZE,
        requirements=[
            AchievementRequirement("passport_created", True, comparison="eq")
        ],
        rewards=[
            AchievementReward(RewardType.POINTS, "passport_points", "Очки за паспорт", "За создание паспорта", 25),
            AchievementReward(RewardType.PRIVILEGE, "profile_access", "Доступ к профилю", "Расширенные функции профиля")
        ],
        icon="📋"
    ),
    
    "player_bound": Achievement(
        achievement_id="player_bound",
        name="Связь установлена",
        description="Привяжите игрока Clash of Clans",
        category=AchievementCategory.SYSTEM_MASTERY,
        difficulty=AchievementDifficulty.SILVER,
        requirements=[
            AchievementRequirement("player_bound", True, comparison="eq")
        ],
        rewards=[
            AchievementReward(RewardType.POINTS, "binding_points", "Очки за привязку", "За привязку игрока", 40),
            AchievementReward(RewardType.PRIVILEGE, "game_stats", "Игровая статистика", "Доступ к игровым данным")
        ],
        prerequisites=["passport_created"],
        icon="🎮"
    ),
    
    # Клановые достижения
    "clan_member": Achievement(
        achievement_id="clan_member",
        name="Член семьи",
        description="Станьте участником клана",
        category=AchievementCategory.CLAN_CONTRIBUTION,
        difficulty=AchievementDifficulty.SILVER,
        requirements=[
            AchievementRequirement("clan_membership", True, comparison="eq")
        ],
        rewards=[
            AchievementReward(RewardType.POINTS, "clan_points", "Клановые очки", "За вступление в клан", 30),
            AchievementReward(RewardType.TITLE, "clan_member", "Клановец", "Титул участника клана", icon="🏰")
        ],
        icon="🏰"
    ),
    
    # Игровые достижения
    "trophy_hunter": Achievement(
        achievement_id="trophy_hunter",
        name="Охотник за кубками",
        description="Наберите 3000+ кубков",
        category=AchievementCategory.GAME_PROGRESS,
        difficulty=AchievementDifficulty.GOLD,
        requirements=[
            AchievementRequirement("trophies", 3000)
        ],
        rewards=[
            AchievementReward(RewardType.POINTS, "trophy_points", "Трофейные очки", "За высокие кубки", 75),
            AchievementReward(RewardType.BADGE, "trophy_badge", "Золотой кубок", "За достижение в кубках", icon="🏆")
        ],
        prerequisites=["player_bound"],
        icon="🏆"
    ),
}