"""
Обработчики команд бота
"""
from aiogram import Router

# Прямые импорты для обратной совместимости с bot/main.py
from .greeting_commands import router as greeting_router
from .greeting_events import router as greeting_events_router
from .extended_clash_commands import extended_router
from .clan_commands import clan_router
from .passport_commands import passport_router
from .player_binding_commands import router as binding_router
from .admin_binding_commands import router as admin_binding_router
from .achievement_commands import router as achievement_router
from .contextual_commands import router as contextual_router
from .advanced_contextual_commands import router as advanced_contextual_router


def get_routers() -> list[Router]:
    """
    Получение всех роутеров (для тестов и альтернативной инициализации)
    
    Returns:
        list[Router]: Список роутеров для регистрации
    """
    return [
        greeting_router,
        greeting_events_router,
        clan_router,
        extended_router,
        passport_router,
        binding_router,
        admin_binding_router,
        achievement_router,
        contextual_router,
        advanced_contextual_router
    ]


__all__ = [
    "greeting_router",
    "greeting_events_router",
    "extended_router",
    "clan_router",
    "passport_router",
    "binding_router",
    "admin_binding_router",
    "achievement_router",
    "contextual_router",
    "advanced_contextual_router",
    "get_routers"
]
