# Система метрик и отслеживания прогресса игроков NewPyBot v1.2.2

## 📋 Обзор системы

### Основная концепция

**Автоматическое отслеживание прогресса** - ежедневный сбор и анализ данных игроков через Clash of Clans API для точного расчета изменений, достижений и статистики.

**Принципы системы:**
- 🔄 **Автоматизация** - ежедневные снапшоты без участия пользователей
- 📊 **Точность** - отслеживание реальных изменений через API данные
- 📈 **Историчность** - ведение полной истории прогресса
- ⚡ **Производительность** - оптимизированная обработка больших объемов данных
- 🎯 **Интеграция** - тесная связь с системой паспортов и достижений

---

## 🎯 Ключевые метрики для отслеживания

### 🏰 Основные игровые показатели

#### Кубки и лиги
```
Трофеи:
- current_trophies: Текущие кубки
- best_trophies: Лучший результат
- daily_trophy_change: Изменение за день
- weekly_trophy_trend: Тренд за неделю
- league_id: ID текущей лиги
- league_name: Название лиги

Builder Base:
- bb_trophies: Кубки Builder Base
- bb_best_trophies: Лучший результат BB
- bb_wins: Побед против других игроков
```

#### Уровни и развитие
```
Прогресс:
- exp_level: Уровень опыта
- exp_points: Очки опыта
- town_hall_level: Уровень Town Hall
- town_hall_weapon_level: Уровень оружия ТХ
- builder_hall_level: Уровень Builder Hall

Достижения:
- achievement_points: Очки достижений
- completed_achievements: Завершенные ачивки
- achievement_progress: JSON с прогрессом
```

#### Военная активность  
```
Статистика атак:
- attack_wins: Победы в атаках
- defense_wins: Успешные защиты
- total_stars: Общее количество звезд
- war_stars: Звезды в войнах клана
- capital_contributions: Вклад в Capital Raids

Донаты:
- donations_given: Войска отданы
- donations_received: Войска получены  
- donation_ratio: Соотношение донатов
```

### 🎁 Экономические метрики

#### Ресурсы (через достижения)
```
Gold:
- gold_grab_achievement: Прогресс "Gold Grab"
- daily_gold_farmed: Расчетное количество за день
- total_gold_farmed: Общее количество нафармленного

Elixir:  
- elixir_escapade_achievement: Прогресс "Elixir Escapade"  
- daily_elixir_farmed: Расчетное количество за день
- total_elixir_farmed: Общее количество

Dark Elixir:
- heroic_heist_achievement: Прогресс "Heroic Heist"
- daily_dark_elixir_farmed: Расчетное количество за день
- total_dark_elixir_farmed: Общее количество

Capital Gold:
- aggressive_capitalism: Прогресс достижения
- daily_capital_gold: Заработано за день
- raid_medal_rewards: Медали от рейдов
```

#### Боевые достижения (фарм через атаки)
```
Разрушения:
- destructor_achievement: Прогресс "Destructor" 
- buildings_destroyed: Здания разрушено
- daily_destruction: Разрушений за день

Obstacles:
- nice_and_tidy: Очистка препятствий
- obstacles_removed: Убрано препятствий
- gem_rewards: Гемы за препятствия
```

### 📊 Социальные и клановые метрики

#### Активность в клане
```
Участие:
- clan_role: Роль в клане
- clan_join_date: Дата вступления (если доступно)
- time_in_clan: Время в текущем клане
- previous_clans: История кланов

Войны:
- war_participation: Участие в войнах
- war_performance: Качество атак в войнах
- missed_attacks: Пропущенные атаки
- war_mvp_count: Количество MVP в войнах

Capital Raids:
- raid_attacks_used: Использованные атаки
- raid_damage_dealt: Нанесенный урон
- raid_medals_earned: Заработанные медали
- raid_consistency: Регулярность участия
```

#### Лидерство и влияние  
```
Социальные:
- friend_in_need: Помощь согильдийцам (донаты)
- sharing_is_caring: Заклинания отданы
- siege_sharer: Осадные машины переданы

Качество игры:
- attack_strategy_diversity: Разнообразие стратегий
- base_design_rating: Оценка дизайна базы
- helping_new_players: Помощь новичкам в клане
```

---

## 🏗️ Архитектура системы метрик

### База данных для метрик

