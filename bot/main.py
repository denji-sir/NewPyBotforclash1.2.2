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
from .handlers import greeting_router
from .handlers.extended_clash_commands import extended_router, init_extended_services
from .services.extended_clash_api import ExtendedClashAPI
from .services.clan_database_service import ClanDatabaseService

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
        
        # Регистрируем роутеры
        self._register_routers()
    
    def _register_routers(self):
        """Регистрация всех роутеров"""
        
        # Базовые команды (приветствие и т.д.)
        self.dp.include_router(greeting_router)
        
        # Расширенные команды CoC
        self.dp.include_router(extended_router)
        
        logger.info("Роутеры зарегистрированы")
    
    async def init_services(self):
        """Инициализация сервисов"""
        
        try:
            # Инициализируем Clash API
            if self.config.clash_tokens:
                self.clash_api = ExtendedClashAPI(self.config.clash_tokens)
                logger.info(f"Clash API инициализован с {len(self.config.clash_tokens)} токенами")
            else:
                logger.warning("Токены Clash API не настроены")
            
            # Инициализируем базу данных
            if self.config.database_url:
                self.db_service = ClanDatabaseService(self.config.database_url)
                await self.db_service.init_database()
                logger.info("База данных инициализирована")
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
            
            # Запускаем polling
            await self.dp.start_polling(self.bot, skip_updates=True)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        finally:
            # Закрываем сессию бота
            await self.bot.session.close()
            
            # Закрываем сервисы
            if self.clash_api:
                await self.clash_api.close()
            
            if self.db_service:
                await self.db_service.close()
    
    async def stop(self):
        """Остановка бота"""
        
        logger.info("Остановка бота...")
        
        # Закрываем сервисы
        if self.clash_api:
            await self.clash_api.close()
        
        if self.db_service:
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