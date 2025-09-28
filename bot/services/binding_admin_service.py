"""
Административная система управления привязками игроков
Фаза 4: Расширенные возможности администрирования и модерации
"""

from typing import List, Dict, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import asyncio

from ..services.passport_database_service import PassportDatabaseService
from ..services.player_binding_service import PlayerBindingService
from ..services.clan_database_service import ClanDatabaseService
from ..models.passport_models import PassportOperationLog, PlayerBinding, PassportInfo
from ..utils.permissions import check_admin_permission, get_user_permissions

logger = logging.getLogger(__name__)


class BindingAdminService:
    """Административный сервис для управления привязками игроков"""
    
    def __init__(self):
        self.passport_service = PassportDatabaseService()
        self.binding_service = PlayerBindingService()
        self.clan_service = ClanDatabaseService()
    
    async def get_verification_queue(
        self,
        chat_id: int,
        admin_id: int,
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Получение очереди привязок, ожидающих верификации
        
        Args:
            chat_id: ID чата
            admin_id: ID администратора
            filters: Фильтры для очереди (по дате, клану и т.д.)
            
        Returns:
            Dict с очередью привязок и статистикой
        """
        try:
            # Проверяем права администратора
            is_admin = await check_admin_permission(admin_id, chat_id)
            if not is_admin:
                return {
                    'success': False,
                    'error': 'Недостаточно прав доступа',
                    'queue': [],
                    'statistics': {}
                }
            
            # Получаем все паспорта с неверифицированными привязками
            all_passports = await self.passport_service.get_chat_passports(
                chat_id=chat_id,
                include_stats=True
            )
            
            # Фильтруем неверифицированные привязки
            unverified_queue = []
            
            for passport in all_passports:
                if passport.player_binding and not passport.player_binding.is_verified:
                    binding = passport.player_binding
                    
                    queue_item = {
                        'user_id': passport.user_id,
                        'user_name': passport.display_name,
                        'username': passport.username,
                        'player_tag': binding.player_tag,
                        'player_name': binding.player_name,
                        'player_clan_name': binding.player_clan_name,
                        'player_trophies': binding.player_trophies,
                        'binding_date': binding.binding_date,
                        'days_waiting': (datetime.now() - binding.binding_date).days,
                        'is_clan_member': await self._check_is_registered_clan_member(
                            binding.player_tag, chat_id
                        ),
                        'priority': self._calculate_verification_priority(binding, passport)
                    }
                    
                    # Применяем фильтры
                    if self._passes_filters(queue_item, filters):
                        unverified_queue.append(queue_item)
            
            # Сортируем по приоритету (убывание)
            unverified_queue.sort(key=lambda x: x['priority'], reverse=True)
            
            # Рассчитываем статистику
            statistics = await self._calculate_queue_statistics(unverified_queue, chat_id)
            
            return {
                'success': True,
                'queue': unverified_queue,
                'total_unverified': len(unverified_queue),
                'statistics': statistics,
                'admin_id': admin_id
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения очереди верификации: {e}")
            return {
                'success': False,
                'error': str(e),
                'queue': [],
                'statistics': {}
            }
    
    async def bulk_verify_bindings(
        self,
        chat_id: int,
        admin_id: int,
        user_ids: Optional[List[int]] = None,
        criteria: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Массовая верификация привязок
        
        Args:
            chat_id: ID чата
            admin_id: ID администратора
            user_ids: Конкретные ID пользователей (если None - все подходящие)
            criteria: Критерии для автоматической верификации
            
        Returns:
            Результат массовой верификации
        """
        try:
            # Проверяем права администратора
            is_admin = await check_admin_permission(admin_id, chat_id)
            if not is_admin:
                return {
                    'success': False,
                    'error': 'Недостаточно прав доступа',
                    'verified_count': 0,
                    'failed_verifications': []
                }
            
            # Получаем администратора
            admin_info = await self.passport_service.get_passport_by_user(admin_id, chat_id)
            admin_username = admin_info.username if admin_info else 'Unknown Admin'
            
            # Получаем очередь верификации
            queue_result = await self.get_verification_queue(chat_id, admin_id)
            
            if not queue_result['success']:
                return queue_result
            
            verification_queue = queue_result['queue']
            
            # Фильтруем по указанным пользователям или критериям
            targets_to_verify = []
            
            if user_ids:
                # Верифицируем конкретных пользователей
                targets_to_verify = [
                    item for item in verification_queue 
                    if item['user_id'] in user_ids
                ]
            elif criteria:
                # Верифицируем по критериям
                targets_to_verify = [
                    item for item in verification_queue
                    if self._meets_auto_verify_criteria(item, criteria)
                ]
            else:
                # Верифицируем всех в очереди
                targets_to_verify = verification_queue
            
            # Выполняем верификацию
            verified_count = 0
            failed_verifications = []
            
            for target in targets_to_verify:
                try:
                    result = await self.binding_service.verify_player_binding(
                        user_id=target['user_id'],
                        chat_id=chat_id,
                        admin_id=admin_id,
                        admin_username=admin_username
                    )
                    
                    if result['success']:
                        verified_count += 1
                        
                        # Логируем массовую верификацию
                        await self._log_bulk_verification(
                            target['user_id'], admin_id, chat_id, target['player_tag']
                        )
                    else:
                        failed_verifications.append({
                            'user_id': target['user_id'],
                            'user_name': target['user_name'],
                            'error': result.get('error', 'Неизвестная ошибка')
                        })
                        
                except Exception as e:
                    logger.error(f"Ошибка верификации для {target['user_id']}: {e}")
                    failed_verifications.append({
                        'user_id': target['user_id'],
                        'user_name': target['user_name'],
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'verified_count': verified_count,
                'failed_verifications': failed_verifications,
                'total_processed': len(targets_to_verify)
            }
            
        except Exception as e:
            logger.error(f"Ошибка массовой верификации: {e}")
            return {
                'success': False,
                'error': str(e),
                'verified_count': 0,
                'failed_verifications': []
            }
    
    async def get_binding_conflicts(self, chat_id: int, admin_id: int) -> Dict[str, Any]:
        """
        Поиск конфликтов в привязках (дублирующиеся теги игроков)
        
        Args:
            chat_id: ID чата
            admin_id: ID администратора
            
        Returns:
            Dict с найденными конфликтами
        """
        try:
            # Проверяем права администратора
            is_admin = await check_admin_permission(admin_id, chat_id)
            if not is_admin:
                return {
                    'success': False,
                    'error': 'Недостаточно прав доступа',
                    'conflicts': []
                }
            
            # Получаем все привязки в чате
            all_passports = await self.passport_service.get_chat_passports(chat_id)
            
            # Группируем по тегам игроков
            player_tags_map = {}
            
            for passport in all_passports:
                if passport.player_binding and passport.player_binding.player_tag:
                    tag = passport.player_binding.player_tag
                    
                    if tag not in player_tags_map:
                        player_tags_map[tag] = []
                    
                    player_tags_map[tag].append({
                        'user_id': passport.user_id,
                        'user_name': passport.display_name,
                        'username': passport.username,
                        'binding_date': passport.player_binding.binding_date,
                        'is_verified': passport.player_binding.is_verified
                    })
            
            # Ищем конфликты (несколько пользователей с одним тегом)
            conflicts = []
            
            for player_tag, bindings in player_tags_map.items():
                if len(bindings) > 1:
                    # Сортируем по дате привязки (старые первыми)
                    bindings.sort(key=lambda x: x['binding_date'])
                    
                    conflicts.append({
                        'player_tag': player_tag,
                        'bindings_count': len(bindings),
                        'bindings': bindings,
                        'resolution_suggestions': self._generate_conflict_resolution_suggestions(bindings)
                    })
            
            return {
                'success': True,
                'conflicts': conflicts,
                'total_conflicts': len(conflicts),
                'admin_id': admin_id
            }
            
        except Exception as e:
            logger.error(f"Ошибка поиска конфликтов привязок: {e}")
            return {
                'success': False,
                'error': str(e),
                'conflicts': []
            }
    
    async def resolve_binding_conflict(
        self,
        chat_id: int,
        admin_id: int,
        player_tag: str,
        keep_user_id: int,
        remove_user_ids: List[int],
        reason: str = None
    ) -> Dict[str, Any]:
        """
        Разрешение конфликта привязок
        
        Args:
            chat_id: ID чата
            admin_id: ID администратора
            player_tag: Тег игрока с конфликтом
            keep_user_id: ID пользователя, чью привязку оставить
            remove_user_ids: ID пользователей, чьи привязки удалить
            reason: Причина разрешения конфликта
            
        Returns:
            Результат разрешения конфликта
        """
        try:
            # Проверяем права администратора
            is_admin = await check_admin_permission(admin_id, chat_id)
            if not is_admin:
                return {
                    'success': False,
                    'error': 'Недостаточно прав доступа'
                }
            
            # Получаем информацию об администраторе
            admin_info = await self.passport_service.get_passport_by_user(admin_id, chat_id)
            admin_username = admin_info.username if admin_info else 'Unknown Admin'
            
            removed_bindings = []
            failed_removals = []
            
            # Удаляем привязки конфликтных пользователей
            for remove_user_id in remove_user_ids:
                try:
                    # Получаем паспорт пользователя для логирования
                    user_passport = await self.passport_service.get_passport_by_user(
                        remove_user_id, chat_id
                    )
                    
                    if not user_passport:
                        failed_removals.append({
                            'user_id': remove_user_id,
                            'error': 'Паспорт пользователя не найден'
                        })
                        continue
                    
                    # Удаляем привязку
                    result = await self.binding_service.unbind_player_from_passport(
                        user_id=remove_user_id,
                        chat_id=chat_id,
                        requester_id=admin_id
                    )
                    
                    if result['success']:
                        removed_bindings.append({
                            'user_id': remove_user_id,
                            'user_name': user_passport.display_name,
                            'player_tag': player_tag
                        })
                        
                        # Логируем разрешение конфликта
                        await self._log_conflict_resolution(
                            remove_user_id, admin_id, chat_id, player_tag, reason
                        )
                    else:
                        failed_removals.append({
                            'user_id': remove_user_id,
                            'error': result.get('error', 'Неизвестная ошибка')
                        })
                        
                except Exception as e:
                    logger.error(f"Ошибка удаления привязки для {remove_user_id}: {e}")
                    failed_removals.append({
                        'user_id': remove_user_id,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'kept_user_id': keep_user_id,
                'removed_bindings': removed_bindings,
                'failed_removals': failed_removals,
                'resolution_reason': reason
            }
            
        except Exception as e:
            logger.error(f"Ошибка разрешения конфликта привязок: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_binding_analytics(self, chat_id: int, admin_id: int) -> Dict[str, Any]:
        """
        Получение расширенной аналитики по привязкам
        
        Args:
            chat_id: ID чата
            admin_id: ID администратора
            
        Returns:
            Детальная аналитика привязок
        """
        try:
            # Проверяем права администратора
            is_admin = await check_admin_permission(admin_id, chat_id)
            if not is_admin:
                return {
                    'success': False,
                    'error': 'Недостаточно прав доступа'
                }
            
            # Получаем базовую статистику привязок
            base_stats = await self.binding_service.get_binding_statistics(chat_id)
            
            # Получаем все паспорта с привязками
            all_passports = await self.passport_service.get_chat_passports(
                chat_id, include_stats=True
            )
            
            bindings = [p for p in all_passports if p.player_binding]
            
            # Расширенная аналитика
            analytics = {
                'success': True,
                'basic_stats': base_stats,
                'verification_stats': await self._calculate_verification_analytics(bindings),
                'clan_distribution': await self._calculate_clan_distribution_analytics(bindings, chat_id),
                'temporal_analytics': await self._calculate_temporal_analytics(bindings),
                'quality_metrics': await self._calculate_quality_metrics(bindings),
                'admin_activity': await self._calculate_admin_activity(chat_id),
                'recommendations': await self._generate_admin_recommendations(bindings, chat_id)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики привязок: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _check_is_registered_clan_member(self, player_tag: str, chat_id: int) -> bool:
        """Проверка, состоит ли игрок в зарегистрированном клане"""
        try:
            # Получаем зарегистрированные кланы чата
            chat_clans = await self.clan_service.get_chat_clans(chat_id)
            
            if not chat_clans:
                return False
            
            # Проверяем каждый клан
            for clan in chat_clans:
                clan_members = await self.clan_service.get_clan_members(clan['clan_tag'])
                
                if clan_members:
                    member_tags = [member.get('tag', '') for member in clan_members]
                    if player_tag in member_tags:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки членства в клане: {e}")
            return False
    
    def _calculate_verification_priority(self, binding: PlayerBinding, passport: PassportInfo) -> int:
        """Расчет приоритета верификации"""
        priority = 0
        
        # Бонус за дни ожидания (чем дольше ждет - тем выше приоритет)
        days_waiting = (datetime.now() - binding.binding_date).days
        priority += days_waiting * 5
        
        # Бонус за кубки игрока
        trophies_bonus = min(binding.player_trophies // 1000, 10)
        priority += trophies_bonus
        
        # Бонус за активность пользователя
        if passport.stats:
            messages_bonus = min(passport.stats.messages_count // 100, 15)
            priority += messages_bonus
        
        # Бонус, если игрок в клане
        if binding.player_clan_name:
            priority += 10
        
        return priority
    
    def _passes_filters(self, queue_item: Dict, filters: Optional[Dict]) -> bool:
        """Проверка прохождения фильтров для элемента очереди"""
        if not filters:
            return True
        
        # Фильтр по минимальным дням ожидания
        if 'min_days_waiting' in filters:
            if queue_item['days_waiting'] < filters['min_days_waiting']:
                return False
        
        # Фильтр по минимальным кубкам
        if 'min_trophies' in filters:
            if queue_item['player_trophies'] < filters['min_trophies']:
                return False
        
        # Фильтр по наличию клана
        if 'has_clan' in filters:
            has_clan = bool(queue_item['player_clan_name'])
            if has_clan != filters['has_clan']:
                return False
        
        # Фильтр по членству в зарегистрированном клане
        if 'is_clan_member' in filters:
            if queue_item['is_clan_member'] != filters['is_clan_member']:
                return False
        
        return True
    
    def _meets_auto_verify_criteria(self, item: Dict, criteria: Dict) -> bool:
        """Проверка соответствия критериям автоверификации"""
        # Автоверификация членов зарегистрированных кланов
        if criteria.get('auto_verify_clan_members', False) and item['is_clan_member']:
            return True
        
        # Автоверификация по минимальным кубкам
        min_trophies = criteria.get('min_trophies_auto_verify', 0)
        if min_trophies > 0 and item['player_trophies'] >= min_trophies:
            return True
        
        # Автоверификация старых привязок
        max_days_waiting = criteria.get('max_days_waiting', 0)
        if max_days_waiting > 0 and item['days_waiting'] >= max_days_waiting:
            return True
        
        return False
    
    async def _calculate_queue_statistics(self, queue: List[Dict], chat_id: int) -> Dict:
        """Расчет статистики очереди верификации"""
        if not queue:
            return {}
        
        # Базовая статистика
        total = len(queue)
        clan_members = sum(1 for item in queue if item['is_clan_member'])
        high_trophy = sum(1 for item in queue if item['player_trophies'] >= 3000)
        old_requests = sum(1 for item in queue if item['days_waiting'] >= 7)
        
        # Распределение по дням ожидания
        days_distribution = {}
        for item in queue:
            days = item['days_waiting']
            days_range = f"{days//7 * 7}-{days//7 * 7 + 6} дней"
            days_distribution[days_range] = days_distribution.get(days_range, 0) + 1
        
        return {
            'total_in_queue': total,
            'clan_members_count': clan_members,
            'clan_members_percentage': (clan_members / total * 100) if total > 0 else 0,
            'high_trophy_players': high_trophy,
            'old_requests': old_requests,
            'average_days_waiting': sum(item['days_waiting'] for item in queue) / total,
            'days_distribution': days_distribution
        }
    
    def _generate_conflict_resolution_suggestions(self, bindings: List[Dict]) -> List[str]:
        """Генерация предложений по разрешению конфликтов"""
        suggestions = []
        
        # Сортируем по дате (старая привязка первой)
        sorted_bindings = sorted(bindings, key=lambda x: x['binding_date'])
        
        # Предложение оставить самую старую привязку
        oldest = sorted_bindings[0]
        suggestions.append(f"Оставить привязку {oldest['user_name']} (самая старая: {oldest['binding_date'].strftime('%d.%m.%Y')})")
        
        # Предложение оставить верифицированную привязку
        verified = [b for b in bindings if b['is_verified']]
        if verified:
            suggestions.append(f"Оставить верифицированную привязку: {verified[0]['user_name']}")
        
        # Предложение удалить все и позволить переприкрепить
        suggestions.append("Удалить все конфликтные привязки для повторной привязки")
        
        return suggestions
    
    async def _log_bulk_verification(self, user_id: int, admin_id: int, chat_id: int, player_tag: str):
        """Логирование массовой верификации"""
        try:
            operation_log = PassportOperationLog.create_log(
                passport_id=None,
                operation_type='bulk_verification',
                user_id=admin_id,
                username='admin',
                operation_details={
                    'verified_user_id': user_id,
                    'player_tag': player_tag,
                    'verification_type': 'bulk'
                },
                result='success'
            )
            
            # Сохраняем лог (реализация зависит от используемой системы логирования)
            logger.info(f"Bulk verification: Admin {admin_id} verified {user_id} with player {player_tag}")
            
        except Exception as e:
            logger.error(f"Ошибка логирования массовой верификации: {e}")
    
    async def _log_conflict_resolution(self, user_id: int, admin_id: int, chat_id: int, player_tag: str, reason: str):
        """Логирование разрешения конфликта"""
        try:
            operation_log = PassportOperationLog.create_log(
                passport_id=None,
                operation_type='conflict_resolution',
                user_id=admin_id,
                username='admin',
                operation_details={
                    'removed_user_id': user_id,
                    'player_tag': player_tag,
                    'reason': reason
                },
                result='success'
            )
            
            logger.info(f"Conflict resolution: Admin {admin_id} removed binding for {user_id} (player {player_tag})")
            
        except Exception as e:
            logger.error(f"Ошибка логирования разрешения конфликта: {e}")
    
    async def _calculate_verification_analytics(self, bindings: List) -> Dict:
        """Расчет аналитики верификации"""
        if not bindings:
            return {}
        
        verified_count = sum(1 for b in bindings if b.player_binding.is_verified)
        total_count = len(bindings)
        
        # Распределение времени верификации
        verification_times = []
        for passport in bindings:
            binding = passport.player_binding
            if binding.is_verified and binding.verification_date:
                time_delta = binding.verification_date - binding.binding_date
                verification_times.append(time_delta.days)
        
        avg_verification_time = sum(verification_times) / len(verification_times) if verification_times else 0
        
        return {
            'total_bindings': total_count,
            'verified_count': verified_count,
            'verification_rate': (verified_count / total_count * 100) if total_count > 0 else 0,
            'pending_verification': total_count - verified_count,
            'avg_verification_time_days': avg_verification_time
        }
    
    async def _calculate_clan_distribution_analytics(self, bindings: List, chat_id: int) -> Dict:
        """Расчет аналитики распределения по кланам"""
        # Получаем зарегистрированные кланы
        registered_clans = await self.clan_service.get_chat_clans(chat_id)
        registered_clan_names = {clan['clan_name'] for clan in registered_clans}
        
        clan_distribution = {}
        registered_vs_external = {'registered': 0, 'external': 0, 'no_clan': 0}
        
        for passport in bindings:
            binding = passport.player_binding
            clan_name = binding.player_clan_name or 'Без клана'
            
            clan_distribution[clan_name] = clan_distribution.get(clan_name, 0) + 1
            
            # Классификация
            if not binding.player_clan_name:
                registered_vs_external['no_clan'] += 1
            elif clan_name in registered_clan_names:
                registered_vs_external['registered'] += 1
            else:
                registered_vs_external['external'] += 1
        
        return {
            'clan_distribution': clan_distribution,
            'registered_vs_external': registered_vs_external,
            'unique_clans': len(clan_distribution)
        }
    
    async def _calculate_temporal_analytics(self, bindings: List) -> Dict:
        """Расчет временной аналитики привязок"""
        if not bindings:
            return {}
        
        # Распределение по дням недели и часам
        daily_distribution = {}
        hourly_distribution = {}
        
        # Анализ роста привязок по времени
        monthly_growth = {}
        
        for passport in bindings:
            binding_date = passport.player_binding.binding_date
            
            # День недели
            day_name = binding_date.strftime('%A')
            daily_distribution[day_name] = daily_distribution.get(day_name, 0) + 1
            
            # Час
            hour = binding_date.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
            
            # Месяц
            month_key = binding_date.strftime('%Y-%m')
            monthly_growth[month_key] = monthly_growth.get(month_key, 0) + 1
        
        return {
            'daily_distribution': daily_distribution,
            'hourly_distribution': hourly_distribution,
            'monthly_growth': monthly_growth
        }
    
    async def _calculate_quality_metrics(self, bindings: List) -> Dict:
        """Расчет метрик качества привязок"""
        if not bindings:
            return {}
        
        total = len(bindings)
        
        # Качественные метрики
        high_trophy_players = sum(1 for p in bindings if p.player_binding.player_trophies >= 3000)
        players_with_clan = sum(1 for p in bindings if p.player_binding.player_clan_name)
        verified_quickly = sum(
            1 for p in bindings 
            if p.player_binding.is_verified and 
               p.player_binding.verification_date and
               (p.player_binding.verification_date - p.player_binding.binding_date).days <= 1
        )
        
        return {
            'high_trophy_rate': (high_trophy_players / total * 100) if total > 0 else 0,
            'clan_membership_rate': (players_with_clan / total * 100) if total > 0 else 0,
            'quick_verification_rate': (verified_quickly / total * 100) if total > 0 else 0,
            'quality_score': (high_trophy_players + players_with_clan + verified_quickly) / (total * 3) * 100 if total > 0 else 0
        }
    
    async def _calculate_admin_activity(self, chat_id: int) -> Dict:
        """Расчет активности администраторов"""
        # Эта функция требует дополнительного логирования действий администраторов
        # Пока возвращаем заглушку
        return {
            'total_verifications': 0,
            'active_admins': 0,
            'avg_verifications_per_admin': 0
        }
    
    async def _generate_admin_recommendations(self, bindings: List, chat_id: int) -> List[str]:
        """Генерация рекомендаций для администраторов"""
        recommendations = []
        
        if not bindings:
            return ["Нет привязок для анализа"]
        
        # Анализ непроверенных привязок
        unverified = [p for p in bindings if not p.player_binding.is_verified]
        if unverified:
            recommendations.append(f"⏳ {len(unverified)} привязок ожидают верификации")
        
        # Анализ старых непроверенных привязок
        old_unverified = [
            p for p in unverified 
            if (datetime.now() - p.player_binding.binding_date).days > 7
        ]
        if old_unverified:
            recommendations.append(f"🚨 {len(old_unverified)} привязок ожидают более недели")
        
        # Анализ игроков без кланов
        no_clan_players = [p for p in bindings if not p.player_binding.player_clan_name]
        if len(no_clan_players) > len(bindings) * 0.3:  # Более 30%
            recommendations.append("🏰 Много игроков без кланов - рассмотрите промо зарегистрированных кланов")
        
        # Анализ качества привязок
        low_trophy_players = [p for p in bindings if p.player_binding.player_trophies < 1000]
        if len(low_trophy_players) > len(bindings) * 0.2:  # Более 20%
            recommendations.append("💎 Много игроков с низкими кубками - усильте контроль")
        
        return recommendations