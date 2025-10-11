"""
Основной сервис для работы с кланами в базе данных
"""
import aiosqlite
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from ..models.clan_models import (
    ClanData, ClanInfo, ChatClanSettings, ClanOperationLog,
    ClanAlreadyRegistered, ClanNotFound, DatabaseError
)
from .coc_api_service import get_coc_api_service

logger = logging.getLogger(__name__)


class ClanDatabaseService:
    """Сервис для работы с кланами в базе данных"""
    
    def __init__(self, db_path: str):
        # Извлекаем путь из database URL (например, sqlite+aiosqlite:///./data/database/bot.db)
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
    
    async def register_clan(self, clan_data: ClanData, chat_id: int, 
                          registered_by: int, description: str = None) -> int:
        """
        Регистрация клана в базе данных
        
        Args:
            clan_data: Данные клана из CoC API
            chat_id: ID чата где регистрируется клан
            registered_by: ID пользователя регистрирующего клан
            description: Дополнительное описание клана
        
        Returns:
            int: ID зарегистрированного клана
        
        Raises:
            ClanAlreadyRegistered: Если клан уже зарегистрирован
            DatabaseError: При ошибках БД
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON")
                
                # Проверяем что клан не зарегистрирован
                existing = await db.fetchone(
                    "SELECT id, chat_id FROM registered_clans WHERE clan_tag = ? AND is_active = 1",
                    (clan_data.tag,)
                )
                
                if existing:
                    existing_chat = await self.get_chat_title(existing[1])
                    raise ClanAlreadyRegistered(
                        f"Клан {clan_data.tag} уже зарегистрирован в чате: {existing_chat}"
                    )
                
                # Проверяем лимит кланов для чата
                clan_count = await self.get_chat_clan_count(chat_id)
                settings = await self.get_chat_settings(chat_id)
                
                if clan_count >= settings.max_clans_per_chat:
                    raise DatabaseError(
                        f"Достигнут лимит кланов для чата ({settings.max_clans_per_chat})"
                    )
                
                # Подготавливаем метаданные
                metadata = {
                    'war_wins': clan_data.war_wins,
                    'war_win_streak': clan_data.war_win_streak,
                    'location': clan_data.location,
                    'badge_url': clan_data.badge_url,
                    'registered_description': description
                }
                
                # Вставляем клан
                cursor = await db.execute("""
                    INSERT INTO registered_clans (
                        clan_tag, clan_name, clan_description, clan_level,
                        clan_points, member_count, chat_id, registered_by,
                        clan_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clan_data.tag,
                    clan_data.name,
                    description or clan_data.description,
                    clan_data.level,
                    clan_data.points,
                    clan_data.member_count,
                    chat_id,
                    registered_by,
                    json.dumps(metadata)
                ))
                
                clan_id = cursor.lastrowid
                await db.commit()
                
                # Если это первый клан в чате, делаем его основным
                if clan_count == 0:
                    await self._set_default_clan_id(db, chat_id, clan_id)
                    await db.commit()
                
                logger.info(f"Registered clan {clan_data.tag} with ID {clan_id}")
                return clan_id
                
        except ClanAlreadyRegistered:
            raise
        except Exception as e:
            logger.error(f"Database error registering clan {clan_data.tag}: {e}")
            raise DatabaseError(f"Failed to register clan: {e}")
    
    async def get_chat_clans(self, chat_id: int, active_only: bool = True) -> List[ClanInfo]:
        """Получить все кланы чата"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT id, clan_tag, clan_name, clan_description, clan_level,
                           clan_points, member_count, chat_id, registered_by,
                           registered_at, is_active, is_verified, last_updated, clan_metadata
                    FROM registered_clans 
                    WHERE chat_id = ?
                """
                params = [chat_id]
                
                if active_only:
                    query += " AND is_active = 1"
                
                query += " ORDER BY registered_at"
                
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                return [ClanInfo.from_db_row(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting chat clans for {chat_id}: {e}")
            return []
    
    async def get_clan_by_id(self, clan_id: int) -> Optional[ClanInfo]:
        """Получить клан по ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT id, clan_tag, clan_name, clan_description, clan_level,
                           clan_points, member_count, chat_id, registered_by,
                           registered_at, is_active, is_verified, last_updated, clan_metadata
                    FROM registered_clans WHERE id = ?
                """, (clan_id,))
                
                row = await cursor.fetchone()
                return ClanInfo.from_db_row(row) if row else None
                
        except Exception as e:
            logger.error(f"Error getting clan by ID {clan_id}: {e}")
            return None
    
    async def get_clan_by_tag(self, clan_tag: str, chat_id: int = None) -> Optional[ClanInfo]:
        """Получить клан по тегу"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT id, clan_tag, clan_name, clan_description, clan_level,
                           clan_points, member_count, chat_id, registered_by,
                           registered_at, is_active, is_verified, last_updated, clan_metadata
                    FROM registered_clans WHERE clan_tag = ? AND is_active = 1
                """
                params = [clan_tag]
                
                if chat_id:
                    query += " AND chat_id = ?"
                    params.append(chat_id)
                
                cursor = await db.execute(query, params)
                row = await cursor.fetchone()
                
                return ClanInfo.from_db_row(row) if row else None
                
        except Exception as e:
            logger.error(f"Error getting clan by tag {clan_tag}: {e}")
            return None
    
    async def update_clan_data(self, clan_id: int, clan_data: ClanData) -> bool:
        """Обновить данные клана из CoC API"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Получаем текущие метаданные
                cursor = await db.execute(
                    "SELECT clan_metadata FROM registered_clans WHERE id = ?",
                    (clan_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return False
                
                # Обновляем метаданные
                current_metadata = json.loads(row[0] or '{}')
                current_metadata.update({
                    'war_wins': clan_data.war_wins,
                    'war_win_streak': clan_data.war_win_streak,
                    'location': clan_data.location,
                    'badge_url': clan_data.badge_url,
                    'last_api_update': datetime.now().isoformat()
                })
                
                # Обновляем данные
                await db.execute("""
                    UPDATE registered_clans SET
                        clan_name = ?, clan_level = ?, clan_points = ?,
                        member_count = ?, last_updated = CURRENT_TIMESTAMP,
                        clan_metadata = ?
                    WHERE id = ?
                """, (
                    clan_data.name, clan_data.level, clan_data.points,
                    clan_data.member_count, json.dumps(current_metadata), clan_id
                ))
                
                await db.commit()
                logger.info(f"Updated clan data for ID {clan_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating clan {clan_id}: {e}")
            return False
    
    async def get_chat_clan_count(self, chat_id: int, active_only: bool = True) -> int:
        """Получить количество кланов в чате"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT COUNT(*) FROM registered_clans WHERE chat_id = ?"
                params = [chat_id]
                
                if active_only:
                    query += " AND is_active = 1"
                
                cursor = await db.execute(query, params)
                result = await cursor.fetchone()
                
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Error getting clan count for chat {chat_id}: {e}")
            return 0
    
    async def get_chat_settings(self, chat_id: int) -> ChatClanSettings:
        """Получить настройки чата (создать если не существует)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT id, chat_id, chat_title, default_clan_id, max_clans_per_chat,
                           show_clan_numbers, auto_detect_clan, admin_only_registration,
                           created_at, updated_at
                    FROM chat_clan_settings WHERE chat_id = ?
                """, (chat_id,))
                
                row = await cursor.fetchone()
                
                if row:
                    return ChatClanSettings.from_db_row(row)
                else:
                    # Создаем настройки по умолчанию
                    return await self._create_default_chat_settings(db, chat_id)
                    
        except Exception as e:
            logger.error(f"Error getting chat settings for {chat_id}: {e}")
            return ChatClanSettings.default_for_chat(chat_id)
    
    async def _create_default_chat_settings(self, db: aiosqlite.Connection, chat_id: int) -> ChatClanSettings:
        """Создать настройки чата по умолчанию"""
        cursor = await db.execute("""
            INSERT INTO chat_clan_settings (chat_id, max_clans_per_chat, show_clan_numbers,
                                          auto_detect_clan, admin_only_registration)
            VALUES (?, 10, 1, 1, 1)
        """, (chat_id,))
        
        settings_id = cursor.lastrowid
        await db.commit()
        
        # Возвращаем созданные настройки
        cursor = await db.execute("""
            SELECT id, chat_id, chat_title, default_clan_id, max_clans_per_chat,
                   show_clan_numbers, auto_detect_clan, admin_only_registration,
                   created_at, updated_at
            FROM chat_clan_settings WHERE id = ?
        """, (settings_id,))
        
        row = await cursor.fetchone()
        return ChatClanSettings.from_db_row(row)
    
    async def _set_default_clan_id(self, db: aiosqlite.Connection, chat_id: int, clan_id: int):
        """Установить основной клан чата"""
        await db.execute("""
            UPDATE chat_clan_settings SET default_clan_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """, (clan_id, chat_id))
    
    async def set_default_clan(self, chat_id: int, clan_id: int) -> bool:
        """Установить основной клан чата"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем что клан существует и принадлежит чату
                cursor = await db.execute(
                    "SELECT id FROM registered_clans WHERE id = ? AND chat_id = ? AND is_active = 1",
                    (clan_id, chat_id)
                )
                
                if not await cursor.fetchone():
                    return False
                
                await self._set_default_clan_id(db, chat_id, clan_id)
                await db.commit()
                
                logger.info(f"Set default clan {clan_id} for chat {chat_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting default clan {clan_id} for chat {chat_id}: {e}")
            return False
    
    async def get_chat_title(self, chat_id: int) -> str:
        """Получить название чата (или ID если название неизвестно)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT chat_title FROM chat_clan_settings WHERE chat_id = ?",
                    (chat_id,)
                )
                row = await cursor.fetchone()
                
                if row and row[0]:
                    return row[0]
                else:
                    return f"Chat {chat_id}"
                    
        except Exception as e:
            logger.error(f"Error getting chat title for {chat_id}: {e}")
            return f"Chat {chat_id}"
    
    async def log_operation(self, log_entry: ClanOperationLog) -> int:
        """Записать лог операции"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO clan_operation_logs (
                        operation_type, clan_id, clan_tag, chat_id, user_id,
                        username, operation_details, result, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry.operation_type, log_entry.clan_id, log_entry.clan_tag,
                    log_entry.chat_id, log_entry.user_id, log_entry.username,
                    json.dumps(log_entry.operation_details), log_entry.result,
                    log_entry.error_message
                ))
                
                log_id = cursor.lastrowid
                await db.commit()
                
                return log_id
                
        except Exception as e:
            logger.error(f"Error logging operation: {e}")
            return 0


# Singleton instance
_clan_db_service: Optional[ClanDatabaseService] = None


def init_clan_db_service(db_path: str) -> ClanDatabaseService:
    """Инициализировать глобальный сервис БД кланов"""
    global _clan_db_service
    _clan_db_service = ClanDatabaseService(db_path)
    return _clan_db_service


def get_clan_db_service() -> ClanDatabaseService:
    """Получить глобальный сервис БД кланов"""
    if _clan_db_service is None:
        raise RuntimeError("Clan DB service not initialized. Call init_clan_db_service() first.")
    return _clan_db_service