#### Ежедневные снапшоты игроков
```sql
-- Основная таблица ежедневных снимков
CREATE TABLE daily_player_snapshots (
    id SERIAL PRIMARY KEY,
    player_tag VARCHAR(15) NOT NULL,
    snapshot_date DATE NOT NULL,
    
    -- Основные показатели
    trophies INTEGER NOT NULL,
    best_trophies INTEGER NOT NULL,
    exp_level INTEGER NOT NULL,
    exp_points INTEGER NOT NULL,
    town_hall_level INTEGER NOT NULL,
    town_hall_weapon_level INTEGER DEFAULT NULL,
    builder_hall_level INTEGER DEFAULT NULL,
    
    -- Builder Base
    bb_trophies INTEGER DEFAULT 0,
    bb_best_trophies INTEGER DEFAULT 0,
    bb_wins INTEGER DEFAULT 0,
    
    -- Лига
    league_id INTEGER DEFAULT NULL,
    league_name VARCHAR(50) DEFAULT NULL,
    
    -- Боевая статистика
    attack_wins INTEGER DEFAULT 0,
    defense_wins INTEGER DEFAULT 0,
    war_stars INTEGER DEFAULT 0,
    
    -- Донаты
    donations_given INTEGER DEFAULT 0,
    donations_received INTEGER DEFAULT 0,
    
    -- Достижения (JSON для гибкости)
    achievements_progress JSON NOT NULL DEFAULT '{}',
    
    -- Клановая информация
    clan_tag VARCHAR(15) DEFAULT NULL,
    clan_name VARCHAR(100) DEFAULT NULL,
    clan_role VARCHAR(20) DEFAULT NULL,
    
    -- Метаданные
    api_response_hash VARCHAR(64), -- Для определения изменений
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(player_tag, snapshot_date),
    INDEX idx_player_date (player_tag, snapshot_date DESC),
    INDEX idx_snapshot_date (snapshot_date),
    INDEX idx_clan_tag (clan_tag, snapshot_date)
);

-- Таблица рассчитанных изменений  
CREATE TABLE player_daily_changes (
    id SERIAL PRIMARY KEY,
    player_tag VARCHAR(15) NOT NULL,
    change_date DATE NOT NULL,
    
    -- Изменения кубков
    trophy_change INTEGER DEFAULT 0,
    bb_trophy_change INTEGER DEFAULT 0,
    
    -- Изменения опыта и уровней
    exp_gained INTEGER DEFAULT 0,
    level_ups INTEGER DEFAULT 0, -- Количество поднятых уровней (ТХ, БХ и т.д.)
    
    -- Изменения боевой статистики
    attacks_won INTEGER DEFAULT 0,
    defenses_won INTEGER DEFAULT 0,
    war_stars_gained INTEGER DEFAULT 0,
    
    -- Изменения донатов
    donations_made INTEGER DEFAULT 0,
    donations_got INTEGER DEFAULT 0,
    
    -- Ресурсы (рассчитанные)
    gold_farmed BIGINT DEFAULT 0,
    elixir_farmed BIGINT DEFAULT 0,
    dark_elixir_farmed INTEGER DEFAULT 0,
    capital_gold_earned INTEGER DEFAULT 0,
    
    -- Другие активности
    buildings_destroyed INTEGER DEFAULT 0,
    obstacles_removed INTEGER DEFAULT 0,
    achievements_completed INTEGER DEFAULT 0,
    
    -- Клановые изменения
    clan_changed BOOLEAN DEFAULT FALSE,
    new_clan_tag VARCHAR(15) DEFAULT NULL,
    role_changed BOOLEAN DEFAULT FALSE,
    new_role VARCHAR(20) DEFAULT NULL,
    
    -- Метаданные
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(player_tag, change_date),
    INDEX idx_player_changes (player_tag, change_date DESC),
    INDEX idx_change_date (change_date),
    INDEX idx_trophy_change (change_date, trophy_change DESC)
);

-- Таблица агрегированной статистики за периоды
CREATE TABLE player_period_stats (
    id SERIAL PRIMARY KEY,
    player_tag VARCHAR(15) NOT NULL,
    period_type VARCHAR(10) NOT NULL, -- 'week', 'month', 'season'
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Агрегированные изменения
    total_trophy_change INTEGER DEFAULT 0,
    total_gold_farmed BIGINT DEFAULT 0,
    total_elixir_farmed BIGINT DEFAULT 0,
    total_dark_elixir_farmed INTEGER DEFAULT 0,
    total_capital_gold BIGINT DEFAULT 0,
    
    total_attacks_won INTEGER DEFAULT 0,
    total_defenses_won INTEGER DEFAULT 0,
    total_war_stars INTEGER DEFAULT 0,
    total_donations_made INTEGER DEFAULT 0,
    
    -- Средние показатели
    avg_daily_trophies DECIMAL(8,2) DEFAULT 0,
    avg_daily_donations DECIMAL(8,2) DEFAULT 0,
    
    -- Достижения за период
    achievements_earned INTEGER DEFAULT 0,
    levels_gained INTEGER DEFAULT 0,
    
    -- Активность
    days_active INTEGER DEFAULT 0, -- Дней с изменениями
    consistency_score DECIMAL(5,2) DEFAULT 0, -- Индекс постоянства
    
    -- Метаданные
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(player_tag, period_type, period_start),
    INDEX idx_player_period (player_tag, period_type, period_start DESC),
    INDEX idx_period_stats (period_type, period_start)
);
```

#### Метрики достижений игроков
```sql  
-- Отслеживание прогресса к достижениям Clash of Clans
CREATE TABLE coc_achievement_tracking (
    id SERIAL PRIMARY KEY,
    player_tag VARCHAR(15) NOT NULL,
    achievement_name VARCHAR(100) NOT NULL, -- "Gold Grab", "Elixir Escapade" и т.д.
    
    current_value BIGINT DEFAULT 0,      -- Текущее значение
    target_value BIGINT DEFAULT 0,       -- Целевое значение для завершения
    is_completed BOOLEAN DEFAULT FALSE,  -- Завершено ли достижение
    
    -- Отслеживание изменений
    previous_value BIGINT DEFAULT 0,     -- Предыдущее значение
    daily_progress BIGINT DEFAULT 0,     -- Прогресс за день
    
    last_updated DATE DEFAULT CURRENT_DATE,
    completed_at DATE DEFAULT NULL,
    
    UNIQUE(player_tag, achievement_name),
    INDEX idx_player_achievements (player_tag),
    INDEX idx_achievement_progress (achievement_name, current_value DESC)
);

-- Связь достижений CoC с достижениями паспорта
CREATE TABLE achievement_mapping (
    id SERIAL PRIMARY KEY,
    passport_achievement_id INTEGER NOT NULL, -- ID из таблицы achievements
    coc_achievement_name VARCHAR(100) NOT NULL, -- Название достижения в CoC
    calculation_type VARCHAR(20) NOT NULL,   -- 'direct', 'calculated', 'threshold'
    
    -- Параметры расчета
    multiplier DECIMAL(10,4) DEFAULT 1.0,   -- Множитель для пересчета
    threshold_value BIGINT DEFAULT NULL,     -- Пороговое значение
    
    FOREIGN KEY (passport_achievement_id) REFERENCES achievements(id),
    INDEX idx_coc_achievement (coc_achievement_name),
    INDEX idx_passport_achievement (passport_achievement_id)
);
```

