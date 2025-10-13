"""
Сервис для защиты от спама командами (Rate Limiting)
Блокирует пользователей при злоупотреблении командами
"""

import asyncio
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BlockReason(Enum):
    """Причины блокировки"""
    SPAM_COMMANDS = "spam_commands"      # Спам одной командой
    REPEATED_VIOLATIONS = "repeated"      # Повторные нарушения
    MANUAL_ADMIN = "manual_admin"        # Ручная блокировка админом


class BlockDuration(Enum):
    """Длительность блокировки"""
    SHORT = 300         # 5 минут (первое нарушение)
    MEDIUM = 3600       # 1 час (второе нарушение)
    LONG = 86400        # 1 день (третье нарушение)
    WEEK = 604800       # 7 дней (4+ нарушения)


@dataclass
class UserBlock:
    """Информация о блокировке пользователя"""
    user_id: int
    chat_id: int
    blocked_until: datetime
    reason: BlockReason
    violations_count: int
    blocked_at: datetime
    blocked_by: Optional[int] = None  # ID админа (если ручная блокировка)


@dataclass
class CommandUsage:
    """Использование команды пользователем"""
    user_id: int
    chat_id: int
    command: str
    timestamp: datetime
    count: int = 1


class RateLimitService:
    """
    Сервис для отслеживания и блокировки спама командами
    
    Правила:
    - 4+ одинаковых команд за короткое время = блокировка
    - Первое нарушение: блок на 5 минут
    - Второе нарушение: блок на 1 час
    - Третье нарушение: блок на 1 день
    - 4+ нарушений: блок на неделю
    """
    
    def __init__(self, db_path: str = "data/bot.db"):
        """
        Инициализация сервиса
        
        Args:
            db_path: Путь к базе данных
        """
        self.db_path = db_path
        
        # Настройки антиспама
        self.SPAM_THRESHOLD = 4          # Количество команд для спама
        self.SPAM_WINDOW = 10            # Окно времени в секундах
        self.COMMAND_COOLDOWN = 2        # Cooldown между командами (сек)
        
        # Кэш последних команд пользователей (user_id -> [CommandUsage])
        self._command_cache: Dict[int, List[CommandUsage]] = {}
        
        # Кэш блокировок (user_id -> UserBlock)
        self._blocks_cache: Dict[int, UserBlock] = {}
        
        # Блокировка для thread-safety
        self._lock = asyncio.Lock()
    
    async def initialize_database(self):
        """Создание таблиц в БД"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица блокировок
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_blocks (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    blocked_at TEXT NOT NULL,
                    blocked_until TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    violations_count INTEGER DEFAULT 1,
                    blocked_by INTEGER,
                    PRIMARY KEY (user_id, chat_id)
                )
            """)
            
            # Таблица истории нарушений
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    violation_time TEXT NOT NULL,
                    command_count INTEGER NOT NULL,
                    block_duration INTEGER NOT NULL
                )
            """)
            
            # Таблица использования команд (для статистики)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS command_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    used_at TEXT NOT NULL,
                    was_blocked BOOLEAN DEFAULT 0
                )
            """)
            
            # Индексы для производительности
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_blocks_user 
                ON user_blocks(user_id, chat_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_violations_user 
                ON rate_limit_violations(user_id, chat_id)
            """)
            
            await db.commit()
            logger.info("✅ Rate limit database initialized")
    
    async def check_rate_limit(
        self, 
        user_id: int, 
        chat_id: int, 
        command: str
    ) -> tuple[bool, Optional[str]]:
        """
        Проверка, может ли пользователь выполнить команду
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            command: Название команды
            
        Returns:
            (allowed, reason): (можно ли выполнить, причина блокировки)
        """
        async with self._lock:
            # 1. Проверяем активную блокировку
            if await self._is_user_blocked(user_id, chat_id):
                block = await self._get_user_block(user_id, chat_id)
                if block:
                    remaining = (block.blocked_until - datetime.now()).total_seconds()
                    return False, self._format_block_message(block, remaining)
            
            # 2. Проверяем спам
            is_spam = await self._check_command_spam(user_id, chat_id, command)
            
            if is_spam:
                # Создаём блокировку за спам
                await self._create_block_for_spam(user_id, chat_id, command)
                block = await self._get_user_block(user_id, chat_id)
                remaining = (block.blocked_until - datetime.now()).total_seconds()
                return False, self._format_block_message(block, remaining)
            
            # 3. Логируем использование команды
            await self._log_command_usage(user_id, chat_id, command, was_blocked=False)
            
            return True, None
    
    async def _is_user_blocked(self, user_id: int, chat_id: int) -> bool:
        """Проверка активной блокировки"""
        # Проверяем кэш
        cache_key = f"{user_id}_{chat_id}"
        if cache_key in self._blocks_cache:
            block = self._blocks_cache[cache_key]
            if block.blocked_until > datetime.now():
                return True
            else:
                # Блокировка истекла
                del self._blocks_cache[cache_key]
                await self._remove_expired_block(user_id, chat_id)
        
        # Проверяем БД
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT blocked_until FROM user_blocks
                WHERE user_id = ? AND chat_id = ?
            """, (user_id, chat_id))
            
            row = await cursor.fetchone()
            if row:
                blocked_until = datetime.fromisoformat(row[0])
                if blocked_until > datetime.now():
                    return True
                else:
                    # Удаляем истёкшую блокировку
                    await self._remove_expired_block(user_id, chat_id)
        
        return False
    
    async def _get_user_block(self, user_id: int, chat_id: int) -> Optional[UserBlock]:
        """Получение информации о блокировке"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT user_id, chat_id, blocked_at, blocked_until, 
                       reason, violations_count, blocked_by
                FROM user_blocks
                WHERE user_id = ? AND chat_id = ?
            """, (user_id, chat_id))
            
            row = await cursor.fetchone()
            if row:
                return UserBlock(
                    user_id=row[0],
                    chat_id=row[1],
                    blocked_at=datetime.fromisoformat(row[2]),
                    blocked_until=datetime.fromisoformat(row[3]),
                    reason=BlockReason(row[4]),
                    violations_count=row[5],
                    blocked_by=row[6]
                )
        
        return None
    
    async def _check_command_spam(
        self, 
        user_id: int, 
        chat_id: int, 
        command: str
    ) -> bool:
        """
        Проверка на спам одной командой
        
        Спам = 4+ одинаковых команд за 10 секунд
        """
        now = datetime.now()
        cache_key = user_id
        
        # Инициализируем кэш для пользователя
        if cache_key not in self._command_cache:
            self._command_cache[cache_key] = []
        
        # Удаляем старые записи (> 10 секунд)
        self._command_cache[cache_key] = [
            usage for usage in self._command_cache[cache_key]
            if (now - usage.timestamp).total_seconds() < self.SPAM_WINDOW
        ]
        
        # Считаем одинаковые команды за последние 10 секунд
        same_commands = [
            usage for usage in self._command_cache[cache_key]
            if usage.command == command and usage.chat_id == chat_id
        ]
        
        # Добавляем текущую команду
        self._command_cache[cache_key].append(
            CommandUsage(user_id, chat_id, command, now)
        )
        
        # Проверяем превышение лимита
        if len(same_commands) >= self.SPAM_THRESHOLD - 1:  # -1 т.к. текущая уже добавлена
            logger.warning(
                f"🚫 Spam detected: user {user_id} used /{command} "
                f"{len(same_commands) + 1} times in {self.SPAM_WINDOW}s"
            )
            return True
        
        return False
    
    async def _create_block_for_spam(
        self, 
        user_id: int, 
        chat_id: int, 
        command: str
    ):
        """Создание блокировки за спам"""
        # Получаем количество предыдущих нарушений
        violations_count = await self._get_violations_count(user_id, chat_id)
        
        # Определяем длительность блокировки
        block_duration = self._calculate_block_duration(violations_count)
        
        now = datetime.now()
        blocked_until = now + timedelta(seconds=block_duration)
        
        # Сохраняем блокировку в БД
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_blocks 
                (user_id, chat_id, blocked_at, blocked_until, reason, violations_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, chat_id, 
                now.isoformat(), 
                blocked_until.isoformat(),
                BlockReason.SPAM_COMMANDS.value,
                violations_count + 1
            ))
            
            # Логируем нарушение
            await db.execute("""
                INSERT INTO rate_limit_violations
                (user_id, chat_id, command, violation_time, command_count, block_duration)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, chat_id, command, 
                now.isoformat(),
                self.SPAM_THRESHOLD,
                block_duration
            ))
            
            await db.commit()
        
        # Обновляем кэш
        self._blocks_cache[f"{user_id}_{chat_id}"] = UserBlock(
            user_id=user_id,
            chat_id=chat_id,
            blocked_at=now,
            blocked_until=blocked_until,
            reason=BlockReason.SPAM_COMMANDS,
            violations_count=violations_count + 1
        )
        
        logger.warning(
            f"🚫 User {user_id} blocked for {block_duration}s "
            f"(violation #{violations_count + 1})"
        )
    
    async def _get_violations_count(self, user_id: int, chat_id: int) -> int:
        """Получение количества нарушений пользователя за последние 30 дней"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM rate_limit_violations
                WHERE user_id = ? AND chat_id = ?
                AND violation_time > ?
            """, (user_id, chat_id, thirty_days_ago.isoformat()))
            
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    def _calculate_block_duration(self, violations_count: int) -> int:
        """Расчёт длительности блокировки в зависимости от количества нарушений"""
        if violations_count == 0:
            return BlockDuration.SHORT.value      # 5 минут
        elif violations_count == 1:
            return BlockDuration.MEDIUM.value     # 1 час
        elif violations_count == 2:
            return BlockDuration.LONG.value       # 1 день
        else:
            return BlockDuration.WEEK.value       # 7 дней
    
    def _format_block_message(self, block: UserBlock, remaining_seconds: float) -> str:
        """Форматирование сообщения о блокировке"""
        # Форматируем оставшееся время
        if remaining_seconds < 60:
            time_str = f"{int(remaining_seconds)} секунд"
        elif remaining_seconds < 3600:
            time_str = f"{int(remaining_seconds / 60)} минут"
        elif remaining_seconds < 86400:
            time_str = f"{int(remaining_seconds / 3600)} часов"
        else:
            time_str = f"{int(remaining_seconds / 86400)} дней"
        
        # Причина блокировки
        reason_map = {
            BlockReason.SPAM_COMMANDS: "спам командами",
            BlockReason.REPEATED_VIOLATIONS: "повторные нарушения",
            BlockReason.MANUAL_ADMIN: "блокировка администратором"
        }
        reason_str = reason_map.get(block.reason, "нарушение правил")
        
        message = (
            f"🚫 **Вы временно заблокированы**\n\n"
            f"**Причина:** {reason_str}\n"
            f"**Нарушение №:** {block.violations_count}\n"
            f"**Осталось:** {time_str}\n\n"
            f"⚠️ Не злоупотребляйте командами бота!"
        )
        
        return message
    
    async def _remove_expired_block(self, user_id: int, chat_id: int):
        """Удаление истёкшей блокировки"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM user_blocks
                WHERE user_id = ? AND chat_id = ?
                AND blocked_until < ?
            """, (user_id, chat_id, datetime.now().isoformat()))
            await db.commit()
    
    async def _log_command_usage(
        self, 
        user_id: int, 
        chat_id: int, 
        command: str, 
        was_blocked: bool = False
    ):
        """Логирование использования команды"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO command_usage_log
                (user_id, chat_id, command, used_at, was_blocked)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, chat_id, command, datetime.now().isoformat(), was_blocked))
            await db.commit()
    
    # === АДМИН МЕТОДЫ ===
    
    async def manual_block_user(
        self,
        user_id: int,
        chat_id: int,
        duration_seconds: int,
        admin_id: int,
        reason: str = "manual_admin"
    ) -> bool:
        """
        Ручная блокировка пользователя администратором
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            duration_seconds: Длительность блокировки в секундах
            admin_id: ID администратора
            reason: Причина блокировки
            
        Returns:
            True если успешно
        """
        now = datetime.now()
        blocked_until = now + timedelta(seconds=duration_seconds)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_blocks
                (user_id, chat_id, blocked_at, blocked_until, reason, violations_count, blocked_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, chat_id,
                now.isoformat(),
                blocked_until.isoformat(),
                reason,
                0,  # Ручная блокировка не считается нарушением
                admin_id
            ))
            await db.commit()
        
        logger.info(f"Admin {admin_id} blocked user {user_id} for {duration_seconds}s")
        return True
    
    async def unblock_user(
        self,
        user_id: int,
        chat_id: int,
        admin_id: Optional[int] = None
    ) -> bool:
        """
        Разблокировка пользователя
        
        Args:
            user_id: ID пользователя
            chat_id: ID чата
            admin_id: ID администратора (опционально)
            
        Returns:
            True если успешно
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM user_blocks
                WHERE user_id = ? AND chat_id = ?
            """, (user_id, chat_id))
            await db.commit()
        
        # Удаляем из кэша
        cache_key = f"{user_id}_{chat_id}"
        if cache_key in self._blocks_cache:
            del self._blocks_cache[cache_key]
        
        logger.info(f"User {user_id} unblocked (by admin {admin_id})")
        return True
    
    async def get_blocked_users(self, chat_id: int) -> List[UserBlock]:
        """Получение списка заблокированных пользователей в чате"""
        blocks = []
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT user_id, chat_id, blocked_at, blocked_until,
                       reason, violations_count, blocked_by
                FROM user_blocks
                WHERE chat_id = ? AND blocked_until > ?
            """, (chat_id, datetime.now().isoformat()))
            
            async for row in cursor:
                blocks.append(UserBlock(
                    user_id=row[0],
                    chat_id=row[1],
                    blocked_at=datetime.fromisoformat(row[2]),
                    blocked_until=datetime.fromisoformat(row[3]),
                    reason=BlockReason(row[4]),
                    violations_count=row[5],
                    blocked_by=row[6]
                ))
        
        return blocks
    
    async def get_user_statistics(
        self, 
        user_id: int, 
        chat_id: int
    ) -> Dict:
        """Получение статистики по пользователю"""
        async with aiosqlite.connect(self.db_path) as db:
            # Количество нарушений
            cursor = await db.execute("""
                SELECT COUNT(*) FROM rate_limit_violations
                WHERE user_id = ? AND chat_id = ?
            """, (user_id, chat_id))
            violations = (await cursor.fetchone())[0]
            
            # Последнее нарушение
            cursor = await db.execute("""
                SELECT violation_time, command, block_duration
                FROM rate_limit_violations
                WHERE user_id = ? AND chat_id = ?
                ORDER BY violation_time DESC LIMIT 1
            """, (user_id, chat_id))
            last_violation = await cursor.fetchone()
            
            # Текущая блокировка
            cursor = await db.execute("""
                SELECT blocked_until, reason
                FROM user_blocks
                WHERE user_id = ? AND chat_id = ?
            """, (user_id, chat_id))
            current_block = await cursor.fetchone()
        
        return {
            'violations_total': violations,
            'last_violation': {
                'time': last_violation[0] if last_violation else None,
                'command': last_violation[1] if last_violation else None,
                'duration': last_violation[2] if last_violation else None
            } if last_violation else None,
            'currently_blocked': current_block is not None,
            'blocked_until': current_block[0] if current_block else None,
            'block_reason': current_block[1] if current_block else None
        }


# Глобальный экземпляр сервиса
_rate_limit_service: Optional[RateLimitService] = None


def init_rate_limit_service(db_path: str = "data/bot.db") -> RateLimitService:
    """Инициализация глобального сервиса rate limiting"""
    global _rate_limit_service
    _rate_limit_service = RateLimitService(db_path)
    return _rate_limit_service


def get_rate_limit_service() -> RateLimitService:
    """Получение глобального сервиса rate limiting"""
    if _rate_limit_service is None:
        raise RuntimeError("Rate limit service not initialized")
    return _rate_limit_service
