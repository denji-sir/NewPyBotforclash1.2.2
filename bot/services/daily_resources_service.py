"""
Сервис для отслеживания ежедневных ресурсов игроков
"""
import logging
import aiosqlite
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class DailyResourcesService:
    """Сервис для работы с ежедневными ресурсами игроков"""
    
    def __init__(self, db_path: str = "data/daily_resources.db"):
        self.db_path = db_path
        self.moscow_tz = timezone(timedelta(hours=3))  # МСК = UTC+3
        
    async def initialize_database(self) -> bool:
        """Инициализация базы данных для ежедневных ресурсов"""
        try:
            # Создаем директорию если не существует
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Создаем таблицу для ежедневных базисов
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS daily_resource_baselines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        player_tag TEXT NOT NULL,
                        baseline_date DATE NOT NULL,
                        gold_grab_value INTEGER DEFAULT 0,
                        elixir_escapade_value INTEGER DEFAULT 0,
                        heroic_heist_value INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(player_tag, baseline_date)
                    )
                """)
                
                # Создаем индексы
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_baselines_player_date 
                    ON daily_resource_baselines(player_tag, baseline_date DESC)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_baselines_date 
                    ON daily_resource_baselines(baseline_date)
                """)
                
                await db.commit()
                
            logger.info(f"Daily resources database initialized: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize daily resources database: {e}")
            return False
    
    async def save_daily_baseline(self, player_tag: str, achievements: List[Dict]) -> bool:
        """
        Сохранение ежедневного базиса ресурсов игрока
        
        Args:
            player_tag: Тег игрока
            achievements: Список достижений игрока
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            # Извлекаем значения ключевых достижений
            key_achievements = {
                'Gold Grab': 0,
                'Elixir Escapade': 0,
                'Heroic Heist': 0
            }
            
            for achievement in achievements:
                name = achievement.get('name', '')
                if name in key_achievements:
                    key_achievements[name] = achievement.get('value', 0)
            
            # Получаем текущую дату по МСК
            moscow_now = datetime.now(self.moscow_tz)
            baseline_date = moscow_now.date()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO daily_resource_baselines 
                    (player_tag, baseline_date, gold_grab_value, elixir_escapade_value, heroic_heist_value)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    player_tag,
                    baseline_date,
                    key_achievements['Gold Grab'],
                    key_achievements['Elixir Escapade'],
                    key_achievements['Heroic Heist']
                ))
                
                await db.commit()
                
            logger.info(f"Saved daily baseline for {player_tag} on {baseline_date}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save daily baseline for {player_tag}: {e}")
            return False
    
    async def get_daily_baseline(self, player_tag: str, date: Optional[datetime] = None) -> Optional[Dict]:
        """
        Получение ежедневного базиса ресурсов игрока
        
        Args:
            player_tag: Тег игрока
            date: Дата базиса (по умолчанию - сегодня по МСК)
            
        Returns:
            Dict с базисными значениями или None
        """
        try:
            if date is None:
                moscow_now = datetime.now(self.moscow_tz)
                baseline_date = moscow_now.date()
            else:
                baseline_date = date.date()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT gold_grab_value, elixir_escapade_value, heroic_heist_value, created_at
                    FROM daily_resource_baselines
                    WHERE player_tag = ? AND baseline_date = ?
                """, (player_tag, baseline_date))
                
                row = await cursor.fetchone()
                
                if row:
                    return {
                        'Gold Grab': row[0],
                        'Elixir Escapade': row[1],
                        'Heroic Heist': row[2],
                        'created_at': row[3]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get daily baseline for {player_tag}: {e}")
            return None
    
    async def calculate_daily_resources(self, player_tag: str, current_achievements: List[Dict]) -> Dict:
        """
        Вычисление нафармленных ресурсов за день
        
        Args:
            player_tag: Тег игрока
            current_achievements: Текущие достижения игрока
            
        Returns:
            Dict с информацией о нафармленных ресурсах
        """
        try:
            # Получаем базис на сегодня
            baseline = await self.get_daily_baseline(player_tag)
            
            if not baseline:
                # Если базиса нет, создаем его и возвращаем нули
                await self.save_daily_baseline(player_tag, current_achievements)
                return {
                    'gold_farmed': 0,
                    'elixir_farmed': 0,
                    'dark_elixir_farmed': 0,
                    'total_farmed': 0,
                    'baseline_created': True
                }
            
            # Извлекаем текущие значения достижений
            current_values = {
                'Gold Grab': 0,
                'Elixir Escapade': 0,
                'Heroic Heist': 0
            }
            
            for achievement in current_achievements:
                name = achievement.get('name', '')
                if name in current_values:
                    current_values[name] = achievement.get('value', 0)
            
            # Вычисляем разность
            gold_farmed = max(0, current_values['Gold Grab'] - baseline['Gold Grab'])
            elixir_farmed = max(0, current_values['Elixir Escapade'] - baseline['Elixir Escapade'])
            dark_elixir_farmed = max(0, current_values['Heroic Heist'] - baseline['Heroic Heist'])
            
            total_farmed = gold_farmed + elixir_farmed + dark_elixir_farmed
            
            return {
                'gold_farmed': gold_farmed,
                'elixir_farmed': elixir_farmed,
                'dark_elixir_farmed': dark_elixir_farmed,
                'total_farmed': total_farmed,
                'baseline_created': False,
                'current_totals': current_values,
                'baseline_values': baseline
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate daily resources for {player_tag}: {e}")
            return {
                'gold_farmed': 0,
                'elixir_farmed': 0,
                'dark_elixir_farmed': 0,
                'total_farmed': 0,
                'error': str(e)
            }
    
    async def update_all_baselines(self) -> Dict:
        """
        Обновление базисов для всех привязанных игроков (запускается в 00:00 МСК)
        
        Returns:
            Dict с результатами обновления
        """
        try:
            from .passport_db_service import get_passport_db_service
            from .extended_clash_api import get_extended_clash_api
            
            passport_service = get_passport_db_service()
            extended_api = get_extended_clash_api()
            
            # Получаем всех привязанных игроков
            passports = await passport_service.get_all_passports()
            
            results = {
                'success': 0,
                'failed': 0,
                'errors': []
            }
            
            for passport in passports:
                if not passport.player_tag:
                    continue
                    
                try:
                    # Получаем данные игрока
                    player_data = await extended_api.get_player_detailed_info(passport.player_tag)
                    achievements = player_data.get('achievements', [])
                    
                    if achievements:
                        success = await self.save_daily_baseline(passport.player_tag, achievements)
                        if success:
                            results['success'] += 1
                        else:
                            results['failed'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"No achievements for {passport.player_tag}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Error for {passport.player_tag}: {str(e)}")
                    
                # Небольшая задержка между запросами
                await asyncio.sleep(0.1)
            
            logger.info(f"Baseline update completed: {results['success']} success, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to update all baselines: {e}")
            return {
                'success': 0,
                'failed': 0,
                'errors': [str(e)]
            }
    
    async def cleanup_old_baselines(self, days_to_keep: int = 30) -> int:
        """
        Очистка старых базисов (старше указанного количества дней)
        
        Args:
            days_to_keep: Количество дней для хранения
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            cutoff_date = datetime.now(self.moscow_tz).date() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM daily_resource_baselines
                    WHERE baseline_date < ?
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                await db.commit()
                
            logger.info(f"Cleaned up {deleted_count} old baseline records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old baselines: {e}")
            return 0


# Глобальный экземпляр сервиса
_daily_resources_service = None


def get_daily_resources_service() -> DailyResourcesService:
    """Получение глобального экземпляра сервиса ежедневных ресурсов"""
    global _daily_resources_service
    if _daily_resources_service is None:
        _daily_resources_service = DailyResourcesService()
    return _daily_resources_service