### Система сбора данных

#### Основной класс сбора метрик
```python
class PlayerMetricsCollector:
    def __init__(self, coc_api, db_connection):
        self.coc_api = coc_api
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
        
    async def collect_daily_snapshots(self) -> Dict:
        """Ежедневный сбор снапшотов всех привязанных игроков"""
        
        # Получаем всех привязанных игроков
        bound_players = await self.db.fetch_all("""
            SELECT DISTINCT player_tag FROM user_player_bindings 
            WHERE is_active = TRUE
        """)
        
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        # Batch обработка для производительности
        batch_size = 100
        for i in range(0, len(bound_players), batch_size):
            batch = bound_players[i:i + batch_size]
            
            # Параллельные запросы к API
            tasks = [
                self._collect_player_snapshot(player['player_tag']) 
                for player in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results['failed'] += 1
                    results['errors'].append(str(result))
                else:
                    results['success'] += 1
                    
        return results
    
    async def _collect_player_snapshot(self, player_tag: str) -> bool:
        """Сбор снапшота одного игрока"""
        
        try:
            # Получаем данные игрока через API
            player_data = await self.coc_api.get_player(player_tag)
            if not player_data:
                raise ValueError(f"Player not found: {player_tag}")
            
            # Создаем хеш для определения изменений
            data_hash = self._calculate_data_hash(player_data)
            
            # Проверяем, изменились ли данные с прошлого раза
            last_hash = await self.db.fetch_val("""
                SELECT api_response_hash FROM daily_player_snapshots
                WHERE player_tag = ? AND snapshot_date = CURRENT_DATE - INTERVAL '1 day'
            """, (player_tag,))
            
            # Сохраняем снапшот
            snapshot_data = self._extract_snapshot_data(player_data)
            snapshot_data['api_response_hash'] = data_hash
            
            await self._save_snapshot(player_tag, snapshot_data)
            
            # Если данные изменились, рассчитываем изменения
            if data_hash != last_hash:
                await self._calculate_daily_changes(player_tag, player_data)
                await self._update_achievement_progress(player_tag, player_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to collect snapshot for {player_tag}: {e}")
            raise
    
    def _extract_snapshot_data(self, player_data: Dict) -> Dict:
        """Извлечение ключевых метрик из API ответа"""
        
        return {
            'trophies': player_data.get('trophies', 0),
            'best_trophies': player_data.get('bestTrophies', 0),
            'exp_level': player_data.get('expLevel', 0),
            'exp_points': player_data.get('expPoints', 0),
            'town_hall_level': player_data.get('townHallLevel', 0),
            'town_hall_weapon_level': player_data.get('townHallWeaponLevel'),
            'builder_hall_level': player_data.get('builderHallLevel', 0),
            
            'bb_trophies': player_data.get('builderBaseTrophies', 0),
            'bb_best_trophies': player_data.get('bestBuilderBaseTrophies', 0),
            'bb_wins': player_data.get('versusBattleWins', 0),
            
            'league_id': player_data.get('league', {}).get('id'),
            'league_name': player_data.get('league', {}).get('name'),
            
            'attack_wins': player_data.get('attackWins', 0),
            'defense_wins': player_data.get('defenseWins', 0),
            'war_stars': player_data.get('warStars', 0),
            
            'donations_given': player_data.get('donations', 0),
            'donations_received': player_data.get('donationsReceived', 0),
            
            'clan_tag': player_data.get('clan', {}).get('tag'),
            'clan_name': player_data.get('clan', {}).get('name'),  
            'clan_role': player_data.get('role'),
            
            'achievements_progress': self._extract_achievements(player_data.get('achievements', []))
        }
    
    def _extract_achievements(self, achievements: List[Dict]) -> Dict:
        """Извлечение прогресса достижений"""
        
        progress = {}
        
        # Важные достижения для отслеживания ресурсов
        key_achievements = {
            'Gold Grab': 'gold_grab',
            'Elixir Escapade': 'elixir_escapade', 
            'Heroic Heist': 'heroic_heist',
            'Aggressive Capitalism': 'aggressive_capitalism',
            'Destructor': 'destructor',
            'Nice and Tidy': 'nice_and_tidy',
            'Friend in Need': 'friend_in_need',
            'Sharing is caring': 'sharing_is_caring'
        }
        
        for achievement in achievements:
            name = achievement.get('name', '')
            if name in key_achievements:
                key = key_achievements[name]
                progress[key] = {
                    'name': name,
                    'value': achievement.get('value', 0),
                    'target': achievement.get('target', 0),
                    'completed': achievement.get('completionInfo', {}).get('time') is not None
                }
                
        return progress
```

