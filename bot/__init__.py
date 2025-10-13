"""
NewPyBot для Clash of Clans v1.2.2

Telegram бот для мониторинга кланов в Clash of Clans с системой паспортов.
"""

__version__ = "1.2.2"
__author__ = "denji-sir"
__email__ = "your-email@example.com"

# Основные компоненты бота
from .config import load_config
from .services import (
    ClashOfClansAPI,
    DatabaseService, 
    PassportSystem
)

settings = load_config()

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "settings",
    "ClashOfClansAPI",
    "DatabaseService",
    "PassportSystem"
]