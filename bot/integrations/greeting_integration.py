"""
Интеграция системы приветствий с основным ботом
"""

import logging
import asyncio
from typing import Optional

# Импорты будут работать при наличии установленных зависимостей
try:
    from aiogram import Bot
except ImportError:
    Bot = None

from ..services.greeting_service import greeting_service

logger = logging.getLogger(__name__)


class GreetingIntegration:
    """
    Класс для интеграции системы приветствий с основным ботом
    """
    
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self._cleanup_task: Optional[asyncio.Task] = None
        self._deletion_processor_task: Optional[asyncio.Task] = None
    
    async def initialize(self, bot: Optional[Bot] = None):
        """Инициализация интеграции"""
        
        if bot:
            self.bot = bot
        
        try:
            # Инициализируем базу данных
            await greeting_service.initialize_database()
            
            # Запускаем фоновые задачи
            await self._start_background_tasks()
            
            logger.info("Система приветствий инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации системы приветствий: {e}")
            raise
    
    async def _start_background_tasks(self):
        """Запуск фоновых задач"""
        
        # Задача обработки удаления сообщений
        if not self._deletion_processor_task or self._deletion_processor_task.done():
            self._deletion_processor_task = asyncio.create_task(
                greeting_service.process_message_deletions()
            )
            logger.info("Запущена задача обработки удаления сообщений")
        
        # Задача периодической очистки (каждые 24 часа)
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(
                self._periodic_cleanup()
            )
            logger.info("Запущена задача периодической очистки")
    
    async def _periodic_cleanup(self):
        """Периодическая очистка данных"""
        
        while True:
            try:
                await asyncio.sleep(24 * 60 * 60)  # 24 часа
                
                # Очистка кэша
                greeting_service.clear_cache()
                
                # Здесь можно добавить другие задачи очистки
                logger.info("Выполнена периодическая очистка системы приветствий")
                
            except Exception as e:
                logger.error(f"Ошибка периодической очистки: {e}")
                await asyncio.sleep(3600)  # Ждем час при ошибке
    
    async def shutdown(self):
        """Корректное завершение работы интеграции"""
        
        try:
            # Останавливаем фоновые задачи
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            if self._deletion_processor_task and not self._deletion_processor_task.done():
                self._deletion_processor_task.cancel()
                try:
                    await self._deletion_processor_task
                except asyncio.CancelledError:
                    pass
            
            # Очищаем кэш
            greeting_service.clear_cache()
            
            logger.info("Система приветствий корректно завершена")
            
        except Exception as e:
            logger.error(f"Ошибка завершения системы приветствий: {e}")
    
    # Методы для интеграции с другими системами
    
    async def handle_achievement_greeting_sent(self, chat_id: int, user_id: int):
        """Обработка достижения за отправку приветствия"""
        
        try:
            # Интеграция с системой достижений
            # Можно добавить достижения типа "Отправил 100 приветствий" для админов
            pass
            
        except Exception as e:
            logger.debug(f"Ошибка обработки достижения приветствия: {e}")
    
    async def handle_achievement_new_member_responded(self, chat_id: int, user_id: int):
        """Обработка достижения за ответ нового участника"""
        
        try:
            # Интеграция с системой достижений
            # Можно добавить достижения типа "Первое сообщение в чате"
            pass
            
        except Exception as e:
            logger.debug(f"Ошибка обработки достижения ответа: {e}")
    
    # Вспомогательные методы для внешнего использования
    
    async def get_chat_greeting_info(self, chat_id: int) -> dict:
        """Получение информации о приветствиях для чата"""
        
        try:
            settings = await greeting_service.get_greeting_settings(chat_id)
            stats = await greeting_service.get_greeting_stats(chat_id)
            
            return {
                'enabled': settings.is_enabled,
                'has_text': bool(settings.greeting_text),
                'has_sticker': bool(settings.welcome_sticker),
                'auto_delete': settings.delete_after_seconds,
                'mention_user': settings.mention_user,
                'show_rules': settings.show_rules_button,
                'total_greetings': stats.total_greetings_sent,
                'average_per_day': stats.average_new_members_per_day,
                'effectiveness': stats.greeting_effectiveness
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о приветствиях: {e}")
            return {}
    
    async def preview_greeting(self, chat_id: int, user_name: str, username: str = "") -> str:
        """Предварительный просмотр приветствия"""
        
        try:
            settings = await greeting_service.get_greeting_settings(chat_id)
            
            if not settings.greeting_text:
                return "Текст приветствия не установлен"
            
            return settings.format_greeting_for_user(user_name, username)
            
        except Exception as e:
            logger.error(f"Ошибка предварительного просмотра: {e}")
            return "Ошибка формирования приветствия"
    
    async def bulk_enable_greetings(self, chat_ids: list, admin_user_id: int) -> dict:
        """Массовое включение приветствий"""
        
        results = {'success': [], 'failed': []}
        
        for chat_id in chat_ids:
            try:
                success = await greeting_service.toggle_greeting(chat_id, admin_user_id, True)
                
                if success:
                    results['success'].append(chat_id)
                else:
                    results['failed'].append(chat_id)
                    
            except Exception as e:
                logger.error(f"Ошибка включения приветствий для чата {chat_id}: {e}")
                results['failed'].append(chat_id)
        
        return results
    
    async def get_greeting_statistics_summary(self) -> dict:
        """Получение общей статистики по всем чатам"""
        
        try:
            import sqlite3
            
            with sqlite3.connect(greeting_service.db_path) as conn:
                cursor = conn.cursor()
                
                # Общее количество чатов с настроенными приветствиями
                cursor.execute("""
                    SELECT COUNT(*) FROM greeting_settings WHERE is_enabled = TRUE
                """)
                enabled_chats = cursor.fetchone()[0]
                
                # Общее количество отправленных приветствий
                cursor.execute("""
                    SELECT SUM(total_greetings_sent) FROM greeting_stats
                """)
                total_greetings = cursor.fetchone()[0] or 0
                
                # Среднее количество приветствий в день
                cursor.execute("""
                    SELECT AVG(average_new_members_per_day) FROM greeting_stats 
                    WHERE average_new_members_per_day > 0
                """)
                avg_per_day = cursor.fetchone()[0] or 0
                
                # Средняя эффективность
                cursor.execute("""
                    SELECT AVG(greeting_effectiveness) FROM greeting_stats 
                    WHERE greeting_effectiveness > 0
                """)
                avg_effectiveness = cursor.fetchone()[0] or 0
                
                return {
                    'enabled_chats': enabled_chats,
                    'total_greetings': total_greetings,
                    'average_per_day': round(avg_per_day, 1),
                    'average_effectiveness': round(avg_effectiveness, 1)
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения общей статистики: {e}")
            return {}
    
    async def export_greeting_settings(self, chat_id: int) -> dict:
        """Экспорт настроек приветствий"""
        
        try:
            settings = await greeting_service.get_greeting_settings(chat_id)
            
            return {
                'chat_id': settings.chat_id,
                'is_enabled': settings.is_enabled,
                'greeting_text': settings.greeting_text,
                'welcome_sticker': settings.welcome_sticker,
                'delete_after_seconds': settings.delete_after_seconds,
                'mention_user': settings.mention_user,
                'show_rules_button': settings.show_rules_button,
                'rules_text': settings.rules_text,
                'created_date': settings.created_date.isoformat() if settings.created_date else None,
                'updated_date': settings.updated_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка экспорта настроек: {e}")
            return {}
    
    async def import_greeting_settings(self, settings_data: dict, admin_user_id: int) -> bool:
        """Импорт настроек приветствий"""
        
        try:
            chat_id = settings_data.get('chat_id')
            if not chat_id:
                return False
            
            # Фильтруем только разрешенные настройки
            allowed_settings = {
                'is_enabled', 'greeting_text', 'welcome_sticker',
                'delete_after_seconds', 'mention_user', 'show_rules_button', 'rules_text'
            }
            
            filtered_settings = {
                k: v for k, v in settings_data.items() 
                if k in allowed_settings
            }
            
            return await greeting_service.update_greeting_settings(
                chat_id=chat_id,
                admin_user_id=admin_user_id,
                **filtered_settings
            )
            
        except Exception as e:
            logger.error(f"Ошибка импорта настроек: {e}")
            return False


# Создаем глобальный экземпляр интеграции
greeting_integration = GreetingIntegration()


# Функции для быстрого доступа

async def initialize_greeting_system(bot: Optional[Bot] = None):
    """Инициализация системы приветствий"""
    await greeting_integration.initialize(bot)


async def shutdown_greeting_system():
    """Корректное завершение системы приветствий"""
    await greeting_integration.shutdown()


async def get_greeting_info(chat_id: int) -> dict:
    """Быстрое получение информации о приветствиях"""
    return await greeting_integration.get_chat_greeting_info(chat_id)


async def preview_chat_greeting(chat_id: int, user_name: str, username: str = "") -> str:
    """Быстрый предварительный просмотр приветствия"""
    return await greeting_integration.preview_greeting(chat_id, user_name, username)


# Декоратор для интеграции с командами

def with_greeting_integration(func):
    """Декоратор для интеграции команд с системой приветствий"""
    
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в команде с интеграцией приветствий: {e}")
            raise
    
    return wrapper


# Хелперы для статистики

async def get_top_greeting_chats(limit: int = 10) -> list:
    """Получение топ чатов по количеству приветствий"""
    
    try:
        import sqlite3
        
        with sqlite3.connect(greeting_service.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT chat_id, total_greetings_sent, average_new_members_per_day
                FROM greeting_stats
                ORDER BY total_greetings_sent DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    'chat_id': row[0],
                    'total_greetings': row[1],
                    'avg_per_day': row[2]
                }
                for row in cursor.fetchall()
            ]
            
    except Exception as e:
        logger.error(f"Ошибка получения топ чатов: {e}")
        return []


async def get_greeting_activity_report(days: int = 30) -> dict:
    """Получение отчета об активности приветствий"""
    
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(greeting_service.db_path) as conn:
            cursor = conn.cursor()
            
            # Количество приветствий за период
            cursor.execute("""
                SELECT COUNT(*) FROM greeting_history
                WHERE sent_date >= ?
            """, (cutoff_date.isoformat(),))
            
            total_greetings = cursor.fetchone()[0]
            
            # Количество уникальных чатов
            cursor.execute("""
                SELECT COUNT(DISTINCT chat_id) FROM greeting_history
                WHERE sent_date >= ?
            """, (cutoff_date.isoformat(),))
            
            unique_chats = cursor.fetchone()[0]
            
            # Количество ответивших пользователей
            cursor.execute("""
                SELECT COUNT(*) FROM greeting_history
                WHERE sent_date >= ? AND user_responded = TRUE
            """, (cutoff_date.isoformat(),))
            
            responded_users = cursor.fetchone()[0]
            
            # Эффективность
            effectiveness = (responded_users / total_greetings * 100) if total_greetings > 0 else 0
            
            return {
                'period_days': days,
                'total_greetings': total_greetings,
                'unique_chats': unique_chats,
                'responded_users': responded_users,
                'effectiveness_percent': round(effectiveness, 1),
                'avg_greetings_per_day': round(total_greetings / days, 1)
            }
            
    except Exception as e:
        logger.error(f"Ошибка получения отчета активности: {e}")
        return {}