#### Расчет изменений и прогресса
```python
class MetricsCalculator:
    def __init__(self, db_connection):
        self.db = db_connection
        
    async def calculate_daily_changes(self, player_tag: str) -> Dict:
        """Расчет изменений за день"""
        
        # Получаем снапшоты за сегодня и вчера
        today_snapshot = await self._get_snapshot(player_tag, 'CURRENT_DATE')
        yesterday_snapshot = await self._get_snapshot(player_tag, 'CURRENT_DATE - INTERVAL 1 DAY')
        
        if not yesterday_snapshot:
            return {}  # Первый день отслеживания
            
        changes = {
            'trophy_change': today_snapshot['trophies'] - yesterday_snapshot['trophies'],
            'bb_trophy_change': today_snapshot['bb_trophies'] - yesterday_snapshot['bb_trophies'],
            'exp_gained': today_snapshot['exp_points'] - yesterday_snapshot['exp_points'],
            'attacks_won': today_snapshot['attack_wins'] - yesterday_snapshot['attack_wins'],
            'defenses_won': today_snapshot['defense_wins'] - yesterday_snapshot['defense_wins'],
            'war_stars_gained': today_snapshot['war_stars'] - yesterday_snapshot['war_stars'],
            'donations_made': today_snapshot['donations_given'] - yesterday_snapshot['donations_given'],
            'donations_got': today_snapshot['donations_received'] - yesterday_snapshot['donations_received']
        }
        
        # Расчет нафармленных ресурсов через достижения
        resource_changes = await self._calculate_resource_changes(
            today_snapshot, yesterday_snapshot
        )
        changes.update(resource_changes)
        
        # Проверка изменения клана
        clan_changes = self._calculate_clan_changes(today_snapshot, yesterday_snapshot)
        changes.update(clan_changes)
        
        # Сохранение изменений
        await self._save_daily_changes(player_tag, changes)
        
        return changes
    
    async def _calculate_resource_changes(self, today: Dict, yesterday: Dict) -> Dict:
        """Расчет нафармленных ресурсов через достижения"""
        
        today_achievements = today['achievements_progress']
        yesterday_achievements = yesterday['achievements_progress']
        
        changes = {
            'gold_farmed': 0,
            'elixir_farmed': 0,
            'dark_elixir_farmed': 0,
            'capital_gold_earned': 0,
            'buildings_destroyed': 0,
            'obstacles_removed': 0
        }
        
        # Золото (Gold Grab achievement)
        if 'gold_grab' in today_achievements and 'gold_grab' in yesterday_achievements:
            changes['gold_farmed'] = (
                today_achievements['gold_grab']['value'] - 
                yesterday_achievements['gold_grab']['value']
            )
            
        # Эликсир (Elixir Escapade achievement)  
        if 'elixir_escapade' in today_achievements and 'elixir_escapade' in yesterday_achievements:
            changes['elixir_farmed'] = (
                today_achievements['elixir_escapade']['value'] - 
                yesterday_achievements['elixir_escapade']['value']
            )
            
        # Темный эликсир (Heroic Heist achievement)
        if 'heroic_heist' in today_achievements and 'heroic_heist' in yesterday_achievements:
            changes['dark_elixir_farmed'] = (
                today_achievements['heroic_heist']['value'] - 
                yesterday_achievements['heroic_heist']['value']
            )
            
        # Capital Gold (Aggressive Capitalism achievement)
        if 'aggressive_capitalism' in today_achievements and 'aggressive_capitalism' in yesterday_achievements:
            changes['capital_gold_earned'] = (
                today_achievements['aggressive_capitalism']['value'] - 
                yesterday_achievements['aggressive_capitalism']['value']
            )
            
        # Разрушенные здания (Destructor achievement)
        if 'destructor' in today_achievements and 'destructor' in yesterday_achievements:
            changes['buildings_destroyed'] = (
                today_achievements['destructor']['value'] - 
                yesterday_achievements['destructor']['value']
            )
            
        # Убранные препятствия (Nice and Tidy achievement)
        if 'nice_and_tidy' in today_achievements and 'nice_and_tidy' in yesterday_achievements:
            changes['obstacles_removed'] = (
                today_achievements['nice_and_tidy']['value'] - 
                yesterday_achievements['nice_and_tidy']['value']
            )
        
        return changes
```

---

## 📊 Система аналитики и отчетов

### Автоматические расчеты периодов

