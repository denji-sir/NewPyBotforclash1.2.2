"""
NewPyBot для Clash of Clans v1.2.2
Основной файл бота со всеми интегрированными системами
"""

import asyncio
import logging
import os
import sys
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импорты компонентов бота
from bot.config.clan_config import init_clan_config, get_coc_api_keys
from bot.services.clan_system_manager import init_clan_system

# Импорты системы приветствий
from bot.integrations.greeting_integration import initialize_greeting_system, shutdown_greeting_system
from bot.handlers.greeting_commands import router as greeting_router
from bot.handlers.greeting_events import router as greeting_events_router

# Импорты системы достижений
try:
    from bot.integrations.achievement_integration import achievement_integration_manager
    from bot.handlers.achievement_commands import router as achievement_router
    ACHIEVEMENTS_AVAILABLE = True
except ImportError:
    ACHIEVEMENTS_AVAILABLE = False
    logging.warning("Achievement system not found, running without achievements")

# Импорты системы паспортов
try:
    from bot.handlers.passport_commands import passport_router
    PASSPORT_AVAILABLE = True
except ImportError:
    PASSPORT_AVAILABLE = False
    logging.warning("Passport system not found, running without passports")

# Импорты системы ежедневных ресурсов
try:
    from bot.services.daily_baseline_scheduler import daily_baseline_scheduler
    DAILY_RESOURCES_AVAILABLE = True
