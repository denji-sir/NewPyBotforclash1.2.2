"""
Админ команды для управления rate limiting
Позволяют администраторам просматривать статистику и управлять блокировками
"""

import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from typing import List

from ..services.rate_limit_service import get_rate_limit_service, UserBlock, BlockReason
from ..utils.permissions import is_group_admin

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("rate_limits"))
async def rate_limits_command(message: Message):
    """
    Показать статистику по rate limiting в чате
    Доступно только администраторам
    
    Usage: /rate_limits
    """
    try:
        # Проверка прав администратора
        is_admin = await is_group_admin(message.from_user.id, message.chat.id, message.bot)
        if not is_admin:
            await message.reply(
                "❌ Эта команда доступна только администраторам чата!"
            )
            return
        
        rate_limit_service = get_rate_limit_service()
        
        # Получаем список заблокированных пользователей
        blocked_users = await rate_limit_service.get_blocked_users(message.chat.id)
        
        if not blocked_users:
            await message.reply(
                "✅ **Rate Limiting - Статистика**\n\n"
                "📊 В данный момент нет заблокированных пользователей.\n\n"
                "ℹ️ Система автоматически блокирует пользователей при спаме командами:\n"
                "• 4+ одинаковых команд за 10 секунд = блокировка\n"
                "• 1-е нарушение: 5 минут\n"
                "• 2-е нарушение: 1 час\n"
                "• 3-е нарушение: 1 день\n"
                "• 4+ нарушений: 7 дней",
                parse_mode="Markdown"
            )
            return
        
        # Формируем список заблокированных
        blocked_list = []
        for i, block in enumerate(blocked_users[:10], 1):  # Показываем до 10
            remaining = (block.blocked_until - datetime.now()).total_seconds()
            time_str = _format_time(remaining)
            
            reason_emoji = {
                BlockReason.SPAM_COMMANDS: "🚫",
                BlockReason.REPEATED_VIOLATIONS: "⚠️",
                BlockReason.MANUAL_ADMIN: "🔒"
            }
            emoji = reason_emoji.get(block.reason, "❌")
            
            blocked_list.append(
                f"{i}. {emoji} User ID `{block.user_id}`\n"
                f"   Нарушение #{block.violations_count} • Осталось: {time_str}"
            )
        
        message_text = (
            f"🚫 **Заблокированные пользователи ({len(blocked_users)})**\n\n"
            + "\n\n".join(blocked_list)
        )
        
        if len(blocked_users) > 10:
            message_text += f"\n\n_...и ещё {len(blocked_users) - 10}_"
        
        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"rl_refresh:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="📊 Детальная статистика",
                callback_data=f"rl_stats:{message.from_user.id}"
            )]
        ])
        
        await message.reply(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in rate_limits_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при получении статистики rate limiting."
        )


@router.message(Command("unblock_user"))
async def unblock_user_command(message: Message):
    """
    Разблокировать пользователя
    Доступно только администраторам
    
    Usage: 
    /unblock_user <user_id>
    /unblock_user (в ответ на сообщение пользователя)
    """
    try:
        # Проверка прав администратора
        is_admin = await is_group_admin(message.from_user.id, message.chat.id, message.bot)
        if not is_admin:
            await message.reply(
                "❌ Эта команда доступна только администраторам чата!"
            )
            return
        
        # Определяем ID пользователя
        target_user_id = None
        
        # Вариант 1: ID в тексте команды
        parts = message.text.split()
        if len(parts) > 1:
            try:
                target_user_id = int(parts[1])
            except ValueError:
                await message.reply(
                    "❌ Неверный формат ID пользователя!\n\n"
                    "Используйте:\n"
                    "`/unblock_user 123456789`\n"
                    "или ответьте на сообщение пользователя",
                    parse_mode="Markdown"
                )
                return
        
        # Вариант 2: В ответ на сообщение
        elif message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        
        else:
            await message.reply(
                "❌ Укажите ID пользователя или ответьте на его сообщение!\n\n"
                "Используйте:\n"
                "`/unblock_user 123456789`\n"
                "или ответьте на сообщение пользователя",
                parse_mode="Markdown"
            )
            return
        
        rate_limit_service = get_rate_limit_service()
        
        # Проверяем, был ли пользователь заблокирован
        block = await rate_limit_service._get_user_block(target_user_id, message.chat.id)
        
        if not block:
            await message.reply(
                f"ℹ️ Пользователь `{target_user_id}` не заблокирован.",
                parse_mode="Markdown"
            )
            return
        
        # Разблокируем
        success = await rate_limit_service.unblock_user(
            user_id=target_user_id,
            chat_id=message.chat.id,
            admin_id=message.from_user.id
        )
        
        if success:
            await message.reply(
                f"✅ **Пользователь разблокирован**\n\n"
                f"👤 User ID: `{target_user_id}`\n"
                f"👮 Разблокировал: {message.from_user.mention_html()}\n\n"
                f"Пользователь снова может использовать команды бота.",
                parse_mode="HTML"
            )
            logger.info(f"Admin {message.from_user.id} unblocked user {target_user_id}")
        else:
            await message.reply(
                "❌ Не удалось разблокировать пользователя."
            )
        
    except Exception as e:
        logger.error(f"Error in unblock_user_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при разблокировке пользователя."
        )


