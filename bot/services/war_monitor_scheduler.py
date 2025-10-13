"""
Планировщик мониторинга клановых войн
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import aiosqlite

logger = logging.getLogger(__name__)


class WarMonitorScheduler:
    """Планировщик для мониторинга КВ и отправки уведомлений"""
    
    def __init__(self, db_path: str):
        # Извлекаем путь из database URL
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
        
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 300  # 5 минут
    
    async def start(self):
        """Запуск планировщика"""
        if self.is_running:
            logger.warning("War monitor scheduler is already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("War monitor scheduler started")
    
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
        
        logger.info("War monitor scheduler stopped")
    
    async def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                await self._check_wars()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in war monitor loop: {e}")
                await asyncio.sleep(60)  # Подождать минуту при ошибке
    
    async def _check_wars(self):
        """Проверить все активные войны"""
        try:
            from .extended_clash_api import ExtendedClashAPI
            from .war_notification_service import get_war_notification_service
            from .clan_database_service import get_clan_db_service
            
            war_notif = get_war_notification_service()
            clan_db = get_clan_db_service()
            
            # Получаем список зарегистрированных кланов
            clans = await self._get_registered_clans()
            
            for clan in clans:
                try:
                    # Получаем данные войны из API
                    # TODO: Нужно получить ExtendedClashAPI instance
                    # war_data = await clash_api.get_current_war(clan['clan_tag'])
                    
                    # Пока заглушка - в реальности нужно получать из API
                    war_data = None
                    
                    if not war_data:
                        continue
                    
                    state = war_data.get('state', '')
                    
                    # Если война в боевом дне
                    if state == 'inWar':
                        # Начать отслеживание если еще не начато
                        await war_notif.start_war_tracking(
                            clan_tag=clan['clan_tag'],
                            chat_id=clan['chat_id'],
                            war_data=war_data
                        )
                        
                        # Обновить тикер
                        await war_notif.update_ticker(
                            clan_tag=clan['clan_tag'],
                            war_data=war_data
                        )
                        
                        # Проверить, не пора ли отправить H-6
                        await self._check_h6_reminder(
                            clan['clan_tag'],
                            war_data,
                            war_notif
                        )
                    
                    # Если война завершена
                    elif state == 'warEnded':
                        war_id = war_notif._generate_war_id(war_data)
                        await war_notif.cleanup_war_messages(
                            clan_tag=clan['clan_tag'],
                            war_id=war_id
                        )
                    
                except Exception as e:
                    logger.error(f"Error checking war for clan {clan.get('clan_tag')}: {e}")
            
        except Exception as e:
            logger.error(f"Error in _check_wars: {e}")
    
    async def _check_h6_reminder(
        self,
        clan_tag: str,
        war_data: Dict[str, Any],
        war_notif
    ):
        """Проверить, не пора ли отправить H-6 напоминание"""
        try:
            end_time_str = war_data.get('endTime', '')
            if not end_time_str:
                return
            
            # Парсим время окончания
            end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%S.%fZ")
            now = datetime.utcnow()
            
            # Вычисляем время до конца
            time_left = (end_time - now).total_seconds() / 3600  # в часах
            
            # Если осталось от 5.5 до 6.5 часов - отправляем
            if 5.5 <= time_left <= 6.5:
                await war_notif.send_h6_reminder(
                    clan_tag=clan_tag,
                    war_data=war_data
                )
        
        except Exception as e:
            logger.error(f"Error checking H-6 reminder: {e}")
    
    async def _get_registered_clans(self) -> List[Dict[str, Any]]:
        """Получить список зарегистрированных кланов"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT clan_tag, chat_id FROM registered_clans
                    WHERE is_active = 1
                """)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting registered clans: {e}")
            return []


# Глобальный экземпляр
_war_monitor_scheduler: Optional[WarMonitorScheduler] = None


def init_war_monitor_scheduler(db_path: str) -> WarMonitorScheduler:
    """Инициализация глобального планировщика мониторинга КВ"""
    global _war_monitor_scheduler
    _war_monitor_scheduler = WarMonitorScheduler(db_path)
    return _war_monitor_scheduler


def get_war_monitor_scheduler() -> WarMonitorScheduler:
    """Получение глобального планировщика мониторинга КВ"""
    global _war_monitor_scheduler
    if _war_monitor_scheduler is None:
        raise RuntimeError("War monitor scheduler not initialized.")
    return _war_monitor_scheduler


async def start_war_monitor_scheduler():
    """Запуск планировщика мониторинга КВ"""
    scheduler = get_war_monitor_scheduler()
    await scheduler.start()


async def stop_war_monitor_scheduler():
    """Остановка планировщика мониторинга КВ"""
    scheduler = get_war_monitor_scheduler()
    await scheduler.stop()
