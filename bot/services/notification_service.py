"""
Сервис уведомлений для отправки сообщений пользователям
"""
import logging
from typing import List, Optional, Dict, Any
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений пользователям"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_notification(
        self, 
        chat_id: int, 
        text: str,
        parse_mode: Optional[str] = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Отправить уведомление в чат
        
        Args:
            chat_id: ID чата
            text: Текст уведомления
            parse_mode: Режим парсинга (HTML, Markdown)
            disable_notification: Отключить звук уведомления
            
        Returns:
            True если отправлено успешно
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification
            )
            logger.info(f"Notification sent to chat {chat_id}")
            return True
            
        except TelegramAPIError as e:
            logger.error(f"Failed to send notification to chat {chat_id}: {e}")
            return False
    
    async def send_bulk_notifications(
        self,
        chat_ids: List[int],
        text: str,
        parse_mode: Optional[str] = "HTML"
    ) -> Dict[str, int]:
        """
        Отправить уведомления в несколько чатов
        
        Args:
            chat_ids: Список ID чатов
            text: Текст уведомления
            parse_mode: Режим парсинга
            
        Returns:
            Словарь с количеством успешных и неудачных отправок
        """
        success = 0
        failed = 0
        
        for chat_id in chat_ids:
            if await self.send_notification(chat_id, text, parse_mode):
                success += 1
            else:
                failed += 1
        
        logger.info(f"Bulk notifications sent: {success} success, {failed} failed")
        return {"success": success, "failed": failed}
    
    async def notify_war_start(
        self,
        chat_id: int,
        clan_name: str,
        opponent_name: str,
        war_size: int
    ) -> bool:
        """Уведомление о начале КВ"""
        text = (
            f"⚔️ <b>Началась Клановая Война!</b>\n\n"
            f"🏰 Клан: <b>{clan_name}</b>\n"
            f"🎯 Противник: <b>{opponent_name}</b>\n"
            f"👥 Размер: <b>{war_size} vs {war_size}</b>\n\n"
            f"Удачи в бою! 💪"
        )
        return await self.send_notification(chat_id, text)
    
    async def notify_war_end(
        self,
        chat_id: int,
        clan_name: str,
        result: str,
        stars: int,
        opponent_stars: int
    ) -> bool:
        """Уведомление об окончании КВ"""
        emoji = "🏆" if result == "win" else "😔" if result == "lose" else "🤝"
        result_text = "Победа!" if result == "win" else "Поражение" if result == "lose" else "Ничья"
        
        text = (
            f"{emoji} <b>Клановая Война завершена!</b>\n\n"
            f"🏰 Клан: <b>{clan_name}</b>\n"
            f"📊 Результат: <b>{result_text}</b>\n"
            f"⭐ Звезды: <b>{stars} - {opponent_stars}</b>\n"
        )
        return await self.send_notification(chat_id, text)
    
    async def notify_raid_weekend_start(
        self,
        chat_id: int,
        clan_name: str
    ) -> bool:
        """Уведомление о начале рейдовых выходных"""
        text = (
            f"🏛️ <b>Начались Рейдовые Выходные!</b>\n\n"
            f"🏰 Клан: <b>{clan_name}</b>\n"
            f"⚔️ Время атаковать столицу клана!\n\n"
            f"Удачных рейдов! 💰"
        )
        return await self.send_notification(chat_id, text)
    
    async def notify_raid_weekend_end(
        self,
        chat_id: int,
        clan_name: str,
        total_loot: int,
        raids_completed: int
    ) -> bool:
        """Уведомление об окончании рейдовых выходных"""
        text = (
            f"🏛️ <b>Рейдовые Выходные завершены!</b>\n\n"
            f"🏰 Клан: <b>{clan_name}</b>\n"
            f"💰 Награбленное золото: <b>{total_loot:,}</b>\n"
            f"⚔️ Завершено рейдов: <b>{raids_completed}</b>\n"
        )
        return await self.send_notification(chat_id, text)
    
    async def notify_achievement_unlocked(
        self,
        chat_id: int,
        user_id: int,
        achievement_name: str,
        achievement_description: str,
        points: int
    ) -> bool:
        """Уведомление о разблокировке достижения"""
        text = (
            f"🏆 <b>Достижение разблокировано!</b>\n\n"
            f"👤 Пользователь: <a href='tg://user?id={user_id}'>@user</a>\n"
            f"🎯 Достижение: <b>{achievement_name}</b>\n"
            f"📝 {achievement_description}\n"
            f"⭐ Очки: <b>+{points}</b>\n"
        )
        return await self.send_notification(chat_id, text)
    
    async def notify_daily_baseline_update(
        self,
        chat_id: int,
        success_count: int,
        failed_count: int
    ) -> bool:
        """Уведомление об обновлении ежедневных базисов"""
        text = (
            f"📊 <b>Обновление ежедневных базисов</b>\n\n"
            f"✅ Успешно: <b>{success_count}</b>\n"
            f"❌ Ошибок: <b>{failed_count}</b>\n"
        )
        return await self.send_notification(chat_id, text, disable_notification=True)


# Глобальный экземпляр
_notification_service: Optional[NotificationService] = None


def init_notification_service(bot: Bot) -> NotificationService:
    """Инициализация глобального сервиса уведомлений"""
    global _notification_service
    _notification_service = NotificationService(bot)
    return _notification_service


def get_notification_service() -> NotificationService:
    """Получение глобального сервиса уведомлений"""
    global _notification_service
    if _notification_service is None:
        raise RuntimeError("Notification service not initialized. Call init_notification_service() first.")
    return _notification_service
