"""
Главный модуль инициализации бота
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import BotConfig
from .handlers import (
    greeting_router,
    greeting_events_router,
    extended_router,
    clan_router,
    passport_router,
    binding_router,
    admin_binding_router,
    achievement_router,
    contextual_router,
    advanced_contextual_router
)
from .handlers.notification_commands import notification_router
from .handlers.clan_stats_commands import router as clan_stats_router, ChatStatisticsMiddleware
from .handlers.extended_clash_commands import init_extended_services
from .services.extended_clash_api import ExtendedClashAPI
from .services.coc_api_service import init_coc_api_service
from .services.clan_database_service import ClanDatabaseService, init_clan_db_service
from .services.database_init import DatabaseInitializer
from .services.passport_database_service import init_passport_db_service
from .services.greeting_service import init_greeting_service, get_greeting_service
from .services.daily_resources_service import DailyResourcesService
from .services.achievement_service import AchievementService
from .services.daily_baseline_scheduler import (
    init_daily_baseline_scheduler, 
    start_daily_baseline_scheduler, 
    stop_daily_baseline_scheduler
)
from .services.notification_service import init_notification_service
from .services.war_stats_service import init_war_stats_service
from .services.raid_stats_service import init_raid_stats_service
from .services.war_notification_service import init_war_notification_service
from .services.war_monitor_scheduler import (
    init_war_monitor_scheduler,
    start_war_monitor_scheduler,
    stop_war_monitor_scheduler
)
from .services.donation_history_service import init_donation_history_service
from .services.donation_archive_scheduler import (
    init_donation_archive_scheduler,
    start_donation_archive_scheduler,
    stop_donation_archive_scheduler
)
from .services.rate_limit_service import init_rate_limit_service
from .middlewares.rate_limit_middleware import RateLimitMiddleware
from .handlers.rate_limit_admin_commands import router as rate_limit_admin_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class CoClashBot:
    """Основной класс бота для Clash of Clans"""
    
    def __init__(self, config: BotConfig):
        """
        Инициализация бота
        
        Args:
            config: Конфигурация бота
        """
        self.config = config
        
        # Создаем бота
        self.bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        # Создаем диспетчер
        storage = MemoryStorage()
        self.dp = Dispatcher(storage=storage)
        
        # Сервисы
        self.clash_api: Optional[ExtendedClashAPI] = None
        self.db_service: Optional[ClanDatabaseService] = None
        
        # Регистрируем middleware
        self.dp.message.middleware(ChatStatisticsMiddleware())     # Статистика чата
        self.dp.message.middleware(RateLimitMiddleware())          # Защита от спама
        
        # Регистрируем роутеры в правильном порядке
        self.dp.include_router(greeting_router)           # Команды приветствий и /commands
        self.dp.include_router(greeting_events_router)    # События новых участников
        self.dp.include_router(clan_router)               # Команды кланов
        self.dp.include_router(extended_router)           # Расширенные команды CoC
        self.dp.include_router(passport_router)           # Команды паспортов
        self.dp.include_router(binding_router)            # Привязка игроков
        self.dp.include_router(admin_binding_router)      # Админ команды привязок
        self.dp.include_router(achievement_router)        # Достижения
        self.dp.include_router(notification_router)       # Уведомления
        self.dp.include_router(clan_stats_router)         # Статистика кланов
        self.dp.include_router(contextual_router)         # Контекстные команды
        self.dp.include_router(advanced_contextual_router) # Расширенные контекстные
        self.dp.include_router(rate_limit_admin_router)   # Админ команды rate limiting
    
    
    async def init_services(self):
        """Инициализация сервисов"""
        
        try:
            # Инициализируем Clash API
            if self.config.clash_tokens:
                self.clash_api = ExtendedClashAPI(self.config.clash_tokens)
                init_coc_api_service(self.config.clash_tokens)
                logger.info(f"Clash API инициализован с {len(self.config.clash_tokens)} токенами")
            else:
                logger.warning("Токены Clash API не настроены")
            
            # Инициализируем базу данных
            if self.config.database_url:
                # Инициализируем схему БД
                db_initializer = DatabaseInitializer(self.config.database_url)
                await db_initializer.initialize_database()
                
                # Инициализируем все сервисы БД с единым путем
                self.db_service = ClanDatabaseService(self.config.database_url)
                init_clan_db_service(self.config.database_url)
                init_passport_db_service(self.config.database_url)
                
                # Инициализируем дополнительные сервисы
                init_greeting_service(self.config.database_url)
                self.greeting_service = get_greeting_service()
                await self.greeting_service.initialize_database()
                self.daily_resources_service = DailyResourcesService(self.config.database_url)
                self.achievement_service = AchievementService(self.config.database_url)
                
                # Инициализируем планировщик базисов
                init_daily_baseline_scheduler(self.config.database_url)
                
                # Инициализируем сервис уведомлений
                init_notification_service(self.bot)
                
                # Инициализируем сервисы статистики
                init_war_stats_service(self.config.database_url)
                init_raid_stats_service(self.config.database_url)
                
                # Инициализируем сервис КВ-оповещений
                init_war_notification_service(self.bot, self.config.database_url)
                init_war_monitor_scheduler(self.config.database_url)
                
                # Инициализируем сервис истории донатов
                init_donation_history_service(self.config.database_url)
                init_donation_archive_scheduler(self.config.database_url)
                
                # Инициализируем сервис rate limiting
                rate_limit_service = init_rate_limit_service(self.config.database_url)
                await rate_limit_service.initialize_database()
                logger.info("✅ Rate limiting инициализирован")
                
                logger.info("База данных и все сервисы инициализированы")
            else:
                logger.warning("База данных не настроена")
            
            # Инициализируем сервисы для расширенных команд
            if self.clash_api and self.db_service:
                init_extended_services(self.clash_api, self.db_service)
                logger.info("Расширенные сервисы инициализированы")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации сервисов: {e}")
            raise
    
    async def start_polling(self):
        """Запуск бота в режиме polling"""
        
        try:
            # Инициализируем сервисы
            await self.init_services()
            
            # Получаем информацию о боте
            bot_info = await self.bot.get_me()
            logger.info(f"Бот запущен: @{bot_info.username}")
            
            # Запускаем планировщики
            if self.config.database_url:
                await start_daily_baseline_scheduler()
                logger.info("Планировщик ежедневных базисов запущен")
                
                await start_war_monitor_scheduler()
                logger.info("Планировщик мониторинга КВ запущен")
                
                await start_donation_archive_scheduler()
                logger.info("Планировщик архивирования донатов запущен")
            
            # Запускаем polling
            await self.dp.start_polling(self.bot, skip_updates=True)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        finally:
            # Останавливаем планировщики
            if self.config.database_url:
                await stop_daily_baseline_scheduler()
                logger.info("Планировщик ежедневных базисов остановлен")
                
                await stop_war_monitor_scheduler()
                logger.info("Планировщик мониторинга КВ остановлен")
                
                await stop_donation_archive_scheduler()
                logger.info("Планировщик архивирования донатов остановлен")
            
            # Закрываем сессию бота
            await self.bot.session.close()
            
            # Закрываем сервисы
            if self.clash_api and hasattr(self.clash_api, 'close'):
                await self.clash_api.close()
            
            if self.db_service and hasattr(self.db_service, 'close'):
                await self.db_service.close()
    
    async def stop(self):
        """Остановка бота"""
        
        logger.info("Остановка бота...")
        
        # Закрываем сервисы
        if self.clash_api and hasattr(self.clash_api, 'close'):
            await self.clash_api.close()
        
        if self.db_service and hasattr(self.db_service, 'close'):
            await self.db_service.close()
        
        # Закрываем сессию бота
        await self.bot.session.close()
        
        logger.info("Бот остановлен")


def create_bot(config: BotConfig) -> CoClashBot:
    """
    Создать экземпляр бота
    
    Args:
        config: Конфигурация бота
        
    Returns:
        CoClashBot: Экземпляр бота
    """
    return CoClashBot(config)


async def run_bot(config: BotConfig):
    """
    Запустить бота
    
    Args:
        config: Конфигурация бота
    """
    bot = create_bot(config)
    
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        await bot.stop()


if __name__ == "__main__":
    # Загружаем конфигурацию
    config = BotConfig.from_env()
    
    # Запускаем бота
    asyncio.run(run_bot(config))
