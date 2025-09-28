"""
Инициализация базы данных для системы паспортов
"""
import logging
import aiosqlite
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PassportDatabaseInitializer:
    """Инициализатор базы данных паспортов"""
    
    def __init__(self, db_path: str = "data/passports.db"):
        self.db_path = db_path
        
    async def initialize(self) -> bool:
        """
        Инициализация базы данных паспортов
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            # Создаем директорию если не существует
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Создаем основную таблицу паспортов
                await self._create_passports_table(db)
                
                # Создаем таблицу логов операций
                await self._create_passport_logs_table(db)
                
                # Создаем индексы
                await self._create_indexes(db)
                
                # Проверяем целостность
                await self._validate_schema(db)
                
                await db.commit()
                
            logger.info(f"Passport database initialized: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize passport database: {e}")
            return False
    
    async def _create_passports_table(self, db: aiosqlite.Connection):
        """Создание основной таблицы паспортов"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_passports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                username TEXT,
                display_name TEXT,
                bio TEXT,
                avatar_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                preferred_clan_id INTEGER,
                preferred_clan_tag TEXT,
                settings TEXT DEFAULT '{}',
                stats TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                player_binding TEXT,
                preferred_clan_name TEXT,
                UNIQUE(user_id, chat_id)
            )
        """)
        
        logger.info("Created user_passports table")
    
    async def _create_passport_logs_table(self, db: aiosqlite.Connection):
        """Создание таблицы логов операций с паспортами"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS passport_operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passport_id INTEGER NOT NULL,
                operation_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                operation_details TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL,
                result TEXT DEFAULT 'success',
                error_message TEXT,
                FOREIGN KEY (passport_id) REFERENCES user_passports(id)
            )
        """)
        
        logger.info("Created passport_operation_logs table")
    
    async def _create_indexes(self, db: aiosqlite.Connection):
        """Создание индексов для оптимизации"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_passports_user_chat ON user_passports(user_id, chat_id)",
            "CREATE INDEX IF NOT EXISTS idx_passports_chat ON user_passports(chat_id)",
            "CREATE INDEX IF NOT EXISTS idx_passports_clan ON user_passports(preferred_clan_id)",
            "CREATE INDEX IF NOT EXISTS idx_passports_status ON user_passports(status)",
            "CREATE INDEX IF NOT EXISTS idx_passport_logs_passport ON passport_operation_logs(passport_id)",
            "CREATE INDEX IF NOT EXISTS idx_passport_logs_user ON passport_operation_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_passport_logs_type ON passport_operation_logs(operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_passport_logs_timestamp ON passport_operation_logs(timestamp)"
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
        
        logger.info("Created database indexes")
    
    async def _validate_schema(self, db: aiosqlite.Connection):
        """Валидация схемы базы данных"""
        # Проверяем существование таблиц
        async with db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('user_passports', 'passport_operation_logs')
        """) as cursor:
            tables = await cursor.fetchall()
            
        if len(tables) != 2:
            raise Exception("Missing required tables in passport database")
        
        # Проверяем структуру основной таблицы
        async with db.execute("PRAGMA table_info(user_passports)") as cursor:
            columns = await cursor.fetchall()
            
        required_columns = {
            'id', 'user_id', 'chat_id', 'username', 'display_name', 
            'bio', 'avatar_url', 'created_at', 'updated_at', 'status',
            'preferred_clan_id', 'preferred_clan_tag', 'settings', 
            'stats', 'metadata', 'player_binding', 'preferred_clan_name'
        }
        
        existing_columns = {col[1] for col in columns}
        
        if not required_columns.issubset(existing_columns):
            missing = required_columns - existing_columns
            raise Exception(f"Missing columns in user_passports: {missing}")
        
        logger.info("Database schema validation passed")
    
    async def get_database_info(self) -> dict:
        """Получение информации о базе данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Количество паспортов
                async with db.execute("SELECT COUNT(*) FROM user_passports") as cursor:
                    passports_count = (await cursor.fetchone())[0]
                
                # Активные паспорты
                async with db.execute(
                    "SELECT COUNT(*) FROM user_passports WHERE status = 'active'"
                ) as cursor:
                    active_count = (await cursor.fetchone())[0]
                
                # Паспорты с привязанными игроками
                async with db.execute(
                    "SELECT COUNT(*) FROM user_passports WHERE player_binding IS NOT NULL"
                ) as cursor:
                    bound_count = (await cursor.fetchone())[0]
                
                # Количество операций в логах
                async with db.execute("SELECT COUNT(*) FROM passport_operation_logs") as cursor:
                    operations_count = (await cursor.fetchone())[0]
                
                return {
                    'total_passports': passports_count,
                    'active_passports': active_count,
                    'bound_passports': bound_count,
                    'operations_logged': operations_count,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Очистка старых логов операций
        
        Args:
            days_to_keep: Количество дней для хранения логов
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "DELETE FROM passport_operation_logs WHERE timestamp < ?",
                    (cutoff_str,)
                ) as cursor:
                    deleted_count = cursor.rowcount
                
                await db.commit()
                
            logger.info(f"Cleaned up {deleted_count} old passport operation logs")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            return 0


# Глобальная функция инициализации
async def init_passport_database(db_path: str = "data/passports.db") -> bool:
    """
    Глобальная функция инициализации базы данных паспортов
    
    Args:
        db_path: Путь к файлу базы данных
        
    Returns:
        bool: True если инициализация успешна
    """
    initializer = PassportDatabaseInitializer(db_path)
    return await initializer.initialize()


# Функция получения инициализатора
def get_passport_db_initializer(db_path: str = "data/passports.db") -> PassportDatabaseInitializer:
    """Получение экземпляра инициализатора БД паспортов"""
    return PassportDatabaseInitializer(db_path)