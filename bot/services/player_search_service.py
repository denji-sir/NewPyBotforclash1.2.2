"""
Расширенная система поиска и выбора игроков для привязки
Фаза 4: Интеллектуальный поиск с автодополнением и рекомендациями
"""

from typing import List, Dict, Optional, Any, Tuple
import logging
import re
import asyncio
from datetime import datetime, timedelta

from ..services.coc_api_service import CoCAPIService
from ..services.clan_database_service import ClanDatabaseService
from ..services.passport_database_service import PassportDatabaseService
from ..models.passport_models import PlayerBinding
from ..utils.validators import validate_player_tag
from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)


class PlayerSearchService:
    """Сервис для расширенного поиска и выбора игроков"""
    
    def __init__(self):
        self.coc_api = CoCAPIService()
        self.clan_service = ClanDatabaseService()
        self.passport_service = PassportDatabaseService()
        self.cache = CacheManager()
        
        # Кэш для поисковых результатов
        self._search_cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(minutes=10)
    
    async def search_players_by_name(
        self, 
        name_query: str, 
        chat_id: int,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Поиск игроков по имени с интеллектуальными рекомендациями
        
        Args:
            name_query: Поисковый запрос (имя игрока)
            chat_id: ID чата для контекстуального поиска
            limit: Максимальное количество результатов
            
        Returns:
            Dict с результатами поиска и рекомендациями
        """
        try:
            # Нормализуем поисковый запрос
            normalized_query = self._normalize_search_query(name_query)
            cache_key = f"player_search_{chat_id}_{normalized_query}_{limit}"
            
            # Проверяем кэш
            if cache_key in self._search_cache:
                cached_result = self._search_cache[cache_key]
                if datetime.now() - cached_result['timestamp'] < self._cache_ttl:
                    return cached_result['data']
            
            # Получаем зарегистрированные кланы чата
            chat_clans = await self.clan_service.get_chat_clans(chat_id)
            
            results = {
                'success': True,
                'total_found': 0,
                'clan_members': [],
                'global_results': [],
                'recommendations': [],
                'search_query': name_query,
                'normalized_query': normalized_query
            }
            
            # Поиск среди участников зарегистрированных кланов
            if chat_clans:
                clan_results = await self._search_in_registered_clans(
                    normalized_query, chat_clans, limit
                )
                results['clan_members'] = clan_results
                results['total_found'] += len(clan_results)
            
            # Глобальный поиск через CoC API (если мало результатов из кланов)
            if len(results['clan_members']) < 5:
                global_results = await self._global_player_search(
                    normalized_query, limit - len(results['clan_members'])
                )
                results['global_results'] = global_results
                results['total_found'] += len(global_results)
            
            # Генерируем рекомендации
            results['recommendations'] = await self._generate_search_recommendations(
                normalized_query, chat_id, results
            )
            
            # Кэшируем результаты
            self._search_cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска игроков по имени: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_found': 0,
                'clan_members': [],
                'global_results': [],
                'recommendations': []
            }
    
    async def _search_in_registered_clans(
        self, 
        query: str, 
        clans: List[Dict], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Поиск игроков в зарегистрированных кланах чата"""
        results = []
        
        for clan in clans:
            try:
                # Получаем участников клана
                clan_members = await self.coc_api.get_clan_members(clan['clan_tag'])
                
                if not clan_members:
                    continue
                
                # Фильтруем по имени
                matching_members = []
                for member in clan_members:
                    member_name = member.get('name', '').lower()
                    if query.lower() in member_name:
                        matching_members.append({
                            'player_tag': member['tag'],
                            'player_name': member['name'],
                            'player_trophies': member.get('trophies', 0),
                            'player_role': member.get('role', 'member'),
                            'clan_name': clan['clan_name'],
                            'clan_tag': clan['clan_tag'],
                            'match_type': 'clan_member',
                            'match_score': self._calculate_match_score(
                                query, member['name'], member.get('trophies', 0)
                            ),
                            'is_registered_clan': True
                        })
                
                # Сортируем по релевантности
                matching_members.sort(key=lambda x: x['match_score'], reverse=True)
                results.extend(matching_members)
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"Ошибка поиска в клане {clan['clan_name']}: {e}")
                continue
        
        return results[:limit]
    
    async def _global_player_search(
        self, 
        query: str, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Глобальный поиск игроков через CoC API"""
        try:
            # Используем поиск по имени через CoC API
            # Примечание: CoC API не предоставляет прямой поиск по имени,
            # поэтому используем альтернативные методы
            
            results = []
            
            # Попытка найти игроков через популярные кланы
            popular_clans = await self._get_popular_clans_for_search()
            
            for clan_tag in popular_clans:
                try:
                    clan_members = await self.coc_api.get_clan_members(clan_tag)
                    
                    if not clan_members:
                        continue
                    
                    matching_members = []
                    for member in clan_members:
                        member_name = member.get('name', '').lower()
                        if query.lower() in member_name:
                            matching_members.append({
                                'player_tag': member['tag'],
                                'player_name': member['name'],
                                'player_trophies': member.get('trophies', 0),
                                'player_role': member.get('role', 'member'),
                                'clan_name': 'Unknown Clan',
                                'clan_tag': clan_tag,
                                'match_type': 'global_search',
                                'match_score': self._calculate_match_score(
                                    query, member['name'], member.get('trophies', 0)
                                ),
                                'is_registered_clan': False
                            })
                    
                    matching_members.sort(key=lambda x: x['match_score'], reverse=True)
                    results.extend(matching_members[:5])  # Максимум 5 из каждого клана
                    
                    if len(results) >= limit:
                        break
                        
                except Exception as e:
                    logger.error(f"Ошибка поиска в популярном клане {clan_tag}: {e}")
                    continue
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка глобального поиска: {e}")
            return []
    
    async def get_clan_members_with_filters(
        self,
        clan_tag: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Получение участников клана с возможностью фильтрации
        
        Args:
            clan_tag: Тег клана
            filters: Фильтры (min_trophies, max_trophies, roles, etc.)
            
        Returns:
            Dict с участниками и статистикой
        """
        try:
            # Получаем участников клана
            clan_members = await self.coc_api.get_clan_members(clan_tag)
            
            if not clan_members:
                return {
                    'success': False,
                    'error': 'Участники клана не найдены',
                    'members': [],
                    'total_members': 0,
                    'filtered_members': 0
                }
            
            # Применяем фильтры
            filtered_members = clan_members
            
            if filters:
                if 'min_trophies' in filters:
                    min_trophies = filters['min_trophies']
                    filtered_members = [
                        m for m in filtered_members 
                        if m.get('trophies', 0) >= min_trophies
                    ]
                
                if 'max_trophies' in filters:
                    max_trophies = filters['max_trophies']
                    filtered_members = [
                        m for m in filtered_members 
                        if m.get('trophies', 0) <= max_trophies
                    ]
                
                if 'roles' in filters and filters['roles']:
                    allowed_roles = filters['roles']
                    filtered_members = [
                        m for m in filtered_members 
                        if m.get('role', 'member') in allowed_roles
                    ]
                
                if 'name_filter' in filters and filters['name_filter']:
                    name_filter = filters['name_filter'].lower()
                    filtered_members = [
                        m for m in filtered_members 
                        if name_filter in m.get('name', '').lower()
                    ]
            
            # Сортируем по кубкам (по убыванию)
            filtered_members.sort(key=lambda x: x.get('trophies', 0), reverse=True)
            
            # Дополняем информацию о участниках
            enriched_members = []
            for member in filtered_members:
                enriched_member = {
                    'player_tag': member['tag'],
                    'player_name': member['name'],
                    'player_trophies': member.get('trophies', 0),
                    'player_role': member.get('role', 'member'),
                    'player_level': member.get('expLevel', 'N/A'),
                    'donations': member.get('donations', 0),
                    'donations_received': member.get('donationsReceived', 0),
                    'role_emoji': self._get_role_emoji(member.get('role', 'member')),
                    'is_online': False,  # CoC API не предоставляет информацию о статусе онлайн
                }
                enriched_members.append(enriched_member)
            
            return {
                'success': True,
                'members': enriched_members,
                'total_members': len(clan_members),
                'filtered_members': len(filtered_members),
                'filters_applied': filters or {},
                'statistics': self._calculate_clan_statistics(filtered_members)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения участников клана с фильтрами: {e}")
            return {
                'success': False,
                'error': str(e),
                'members': [],
                'total_members': 0,
                'filtered_members': 0
            }
    
    async def suggest_similar_players(
        self,
        partial_name: str,
        chat_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Предложение похожих игроков на основе частичного имени
        
        Args:
            partial_name: Частичное имя игрока
            chat_id: ID чата
            limit: Максимальное количество предложений
            
        Returns:
            Список предложений игроков
        """
        try:
            if len(partial_name) < 2:
                return []
            
            # Получаем зарегистрированные кланы
            chat_clans = await self.clan_service.get_chat_clans(chat_id)
            suggestions = []
            
            for clan in chat_clans:
                try:
                    clan_members = await self.coc_api.get_clan_members(clan['clan_tag'])
                    
                    if not clan_members:
                        continue
                    
                    for member in clan_members:
                        member_name = member.get('name', '')
                        
                        # Проверяем, начинается ли имя с введенного текста
                        if member_name.lower().startswith(partial_name.lower()):
                            similarity_score = len(partial_name) / len(member_name)
                        # Проверяем, содержится ли введенный текст в имени
                        elif partial_name.lower() in member_name.lower():
                            similarity_score = len(partial_name) / len(member_name) * 0.7
                        else:
                            continue
                        
                        suggestions.append({
                            'player_tag': member['tag'],
                            'player_name': member_name,
                            'player_trophies': member.get('trophies', 0),
                            'clan_name': clan['clan_name'],
                            'similarity_score': similarity_score,
                            'suggestion_type': 'name_match'
                        })
                        
                except Exception as e:
                    logger.error(f"Ошибка получения предложений из клана {clan['clan_name']}: {e}")
                    continue
            
            # Сортируем по релевантности
            suggestions.sort(key=lambda x: (x['similarity_score'], x['player_trophies']), reverse=True)
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка генерации предложений: {e}")
            return []
    
    async def validate_player_for_binding(
        self,
        player_tag: str,
        chat_id: int
    ) -> Dict[str, Any]:
        """
        Валидация игрока перед привязкой с детальной информацией
        
        Args:
            player_tag: Тег игрока
            chat_id: ID чата
            
        Returns:
            Результат валидации с рекомендациями
        """
        try:
            # Базовая валидация тега
            if not validate_player_tag(player_tag):
                return {
                    'success': False,
                    'error': 'Неверный формат тега игрока',
                    'recommendations': ['Тег должен начинаться с # и содержать 8-9 символов']
                }
            
            # Получаем информацию об игроке
            player_info = await self.coc_api.get_player(player_tag)
            
            if not player_info:
                return {
                    'success': False,
                    'error': 'Игрок не найден в Clash of Clans',
                    'recommendations': [
                        'Проверьте правильность тега',
                        'Убедитесь, что аккаунт активен'
                    ]
                }
            
            # Проверяем, не привязан ли уже этот игрок к другому паспорту
            existing_passport = await self.passport_service.get_passport_by_player_tag(
                player_tag=player_tag,
                chat_id=chat_id
            )
            
            if existing_passport:
                return {
                    'success': False,
                    'error': f'Игрок уже привязан к паспорту пользователя {existing_passport.display_name}',
                    'recommendations': [
                        'Выберите другого игрока',
                        'Обратитесь к администратору для решения конфликта'
                    ]
                }
            
            # Анализируем клан игрока
            clan_analysis = await self._analyze_player_clan(player_info, chat_id)
            
            # Генерируем детальную информацию
            validation_result = {
                'success': True,
                'player_info': {
                    'tag': player_info['tag'],
                    'name': player_info['name'],
                    'level': player_info.get('expLevel', 'N/A'),
                    'trophies': player_info.get('trophies', 0),
                    'best_trophies': player_info.get('bestTrophies', 0),
                    'clan': player_info.get('clan', {}),
                    'league': player_info.get('league', {}),
                },
                'clan_analysis': clan_analysis,
                'recommendations': [],
                'auto_verify': False
            }
            
            # Генерируем рекомендации
            if clan_analysis['is_registered_clan']:
                validation_result['auto_verify'] = True
                validation_result['recommendations'].append(
                    '✅ Игрок состоит в зарегистрированном клане - автоматическая верификация'
                )
            else:
                validation_result['recommendations'].append(
                    '⏳ Потребуется верификация администратором'
                )
            
            if player_info.get('trophies', 0) < 1000:
                validation_result['recommendations'].append(
                    '⚠️ У игрока мало кубков - убедитесь в правильности выбора'
                )
            
            if not player_info.get('clan'):
                validation_result['recommendations'].append(
                    '🏰 Игрок не состоит в клане'
                )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Ошибка валидации игрока: {e}")
            return {
                'success': False,
                'error': f'Ошибка при валидации: {str(e)}',
                'recommendations': ['Попробуйте еще раз позже']
            }
    
    def _normalize_search_query(self, query: str) -> str:
        """Нормализация поискового запроса"""
        # Удаляем лишние пробелы и приводим к нижнему регистру
        normalized = re.sub(r'\s+', ' ', query.strip().lower())
        
        # Удаляем специальные символы, кроме букв, цифр и пробелов
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized
    
    def _calculate_match_score(self, query: str, player_name: str, trophies: int) -> float:
        """Расчет релевантности совпадения"""
        query_lower = query.lower()
        name_lower = player_name.lower()
        
        # Базовый скор на основе совпадения имени
        if name_lower == query_lower:
            base_score = 100.0
        elif name_lower.startswith(query_lower):
            base_score = 80.0
        elif query_lower in name_lower:
            base_score = 60.0
        else:
            base_score = 20.0
        
        # Бонус за количество кубков (нормализуем от 0 до 20)
        trophy_bonus = min(trophies / 200, 20.0)
        
        return base_score + trophy_bonus
    
    def _get_role_emoji(self, role: str) -> str:
        """Получение emoji для роли в клане"""
        role_emojis = {
            'leader': '👑',
            'coLeader': '🔥',
            'elder': '⭐',
            'member': '👤'
        }
        return role_emojis.get(role, '👤')
    
    def _calculate_clan_statistics(self, members: List[Dict]) -> Dict[str, Any]:
        """Расчет статистики клана"""
        if not members:
            return {}
        
        trophies = [m.get('trophies', 0) for m in members]
        donations_given = [m.get('donations', 0) for m in members]
        
        return {
            'avg_trophies': sum(trophies) / len(trophies),
            'total_trophies': sum(trophies),
            'min_trophies': min(trophies),
            'max_trophies': max(trophies),
            'total_donations': sum(donations_given),
            'avg_donations': sum(donations_given) / len(donations_given) if donations_given else 0,
            'member_count': len(members)
        }
    
    async def _get_popular_clans_for_search(self) -> List[str]:
        """Получение списка популярных кланов для глобального поиска"""
        # Возвращаем теги популярных кланов (можно получать из рейтингов)
        # Здесь используются примерные теги для демонстрации
        return [
            '#2PP',  # Примерный тег
            '#9PJYVVL2',  # Примерный тег
            '#YJLV8GJG'   # Примерный тег
        ]
    
    async def _analyze_player_clan(
        self, 
        player_info: Dict, 
        chat_id: int
    ) -> Dict[str, Any]:
        """Анализ клана игрока в контексте чата"""
        clan_info = player_info.get('clan', {})
        
        if not clan_info:
            return {
                'has_clan': False,
                'is_registered_clan': False,
                'clan_name': None,
                'clan_tag': None,
                'analysis': 'Игрок не состоит в клане'
            }
        
        clan_tag = clan_info.get('tag', '')
        clan_name = clan_info.get('name', 'Неизвестный клан')
        
        # Проверяем, зарегистрирован ли клан в чате
        registered_clan = await self.clan_service.get_clan_by_tag(clan_tag)
        is_registered = registered_clan is not None
        
        return {
            'has_clan': True,
            'is_registered_clan': is_registered,
            'clan_name': clan_name,
            'clan_tag': clan_tag,
            'clan_level': clan_info.get('clanLevel', 'N/A'),
            'clan_points': clan_info.get('clanPoints', 0),
            'analysis': (
                f'Состоит в {"зарегистрированном" if is_registered else "незарегистрированном"} клане'
            )
        }
    
    async def _generate_search_recommendations(
        self,
        query: str,
        chat_id: int,
        search_results: Dict
    ) -> List[str]:
        """Генерация рекомендаций по поиску"""
        recommendations = []
        
        total_found = search_results.get('total_found', 0)
        clan_members_count = len(search_results.get('clan_members', []))
        
        if total_found == 0:
            recommendations.extend([
                "🔍 Попробуйте изменить поисковый запрос",
                "📝 Проверьте правильность написания имени",
                "🏰 Убедитесь, что игрок состоит в одном из зарегистрированных кланов"
            ])
        elif total_found > 50:
            recommendations.append(
                "📊 Найдено много результатов - уточните запрос для лучшей точности"
            )
        
        if clan_members_count > 0:
            recommendations.append(
                "✅ Найдены игроки в зарегистрированных кланах - рекомендуем выбрать их"
            )
        
        if len(query) < 3:
            recommendations.append(
                "💡 Введите минимум 3 символа для более точного поиска"
            )
        
        return recommendations