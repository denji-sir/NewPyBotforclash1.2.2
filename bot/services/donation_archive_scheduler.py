"""
Планировщик автоматического архивирования донатов в конце сезона
Сезон заканчивается в последний понедельник месяца в 05:00 UTC
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from .donation_history_service import DonationHistoryService
from .coc_api_service import get_coc_api_service

logger = logging.getLogger(__name__)


class DonationArchiveScheduler:
    """Планировщик для архивирования донатов в конце каждого сезона"""
    
    def __init__(self, db_path: str):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.donation_service = DonationHistoryService(db_path)
        self.db_path = db_path
        
    async def start(self):
        """Запуск планировщика"""
        if self.is_running:
            logger.warning("Donation archive scheduler is already running")
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("Donation archive scheduler started")
        
    async def stop(self):
        """Остановка планировщика"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
                
        logger.info("Donation archive scheduler stopped")
        
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.is_running:
            try:
                # Вычисляем время до следующего конца сезона (последний понедельник месяца 05:00 UTC)
                next_season_end = DonationHistoryService.get_next_season_end()
                now = datetime.now(timezone.utc)
                
                sleep_seconds = (next_season_end - now).total_seconds()
                
                if sleep_seconds > 0:
                    logger.info(
                        f"Next donation archive scheduled for {next_season_end.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                        f"(last Monday of month at 05:00 UTC)"
                    )
                    await asyncio.sleep(sleep_seconds)
                
                if self.is_running:
                    await self._archive_all_clans()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in donation archive scheduler loop: {e}")
                # Ждем 1 час перед повторной попыткой
                await asyncio.sleep(3600)
                
    async def _archive_all_clans(self):
        """Архивировать донаты для всех зарегистрированных кланов"""
        try:
            logger.info("Starting season-end donation archiving...")
            
            season_end_time = datetime.now(timezone.utc)
            year = season_end_time.year
            month = season_end_time.month
            
            # Получаем список всех зарегистрированных кланов
            import aiosqlite
            
            if ':///' in self.db_path:
                db_path = self.db_path.split(':///')[-1]
            elif '://' in self.db_path:
                db_path = self.db_path.split('://')[-1]
            else:
                db_path = self.db_path
            
            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("""
                    SELECT clan_tag, clan_name 
                    FROM registered_clans 
                    WHERE is_active = TRUE
                """)
                clans = await cursor.fetchall()
            
            if not clans:
                logger.info("No active clans found for archiving")
                return
            
            # Получаем API сервис
            try:
                coc_api = get_coc_api_service()
            except RuntimeError:
                logger.error("CoC API service not initialized, cannot archive donations")
                return
            
            success_count = 0
            failed_count = 0
            total_archived_members = 0
            total_donations = 0
            
            # Архивируем каждый клан
            for clan_tag, clan_name in clans:
                try:
                    # Получаем текущие данные клана через API
                    clan_data = await coc_api.get_clan(clan_tag)
                    
                    if not clan_data:
                        logger.warning(f"Could not fetch clan data for {clan_tag}")
                        failed_count += 1
                        continue
                    
                    members = clan_data.get('memberList', [])
                    
                    # Архивируем донаты
                    result = await self.donation_service.archive_clan_donations(
                        clan_tag=clan_tag,
                        clan_name=clan_name,
                        members=members,
                        season_end_time=season_end_time
                    )
                    
                    if result.get('success'):
                        success_count += 1
                        total_archived_members += result.get('archived_members', 0)
                        total_donations += result.get('total_donations', 0)
                        logger.info(
                            f"✓ Archived {result.get('archived_members')} members "
                            f"from {clan_name} ({result.get('total_donations'):,} donations)"
                        )
                    else:
                        failed_count += 1
                        logger.error(f"✗ Failed to archive {clan_name}: {result.get('error')}")
                    
                    # Небольшая пауза между кланами для предотвращения rate limit
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error archiving clan {clan_tag}: {e}")
                    failed_count += 1
            
            logger.info(
                f"Season-end donation archiving completed for {year}-{month:02d}: "
                f"{success_count} clans success, {failed_count} failed, "
                f"{total_archived_members} members archived, "
                f"{total_donations:,} total donations"
            )
            
            # Очищаем старые записи (хранить последние 12 месяцев)
            cleaned = await self.donation_service.cleanup_old_history(months_to_keep=12)
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} old donation history records")
                
        except Exception as e:
            logger.error(f"Failed to archive donations: {e}")
            
    async def force_archive(self) -> dict:
        """Принудительное архивирование (для тестирования)"""
        logger.info("Force archiving donations...")
        await self._archive_all_clans()
        return {'status': 'completed', 'timestamp': datetime.now(timezone.utc).isoformat()}


# Глобальный экземпляр планировщика
_scheduler: Optional[DonationArchiveScheduler] = None


def init_donation_archive_scheduler(db_path: str) -> DonationArchiveScheduler:
    """Инициализация глобального планировщика"""
    global _scheduler
    _scheduler = DonationArchiveScheduler(db_path)
    return _scheduler


def get_donation_archive_scheduler() -> DonationArchiveScheduler:
    """Получение глобального экземпляра планировщика"""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Donation archive scheduler not initialized")
    return _scheduler


async def start_donation_archive_scheduler():
    """Запуск планировщика архивирования донатов"""
    scheduler = get_donation_archive_scheduler()
    await scheduler.start()


async def stop_donation_archive_scheduler():
    """Остановка планировщика архивирования донатов"""
    scheduler = get_donation_archive_scheduler()
    await scheduler.stop()
