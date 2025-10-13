"""
Сервис КВ-оповещений с двумя сообщениями (тикер и H-6)
"""
import logging
import aiosqlite
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

logger = logging.getLogger(__name__)


class WarNotificationService:
    """Сервис для управления КВ-оповещениями"""
    
    def __init__(self, bot: Bot, db_path: str):
        self.bot = bot
        # Извлекаем путь из database URL
        if ':///' in db_path:
            self.db_path = db_path.split(':///')[-1]
        elif '://' in db_path:
            self.db_path = db_path.split('://')[-1]
        else:
            self.db_path = db_path
        
        self.MAX_MENTIONS = 20  # Максимум упоминаний в одном сообщении
    
    async def start_war_tracking(
        self,
        clan_tag: str,
        chat_id: int,
        war_data: Dict[str, Any]
    ) -> bool:
        """
        Начать отслеживание КВ и создать тикер
        
        Args:
            clan_tag: Тег клана
            chat_id: ID чата
            war_data: Данные войны из API
            
        Returns:
            True если успешно
        """
        try:
            war_id = self._generate_war_id(war_data)
            war_start = war_data.get('startTime', '')
            war_end = war_data.get('endTime', '')
            
            # Проверяем, не отслеживается ли уже эта война
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT id, ticker_message_id FROM active_war_notifications
                    WHERE clan_tag = ? AND war_id = ? AND state = 'active'
                """, (clan_tag, war_id))
                existing = await cursor.fetchone()
                
                if existing:
                    logger.info(f"War {war_id} already being tracked")
                    return True
                
                # Создаем запись
                await db.execute("""
                    INSERT INTO active_war_notifications (
                        clan_tag, chat_id, war_id, war_start_time, war_end_time, state
                    ) VALUES (?, ?, ?, ?, ?, 'active')
                """, (clan_tag, chat_id, war_id, war_start, war_end))
                await db.commit()
            
            # Создаем тикер-сообщение
            await self._create_ticker_message(clan_tag, chat_id, war_id, war_data)
            
            logger.info(f"Started tracking war {war_id} for clan {clan_tag}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting war tracking: {e}")
            return False
    
    async def _create_ticker_message(
        self,
        clan_tag: str,
        chat_id: int,
        war_id: str,
        war_data: Dict[str, Any]
    ):
        """Создать тикер-сообщение"""
        try:
            text = self._format_ticker_text(war_data)
            
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            
            # Сохраняем ID сообщения
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE active_war_notifications
                    SET ticker_message_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE clan_tag = ? AND war_id = ?
                """, (message.message_id, clan_tag, war_id))
                await db.commit()
            
            logger.info(f"Created ticker message {message.message_id} for war {war_id}")
            
        except TelegramAPIError as e:
            logger.error(f"Failed to create ticker message: {e}")
    
    async def update_ticker(
        self,
        clan_tag: str,
        war_data: Dict[str, Any]
    ) -> bool:
        """
        Обновить тикер-сообщение
        
        Args:
            clan_tag: Тег клана
            war_data: Актуальные данные войны
            
        Returns:
            True если успешно
        """
        try:
            war_id = self._generate_war_id(war_data)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT chat_id, ticker_message_id FROM active_war_notifications
                    WHERE clan_tag = ? AND war_id = ? AND state = 'active'
                """, (clan_tag, war_id))
                row = await cursor.fetchone()
                
                if not row or not row[1]:
                    return False
                
                chat_id, message_id = row
            
            # Обновляем текст сообщения
            text = self._format_ticker_text(war_data)
            
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="HTML"
            )
            
            return True
            
        except TelegramAPIError as e:
            if "message is not modified" not in str(e).lower():
                logger.error(f"Failed to update ticker: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating ticker: {e}")
            return False
    
    async def send_h6_reminder(
        self,
        clan_tag: str,
        war_data: Dict[str, Any]
    ) -> bool:
        """
        Отправить H-6 напоминание
        
        Args:
            clan_tag: Тег клана
            war_data: Данные войны
            
        Returns:
            True если успешно
        """
        try:
            war_id = self._generate_war_id(war_data)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT chat_id, h6_sent FROM active_war_notifications
                    WHERE clan_tag = ? AND war_id = ? AND state = 'active'
                """, (clan_tag, war_id))
                row = await cursor.fetchone()
                
                if not row:
                    return False
                
                chat_id, h6_sent = row
                
                # Проверяем, не отправляли ли уже
                if h6_sent:
                    logger.info(f"H-6 reminder already sent for war {war_id}")
                    return True
            
            # Получаем список игроков без всех атак
            players_without_attacks = await self._get_players_without_attacks(
                clan_tag, chat_id, war_data
            )
            
            # Формируем текст
            text = await self._format_h6_text(war_data, players_without_attacks, chat_id)
            
            # Отправляем сообщение
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            
            # Сохраняем ID сообщения и отмечаем как отправленное
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE active_war_notifications
                    SET h6_message_id = ?, h6_sent = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE clan_tag = ? AND war_id = ?
                """, (message.message_id, clan_tag, war_id))
                await db.commit()
            
            logger.info(f"Sent H-6 reminder for war {war_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending H-6 reminder: {e}")
            return False
    
    async def cleanup_war_messages(
        self,
        clan_tag: str,
        war_id: str
    ) -> bool:
        """
        Удалить оба сообщения после окончания КВ
        
        Args:
            clan_tag: Тег клана
            war_id: ID войны
            
        Returns:
            True если успешно
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT chat_id, ticker_message_id, h6_message_id
                    FROM active_war_notifications
                    WHERE clan_tag = ? AND war_id = ? AND state = 'active'
                """, (clan_tag, war_id))
                row = await cursor.fetchone()
                
                if not row:
                    return False
                
                chat_id, ticker_id, h6_id = row
                
                # Удаляем тикер
                if ticker_id:
                    try:
                        await self.bot.delete_message(chat_id=chat_id, message_id=ticker_id)
                        logger.info(f"Deleted ticker message {ticker_id}")
                    except TelegramAPIError as e:
                        logger.warning(f"Failed to delete ticker: {e}")
                
                # Удаляем H-6
                if h6_id:
                    try:
                        await self.bot.delete_message(chat_id=chat_id, message_id=h6_id)
                        logger.info(f"Deleted H-6 message {h6_id}")
                    except TelegramAPIError as e:
                        logger.warning(f"Failed to delete H-6: {e}")
                
                # Помечаем как завершенное
                await db.execute("""
                    UPDATE active_war_notifications
                    SET state = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE clan_tag = ? AND war_id = ?
                """, (clan_tag, war_id))
                await db.commit()
            
            logger.info(f"Cleaned up war {war_id} messages")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up war messages: {e}")
            return False
    
    def _generate_war_id(self, war_data: Dict[str, Any]) -> str:
        """Генерировать уникальный ID войны"""
        start_time = war_data.get('startTime', '')
        clan_tag = war_data.get('clan', {}).get('tag', '')
        opponent_tag = war_data.get('opponent', {}).get('tag', '')
        return f"{clan_tag}_{opponent_tag}_{start_time}"
    
    def _format_ticker_text(self, war_data: Dict[str, Any]) -> str:
        """Форматировать текст тикера"""
        clan = war_data.get('clan', {})
        opponent = war_data.get('opponent', {})
        
        # Подсчет времени до конца
        end_time_str = war_data.get('endTime', '')
        time_left = self._calculate_time_left(end_time_str)
        
        # Подсчет атак
        clan_members = clan.get('members', [])
        total_attacks = len(clan_members) * 2
        used_attacks = sum(len(m.get('attacks', [])) for m in clan_members)
        
        # Список игроков с оставшимися атаками
        players_with_attacks = []
        for member in clan_members:
            attacks_used = len(member.get('attacks', []))
            if attacks_used < 2:
                remaining = 2 - attacks_used
                players_with_attacks.append(f"{member.get('name', '?')} ({remaining})")
        
        text = (
            f"⚔️ <b>КВ — Лайв-сводка</b>\n\n"
            f"⏱️ До конца: <b>{time_left}</b>\n"
            f"📊 Счёт: <b>{clan.get('stars', 0)} - {opponent.get('stars', 0)}</b> "
            f"({clan.get('destructionPercentage', 0):.1f}% - {opponent.get('destructionPercentage', 0):.1f}%)\n"
            f"⚔️ Атаки: <b>{used_attacks}/{total_attacks}</b>\n\n"
        )
        
        if players_with_attacks:
            # Показываем первых 10
            shown = players_with_attacks[:10]
            text += "🎯 Остались атаки:\n" + "\n".join(f"• {p}" for p in shown)
            if len(players_with_attacks) > 10:
                text += f"\n…и ещё {len(players_with_attacks) - 10}"
        else:
            text += "✅ Все атаки использованы!"
        
        return text
    
    async def _format_h6_text(
        self,
        war_data: Dict[str, Any],
        players_without_attacks: List[Dict[str, Any]],
        chat_id: int
    ) -> str:
        """Форматировать текст H-6 напоминания"""
        total_unused = sum(2 - p['attacks_used'] for p in players_without_attacks)
        
        text = (
            f"⚔️ <b>До конца КВ осталось 6 часов!</b>\n\n"
            f"Проверьте атаки и донат.\n"
            f"Не использовано атак: <b>{total_unused}</b>\n\n"
        )
        
        if players_without_attacks:
            mentions = []
            for player in players_without_attacks[:self.MAX_MENTIONS]:
                mention = await self._get_player_mention(player, chat_id)
                attacks_left = 2 - player['attacks_used']
                mentions.append(f"• {mention} ({attacks_left})")
            
            text += "Не добили:\n" + "\n".join(mentions)
            
            if len(players_without_attacks) > self.MAX_MENTIONS:
                text += f"\n…и ещё {len(players_without_attacks) - self.MAX_MENTIONS}"
        
        return text
    
    async def _get_players_without_attacks(
        self,
        clan_tag: str,
        chat_id: int,
        war_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Получить список игроков без всех атак"""
        clan_members = war_data.get('clan', {}).get('members', [])
        players = []
        
        for member in clan_members:
            attacks_used = len(member.get('attacks', []))
            if attacks_used < 2:
                players.append({
                    'tag': member.get('tag', '').replace('#', '').upper(),
                    'name': member.get('name', ''),
                    'attacks_used': attacks_used
                })
        
        return players
    
    async def _get_player_mention(
        self,
        player: Dict[str, Any],
        chat_id: int
    ) -> str:
        """Получить упоминание игрока с учетом настроек"""
        try:
            # Ищем привязку игрока к Telegram
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT pb.user_id, up.username, uns.allow_mentions
                    FROM player_bindings pb
                    LEFT JOIN user_passports up ON pb.user_id = up.user_id AND pb.chat_id = up.chat_id
                    LEFT JOIN user_notification_settings uns ON pb.user_id = uns.user_id AND pb.chat_id = uns.chat_id
                    WHERE pb.player_tag = ? AND pb.chat_id = ?
                    LIMIT 1
                """, (player['tag'], chat_id))
                row = await cursor.fetchone()
                
                if row:
                    user_id, username, allow_mentions = row
                    # По умолчанию разрешаем упоминания
                    if allow_mentions is None:
                        allow_mentions = True
                    
                    if allow_mentions:
                        if user_id:
                            return f"<a href='tg://user?id={user_id}'>{player['name']}</a>"
                        elif username:
                            return f"@{username}"
                
                # Если нет привязки или запрещены упоминания
                return player['name']
                
        except Exception as e:
            logger.error(f"Error getting player mention: {e}")
            return player['name']
    
    def _calculate_time_left(self, end_time_str: str) -> str:
        """Вычислить оставшееся время"""
        try:
            # Формат: 20250110T120000.000Z
            end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%S.%fZ")
            now = datetime.utcnow()
            delta = end_time - now
            
            if delta.total_seconds() < 0:
                return "Завершена"
            
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            
            if hours > 0:
                return f"{hours}ч {minutes}м"
            else:
                return f"{minutes}м"
                
        except Exception as e:
            logger.error(f"Error calculating time left: {e}")
            return "?"
    
    async def set_user_notification_settings(
        self,
        user_id: int,
        chat_id: int,
        allow_mentions: bool = True,
        allow_dm: bool = True
    ) -> bool:
        """Установить настройки уведомлений пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO user_notification_settings (user_id, chat_id, allow_mentions, allow_dm)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, chat_id) DO UPDATE SET
                        allow_mentions = excluded.allow_mentions,
                        allow_dm = excluded.allow_dm,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, chat_id, allow_mentions, allow_dm))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting notification settings: {e}")
            return False


# Глобальный экземпляр
_war_notification_service: Optional[WarNotificationService] = None


def init_war_notification_service(bot: Bot, db_path: str) -> WarNotificationService:
    """Инициализация глобального сервиса КВ-оповещений"""
    global _war_notification_service
    _war_notification_service = WarNotificationService(bot, db_path)
    return _war_notification_service


def get_war_notification_service() -> WarNotificationService:
    """Получение глобального сервиса КВ-оповещений"""
    global _war_notification_service
    if _war_notification_service is None:
        raise RuntimeError("War notification service not initialized.")
    return _war_notification_service
