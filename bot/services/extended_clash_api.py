"""
Расширенный сервис для работы с CoC API - рейды, войны, ЛВК и статистика
"""

import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from ..models.extended_clan_models import (
    ExtendedClanInfo, ExtendedClanMember, ClanWar, CWLSeason, CapitalRaid,
    WarState, CWLState, CapitalRaidState, MemberRole, MonthlyDonationStats,
    DonationStats, ClanWarHistory, WarMember, WarAttack, CapitalRaidMember,
    CapitalRaidDistrict, CapitalRaidAttack
)
from ..utils.api_error_handler import api_request_handler

logger = logging.getLogger(__name__)


class ExtendedClashAPI:
    """
    Расширенный API клиент для Clash of Clans с поддержкой 
    рейдов, войн, ЛВК и детальной статистики
    """
    
    def __init__(self, tokens: List[str]):
        """
        Инициализация API клиента
        
        Args:
            tokens: Список API токенов для ротации
        """
        self.tokens = tokens
        self.current_token_index = 0
        self.base_url = "https://api.clashofclans.com/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Кеш для уменьшения количества запросов
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 минут
        
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запроса с текущим токеном"""
        token = self.tokens[self.current_token_index]
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
    
    def _rotate_token(self):
        """Переключиться на следующий токен"""
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
    
    def _encode_tag(self, tag: str) -> str:
        """Кодировать тег для использования в URL"""
        if not tag.startswith('#'):
            tag = f"#{tag}"
        return quote(tag, safe='')
    
    @api_request_handler(
        logger,
        ValueError,
        base_message="Не удалось выполнить запрос к Clash of Clans API"
    )
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Выполнить запрос к API с обработкой ошибок и ротацией токенов"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Проверка кеша
        cache_key = f"{endpoint}:{str(params)}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return cached_data
        
        max_retries = len(self.tokens)
        
        for attempt in range(max_retries):
            try:
                headers = self._get_headers()
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Кешируем успешный ответ
                        self.cache[cache_key] = (data, datetime.now())
                        return data
                    elif response.status == 403:
                        # Неверный токен - переключаемся на следующий
                        self._rotate_token()
                        if attempt < max_retries - 1:
                            continue
                        raise ValueError("All API tokens are invalid")
                    elif response.status == 404:
                        raise ValueError(f"Resource not found: {endpoint}")
                    elif response.status == 429:
                        # Rate limit - ждем и пробуем следующий токен
                        self._rotate_token()
                        await asyncio.sleep(1)
                        if attempt < max_retries - 1:
                            continue
                        raise ValueError("Rate limit exceeded for all tokens")
                    else:
                        error_data = await response.json() if response.content_type == 'application/json' else {}
                        raise ValueError(f"API Error {response.status}: {error_data}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Request failed for {url}: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise ValueError(f"Failed to complete request after {max_retries} attempts")
    
    # Расширенная информация о клане
    
    async def get_extended_clan_info(self, clan_tag: str) -> ExtendedClanInfo:
        """Получить расширенную информацию о клане"""
        try:
            # Базовая информация о клане
            clan_data = await self._make_request(f"/clans/{self._encode_tag(clan_tag)}")
            
            # Участники клана
            members_data = await self._make_request(f"/clans/{self._encode_tag(clan_tag)}/members")
            
            # Создаем список расширенных участников
            member_list = []
            for member_data in members_data.get('items', []):
                member = ExtendedClanMember(
                    tag=member_data['tag'],
                    name=member_data['name'],
                    role=MemberRole(member_data['role']),
                    exp_level=member_data['expLevel'],
                    trophies=member_data['trophies'],
                    versus_trophies=member_data['versusTrophies'],
                    clan_rank=member_data['clanRank'],
                    previous_clan_rank=member_data['previousClanRank'],
                    donations=member_data['donations'],
                    donations_received=member_data['donationsReceived']
                )
                member_list.append(member)
            
            # Создаем расширенную информацию о клане
            extended_info = ExtendedClanInfo(
                tag=clan_data['tag'],
                name=clan_data['name'],
                description=clan_data.get('description', ''),
                clan_level=clan_data['clanLevel'],
                clan_points=clan_data['clanPoints'],
                clan_versus_points=clan_data['clanVersusPoints'],
                clan_capital_points=clan_data.get('clanCapitalPoints', 0),
                required_trophies=clan_data['requiredTrophies'],
                war_frequency=clan_data['warFrequency'],
                war_win_streak=clan_data['warWinStreak'],
                war_wins=clan_data['warWins'],
                war_ties=clan_data.get('warTies', 0),
                war_losses=clan_data.get('warLosses', 0),
                is_war_log_public=clan_data['isWarLogPublic'],
                members=clan_data['members'],
                location=clan_data.get('location', {}),
                member_list=member_list
            )
            
            return extended_info
            
        except Exception as e:
            logger.error(f"Error getting extended clan info for {clan_tag}: {e}")
            raise
    
    # Клановые войны
    
    async def get_current_war(self, clan_tag: str) -> Optional[ClanWar]:
        """Получить текущую войну клана"""
        try:
            war_data = await self._make_request(f"/clans/{self._encode_tag(clan_tag)}/currentwar")
            
            if war_data.get('state') == 'notInWar':
                return None
            
            return self._parse_war_data(war_data)
            
        except ValueError as e:
            if "not found" in str(e).lower():
                return None
            logger.error(f"Error getting current war for {clan_tag}: {e}")
            raise
    
    async def get_war_log(self, clan_tag: str, limit: int = 10) -> ClanWarHistory:
        """Получить журнал войн клана"""
        try:
            war_log_data = await self._make_request(
                f"/clans/{self._encode_tag(clan_tag)}/warlog",
                params={'limit': min(limit, 50)}
            )
            
            wars = []
            for war_item in war_log_data.get('items', []):
                if war_item.get('result'):  # Только завершенные войны
                    war = self._parse_war_log_item(war_item, clan_tag)
                    if war:
                        wars.append(war)
            
            return ClanWarHistory(clan_tag=clan_tag, wars=wars)
            
        except Exception as e:
            logger.error(f"Error getting war log for {clan_tag}: {e}")
            return ClanWarHistory(clan_tag=clan_tag)
    
    def _parse_war_data(self, war_data: Dict) -> ClanWar:
        """Парсить данные войны"""
        state = WarState(war_data['state'])
        
        # Время
        prep_start = None
        start_time = None
        end_time = None
        
        if war_data.get('preparationStartTime'):
            prep_start = datetime.fromisoformat(war_data['preparationStartTime'].replace('Z', '+00:00'))
        if war_data.get('startTime'):
            start_time = datetime.fromisoformat(war_data['startTime'].replace('Z', '+00:00'))
        if war_data.get('endTime'):
            end_time = datetime.fromisoformat(war_data['endTime'].replace('Z', '+00:00'))
        
        # Информация о клане и противнике
        clan_info = war_data['clan']
        opponent_info = war_data['opponent']
        
        # Участники
        members = []
        for member_data in clan_info.get('members', []):
            attacks = []
            for attack_data in member_data.get('attacks', []):
                attack = WarAttack(
                    order=attack_data['order'],
                    attacker_tag=attack_data['attackerTag'],
                    attacker_name=member_data['name'],
                    defender_tag=attack_data['defenderTag'],
                    defender_name='Unknown',  # Нужно искать в противнике
                    stars=attack_data['stars'],
                    destruction_percentage=attack_data['destructionPercentage'],
                    duration=attack_data['duration']
                )
                attacks.append(attack)
            
            # Лучшая атака противника на этого участника
            best_opponent_attack = None
            if member_data.get('bestOpponentAttack'):
                boa_data = member_data['bestOpponentAttack']
                best_opponent_attack = WarAttack(
                    order=boa_data['order'],
                    attacker_tag=boa_data['attackerTag'],
                    attacker_name='Unknown',
                    defender_tag=member_data['tag'],
                    defender_name=member_data['name'],
                    stars=boa_data['stars'],
                    destruction_percentage=boa_data['destructionPercentage'],
                    duration=boa_data['duration']
                )
            
            member = WarMember(
                tag=member_data['tag'],
                name=member_data['name'],
                town_hall_level=member_data['townhallLevel'],
                map_position=member_data['mapPosition'],
                attacks=attacks,
                opponent_attacks=member_data.get('opponentAttacks', 0),
                best_opponent_attack=best_opponent_attack
            )
            members.append(member)
        
        war = ClanWar(
            state=state,
            team_size=war_data['teamSize'],
            attacks_per_member=war_data.get('attacksPerMember', 2),
            preparation_start_time=prep_start,
            start_time=start_time,
            end_time=end_time,
            clan_tag=clan_info['tag'],
            clan_name=clan_info['name'],
            clan_level=clan_info['clanLevel'],
            clan_attacks=clan_info.get('attacks', 0),
            clan_stars=clan_info.get('stars', 0),
            clan_destruction_percentage=clan_info.get('destructionPercentage', 0.0),
            opponent_tag=opponent_info['tag'],
            opponent_name=opponent_info['name'],
            opponent_level=opponent_info['clanLevel'],
            opponent_attacks=opponent_info.get('attacks', 0),
            opponent_stars=opponent_info.get('stars', 0),
            opponent_destruction_percentage=opponent_info.get('destructionPercentage', 0.0),
            members=members
        )
        
        return war
    
    def _parse_war_log_item(self, war_item: Dict, clan_tag: str) -> Optional[ClanWar]:
        """Парсить элемент журнала войн"""
        try:
            # Определить, какая команда - наш клан
            clan_info = war_item['clan']
            opponent_info = war_item['opponent']
            
            if clan_info['tag'] != clan_tag:
                clan_info, opponent_info = opponent_info, clan_info
            
            # Создать упрощенную войну из лога
            war = ClanWar(
                state=WarState.WAR_ENDED,
                team_size=war_item['teamSize'],
                attacks_per_member=war_item.get('attacksPerMember', 2),
                preparation_start_time=None,
                start_time=None,
                end_time=datetime.fromisoformat(war_item['endTime'].replace('Z', '+00:00')),
                clan_tag=clan_info['tag'],
                clan_name=clan_info['name'],
                clan_level=clan_info['clanLevel'],
                clan_attacks=clan_info.get('attacks', 0),
                clan_stars=clan_info.get('stars', 0),
                clan_destruction_percentage=clan_info.get('destructionPercentage', 0.0),
                opponent_tag=opponent_info['tag'],
                opponent_name=opponent_info['name'],
                opponent_level=opponent_info['clanLevel'],
                opponent_attacks=opponent_info.get('attacks', 0),
                opponent_stars=opponent_info.get('stars', 0),
                opponent_destruction_percentage=opponent_info.get('destructionPercentage', 0.0)
            )
            
            return war
            
        except Exception as e:
            logger.error(f"Error parsing war log item: {e}")
            return None
    
    # Лига Войн Кланов (ЛВК)
    
    async def get_cwl_info(self, clan_tag: str) -> Optional[CWLSeason]:
        """Получить информацию о текущем сезоне ЛВК"""
        try:
            # CoC API не предоставляет прямой endpoint для CWL
            # Используем текущую войну и пытаемся определить, является ли она частью CWL
            current_war = await self.get_current_war(clan_tag)
            
            if not current_war:
                return None
            
            # Простая эвристика для определения CWL
            # В CWL обычно войны 15x15 или 30x30 и проходят в определенные даты
            if current_war.team_size in [15, 30]:
                # Создаем базовую информацию о CWL
                cwl_season = CWLSeason(
                    state=CWLState(current_war.state.value),
                    season=datetime.now().strftime("%Y-%m"),
                    clan_tag=clan_tag
                )
                return cwl_season
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting CWL info for {clan_tag}: {e}")
            return None
    
    # Капитальные рейды
    
    async def get_capital_raid_seasons(self, clan_tag: str, limit: int = 10) -> List[CapitalRaid]:
        """Получить сезоны капитальных рейдов"""
        try:
            raid_data = await self._make_request(
                f"/clans/{self._encode_tag(clan_tag)}/capitalraidseasons",
                params={'limit': min(limit, 50)}
            )
            
            raids = []
            for raid_item in raid_data.get('items', []):
                raid = self._parse_capital_raid(raid_item)
                if raid:
                    raids.append(raid)
            
            return raids
            
        except Exception as e:
            logger.error(f"Error getting capital raid seasons for {clan_tag}: {e}")
            return []
    
    def _parse_capital_raid(self, raid_data: Dict) -> Optional[CapitalRaid]:
        """Парсить данные капитального рейда"""
        try:
            state = CapitalRaidState.ENDED  # Исторические рейды всегда завершены
            
            start_time = datetime.fromisoformat(raid_data['startTime'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(raid_data['endTime'].replace('Z', '+00:00'))
            
            # Участники
            members = []
            for member_data in raid_data.get('members', []):
                member = CapitalRaidMember(
                    tag=member_data['tag'],
                    name=member_data['name'],
                    attacks=member_data['attacks'],
                    attack_limit=member_data['attackLimit'],
                    bonus_attack_limit=member_data['bonusAttackLimit'],
                    capital_resources_looted=member_data['capitalResourcesLooted']
                )
                members.append(member)
            
            # Атакованные районы
            attack_log = []
            for district_data in raid_data.get('attackLog', []):
                attacks = []
                for attack_data in district_data.get('attacks', []):
                    attack = CapitalRaidAttack(
                        attacker_tag=attack_data['attacker']['tag'],
                        attacker_name=attack_data['attacker']['name'],
                        district_name=district_data['name'],
                        district_id=district_data['id'],
                        destruction_percentage=attack_data['destructionPercentage'],
                        attack_count=1,
                        limit=attack_data.get('limit', 5)
                    )
                    attacks.append(attack)
                
                district = CapitalRaidDistrict(
                    id=district_data['id'],
                    name=district_data['name'],
                    district_hall_level=district_data['districtHallLevel'],
                    destruction_percentage=district_data.get('destructionPercentage', 0),
                    attack_count=district_data.get('attackCount', 0),
                    total_looted=district_data.get('totalLooted', 0),
                    attacks=attacks
                )
                attack_log.append(district)
            
            raid = CapitalRaid(
                state=state,
                start_time=start_time,
                end_time=end_time,
                capital_total_loot=raid_data.get('capitalTotalLoot', 0),
                raids_completed=raid_data.get('raidsCompleted', 0),
                total_attacks=raid_data.get('totalAttacks', 0),
                enemy_districts_destroyed=raid_data.get('enemyDistrictsDestroyed', 0),
                offensive_reward=raid_data.get('offensiveReward', 0),
                defensive_reward=raid_data.get('defensiveReward', 0),
                members=members,
                attack_log=attack_log
            )
            
            return raid
            
        except Exception as e:
            logger.error(f"Error parsing capital raid data: {e}")
            return None
    
    # Статистика донатов
    
    async def calculate_monthly_donation_stats(
        self, 
        clan_tag: str, 
        year: int = None, 
        month: int = None
    ) -> MonthlyDonationStats:
        """Рассчитать месячную статистику донатов"""
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        try:
            # Получаем текущую информацию о клане
            clan_info = await self.get_extended_clan_info(clan_tag)
            
            # Создаем статистику донатов
            donation_stats = []
            total_donations = 0
            total_received = 0
            active_members = 0
            
            for member in clan_info.member_list:
                if member.donations > 0 or member.donations_received > 0:
                    active_members += 1
                
                total_donations += member.donations
                total_received += member.donations_received
                
                stats = DonationStats(
                    player_tag=member.tag,
                    player_name=member.name,
                    donations=member.donations,
                    donations_received=member.donations_received
                )
                donation_stats.append(stats)
            
            # Сортируем по количеству донатов
            top_donors = sorted(donation_stats, key=lambda x: x.donations, reverse=True)[:20]
            
            monthly_stats = MonthlyDonationStats(
                year=year,
                month=month,
                clan_tag=clan_tag,
                total_donations=total_donations,
                total_received=total_received,
                active_members=active_members,
                top_donors=top_donors
            )
            
            return monthly_stats
            
        except Exception as e:
            logger.error(f"Error calculating monthly donation stats for {clan_tag}: {e}")
            return MonthlyDonationStats(
                year=year,
                month=month,
                clan_tag=clan_tag,
                total_donations=0,
                total_received=0,
                active_members=0
            )
    
    # Вспомогательные методы
    
    async def get_player_detailed_info(self, player_tag: str) -> Dict[str, Any]:
        """Получить детальную информацию об игроке"""
        try:
            return await self._make_request(f"/players/{self._encode_tag(player_tag)}")
        except Exception as e:
            logger.error(f"Error getting player info for {player_tag}: {e}")
            raise
    
    def clear_cache(self):
        """Очистить кеш"""
        self.cache.clear()
        logger.info("API cache cleared")
