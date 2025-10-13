# Использование сервисов статистики

## Сохранение статистики клановых войн

### Пример сохранения результата войны

```python
from bot.services.war_stats_service import get_war_stats_service

# Получаем сервис
war_stats = get_war_stats_service()

# Данные войны из Clash of Clans API
war_data = {
    'teamSize': 15,
    'clan': {
        'tag': '#2PP',
        'name': 'My Clan',
        'stars': 42,
        'destructionPercentage': 95.5,
        'members': [
            {
                'tag': '#PLAYER1',
                'name': 'Player 1',
                'townhallLevel': 14,
                'mapPosition': 1,
                'attacks': [
                    {
                        'defenderTag': '#ENEMY1',
                        'defenderName': 'Enemy 1',
                        'stars': 3,
                        'destructionPercentage': 100.0,
                        'order': 1,
                        'duration': 180
                    }
                ],
                'bestOpponentAttack': {
                    'stars': 2,
                    'destructionPercentage': 85.0
                }
            }
        ]
    },
    'opponent': {
        'tag': '#ENEMY',
        'name': 'Enemy Clan',
        'stars': 38,
        'destructionPercentage': 88.2
    },
    'startTime': '20250110T120000.000Z',
    'endTime': '20250111T120000.000Z',
    'preparationStartTime': '20250109T120000.000Z',
    'warType': 'regular'
}

# Сохраняем результат войны
war_id = await war_stats.save_war_result(
    clan_tag='#2PP',
    clan_name='My Clan',
    opponent_tag='#ENEMY',
    opponent_name='Enemy Clan',
    war_data=war_data
)

print(f"War saved with ID: {war_id}")
```

### Получение истории войн клана

```python
# Получить последние 10 войн клана
wars = await war_stats.get_clan_war_history(
    clan_tag='#2PP',
    limit=10
)

for war in wars:
    print(f"{war['clan_name']} vs {war['opponent_name']}: {war['result']}")
    print(f"Stars: {war['clan_stars']} - {war['opponent_stars']}")
```

### Получение статистики игрока по войнам

```python
# Получить статистику игрока
player_stats = await war_stats.get_player_war_stats(
    player_tag='#PLAYER1',
    limit=20
)

for stat in player_stats:
    print(f"War vs {stat['opponent_name']}: {stat['stars_earned']} stars")
    print(f"Attacks: {stat['attacks_used']}/{stat['attacks_total']}")
```

---

## Сохранение статистики рейдов

### Пример сохранения результата рейдовых выходных

```python
from bot.services.raid_stats_service import get_raid_stats_service

# Получаем сервис
raid_stats = get_raid_stats_service()

# Данные рейда из Clash of Clans API
raid_data = {
    'startTime': '20250110T000000.000Z',
    'endTime': '20250113T000000.000Z',
    'state': 'ended',
    'capitalTotalLoot': 125000,
    'raidsCompleted': 5,
    'totalAttacks': 180,
    'enemyDistrictsDestroyed': 23,
    'defensiveReward': 50000,
    'offensiveReward': 75000,
    'members': [
        {
            'tag': '#PLAYER1',
            'name': 'Player 1',
            'attacks': 6,
            'attackLimit': 6,
            'capitalResourcesLooted': 15000,
            'bonusAttackLimit': 0,
            'attacks': [
                {
                    'districtId': 1,
                    'districtName': 'Capital Peak',
                    'stars': 3,
                    'destructionPercent': 100.0,
                    'capitalResourcesLooted': 5000
                }
            ]
        }
    ]
}

# Сохраняем результат рейда
raid_id = await raid_stats.save_raid_weekend_result(
    clan_tag='#2PP',
    clan_name='My Clan',
    raid_data=raid_data
)

print(f"Raid saved with ID: {raid_id}")
```

### Получение истории рейдов клана

```python
# Получить последние 10 рейдов клана
raids = await raid_stats.get_clan_raid_history(
    clan_tag='#2PP',
    limit=10
)

for raid in raids:
    print(f"Raid {raid['end_time']}: {raid['total_loot']} loot")
    print(f"Raids completed: {raid['raids_completed']}")
```

### Получение статистики игрока по рейдам

```python
# Получить статистику игрока
player_stats = await raid_stats.get_player_raid_stats(
    player_tag='#PLAYER1',
    limit=20
)

for stat in player_stats:
    print(f"Raid {stat['end_time']}: {stat['capital_resources_looted']} loot")
    print(f"Attacks: {stat['attacks_used']}/{stat['attacks_limit']}")
```

### Получение таблицы лидеров рейда

```python
# Получить топ игроков по награбленному золоту
leaderboard = await raid_stats.get_raid_leaderboard(
    raid_id=1,
    order_by='capital_resources_looted'
)

for i, player in enumerate(leaderboard, 1):
    print(f"{i}. {player['player_name']}: {player['capital_resources_looted']} gold")
```

---

## Структура таблиц БД

### Клановые войны

**clan_wars** - основная информация о войнах
- id, clan_tag, clan_name, opponent_tag, opponent_name
- war_size, result (win/lose/draw)
- clan_stars, clan_destruction, opponent_stars, opponent_destruction
- start_time, end_time, war_type

**war_player_stats** - статистика игроков
- war_id, player_tag, player_name
- attacks_used, attacks_total, stars_earned
- destruction_percentage, town_hall_level, map_position

**war_attacks** - детали атак
- war_id, attacker_tag, defender_tag
- stars, destruction_percentage, attack_order, duration

### Рейды

**raid_weekends** - рейдовые выходные
- id, clan_tag, clan_name, start_time, end_time
- total_loot, raids_completed, total_attacks
- enemy_districts_destroyed, defensive_reward, offensive_reward

**raid_player_stats** - статистика игроков
- raid_id, player_tag, player_name
- attacks_used, attacks_limit, capital_resources_looted

**raid_attacks** - детали атак
- raid_id, attacker_tag, district_name
- stars, destruction_percentage, loot

---

## Автоматическое сохранение

Для автоматического сохранения статистики после окончания войн/рейдов можно использовать планировщик или webhook от Clash of Clans API.

### Пример с планировщиком

```python
from bot.services.extended_clash_api import ExtendedClashAPI
from bot.services.war_stats_service import get_war_stats_service

async def check_and_save_wars():
    """Проверить и сохранить завершенные войны"""
    clash_api = ExtendedClashAPI(tokens)
    war_stats = get_war_stats_service()
    
    # Получаем список кланов из БД
    clans = await get_registered_clans()
    
    for clan in clans:
        # Получаем текущую войну
        war = await clash_api.get_current_war(clan['clan_tag'])
        
        if war and war['state'] == 'warEnded':
            # Сохраняем результат
            await war_stats.save_war_result(
                clan_tag=clan['clan_tag'],
                clan_name=clan['clan_name'],
                opponent_tag=war['opponent']['tag'],
                opponent_name=war['opponent']['name'],
                war_data=war
            )
```