#### Еженедельные агрегации
```python
class PeriodStatsCalculator:
    def __init__(self, db_connection):
        self.db = db_connection
        
    async def calculate_weekly_stats(self, week_start: date) -> None:
        """Расчет еженедельной статистики для всех игроков"""
        
        week_end = week_start + timedelta(days=6)
        
        # Получаем всех активных игроков
        active_players = await self.db.fetch_all("""
            SELECT DISTINCT player_tag FROM daily_player_changes 
            WHERE change_date BETWEEN ? AND ?
        """, (week_start, week_end))
        
        for player in active_players:
            player_tag = player['player_tag']
            
            # Агрегируем изменения за неделю  
            weekly_stats = await self.db.fetch_one("""
                SELECT 
                    SUM(trophy_change) as total_trophy_change,
                    SUM(gold_farmed) as total_gold_farmed,
                    SUM(elixir_farmed) as total_elixir_farmed,
                    SUM(dark_elixir_farmed) as total_dark_elixir_farmed,
                    SUM(capital_gold_earned) as total_capital_gold,
                    
                    SUM(attacks_won) as total_attacks_won,
                    SUM(defenses_won) as total_defenses_won,
                    SUM(war_stars_gained) as total_war_stars,
                    SUM(donations_made) as total_donations_made,
                    
                    AVG(trophy_change) as avg_daily_trophies,
                    AVG(donations_made) as avg_daily_donations,
                    
                    COUNT(DISTINCT change_date) as days_active,
                    
                    CASE WHEN COUNT(*) > 0 
                         THEN STDDEV(trophy_change) / (ABS(AVG(trophy_change)) + 1) 
                         ELSE 0 
                    END as consistency_score
                    
                FROM daily_player_changes 
                WHERE player_tag = ? AND change_date BETWEEN ? AND ?
            """, (player_tag, week_start, week_end))
            
            if weekly_stats:
                await self._save_period_stats(player_tag, 'week', week_start, week_end, weekly_stats)
    
    async def calculate_resource_efficiency(self, player_tag: str, period_days: int = 7) -> Dict:
        """Расчет эффективности фарма ресурсов"""
        
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        resource_stats = await self.db.fetch_one("""
            SELECT 
                SUM(gold_farmed) as total_gold,
                SUM(elixir_farmed) as total_elixir,
                SUM(dark_elixir_farmed) as total_dark_elixir,
                SUM(attacks_won) as total_attacks,
                COUNT(DISTINCT change_date) as active_days,
                
                -- Эффективность за атаку
                CASE WHEN SUM(attacks_won) > 0 
                     THEN SUM(gold_farmed) / SUM(attacks_won) 
                     ELSE 0 
                END as gold_per_attack,
                
                CASE WHEN SUM(attacks_won) > 0 
                     THEN SUM(elixir_farmed) / SUM(attacks_won)
                     ELSE 0 
                END as elixir_per_attack,
                
                CASE WHEN SUM(attacks_won) > 0 
                     THEN SUM(dark_elixir_farmed) / SUM(attacks_won)
                     ELSE 0 
                END as de_per_attack
                
            FROM daily_player_changes 
            WHERE player_tag = ? AND change_date BETWEEN ? AND ?
        """, (player_tag, start_date, end_date))
        
        return {
            'period_days': period_days,
            'active_days': resource_stats['active_days'],
            'total_resources': {
                'gold': resource_stats['total_gold'],
                'elixir': resource_stats['total_elixir'], 
                'dark_elixir': resource_stats['total_dark_elixir']
            },
            'daily_average': {
                'gold': resource_stats['total_gold'] / max(resource_stats['active_days'], 1),
                'elixir': resource_stats['total_elixir'] / max(resource_stats['active_days'], 1),
                'dark_elixir': resource_stats['total_dark_elixir'] / max(resource_stats['active_days'], 1)
            },
            'efficiency_per_attack': {
                'gold': resource_stats['gold_per_attack'],
                'elixir': resource_stats['elixir_per_attack'],
                'dark_elixir': resource_stats['de_per_attack']
            },
            'total_attacks': resource_stats['total_attacks']
        }
```

### Интеграция с системой достижений

#### Автоматическое начисление достижений
```python
class AchievementProcessor:
    def __init__(self, db_connection):
        self.db = db_connection
        
    async def process_daily_achievements(self, player_tag: str, changes: Dict) -> List[Dict]:
        """Обработка достижений на основе дневных изменений"""
        
        # Получаем пользователя по player_tag
        user_id = await self.db.fetch_val("""
            SELECT user_id FROM user_player_bindings 
            WHERE player_tag = ? AND is_active = TRUE
        """, (player_tag,))
        
        if not user_id:
            return []
            
        # Обновляем статистику активности для достижений
        await self._update_activity_stats(user_id, changes)
        
        # Проверяем новые достижения
        new_achievements = await self._check_new_achievements(user_id)
        
        return new_achievements
    
    async def _update_activity_stats(self, user_id: int, changes: Dict) -> None:
        """Обновление статистики активности пользователя"""
        
        # Обновляем статистику на основе изменений
        await self.db.execute("""
            INSERT INTO user_activity_stats (user_id, last_activity)
            VALUES (?, CURRENT_DATE)
            ON DUPLICATE KEY UPDATE
                -- Игровые метрики
                wars_participated = wars_participated + CASE WHEN ? > 0 THEN 1 ELSE 0 END,
                
                -- Ресурсные достижения  
                total_gold_farmed = total_gold_farmed + ?,
                total_elixir_farmed = total_elixir_farmed + ?,
                total_dark_elixir_farmed = total_dark_elixir_farmed + ?,
                
                -- Боевые достижения
                buildings_destroyed = buildings_destroyed + ?,
                successful_attacks = successful_attacks + ?,
                successful_defenses = successful_defenses + ?,
                
                -- Социальные достижения
                donations_made = donations_made + ?,
                
                -- Временные метрики
                days_active = days_active + 1,
                last_activity = CURRENT_DATE
        """, (
            user_id,
            changes.get('war_stars_gained', 0),  # Участие в войне
            changes.get('gold_farmed', 0),
            changes.get('elixir_farmed', 0), 
            changes.get('dark_elixir_farmed', 0),
            changes.get('buildings_destroyed', 0),
            changes.get('attacks_won', 0),
            changes.get('defenses_won', 0),
            changes.get('donations_made', 0)
        ))
    
    async def _check_new_achievements(self, user_id: int) -> List[Dict]:
        """Проверка и начисление новых достижений"""
        
        # Получаем текущую статистику
        stats = await self.db.fetch_one("""
            SELECT * FROM user_activity_stats WHERE user_id = ?
        """, (user_id,))
        
        if not stats:
            return []
            
        # Получаем незаработанные достижения
        available_achievements = await self.db.fetch_all("""
            SELECT a.* FROM achievements a
            WHERE a.is_active = TRUE 
            AND NOT EXISTS (
                SELECT 1 FROM user_achievements ua 
                WHERE ua.user_id = ? AND ua.achievement_id = a.id
            )
        """, (user_id,))
        
        new_achievements = []
        
        for achievement in available_achievements:
            if await self._check_achievement_criteria(stats, achievement):
                await self._award_achievement(user_id, achievement)
                new_achievements.append(achievement)
                
        return new_achievements
    
    async def _check_achievement_criteria(self, stats: Dict, achievement: Dict) -> bool:
        """Проверка критериев достижения"""
        
        requirement_type = achievement['requirement_type'] 
        requirement_value = achievement['requirement_value']
        
        criteria_map = {
            # Ресурсные достижения
            'gold_farmed': stats.get('total_gold_farmed', 0),
            'elixir_farmed': stats.get('total_elixir_farmed', 0),
            'dark_elixir_farmed': stats.get('total_dark_elixir_farmed', 0),
            
            # Боевые достижения
            'buildings_destroyed': stats.get('buildings_destroyed', 0),
            'attacks_won': stats.get('successful_attacks', 0),
            'defenses_won': stats.get('successful_defenses', 0),
            'wars_participated': stats.get('wars_participated', 0),
            
            # Социальные достижения  
            'donations_made': stats.get('donations_made', 0),
            'days_active': stats.get('days_active', 0),
            
            # Интеграция с чат активностью (из другой таблицы)
            'messages_count': await self._get_chat_messages_count(stats['user_id']),
            'help_count': await self._get_help_count(stats['user_id'])
        }
        
        current_value = criteria_map.get(requirement_type, 0)
        return current_value >= requirement_value
```

