"""
Пакет сервисов для бота.

Этот пакет объединяет различные сервисы, используемые в боте, 
и предоставляет удобный интерфейс для их инициализации и доступа.

Доступные сервисы:
- ClashOfClansAPI: Расширенный клиент для работы с Clash of Clans API.
- DatabaseService: Сервис для взаимодействия с базой данных.
- PassportSystem: Система для управления паспортами игроков.
- NotificationService: Сервис для отправки уведомлений.

Пример использования:

from bot.services import ClashOfClansAPI, DatabaseService

api = ClashOfClansAPI()
db = DatabaseService()

"""

from .extended_clash_api import ExtendedClashAPI as ClashOfClansAPI
from .clan_database_service import ClanDatabaseService as DatabaseService
from .passport_system_manager import PassportSystemManager as PassportSystem
# from .system_services import NotificationService

__all__ = [
    "ClashOfClansAPI",
    "DatabaseService",
    "PassportSystem",
]