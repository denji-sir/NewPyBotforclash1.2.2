"""
Утилиты для обработки ошибок при обращении к внешним API.
"""
from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Callable, Type, TypeVar, Awaitable

import aiohttp

ReturnType = TypeVar("ReturnType")


def api_request_handler(
    logger: logging.Logger,
    error_cls: Type[Exception],
    *,
    base_message: str = "Не удалось выполнить запрос к внешнему API"
) -> Callable[[Callable[..., Awaitable[ReturnType]]], Callable[..., Awaitable[ReturnType]]]:
    """
    Декоратор для унифицированной обработки ошибок запросов к внешним API.

    Args:
        logger: Экземпляр логгера для записи ошибок.
        error_cls: Тип исключения, которое необходимо пробрасывать наверх.
        base_message: Базовое сообщение, которое будет добавлено к деталям ошибки.

    Returns:
        Callable: Декоратор, оборачивающий асинхронную функцию.
    """

    def decorator(func: Callable[..., Awaitable[ReturnType]]) -> Callable[..., Awaitable[ReturnType]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> ReturnType:
            try:
                return await func(*args, **kwargs)
            except error_cls:
                # Уже нормализованное исключение, пробрасываем дальше
                raise
            except asyncio.CancelledError:
                # Позволяем корректно завершать задачи
                raise
            except asyncio.TimeoutError as exc:
                message = f"{base_message}. Причина: превышено время ожидания ответа."
                logger.error(f"{message} (метод {func.__name__})", exc_info=True)
                raise error_cls(message) from exc
            except aiohttp.ClientConnectorError as exc:
                message = f"{base_message}. Причина: ошибка соединения."
                logger.error(f"{message} (метод {func.__name__})", exc_info=True)
                raise error_cls(message) from exc
            except aiohttp.ClientPayloadError as exc:
                message = f"{base_message}. Причина: некорректный ответ сервера."
                logger.error(f"{message} (метод {func.__name__})", exc_info=True)
                raise error_cls(message) from exc
            except aiohttp.ClientError as exc:
                message = f"{base_message}. Причина: ошибка HTTP-клиента."
                logger.error(f"{message} (метод {func.__name__}): {exc}", exc_info=True)
                raise error_cls(message) from exc

        return wrapper

    return decorator
