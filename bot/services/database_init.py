"""
Инициализация базы данных SQLite для системы кланов
"""
import aiosqlite
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Класс для инициализации базы данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # Создаем директорию если не существует
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize_database(self) -> None:
        """Инициализация базы данных со всеми таблицами"""
        logger.info(f"Initializing database at {self.db_path}")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Включаем поддержку внешних ключей
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Создаем таблицы
            await self._create_registered_clans_table(db)
            await self._create_chat_clan_settings_table(db)
            await self._create_clan_operation_logs_table(db)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def _create_registered_clans_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы зарегистрированных кланов"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registered_clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Основная информация о клане
                clan_tag TEXT UNIQUE NOT NULL,
                clan_name TEXT NOT NULL,
                clan_description TEXT,
                clan_level INTEGER DEFAULT 1,
                clan_points INTEGER DEFAULT 0,
                member_count INTEGER DEFAULT 0,
                
                -- Информация о регистрации
                chat_id INTEGER NOT NULL,
                registered_by INTEGER NOT NULL,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Настройки и статус
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT TRUE,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Дополнительные данные (JSON)
                clan_metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Создаем индексы
        await db.execute("CREATE INDEX IF NOT EXISTS idx_clan_tag ON registered_clans(clan_tag)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_clan_chat ON registered_clans(chat_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_clan_active ON registered_clans(is_active)")
        
        logger.info("Created registered_clans table")
    
    async def _create_chat_clan_settings_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы настроек чатов"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_clan_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Основная информация
                chat_id INTEGER UNIQUE NOT NULL,
                chat_title TEXT,
                
                -- Настройки кланов
                default_clan_id INTEGER,
                max_clans_per_chat INTEGER DEFAULT 10,
                
                -- Настройки отображения
                show_clan_numbers BOOLEAN DEFAULT TRUE,
                auto_detect_clan BOOLEAN DEFAULT TRUE,
                
                -- Разрешения
                admin_only_registration BOOLEAN DEFAULT TRUE,
                
                -- Временные метки
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Внешние ключи
                FOREIGN KEY (default_clan_id) REFERENCES registered_clans(id)
            )
        """)
        
        # Создаем индекс
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_settings ON chat_clan_settings(chat_id)")
        
        logger.info("Created chat_clan_settings table")
    
    async def _create_clan_operation_logs_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы логов операций"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Основная информация
                operation_type TEXT NOT NULL,
                clan_id INTEGER,
                clan_tag TEXT,
                
                -- Контекст операции
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                
                -- Детали операции
                operation_details TEXT DEFAULT '{}',
                result TEXT NOT NULL,
                error_message TEXT,
                
                -- Временная метка
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индексы
        await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_clan ON clan_operation_logs(clan_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_chat ON clan_operation_logs(chat_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON clan_operation_logs(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_operation ON clan_operation_logs(operation_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON clan_operation_logs(created_at)")
        
        logger.info("Created clan_operation_logs table")
    
    async def check_database_integrity(self) -> bool:
        """Проверка целостности базы данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем наличие всех таблиц
                tables = [
                    'registered_clans',
                    'chat_clan_settings', 
                    'clan_operation_logs'
                ]
                
                for table in tables:
                    cursor = await db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)
                    )
                    result = await cursor.fetchone()
                    if not result:
                        logger.error(f"Table {table} not found in database")
                        return False
                
                # Проверяем внешние ключи
                await db.execute("PRAGMA foreign_key_check")
                
                logger.info("Database integrity check passed")
                return True
                
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False
    
    async def get_database_info(self) -> dict:
        """Получить информацию о базе данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Получаем количество записей в каждой таблице
                clan_count = await (await db.execute("SELECT COUNT(*) FROM registered_clans")).fetchone()
                settings_count = await (await db.execute("SELECT COUNT(*) FROM chat_clan_settings")).fetchone()
                logs_count = await (await db.execute("SELECT COUNT(*) FROM clan_operation_logs")).fetchone()
                
                # Размер файла
                file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'database_path': self.db_path,
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / 1024 / 1024, 2),
                    'tables': {
                        'registered_clans': clan_count[0] if clan_count else 0,
                        'chat_clan_settings': settings_count[0] if settings_count else 0,
                        'clan_operation_logs': logs_count[0] if logs_count else 0
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {'error': str(e)}


# Функция для быстрой инициализации
async def init_clan_database(db_path: str = "data/clans.db") -> DatabaseInitializer:
    """Быстрая инициализация базы данных для кланов"""
    initializer = DatabaseInitializer(db_path)
    await initializer.initialize_database()
    
    # Проверяем целостность
    if await initializer.check_database_integrity():
        logger.info("Database ready for use")
    else:
        raise DatabaseError("Database integrity check failed")
    
    return initializer