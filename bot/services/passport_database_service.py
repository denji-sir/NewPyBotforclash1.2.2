"""
Сервис для работы с паспортами игроков
"""
import logging
import aiosqlite
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from ..models.passport_models import (
    PassportInfo, PassportOperationLog, PassportStatus, PassportSettings,
    PassportStats, PlayerBinding, PassportNotFound, PassportAlreadyExists,
    PassportValidationError, PassportAccessDenied
)

logger = logging.getLogger(__name__)


class PassportDatabaseService:
    """Сервис для работы с базой данных паспортов"""
    
    def __init__(self, db_path: str = "data/passports.db"):
        # Извлекаем путь из database URL (например, sqlite+aiosqlite:///./data/database/bot.db)
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
    
    async def create_passport(self, user_id: int, chat_id: int, username: Optional[str] = None,
                             display_name: Optional[str] = None, preferred_clan_id: Optional[int] = None) -> PassportInfo:
        """
        Создание нового паспорта
        
        Args:
            user_id: ID пользователя Telegram
            chat_id: ID чата
            username: Имя пользователя
            display_name: Отображаемое имя
            preferred_clan_id: ID предпочитаемого клана
            
        Returns:
            PassportInfo: Созданный паспорт
        """
        try:
            # Проверяем, не существует ли уже паспорт
            existing = await self.get_passport_by_user(user_id, chat_id)
            if existing:
                raise PassportAlreadyExists(f"Паспорт для пользователя {user_id} уже существует")
            
            # Создаем новый паспорт
            passport = PassportInfo(
                user_id=user_id,
                chat_id=chat_id,
                username=username,
                display_name=display_name or username,
                preferred_clan_id=preferred_clan_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            async with aiosqlite.connect(self.db_path) as db:
                # Если указан клан, получаем его данные
                if preferred_clan_id:
                    clan_data = await self._get_clan_data_by_id(db, preferred_clan_id)
                    if clan_data:
                        passport.preferred_clan_tag = clan_data['clan_tag']
                        passport.preferred_clan_name = clan_data['clan_name']
                
                # Вставляем в БД
                cursor = await db.execute("""
                    INSERT INTO user_passports 
                    (user_id, chat_id, username, display_name, bio, avatar_url, 
                     created_at, updated_at, status, preferred_clan_id, preferred_clan_tag,
                     settings, stats, metadata, player_binding, preferred_clan_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, passport.to_db_values())
                
                passport.id = cursor.lastrowid
                await db.commit()
                
            logger.info(f"Created passport {passport.id} for user {user_id}")
            return passport
            
        except PassportAlreadyExists:
            raise
        except Exception as e:
            logger.error(f"Error creating passport for user {user_id}: {e}")
            raise PassportValidationError(f"Ошибка создания паспорта: {e}")
    
    async def get_passport_by_user(self, user_id: int, chat_id: int) -> Optional[PassportInfo]:
        """
        Получение паспорта по пользователю
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            
        Returns:
            Optional[PassportInfo]: Паспорт или None
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT p.*, c.clan_name 
                    FROM user_passports p
                    LEFT JOIN registered_clans c ON p.preferred_clan_id = c.id
                    WHERE p.user_id = ? AND p.chat_id = ?
                """, (user_id, chat_id)) as cursor:
                    row = await cursor.fetchone()
                    
            if row:
                return PassportInfo.from_db_row(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting passport for user {user_id}: {e}")
            return None
    
    async def get_passport_by_id(self, passport_id: int) -> Optional[PassportInfo]:
        """
        Получение паспорта по ID
        
        Args:
            passport_id: ID паспорта
            
        Returns:
            Optional[PassportInfo]: Паспорт или None
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT p.*, c.clan_name 
                    FROM user_passports p
                    LEFT JOIN registered_clans c ON p.preferred_clan_id = c.id
                    WHERE p.id = ?
                """, (passport_id,)) as cursor:
                    row = await cursor.fetchone()
                    
            if row:
                return PassportInfo.from_db_row(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting passport {passport_id}: {e}")
            return None
    
    async def get_chat_passports(self, chat_id: int, status: Optional[PassportStatus] = None) -> List[PassportInfo]:
        """
        Получение всех паспортов чата
        
        Args:
            chat_id: ID чата
            status: Фильтр по статусу
            
        Returns:
            List[PassportInfo]: Список паспортов
        """
        try:
            query = """
                SELECT p.*, c.clan_name 
                FROM user_passports p
                LEFT JOIN registered_clans c ON p.preferred_clan_id = c.id
                WHERE p.chat_id = ?
            """
            params = [chat_id]
            
            if status:
                query += " AND p.status = ?"
                params.append(status.value)
            
            query += " ORDER BY p.created_at DESC"
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    
            return [PassportInfo.from_db_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting chat passports for {chat_id}: {e}")
            return []
    
    async def update_passport(self, passport_id: int, **kwargs) -> bool:
        """
        Обновление паспорта
        
        Args:
            passport_id: ID паспорта
            **kwargs: Поля для обновления
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            # Получаем текущий паспорт
            passport = await self.get_passport_by_id(passport_id)
            if not passport:
                raise PassportNotFound(f"Паспорт {passport_id} не найден")
            
            # Подготавливаем поля для обновления
            update_fields = []
            params = []
            
            # Простые поля
            simple_fields = ['username', 'display_name', 'bio', 'avatar_url', 'status']
            for field in simple_fields:
                if field in kwargs:
                    update_fields.append(f"{field} = ?")
                    params.append(kwargs[field])
            
            # Обновляем настройки
            if 'settings' in kwargs:
                if isinstance(kwargs['settings'], PassportSettings):
                    settings_json = json.dumps(kwargs['settings'].to_dict())
                else:
                    settings_json = json.dumps(kwargs['settings'])
                update_fields.append("settings = ?")
                params.append(settings_json)
            
            # Обновляем статистику
            if 'stats' in kwargs:
                if isinstance(kwargs['stats'], PassportStats):
                    stats_json = json.dumps(kwargs['stats'].to_dict())
                else:
                    stats_json = json.dumps(kwargs['stats'])
                update_fields.append("stats = ?")
                params.append(stats_json)
            
            # Обновляем привязку игрока
            if 'player_binding' in kwargs:
                if kwargs['player_binding'] is None:
                    player_binding_json = None
                elif isinstance(kwargs['player_binding'], PlayerBinding):
                    player_binding_json = json.dumps(kwargs['player_binding'].to_dict())
                else:
                    player_binding_json = json.dumps(kwargs['player_binding'])
                update_fields.append("player_binding = ?")
                params.append(player_binding_json)
            
            # Обновляем предпочитаемый клан
            if 'preferred_clan_id' in kwargs:
                update_fields.append("preferred_clan_id = ?")
                params.append(kwargs['preferred_clan_id'])
                
                # Получаем данные клана
                if kwargs['preferred_clan_id']:
                    async with aiosqlite.connect(self.db_path) as db:
                        clan_data = await self._get_clan_data_by_id(db, kwargs['preferred_clan_id'])
                        if clan_data:
                            update_fields.extend(["preferred_clan_tag = ?", "preferred_clan_name = ?"])
                            params.extend([clan_data['clan_tag'], clan_data['clan_name']])
                else:
                    update_fields.extend(["preferred_clan_tag = ?", "preferred_clan_name = ?"])
                    params.extend([None, None])
            
            # Всегда обновляем время изменения
            update_fields.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            # Формируем запрос
            if not update_fields:
                return True  # Нечего обновлять
            
            query = f"UPDATE user_passports SET {', '.join(update_fields)} WHERE id = ?"
            params.append(passport_id)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, params)
                await db.commit()
                
            logger.info(f"Updated passport {passport_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating passport {passport_id}: {e}")
            return False
    
    async def delete_passport(self, passport_id: int) -> bool:
        """
        Удаление паспорта
        
        Args:
            passport_id: ID паспорта
            
        Returns:
            bool: True если удаление успешно
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Сначала удаляем логи
                await db.execute(
                    "DELETE FROM passport_operation_logs WHERE passport_id = ?",
                    (passport_id,)
                )
                
                # Затем удаляем паспорт
                cursor = await db.execute(
                    "DELETE FROM user_passports WHERE id = ?",
                    (passport_id,)
                )
                
                await db.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Deleted passport {passport_id}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting passport {passport_id}: {e}")
            return False
    
    async def log_operation(self, log_entry: PassportOperationLog) -> bool:
        """
        Запись операции в лог
        
        Args:
            log_entry: Запись лога
            
        Returns:
            bool: True если запись успешна
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO passport_operation_logs
                    (passport_id, operation_type, user_id, username, operation_details, 
                     timestamp, result, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry.passport_id,
                    log_entry.operation_type,
                    log_entry.user_id,
                    log_entry.username,
                    json.dumps(log_entry.operation_details),
                    log_entry.timestamp.isoformat() if log_entry.timestamp else datetime.now().isoformat(),
                    log_entry.result,
                    log_entry.error_message
                ))
                
                await db.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Error logging passport operation: {e}")
            return False
    
    async def get_passport_stats_summary(self, chat_id: int) -> Dict[str, Any]:
        """
        Получение сводной статистики паспортов чата
        
        Args:
            chat_id: ID чата
            
        Returns:
            Dict[str, Any]: Сводная статистика
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Общее количество паспортов
                async with db.execute(
                    "SELECT COUNT(*) FROM user_passports WHERE chat_id = ?",
                    (chat_id,)
                ) as cursor:
                    total_passports = (await cursor.fetchone())[0]
                
                # Активные паспорты
                async with db.execute(
                    "SELECT COUNT(*) FROM user_passports WHERE chat_id = ? AND status = 'active'",
                    (chat_id,)
                ) as cursor:
                    active_passports = (await cursor.fetchone())[0]
                
                # Паспорты с привязанными игроками
                async with db.execute(
                    "SELECT COUNT(*) FROM user_passports WHERE chat_id = ? AND player_binding IS NOT NULL",
                    (chat_id,)
                ) as cursor:
                    bound_passports = (await cursor.fetchone())[0]
                
                # Паспорты с предпочитаемыми кланами
                async with db.execute(
                    "SELECT COUNT(*) FROM user_passports WHERE chat_id = ? AND preferred_clan_id IS NOT NULL",
                    (chat_id,)
                ) as cursor:
                    clan_bound_passports = (await cursor.fetchone())[0]
                
            return {
                'total_passports': total_passports,
                'active_passports': active_passports,
                'bound_passports': bound_passports,
                'clan_bound_passports': clan_bound_passports,
                'completion_rate': (bound_passports / total_passports * 100) if total_passports > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting passport stats summary: {e}")
            return {
                'total_passports': 0,
                'active_passports': 0,
                'bound_passports': 0,
                'clan_bound_passports': 0,
                'completion_rate': 0
            }
    
    async def _get_clan_data_by_id(self, db: aiosqlite.Connection, clan_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных клана по ID"""
        try:
            async with db.execute(
                "SELECT clan_tag, clan_name FROM registered_clans WHERE id = ?",
                (clan_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
            if row:
                return {
                    'clan_tag': row[0],
                    'clan_name': row[1]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting clan data for ID {clan_id}: {e}")
            return None


# Глобальные функции
_passport_db_service = None

def init_passport_db_service(db_path: str) -> PassportDatabaseService:
    """Инициализация глобального сервиса БД паспортов"""
    global _passport_db_service
    _passport_db_service = PassportDatabaseService(db_path)
    return _passport_db_service

def get_passport_db_service() -> PassportDatabaseService:
    """Получение экземпляра сервиса БД паспортов"""
    global _passport_db_service
    if _passport_db_service is None:
        # Автоинициализация в тестовом режиме
        import os
        if os.getenv("TESTING") == "1":
            init_passport_db_service(":memory:")
        else:
            raise RuntimeError("Passport DB service not initialized. Call init_passport_db_service() first.")
    return _passport_db_service