"""
Конфигурация системы кланов
"""
import os
from dataclasses import dataclass
from typing import List, Optional
import logging


@dataclass
class ClanSystemConfig:
    """Конфигурация системы кланов"""
    
    # База данных
    database_path: str = "data/clans.db"
    
    # CoC API
    coc_api_keys: List[str] = None
    coc_api_timeout: int = 30
    coc_api_rate_limit: int = 35
    
    # Лимиты системы
    max_clans_per_chat: int = 10
    max_clan_description_length: int = 200
    
    # Настройки по умолчанию для чатов
    default_admin_only_registration: bool = True
    default_show_clan_numbers: bool = True
    default_auto_detect_clan: bool = True
    
    # Логирование
    enable_operation_logging: bool = True
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Пост-инициализация с валидацией"""
        if not self.coc_api_keys:
            self.coc_api_keys = []
        
        # Проверяем наличие API ключей
        if not self.coc_api_keys:
            # Пытаемся получить из переменных окружения
            env_keys = []
            for i in range(1, 6):  # Поддерживаем до 5 ключей
                key = os.getenv(f'COC_API_KEY_{i}')
                if key:
                    env_keys.append(key)
            
            if env_keys:
                self.coc_api_keys = env_keys
        
        # Валидация параметров
        if self.max_clans_per_chat < 1:
            self.max_clans_per_chat = 1
        elif self.max_clans_per_chat > 50:
            self.max_clans_per_chat = 50
        
        if self.coc_api_rate_limit < 1:
            self.coc_api_rate_limit = 35
        
        if self.coc_api_timeout < 5:
            self.coc_api_timeout = 5
    
    @classmethod
    def from_env(cls) -> 'ClanSystemConfig':
        """Создать конфигурацию из переменных окружения"""
        return cls(
            database_path=os.getenv('CLAN_DB_PATH', 'data/clans.db'),
            coc_api_timeout=int(os.getenv('COC_API_TIMEOUT', '30')),
            coc_api_rate_limit=int(os.getenv('COC_API_RATE_LIMIT', '35')),
            max_clans_per_chat=int(os.getenv('MAX_CLANS_PER_CHAT', '10')),
            max_clan_description_length=int(os.getenv('MAX_CLAN_DESC_LENGTH', '200')),
            default_admin_only_registration=os.getenv('ADMIN_ONLY_REGISTRATION', 'true').lower() == 'true',
            default_show_clan_numbers=os.getenv('SHOW_CLAN_NUMBERS', 'true').lower() == 'true',
            default_auto_detect_clan=os.getenv('AUTO_DETECT_CLAN', 'true').lower() == 'true',
            enable_operation_logging=os.getenv('ENABLE_OP_LOGGING', 'true').lower() == 'true',
            log_level=os.getenv('CLAN_LOG_LEVEL', 'INFO')
        )
    
    def validate(self) -> List[str]:
        """
        Валидация конфигурации
        
        Returns:
            List[str]: Список ошибок (пустой если все в порядке)
        """
        errors = []
        
        if not self.coc_api_keys:
            errors.append("No CoC API keys provided")
        
        if not self.database_path:
            errors.append("Database path is required")
        
        if self.max_clans_per_chat < 1:
            errors.append("max_clans_per_chat must be at least 1")
        
        if self.coc_api_timeout < 5:
            errors.append("coc_api_timeout must be at least 5 seconds")
        
        return errors
    
    def is_valid(self) -> bool:
        """Проверить валидность конфигурации"""
        return len(self.validate()) == 0
    
    def setup_logging(self) -> None:
        """Настроить логирование для системы кланов"""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Настраиваем логгер для модулей кланов
        clan_logger = logging.getLogger('bot.models.clan_models')
        clan_logger.setLevel(log_level)
        
        services_logger = logging.getLogger('bot.services')
        services_logger.setLevel(log_level)
        
        handlers_logger = logging.getLogger('bot.handlers.clan_commands')
        handlers_logger.setLevel(log_level)


# Глобальная конфигурация
_config: Optional[ClanSystemConfig] = None


def get_clan_config() -> ClanSystemConfig:
    """Получить глобальную конфигурацию системы кланов"""
    global _config
    
    if _config is None:
        _config = ClanSystemConfig.from_env()
    
    return _config


def set_clan_config(config: ClanSystemConfig) -> None:
    """Установить глобальную конфигурацию"""
    global _config
    _config = config


def init_clan_config(**kwargs) -> ClanSystemConfig:
    """
    Инициализировать конфигурацию с переданными параметрами
    
    Args:
        **kwargs: Параметры конфигурации
        
    Returns:
        ClanSystemConfig: Инициализированная конфигурация
    """
    config = ClanSystemConfig(**kwargs)
    set_clan_config(config)
    
    # Настраиваем логирование
    config.setup_logging()
    
    return config


# Вспомогательные функции для быстрого доступа к настройкам
def get_coc_api_keys() -> List[str]:
    """Получить ключи CoC API"""
    return get_clan_config().coc_api_keys


def get_database_path() -> str:
    """Получить путь к базе данных"""
    return get_clan_config().database_path


def get_max_clans_per_chat() -> int:
    """Получить максимальное количество кланов на чат"""
    return get_clan_config().max_clans_per_chat


def is_operation_logging_enabled() -> bool:
    """Проверить включено ли логирование операций"""
    return get_clan_config().enable_operation_logging