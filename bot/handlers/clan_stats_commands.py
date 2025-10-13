"""
Команды статистики клана: донаты, руководители, топ чата
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import logging
from typing import Dict, List, Optional
from datetime import datetime

from ..services.extended_clash_api import ExtendedClashAPI
from ..services.clan_database_service import get_clan_db_service

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("donations", "donates"))
async def cmd_clan_donations(message: Message, command: CommandObject):
    """
    Статистика донатов клана
    Использование: /donations [тег_клана]
    """
    try:
        # Получаем тег клана
        clan_tag = None
        if command.args:
            clan_tag = command.args.strip()
        else:
            # Пытаемся получить клан из чата
            clan_db = get_clan_db_service()
            clans = await clan_db.get_chat_clans(message.chat.id)
            if clans:
                clan_tag = clans[0]['clan_tag']
        
        if not clan_tag:
            await message.reply(
                "❌ Укажите тег клана: /donations #TAG\n"
                "Или зарегистрируйте клан в этом чате."
            )
            return
        
        # Нормализуем тег
        if not clan_tag.startswith('#'):
            clan_tag = '#' + clan_tag
        
        await message.reply("⏳ Загружаю статистику донатов...")
        
        # Получаем данные клана через API
        clash_api = ExtendedClashAPI([])  # TODO: получить токены
        clan_data = await clash_api.get_clan(clan_tag)
        
        if not clan_data:
            await message.reply("❌ Клан не найден")
            return
        
        # Сортируем участников по донатам
        members = clan_data.get('memberList', [])
        members_sorted = sorted(members, key=lambda x: x.get('donations', 0), reverse=True)
        
        # Формируем текст
        text_lines = [
            f"📊 <b>Донаты клана {clan_data.get('name', '')}</b>",
            f"👥 Участников: {len(members)}\n"
        ]
        
        # Подсчитываем общую статистику
        total_donations = sum(m.get('donations', 0) for m in members)
        total_received = sum(m.get('donationsReceived', 0) for m in members)
        
        text_lines.extend([
            f"💰 <b>Общая статистика:</b>",
            f"Отдано: {total_donations:,}",
            f"Получено: {total_received:,}",
            f"Средний донат: {total_donations // len(members) if members else 0:,}\n"
        ])
        
        # Топ-10 донатеров
        text_lines.append("🏆 <b>Топ-10 донатеров:</b>")
        
        medals = ['🥇', '🥈', '🥉']
        for i, member in enumerate(members_sorted[:10], 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = member.get('name', 'Unknown')
            donations = member.get('donations', 0)
            received = member.get('donationsReceived', 0)
            
            text_lines.append(
                f"{medal} <b>{name}</b>\n"
                f"    Отдал: {donations:,} | Получил: {received:,}"
            )
        
        # Участники без донатов
        no_donations = [m for m in members if m.get('donations', 0) == 0]
        if no_donations:
            text_lines.append(f"\n⚠️ Без донатов: {len(no_donations)} чел.")
        
        await message.reply("\n".join(text_lines), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in donations command: {e}")
        await message.reply("❌ Ошибка получения статистики донатов")


@router.message(Command("leaders", "leadership"))
async def cmd_clan_leaders(message: Message, command: CommandObject):
    """
    Список руководителей клана (глава, соруки)
    Использование: /leaders [тег_клана]
    """
    try:
        # Получаем тег клана
        clan_tag = None
        if command.args:
            clan_tag = command.args.strip()
        else:
            # Пытаемся получить клан из чата
            clan_db = get_clan_db_service()
            clans = await clan_db.get_chat_clans(message.chat.id)
            if clans:
                clan_tag = clans[0]['clan_tag']
        
        if not clan_tag:
            await message.reply(
                "❌ Укажите тег клана: /leaders #TAG\n"
                "Или зарегистрируйте клан в этом чате."
            )
            return
        
        # Нормализуем тег
        if not clan_tag.startswith('#'):
            clan_tag = '#' + clan_tag
        
        await message.reply("⏳ Загружаю список руководителей...")
        
        # Получаем данные клана через API
        clash_api = ExtendedClashAPI([])  # TODO: получить токены
        clan_data = await clash_api.get_clan(clan_tag)
        
        if not clan_data:
            await message.reply("❌ Клан не найден")
            return
        
        members = clan_data.get('memberList', [])
        
        # Группируем по ролям
        leader = []
        co_leaders = []
        elders = []
        
        for member in members:
            role = member.get('role', 'member')
            if role == 'leader':
                leader.append(member)
            elif role == 'coLeader':
                co_leaders.append(member)
            elif role == 'admin':
                elders.append(member)
        
        # Сортируем соруков по алфавиту
        co_leaders.sort(key=lambda x: x.get('name', '').lower())
        elders.sort(key=lambda x: x.get('name', '').lower())
        
        # Формируем текст
        text_lines = [
            f"👑 <b>Руководство клана {clan_data.get('name', '')}</b>\n"
        ]
        
        # Глава (первым)
        if leader:
            text_lines.append("👑 <b>Глава:</b>")
            for member in leader:
                name = member.get('name', 'Unknown')
                tag = member.get('tag', '')
                trophies = member.get('trophies', 0)
                donations = member.get('donations', 0)
                text_lines.append(
                    f"   <b>{name}</b> {tag}\n"
                    f"   🏆 {trophies:,} | 💰 {donations:,}\n"
                )
        
        # Соруководители (по алфавиту)
        if co_leaders:
            text_lines.append("🔱 <b>Соруководители:</b>")
            for member in co_leaders:
                name = member.get('name', 'Unknown')
                tag = member.get('tag', '')
                trophies = member.get('trophies', 0)
                donations = member.get('donations', 0)
                text_lines.append(
                    f"   • <b>{name}</b> {tag}\n"
                    f"     🏆 {trophies:,} | 💰 {donations:,}"
                )
            text_lines.append("")
        
        # Старейшины (опционально)
        if elders:
            text_lines.append(f"⭐ <b>Старейшин:</b> {len(elders)} чел.")
        
        # Общая статистика
        text_lines.extend([
            "",
            f"📊 <b>Всего участников:</b> {len(members)}",
            f"👑 Глав: {len(leader)}",
            f"🔱 Соруков: {len(co_leaders)}",
            f"⭐ Старейшин: {len(elders)}",
            f"👤 Участников: {len(members) - len(leader) - len(co_leaders) - len(elders)}"
        ])
        
        await message.reply("\n".join(text_lines), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in leaders command: {e}")
        await message.reply("❌ Ошибка получения списка руководителей")


@router.message(Command("top"))
async def cmd_chat_top(message: Message):
    """
    Топ активных участников чата по сообщениям и символам
    """
    try:
        import aiosqlite
        from ..services.clan_database_service import get_clan_db_service
        
        clan_db = get_clan_db_service()
        db_path = clan_db.db_path
        
        # Создаем таблицу статистики чата если не существует
        async with aiosqlite.connect(db_path) as db:
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
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_stats 
                ON chat_statistics(chat_id, message_count DESC)
            """)
            await db.commit()
            
            # Получаем статистику
            cursor = await db.execute("""
                SELECT 
                    user_id, username, first_name, 
                    message_count, character_count
                FROM chat_statistics
                WHERE chat_id = ?
                ORDER BY message_count DESC
                LIMIT 15
            """, (message.chat.id,))
            
            rows = await cursor.fetchall()
        
        if not rows:
            await message.reply(
                "📊 Статистика чата пока пуста.\n"
                "Начните общаться, и я буду собирать статистику!"
            )
            return
        
        # Формируем текст
        text_lines = [
            "📊 <b>Топ активных участников чата</b>\n"
        ]
        
        # Подсчитываем общую статистику
        total_messages = sum(row[3] for row in rows)
        total_chars = sum(row[4] for row in rows)
        
        text_lines.extend([
            f"💬 Всего сообщений: {total_messages:,}",
            f"📝 Всего символов: {total_chars:,}\n"
        ])
        
        # Топ по сообщениям
        text_lines.append("🏆 <b>По сообщениям:</b>")
        medals = ['🥇', '🥈', '🥉']
        
        for i, row in enumerate(rows[:10], 1):
            user_id, username, first_name, msg_count, char_count = row
            
            medal = medals[i-1] if i <= 3 else f"{i}."
            
            # Формируем имя
            if username:
                name = f"@{username}"
            elif first_name:
                name = first_name
            else:
                name = f"User {user_id}"
            
            # Процент от общего
            percent = (msg_count / total_messages * 100) if total_messages > 0 else 0
            avg_chars = char_count // msg_count if msg_count > 0 else 0
            
            text_lines.append(
                f"{medal} <b>{name}</b>\n"
                f"    💬 {msg_count:,} сообщений ({percent:.1f}%)\n"
                f"    📝 {char_count:,} символов (ср. {avg_chars})"
            )
        
        # Топ по символам
        rows_by_chars = sorted(rows, key=lambda x: x[4], reverse=True)[:5]
        text_lines.append("\n📝 <b>Топ-5 по символам:</b>")
        
        for i, row in enumerate(rows_by_chars, 1):
            user_id, username, first_name, msg_count, char_count = row
            
            if username:
                name = f"@{username}"
            elif first_name:
                name = first_name
            else:
                name = f"User {user_id}"
            
            text_lines.append(f"{i}. <b>{name}</b> - {char_count:,} символов")
        
        await message.reply("\n".join(text_lines), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in top command: {e}")
        await message.reply("❌ Ошибка получения статистики чата")


# Middleware для сбора статистики сообщений
from aiogram import BaseMiddleware
from aiogram.types import Message as AiogramMessage
from typing import Callable, Dict, Any, Awaitable


class ChatStatisticsMiddleware(BaseMiddleware):
    """Middleware для сбора статистики сообщений в чате"""
    
    async def __call__(
        self,
        handler: Callable[[AiogramMessage, Dict[str, Any]], Awaitable[Any]],
        event: AiogramMessage,
        data: Dict[str, Any]
    ) -> Any:
        # Сначала обрабатываем сообщение
        result = await handler(event, data)
        
        # Затем собираем статистику (только для групповых чатов)
        if event.chat.type in ['group', 'supergroup']:
            try:
                await self._update_statistics(event)
            except Exception as e:
                logger.error(f"Error updating chat statistics: {e}")
        
        return result
    
    async def _update_statistics(self, message: AiogramMessage):
        """Обновить статистику сообщения"""
        try:
            import aiosqlite
            from ..services.clan_database_service import get_clan_db_service
            
            clan_db = get_clan_db_service()
            db_path = clan_db.db_path
            
            # Подсчитываем символы
            char_count = len(message.text or message.caption or "")
            
            async with aiosqlite.connect(db_path) as db:
                # Обновляем или создаем запись
                await db.execute("""
                    INSERT INTO chat_statistics (
                        chat_id, user_id, username, first_name,
                        message_count, character_count, last_message_date
                    ) VALUES (?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(chat_id, user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name,
                        message_count = message_count + 1,
                        character_count = character_count + excluded.character_count,
                        last_message_date = excluded.last_message_date,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    message.chat.id,
                    message.from_user.id,
                    message.from_user.username,
                    message.from_user.first_name,
                    char_count,
                    datetime.now().isoformat()
                ))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error in _update_statistics: {e}")
