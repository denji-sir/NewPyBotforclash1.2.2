"""
Планировщик для автоматического обновления базисов ресурсов
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from .daily_resources_service import DailyResourcesService

logger = logging.getLogger(__name__)


class DailyBaselineScheduler:
    """Планировщик для обновления базисов ресурсов в 00:00 МСК"""
    
    def __init__(self, db_path: str):
        self.moscow_tz = timezone(timedelta(hours=3))  # МСК = UTC+3
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.daily_resources_service = DailyResourcesService(db_path)
        
    async def start(self):
        """Запуск планировщика"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("Daily baseline scheduler started")
        
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
                
        logger.info("Daily baseline scheduler stopped")
        
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.is_running:
            try:
                # Вычисляем время до следующего запуска (00:00 МСК)
                next_run = self._get_next_midnight_moscow()
                now = datetime.now(self.moscow_tz)
                
                sleep_seconds = (next_run - now).total_seconds()
                
                if sleep_seconds > 0:
                    logger.info(f"Next baseline update scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    await asyncio.sleep(sleep_seconds)
                
                if self.is_running:
                    await self._update_baselines()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Ждем 1 час перед повторной попыткой
                await asyncio.sleep(3600)
                
    def _get_next_midnight_moscow(self) -> datetime:
        """Получение времени следующей полуночи по МСК"""
        now = datetime.now(self.moscow_tz)
        
        # Если сейчас уже после полуночи, берем следующий день
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now >= next_midnight:
            next_midnight += timedelta(days=1)
            
        return next_midnight
        
    async def _update_baselines(self):
        """Обновление базисов для всех игроков"""
        try:
            logger.info("Starting daily baseline update...")
            
            results = await self.daily_resources_service.update_all_baselines()
            
            logger.info(
                f"Daily baseline update completed: "
                f"{results['success']} success, {results['failed']} failed"
            )
            
            if results['errors']:
                logger.warning(f"Errors during baseline update: {results['errors'][:5]}")  # Показываем первые 5 ошибок
                
            # Очищаем старые базисы (старше 30 дней)
            cleaned = await self.daily_resources_service.cleanup_old_baselines(30)
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} old baseline records")
                
        except Exception as e:
            logger.error(f"Failed to update baselines: {e}")
            
    async def force_update(self) -> dict:
        """Принудительное обновление базисов (для тестирования)"""
        logger.info("Force updating baselines...")
        await self._update_baselines()
        return await self.daily_resources_service.update_all_baselines()


# Глобальный экземпляр планировщика
_scheduler = None


def init_daily_baseline_scheduler(db_path: str) -> DailyBaselineScheduler:
    """Инициализация глобального планировщика"""
    global _scheduler
    _scheduler = DailyBaselineScheduler(db_path)
    return _scheduler


def get_daily_baseline_scheduler() -> DailyBaselineScheduler:
    """Получение глобального экземпляра планировщика"""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_daily_baseline_scheduler() first.")
    return _scheduler


async def start_daily_baseline_scheduler():
    """Запуск планировщика базисов"""
    scheduler = get_daily_baseline_scheduler()
    await scheduler.start()


async def stop_daily_baseline_scheduler():
    """Остановка планировщика базисов"""
    scheduler = get_daily_baseline_scheduler()
    await scheduler.stop()