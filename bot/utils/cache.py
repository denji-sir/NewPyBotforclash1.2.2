"""
Простой менеджер кэша для временного хранения данных
"""
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta


class CacheManager:
    """Менеджер кэша с поддержкой TTL"""
    
    def __init__(self, default_ttl: int = 300):
        """
        Args:
            default_ttl: Время жизни кэша по умолчанию в секундах (5 минут)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Сохранить значение в кэш
        
        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl: Время жизни в секундах (если None, используется default_ttl)
        """
        expiry_time = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._cache[key] = {
            'value': value,
            'expiry': expiry_time
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение из кэша
        
        Args:
            key: Ключ кэша
            default: Значение по умолчанию, если ключ не найден или истек
            
        Returns:
            Значение из кэша или default
        """
        if key not in self._cache:
            return default
        
        cache_entry = self._cache[key]
        
        # Проверяем, не истек ли кэш
        if time.time() > cache_entry['expiry']:
            del self._cache[key]
            return default
        
        return cache_entry['value']
    
    def delete(self, key: str) -> bool:
        """
        Удалить значение из кэша
        
        Args:
            key: Ключ кэша
            
        Returns:
            True если ключ был удален, False если не найден
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Очистить весь кэш"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Удалить все истекшие записи
        
        Returns:
            Количество удаленных записей
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time > entry['expiry']
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    def has(self, key: str) -> bool:
        """
        Проверить наличие ключа в кэше
        
        Args:
            key: Ключ кэша
            
        Returns:
            True если ключ существует и не истек
        """
        if key not in self._cache:
            return False
        
        if time.time() > self._cache[key]['expiry']:
            del self._cache[key]
            return False
        
        return True
    
    def size(self) -> int:
        """
        Получить количество записей в кэше
        
        Returns:
            Количество активных записей
        """
        self.cleanup_expired()
        return len(self._cache)
