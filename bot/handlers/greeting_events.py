"""
Обработчики событий новых участников для системы приветствий
"""

import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from typing import Optional

from ..services.greeting_service import greeting_service

logger = logging.getLogger(__name__)

router = Router()


# Обработчик новых участников

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER))
async def on_new_member_join(event: ChatMemberUpdated):
    """Обработчик присоединения нового участника"""
    
    try:
        # Получаем информацию о новом участнике
        new_member = event.new_chat_member.user
        chat = event.chat
        
        # Пропускаем ботов
        if new_member.is_bot:
            logger.debug(f"Пропускаем бота {new_member.username} в чате {chat.id}")
            return
        
        # Получаем данные для приветствия
        greeting_data = await greeting_service.handle_new_member(
            chat_id=chat.id,
            user_id=new_member.id,
            username=new_member.username or "",
            first_name=new_member.first_name or ""
        )
        
        if not greeting_data:
            logger.debug(f"Приветствия отключены для чата {chat.id}")
            return
        
        # Отправляем приветствие
        await send_greeting_message(event, new_member, greeting_data)
        
        logger.info(f"Отправлено приветствие для пользователя {new_member.id} в чате {chat.id}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки нового участника: {e}")


async def send_greeting_message(event: ChatMemberUpdated, new_member, greeting_data: dict):
    """Отправка приветственного сообщения"""
    
    try:
        bot = event.bot
        chat_id = event.chat.id
        
        # Подготавливаем клавиатуру
        keyboard = None
        if greeting_data.get('show_rules_button') and greeting_data.get('rules_text'):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Правила чата", callback_data="show_rules")]
            ])
        
        # Отправляем стикер (если есть)
        if greeting_data.get('sticker'):
            try:
                await bot.send_sticker(
                    chat_id=chat_id,
                    sticker=greeting_data['sticker']
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить стикер: {e}")
        
        # Отправляем текстовое приветствие
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=greeting_data['text'],
            reply_markup=keyboard,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        # Обновляем ID сообщения в истории
        await greeting_service.update_greeting_message_id(
            chat_id=chat_id,
            user_id=new_member.id,
            message_id=sent_message.message_id
        )
        
        # Планируем удаление сообщения (если настроено)
        delete_after = greeting_data.get('delete_after')
        if delete_after and delete_after > 0:
            await greeting_service.schedule_message_deletion(
                chat_id=chat_id,
                message_id=sent_message.message_id,
                delay_seconds=delete_after
            )
            
            # Запускаем задачу удаления
            asyncio.create_task(
                delete_message_after_delay(bot, chat_id, sent_message.message_id, delete_after)
            )
        
    except Exception as e:
        logger.error(f"Ошибка отправки приветственного сообщения: {e}")


async def delete_message_after_delay(bot, chat_id: int, message_id: int, delay_seconds: int):
    """Удаление сообщения после задержки"""
    
    try:
        await asyncio.sleep(delay_seconds)
        
        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        logger.debug(f"Удалено приветственное сообщение {message_id} в чате {chat_id}")
        
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")


# Обработчик ответов новых участников (для статистики)

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def track_new_member_response(message: Message):
    """Отслеживание ответов новых участников для статистики"""
    
    try:
        # Проверяем, что пользователь недавно присоединился
        # (в течение последних 24 часов по истории приветствий)
        
        # Получаем историю приветствий
        history = await greeting_service.get_greeting_history(message.chat.id, 50)
        
        # Ищем запись о приветствии этого пользователя за последние 24 часа
        from datetime import datetime, timedelta
        
        recent_cutoff = datetime.now() - timedelta(hours=24)
        
        for entry in history:
            if (entry['user_id'] == message.from_user.id and 
                entry['sent_date'] > recent_cutoff and 
                not entry['user_responded']):
                
                # Отмечаем, что пользователь ответил
                await greeting_service.mark_user_responded(
                    chat_id=message.chat.id,
                    user_id=message.from_user.id
                )
                
                logger.debug(f"Отмечен ответ пользователя {message.from_user.id} на приветствие")
                break
        
    except Exception as e:
        logger.debug(f"Ошибка отслеживания ответа участника: {e}")


# Обработчик выхода участников (для статистики)

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_NOT_MEMBER))
async def on_member_left(event: ChatMemberUpdated):
    """Обработчик выхода участника"""
    
    try:
        left_member = event.old_chat_member.user
        chat = event.chat
        
        # Пропускаем ботов
        if left_member.is_bot:
            return
        
        logger.debug(f"Участник {left_member.id} покинул чат {chat.id}")
        
        # Здесь можно добавить дополнительную логику, например:
        # - Обновление статистики удержания участников
        # - Анализ эффективности приветствий
        
    except Exception as e:
        logger.error(f"Ошибка обработки выхода участника: {e}")


