"""
Универсальный обработчик ошибок для команд бота
"""
import logging
import traceback
from functools import wraps
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


def error_handler(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в командах бота
    Показывает пользователю понятное сообщение об ошибке
    И логирует детальную информацию для отладки
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Находим message или callback в аргументах
        message = None
        callback = None
        
        for arg in args:
            if isinstance(arg, Message):
                message = arg
                break
            elif isinstance(arg, CallbackQuery):
                callback = arg
                message = callback.message
                break
        
        try:
            return await func(*args, **kwargs)
            
        except Exception as e:
            # Формируем детальное сообщение об ошибке
            error_type = type(e).__name__
            error_message = str(e)
            command_name = func.__name__
            
            # Логируем полную информацию
            logger.error(
                f"\n{'='*60}\n"
                f"❌ ОШИБКА В КОМАНДЕ: {command_name}\n"
                f"{'='*60}\n"
                f"Тип ошибки: {error_type}\n"
                f"Сообщение: {error_message}\n"
                f"Traceback:\n{traceback.format_exc()}\n"
                f"{'='*60}"
            )
            
            # Отправляем пользователю понятное сообщение
            error_text = (
                f"❌ **Ошибка выполнения команды**\n\n"
                f"**Команда:** `{command_name}`\n"
                f"**Тип ошибки:** `{error_type}`\n"
                f"**Описание:** {error_message}\n\n"
                f"📝 Детальная информация записана в лог.\n"
                f"🔧 Обратитесь к администратору бота."
            )
            
            try:
                if callback:
                    await callback.answer(f"❌ Ошибка: {error_type}", show_alert=True)
                    if message:
                        await message.reply(error_text, parse_mode="Markdown")
                elif message:
                    await message.reply(error_text, parse_mode="Markdown")
            except Exception as send_error:
                logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")
    
    return wrapper


def command_error_handler(command_name: str = None):
    """
    Декоратор с параметрами для обработки ошибок
    
    Args:
        command_name: Имя команды для отображения
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Находим message или callback
            message = None
            callback = None
            
            for arg in args:
                if isinstance(arg, Message):
                    message = arg
                    break
                elif isinstance(arg, CallbackQuery):
                    callback = arg
                    message = callback.message
                    break
            
            try:
                return await func(*args, **kwargs)
                
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                func_name = command_name or func.__name__
                
                # Логируем с цветами для терминала
                logger.error(
                    f"\n\033[91m{'='*60}\033[0m\n"
                    f"\033[91m❌ ОШИБКА В КОМАНДЕ: {func_name}\033[0m\n"
                    f"\033[91m{'='*60}\033[0m\n"
                    f"\033[93mТип ошибки:\033[0m {error_type}\n"
                    f"\033[93mСообщение:\033[0m {error_message}\n"
                    f"\033[93mФункция:\033[0m {func.__name__}\n"
                    f"\033[93mАргументы:\033[0m {args}\n"
                    f"\n\033[94mТрассировка:\033[0m\n{traceback.format_exc()}\n"
                    f"\033[91m{'='*60}\033[0m"
                )
                
                # Сообщение пользователю
                user_text = (
                    f"❌ **Ошибка: `{func_name}`**\n\n"
                    f"**Тип:** `{error_type}`\n"
                    f"**Причина:** {error_message[:200]}\n\n"
                    f"💡 Проверьте правильность команды и попробуйте снова.\n"
                    f"📋 Детали в логах: `bot.log`"
                )
                
                try:
                    if callback:
                        await callback.answer(f"❌ {error_type}", show_alert=True)
                    if message:
                        await message.reply(user_text, parse_mode="Markdown")
                except:
                    pass
        
        return wrapper
    return decorator
