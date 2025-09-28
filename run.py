"""
Точка входа для запуска бота
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.main import run_bot
from bot.config import load_config


async def main():
    """Главная функция запуска бота"""
    
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        print("🚀 Запуск бота Clash of Clans...")
        print(f"📋 Clash API токенов: {len(config.clash_tokens)}")
        
        if config.database_url:
            print(f"💾 База данных: настроена")
        else:
            print("⚠️  База данных: не настроена")
        
        # Запускаем бота
        await run_bot(config)
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())