except ImportError:
    DAILY_RESOURCES_AVAILABLE = False
    logging.warning("Daily resources system not found, running without daily resources tracking")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class NewPyBot:
    """
    Основной класс бота NewPyBot для Clash of Clans
    """
    
    def __init__(self, token: str, coc_api_keys: list, database_path: str = "data/bot.db"):
        """
        Инициализация бота
        
        Args:
            token: Telegram Bot Token
            coc_api_keys: Список API ключей Clash of Clans
            database_path: Путь к файлу базы данных
        """
        self.token = token
        self.coc_api_keys = coc_api_keys
        self.database_path = database_path
        
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.clan_manager = None
        
        self._initialized = False
    
    async def initialize(self):
        """Инициализация всех систем бота"""
        
        if self._initialized:
            logger.warning("Bot already initialized")
            return
        
        try:
            logger.info("🚀 Initializing NewPyBot v1.2.2...")
            
            # 1. Создаем бота и диспетчер
            self.bot = Bot(token=self.token)
            self.dp = Dispatcher(storage=MemoryStorage())
            
            # 2. Инициализируем конфигурацию кланов
            clan_config = init_clan_config(
                coc_api_keys=self.coc_api_keys,
                database_path=self.database_path,
                max_clans_per_chat=10
            )
            
            # Проверяем валидность конфигурации
            validation_errors = clan_config.validate()
            if validation_errors:
                logger.error("❌ Clan configuration errors:")
                for error in validation_errors:
                    logger.error(f"  - {error}")
                raise ValueError("Invalid clan configuration")
            
            # 3. Инициализируем систему кланов
            logger.info("📊 Initializing clan system...")
            self.clan_manager = await init_clan_system(
                bot=self.bot,
                dp=self.dp,
                coc_api_keys=self.coc_api_keys,
                db_path=self.database_path
            )
            
            # 4. Инициализируем систему приветствий
            logger.info("🤝 Initializing greeting system...")
            await initialize_greeting_system(self.bot)
            
            # 5. Регистрируем роутеры системы приветствий
            self.dp.include_router(greeting_router)
            self.dp.include_router(greeting_events_router)
            logger.info("✅ Greeting system handlers registered")
            
            # 6. Инициализируем систему достижений (если доступна)
            if ACHIEVEMENTS_AVAILABLE:
                logger.info("🏆 Initializing achievement system...")
                await achievement_integration_manager.initialize(self.bot, self.dp)
                self.dp.include_router(achievement_router)
                logger.info("✅ Achievement system initialized")
            
            # 7. Регистрируем систему паспортов (если доступна)
            if PASSPORT_AVAILABLE:
                logger.info("📋 Registering passport system...")
                self.dp.include_router(passport_router)
                logger.info("✅ Passport system registered")
            
            # 8. Запускаем планировщик ежедневных базисов (если доступен)
            if DAILY_RESOURCES_AVAILABLE:
                logger.info("⏰ Starting daily baseline scheduler...")
                await daily_baseline_scheduler.start()
                logger.info("✅ Daily baseline scheduler started")
            
            # 9. Устанавливаем команды бота
            await self._setup_bot_commands()
            
            # 10. Проверяем статус всех систем
            await self._check_systems_status()
            
            self._initialized = True
            logger.info("✅ NewPyBot fully initialized!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bot: {e}")
            await self.shutdown()
            raise
    
    async def _setup_bot_commands(self):
        """Настройка списка команд бота"""
        
        commands = [
            # Основные команды
            BotCommand(command="start", description="🚀 Запуск бота"),
            BotCommand(command="help", description="📚 Помощь по командам"),
            BotCommand(command="status", description="📊 Статус бота"),
            
            # Команды кланов
            BotCommand(command="register_clan", description="🏰 Регистрация клана"),
            BotCommand(command="clan_list", description="📋 Список кланов"),
            BotCommand(command="clan_info", description="ℹ️ Информация о клане"),
            BotCommand(command="clan_members", description="👥 Участники клана"),
            BotCommand(command="clan_stats", description="📊 Статистика клана"),
            
            # Команды приветствий
            BotCommand(command="greeting", description="🤝 Настройка приветствий"),
            BotCommand(command="greeting_on", description="✅ Включить приветствия"),
            BotCommand(command="greeting_off", description="❌ Выключить приветствия"),
        ]
        
        # Добавляем команды достижений (если доступны)
        if ACHIEVEMENTS_AVAILABLE:
            commands.extend([
                BotCommand(command="achievements", description="🏆 Система достижений"),
                BotCommand(command="my_progress", description="📈 Мой прогресс"),
            ])
        
        # Добавляем команды паспортов (если доступны)
        if PASSPORT_AVAILABLE:
            commands.extend([
                BotCommand(command="create_passport", description="📋 Создать паспорт"),
                BotCommand(command="passport", description="👤 Мой паспорт"),
                BotCommand(command="passport_list", description="📄 Список паспортов"),
            ])
        
        await self.bot.set_my_commands(commands)
        logger.info(f"✅ Set {len(commands)} bot commands")
    
    async def _check_systems_status(self):
        """Проверка статуса всех систем"""
        
        status_report = []
        
        # Статус системы кланов
        if self.clan_manager:
            clan_status = await self.clan_manager.get_system_status()
            status_report.append(f"🏰 Clan System: {clan_status}")
        
        # Статус системы приветствий
        try:
            from bot.integrations.greeting_integration import greeting_integration
            greeting_info = await greeting_integration.get_greeting_statistics_summary()
            if greeting_info:
                status_report.append(f"🤝 Greeting System: {greeting_info.get('enabled_chats', 0)} active chats")
            else:
                status_report.append("🤝 Greeting System: Active")
        except Exception as e:
            status_report.append(f"🤝 Greeting System: Error - {e}")
        
        # Статус системы достижений
        if ACHIEVEMENTS_AVAILABLE:
            status_report.append("🏆 Achievement System: Active")
        else:
            status_report.append("🏆 Achievement System: Not Available")
        
        # Статус системы паспортов
        if PASSPORT_AVAILABLE:
            status_report.append("📋 Passport System: Active")
        else:
            status_report.append("📋 Passport System: Not Available")
        
        logger.info("📊 Systems Status Report:")
        for status in status_report:
            logger.info(f"  {status}")
    
    async def start_polling(self):
        """Запуск поллинга бота"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.info("🚀 Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except KeyboardInterrupt:
            logger.info("👋 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            raise
    
    async def shutdown(self):
        """Корректное завершение работы бота"""
        
        try:
            logger.info("🛑 Shutting down NewPyBot...")
            
            # Завершаем систему приветствий
            try:
                await shutdown_greeting_system()
                logger.info("✅ Greeting system shut down")
            except Exception as e:
                logger.error(f"❌ Error shutting down greeting system: {e}")
            
            # Завершаем систему достижений
            if ACHIEVEMENTS_AVAILABLE:
                try:
                    await achievement_integration_manager.shutdown()
                    logger.info("✅ Achievement system shut down")
                except Exception as e:
                    logger.error(f"❌ Error shutting down achievement system: {e}")
            
            # Останавливаем планировщик ежедневных базисов
            if DAILY_RESOURCES_AVAILABLE:
                try:
                    await daily_baseline_scheduler.stop()
                    logger.info("✅ Daily baseline scheduler stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping daily baseline scheduler: {e}")
            
            # Закрываем сессию бота
            if self.bot:
                await self.bot.session.close()
                logger.info("✅ Bot session closed")
            
            logger.info("👋 NewPyBot shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")


async def main():
    """Основная функция для запуска бота"""
    
    # Получаем конфигурацию из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    # API ключи Clash of Clans
    coc_api_keys = []
    for i in range(1, 6):  # Поддерживаем до 5 ключей
        key = os.getenv(f'COC_API_KEY_{i}')
        if key:
            coc_api_keys.append(key)
    
    if not coc_api_keys:
        # Пытаемся получить один ключ
        single_key = os.getenv('COC_API_KEY')
        if single_key:
            coc_api_keys.append(single_key)
        else:
            logger.warning("⚠️ No CoC API keys provided, clan functionality will be limited")
            coc_api_keys = ["dummy_key"]  # Заглушка для работы без CoC API
    
    # Путь к базе данных
    database_path = os.getenv('DATABASE_PATH', 'data/bot.db')
    
    # Создаем директорию для данных
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    
    # Создаем и запускаем бота
    bot = NewPyBot(
        token=token,
        coc_api_keys=coc_api_keys,
        database_path=database_path
    )
    
    try:
        await bot.start_polling()
    finally:
        await bot.shutdown()


def run_bot():
    """Функция для запуска бота"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Запуск бота
    run_bot()