# Обработчик изменений статуса участников

@router.chat_member()
async def on_chat_member_updated(event: ChatMemberUpdated):
    """Общий обработчик изменений статуса участников чата"""
    
    try:
        # Логируем изменения для отладки
        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status
        user = event.new_chat_member.user
        
        logger.debug(f"Статус участника {user.id} изменен с '{old_status}' на '{new_status}' в чате {event.chat.id}")
        
        # Дополнительная логика обработки изменений статуса
        # например, для отслеживания повышений до админов и т.д.
        
    except Exception as e:
        logger.debug(f"Ошибка обработки изменения статуса участника: {e}")


# Обработчик добавления бота в группу

@router.message(F.new_chat_members)
async def on_bot_added_to_group(message: Message):
    """Обработчик добавления бота в новую группу"""
    
    try:
        # Проверяем, добавили ли нашего бота
        bot_user = await message.bot.get_me()
        
        for new_member in message.new_chat_members:
            if new_member.id == bot_user.id:
                # Бот добавлен в новую группу
                logger.info(f"Бот добавлен в группу {message.chat.id} ({message.chat.title})")
                
                # Инициализируем настройки приветствий для новой группы
                await greeting_service.get_greeting_settings(message.chat.id)
                
                # Отправляем приветственное сообщение о возможностях бота
                welcome_text = """🤖 **Привет! Я добавлен в вашу группу!**

**Система приветствий:**
• `/greeting` - настроить приветствия для новых участников
• `/greeting_on` - включить приветствия  
• `/greeting_off` - выключить приветствия

**Другие возможности:**
• Система достижений
• Привязка игровых профилей
• Управление кланами
• И многое другое!

Используйте `/help` для просмотра всех команд."""
                
                await message.reply(welcome_text, parse_mode="Markdown")
                break
        
    except Exception as e:
        logger.error(f"Ошибка обработки добавления бота в группу: {e}")


# Вспомогательная функция для форматирования участников

def format_user_info(user) -> str:
    """Форматирование информации о пользователе"""
    
    name_parts = []
    
    if user.first_name:
        name_parts.append(user.first_name)
    
    if user.last_name:
        name_parts.append(user.last_name)
    
    full_name = " ".join(name_parts) if name_parts else "Пользователь"
    
    if user.username:
        return f"{full_name} (@{user.username})"
    else:
        return f"{full_name} (ID: {user.id})"


# Обработчик массовых изменений участников

@router.message(F.left_chat_member)
async def on_member_left_legacy(message: Message):
    """Обработчик выхода участника (legacy метод)"""
    
    try:
        left_member = message.left_chat_member
        
        if left_member and not left_member.is_bot:
            logger.debug(f"Участник {format_user_info(left_member)} покинул чат {message.chat.id}")
    
    except Exception as e:
        logger.debug(f"Ошибка legacy обработчика выхода: {e}")


# Периодическая задача очистки старых записей

async def cleanup_old_greeting_history():
    """Периодическая очистка старых записей приветствий"""
    
    while True:
        try:
            # Ждем сутки
            await asyncio.sleep(24 * 60 * 60)
            
            # Здесь можно добавить логику очистки старых записей
            # например, записей старше 90 дней
            
            logger.info("Выполнена периодическая очистка истории приветствий")
            
        except Exception as e:
            logger.error(f"Ошибка периодической очистки: {e}")
            await asyncio.sleep(60)  # Ждем минуту перед повтором