"""
Сервис для управления историей донатов с ежемесячным сбросом
Сезон заканчивается в последний понедельник месяца в 05:00 UTC
"""
import aiosqlite
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from calendar import monthrange

logger = logging.getLogger(__name__)


class DonationHistoryService:
    """Сервис для работы с историей донатов"""
    
    def __init__(self, db_path: str):
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
    
    @staticmethod
    def get_last_monday_of_month(year: int, month: int) -> datetime:
        """
        Получить последний понедельник месяца в 05:00 UTC
        
        Args:
            year: Год
            month: Месяц (1-12)
            
        Returns:
            datetime объект последнего понедельника месяца в 05:00 UTC
        """
        # Получаем последний день месяца
        last_day = monthrange(year, month)[1]
        last_date = datetime(year, month, last_day, 5, 0, 0, tzinfo=timezone.utc)
        
        # Находим последний понедельник (0 = Monday)
        days_to_subtract = (last_date.weekday() - 0) % 7
        if days_to_subtract == 0 and last_date.day == last_day:
            # Если последний день - понедельник, это и есть последний понедельник
            last_monday = last_date
        else:
            # Иначе идем назад до понедельника
            last_monday = last_date - timedelta(days=days_to_subtract)
            if last_monday.day > last_day:
                # Если вышли за границы месяца, берем предыдущий понедельник
                last_monday = last_monday - timedelta(weeks=1)
        
        # Устанавливаем время 05:00 UTC
        last_monday = last_monday.replace(hour=5, minute=0, second=0, microsecond=0)
        
        return last_monday
    
    @staticmethod
    def get_next_season_end() -> datetime:
        """
        Получить дату и время следующего конца сезона
        
        Returns:
            datetime объект следующего конца сезона
        """
        now = datetime.now(timezone.utc)
        
        # Проверяем текущий месяц
        current_month_end = DonationHistoryService.get_last_monday_of_month(now.year, now.month)
        
        if now < current_month_end:
            return current_month_end
        
        # Если прошел конец текущего месяца, берем следующий месяц
        next_month = now.month + 1
        next_year = now.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        return DonationHistoryService.get_last_monday_of_month(next_year, next_month)
    
    @staticmethod
    def is_season_end_time(check_time: Optional[datetime] = None) -> bool:
        """
        Проверить, является ли текущее время концом сезона
        
        Args:
            check_time: Время для проверки (по умолчанию текущее время UTC)
            
        Returns:
            True если сейчас время конца сезона (±5 минут)
        """
        if check_time is None:
            check_time = datetime.now(timezone.utc)
        
        season_end = DonationHistoryService.get_last_monday_of_month(check_time.year, check_time.month)
        
        # Проверяем, находимся ли мы в пределах ±5 минут от конца сезона
        time_diff = abs((check_time - season_end).total_seconds())
        return time_diff <= 300  # 5 минут = 300 секунд
    
    async def archive_clan_donations(
        self,
        clan_tag: str,
        clan_name: str,
        members: List[Dict[str, Any]],
        season_end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Архивировать донаты клана за текущий сезон
        
        Args:
            clan_tag: Тег клана
            clan_name: Имя клана
            members: Список участников с данными о донатах
            season_end_time: Время окончания сезона (по умолчанию текущее время)
            
        Returns:
            Статистика архивирования
        """
        if season_end_time is None:
            season_end_time = datetime.now(timezone.utc)
        
        year = season_end_time.year
        month = season_end_time.month
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                archived_count = 0
                total_donations = 0
                total_received = 0
                active_members = 0
                top_donor = None
                top_donor_amount = 0
                
                # Архивируем данные каждого участника
                for member in members:
                    player_tag = member.get('tag', '')
                    player_name = member.get('name', 'Unknown')
                    donations = member.get('donations', 0)
                    donations_received = member.get('donationsReceived', 0)
                    
                    if donations > 0:
                        active_members += 1
                    
                    total_donations += donations
                    total_received += donations_received
                    
                    # Отслеживаем топ донора
                    if donations > top_donor_amount:
                        top_donor_amount = donations
                        top_donor = {'tag': player_tag, 'name': player_name}
                    
                    # Рассчитываем коэффициент донатов
                    donation_ratio = donations / donations_received if donations_received > 0 else float('inf') if donations > 0 else 0.0
                    
                    # Вставляем или обновляем запись
                    await db.execute("""
                        INSERT INTO monthly_donation_history 
                        (clan_tag, clan_name, player_tag, player_name, year, month, 
                         donations, donations_received, donation_ratio, season_end_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(clan_tag, player_tag, year, month) 
                        DO UPDATE SET
                            donations = excluded.donations,
                            donations_received = excluded.donations_received,
                            donation_ratio = excluded.donation_ratio,
                            season_end_time = excluded.season_end_time,
                            archived_at = CURRENT_TIMESTAMP
                    """, (
                        clan_tag, clan_name, player_tag, player_name, year, month,
                        donations, donations_received, donation_ratio, season_end_time.isoformat()
                    ))
                    archived_count += 1
                
                # Сохраняем сводную статистику сезона
                average_donations = total_donations / active_members if active_members > 0 else 0.0
                
                await db.execute("""
                    INSERT INTO season_donation_summary
                    (clan_tag, clan_name, year, month, total_donations, total_received,
                     active_members, average_donations, top_donor_tag, top_donor_name,
                     top_donor_amount, season_end_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(clan_tag, year, month)
                    DO UPDATE SET
                        total_donations = excluded.total_donations,
                        total_received = excluded.total_received,
                        active_members = excluded.active_members,
                        average_donations = excluded.average_donations,
                        top_donor_tag = excluded.top_donor_tag,
                        top_donor_name = excluded.top_donor_name,
                        top_donor_amount = excluded.top_donor_amount,
                        season_end_time = excluded.season_end_time,
                        archived_at = CURRENT_TIMESTAMP
                """, (
                    clan_tag, clan_name, year, month, total_donations, total_received,
                    active_members, average_donations,
                    top_donor['tag'] if top_donor else None,
                    top_donor['name'] if top_donor else None,
                    top_donor_amount, season_end_time.isoformat()
                ))
                
                await db.commit()
                
                logger.info(
                    f"Archived donations for clan {clan_name} ({clan_tag}): "
                    f"{archived_count} members, {total_donations:,} total donations for {year}-{month:02d}"
                )
                
                return {
                    'success': True,
                    'clan_tag': clan_tag,
                    'clan_name': clan_name,
                    'year': year,
                    'month': month,
                    'archived_members': archived_count,
                    'total_donations': total_donations,
                    'total_received': total_received,
                    'active_members': active_members,
                    'average_donations': round(average_donations, 1),
                    'top_donor': top_donor,
                    'top_donor_amount': top_donor_amount,
                    'season_end_time': season_end_time.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Failed to archive donations for {clan_tag}: {e}")
                await db.rollback()
                return {
                    'success': False,
                    'clan_tag': clan_tag,
                    'error': str(e)
                }
    
    async def get_player_donation_history(
        self,
        player_tag: str,
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Получить историю донатов игрока
        
        Args:
            player_tag: Тег игрока
            limit: Максимальное количество месяцев
            
        Returns:
            Список записей истории донатов
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT clan_tag, clan_name, player_name, year, month,
                       donations, donations_received, donation_ratio,
                       season_end_time, archived_at
                FROM monthly_donation_history
                WHERE player_tag = ?
                ORDER BY year DESC, month DESC
                LIMIT ?
            """, (player_tag, limit))
            
            rows = await cursor.fetchall()
            
            return [
                {
                    'clan_tag': row[0],
                    'clan_name': row[1],
                    'player_name': row[2],
                    'year': row[3],
                    'month': row[4],
                    'donations': row[5],
                    'donations_received': row[6],
                    'donation_ratio': row[7],
                    'season_end_time': row[8],
                    'archived_at': row[9]
                }
                for row in rows
            ]
    
    async def get_clan_season_summary(
        self,
        clan_tag: str,
        year: int,
        month: int
    ) -> Optional[Dict[str, Any]]:
        """
        Получить сводку по сезону для клана
        
        Args:
            clan_tag: Тег клана
            year: Год
            month: Месяц
            
        Returns:
            Сводка сезона или None
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT clan_name, total_donations, total_received, active_members,
                       average_donations, top_donor_tag, top_donor_name,
                       top_donor_amount, season_end_time, archived_at
                FROM season_donation_summary
                WHERE clan_tag = ? AND year = ? AND month = ?
            """, (clan_tag, year, month))
            
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'clan_tag': clan_tag,
                'clan_name': row[0],
                'year': year,
                'month': month,
                'total_donations': row[1],
                'total_received': row[2],
                'active_members': row[3],
                'average_donations': row[4],
                'top_donor_tag': row[5],
                'top_donor_name': row[6],
                'top_donor_amount': row[7],
                'season_end_time': row[8],
                'archived_at': row[9]
            }
    
    async def get_clan_top_donors(
        self,
        clan_tag: str,
        year: int,
        month: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить топ донаторов клана за сезон
        
        Args:
            clan_tag: Тег клана
            year: Год
            month: Месяц
            limit: Количество топ донаторов
            
        Returns:
            Список топ донаторов
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT player_tag, player_name, donations, donations_received, donation_ratio
                FROM monthly_donation_history
                WHERE clan_tag = ? AND year = ? AND month = ?
                ORDER BY donations DESC
                LIMIT ?
            """, (clan_tag, year, month, limit))
            
            rows = await cursor.fetchall()
            
            return [
                {
                    'player_tag': row[0],
                    'player_name': row[1],
                    'donations': row[2],
                    'donations_received': row[3],
                    'donation_ratio': row[4]
                }
                for row in rows
            ]
    
    async def get_all_clan_seasons(self, clan_tag: str, limit: int = 12) -> List[Dict[str, Any]]:
        """
        Получить все сезоны клана
        
        Args:
            clan_tag: Тег клана
            limit: Максимальное количество сезонов
            
        Returns:
            Список сезонов
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT clan_name, year, month, total_donations, total_received,
                       active_members, average_donations, top_donor_name,
                       top_donor_amount, season_end_time
                FROM season_donation_summary
                WHERE clan_tag = ?
                ORDER BY year DESC, month DESC
                LIMIT ?
            """, (clan_tag, limit))
            
            rows = await cursor.fetchall()
            
            return [
                {
                    'clan_tag': clan_tag,
                    'clan_name': row[0],
                    'year': row[1],
                    'month': row[2],
                    'total_donations': row[3],
                    'total_received': row[4],
                    'active_members': row[5],
                    'average_donations': row[6],
                    'top_donor_name': row[7],
                    'top_donor_amount': row[8],
                    'season_end_time': row[9]
                }
                for row in rows
            ]
    
    async def cleanup_old_history(self, months_to_keep: int = 12) -> int:
        """
        Очистить старые записи истории
        
        Args:
            months_to_keep: Количество месяцев для хранения
            
        Returns:
            Количество удаленных записей
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=months_to_keep * 30)
        cutoff_year = cutoff_date.year
        cutoff_month = cutoff_date.month
        
        async with aiosqlite.connect(self.db_path) as db:
            # Удаляем старые записи из истории
            cursor = await db.execute("""
                DELETE FROM monthly_donation_history
                WHERE (year < ?) OR (year = ? AND month < ?)
            """, (cutoff_year, cutoff_year, cutoff_month))
            
            deleted_history = cursor.rowcount
            
            # Удаляем старые сводки
            cursor = await db.execute("""
                DELETE FROM season_donation_summary
                WHERE (year < ?) OR (year = ? AND month < ?)
            """, (cutoff_year, cutoff_year, cutoff_month))
            
            deleted_summary = cursor.rowcount
            
            await db.commit()
            
            total_deleted = deleted_history + deleted_summary
            if total_deleted > 0:
                logger.info(f"Cleaned up {total_deleted} old donation history records")
            
            return total_deleted


# Глобальный экземпляр сервиса
_donation_history_service: Optional[DonationHistoryService] = None


def init_donation_history_service(db_path: str) -> DonationHistoryService:
    """Инициализация глобального сервиса истории донатов"""
    global _donation_history_service
    _donation_history_service = DonationHistoryService(db_path)
    return _donation_history_service


def get_donation_history_service() -> DonationHistoryService:
    """Получение глобального экземпляра сервиса"""
    if _donation_history_service is None:
        raise RuntimeError("Donation history service not initialized")
    return _donation_history_service
