"""
Сервис для сохранения статистики рейдов
"""
import logging
import aiosqlite
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RaidStatsService:
    """Сервис для работы со статистикой рейдов"""
    
    def __init__(self, db_path: str):
        # Извлекаем путь из database URL
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
    
    async def save_raid_weekend_result(
        self,
        clan_tag: str,
        clan_name: str,
        raid_data: Dict[str, Any]
    ) -> int:
        """
        Сохранить результаты рейдовых выходных
        
        Args:
            clan_tag: Тег клана
            clan_name: Название клана
            raid_data: Данные рейда из API
            
        Returns:
            ID сохраненного рейда
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Подсчитываем общую статистику
                total_loot = raid_data.get('capitalTotalLoot', 0)
                raids_completed = raid_data.get('raidsCompleted', 0)
                total_attacks = raid_data.get('totalAttacks', 0)
                enemy_districts_destroyed = raid_data.get('enemyDistrictsDestroyed', 0)
                defensive_reward = raid_data.get('defensiveReward', 0)
                offensive_reward = raid_data.get('offensiveReward', 0)
                
                # Сохраняем основную информацию о рейде
                cursor = await db.execute("""
                    INSERT INTO raid_weekends (
                        clan_tag, clan_name, start_time, end_time, state,
                        total_loot, raids_completed, total_attacks,
                        enemy_districts_destroyed, defensive_reward, offensive_reward, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clan_tag,
                    clan_name,
                    raid_data.get('startTime', ''),
                    raid_data.get('endTime', ''),
                    raid_data.get('state', 'ended'),
                    total_loot,
                    raids_completed,
                    total_attacks,
                    enemy_districts_destroyed,
                    defensive_reward,
                    offensive_reward,
                    json.dumps(raid_data.get('metadata', {}))
                ))
                
                raid_id = cursor.lastrowid
                
                # Сохраняем статистику игроков
                members = raid_data.get('members', [])
                for member in members:
                    await self._save_player_raid_stats(db, raid_id, member, clan_tag)
                    
                    # Сохраняем атаки игрока
                    attacks = member.get('attacks', [])
                    for attack in attacks:
                        await self._save_raid_attack(
                            db, raid_id, 
                            member.get('tag', ''), 
                            member.get('name', ''),
                            attack
                        )
                
                await db.commit()
                logger.info(f"Raid weekend result saved for {clan_name}: {total_loot} loot, {raids_completed} raids")
                return raid_id
                
        except Exception as e:
            logger.error(f"Error saving raid weekend result: {e}")
            return 0
    
    async def _save_player_raid_stats(
        self,
        db: aiosqlite.Connection,
        raid_id: int,
        member_data: Dict[str, Any],
        clan_tag: str
    ):
        """Сохранить статистику игрока в рейде"""
        await db.execute("""
            INSERT INTO raid_player_stats (
                raid_id, player_tag, player_name, clan_tag,
                attacks_used, attacks_limit, capital_resources_looted, raids_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            raid_id,
            member_data.get('tag', ''),
            member_data.get('name', ''),
            clan_tag,
            member_data.get('attacks', 0),
            member_data.get('attackLimit', 6),
            member_data.get('capitalResourcesLooted', 0),
            member_data.get('bonusAttackLimit', 0)
        ))
    
    async def _save_raid_attack(
        self,
        db: aiosqlite.Connection,
        raid_id: int,
        attacker_tag: str,
        attacker_name: str,
        attack_data: Dict[str, Any]
    ):
        """Сохранить атаку в рейде"""
        await db.execute("""
            INSERT INTO raid_attacks (
                raid_id, attacker_tag, attacker_name,
                district_id, district_name, stars, destruction_percentage, loot
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            raid_id,
            attacker_tag,
            attacker_name,
            attack_data.get('districtId', 0),
            attack_data.get('districtName', ''),
            attack_data.get('stars', 0),
            attack_data.get('destructionPercent', 0.0),
            attack_data.get('capitalResourcesLooted', 0)
        ))
    
    async def get_clan_raid_history(
        self,
        clan_tag: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить историю рейдов клана
        
        Args:
            clan_tag: Тег клана
            limit: Количество последних рейдов
            
        Returns:
            Список рейдов
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM raid_weekends
                    WHERE clan_tag = ?
                    ORDER BY end_time DESC
                    LIMIT ?
                """, (clan_tag, limit))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting raid history: {e}")
            return []
    
    async def get_player_raid_stats(
        self,
        player_tag: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получить статистику игрока по рейдам
        
        Args:
            player_tag: Тег игрока
            limit: Количество последних рейдов
            
        Returns:
            Список статистики
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT rps.*, rw.total_loot, rw.end_time
                    FROM raid_player_stats rps
                    JOIN raid_weekends rw ON rps.raid_id = rw.id
                    WHERE rps.player_tag = ?
                    ORDER BY rw.end_time DESC
                    LIMIT ?
                """, (player_tag, limit))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting player raid stats: {e}")
            return []
    
    async def get_raid_leaderboard(
        self,
        raid_id: int,
        order_by: str = 'capital_resources_looted'
    ) -> List[Dict[str, Any]]:
        """
        Получить таблицу лидеров рейда
        
        Args:
            raid_id: ID рейда
            order_by: Поле для сортировки
            
        Returns:
            Список игроков с статистикой
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(f"""
                    SELECT * FROM raid_player_stats
                    WHERE raid_id = ?
                    ORDER BY {order_by} DESC
                """, (raid_id,))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting raid leaderboard: {e}")
            return []


# Глобальный экземпляр
_raid_stats_service: Optional[RaidStatsService] = None


def init_raid_stats_service(db_path: str) -> RaidStatsService:
    """Инициализация глобального сервиса статистики рейдов"""
    global _raid_stats_service
    _raid_stats_service = RaidStatsService(db_path)
    return _raid_stats_service


def get_raid_stats_service() -> RaidStatsService:
    """Получение глобального сервиса статистики рейдов"""
    global _raid_stats_service
    if _raid_stats_service is None:
        raise RuntimeError("Raid stats service not initialized. Call init_raid_stats_service() first.")
    return _raid_stats_service
