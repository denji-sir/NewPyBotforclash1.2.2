"""
Сервис для сохранения статистики клановых войн
"""
import logging
import aiosqlite
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class WarStatsService:
    """Сервис для работы со статистикой клановых войн"""
    
    def __init__(self, db_path: str):
        # Извлекаем путь из database URL
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
    
    async def save_war_result(
        self,
        clan_tag: str,
        clan_name: str,
        opponent_tag: str,
        opponent_name: str,
        war_data: Dict[str, Any]
    ) -> int:
        """
        Сохранить результаты войны
        
        Args:
            clan_tag: Тег клана
            clan_name: Название клана
            opponent_tag: Тег противника
            opponent_name: Название противника
            war_data: Данные войны из API
            
        Returns:
            ID сохраненной войны
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Определяем результат
                clan_stars = war_data.get('clan', {}).get('stars', 0)
                opponent_stars = war_data.get('opponent', {}).get('stars', 0)
                
                if clan_stars > opponent_stars:
                    result = 'win'
                elif clan_stars < opponent_stars:
                    result = 'lose'
                else:
                    result = 'draw'
                
                # Сохраняем основную информацию о войне
                cursor = await db.execute("""
                    INSERT INTO clan_wars (
                        clan_tag, clan_name, opponent_tag, opponent_name,
                        war_size, result, clan_stars, clan_destruction,
                        opponent_stars, opponent_destruction,
                        start_time, end_time, preparation_start_time, war_type, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clan_tag,
                    clan_name,
                    opponent_tag,
                    opponent_name,
                    war_data.get('teamSize', 0),
                    result,
                    clan_stars,
                    war_data.get('clan', {}).get('destructionPercentage', 0.0),
                    opponent_stars,
                    war_data.get('opponent', {}).get('destructionPercentage', 0.0),
                    war_data.get('startTime', ''),
                    war_data.get('endTime', ''),
                    war_data.get('preparationStartTime', ''),
                    war_data.get('warType', 'regular'),
                    json.dumps(war_data.get('metadata', {}))
                ))
                
                war_id = cursor.lastrowid
                
                # Сохраняем статистику игроков клана
                clan_members = war_data.get('clan', {}).get('members', [])
                for member in clan_members:
                    await self._save_player_war_stats(db, war_id, member, clan_tag)
                
                # Сохраняем атаки
                for member in clan_members:
                    attacks = member.get('attacks', [])
                    for attack in attacks:
                        await self._save_war_attack(db, war_id, member['tag'], member['name'], attack)
                
                await db.commit()
                logger.info(f"War result saved: {clan_name} vs {opponent_name} - {result}")
                return war_id
                
        except Exception as e:
            logger.error(f"Error saving war result: {e}")
            return 0
    
    async def _save_player_war_stats(
        self,
        db: aiosqlite.Connection,
        war_id: int,
        member_data: Dict[str, Any],
        clan_tag: str
    ):
        """Сохранить статистику игрока в войне"""
        attacks = member_data.get('attacks', [])
        total_stars = sum(attack.get('stars', 0) for attack in attacks)
        total_destruction = sum(attack.get('destructionPercentage', 0) for attack in attacks)
        avg_destruction = total_destruction / len(attacks) if attacks else 0
        
        # Находим лучшую атаку противника на этого игрока
        best_opponent_attack = member_data.get('bestOpponentAttack', {})
        
        await db.execute("""
            INSERT INTO war_player_stats (
                war_id, player_tag, player_name, clan_tag,
                attacks_used, attacks_total, stars_earned, destruction_percentage,
                best_opponent_attack_stars, best_opponent_attack_destruction,
                town_hall_level, map_position
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            war_id,
            member_data.get('tag', ''),
            member_data.get('name', ''),
            clan_tag,
            len(attacks),
            2,  # Обычно 2 атаки в КВ
            total_stars,
            avg_destruction,
            best_opponent_attack.get('stars', 0),
            best_opponent_attack.get('destructionPercentage', 0.0),
            member_data.get('townhallLevel', 0),
            member_data.get('mapPosition', 0)
        ))
    
    async def _save_war_attack(
        self,
        db: aiosqlite.Connection,
        war_id: int,
        attacker_tag: str,
        attacker_name: str,
        attack_data: Dict[str, Any]
    ):
        """Сохранить атаку в войне"""
        await db.execute("""
            INSERT INTO war_attacks (
                war_id, attacker_tag, attacker_name,
                defender_tag, defender_name,
                stars, destruction_percentage, attack_order, duration
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            war_id,
            attacker_tag,
            attacker_name,
            attack_data.get('defenderTag', ''),
            attack_data.get('defenderName', ''),
            attack_data.get('stars', 0),
            attack_data.get('destructionPercentage', 0.0),
            attack_data.get('order', 0),
            attack_data.get('duration', 0)
        ))
    
    async def get_clan_war_history(
        self,
        clan_tag: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить историю войн клана
        
        Args:
            clan_tag: Тег клана
            limit: Количество последних войн
            
        Returns:
            Список войн
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM clan_wars
                    WHERE clan_tag = ?
                    ORDER BY end_time DESC
                    LIMIT ?
                """, (clan_tag, limit))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting war history: {e}")
            return []
    
    async def get_player_war_stats(
        self,
        player_tag: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получить статистику игрока по войнам
        
        Args:
            player_tag: Тег игрока
            limit: Количество последних войн
            
        Returns:
            Список статистики
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT wps.*, cw.opponent_name, cw.result, cw.end_time
                    FROM war_player_stats wps
                    JOIN clan_wars cw ON wps.war_id = cw.id
                    WHERE wps.player_tag = ?
                    ORDER BY cw.end_time DESC
                    LIMIT ?
                """, (player_tag, limit))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting player war stats: {e}")
            return []


# Глобальный экземпляр
_war_stats_service: Optional[WarStatsService] = None


def init_war_stats_service(db_path: str) -> WarStatsService:
    """Инициализация глобального сервиса статистики войн"""
    global _war_stats_service
    _war_stats_service = WarStatsService(db_path)
    return _war_stats_service


def get_war_stats_service() -> WarStatsService:
    """Получение глобального сервиса статистики войн"""
    global _war_stats_service
    if _war_stats_service is None:
        raise RuntimeError("War stats service not initialized. Call init_war_stats_service() first.")
    return _war_stats_service