---

## ⚙️ Система cron задач и автоматизации

### Ежедневные задачи
```python
# Cron задачи для системы метрик
DAILY_TASKS = {
    # Основной сбор данных - каждый день в 02:00 UTC
    "0 2 * * *": "collect_all_player_snapshots",
    
    # Расчет изменений - через час после сбора
    "0 3 * * *": "calculate_daily_changes_batch", 
    
    # Обработка достижений - еще через час
    "0 4 * * *": "process_daily_achievements_batch",
    
    # Очистка старых данных - раз в день в 05:00
    "0 5 * * *": "cleanup_old_snapshots"
}

WEEKLY_TASKS = {
    # Еженедельные агрегации - понедельник в 06:00
    "0 6 * * 1": "calculate_weekly_stats_all",
    
    # Месячные агрегации - первое число месяца в 07:00  
    "0 7 1 * *": "calculate_monthly_stats_all"
}

class MetricsCronManager:
    def __init__(self, metrics_collector, calculator, achievement_processor):
        self.collector = metrics_collector
        self.calculator = calculator
        self.achievements = achievement_processor
        
    async def collect_all_player_snapshots(self) -> None:
        """Ежедневный сбор всех снапшотов"""
        
        start_time = time.time()
        results = await self.collector.collect_daily_snapshots()
        
        # Логирование результатов
        self.logger.info(f"""
        Daily snapshots collection completed:
        - Success: {results['success']} players
        - Failed: {results['failed']} players  
        - Duration: {time.time() - start_time:.2f} seconds
        - Errors: {len(results['errors'])} 
        """)
        
        # Уведомление о критических ошибках
        if results['failed'] > results['success'] * 0.1:  # Более 10% ошибок
            await self._send_admin_alert(
                "High failure rate in daily snapshots collection", 
                results
            )
    
    async def calculate_daily_changes_batch(self) -> None:
        """Batch расчет изменений за день"""
        
        # Получаем игроков, для которых есть свежие снапшоты
        players_to_process = await self.db.fetch_all("""
            SELECT DISTINCT player_tag FROM daily_player_snapshots 
            WHERE snapshot_date = CURRENT_DATE 
            AND NOT EXISTS (
                SELECT 1 FROM player_daily_changes 
                WHERE player_tag = daily_player_snapshots.player_tag 
                AND change_date = CURRENT_DATE
            )
        """)
        
        processed = 0
        errors = 0
        
        for player in players_to_process:
            try:
                await self.calculator.calculate_daily_changes(player['player_tag'])
                processed += 1
            except Exception as e:
                self.logger.error(f"Failed to calculate changes for {player['player_tag']}: {e}")
                errors += 1
        
        self.logger.info(f"Daily changes calculated: {processed} success, {errors} errors")
    
    async def process_daily_achievements_batch(self) -> None:
        """Batch обработка достижений"""
        
        # Получаем изменения за сегодня
        todays_changes = await self.db.fetch_all("""
            SELECT player_tag, * FROM player_daily_changes 
            WHERE change_date = CURRENT_DATE
        """)
        
        total_new_achievements = 0
        
        for change_record in todays_changes:
            try:
                new_achievements = await self.achievements.process_daily_achievements(
                    change_record['player_tag'], 
                    dict(change_record)
                )
                total_new_achievements += len(new_achievements)
                
                # Отправка уведомлений о новых достижениях  
                for achievement in new_achievements:
                    await self._send_achievement_notification(
                        change_record['player_tag'], 
                        achievement
                    )
                    
            except Exception as e:
                self.logger.error(f"Failed to process achievements for {change_record['player_tag']}: {e}")
        
        self.logger.info(f"Processed daily achievements: {total_new_achievements} new achievements earned")
```

---

## 📈 Примеры команд и отображения статистики

### Команды для пользователей

