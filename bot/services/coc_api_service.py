"""
Сервис для работы с Clash of Clans API
"""
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import logging
from ..models.clan_models import ClanData, ClanNotFound, ApiError, ApiRateLimited

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """Асинхронный лимитер запросов"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # Убираем старые запросы
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            # Ждем если достигнут лимит
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    return await self.__aenter__()
            
            # Добавляем текущий запрос
            self.requests.append(now)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class CocApiService:
    """Сервис для работы с Clash of Clans API"""
    
    BASE_URL = "https://api.clashofclans.com/v1"
    
    def __init__(self, api_keys: List[str]):
        if not api_keys:
            raise ValueError("At least one API key is required")
        
        self.api_keys = api_keys
        self.current_key_index = 0
        self.rate_limiter = AsyncRateLimiter(35, 1)  # 35 запросов в секунду
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def _ensure_session(self):
        """Обеспечить наличие HTTP сессии"""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"Accept": "application/json"}
            )
    
    def _get_current_api_key(self) -> str:
        """Получить текущий API ключ"""
        return self.api_keys[self.current_key_index]
    
    async def _rotate_api_key(self):
        """Ротация API ключей при превышении лимита"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Rotated to API key index: {self.current_key_index}")
    
    def _normalize_clan_tag(self, clan_tag: str) -> str:
        """Нормализация тега клана для API"""
        # Убираем # если есть
        tag = clan_tag.replace('#', '').upper()
        
        # Добавляем %23 для URL encoding
        return f"%23{tag}"
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполнить запрос к CoC API"""
        await self._ensure_session()
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._get_current_api_key()}",
            "Accept": "application/json"
        }
        
        max_retries = len(self.api_keys)
        
        for attempt in range(max_retries):
            try:
                async with self.rate_limiter:
                    async with self._session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            raise ClanNotFound("Clan not found")
                        elif response.status == 429:
                            logger.warning(f"Rate limited on key {self.current_key_index}")
                            await self._rotate_api_key()
                            headers["Authorization"] = f"Bearer {self._get_current_api_key()}"
                            await asyncio.sleep(2)  # Небольшая пауза
                            continue
                        else:
                            error_text = await response.text()
                            raise ApiError(f"API error {response.status}: {error_text}")
            
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise ApiError(f"Network error: {e}")
                await asyncio.sleep(1)
        
        raise ApiError("All API keys exhausted")
    
    async def get_clan(self, clan_tag: str) -> ClanData:
        """
        Получить информацию о клане
        
        Args:
            clan_tag: Тег клана (с # или без)
        
        Returns:
            ClanData: Информация о клане
        
        Raises:
            ClanNotFound: Клан не найден
            ApiError: Ошибка API
        """
        try:
            normalized_tag = self._normalize_clan_tag(clan_tag)
            endpoint = f"/clans/{normalized_tag}"
            
            logger.debug(f"Getting clan info for {clan_tag}")
            
            data = await self._make_request(endpoint)
            clan_data = ClanData.from_api_response(data)
            
            logger.info(f"Successfully got clan info: {clan_data.name} ({clan_data.tag})")
            return clan_data
            
        except ClanNotFound:
            logger.warning(f"Clan {clan_tag} not found")
            raise
        except Exception as e:
            logger.error(f"Error getting clan {clan_tag}: {e}")
            raise ApiError(f"Failed to get clan info: {e}")
    
    async def get_clan_members(self, clan_tag: str) -> List[Dict[str, Any]]:
        """
        Получить список участников клана
        
        Args:
            clan_tag: Тег клана
        
        Returns:
            List[Dict]: Список участников клана
        """
        try:
            normalized_tag = self._normalize_clan_tag(clan_tag)
            endpoint = f"/clans/{normalized_tag}/members"
            
            logger.debug(f"Getting clan members for {clan_tag}")
            
            data = await self._make_request(endpoint)
            members = data.get('items', [])
            
            logger.info(f"Got {len(members)} members for clan {clan_tag}")
            return members
            
        except Exception as e:
            logger.error(f"Error getting clan members {clan_tag}: {e}")
            raise ApiError(f"Failed to get clan members: {e}")
    
    async def verify_clan_exists(self, clan_tag: str) -> bool:
        """
        Проверить существует ли клан (быстрая проверка)
        
        Args:
            clan_tag: Тег клана
        
        Returns:
            bool: True если клан существует
        """
        try:
            await self.get_clan(clan_tag)
            return True
        except ClanNotFound:
            return False
        except ApiError:
            # При ошибке API считаем что клан может существовать
            return True
    
    async def get_api_status(self) -> Dict[str, Any]:
        """Получить статус API"""
        try:
            # Простой запрос для проверки работоспособности
            await self._make_request("/locations")
            return {
                'status': 'online',
                'current_key_index': self.current_key_index,
                'total_keys': len(self.api_keys)
            }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e),
                'current_key_index': self.current_key_index,
                'total_keys': len(self.api_keys)
            }


# Singleton instance
_coc_api_service: Optional[CocApiService] = None


def init_coc_api_service(api_keys: List[str]) -> CocApiService:
    """Инициализировать глобальный сервис CoC API"""
    global _coc_api_service
    _coc_api_service = CocApiService(api_keys)
    return _coc_api_service


def get_coc_api_service() -> CocApiService:
    """Получить глобальный сервис CoC API"""
    if _coc_api_service is None:
        raise RuntimeError("CoC API service not initialized. Call init_coc_api_service() first.")
    return _coc_api_service