"""
Расширенные модели данных для кланов с поддержкой рейдов, войн и детальной статистики
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum


class WarState(Enum):
    """Состояния клановых войн"""
    NOT_IN_WAR = "notInWar"
    PREPARATION = "preparation"
    IN_WAR = "inWar"
    WAR_ENDED = "warEnded"


class CWLState(Enum):
    """Состояния Лиги Войн Кланов"""
    NOT_IN_WAR = "notInWar"
    PREPARATION = "preparation"
    IN_WAR = "inWar"
    WAR_ENDED = "warEnded"
    ENDED = "ended"


class CapitalRaidState(Enum):
    """Состояния капитальных рейдов"""
    ONGOING = "ongoing"
    ENDED = "ended"


class MemberRole(Enum):
    """Роли участников клана"""
    MEMBER = "member"
    ELDER = "elder"
    CO_LEADER = "coLeader"
    LEADER = "leader"


@dataclass
class WarAttack:
    """Модель атаки в войне"""
    order: int
    attacker_tag: str
    attacker_name: str
    defender_tag: str
    defender_name: str
    stars: int
    destruction_percentage: float
    duration: int
    timestamp: Optional[datetime] = None


@dataclass
class WarMember:
    """Модель участника войны"""
    tag: str
    name: str
    town_hall_level: int
    map_position: int
    attacks: List[WarAttack] = field(default_factory=list)
    opponent_attacks: int = 0
    best_opponent_attack: Optional[WarAttack] = None


@dataclass
class ClanWar:
    """Модель клановой войны"""
    state: WarState
    team_size: int
    attacks_per_member: int
    preparation_start_time: Optional[datetime]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    
    # Информация о клане
    clan_tag: str
    clan_name: str
    clan_level: int
    clan_attacks: int
    clan_stars: int
    clan_destruction_percentage: float
    
    # Информация о противнике
    opponent_tag: str
    opponent_name: str
    opponent_level: int
    opponent_attacks: int
    opponent_stars: int
    opponent_destruction_percentage: float
    
    # Участники
    members: List[WarMember] = field(default_factory=list)
    
    @property
    def is_victory(self) -> Optional[bool]:
        """Определить победу (если война завершена)"""
        if self.state != WarState.WAR_ENDED:
            return None
        
        if self.clan_stars > self.opponent_stars:
            return True
        elif self.clan_stars < self.opponent_stars:
            return False
        elif self.clan_destruction_percentage > self.opponent_destruction_percentage:
            return True
        elif self.clan_destruction_percentage < self.opponent_destruction_percentage:
            return False
        else:
            return None  # Ничья


@dataclass
class CWLRound:
    """Модель раунда ЛВК"""
    round_number: int
    wars: List[ClanWar] = field(default_factory=list)


@dataclass
class CWLSeason:
    """Модель сезона ЛВК"""
    state: CWLState
    season: str
    clan_tag: str
    rounds: List[CWLRound] = field(default_factory=list)
    
    @property
    def total_stars(self) -> int:
        """Общее количество звезд за сезон"""
        total = 0
        for round_data in self.rounds:
            for war in round_data.wars:
                total += war.clan_stars
        return total


@dataclass
class CapitalRaidAttack:
    """Модель атаки в капитальном рейде"""
    attacker_tag: str
    attacker_name: str
    district_name: str
    district_id: int
    destruction_percentage: int
    attack_count: int
    limit: int


@dataclass
class CapitalRaidDistrict:
    """Модель района в капитальном рейде"""
    id: int
    name: str
    district_hall_level: int
    destruction_percentage: int
    attack_count: int
    total_looted: int
    attacks: List[CapitalRaidAttack] = field(default_factory=list)


@dataclass
class CapitalRaidMember:
    """Модель участника капитального рейда"""
    tag: str
    name: str
    attacks: int
    attack_limit: int
    bonus_attack_limit: int
    capital_resources_looted: int


@dataclass
class CapitalRaid:
    """Модель капитального рейда"""
    state: CapitalRaidState
    start_time: datetime
    end_time: datetime
    capital_total_loot: int
    raids_completed: int
    total_attacks: int
    enemy_districts_destroyed: int
    offensive_reward: int
    defensive_reward: int
    
    # Участники
    members: List[CapitalRaidMember] = field(default_factory=list)
    
    # Атакованные районы
    attack_log: List[CapitalRaidDistrict] = field(default_factory=list)
    
    # Защитные логи
    defense_log: List[CapitalRaidDistrict] = field(default_factory=list)


@dataclass
class ClanLeadership:
    """Модель руководства клана"""
    leader: Optional['ExtendedClanMember'] = None
    co_leaders: List['ExtendedClanMember'] = field(default_factory=list)
    elders: List['ExtendedClanMember'] = field(default_factory=list)
    
    @property
    def total_leaders(self) -> int:
        """Общее количество руководителей"""
        return 1 + len(self.co_leaders) + len(self.elders) if self.leader else 0


@dataclass
class DonationStats:
    """Статистика донатов участника"""
    player_tag: str
    player_name: str
    donations: int
    donations_received: int
    donation_ratio: float = 0.0
    last_active: Optional[datetime] = None
    
    def __post_init__(self):
        if self.donations_received > 0:
            self.donation_ratio = self.donations / self.donations_received
        else:
            self.donation_ratio = float('inf') if self.donations > 0 else 0.0


@dataclass
class MonthlyDonationStats:
    """Месячная статистика донатов"""
    year: int
    month: int
    clan_tag: str
    total_donations: int
    total_received: int
    active_members: int
    top_donors: List[DonationStats] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def average_donations(self) -> float:
        """Средние донаты на активного участника"""
        if self.active_members > 0:
            return self.total_donations / self.active_members
        return 0.0


@dataclass
class ExtendedClanMember:
    """Расширенная модель участника клана"""
    tag: str
    name: str
    role: MemberRole
    exp_level: int
    trophies: int
    versus_trophies: int
    clan_rank: int
    previous_clan_rank: int
    donations: int
    donations_received: int
    
    # Дополнительная информация (если доступна через API)
    town_hall_level: Optional[int] = None
    builder_hall_level: Optional[int] = None
    war_stars: Optional[int] = None
    last_seen: Optional[datetime] = None
    
    @property
    def is_leadership(self) -> bool:
        """Является ли участник руководителем"""
        return self.role in [MemberRole.LEADER, MemberRole.CO_LEADER, MemberRole.ELDER]
    
    @property
    def donation_ratio(self) -> float:
        """Коэффициент донатов"""
        if self.donations_received > 0:
            return self.donations / self.donations_received
        return float('inf') if self.donations > 0 else 0.0


@dataclass
class ExtendedClanInfo:
    """Расширенная информация о клане"""
    tag: str
    name: str
    description: str
    clan_level: int
    clan_points: int
    clan_versus_points: int
    clan_capital_points: int
    required_trophies: int
    war_frequency: str
    war_win_streak: int
    war_wins: int
    war_ties: int
    war_losses: int
    is_war_log_public: bool
    members: int
    location: Dict[str, Any]
    
    # Расширенная информация
    member_list: List[ExtendedClanMember] = field(default_factory=list)
    leadership: Optional[ClanLeadership] = None
    current_war: Optional[ClanWar] = None
    current_cwl: Optional[CWLSeason] = None
    current_raid: Optional[CapitalRaid] = None
    
    # Статистика
    donation_stats: Optional[MonthlyDonationStats] = None
    
    def __post_init__(self):
        """Инициализация дополнительных полей"""
        if self.member_list and not self.leadership:
            self.leadership = self._build_leadership()
    
    def _build_leadership(self) -> ClanLeadership:
        """Построить структуру руководства из списка участников"""
        leadership = ClanLeadership()
        
        for member in self.member_list:
            if member.role == MemberRole.LEADER:
                leadership.leader = member
            elif member.role == MemberRole.CO_LEADER:
                leadership.co_leaders.append(member)
            elif member.role == MemberRole.ELDER:
                leadership.elders.append(member)
        
        return leadership
    
    @property
    def war_win_rate(self) -> float:
        """Процент побед в войнах"""
        total_wars = self.war_wins + self.war_losses + self.war_ties
        if total_wars > 0:
            return (self.war_wins / total_wars) * 100
        return 0.0
    
    @property
    def average_trophies(self) -> float:
        """Средние кубки участников"""
        if self.member_list:
            return sum(member.trophies for member in self.member_list) / len(self.member_list)
        return 0.0
    
    def get_top_donors(self, limit: int = 10) -> List[ExtendedClanMember]:
        """Получить топ донатеров"""
        return sorted(
            self.member_list,
            key=lambda x: x.donations,
            reverse=True
        )[:limit]
    
    def get_leadership_by_role(self, role: MemberRole) -> List[ExtendedClanMember]:
        """Получить руководителей определенной роли"""
        return [member for member in self.member_list if member.role == role]


@dataclass
class ClanWarHistory:
    """История войн клана"""
    clan_tag: str
    wars: List[ClanWar] = field(default_factory=list)
    
    @property
    def total_wars(self) -> int:
        return len(self.wars)
    
    @property
    def victories(self) -> int:
        return sum(1 for war in self.wars if war.is_victory is True)
    
    @property
    def defeats(self) -> int:
        return sum(1 for war in self.wars if war.is_victory is False)
    
    @property
    def draws(self) -> int:
        return sum(1 for war in self.wars if war.is_victory is None)
    
    @property
    def win_rate(self) -> float:
        if self.total_wars > 0:
            return (self.victories / self.total_wars) * 100
        return 0.0


# Вспомогательные функции для работы с моделями

def war_state_to_emoji(state: WarState) -> str:
    """Конвертировать состояние войны в эмодзи"""
    mapping = {
        WarState.NOT_IN_WAR: "✅",
        WarState.PREPARATION: "⏳",
        WarState.IN_WAR: "⚔️",
        WarState.WAR_ENDED: "🏆"
    }
    return mapping.get(state, "❓")


def role_to_emoji(role: MemberRole) -> str:
    """Конвертировать роль в эмодзи"""
    mapping = {
        MemberRole.LEADER: "👑",
        MemberRole.CO_LEADER: "🔱",
        MemberRole.ELDER: "⭐",
        MemberRole.MEMBER: "👤"
    }
    return mapping.get(role, "❓")


def format_duration(seconds: int) -> str:
    """Форматировать длительность атаки"""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"


def calculate_war_performance(member: WarMember) -> Dict[str, float]:
    """Рассчитать производительность участника в войне"""
    if not member.attacks:
        return {
            'average_stars': 0.0,
            'average_destruction': 0.0,
            'total_stars': 0,
            'attacks_used': 0
        }
    
    total_stars = sum(attack.stars for attack in member.attacks)
    total_destruction = sum(attack.destruction_percentage for attack in member.attacks)
    attacks_count = len(member.attacks)
    
    return {
        'average_stars': total_stars / attacks_count,
        'average_destruction': total_destruction / attacks_count,
        'total_stars': total_stars,
        'attacks_used': attacks_count
    }


def format_clan_role_distribution(clan_info: ExtendedClanInfo) -> Dict[str, int]:
    """Получить распределение ролей в клане"""
    distribution = {
        'leader': 0,
        'co_leader': 0,
        'elder': 0,
        'member': 0
    }
    
    for member in clan_info.member_list:
        if member.role == MemberRole.LEADER:
            distribution['leader'] += 1
        elif member.role == MemberRole.CO_LEADER:
            distribution['co_leader'] += 1
        elif member.role == MemberRole.ELDER:
            distribution['elder'] += 1
        else:
            distribution['member'] += 1
    
    return distribution