"""
Ленивые геттеры для сервисов - предотвращение сайд-эффектов при импорте
"""
from functools import lru_cache
import os


def is_testing() -> bool:
    """Проверка режима тестирования"""
    return os.getenv("TESTING") == "1"


@lru_cache
def get_player_binding_service():
    """Ленивое получение PlayerBindingService"""
    from ..services.player_binding_service import PlayerBindingService
    return PlayerBindingService()


@lru_cache
def get_passport_service():
    """Ленивое получение PassportDatabaseService"""
    from ..services.passport_database_service import get_passport_db_service
    return get_passport_db_service()


@lru_cache
def get_clan_service():
    """Ленивое получение ClanDatabaseService"""
    from ..services.clan_database_service import ClanDatabaseService
    return ClanDatabaseService()


@lru_cache
def get_coc_api_service():
    """Ленивое получение CocApiService"""
    from ..services.coc_api_service import get_coc_api_service
    return get_coc_api_service()


@lru_cache
def get_passport_manager():
    """Ленивое получение PassportSystemManager"""
    from ..services.passport_system_manager import PassportSystemManager
    return PassportSystemManager()


@lru_cache
def get_notification_service():
    """Ленивое получение NotificationService"""
    from ..services.notification_service import NotificationService
    return NotificationService()


@lru_cache
def get_greeting_service():
    """Ленивое получение GreetingService"""
    from ..services.greeting_service import GreetingService
    return GreetingService()


@lru_cache
def get_achievement_service():
    """Ленивое получение AchievementService"""
    from ..services.achievement_service import AchievementService
    return AchievementService()


@lru_cache
def get_admin_service():
    """Ленивое получение BindingAdminService"""
    from ..services.binding_admin_service import BindingAdminService
    return BindingAdminService()
