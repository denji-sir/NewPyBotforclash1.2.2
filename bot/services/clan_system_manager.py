"""
Главный модуль для инициализации системы кланов
"""
import logging
from typing import List
from aiogram import Bot, Dispatcher

from .database_init import init_clan_database
from .coc_api_service import init_coc_api_service
from .clan_database_service import init_clan_db_service
from .permission_service import init_permission_service
from ..handlers.clan_commands import clan_router

logger = logging.getLogger(__name__)


class ClanSystemManager:
    """Менеджер системы кланов"""
    
    def __init__(self, db_path: str = "data/clans.db"):
        self.db_path = db_path
        self.is_initialized = False
    
    async def initialize(self, bot: Bot, coc_api_keys: List[str]) -> None:
        """
        Инициализация системы кланов
        
        Args:
            bot: Экземпляр бота
            coc_api_keys: Список ключей CoC API
        """
        try:
            logger.info("Initializing clan system...")
            
            # 1. Инициализируем базу данных
            logger.info("Setting up database...")
            await init_clan_database(self.db_path)
            
            # 2. Инициализируем сервисы
            logger.info("Initializing services...")
            init_coc_api_service(coc_api_keys)
            init_clan_db_service(self.db_path)
            init_permission_service(bot)
            
            self.is_initialized = True
            logger.info("✅ Clan system initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize clan system: {e}")
            raise
    
    def register_handlers(self, dp: Dispatcher) -> None:
        """Регистрация хандлеров команд"""
        if not self.is_initialized:
            raise RuntimeError("Clan system not initialized. Call initialize() first.")
        
        dp.include_router(clan_router)
        logger.info("✅ Clan handlers registered")
    
    async def get_system_status(self) -> dict:
        """Получить статус системы кланов"""
        if not self.is_initialized:
            return {'status': 'not_initialized'}
        
        try:
            from .database_init import DatabaseInitializer
            from .coc_api_service import get_coc_api_service
            
            # Проверяем БД
            db_init = DatabaseInitializer(self.db_path)
            db_status = await db_init.check_database_integrity()
            db_info = await db_init.get_database_info()
            
            # Проверяем CoC API
            coc_api = get_coc_api_service()
            api_status = await coc_api.get_api_status()
            
            return {
                'status': 'initialized',
                'database': {
                    'integrity': db_status,
                    'info': db_info
                },
                'coc_api': api_status,
                'initialized': self.is_initialized
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }


# Глобальный экземпляр менеджера
_clan_system_manager: ClanSystemManager = None


def get_clan_system_manager(db_path: str = "data/clans.db") -> ClanSystemManager:
    """Получить глобальный менеджер системы кланов"""
    global _clan_system_manager
    
    if _clan_system_manager is None:
        _clan_system_manager = ClanSystemManager(db_path)
    
    return _clan_system_manager


async def init_clan_system(bot: Bot, dp: Dispatcher, coc_api_keys: List[str], 
                         db_path: str = "data/clans.db") -> ClanSystemManager:
    """
    Быстрая инициализация системы кланов
    
    Args:
        bot: Экземпляр бота
        dp: Диспетчер
        coc_api_keys: Ключи CoC API
        db_path: Путь к БД
        
    Returns:
        ClanSystemManager: Инициализированный менеджер
    """
    manager = get_clan_system_manager(db_path)
    
    # Инициализируем систему
    await manager.initialize(bot, coc_api_keys)
    
    # Регистрируем хандлеры
    manager.register_handlers(dp)
    
    return manager


# Вспомогательные функции для быстрого доступа
def get_system_status():
    """Получить статус системы (синхронная версия)"""
    manager = get_clan_system_manager()
    return {'initialized': manager.is_initialized}


async def quick_clan_check() -> bool:
    """Быстрая проверка работоспособности системы"""
    try:
        manager = get_clan_system_manager()
        if not manager.is_initialized:
            return False
        
        status = await manager.get_system_status()
        return status.get('database', {}).get('integrity', False)
        
    except Exception:
        return False