@router.message(Command("block_user"))
async def block_user_command(message: Message):
    """
    Вручную заблокировать пользователя
    Доступно только администраторам
    
    Usage:
    /block_user <user_id> <duration_minutes>
    /block_user (в ответ на сообщение) <duration_minutes>
    """
    try:
        # Проверка прав администратора
        is_admin = await is_group_admin(message.from_user.id, message.chat.id, message.bot)
        if not is_admin:
            await message.reply(
                "❌ Эта команда доступна только администраторам чата!"
            )
            return
        
        parts = message.text.split()
        target_user_id = None
        duration_minutes = None
        
        # Парсинг аргументов
        if message.reply_to_message:
            # В ответ на сообщение
            target_user_id = message.reply_to_message.from_user.id
            if len(parts) > 1:
                try:
                    duration_minutes = int(parts[1])
                except ValueError:
                    pass
        elif len(parts) >= 3:
            # ID и длительность в тексте
            try:
                target_user_id = int(parts[1])
                duration_minutes = int(parts[2])
            except ValueError:
                pass
        
        # Валидация
        if not target_user_id or not duration_minutes:
            await message.reply(
                "❌ Неверный формат команды!\n\n"
                "**Использование:**\n"
                "`/block_user 123456789 60` - заблокировать на 60 минут\n"
                "или ответьте на сообщение:\n"
                "`/block_user 60`",
                parse_mode="Markdown"
            )
            return
        
        if duration_minutes < 1 or duration_minutes > 10080:  # Максимум неделя
            await message.reply(
                "❌ Длительность должна быть от 1 до 10080 минут (7 дней)!"
            )
            return
        
        rate_limit_service = get_rate_limit_service()
        
        # Блокируем пользователя
        success = await rate_limit_service.manual_block_user(
            user_id=target_user_id,
            chat_id=message.chat.id,
            duration_seconds=duration_minutes * 60,
            admin_id=message.from_user.id,
            reason="manual_admin"
        )
        
        if success:
            time_str = _format_time(duration_minutes * 60)
            await message.reply(
                f"🔒 **Пользователь заблокирован**\n\n"
                f"👤 User ID: `{target_user_id}`\n"
                f"⏱️ Длительность: {time_str}\n"
                f"👮 Заблокировал: {message.from_user.mention_html()}\n\n"
                f"Пользователь не сможет использовать команды бота до истечения блокировки.",
                parse_mode="HTML"
            )
            logger.info(
                f"Admin {message.from_user.id} manually blocked user {target_user_id} "
                f"for {duration_minutes} minutes"
            )
        else:
            await message.reply(
                "❌ Не удалось заблокировать пользователя."
            )
        
    except Exception as e:
        logger.error(f"Error in block_user_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при блокировке пользователя."
        )


