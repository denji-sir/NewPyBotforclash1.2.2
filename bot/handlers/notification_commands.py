"""
Команды управления уведомлениями
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
import logging

from ..services.war_notification_service import get_war_notification_service

logger = logging.getLogger(__name__)

notification_router = Router()


@notification_router.message(Command("notif_off"))
async def cmd_notif_off(message: Message):
    """Отключить упоминания в КВ-уведомлениях"""
    try:
        war_notif = get_war_notification_service()
        
        success = await war_notif.set_user_notification_settings(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            allow_mentions=False,
            allow_dm=True
        )
        
        if success:
            await message.reply(
                "✅ Упоминания в КВ-уведомлениях отключены.\n"
                "Вы больше не будете получать теги в напоминаниях.\n\n"
                "Для включения используйте /notif_on"
            )
        else:
            await message.reply("❌ Ошибка при изменении настроек")
    
    except Exception as e:
        logger.error(f"Error in notif_off: {e}")
        await message.reply("❌ Произошла ошибка")


@notification_router.message(Command("notif_on"))
async def cmd_notif_on(message: Message):
    """Включить упоминания в КВ-уведомлениях"""
    try:
        war_notif = get_war_notification_service()
        
        success = await war_notif.set_user_notification_settings(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            allow_mentions=True,
            allow_dm=True
        )
        
        if success:
            await message.reply(
                "✅ Упоминания в КВ-уведомлениях включены.\n"
                "Вы будете получать теги в напоминаниях о КВ.\n\n"
                "Для отключения используйте /notif_off"
            )
        else:
            await message.reply("❌ Ошибка при изменении настроек")
    
    except Exception as e:
        logger.error(f"Error in notif_on: {e}")
        await message.reply("❌ Произошла ошибка")


@notification_router.message(Command("notif_status"))
async def cmd_notif_status(message: Message):
    """Показать текущие настройки уведомлений"""
    try:
        war_notif = get_war_notification_service()
        
        # Получаем настройки из БД
        import aiosqlite
        async with aiosqlite.connect(war_notif.db_path) as db:
            cursor = await db.execute("""
                SELECT allow_mentions, allow_dm FROM user_notification_settings
                WHERE user_id = ? AND chat_id = ?
            """, (message.from_user.id, message.chat.id))
            row = await cursor.fetchone()
        
        if row:
            allow_mentions, allow_dm = row
            status_mentions = "✅ Включены" if allow_mentions else "❌ Отключены"
            status_dm = "✅ Включены" if allow_dm else "❌ Отключены"
        else:
            # По умолчанию всё включено
            status_mentions = "✅ Включены (по умолчанию)"
            status_dm = "✅ Включены (по умолчанию)"
        
        await message.reply(
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Упоминания в чате: {status_mentions}\n"
            f"Личные сообщения: {status_dm}\n\n"
            f"Команды:\n"
            f"/notif_off - отключить упоминания\n"
            f"/notif_on - включить упоминания",
            parse_mode="HTML"
        )
    
    except Exception as e:
        logger.error(f"Error in notif_status: {e}")
        await message.reply("❌ Произошла ошибка")
