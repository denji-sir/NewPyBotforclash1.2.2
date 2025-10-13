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
        # Извлекаем путь из database URL (например, sqlite+aiosqlite:///./data/database/bot.db)
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
        
        # Создаем директорию если не существует
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize_database(self) -> None:
        """Инициализация базы данных со всеми таблицами"""
        logger.info(f"Initializing database at {self.db_path}")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Включаем поддержку внешних ключей
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Создаем таблицы кланов
            await self._create_registered_clans_table(db)
            await self._create_chat_clan_settings_table(db)
            await self._create_clan_operation_logs_table(db)
            
            # Создаем таблицы паспортов
            await self._create_passports_table(db)
            await self._create_passport_logs_table(db)
            await self._create_player_bindings_table(db)
            
            # Создаем таблицы достижений
            await self._create_achievements_tables(db)
            
            # Создаем таблицы ежедневных ресурсов
            await self._create_daily_resources_table(db)
            
            # Создаем таблицы приветствий
            await self._create_greeting_tables(db)
            
            # Создаем таблицы статистики войн и рейдов
            await self._create_war_stats_tables(db)
            await self._create_raid_stats_tables(db)
            
            # Создаем таблицы для КВ-оповещений
            await self._create_war_notifications_tables(db)
            
            # Создаем таблицу статистики чата
            await self._create_chat_statistics_table(db)
            
            # Создаем таблицы истории донатов
            await self._create_donation_history_tables(db)
            
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
    
    async def _create_passports_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы паспортов"""
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
                preferred_clan_name TEXT,
                settings TEXT DEFAULT '{}',
                stats TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                player_binding TEXT,
                UNIQUE(user_id, chat_id)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_passports_user_chat ON user_passports(user_id, chat_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_passports_user ON user_passports(user_id)")
        logger.info("Created user_passports table")
    
    async def _create_passport_logs_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы логов паспортов"""
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
        await db.execute("CREATE INDEX IF NOT EXISTS idx_passport_logs ON passport_operation_logs(passport_id)")
        logger.info("Created passport_operation_logs table")
    
    async def _create_player_bindings_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы привязок игроков"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_bindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                player_tag TEXT NOT NULL,
                player_name TEXT,
                clan_tag TEXT,
                clan_name TEXT,
                is_primary BOOLEAN DEFAULT FALSE,
                verified BOOLEAN DEFAULT FALSE,
                verified_by INTEGER,
                verified_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                UNIQUE(user_id, chat_id, player_tag)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bindings_user ON player_bindings(user_id, chat_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bindings_player ON player_bindings(player_tag)")
        logger.info("Created player_bindings table")
    
    async def _create_achievements_tables(self, db: aiosqlite.Connection) -> None:
        """Создание таблиц достижений"""
        # Таблица достижений
        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                max_progress INTEGER DEFAULT 1,
                icon TEXT,
                requirements TEXT DEFAULT '{}',
                rewards TEXT DEFAULT '{}',
                prerequisites TEXT DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                hidden BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица прогресса пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_achievement_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                current_progress INTEGER DEFAULT 0,
                target_progress INTEGER NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TEXT,
                last_updated TEXT NOT NULL,
                UNIQUE(user_id, chat_id, achievement_id),
                FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id)
            )
        """)
        
        # Таблица профилей пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                total_points INTEGER DEFAULT 0,
                completed_achievements INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                title TEXT,
                badges TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        
        # Таблица истории наград
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reward_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                reward_type TEXT NOT NULL,
                reward_value TEXT NOT NULL,
                claimed_at TEXT NOT NULL,
                FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id)
            )
        """)
        
        # Таблица событий для отслеживания прогресса
        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievement_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_progress_user ON user_achievement_progress(user_id, chat_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON achievement_events(user_id, chat_id)")
        logger.info("Created achievements tables")
    
    async def _create_daily_resources_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы ежедневных ресурсов"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_resource_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_tag TEXT NOT NULL,
                baseline_date DATE NOT NULL,
                gold INTEGER DEFAULT 0,
                elixir INTEGER DEFAULT 0,
                dark_elixir INTEGER DEFAULT 0,
                clan_capital_gold INTEGER DEFAULT 0,
                trophies INTEGER DEFAULT 0,
                war_stars INTEGER DEFAULT 0,
                donations INTEGER DEFAULT 0,
                donations_received INTEGER DEFAULT 0,
                attacks_won INTEGER DEFAULT 0,
                defenses_won INTEGER DEFAULT 0,
                town_hall_level INTEGER DEFAULT 0,
                builder_hall_level INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                UNIQUE(player_tag, baseline_date)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_baselines_player ON daily_resource_baselines(player_tag)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_baselines_date ON daily_resource_baselines(baseline_date)")
        logger.info("Created daily_resource_baselines table")
    
    async def _create_greeting_tables(self, db: aiosqlite.Connection) -> None:
        """Создание таблиц системы приветствий"""
        # Таблица настроек приветствий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS greeting_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                greeting_message TEXT,
                farewell_message TEXT,
                use_custom_message BOOLEAN DEFAULT FALSE,
                mention_user BOOLEAN DEFAULT TRUE,
                delete_after_seconds INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Таблица статистики приветствий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS greeting_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_greeting_chat ON greeting_settings(chat_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_greeting_stats ON greeting_statistics(chat_id)")
        logger.info("Created greeting tables")
    
    async def _create_war_stats_tables(self, db: aiosqlite.Connection) -> None:
        """Создание таблиц статистики клановых войн"""
        # Таблица войн
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_wars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_tag TEXT NOT NULL,
                clan_name TEXT NOT NULL,
                opponent_tag TEXT NOT NULL,
                opponent_name TEXT NOT NULL,
                war_size INTEGER NOT NULL,
                result TEXT NOT NULL,
                clan_stars INTEGER DEFAULT 0,
                clan_destruction REAL DEFAULT 0.0,
                opponent_stars INTEGER DEFAULT 0,
                opponent_destruction REAL DEFAULT 0.0,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                preparation_start_time TEXT,
                war_type TEXT DEFAULT 'regular',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Таблица статистики игроков в войнах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS war_player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                war_id INTEGER NOT NULL,
                player_tag TEXT NOT NULL,
                player_name TEXT NOT NULL,
                clan_tag TEXT NOT NULL,
                attacks_used INTEGER DEFAULT 0,
                attacks_total INTEGER DEFAULT 2,
                stars_earned INTEGER DEFAULT 0,
                destruction_percentage REAL DEFAULT 0.0,
                best_opponent_attack_stars INTEGER DEFAULT 0,
                best_opponent_attack_destruction REAL DEFAULT 0.0,
                town_hall_level INTEGER,
                map_position INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (war_id) REFERENCES clan_wars(id)
            )
        """)
        
        # Таблица атак в войнах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS war_attacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                war_id INTEGER NOT NULL,
                attacker_tag TEXT NOT NULL,
                attacker_name TEXT NOT NULL,
                defender_tag TEXT NOT NULL,
                defender_name TEXT NOT NULL,
                stars INTEGER NOT NULL,
                destruction_percentage REAL NOT NULL,
                attack_order INTEGER,
                duration INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (war_id) REFERENCES clan_wars(id)
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_wars_clan ON clan_wars(clan_tag)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_wars_time ON clan_wars(end_time)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_war_players ON war_player_stats(war_id, player_tag)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_war_attacks ON war_attacks(war_id)")
        logger.info("Created war statistics tables")
    
    async def _create_raid_stats_tables(self, db: aiosqlite.Connection) -> None:
        """Создание таблиц статистики рейдов"""
        # Таблица рейдовых выходных
        await db.execute("""
            CREATE TABLE IF NOT EXISTS raid_weekends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_tag TEXT NOT NULL,
                clan_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                state TEXT NOT NULL,
                total_loot INTEGER DEFAULT 0,
                raids_completed INTEGER DEFAULT 0,
                total_attacks INTEGER DEFAULT 0,
                enemy_districts_destroyed INTEGER DEFAULT 0,
                defensive_reward INTEGER DEFAULT 0,
                offensive_reward INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Таблица статистики игроков в рейдах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS raid_player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raid_id INTEGER NOT NULL,
                player_tag TEXT NOT NULL,
                player_name TEXT NOT NULL,
                clan_tag TEXT NOT NULL,
                attacks_used INTEGER DEFAULT 0,
                attacks_limit INTEGER DEFAULT 6,
                capital_resources_looted INTEGER DEFAULT 0,
                raids_completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (raid_id) REFERENCES raid_weekends(id)
            )
        """)
        
        # Таблица атак в рейдах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS raid_attacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raid_id INTEGER NOT NULL,
                attacker_tag TEXT NOT NULL,
                attacker_name TEXT NOT NULL,
                district_id INTEGER,
                district_name TEXT,
                stars INTEGER DEFAULT 0,
                destruction_percentage REAL DEFAULT 0.0,
                loot INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (raid_id) REFERENCES raid_weekends(id)
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_raids_clan ON raid_weekends(clan_tag)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_raids_time ON raid_weekends(end_time)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_raid_players ON raid_player_stats(raid_id, player_tag)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_raid_attacks ON raid_attacks(raid_id)")
        logger.info("Created raid statistics tables")
    
    async def _create_war_notifications_tables(self, db: aiosqlite.Connection) -> None:
        """Создание таблиц для КВ-оповещений"""
        # Таблица активных КВ с сообщениями
        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_war_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_tag TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                war_id TEXT NOT NULL,
                war_start_time TEXT NOT NULL,
                war_end_time TEXT NOT NULL,
                ticker_message_id INTEGER,
                h6_message_id INTEGER,
                h6_sent BOOLEAN DEFAULT FALSE,
                state TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(clan_tag, war_id)
            )
        """)
        
        # Таблица настроек уведомлений для пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                allow_mentions BOOLEAN DEFAULT TRUE,
                allow_dm BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, chat_id)
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_active_wars ON active_war_notifications(clan_tag, state)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_war_chat ON active_war_notifications(chat_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_notif ON user_notification_settings(user_id, chat_id)")
        logger.info("Created war notifications tables")
    
    async def _create_chat_statistics_table(self, db: aiosqlite.Connection) -> None:
        """Создание таблицы статистики чата"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                message_count INTEGER DEFAULT 0,
                character_count INTEGER DEFAULT 0,
                last_message_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, user_id)
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_stats ON chat_statistics(chat_id, message_count DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_statistics(chat_id, user_id)")
        logger.info("Created chat statistics table")
    
    async def _create_donation_history_tables(self, db: aiosqlite.Connection) -> None:
        """Создание таблиц истории донатов"""
        # Таблица истории донатов по месяцам
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monthly_donation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_tag TEXT NOT NULL,
                clan_name TEXT NOT NULL,
                player_tag TEXT NOT NULL,
                player_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                donations INTEGER DEFAULT 0,
                donations_received INTEGER DEFAULT 0,
                donation_ratio REAL DEFAULT 0.0,
                season_end_time TEXT NOT NULL,
                archived_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                UNIQUE(clan_tag, player_tag, year, month)
            )
        """)
        
        # Таблица сводной статистики по сезонам
        await db.execute("""
            CREATE TABLE IF NOT EXISTS season_donation_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_tag TEXT NOT NULL,
                clan_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                total_donations INTEGER DEFAULT 0,
                total_received INTEGER DEFAULT 0,
                active_members INTEGER DEFAULT 0,
                average_donations REAL DEFAULT 0.0,
                top_donor_tag TEXT,
                top_donor_name TEXT,
                top_donor_amount INTEGER DEFAULT 0,
                season_end_time TEXT NOT NULL,
                archived_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                UNIQUE(clan_tag, year, month)
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_donation_history_clan ON monthly_donation_history(clan_tag, year, month)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_donation_history_player ON monthly_donation_history(player_tag, year, month)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_season_summary ON season_donation_summary(clan_tag, year, month)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_season_time ON season_donation_summary(season_end_time)")
        logger.info("Created donation history tables")
    
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