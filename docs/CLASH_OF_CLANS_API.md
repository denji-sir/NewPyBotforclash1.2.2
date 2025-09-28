# Clash of Clans API - Полная документация

## 📋 Оглавление

1. [Введение](#введение)
2. [Аутентификация](#аутентификация)
3. [Базовые URL и конфигурация](#базовые-url-и-конфигурация)
4. [Rate Limits](#rate-limits)
5. [Endpoints](#endpoints)
6. [Модели данных](#модели-данных)
7. [Система паспортов](#система-паспортов)
8. [Примеры использования](#примеры-использования)
9. [Обработка ошибок](#обработка-ошибок)
10. [Best Practices](#best-practices)

---

## 🔐 Введение

Clash of Clans API предоставляет доступ к данным игры, включая информацию о кланах, игроках, войнах, лигах и локациях. API использует REST архитектуру и возвращает данные в формате JSON.

### Официальные ресурсы

- **Официальный сайт**: https://developer.clashofclans.com/
- **Discord сервер**: https://discord.gg/clashapi
- **Документация**: https://developer.clashofclans.com/#/documentation

---

## 🔑 Аутентификация

### Получение токена

1. Зарегистрируйтесь на https://developer.clashofclans.com/
2. Создайте новый ключ API
3. Укажите ваш IP адрес (для development можно использовать wildcard)
4. Получите токен API

### Использование токена

Токен должен передаваться в заголовке `Authorization`:

```http
Authorization: Bearer YOUR_API_TOKEN
```

### Конфигурация в Python

```python
import aiohttp
import asyncio

class ClashAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.clashofclans.com/v1"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
```

---

## 🌐 Базовые URL и конфигурация

### Base URL
```
https://api.clashofclans.com/v1
```

### Основные заголовки

```http
Authorization: Bearer YOUR_API_TOKEN
Accept: application/json
Content-Type: application/json
```

---

## ⏱️ Rate Limits

### Лимиты запросов

- **1000 запросов в секунду** на токен
- **30 000 запросов в час** на токен
- **1 000 000 запросов в месяц** на токен

### Заголовки ответа

```http
X-Ratelimit-Limit: 1000
X-Ratelimit-Remaining: 999
X-Ratelimit-Reset: 1640995200
```

### Обработка rate limits

```python
import asyncio
from datetime import datetime

class RateLimiter:
    def __init__(self, requests_per_second: int = 10):
        self.requests_per_second = requests_per_second
        self.requests = []
    
    async def wait_if_needed(self):
        now = datetime.now()
        # Удаляем запросы старше секунды
        self.requests = [req for req in self.requests if (now - req).seconds < 1]
        
        if len(self.requests) >= self.requests_per_second:
            sleep_time = 1 - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)
```

---

## 🔗 Endpoints

### 1. Clans (Кланы)

#### GET /clans
Поиск кланов по различным критериям

**Параметры:**
- `name` (string) - Название клана
- `warFrequency` (string) - Частота войн: `always`, `moreThanOncePerWeek`, `oncePerWeek`, `lessThanOncePerWeek`, `never`, `unknown`
- `locationId` (integer) - ID локации
- `minMembers` (integer) - Минимальное количество участников (1-50)
- `maxMembers` (integer) - Максимальное количество участников (1-50)
- `minClanPoints` (integer) - Минимальные очки клана
- `minClanLevel` (integer) - Минимальный уровень клана
- `limit` (integer) - Количество результатов (1-50, по умолчанию 10)
- `after` (string) - Курсор для пагинации
- `before` (string) - Курсор для пагинации

**Пример запроса:**
```http
GET /v1/clans?name=dragons&minMembers=25&limit=10
```

#### GET /clans/{clanTag}
Получить информацию о конкретном клане

**Параметры:**
- `clanTag` (string) - Тег клана (включая #)

**Пример запроса:**
```http
GET /v1/clans/%23YU88VQJ2
```

#### GET /clans/{clanTag}/members
Получить список участников клана

**Параметры:**
- `clanTag` (string) - Тег клана
- `limit` (integer) - Количество результатов (1-50)
- `after` (string) - Курсор для пагинации
- `before` (string) - Курсор для пагинации

#### GET /clans/{clanTag}/warlog
Получить журнал войн клана

**Параметры:**
- `clanTag` (string) - Тег клана
- `limit` (integer) - Количество результатов (1-50)
- `after` (string) - Курсор для пагинации
- `before` (string) - Курсор для пагинации

#### GET /clans/{clanTag}/currentwar
Получить текущую войну клана

**Параметры:**
- `clanTag` (string) - Тег клана

### 2. Players (Игроки)

#### GET /players/{playerTag}
Получить информацию об игроке

**Параметры:**
- `playerTag` (string) - Тег игрока (включая #)

**Пример запроса:**
```http
GET /v1/players/%23YU88VQJ2C
```

### 3. Leagues (Лиги)

#### GET /leagues
Получить список всех лиг

**Параметры:**
- `limit` (integer) - Количество результатов (1-50)
- `after` (string) - Курсор для пагинации
- `before` (string) - Курсор для пагинации

#### GET /leagues/{leagueId}
Получить информацию о конкретной лиге

#### GET /leagues/{leagueId}/seasons
Получить сезоны лиги

#### GET /leagues/{leagueId}/seasons/{seasonId}
Получить топ игроков сезона

### 4. Locations (Локации)

#### GET /locations
Получить список всех локаций

#### GET /locations/{locationId}
Получить информацию о конкретной локации

#### GET /locations/{locationId}/rankings/clans
Топ кланов по локации

#### GET /locations/{locationId}/rankings/players
Топ игроков по локации

#### GET /locations/{locationId}/rankings/versus
Топ игроков Builder Base по локации

### 5. Goldpass (Золотой пропуск)

#### GET /goldpass/seasons/current
Получить информацию о текущем сезоне золотого пропуска

---

## 📊 Модели данных

### Clan (Клан)

```json
{
  "tag": "#YU88VQJ2",
  "name": "Dragons Eight",
  "type": "inviteOnly",
  "description": "Welcome to Dragons Eight!",
  "location": {
    "id": 32000000,
    "name": "International",
    "isCountry": false,
    "countryCode": "XX"
  },
  "badgeUrls": {
    "small": "https://api-assets.clashofclans.com/badges/70/...",
    "large": "https://api-assets.clashofclans.com/badges/512/...",
    "medium": "https://api-assets.clashofclans.com/badges/200/..."
  },
  "clanLevel": 15,
  "clanPoints": 45000,
  "clanVersusPoints": 25000,
  "requiredTrophies": 2600,
  "warFrequency": "always",
  "warWinStreak": 5,
  "warWins": 150,
  "warTies": 0,
  "warLosses": 25,
  "isWarLogPublic": true,
  "warLeague": {
    "id": 48000015,
    "name": "Champion League I"
  },
  "members": 50,
  "memberList": [...],
  "labels": [...],
  "chatLanguage": {
    "id": 75000000,
    "name": "English",
    "languageCode": "EN"
  }
}
```

### Player (Игрок)

```json
{
  "tag": "#YU88VQJ2C",
  "name": "Player Name",
  "townHallLevel": 14,
  "townHallWeaponLevel": 3,
  "expLevel": 200,
  "trophies": 4500,
  "bestTrophies": 5000,
  "warStars": 500,
  "attackWins": 1200,
  "defenseWins": 800,
  "builderHallLevel": 9,
  "versusTrophies": 3500,
  "bestVersusTrophies": 4000,
  "versusBattleWins": 300,
  "role": "leader",
  "donations": 2500,
  "donationsReceived": 1800,
  "clan": {
    "tag": "#YU88VQJ2",
    "name": "Dragons Eight",
    "clanLevel": 15,
    "badgeUrls": {...}
  },
  "league": {
    "id": 29000015,
    "name": "Champions League III",
    "iconUrls": {...}
  },
  "achievements": [...],
  "versusBattleWinCount": 300,
  "labels": [...],
  "troops": [...],
  "heroes": [...],
  "spells": [...]
}
```

### War (Война)

```json
{
  "state": "inWar",
  "teamSize": 50,
  "attacksPerMember": 2,
  "preparationStartTime": "20231201T080000.000Z",
  "startTime": "20231202T080000.000Z",
  "endTime": "20231203T080000.000Z",
  "clan": {
    "tag": "#YU88VQJ2",
    "name": "Dragons Eight",
    "badgeUrls": {...},
    "clanLevel": 15,
    "attacks": 85,
    "stars": 145,
    "destructionPercentage": 95.5,
    "members": [...]
  },
  "opponent": {
    "tag": "#OPPONENT",
    "name": "Enemy Clan",
    "badgeUrls": {...},
    "clanLevel": 12,
    "attacks": 80,
    "stars": 120,
    "destructionPercentage": 88.2,
    "members": [...]
  }
}
```

### WarMember (Участник войны)

```json
{
  "tag": "#YU88VQJ2C",
  "name": "Player Name",
  "townhallLevel": 14,
  "mapPosition": 1,
  "attacks": [
    {
      "order": 1,
      "attackerTag": "#YU88VQJ2C",
      "defenderTag": "#DEFENDER",
      "stars": 3,
      "destructionPercentage": 100,
      "duration": 180
    }
  ],
  "opponentAttacks": 2,
  "bestOpponentAttack": {
    "order": 15,
    "attackerTag": "#ATTACKER",
    "defenderTag": "#YU88VQJ2C",
    "stars": 2,
    "destructionPercentage": 85,
    "duration": 210
  }
}
```

---

## � Система паспортов

### Описание системы

Система паспортов предназначена для привязки игровых аккаунтов Clash of Clans к аккаунтам Telegram, что позволяет верифицировать игроков и предоставлять им расширенную функциональность бота.

### Основные возможности

#### 1. Привязка игровых аккаунтов к Telegram

Пользователи могут привязать свои игровые аккаунты к Telegram профилю через специальную процедуру верификации:

```python
@dataclass
class UserPassport:
    user_id: int  # Telegram User ID
    player_tag: str  # Игровой тег в Clash of Clans
    verified_at: datetime  # Время верификации
    verification_method: str  # Метод верификации ('api_token', 'manual', 'clan_verification')
    is_active: bool = True  # Активность паспорта
    verified_by: Optional[int] = None  # ID админа, который верифицировал (для manual)
    clan_tag: Optional[str] = None  # Тег клана на момент верификации

class PassportSystem:
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def create_passport(
        self, 
        user_id: int, 
        player_tag: str, 
        method: str = 'api_token'
    ) -> UserPassport:
        """Создать новый паспорт пользователя"""
        # Проверка существования игрока через API
        player_data = await self.verify_player_exists(player_tag)
        if not player_data:
            raise ValueError("Игрок не найден")
        
        # Проверка уникальности привязки
        existing = await self.get_passport_by_player_tag(player_tag)
        if existing and existing.is_active:
            raise ValueError("Этот аккаунт уже привязан к другому пользователю")
        
        passport = UserPassport(
            user_id=user_id,
            player_tag=player_tag,
            verified_at=datetime.now(),
            verification_method=method,
            clan_tag=player_data.get('clan', {}).get('tag') if player_data.get('clan') else None
        )
        
        await self.save_passport(passport)
        return passport
```

#### 2. Верифицированные игроки в интерфейсе

Верифицированные пользователи отображаются в боте с особыми визуальными индикаторами:

```python
def format_player_name(player_name: str, is_verified: bool) -> str:
    """Форматировать имя игрока с учетом верификации"""
    if is_verified:
        return f"**{player_name}** ✅"  # Жирный шрифт + галочка
    return player_name

def format_clan_member_list(members_data: List[Dict], verified_players: Set[str]) -> str:
    """Форматировать список участников клана"""
    formatted_members = []
    
    for member in members_data:
        player_tag = member['tag']
        player_name = member['name']
        role = member['role']
        trophies = member['trophies']
        
        # Проверка верификации
        is_verified = player_tag in verified_players
        formatted_name = format_player_name(player_name, is_verified)
        
        member_line = f"{formatted_name} | {role} | 🏆 {trophies:,}"
        formatted_members.append(member_line)
    
    return "\n".join(formatted_members)

# Пример использования в Telegram боте
async def show_clan_info(clan_tag: str, chat_id: int):
    """Показать информацию о клане с выделением верифицированных игроков"""
    clan_data = await api.get_clan(clan_tag)
    members_data = await api.get_clan_members(clan_tag)
    
    # Получить список верифицированных игроков в клане
    verified_players = await passport_system.get_verified_players_in_clan(clan_tag)
    
    message = f"🏰 **{clan_data['name']}** (#{clan_data['tag'][1:]})\n"
    message += f"📈 Уровень клана: {clan_data['clanLevel']}\n"
    message += f"👥 Участников: {clan_data['members']}/50\n"
    message += f"🏆 Очки клана: {clan_data['clanPoints']:,}\n\n"
    
    message += "👥 **Участники:**\n"
    message += format_clan_member_list(members_data['items'], verified_players)
    
    await bot.send_message(chat_id, message, parse_mode='Markdown')
```

#### 3. Расширенная статистика для владельцев паспортов

Пользователи с привязанными аккаунтами получают доступ к дополнительной статистике:

```python
class ExtendedStats:
    def __init__(self, passport_system: PassportSystem, api: ClashOfClansAPI):
        self.passports = passport_system
        self.api = api
    
    async def get_personal_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить персональную статистику пользователя"""
        passport = await self.passports.get_passport_by_user_id(user_id)
        if not passport:
            raise ValueError("Аккаунт не привязан")
        
        player_data = await self.api.get_player(passport.player_tag)
        
        # Базовая статистика
        stats = {
            'player_info': {
                'name': player_data['name'],
                'tag': player_data['tag'],
                'town_hall': player_data['townHallLevel'],
                'exp_level': player_data['expLevel'],
                'trophies': player_data['trophies'],
                'best_trophies': player_data['bestTrophies']
            },
            'war_stats': {
                'war_stars': player_data['warStars'],
                'attack_wins': player_data['attackWins'],
                'defense_wins': player_data['defenseWins']
            },
            'donation_stats': {
                'donations': player_data['donations'],
                'donations_received': player_data['donationsReceived']
            }
        }
        
        # Расширенная статистика для верифицированных пользователей
        if passport.is_active:
            stats['extended'] = await self._get_extended_stats(passport.player_tag)
        
        return stats
    
    async def _get_extended_stats(self, player_tag: str) -> Dict[str, Any]:
        """Получить расширенную статистику"""
        # История донатов за последние 30 дней
        donation_history = await self._get_donation_history(player_tag, days=30)
        
        # Статистика по войнам клана
        war_participation = await self._get_war_participation(player_tag)
        
        # Позиции в различных топах
        rankings = await self._get_player_rankings(player_tag)
        
        return {
            'donation_history': donation_history,
            'war_participation': war_participation,
            'rankings': rankings,
            'achievements_progress': await self._get_achievements_progress(player_tag)
        }
    
    async def _get_player_rankings(self, player_tag: str) -> Dict[str, Any]:
        """Получить позиции игрока в различных топах"""
        player_data = await self.api.get_player(player_tag)
        
        rankings = {}
        
        if player_data.get('clan'):
            clan_tag = player_data['clan']['tag']
            clan_members = await self.api.get_clan_members(clan_tag)
            
            # Позиция по донатам в клане
            members_by_donations = sorted(
                clan_members['items'],
                key=lambda x: x['donations'],
                reverse=True
            )
            
            for i, member in enumerate(members_by_donations, 1):
                if member['tag'] == player_tag:
                    rankings['clan_donations_rank'] = i
                    rankings['clan_donations_total'] = len(members_by_donations)
                    break
            
            # Позиция по кубкам в клане
            members_by_trophies = sorted(
                clan_members['items'],
                key=lambda x: x['trophies'],
                reverse=True
            )
            
            for i, member in enumerate(members_by_trophies, 1):
                if member['tag'] == player_tag:
                    rankings['clan_trophies_rank'] = i
                    rankings['clan_trophies_total'] = len(members_by_trophies)
                    break
        
        return rankings
```

#### 4. Система топов и рейтингов

```python
class PlayerRankings:
    def __init__(self, db_connection, api: ClashOfClansAPI):
        self.db = db_connection
        self.api = api
    
    async def get_clan_top_donors(self, clan_tag: str, limit: int = 10) -> List[Dict]:
        """Топ донатеров клана с выделением верифицированных"""
        members_data = await self.api.get_clan_members(clan_tag)
        verified_players = await self.passports.get_verified_players_in_clan(clan_tag)
        
        # Сортировка по донатам
        sorted_members = sorted(
            members_data['items'],
            key=lambda x: x['donations'],
            reverse=True
        )[:limit]
        
        result = []
        for i, member in enumerate(sorted_members, 1):
            player_info = {
                'rank': i,
                'name': member['name'],
                'tag': member['tag'],
                'donations': member['donations'],
                'is_verified': member['tag'] in verified_players,
                'role': member['role']
            }
            result.append(player_info)
        
        return result
    
    async def get_global_verified_top(
        self, 
        category: str = 'trophies', 
        limit: int = 50
    ) -> List[Dict]:
        """Глобальный топ среди всех верифицированных игроков"""
        verified_players = await self.passports.get_all_verified_players()
        
        players_stats = []
        for passport in verified_players:
            try:
                player_data = await self.api.get_player(passport.player_tag)
                stat_value = self._get_stat_value(player_data, category)
                
                players_stats.append({
                    'passport': passport,
                    'player_data': player_data,
                    'stat_value': stat_value
                })
            except Exception as e:
                print(f"Ошибка получения данных для {passport.player_tag}: {e}")
                continue
        
        # Сортировка по выбранной категории
        sorted_players = sorted(
            players_stats,
            key=lambda x: x['stat_value'],
            reverse=True
        )[:limit]
        
        result = []
        for i, player_stat in enumerate(sorted_players, 1):
            result.append({
                'rank': i,
                'name': player_stat['player_data']['name'],
                'tag': player_stat['player_data']['tag'],
                'stat_value': player_stat['stat_value'],
                'telegram_user_id': player_stat['passport'].user_id,
                'category': category
            })
        
        return result
    
    def _get_stat_value(self, player_data: Dict, category: str) -> int:
        """Получить значение статистики по категории"""
        category_mapping = {
            'trophies': 'trophies',
            'donations': 'donations',
            'war_stars': 'warStars',
            'attack_wins': 'attackWins',
            'defense_wins': 'defenseWins',
            'exp_level': 'expLevel'
        }
        
        return player_data.get(category_mapping.get(category, 'trophies'), 0)
```

#### 5. Форматирование топов для Telegram

```python
def format_ranking_message(
    rankings: List[Dict], 
    category: str, 
    title: str
) -> str:
    """Форматировать сообщение с топом игроков"""
    
    category_emojis = {
        'trophies': '🏆',
        'donations': '🎁',
        'war_stars': '⭐',
        'attack_wins': '⚔️',
        'defense_wins': '🛡️',
        'exp_level': '📊'
    }
    
    emoji = category_emojis.get(category, '📈')
    
    message = f"{emoji} **{title}**\n\n"
    
    for rank_data in rankings:
        rank = rank_data['rank']
        name = rank_data['name']
        value = rank_data['stat_value']
        is_verified = rank_data.get('is_verified', False)
        
        # Медали для топ-3
        medal = ""
        if rank == 1:
            medal = "🥇 "
        elif rank == 2:
            medal = "🥈 "
        elif rank == 3:
            medal = "🥉 "
        
        # Форматирование имени
        formatted_name = format_player_name(name, is_verified)
        
        # Форматирование значения
        formatted_value = f"{value:,}" if isinstance(value, int) else str(value)
        
        message += f"{medal}`{rank}.` {formatted_name} - {emoji} {formatted_value}\n"
    
    message += f"\n💡 Верифицированные игроки выделены **жирным** ✅"
    
    return message

# Пример команды бота
async def cmd_top_donations(message, clan_tag: str):
    """Команда показа топа донатеров"""
    try:
        rankings = await player_rankings.get_clan_top_donors(clan_tag, limit=10)
        
        if not rankings:
            await message.reply("❌ Не удалось получить данные о клане")
            return
        
        clan_data = await api.get_clan(clan_tag)
        title = f"Топ донатеров клана {clan_data['name']}"
        
        formatted_message = format_ranking_message(rankings, 'donations', title)
        
        await message.reply(formatted_message, parse_mode='Markdown')
        
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")
```

### Преимущества системы паспортов

#### Для пользователей:
- 🔐 **Верификация личности** - подтверждение владения аккаунтом
- 📊 **Расширенная статистика** - детальная аналитика прогресса
- 🏆 **Участие в рейтингах** - позиции в различных топах
- ⭐ **Эксклюзивные функции** - доступ к дополнительным возможностям бота

#### Для администраторов кланов:
- 👥 **Управление участниками** - легкая идентификация игроков
- 📈 **Мониторинг активности** - отслеживание вклада участников
- 🛡️ **Защита от мультиаккаунтов** - одна привязка на пользователя
- 📋 **Детальная отчетность** - расширенная аналитика клана

---

## �💡 Примеры использования

### Базовый клиент API

```python
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote

class ClashOfClansAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.clashofclans.com/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _encode_tag(self, tag: str) -> str:
        """Кодирует тег для использования в URL"""
        if not tag.startswith('#'):
            tag = f"#{tag}"
        return quote(tag, safe='')
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполняет запрос к API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise ValueError(f"Resource not found: {url}")
                elif response.status == 429:
                    raise ValueError("Rate limit exceeded")
                else:
                    error_data = await response.json()
                    raise ValueError(f"API Error {response.status}: {error_data}")
        except aiohttp.ClientError as e:
            self.logger.error(f"Request failed: {e}")
            raise
    
    # Методы для работы с кланами
    async def get_clan(self, clan_tag: str) -> Dict[str, Any]:
        """Получить информацию о клане"""
        encoded_tag = self._encode_tag(clan_tag)
        return await self._make_request(f"/clans/{encoded_tag}")
    
    async def get_clan_members(self, clan_tag: str, limit: int = 50) -> Dict[str, Any]:
        """Получить участников клана"""
        encoded_tag = self._encode_tag(clan_tag)
        params = {"limit": min(limit, 50)}
        return await self._make_request(f"/clans/{encoded_tag}/members", params)
    
    async def get_clan_war(self, clan_tag: str) -> Dict[str, Any]:
        """Получить текущую войну клана"""
        encoded_tag = self._encode_tag(clan_tag)
        return await self._make_request(f"/clans/{encoded_tag}/currentwar")
    
    async def get_clan_warlog(self, clan_tag: str, limit: int = 10) -> Dict[str, Any]:
        """Получить журнал войн клана"""
        encoded_tag = self._encode_tag(clan_tag)
        params = {"limit": min(limit, 50)}
        return await self._make_request(f"/clans/{encoded_tag}/warlog", params)
    
    async def search_clans(self, **kwargs) -> Dict[str, Any]:
        """Поиск кланов"""
        allowed_params = [
            'name', 'warFrequency', 'locationId', 'minMembers', 
            'maxMembers', 'minClanPoints', 'minClanLevel', 'limit'
        ]
        params = {k: v for k, v in kwargs.items() if k in allowed_params}
        return await self._make_request("/clans", params)
    
    # Методы для работы с игроками
    async def get_player(self, player_tag: str) -> Dict[str, Any]:
        """Получить информацию об игроке"""
        encoded_tag = self._encode_tag(player_tag)
        return await self._make_request(f"/players/{encoded_tag}")
    
    # Методы для работы с лигами
    async def get_leagues(self, limit: int = 50) -> Dict[str, Any]:
        """Получить список лиг"""
        params = {"limit": min(limit, 50)}
        return await self._make_request("/leagues", params)
    
    async def get_league_seasons(self, league_id: int, limit: int = 50) -> Dict[str, Any]:
        """Получить сезоны лиги"""
        params = {"limit": min(limit, 50)}
        return await self._make_request(f"/leagues/{league_id}/seasons", params)
    
    # Методы для работы с локациями
    async def get_locations(self, limit: int = 50) -> Dict[str, Any]:
        """Получить список локаций"""
        params = {"limit": min(limit, 50)}
        return await self._make_request("/locations", params)
    
    async def get_location_clan_rankings(self, location_id: int, limit: int = 200) -> Dict[str, Any]:
        """Получить топ кланов по локации"""
        params = {"limit": min(limit, 200)}
        return await self._make_request(f"/locations/{location_id}/rankings/clans", params)
```

### Пример использования

```python
async def main():
    api_token = "your_api_token_here"
    clan_tag = "#YU88VQJ2"
    
    async with ClashOfClansAPI(api_token) as api:
        try:
            # Получить информацию о клане
            clan = await api.get_clan(clan_tag)
            print(f"Клан: {clan['name']} (Уровень: {clan['clanLevel']})")
            print(f"Участников: {clan['members']}/50")
            print(f"Очки клана: {clan['clanPoints']:,}")
            
            # Получить участников клана
            members = await api.get_clan_members(clan_tag)
            print(f"\nТоп-5 участников по донатам:")
            sorted_members = sorted(
                members['items'], 
                key=lambda x: x['donations'], 
                reverse=True
            )[:5]
            
            for i, member in enumerate(sorted_members, 1):
                print(f"{i}. {member['name']}: {member['donations']} донатов")
            
            # Получить текущую войну
            try:
                war = await api.get_clan_war(clan_tag)
                if war['state'] != 'notInWar':
                    print(f"\nТекущая война: {war['state']}")
                    print(f"Противник: {war['opponent']['name']}")
                    print(f"Размер войны: {war['teamSize']}x{war['teamSize']}")
                else:
                    print("\nКлан не участвует в войне")
            except ValueError as e:
                print(f"\nНе удалось получить информацию о войне: {e}")
            
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Мониторинг изменений в клане

```python
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Set
from datetime import datetime

@dataclass
class ClanMember:
    tag: str
    name: str
    role: str
    donations: int
    donations_received: int
    trophies: int

class ClanMonitor:
    def __init__(self, api: ClashOfClansAPI, clan_tag: str):
        self.api = api
        self.clan_tag = clan_tag
        self.previous_members: Dict[str, ClanMember] = {}
        self.callbacks = []
    
    def add_callback(self, callback):
        """Добавить callback для уведомлений"""
        self.callbacks.append(callback)
    
    async def check_changes(self):
        """Проверить изменения в клане"""
        try:
            members_data = await self.api.get_clan_members(self.clan_tag)
            current_members = {
                member['tag']: ClanMember(
                    tag=member['tag'],
                    name=member['name'],
                    role=member['role'],
                    donations=member['donations'],
                    donations_received=member['donationsReceived'],
                    trophies=member['trophies']
                )
                for member in members_data['items']
            }
            
            if self.previous_members:
                await self._detect_changes(current_members)
            
            self.previous_members = current_members
            
        except Exception as e:
            print(f"Ошибка при проверке изменений: {e}")
    
    async def _detect_changes(self, current_members: Dict[str, ClanMember]):
        """Обнаружить изменения между проверками"""
        previous_tags = set(self.previous_members.keys())
        current_tags = set(current_members.keys())
        
        # Новые участники
        new_members = current_tags - previous_tags
        for tag in new_members:
            member = current_members[tag]
            await self._notify('member_joined', {
                'member': member,
                'timestamp': datetime.now()
            })
        
        # Покинувшие участники
        left_members = previous_tags - current_tags
        for tag in left_members:
            member = self.previous_members[tag]
            await self._notify('member_left', {
                'member': member,
                'timestamp': datetime.now()
            })
        
        # Изменения у существующих участников
        for tag in current_tags & previous_tags:
            current = current_members[tag]
            previous = self.previous_members[tag]
            
            # Проверка донатов
            if current.donations > previous.donations:
                donated = current.donations - previous.donations
                await self._notify('member_donated', {
                    'member': current,
                    'amount': donated,
                    'timestamp': datetime.now()
                })
            
            # Проверка изменения роли
            if current.role != previous.role:
                await self._notify('role_changed', {
                    'member': current,
                    'old_role': previous.role,
                    'new_role': current.role,
                    'timestamp': datetime.now()
                })
    
    async def _notify(self, event_type: str, data: Dict):
        """Отправить уведомление всем callback'ам"""
        for callback in self.callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                print(f"Ошибка в callback {callback}: {e}")
    
    async def start_monitoring(self, interval: int = 300):
        """Запустить мониторинг с заданным интервалом (в секундах)"""
        print(f"Запуск мониторинга клана {self.clan_tag} с интервалом {interval} секунд")
        
        while True:
            await self.check_changes()
            await asyncio.sleep(interval)

# Пример callback'а для уведомлений
async def on_clan_event(event_type: str, data: Dict):
    timestamp = data['timestamp'].strftime('%H:%M:%S')
    
    if event_type == 'member_joined':
        print(f"[{timestamp}] ➕ {data['member'].name} вступил в клан")
    elif event_type == 'member_left':
        print(f"[{timestamp}] ➖ {data['member'].name} покинул клан")
    elif event_type == 'member_donated':
        print(f"[{timestamp}] 🎁 {data['member'].name} задонатил {data['amount']} войск")
    elif event_type == 'role_changed':
        print(f"[{timestamp}] 👑 {data['member'].name}: {data['old_role']} → {data['new_role']}")

# Использование мониторинга
async def monitor_example():
    api_token = "your_api_token_here"
    clan_tag = "#YU88VQJ2"
    
    async with ClashOfClansAPI(api_token) as api:
        monitor = ClanMonitor(api, clan_tag)
        monitor.add_callback(on_clan_event)
        
        await monitor.start_monitoring(interval=60)  # Проверка каждую минуту
```

---

## ❌ Обработка ошибок

### Типичные ошибки

```python
class ClashAPIError(Exception):
    """Базовый класс для ошибок API"""
    pass

class NotFoundError(ClashAPIError):
    """Ресурс не найден (404)"""
    pass

class RateLimitError(ClashAPIError):
    """Превышен лимит запросов (429)"""
    pass

class InvalidCredentialsError(ClashAPIError):
    """Неверные учетные данные (403)"""
    pass

class MaintenanceError(ClashAPIError):
    """Техническое обслуживание (503)"""
    pass

async def handle_api_error(response: aiohttp.ClientResponse) -> None:
    """Обработать ошибки API"""
    error_data = await response.json() if response.content_type == 'application/json' else {}
    
    if response.status == 400:
        raise ClashAPIError(f"Bad request: {error_data.get('message', 'Unknown error')}")
    elif response.status == 403:
        raise InvalidCredentialsError("Invalid API token or insufficient permissions")
    elif response.status == 404:
        raise NotFoundError("Resource not found")
    elif response.status == 429:
        raise RateLimitError("Rate limit exceeded")
    elif response.status == 503:
        raise MaintenanceError("Service temporarily unavailable")
    else:
        raise ClashAPIError(f"API Error {response.status}: {error_data}")
```

### Retry механизм

```python
import asyncio
from functools import wraps

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError:
                    if attempt < max_retries:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        await asyncio.sleep(wait_time)
                        continue
                    raise
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    # Не повторяем для других типов ошибок
                    raise
            
            raise last_exception
        return wrapper
    return decorator
```

---

## 🏆 Best Practices

### 1. Управление токенами

```python
import os
from typing import List

class TokenManager:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.current_index = 0
        self.rate_limit_reset_times = {}
    
    def get_next_token(self) -> str:
        """Получить следующий доступный токен"""
        for _ in range(len(self.tokens)):
            token = self.tokens[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.tokens)
            
            # Проверить, не заблокирован ли токен
            if not self._is_rate_limited(token):
                return token
        
        raise RateLimitError("All tokens are rate limited")
    
    def _is_rate_limited(self, token: str) -> bool:
        """Проверить, заблокирован ли токен"""
        reset_time = self.rate_limit_reset_times.get(token)
        if reset_time and datetime.now() < reset_time:
            return True
        return False
```

### 2. Кеширование данных

```python
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional

class APICache:
    def __init__(self, default_ttl: int = 300):  # 5 минут по умолчанию
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Получить данные из кеша"""
        if key in self.cache:
            data, expires_at = self.cache[key]
            if datetime.now() < expires_at:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Сохранить данные в кеш"""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (data, expires_at)
    
    def clear_expired(self) -> None:
        """Очистить просроченные записи"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self.cache.items()
            if now >= expires_at
        ]
        for key in expired_keys:
            del self.cache[key]
```

### 3. Batch операции

```python
async def get_multiple_players(api: ClashOfClansAPI, player_tags: List[str]) -> Dict[str, Dict]:
    """Получить информацию о нескольких игроках параллельно"""
    tasks = []
    semaphore = asyncio.Semaphore(10)  # Ограничить количество одновременных запросов
    
    async def get_player_with_semaphore(tag: str):
        async with semaphore:
            try:
                return tag, await api.get_player(tag)
            except Exception as e:
                return tag, {"error": str(e)}
    
    tasks = [get_player_with_semaphore(tag) for tag in player_tags]
    results = await asyncio.gather(*tasks)
    
    return dict(results)
```

### 4. Валидация тегов

```python
import re

def validate_tag(tag: str) -> str:
    """Валидировать и нормализовать тег"""
    if not tag:
        raise ValueError("Tag cannot be empty")
    
    # Добавить # если отсутствует
    if not tag.startswith('#'):
        tag = f"#{tag}"
    
    # Проверить формат (буквы, цифры, длина 3-15 символов после #)
    if not re.match(r'^#[A-Z0-9]{3,15}$', tag.upper()):
        raise ValueError(f"Invalid tag format: {tag}")
    
    return tag.upper()
```

### 5. Логирование

```python
import logging
import structlog

# Настройка структурированного логирования
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

async def log_api_request(endpoint: str, params: Dict, response_time: float, status: int):
    """Логировать API запрос"""
    logger.info(
        "API request completed",
        endpoint=endpoint,
        params=params,
        response_time=response_time,
        status=status
    )
```

---

## 📝 Заключение

Clash of Clans API предоставляет мощные возможности для создания ботов и приложений для мониторинга кланов и игроков. Следуя best practices и правильно обрабатывая ошибки, вы сможете создать надежное и эффективное приложение.

### Ключевые моменты:

1. **Всегда обрабатывайте rate limits** - используйте retry механизмы и множественные токены
2. **Кешируйте данные** - избегайте избыточных запросов
3. **Валидируйте входные данные** - проверяйте теги перед отправкой запросов
4. **Логируйте операции** - это поможет при отладке и мониторинге
5. **Используйте асинхронность** - для лучшей производительности

### Полезные ссылки:

- **Официальная документация**: https://developer.clashofclans.com/#/documentation
- **coc.py библиотека**: https://github.com/mathsman5133/coc.py
- **Discord сервер**: https://discord.gg/clashapi
- **Fan Content Policy**: https://supercell.com/en/fan-content-policy/

---

*Этот документ создан для использования в проекте NewPyBot для Clash of Clans v1.2.2*