#### `/my_progress [период]` - Прогресс игрока
```python
async def cmd_my_progress(message: Message):
    """Показать прогресс за период"""
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else ['week']
    period = args[0] if args[0] in ['day', 'week', 'month'] else 'week'
    
    # Получаем привязанного игрока
    player_tag = await get_user_player_tag(message.from_user.id)
    if not player_tag:
        await message.reply("У вас нет привязанного игрока. Создайте паспорт: /create_passport")
        return
        
    # Получаем данные прогресса
    if period == 'day':
        progress_data = await get_daily_progress(player_tag)
    elif period == 'week':
        progress_data = await get_weekly_progress(player_tag) 
    else:
        progress_data = await get_monthly_progress(player_tag)
    
    if not progress_data:
        await message.reply(f"Нет данных прогресса за {period}")
        return
        
    # Форматируем сообщение
    text = f"""
📊 **Прогресс за {PERIOD_NAMES[period]}**
👤 **{progress_data['player_name']}** ✅

🏆 **Кубки:**
• Изменение: {format_change(progress_data['trophy_change'])}
• Текущие: {progress_data['current_trophies']:,}

💰 **Ресурсы нафармлено:**
• 🥇 Золото: {format_number(progress_data['gold_farmed'])}
• ⚗️ Эликсир: {format_number(progress_data['elixir_farmed'])}
• 🖤 Темный эликсир: {format_number(progress_data['dark_elixir_farmed'])}
• 🏛️ Capital Gold: {format_number(progress_data['capital_gold_earned'])}

⚔️ **Боевая активность:**
• Атаки выиграно: {progress_data['attacks_won']}
• Защиты успешно: {progress_data['defenses_won']} 
• Звезды в войнах: +{progress_data['war_stars_gained']}
• Зданий разрушено: {progress_data['buildings_destroyed']}

🎁 **Социальная активность:**
• Донатов сделано: {progress_data['donations_made']}
• Донатов получено: {progress_data['donations_got']}
• Соотношение: {progress_data['donation_ratio']:.2f}

📈 **Эффективность:**
• Золота за атаку: {progress_data.get('gold_per_attack', 0):,.0f}
• Активных дней: {progress_data['days_active']}/{period_total_days(period)}
"""
    
    # Добавляем достижения за период если есть
    if progress_data.get('achievements_earned'):
        text += f"\n🏆 **Новые достижения: {len(progress_data['achievements_earned'])}**\n"
        for ach in progress_data['achievements_earned']:
            text += f"• {ach['icon']} {ach['title']}\n"
    
    await message.reply(text, parse_mode='Markdown')
```

#### `/my_resources` - Детальная статистика ресурсов  
```python
async def cmd_my_resources(message: Message):
    """Детальная статистика по ресурсам"""
    
    player_tag = await get_user_player_tag(message.from_user.id)
    if not player_tag:
        await message.reply("Создайте паспорт для просмотра статистики: /create_passport")
        return
    
    # Получаем статистику за разные периоды
    daily_resources = await get_resource_stats(player_tag, days=1)
    weekly_resources = await get_resource_stats(player_tag, days=7) 
    monthly_resources = await get_resource_stats(player_tag, days=30)
    
    text = f"""
💰 **Статистика ресурсов**
👤 **{daily_resources['player_name']}** ✅

📊 **За последние периоды:**

**🔥 Сегодня:**
• 🥇 Золото: {format_number(daily_resources['total_gold'])}
• ⚗️ Эликсир: {format_number(daily_resources['total_elixir'])}  
• 🖤 Темный эликсир: {format_number(daily_resources['total_dark_elixir'])}
• Атак: {daily_resources['total_attacks']}

**📅 За неделю:**
• 🥇 Золото: {format_number(weekly_resources['total_gold'])} (среднее: {format_number(weekly_resources['total_gold']/7)}/день)
• ⚗️ Эликсир: {format_number(weekly_resources['total_elixir'])} (среднее: {format_number(weekly_resources['total_elixir']/7)}/день)
• 🖤 Темный эликсир: {format_number(weekly_resources['total_dark_elixir'])} (среднее: {format_number(weekly_resources['total_dark_elixir']/7)}/день)  
• Атак: {weekly_resources['total_attacks']} (среднее: {weekly_resources['total_attacks']/7:.1f}/день)

**📅 За месяц:**
• 🥇 Золото: {format_number(monthly_resources['total_gold'])}
• ⚗️ Эликсир: {format_number(monthly_resources['total_elixir'])}
• 🖤 Темный эликсир: {format_number(monthly_resources['total_dark_elixir'])}
• Атак: {monthly_resources['total_attacks']}

⚡ **Эффективность за неделю:**
• Золота за атаку: {weekly_resources['efficiency']['gold_per_attack']:,.0f}
• Эликсира за атаку: {weekly_resources['efficiency']['elixir_per_attack']:,.0f}
• ТЭ за атаку: {weekly_resources['efficiency']['de_per_attack']:,.0f}
• Активных дней: {weekly_resources['active_days']}/7

🎯 **Прогресс достижений:**
• Gold Grab: {format_achievement_progress('gold_grab', player_tag)}
• Elixir Escapade: {format_achievement_progress('elixir_escapade', player_tag)}
• Heroic Heist: {format_achievement_progress('heroic_heist', player_tag)}
"""

    await message.reply(text, parse_mode='Markdown')
```

---

## 🔧 Оптимизация и масштабирование

### Performance оптимизации