@router.message(Command("user_rl_stats"))
async def user_rl_stats_command(message: Message):
    """
    Показать статистику rate limiting для пользователя
    Доступно только администраторам
    
    Usage:
    /user_rl_stats <user_id>
    /user_rl_stats (в ответ на сообщение)
    """
    try:
        # Проверка прав администратора
        is_admin = await is_group_admin(message.from_user.id, message.chat.id, message.bot)
        if not is_admin:
            await message.reply(
                "❌ Эта команда доступна только администраторам чата!"
            )
            return
        
        # Определяем ID пользователя
        target_user_id = None
        
        parts = message.text.split()
        if len(parts) > 1:
            try:
                target_user_id = int(parts[1])
            except ValueError:
                pass
        elif message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        
        if not target_user_id:
            await message.reply(
                "❌ Укажите ID пользователя или ответьте на его сообщение!\n\n"
                "Используйте:\n"
                "`/user_rl_stats 123456789`",
                parse_mode="Markdown"
            )
            return
        
        rate_limit_service = get_rate_limit_service()
        
        # Получаем статистику
        stats = await rate_limit_service.get_user_statistics(
            user_id=target_user_id,
            chat_id=message.chat.id
        )
        
        # Формируем сообщение
        message_text = f"📊 **Статистика пользователя**\n\n"
        message_text += f"👤 User ID: `{target_user_id}`\n"
        message_text += f"⚠️ Всего нарушений: {stats['violations_total']}\n\n"
        
        if stats['currently_blocked']:
            blocked_until = datetime.fromisoformat(stats['blocked_until'])
            remaining = (blocked_until - datetime.now()).total_seconds()
            time_str = _format_time(remaining)
            
            message_text += f"🚫 **Текущая блокировка:**\n"
            message_text += f"• Причина: {stats['block_reason']}\n"
            message_text += f"• Осталось: {time_str}\n\n"
        else:
            message_text += "✅ Пользователь не заблокирован\n\n"
        
        if stats['last_violation']:
            last_time = datetime.fromisoformat(stats['last_violation']['time'])
            message_text += f"📅 **Последнее нарушение:**\n"
            message_text += f"• Дата: {last_time.strftime('%d.%m.%Y %H:%M')}\n"
            message_text += f"• Команда: /{stats['last_violation']['command']}\n"
            message_text += f"• Блокировка: {_format_time(stats['last_violation']['duration'])}\n"
        
        await message.reply(
            message_text,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in user_rl_stats_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при получении статистики пользователя."
        )


# === CALLBACK HANDLERS ===

@router.callback_query(F.data.startswith("rl_refresh:"))
async def refresh_rate_limits_callback(callback: CallbackQuery):
    """Обновить список заблокированных пользователей"""
    try:
        admin_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        rate_limit_service = get_rate_limit_service()
        blocked_users = await rate_limit_service.get_blocked_users(callback.message.chat.id)
        
        if not blocked_users:
            await callback.message.edit_text(
                "✅ **Rate Limiting - Статистика**\n\n"
                "📊 В данный момент нет заблокированных пользователей.",
                parse_mode="Markdown"
            )
            await callback.answer("Обновлено ✅")
            return
        
        # Формируем обновлённый список
        blocked_list = []
        for i, block in enumerate(blocked_users[:10], 1):
            remaining = (block.blocked_until - datetime.now()).total_seconds()
            time_str = _format_time(remaining)
            
            reason_emoji = {
                BlockReason.SPAM_COMMANDS: "🚫",
                BlockReason.REPEATED_VIOLATIONS: "⚠️",
                BlockReason.MANUAL_ADMIN: "🔒"
            }
            emoji = reason_emoji.get(block.reason, "❌")
            
            blocked_list.append(
                f"{i}. {emoji} User ID `{block.user_id}`\n"
                f"   Нарушение #{block.violations_count} • Осталось: {time_str}"
            )
        
        message_text = (
            f"🚫 **Заблокированные пользователи ({len(blocked_users)})**\n\n"
            + "\n\n".join(blocked_list)
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"rl_refresh:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="📊 Детальная статистика",
                callback_data=f"rl_stats:{admin_id}"
            )]
        ])
        
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer("Обновлено ✅")
        
    except Exception as e:
        logger.error(f"Error in refresh_rate_limits_callback: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)


# === HELPER FUNCTIONS ===

def _format_time(seconds: float) -> str:
    """Форматирование времени в читаемый вид"""
    if seconds < 60:
        return f"{int(seconds)} сек"
    elif seconds < 3600:
        return f"{int(seconds / 60)} мин"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} ч {minutes} мин"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days} дн {hours} ч"
