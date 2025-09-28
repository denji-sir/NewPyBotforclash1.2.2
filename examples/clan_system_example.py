"""
Пример инициализации и запуска системы кланов
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config.clan_config import init_clan_config, get_coc_api_keys
from bot.services.clan_system_manager import init_clan_system

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Основная функция для запуска бота с системой кланов"""
    
    # 1. Инициализируем конфигурацию
    config = init_clan_config(
        coc_api_keys=[
            "YOUR_COC_API_KEY_1",
            "YOUR_COC_API_KEY_2",  # Можно несколько для ротации
        ],
        database_path="data/clans.db",
        max_clans_per_chat=10
    )
    
    # Проверяем валидность конфигурации
    validation_errors = config.validate()
    if validation_errors:
        logger.error("Configuration errors:")
        for error in validation_errors:
            logger.error(f"  - {error}")
        return
    
    # 2. Создаем бота и диспетчер
    bot = Bot(token="YOUR_BOT_TOKEN")
    dp = Dispatcher(storage=MemoryStorage())
    
    try:
        # 3. Инициализируем систему кланов
        logger.info("🚀 Initializing clan system...")
        clan_manager = await init_clan_system(
            bot=bot,
            dp=dp,
            coc_api_keys=config.coc_api_keys,
            db_path=config.database_path
        )
        
        # 4. Проверяем статус системы
        status = await clan_manager.get_system_status()
        logger.info(f"📊 System status: {status}")
        
        # 5. Запускаем поллинг
        logger.info("✅ Starting bot polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    # Запуск бота
    asyncio.run(main())