#### Batch processing и кеширование
```python
class OptimizedMetricsCollector:
    def __init__(self, coc_api, db_connection, redis_client):
        self.coc_api = coc_api
        self.db = db_connection
        self.redis = redis_client
        
    async def collect_batch_optimized(self, player_tags: List[str]) -> Dict:
        """Оптимизированный batch сбор с кешированием"""
        
        # Проверяем кеш для недавно обновленных игроков  
        cached_results = await self._check_cached_data(player_tags)
        
        # Оставляем только тех, кого нужно обновить
        players_to_fetch = [
            tag for tag in player_tags 
            if tag not in cached_results
        ]
        
        results = cached_results.copy()
        
        if players_to_fetch:
            # Используем connection pooling для API запросов
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=20),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                
                # Batch запросы с rate limiting
                batch_results = await self._fetch_players_batch(
                    session, players_to_fetch
                )
                results.update(batch_results)
                
                # Кешируем результаты
                await self._cache_results(batch_results)
        
        return results
    
    async def _check_cached_data(self, player_tags: List[str]) -> Dict:
        """Проверка кешированных данных"""
        
        cached = {}
        
        # Batch получение из Redis
        cache_keys = [f"player_snapshot:{tag}" for tag in player_tags]
        cached_values = await self.redis.mget(cache_keys)
        
        for i, value in enumerate(cached_values):
            if value:
                player_tag = player_tags[i]
                cached_data = json.loads(value)
                
                # Проверяем возраст данных (максимум 23 часа)
                if self._is_cache_valid(cached_data['timestamp']):
                    cached[player_tag] = cached_data['snapshot']
                    
        return cached
    
    async def _fetch_players_batch(self, session: aiohttp.ClientSession, 
                                 player_tags: List[str]) -> Dict:
        """Batch запросы к API с rate limiting"""
        
        results = {}
        
        # Rate limiting: максимум 10 запросов в секунду
        semaphore = asyncio.Semaphore(10)
        
        async def fetch_single_player(tag: str):
            async with semaphore:
                try:
                    player_data = await self.coc_api.get_player(tag, session=session)
                    if player_data:
                        results[tag] = self._extract_snapshot_data(player_data)
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    self.logger.error(f"Failed to fetch {tag}: {e}")
                    
        # Параллельное выполнение с ограничением
        await asyncio.gather(
            *[fetch_single_player(tag) for tag in player_tags],
            return_exceptions=True
        )
        
        return results
```

#### Database оптимизации
```sql
-- Партицирование таблицы снапшотов по месяцам
CREATE TABLE daily_player_snapshots_2025_10 
PARTITION OF daily_player_snapshots
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE daily_player_snapshots_2025_11 
PARTITION OF daily_player_snapshots  
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- Индексы для быстрых запросов
CREATE INDEX CONCURRENTLY idx_snapshots_player_recent 
ON daily_player_snapshots (player_tag, snapshot_date DESC) 
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '30 days';

CREATE INDEX CONCURRENTLY idx_changes_trophy_range
ON player_daily_changes (change_date, trophy_change)
WHERE trophy_change != 0;

-- Материализованные представления для агрегатов
CREATE MATERIALIZED VIEW player_monthly_aggregates AS
SELECT 
    player_tag,
    DATE_TRUNC('month', change_date) as month,
    SUM(trophy_change) as monthly_trophy_change,
    SUM(gold_farmed) as monthly_gold,
    SUM(elixir_farmed) as monthly_elixir,
    SUM(dark_elixir_farmed) as monthly_dark_elixir,
    COUNT(*) as active_days
FROM player_daily_changes
GROUP BY player_tag, DATE_TRUNC('month', change_date);

-- Автообновление материализованных представлений
CREATE OR REPLACE FUNCTION refresh_monthly_aggregates()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY player_monthly_aggregates;
END;
$$ LANGUAGE plpgsql;

-- Cron задача для обновления (выполняется ежедневно)
SELECT cron.schedule('refresh-aggregates', '0 1 * * *', 'SELECT refresh_monthly_aggregates();');
```

---

## 🎯 Интеграция с MVP паспортов

### Приоритетные метрики для первой версии

**Критично для MVP:**
1. ✅ **Базовые снапшоты** - кубки, уровень, донаты
2. ✅ **Простые изменения** - изменение кубков, донатов за день
3. ✅ **Ресурсные достижения** - отслеживание через Gold Grab, Elixir Escapade
4. ✅ **Интеграция с достижениями паспорта** - автоматическое начисление

**Можно отложить:**
- 🔄 Сложная аналитика эффективности
- 🔄 Материализованные представления  
- 🔄 Детальное отслеживание всех достижений CoC
- 🔄 Расширенные периодические отчеты

### Упрощенная схема для стадии MVP

```sql
-- Минимальная таблица для MVP
CREATE TABLE player_daily_snapshots_mvp (
    player_tag VARCHAR(15) NOT NULL,
    snapshot_date DATE NOT NULL,
    
    -- Основные метрики
    trophies INTEGER NOT NULL,
    donations_given INTEGER DEFAULT 0,
    donations_received INTEGER DEFAULT 0,
    war_stars INTEGER DEFAULT 0,
    
    -- Ключевые достижения (JSON)
    key_achievements JSON DEFAULT '{}', -- Только Gold Grab, Elixir Escapade, Heroic Heist
    
    PRIMARY KEY (player_tag, snapshot_date),
    INDEX idx_recent (snapshot_date DESC)
);

-- Упрощенные изменения
CREATE TABLE player_daily_changes_mvp (
    player_tag VARCHAR(15) NOT NULL,
    change_date DATE NOT NULL,
    
    trophy_change INTEGER DEFAULT 0,
    donations_change INTEGER DEFAULT 0,
    war_stars_change INTEGER DEFAULT 0,
    
    -- Ресурсы (основные)
    gold_farmed BIGINT DEFAULT 0,
    elixir_farmed BIGINT DEFAULT 0,
    dark_elixir_farmed INTEGER DEFAULT 0,
    
    PRIMARY KEY (player_tag, change_date)
);
```

Система метрик станет мощным фундаментом для точного отслеживания прогресса игроков и автоматического начисления достижений, создавая замкнутый цикл мотивации и вознаграждений в системе паспортов! 🚀