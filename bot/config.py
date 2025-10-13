"""
Конфигурация бота
"""

import os
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class BotConfig:
    """Конфигурация бота"""
    
    # Основные настройки бота
    bot_token: str
    
    # Токены Clash of Clans API
    clash_tokens: List[str]
    
    # База данных
    database_url: Optional[str] = None
    
    # Настройки логирования
    log_level: str = "INFO"
    log_file: Optional[str] = "bot.log"
    
    # Настройки кеширования
    cache_ttl: int = 300  # 5 минут
    
    # Администраторы бота
    admin_user_ids: List[int] = None
    
    def __post_init__(self):
        """Валидация конфигурации после инициализации"""
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN обязателен")
        
        if not self.clash_tokens:
            raise ValueError("Необходим хотя бы один CLASH_TOKEN")
        
        if self.admin_user_ids is None:
            self.admin_user_ids = []
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """
        Создать конфигурацию из переменных окружения
        
        Returns:
            BotConfig: Конфигурация бота
        """
        
        # Проверка тестового режима
        is_testing = os.getenv("TESTING") == "1"
        
        # Получаем токен бота
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            if is_testing:
                bot_token = "TEST_TOKEN_123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            else:
                raise ValueError("Переменная окружения BOT_TOKEN не установлена")
        
        # Получаем токены Clash of Clans API
        clash_tokens = []
        
        # Проверяем отдельные токены
        for i in range(1, 11):  # Поддержка до 10 токенов
            token_key = f'CLASH_TOKEN_{i}' if i > 1 else 'CLASH_TOKEN'
            token = os.getenv(token_key)
            if token:
                clash_tokens.append(token)
        
        # Также проверяем список через запятую
        clash_tokens_str = os.getenv('CLASH_TOKENS')
        if clash_tokens_str:
            for token in clash_tokens_str.split(','):
                token = token.strip()
                if token and token not in clash_tokens:
                    clash_tokens.append(token)
        
        if not clash_tokens:
            raise ValueError(
                "Необходимо установить хотя бы один токен Clash API:\n"
                "CLASH_TOKEN или CLASH_TOKENS (через запятую)"
            )
        
        # База данных
        database_url = os.getenv('DATABASE_URL')
        
        # Настройки логирования
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_file = os.getenv('LOG_FILE', 'bot.log')
        
        # Кеширование
        cache_ttl = int(os.getenv('CACHE_TTL', '300'))
        
        # Администраторы
        admin_user_ids = []
        admin_ids_str = os.getenv('ADMIN_USER_IDS')
        if admin_ids_str:
            for user_id in admin_ids_str.split(','):
                try:
                    admin_user_ids.append(int(user_id.strip()))
                except ValueError:
                    pass
        
        return cls(
            bot_token=bot_token,
            clash_tokens=clash_tokens,
            database_url=database_url,
            log_level=log_level,
            log_file=log_file,
            cache_ttl=cache_ttl,
            admin_user_ids=admin_user_ids
        )
    
    @classmethod
    def from_file(cls, config_file: str) -> 'BotConfig':
        """
        Создать конфигурацию из файла .env
        
        Args:
            config_file: Путь к файлу конфигурации
            
        Returns:
            BotConfig: Конфигурация бота
        """
        
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Файл конфигурации не найден: {config_file}")
        
        # Загружаем переменные из файла
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
        
        return cls.from_env()
    
    def validate_tokens(self) -> bool:
        """
        Проверить валидность токенов Clash API
        
        Returns:
            bool: True если все токены валидны
        """
        
        # TODO: Реализовать проверку токенов через API
        return len(self.clash_tokens) > 0
    
    def get_database_config(self) -> dict:
        """
        Получить конфигурацию базы данных
        
        Returns:
            dict: Параметры подключения к БД
        """
        
        if not self.database_url:
            return {}
        
        # Парсим URL базы данных
        if self.database_url.startswith('sqlite:'):
            return {
                'type': 'sqlite',
                'path': self.database_url.replace('sqlite:', '').replace('///', '')
            }
        elif self.database_url.startswith('postgresql:'):
            return {
                'type': 'postgresql',
                'url': self.database_url
            }
        else:
            return {
                'type': 'unknown',
                'url': self.database_url
            }


def load_config() -> BotConfig:
    """
    Загрузить конфигурацию бота
    
    Пытается загрузить конфигурацию в следующем порядке:
    1. Из файла .env (если существует)
    2. Из переменных окружения
    
    Returns:
        BotConfig: Конфигурация бота
    """
    
    # Проверяем наличие файла .env
    env_file = Path('.env')
    if env_file.exists():
        return BotConfig.from_file('.env')
    
    # Загружаем из переменных окружения
    return BotConfig.from_env()


# Создаем пример файла конфигурации
EXAMPLE_ENV_FILE = """# Конфигурация бота Clash of Clans

# Токен Telegram бота (получить у @BotFather)
BOT_TOKEN=your_bot_token_here

# Токены Clash of Clans API (получить на https://developer.clashofclans.com/)
# Можно указать несколько токенов для увеличения лимита запросов
CLASH_TOKEN=your_clash_token_here
# CLASH_TOKEN_2=your_second_clash_token_here
# CLASH_TOKEN_3=your_third_clash_token_here

# Или все токены через запятую
# CLASH_TOKENS=token1,token2,token3

# База данных (опционально)
# Для SQLite (по умолчанию)
# DATABASE_URL=sqlite:///bot_data.db
# Для PostgreSQL
# DATABASE_URL=postgresql://user:password@localhost:5432/database

# Настройки логирования
LOG_LEVEL=INFO
LOG_FILE=bot.log

# Время кеширования в секундах (по умолчанию 300 = 5 минут)
CACHE_TTL=300

# ID администраторов бота (через запятую)
# ADMIN_USER_IDS=123456789,987654321
"""


def create_example_env_file():
    """Создать пример файла .env"""
    
    env_path = Path('.env.example')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(EXAMPLE_ENV_FILE)
    
    print(f"Создан пример конфигурации: {env_path}")
    print("Скопируйте его в .env и заполните свои данные")


if __name__ == "__main__":
    # Создаем пример файла конфигурации
    create_example_env_file()