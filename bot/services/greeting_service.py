"""
Сервис для управления системой приветствия новых участников
"""

import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ..models.greeting_models import GreetingSettings, GreetingStats, GREETING_TEMPLATES

logger = logging.getLogger(__name__)


class GreetingService:
    """
    Сервис для управления системой приветствия новых участников чата
    """
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        
        # Кэш настроек для быстрого доступа
        self._settings_cache: Dict[int, GreetingSettings] = {}
        self._stats_cache: Dict[int, GreetingStats] = {}
        
        # Очередь для отложенного удаления сообщений
        self._deletion_queue: asyncio.Queue = asyncio.Queue()
    
    async def initialize_database(self):
        """Инициализация таблиц базы данных"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица настроек приветствия
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS greeting_settings (
                        chat_id INTEGER PRIMARY KEY,
                        is_enabled BOOLEAN DEFAULT FALSE,
                        greeting_text TEXT,
                        welcome_sticker TEXT,
                        delete_after_seconds INTEGER,
                        mention_user BOOLEAN DEFAULT TRUE,
                        show_rules_button BOOLEAN DEFAULT FALSE,
                        rules_text TEXT,
                        created_by INTEGER,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Таблица статистики приветствий
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS greeting_stats (
                        chat_id INTEGER PRIMARY KEY,
                        total_greetings_sent INTEGER DEFAULT 0,
                        last_greeting_date TIMESTAMP,
                        average_new_members_per_day REAL DEFAULT 0.0,
                        most_active_day TEXT,
                        greeting_effectiveness REAL DEFAULT 0.0
                    )
                """)
                
                # Таблица истории приветствий
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS greeting_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        greeting_text TEXT,
                        message_id INTEGER,
                        sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        was_deleted BOOLEAN DEFAULT FALSE,
                        user_responded BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Индексы для оптимизации
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_greeting_history_chat ON greeting_history(chat_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_greeting_history_user ON greeting_history(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_greeting_history_date ON greeting_history(sent_date)")
                
                conn.commit()
                logger.info("База данных системы приветствий инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД приветствий: {e}")
            raise
    
    # Управление настройками
    
    async def get_greeting_settings(self, chat_id: int) -> GreetingSettings:
        """Получение настроек приветствия для чата"""
        
        # Проверяем кэш
        if chat_id in self._settings_cache:
            return self._settings_cache[chat_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT chat_id, is_enabled, greeting_text, welcome_sticker,
                           delete_after_seconds, mention_user, show_rules_button,
                           rules_text, created_by, created_date, updated_date
                    FROM greeting_settings WHERE chat_id = ?
                """, (chat_id,))
                
                row = cursor.fetchone()
                
                if row:
                    settings = GreetingSettings(
                        chat_id=row[0],
                        is_enabled=bool(row[1]),
                        greeting_text=row[2],
                        welcome_sticker=row[3],
                        delete_after_seconds=row[4],
                        mention_user=bool(row[5]),
                        show_rules_button=bool(row[6]),
                        rules_text=row[7],
                        created_by=row[8],
                        created_date=datetime.fromisoformat(row[9]) if row[9] else None,
                        updated_date=datetime.fromisoformat(row[10]) if row[10] else None
                    )
                else:
                    # Создаем настройки по умолчанию
                    settings = GreetingSettings(chat_id=chat_id)
                    await self._save_greeting_settings(settings)
                
                # Кэшируем
                self._settings_cache[chat_id] = settings
                return settings
                
        except Exception as e:
            logger.error(f"Ошибка получения настроек приветствия для чата {chat_id}: {e}")
            return GreetingSettings(chat_id=chat_id)
    
    async def update_greeting_settings(
        self, 
        chat_id: int, 
        admin_user_id: int,
        **settings
    ) -> bool:
        """Обновление настроек приветствия"""
        
        try:
            current_settings = await self.get_greeting_settings(chat_id)
            
            # Обновляем настройки
            current_settings.update_settings(**settings)
            current_settings.created_by = admin_user_id
            
            # Сохраняем в БД
            success = await self._save_greeting_settings(current_settings)
            
            if success:
                # Обновляем кэш
                self._settings_cache[chat_id] = current_settings
                logger.info(f"Настройки приветствия обновлены для чата {chat_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка обновления настроек приветствия: {e}")
            return False
    
    async def set_greeting_text(self, chat_id: int, admin_user_id: int, text: str) -> bool:
        """Установка текста приветствия"""
        
        return await self.update_greeting_settings(
            chat_id=chat_id,
            admin_user_id=admin_user_id,
            greeting_text=text
        )
    
    async def toggle_greeting(self, chat_id: int, admin_user_id: int, enabled: bool) -> bool:
        """Включение/выключение приветствий"""
        
        return await self.update_greeting_settings(
            chat_id=chat_id,
            admin_user_id=admin_user_id,
            is_enabled=enabled
        )
    
    async def _save_greeting_settings(self, settings: GreetingSettings) -> bool:
        """Сохранение настроек в БД"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO greeting_settings (
                        chat_id, is_enabled, greeting_text, welcome_sticker,
                        delete_after_seconds, mention_user, show_rules_button,
                        rules_text, created_by, created_date, updated_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    settings.chat_id,
                    settings.is_enabled,
                    settings.greeting_text,
                    settings.welcome_sticker,
                    settings.delete_after_seconds,
                    settings.mention_user,
                    settings.show_rules_button,
                    settings.rules_text,
                    settings.created_by,
                    settings.created_date.isoformat() if settings.created_date else None,
                    settings.updated_date.isoformat()
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек приветствия: {e}")
            return False
    
    # Обработка новых участников
    
    async def handle_new_member(
        self, 
        chat_id: int, 
        user_id: int, 
        username: str, 
        first_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Обработка нового участника чата
        
        Returns:
            Словарь с данными для отправки приветствия или None
        """
        
        try:
            settings = await self.get_greeting_settings(chat_id)
            
            # Проверяем, включены ли приветствия
            if not settings.is_enabled:
                return None
            
            # Форматируем текст приветствия
            greeting_text = settings.format_greeting_for_user(first_name, username)
            
            # Подготавливаем данные для отправки
            greeting_data = {
                'text': greeting_text,
                'mention_user': settings.mention_user,
                'sticker': settings.welcome_sticker,
                'delete_after': settings.delete_after_seconds,
                'show_rules_button': settings.show_rules_button,
                'rules_text': settings.rules_text
            }
            
            # Записываем в историю (пока без message_id)
            await self._log_greeting_sent(
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                first_name=first_name,
                greeting_text=greeting_text
            )
            
            # Обновляем статистику
            await self._update_greeting_stats(chat_id)
            
            return greeting_data
            
        except Exception as e:
            logger.error(f"Ошибка обработки нового участника {user_id} в чате {chat_id}: {e}")
            return None
    
    async def _log_greeting_sent(
        self, 
        chat_id: int, 
        user_id: int, 
        username: str, 
        first_name: str,
        greeting_text: str,
        message_id: Optional[int] = None
    ):
        """Логирование отправленного приветствия"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO greeting_history (
                        chat_id, user_id, username, first_name, 
                        greeting_text, message_id, sent_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    chat_id, user_id, username, first_name,
                    greeting_text, message_id, datetime.now().isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка логирования приветствия: {e}")
    
    async def update_greeting_message_id(self, chat_id: int, user_id: int, message_id: int):
        """Обновление ID сообщения в истории приветствий"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE greeting_history 
                    SET message_id = ?
                    WHERE chat_id = ? AND user_id = ? AND message_id IS NULL
                    ORDER BY sent_date DESC LIMIT 1
                """, (message_id, chat_id, user_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка обновления ID сообщения приветствия: {e}")
    
    # Статистика
    
    async def get_greeting_stats(self, chat_id: int) -> GreetingStats:
        """Получение статистики приветствий"""
        
        # Проверяем кэш
        if chat_id in self._stats_cache:
            return self._stats_cache[chat_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT chat_id, total_greetings_sent, last_greeting_date,
                           average_new_members_per_day, most_active_day, greeting_effectiveness
                    FROM greeting_stats WHERE chat_id = ?
                """, (chat_id,))
                
                row = cursor.fetchone()
                
                if row:
                    stats = GreetingStats(
                        chat_id=row[0],
                        total_greetings_sent=row[1],
                        last_greeting_date=datetime.fromisoformat(row[2]) if row[2] else None,
                        average_new_members_per_day=row[3],
                        most_active_day=row[4],
                        greeting_effectiveness=row[5]
                    )
                else:
                    stats = GreetingStats(chat_id=chat_id)
                    await self._save_greeting_stats(stats)
                
                # Кэшируем
                self._stats_cache[chat_id] = stats
                return stats
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики приветствий: {e}")
            return GreetingStats(chat_id=chat_id)
    
    async def _update_greeting_stats(self, chat_id: int):
        """Обновление статистики приветствий"""
        
        try:
            stats = await self.get_greeting_stats(chat_id)
            stats.increment_greeting_count()
            
            # Рассчитываем дополнительную статистику
            await self._calculate_advanced_stats(stats)
            
            # Сохраняем
            await self._save_greeting_stats(stats)
            
            # Обновляем кэш
            self._stats_cache[chat_id] = stats
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики приветствий: {e}")
    
    async def _calculate_advanced_stats(self, stats: GreetingStats):
        """Расчет расширенной статистики"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Среднее количество новых участников в день за последние 30 дней
                cursor.execute("""
                    SELECT COUNT(*) as daily_count, DATE(sent_date) as date
                    FROM greeting_history 
                    WHERE chat_id = ? AND sent_date >= date('now', '-30 days')
                    GROUP BY DATE(sent_date)
                """, (stats.chat_id,))
                
                daily_counts = cursor.fetchall()
                if daily_counts:
                    total_members = sum(row[0] for row in daily_counts)
                    days_with_activity = len(daily_counts)
                    stats.average_new_members_per_day = total_members / max(days_with_activity, 1)
                
                # Самый активный день недели
                cursor.execute("""
                    SELECT strftime('%w', sent_date) as day_of_week, COUNT(*) as count
                    FROM greeting_history 
                    WHERE chat_id = ? AND sent_date >= date('now', '-90 days')
                    GROUP BY strftime('%w', sent_date)
                    ORDER BY count DESC LIMIT 1
                """, (stats.chat_id,))
                
                most_active = cursor.fetchone()
                if most_active:
                    days = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
                    stats.most_active_day = days[int(most_active[0])]
                
                # Эффективность приветствий (процент ответивших)
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN user_responded THEN 1 ELSE 0 END) as responded
                    FROM greeting_history 
                    WHERE chat_id = ? AND sent_date >= date('now', '-30 days')
                """, (stats.chat_id,))
                
                effectiveness_data = cursor.fetchone()
                if effectiveness_data and effectiveness_data[0] > 0:
                    stats.greeting_effectiveness = (effectiveness_data[1] / effectiveness_data[0]) * 100
                
        except Exception as e:
            logger.error(f"Ошибка расчета расширенной статистики: {e}")
    
    async def _save_greeting_stats(self, stats: GreetingStats) -> bool:
        """Сохранение статистики в БД"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO greeting_stats (
                        chat_id, total_greetings_sent, last_greeting_date,
                        average_new_members_per_day, most_active_day, greeting_effectiveness
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    stats.chat_id,
                    stats.total_greetings_sent,
                    stats.last_greeting_date.isoformat() if stats.last_greeting_date else None,
                    stats.average_new_members_per_day,
                    stats.most_active_day,
                    stats.greeting_effectiveness
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики приветствий: {e}")
            return False
    
    # Управление сообщениями
    
    async def schedule_message_deletion(self, chat_id: int, message_id: int, delay_seconds: int):
        """Запланировать удаление сообщения"""
        
        if delay_seconds and delay_seconds > 0:
            await self._deletion_queue.put({
                'chat_id': chat_id,
                'message_id': message_id,
                'delete_at': datetime.now() + timedelta(seconds=delay_seconds)
            })
    
    async def process_message_deletions(self):
        """Обработка очереди удаления сообщений (фоновая задача)"""
        
        while True:
            try:
                # Получаем сообщение из очереди с таймаутом
                try:
                    deletion_task = await asyncio.wait_for(self._deletion_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Ждем до времени удаления
                now = datetime.now()
                if deletion_task['delete_at'] > now:
                    sleep_time = (deletion_task['delete_at'] - now).total_seconds()
                    await asyncio.sleep(sleep_time)
                
                # Помечаем в очереди для удаления ботом
                # (Само удаление будет выполнено в основном коде бота)
                logger.info(f"Запланировано удаление сообщения {deletion_task['message_id']} в чате {deletion_task['chat_id']}")
                
            except Exception as e:
                logger.error(f"Ошибка обработки удаления сообщений: {e}")
                await asyncio.sleep(5)
    
    # Шаблоны и утилиты
    
    def get_greeting_templates(self) -> Dict[str, str]:
        """Получение доступных шаблонов приветствий"""
        return GREETING_TEMPLATES.copy()
    
    async def apply_greeting_template(self, chat_id: int, admin_user_id: int, template_name: str) -> bool:
        """Применение шаблона приветствия"""
        
        if template_name not in GREETING_TEMPLATES:
            return False
        
        template_text = GREETING_TEMPLATES[template_name]
        
        return await self.set_greeting_text(chat_id, admin_user_id, template_text)
    
    async def get_greeting_history(self, chat_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение истории приветствий"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id, username, first_name, greeting_text, 
                           sent_date, was_deleted, user_responded
                    FROM greeting_history
                    WHERE chat_id = ?
                    ORDER BY sent_date DESC LIMIT ?
                """, (chat_id, limit))
                
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'greeting_text': row[3],
                        'sent_date': datetime.fromisoformat(row[4]),
                        'was_deleted': bool(row[5]),
                        'user_responded': bool(row[6])
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Ошибка получения истории приветствий: {e}")
            return []
    
    async def mark_user_responded(self, chat_id: int, user_id: int):
        """Отметить, что пользователь ответил на приветствие"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE greeting_history 
                    SET user_responded = TRUE
                    WHERE chat_id = ? AND user_id = ? 
                    AND sent_date >= date('now', '-1 day')
                    ORDER BY sent_date DESC LIMIT 1
                """, (chat_id, user_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка отметки ответа пользователя: {e}")
    
    # Очистка кэша
    
    def clear_cache(self, chat_id: Optional[int] = None):
        """Очистка кэша настроек и статистики"""
        
        if chat_id:
            self._settings_cache.pop(chat_id, None)
            self._stats_cache.pop(chat_id, None)
        else:
            self._settings_cache.clear()
            self._stats_cache.clear()
        
        logger.info(f"Кэш приветствий очищен для чата {chat_id or 'всех чатов'}")


# Создаем глобальный экземпляр сервиса
greeting_service = GreetingService()