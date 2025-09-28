"""
Сервис для управления системой достижений
Фаза 6: Центральный сервис обработки достижений и прогресса
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import json
import sqlite3

from ..models.achievement_models import (
    Achievement, UserAchievementProgress, UserProfile, LeaderboardEntry,
    AchievementStatus, AchievementCategory, AchievementDifficulty,
    AchievementRequirement, RewardType, SYSTEM_ACHIEVEMENTS
)
from ..services.passport_database_service import PassportDatabaseService
from ..services.clan_database_service import ClanDatabaseService
from ..services.user_context_service import UserContextService

logger = logging.getLogger(__name__)


class AchievementService:
    """
    Центральный сервис для управления достижениями и прогрессом пользователей
    """
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.passport_service = PassportDatabaseService()
        self.clan_service = ClanDatabaseService()
        self.context_service = UserContextService()
        
        # Кэш достижений для быстрого доступа
        self._achievements_cache: Dict[str, Achievement] = {}
        self._user_progress_cache: Dict[str, Dict[str, UserAchievementProgress]] = {}
        self._user_profiles_cache: Dict[str, UserProfile] = {}
        
        # Инициализируем базовые достижения
        asyncio.create_task(self._initialize_system_achievements())
    
    async def initialize_database(self):
        """Инициализация таблиц базы данных для достижений"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица достижений
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS achievements (
                        achievement_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        category TEXT NOT NULL,
                        difficulty TEXT NOT NULL,
                        requirements TEXT NOT NULL,  -- JSON
                        rewards TEXT NOT NULL,      -- JSON
                        icon TEXT DEFAULT '🏆',
                        hidden BOOLEAN DEFAULT FALSE,
                        prerequisites TEXT DEFAULT '[]',  -- JSON список ID
                        max_progress INTEGER DEFAULT 100,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Таблица прогресса пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_achievement_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        achievement_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        progress_percentage REAL DEFAULT 0.0,
                        started_date TIMESTAMP,
                        completed_date TIMESTAMP,
                        claimed_date TIMESTAMP,
                        current_values TEXT DEFAULT '{}',  -- JSON
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (achievement_id) REFERENCES achievements (achievement_id),
                        UNIQUE(user_id, chat_id, achievement_id)
                    )
                """)
                
                # Таблица профилей пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        total_points INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        experience_points INTEGER DEFAULT 0,
                        titles TEXT DEFAULT '[]',      -- JSON список
                        badges TEXT DEFAULT '[]',      -- JSON список
                        privileges TEXT DEFAULT '[]',  -- JSON список
                        achievements_completed INTEGER DEFAULT 0,
                        achievements_claimed INTEGER DEFAULT 0,
                        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_achievement_date TIMESTAMP,
                        PRIMARY KEY (user_id, chat_id)
                    )
                """)
                
                # Таблица истории наград
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reward_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        achievement_id TEXT NOT NULL,
                        reward_type TEXT NOT NULL,
                        reward_id TEXT NOT NULL,
                        reward_name TEXT NOT NULL,
                        reward_value TEXT,
                        granted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Таблица событий для отслеживания прогресса
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS achievement_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        event_type TEXT NOT NULL,
                        event_data TEXT NOT NULL,  -- JSON
                        event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Создаем индексы для оптимизации
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_progress ON user_achievement_progress(user_id, chat_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_achievement_status ON user_achievement_progress(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON achievement_events(user_id, chat_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON achievement_events(event_type)")
                
                conn.commit()
                logger.info("База данных достижений успешно инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных достижений: {e}")
            raise
    
    async def _initialize_system_achievements(self):
        """Инициализация системных достижений"""
        
        try:
            for achievement_id, achievement in SYSTEM_ACHIEVEMENTS.items():
                await self.create_or_update_achievement(achievement)
            
            logger.info(f"Инициализировано {len(SYSTEM_ACHIEVEMENTS)} системных достижений")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации системных достижений: {e}")
    
    # Управление достижениями
    
    async def create_or_update_achievement(self, achievement: Achievement) -> bool:
        """Создание или обновление достижения"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO achievements (
                        achievement_id, name, description, category, difficulty,
                        requirements, rewards, icon, hidden, prerequisites, max_progress
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    achievement.achievement_id,
                    achievement.name,
                    achievement.description,
                    achievement.category.value,
                    achievement.difficulty.value,
                    json.dumps([req.to_dict() for req in achievement.requirements]),
                    json.dumps([reward.to_dict() for reward in achievement.rewards]),
                    achievement.icon,
                    achievement.hidden,
                    json.dumps(achievement.prerequisites),
                    achievement.max_progress
                ))
                
                conn.commit()
                
                # Обновляем кэш
                self._achievements_cache[achievement.achievement_id] = achievement
                
                logger.info(f"Достижение {achievement.achievement_id} создано/обновлено")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка создания/обновления достижения {achievement.achievement_id}: {e}")
            return False
    
    async def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """Получение достижения по ID"""
        
        # Проверяем кэш
        if achievement_id in self._achievements_cache:
            return self._achievements_cache[achievement_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT achievement_id, name, description, category, difficulty,
                           requirements, rewards, icon, hidden, prerequisites, max_progress
                    FROM achievements WHERE achievement_id = ?
                """, (achievement_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Парсим данные
                requirements = [AchievementRequirement.from_dict(req) 
                              for req in json.loads(row[5])]
                rewards = [AchievementReward.from_dict(reward) 
                          for reward in json.loads(row[6])]
                
                achievement = Achievement(
                    achievement_id=row[0],
                    name=row[1],
                    description=row[2],
                    category=AchievementCategory(row[3]),
                    difficulty=AchievementDifficulty(row[4]),
                    requirements=requirements,
                    rewards=rewards,
                    icon=row[7],
                    hidden=bool(row[8]),
                    prerequisites=json.loads(row[9]),
                    max_progress=row[10]
                )
                
                # Кэшируем
                self._achievements_cache[achievement_id] = achievement
                
                return achievement
                
        except Exception as e:
            logger.error(f"Ошибка получения достижения {achievement_id}: {e}")
            return None
    
    async def get_all_achievements(self, category: Optional[AchievementCategory] = None) -> List[Achievement]:
        """Получение всех достижений (с фильтрацией по категории)"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT achievement_id, name, description, category, difficulty,
                           requirements, rewards, icon, hidden, prerequisites, max_progress
                    FROM achievements
                """
                params = []
                
                if category:
                    query += " WHERE category = ?"
                    params.append(category.value)
                
                query += " ORDER BY difficulty, name"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                achievements = []
                for row in rows:
                    try:
                        requirements = [AchievementRequirement.from_dict(req) 
                                      for req in json.loads(row[5])]
                        rewards = [AchievementReward.from_dict(reward) 
                                  for reward in json.loads(row[6])]
                        
                        achievement = Achievement(
                            achievement_id=row[0],
                            name=row[1],
                            description=row[2],
                            category=AchievementCategory(row[3]),
                            difficulty=AchievementDifficulty(row[4]),
                            requirements=requirements,
                            rewards=rewards,
                            icon=row[7],
                            hidden=bool(row[8]),
                            prerequisites=json.loads(row[9]),
                            max_progress=row[10]
                        )
                        
                        achievements.append(achievement)
                        
                        # Кэшируем
                        self._achievements_cache[achievement.achievement_id] = achievement
                        
                    except Exception as e:
                        logger.error(f"Ошибка парсинга достижения {row[0]}: {e}")
                        continue
                
                return achievements
                
        except Exception as e:
            logger.error(f"Ошибка получения списка достижений: {e}")
            return []
    
    # Управление прогрессом пользователей
    
    async def get_user_progress(self, user_id: int, chat_id: int, achievement_id: str) -> Optional[UserAchievementProgress]:
        """Получение прогресса пользователя по конкретному достижению"""
        
        cache_key = f"{user_id}_{chat_id}"
        
        # Проверяем кэш
        if (cache_key in self._user_progress_cache and 
            achievement_id in self._user_progress_cache[cache_key]):
            return self._user_progress_cache[cache_key][achievement_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id, chat_id, achievement_id, status, progress_percentage,
                           started_date, completed_date, claimed_date, current_values
                    FROM user_achievement_progress 
                    WHERE user_id = ? AND chat_id = ? AND achievement_id = ?
                """, (user_id, chat_id, achievement_id))
                
                row = cursor.fetchone()
                if not row:
                    # Создаем новый прогресс для пользователя
                    progress = UserAchievementProgress(
                        user_id=user_id,
                        chat_id=chat_id,
                        achievement_id=achievement_id,
                        status=AchievementStatus.LOCKED
                    )
                    await self._create_user_progress(progress)
                    return progress
                
                # Парсим существующий прогресс
                progress = UserAchievementProgress(
                    user_id=row[0],
                    chat_id=row[1],
                    achievement_id=row[2],
                    status=AchievementStatus(row[3]),
                    progress_percentage=row[4],
                    started_date=datetime.fromisoformat(row[5]) if row[5] else None,
                    completed_date=datetime.fromisoformat(row[6]) if row[6] else None,
                    claimed_date=datetime.fromisoformat(row[7]) if row[7] else None,
                    current_values=json.loads(row[8]) if row[8] else {}
                )
                
                # Кэшируем
                if cache_key not in self._user_progress_cache:
                    self._user_progress_cache[cache_key] = {}
                self._user_progress_cache[cache_key][achievement_id] = progress
                
                return progress
                
        except Exception as e:
            logger.error(f"Ошибка получения прогресса пользователя {user_id} для достижения {achievement_id}: {e}")
            return None
    
    async def get_all_user_progress(self, user_id: int, chat_id: int) -> Dict[str, UserAchievementProgress]:
        """Получение всего прогресса пользователя"""
        
        cache_key = f"{user_id}_{chat_id}"
        
        # Проверяем кэш
        if cache_key in self._user_progress_cache:
            return self._user_progress_cache[cache_key]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id, chat_id, achievement_id, status, progress_percentage,
                           started_date, completed_date, claimed_date, current_values
                    FROM user_achievement_progress 
                    WHERE user_id = ? AND chat_id = ?
                """, (user_id, chat_id))
                
                rows = cursor.fetchall()
                progress_dict = {}
                
                for row in rows:
                    try:
                        progress = UserAchievementProgress(
                            user_id=row[0],
                            chat_id=row[1],
                            achievement_id=row[2],
                            status=AchievementStatus(row[3]),
                            progress_percentage=row[4],
                            started_date=datetime.fromisoformat(row[5]) if row[5] else None,
                            completed_date=datetime.fromisoformat(row[6]) if row[6] else None,
                            claimed_date=datetime.fromisoformat(row[7]) if row[7] else None,
                            current_values=json.loads(row[8]) if row[8] else {}
                        )
                        
                        progress_dict[row[2]] = progress
                        
                    except Exception as e:
                        logger.error(f"Ошибка парсинга прогресса для достижения {row[2]}: {e}")
                        continue
                
                # Кэшируем
                self._user_progress_cache[cache_key] = progress_dict
                
                return progress_dict
                
        except Exception as e:
            logger.error(f"Ошибка получения всего прогресса пользователя {user_id}: {e}")
            return {}
    
    async def update_user_progress(
        self, 
        user_id: int, 
        chat_id: int, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> List[Achievement]:
        """
        Обновление прогресса пользователя на основе события
        Возвращает список завершенных достижений
        """
        
        completed_achievements = []
        
        try:
            # Записываем событие
            await self._log_achievement_event(user_id, chat_id, event_type, event_data)
            
            # Получаем все достижения, которые могут быть затронуты этим событием
            all_achievements = await self.get_all_achievements()
            
            for achievement in all_achievements:
                # Проверяем, влияет ли событие на это достижение
                if await self._event_affects_achievement(event_type, achievement):
                    progress = await self.get_user_progress(user_id, chat_id, achievement.achievement_id)
                    
                    if progress and progress.status in [AchievementStatus.LOCKED, AchievementStatus.IN_PROGRESS]:
                        # Обновляем прогресс
                        updated = await self._update_achievement_progress(
                            progress, achievement, event_type, event_data
                        )
                        
                        if updated:
                            await self._save_user_progress(progress)
                            
                            # Проверяем завершение
                            if await self._check_achievement_completion(progress, achievement):
                                progress.complete_achievement()
                                await self._save_user_progress(progress)
                                completed_achievements.append(achievement)
                                
                                # Уведомляем о завершении
                                await self._notify_achievement_completed(user_id, chat_id, achievement)
            
            return completed_achievements
            
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса пользователя {user_id}: {e}")
            return []
    
    async def claim_achievement_rewards(
        self, 
        user_id: int, 
        chat_id: int, 
        achievement_id: str
    ) -> bool:
        """Получение наград за достижение"""
        
        try:
            progress = await self.get_user_progress(user_id, chat_id, achievement_id)
            achievement = await self.get_achievement(achievement_id)
            
            if not progress or not achievement:
                return False
            
            if progress.status != AchievementStatus.COMPLETED:
                logger.warning(f"Попытка получить награды за незавершенное достижение {achievement_id}")
                return False
            
            # Выдаем награды
            user_profile = await self.get_user_profile(user_id, chat_id)
            
            for reward in achievement.rewards:
                await self._grant_reward(user_profile, reward, achievement_id)
            
            # Обновляем прогресс
            progress.claim_rewards()
            await self._save_user_progress(progress)
            
            # Обновляем профиль
            user_profile.achievements_claimed += 1
            user_profile.last_achievement_date = datetime.now()
            await self._save_user_profile(user_profile)
            
            logger.info(f"Награды за достижение {achievement_id} выданы пользователю {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка выдачи наград за достижение {achievement_id} пользователю {user_id}: {e}")
            return False
    
    # Управление профилями пользователей
    
    async def get_user_profile(self, user_id: int, chat_id: int) -> UserProfile:
        """Получение профиля пользователя"""
        
        cache_key = f"{user_id}_{chat_id}"
        
        # Проверяем кэш
        if cache_key in self._user_profiles_cache:
            return self._user_profiles_cache[cache_key]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id, chat_id, total_points, level, experience_points,
                           titles, badges, privileges, achievements_completed, achievements_claimed,
                           join_date, last_achievement_date
                    FROM user_profiles WHERE user_id = ? AND chat_id = ?
                """, (user_id, chat_id))
                
                row = cursor.fetchone()
                
                if row:
                    profile = UserProfile(
                        user_id=row[0],
                        chat_id=row[1],
                        total_points=row[2],
                        level=row[3],
                        experience_points=row[4],
                        titles=set(json.loads(row[5])),
                        badges=set(json.loads(row[6])),
                        privileges=set(json.loads(row[7])),
                        achievements_completed=row[8],
                        achievements_claimed=row[9],
                        join_date=datetime.fromisoformat(row[10]),
                        last_achievement_date=datetime.fromisoformat(row[11]) if row[11] else None
                    )
                else:
                    # Создаем новый профиль
                    profile = UserProfile(user_id=user_id, chat_id=chat_id)
                    await self._save_user_profile(profile)
                
                # Кэшируем
                self._user_profiles_cache[cache_key] = profile
                
                return profile
                
        except Exception as e:
            logger.error(f"Ошибка получения профиля пользователя {user_id}: {e}")
            return UserProfile(user_id=user_id, chat_id=chat_id)
    
    # Вспомогательные методы
    
    async def _create_user_progress(self, progress: UserAchievementProgress):
        """Создание нового прогресса пользователя"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO user_achievement_progress (
                        user_id, chat_id, achievement_id, status, progress_percentage,
                        started_date, completed_date, claimed_date, current_values
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    progress.user_id,
                    progress.chat_id,
                    progress.achievement_id,
                    progress.status.value,
                    progress.progress_percentage,
                    progress.started_date.isoformat() if progress.started_date else None,
                    progress.completed_date.isoformat() if progress.completed_date else None,
                    progress.claimed_date.isoformat() if progress.claimed_date else None,
                    json.dumps(progress.current_values)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка создания прогресса пользователя: {e}")
    
    async def _save_user_progress(self, progress: UserAchievementProgress):
        """Сохранение прогресса пользователя"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE user_achievement_progress SET
                        status = ?, progress_percentage = ?, started_date = ?,
                        completed_date = ?, claimed_date = ?, current_values = ?,
                        updated_date = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND chat_id = ? AND achievement_id = ?
                """, (
                    progress.status.value,
                    progress.progress_percentage,
                    progress.started_date.isoformat() if progress.started_date else None,
                    progress.completed_date.isoformat() if progress.completed_date else None,
                    progress.claimed_date.isoformat() if progress.claimed_date else None,
                    json.dumps(progress.current_values),
                    progress.user_id,
                    progress.chat_id,
                    progress.achievement_id
                ))
                
                conn.commit()
                
                # Обновляем кэш
                cache_key = f"{progress.user_id}_{progress.chat_id}"
                if cache_key in self._user_progress_cache:
                    self._user_progress_cache[cache_key][progress.achievement_id] = progress
                
        except Exception as e:
            logger.error(f"Ошибка сохранения прогресса пользователя: {e}")
    
    async def _save_user_profile(self, profile: UserProfile):
        """Сохранение профиля пользователя"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO user_profiles (
                        user_id, chat_id, total_points, level, experience_points,
                        titles, badges, privileges, achievements_completed, achievements_claimed,
                        join_date, last_achievement_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.user_id,
                    profile.chat_id,
                    profile.total_points,
                    profile.level,
                    profile.experience_points,
                    json.dumps(list(profile.titles)),
                    json.dumps(list(profile.badges)),
                    json.dumps(list(profile.privileges)),
                    profile.achievements_completed,
                    profile.achievements_claimed,
                    profile.join_date.isoformat(),
                    profile.last_achievement_date.isoformat() if profile.last_achievement_date else None
                ))
                
                conn.commit()
                
                # Обновляем кэш
                cache_key = f"{profile.user_id}_{profile.chat_id}"
                self._user_profiles_cache[cache_key] = profile
                
        except Exception as e:
            logger.error(f"Ошибка сохранения профиля пользователя: {e}")
    
    async def _log_achievement_event(self, user_id: int, chat_id: int, event_type: str, event_data: Dict[str, Any]):
        """Логирование события для отслеживания прогресса"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO achievement_events (user_id, chat_id, event_type, event_data)
                    VALUES (?, ?, ?, ?)
                """, (user_id, chat_id, event_type, json.dumps(event_data)))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка логирования события {event_type}: {e}")
    
    async def _event_affects_achievement(self, event_type: str, achievement: Achievement) -> bool:
        """Проверка, влияет ли событие на достижение"""
        
        # Проверяем требования достижения на соответствие типу события
        for requirement in achievement.requirements:
            if self._event_matches_requirement(event_type, requirement.requirement_type):
                return True
        
        return False
    
    def _event_matches_requirement(self, event_type: str, requirement_type: str) -> bool:
        """Проверка соответствия события требованию"""
        
        event_mappings = {
            "message_sent": ["messages_count"],
            "passport_created": ["passport_created"],
            "player_bound": ["player_bound"],
            "clan_joined": ["clan_membership"],
            "player_verified": ["player_verified"],
            "trophies_updated": ["trophies"],
            "clan_war_participated": ["clan_wars_participated"],
            "donation_made": ["donations_made"]
        }
        
        return requirement_type in event_mappings.get(event_type, [])
    
    async def _update_achievement_progress(
        self,
        progress: UserAchievementProgress,
        achievement: Achievement,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Обновление прогресса достижения на основе события"""
        
        updated = False
        
        for requirement in achievement.requirements:
            if self._event_matches_requirement(event_type, requirement.requirement_type):
                # Обновляем текущее значение
                if requirement.requirement_type in event_data:
                    new_value = event_data[requirement.requirement_type]
                    old_value = progress.current_values.get(requirement.requirement_type, 0)
                    
                    # Для счетчиков увеличиваем значение
                    if requirement.requirement_type.endswith("_count"):
                        progress.current_values[requirement.requirement_type] = old_value + 1
                    else:
                        progress.current_values[requirement.requirement_type] = new_value
                    
                    updated = True
                    
                    # Если прогресс только начинается
                    if progress.status == AchievementStatus.LOCKED:
                        progress.status = AchievementStatus.IN_PROGRESS
                        progress.started_date = datetime.now()
        
        return updated
    
    async def _check_achievement_completion(
        self,
        progress: UserAchievementProgress,
        achievement: Achievement
    ) -> bool:
        """Проверка завершения достижения"""
        
        # Проверяем предварительные условия
        if achievement.prerequisites:
            for prereq_id in achievement.prerequisites:
                prereq_progress = await self.get_user_progress(
                    progress.user_id, progress.chat_id, prereq_id
                )
                if not prereq_progress or prereq_progress.status != AchievementStatus.COMPLETED:
                    return False
        
        # Проверяем все требования
        for requirement in achievement.requirements:
            current_value = progress.current_values.get(requirement.requirement_type, 0)
            requirement.current_value = current_value
            
            if not requirement.is_completed():
                return False
        
        # Обновляем счетчики в профиле
        user_profile = await self.get_user_profile(progress.user_id, progress.chat_id)
        user_profile.achievements_completed += 1
        await self._save_user_profile(user_profile)
        
        return True
    
    async def _grant_reward(self, profile: UserProfile, reward: AchievementReward, achievement_id: str):
        """Выдача награды пользователю"""
        
        try:
            if reward.reward_type == RewardType.POINTS:
                profile.add_points(reward.value or 0)
                
            elif reward.reward_type == RewardType.TITLE:
                profile.add_title(reward.reward_id)
                
            elif reward.reward_type == RewardType.BADGE:
                profile.add_badge(reward.reward_id)
                
            elif reward.reward_type == RewardType.PRIVILEGE:
                profile.add_privilege(reward.reward_id)
            
            # Записываем в историю наград
            await self._log_reward_granted(profile, reward, achievement_id)
            
        except Exception as e:
            logger.error(f"Ошибка выдачи награды {reward.reward_id}: {e}")
    
    async def _log_reward_granted(self, profile: UserProfile, reward: AchievementReward, achievement_id: str):
        """Логирование выданной награды"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO reward_history (
                        user_id, chat_id, achievement_id, reward_type, reward_id,
                        reward_name, reward_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.user_id,
                    profile.chat_id,
                    achievement_id,
                    reward.reward_type.value,
                    reward.reward_id,
                    reward.name,
                    str(reward.value) if reward.value else None
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка логирования награды: {e}")
    
    async def _notify_achievement_completed(self, user_id: int, chat_id: int, achievement: Achievement):
        """Уведомление о завершении достижения"""
        
        # Здесь можно добавить отправку уведомления пользователю
        logger.info(f"Пользователь {user_id} завершил достижение {achievement.name}")
    
    # Публичные методы для статистики
    
    async def get_user_achievements_summary(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """Получение сводки достижений пользователя"""
        
        try:
            profile = await self.get_user_profile(user_id, chat_id)
            all_progress = await self.get_all_user_progress(user_id, chat_id)
            
            # Подсчитываем статистику
            completed = len([p for p in all_progress.values() if p.status == AchievementStatus.COMPLETED])
            claimed = len([p for p in all_progress.values() if p.status == AchievementStatus.CLAIMED])
            in_progress = len([p for p in all_progress.values() if p.status == AchievementStatus.IN_PROGRESS])
            
            # Статистика по категориям
            category_stats = {}
            all_achievements = await self.get_all_achievements()
            
            for achievement in all_achievements:
                category = achievement.category.value
                if category not in category_stats:
                    category_stats[category] = {'total': 0, 'completed': 0}
                
                category_stats[category]['total'] += 1
                
                if achievement.achievement_id in all_progress:
                    progress = all_progress[achievement.achievement_id]
                    if progress.status in [AchievementStatus.COMPLETED, AchievementStatus.CLAIMED]:
                        category_stats[category]['completed'] += 1
            
            return {
                'profile': profile,
                'total_achievements': len(all_achievements),
                'completed_achievements': completed,
                'claimed_achievements': claimed,
                'in_progress_achievements': in_progress,
                'category_statistics': category_stats,
                'level_progress': profile.get_progress_to_next_level()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки достижений для пользователя {user_id}: {e}")
            return {}
    
    async def get_leaderboard(self, category: str = "total_points", limit: int = 10) -> List[LeaderboardEntry]:
        """Получение таблицы лидеров"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Определяем поле сортировки
                sort_field = "total_points"
                if category == "level":
                    sort_field = "level"
                elif category == "achievements":
                    sort_field = "achievements_completed"
                
                cursor.execute(f"""
                    SELECT user_id, chat_id, {sort_field}, level, total_points, achievements_completed
                    FROM user_profiles
                    ORDER BY {sort_field} DESC, level DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                leaderboard = []
                
                for rank, row in enumerate(rows, 1):
                    # Получаем дополнительную информацию о пользователе
                    # В реальном проекте здесь можно подтянуть username из другой таблицы
                    entry = LeaderboardEntry(
                        user_id=row[0],
                        chat_id=row[1],
                        username=f"User{row[0]}",  # Заглушка
                        display_name=f"User{row[0]}",  # Заглушка
                        score=row[2],
                        rank=rank,
                        category=category,
                        additional_info={
                            'level': row[3],
                            'total_points': row[4],
                            'achievements_completed': row[5]
                        }
                    )
                    leaderboard.append(entry)
                
                return leaderboard
                
        except Exception as e:
            logger.error(f"Ошибка получения таблицы лидеров: {e}")
            return []