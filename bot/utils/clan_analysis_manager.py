"""
Расширенный менеджер анализа кланов
Предоставляет функции для глубокого анализа производительности кланов
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.clan_models import ClanInfo, ClanOperationLog, DatabaseError
from ..services.clan_database_service import ClanDatabaseService, get_clan_db_service
from ..services.coc_api_service import CocApiService, get_coc_api_service
from ..services.permission_service import PermissionService, get_permission_service
from .clan_helpers import (
    calculate_clan_activity_score, 
    analyze_clan_roles,
    get_clan_health_status,
    calculate_donation_efficiency,
    format_member_list,
    generate_clan_comparison,
    get_clan_recruitment_message
)

logger = logging.getLogger(__name__)


class ClanAnalysisManager:
    """Менеджер для анализа производительности кланов"""
    
    def __init__(self):
        self.db_service = get_clan_db_service()
        self.api_service = get_coc_api_service()
        self.permission_service = get_permission_service()
        
    async def analyze_clan_performance(self, clan_tag: str, chat_id: int) -> Dict[str, Any]:
        """
        Проводит полный анализ производительности клана
        
        Args:
            clan_tag: Тег клана
            chat_id: ID чата
            
        Returns:
            Полный анализ клана
        """
        try:
            # Получаем данные клана
            clan = await self.db_service.get_clan_by_tag(clan_tag, chat_id)
            if not clan:
                return {'error': 'Clan not found'}
            
            # Получаем участников из API
            async with self.api_service:
                members = await self.api_service.get_clan_members(clan_tag)
                clan_data = await self.api_service.get_clan(clan_tag)
            
            # Анализируем активность
            activity_data = calculate_clan_activity_score(members)
            
            # Анализируем роли
            roles_data = analyze_clan_roles(members)
            
            # Получаем статус здоровья
            health_data = get_clan_health_status(clan_data.__dict__, activity_data)
            
            # Анализируем эффективность донатов
            donation_data = calculate_donation_efficiency(members)
            
            return {
                'clan_info': {
                    'name': clan_data.name,
                    'tag': clan_data.tag,
                    'level': clan_data.level,
                    'points': clan_data.points,
                    'member_count': clan_data.member_count,
                    'description': clan_data.description
                },
                'activity': activity_data,
                'roles': roles_data,
                'health': health_data,
                'donations': donation_data,
                'members': members
            }
            
        except Exception as e:
            logger.error(f"Error analyzing clan performance for {clan_tag}: {e}")
            return {'error': str(e)}
            
    async def get_clan_recommendations(self, clan_tag: str, chat_id: int) -> List[str]:
        """
        Получает рекомендации для улучшения клана
        
        Args:
            clan_tag: Тег клана
            chat_id: ID чата
            
        Returns:
            Список рекомендаций
        """
        try:
            analysis = await self.analyze_clan_performance(clan_tag, chat_id)
            
            if 'error' in analysis:
                return [f"Ошибка анализа: {analysis['error']}"]
            
            recommendations = []
            
            # Рекомендации по активности
            activity_score = analysis['activity']['activity_score']
            if activity_score < 50:
                recommendations.append("🔥 Увеличить активность участников - организуйте события клана")
                recommendations.append("💝 Поощрять донаты - установите минимальные требования")
            elif activity_score < 70:
                recommendations.append("⚡ Хорошая активность, можно улучшить организацию событий")
            
            # Рекомендации по составу
            member_count = analysis['clan_info']['member_count']
            if member_count < 20:
                recommendations.append("🚨 Критически мало участников - срочный рекрутинг!")
            elif member_count < 35:
                recommendations.append("👥 Набрать больше участников - проводите рекрутинг")
            elif member_count < 45:
                recommendations.append("📈 Почти полный клан - добор последних участников")
            
            # Рекомендации по ролям
            roles = analysis['roles']
            if roles['admin'] < 3:
                recommendations.append("⭐ Назначить больше старейшин для лучшего управления")
            
            if roles['coLeader'] < 1:
                recommendations.append("🌟 Назначить со-лидера для помощи в управлении")
            elif roles['coLeader'] > 3:
                recommendations.append("⚖️ Слишком много со-лидеров, пересмотрите иерархию")
            
            # Рекомендации по донатам
            donation_balance = analysis['donations']['donation_balance']
            if donation_balance == 'deficit':
                recommendations.append("📤 Улучшить культуру донатов - больше отдавать, чем получать")
            elif donation_balance == 'surplus':
                recommendations.append("📥 Увеличить запросы донатов для лучшего баланса")
            
            # Рекомендации по эффективности донатов
            efficiency_ratio = analysis['donations']['efficiency_ratio']
            if efficiency_ratio < 0.5:
                recommendations.append("💸 Низкая эффективность донатов - обучите участников")
            
            # Рекомендации по здоровью
            health_recommendations = analysis['health']['recommendations']
            recommendations.extend([f"💊 {rec}" for rec in health_recommendations[:3]])
            
            # Общие рекомендации по уровню клана
            clan_level = analysis['clan_info']['level']
            if clan_level < 5:
                recommendations.append("🎮 Активно участвуйте в играх клана для повышения уровня")
            elif clan_level < 10:
                recommendations.append("🏆 Продолжайте участие в кланових событиях")
            
            return recommendations[:10]  # Максимум 10 рекомендаций
            
        except Exception as e:
            logger.error(f"Error getting recommendations for {clan_tag}: {e}")
            return [f"Ошибка получения рекомендаций: {e}"]
            
    async def compare_clans(self, clan_tag1: str, clan_tag2: str, chat_id: int) -> Dict[str, Any]:
        """
        Сравнивает два клана по различным показателям
        
        Args:
            clan_tag1: Тег первого клана
            clan_tag2: Тег второго клана
            chat_id: ID чата
            
        Returns:
            Результат сравнения кланов
        """
        try:
            # Получаем анализ обоих кланов
            analysis1 = await self.analyze_clan_performance(clan_tag1, chat_id)
            analysis2 = await self.analyze_clan_performance(clan_tag2, chat_id)
            
            if 'error' in analysis1:
                return {'error': f"Ошибка анализа клана {clan_tag1}: {analysis1['error']}"}
            if 'error' in analysis2:
                return {'error': f"Ошибка анализа клана {clan_tag2}: {analysis2['error']}"}
            
            comparison = {
                'clan1': analysis1['clan_info'],
                'clan2': analysis2['clan_info'],
                'winner_categories': {},
                'summary': {}
            }
            
            # Сравниваем по категориям
            categories = {
                'points': ('Очки клана', analysis1['clan_info']['points'], analysis2['clan_info']['points']),
                'level': ('Уровень клана', analysis1['clan_info']['level'], analysis2['clan_info']['level']),
                'members': ('Количество участников', analysis1['clan_info']['member_count'], analysis2['clan_info']['member_count']),
                'activity': ('Активность', analysis1['activity']['activity_score'], analysis2['activity']['activity_score']),
                'donations': ('Донаты', analysis1['donations']['total_donated'], analysis2['donations']['total_donated']),
                'health': ('Здоровье клана', analysis1['health']['health_score'], analysis2['health']['health_score'])
            }
            
            clan1_wins = 0
            clan2_wins = 0
            
            for category, (name, val1, val2) in categories.items():
                if val1 > val2:
                    comparison['winner_categories'][category] = 1
                    clan1_wins += 1
                elif val2 > val1:
                    comparison['winner_categories'][category] = 2
                    clan2_wins += 1
                else:
                    comparison['winner_categories'][category] = 0  # Ничья
            
            # Определяем общего победителя
            if clan1_wins > clan2_wins:
                comparison['overall_winner'] = 1
                comparison['summary']['winner_name'] = analysis1['clan_info']['name']
            elif clan2_wins > clan1_wins:
                comparison['overall_winner'] = 2
                comparison['summary']['winner_name'] = analysis2['clan_info']['name']
            else:
                comparison['overall_winner'] = 0
                comparison['summary']['winner_name'] = 'Ничья'
            
            comparison['summary']['clan1_wins'] = clan1_wins
            comparison['summary']['clan2_wins'] = clan2_wins
            comparison['summary']['categories'] = categories
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing clans {clan_tag1} and {clan_tag2}: {e}")
            return {'error': str(e)}
            
    async def get_recruitment_message(self, clan_tag: str, chat_id: int) -> Dict[str, Any]:
        """
        Генерирует сообщение для рекрутинга в клан
        
        Args:
            clan_tag: Тег клана
            chat_id: ID чата
            
        Returns:
            Данные для рекрутингового сообщения
        """
        try:
            analysis = await self.analyze_clan_performance(clan_tag, chat_id)
            
            if 'error' in analysis:
                return {'error': analysis['error']}
            
            clan_info = analysis['clan_info']
            activity_data = analysis['activity']
            
            # Генерируем сообщение
            recruitment_msg = get_clan_recruitment_message(clan_info, activity_data)
            
            # Добавляем дополнительную информацию
            return {
                'message': recruitment_msg,
                'clan_info': clan_info,
                'activity_score': activity_data['activity_score'],
                'health_status': analysis['health']['status'],
                'top_donors': analysis['donations']['top_donors'][:3]
            }
            
        except Exception as e:
            logger.error(f"Error generating recruitment message for {clan_tag}: {e}")
            return {'error': str(e)}
            
    async def get_detailed_member_analysis(self, clan_tag: str, chat_id: int) -> Dict[str, Any]:
        """
        Детальный анализ участников клана
        
        Args:
            clan_tag: Тег клана
            chat_id: ID чата
            
        Returns:
            Подробный анализ участников
        """
        try:
            analysis = await self.analyze_clan_performance(clan_tag, chat_id)
            
            if 'error' in analysis:
                return {'error': analysis['error']}
            
            members = analysis['members']
            
            # Анализируем участников
            member_analysis = {
                'total_members': len(members),
                'by_role': analyze_clan_roles(members),
                'donation_stats': {
                    'top_donors': sorted(members, key=lambda x: x.get('donations', 0), reverse=True)[:10],
                    'low_donors': sorted(members, key=lambda x: x.get('donations', 0))[:5],
                    'avg_donations': sum(m.get('donations', 0) for m in members) / len(members) if members else 0
                },
                'level_stats': {
                    'highest_level': max(m.get('expLevel', 0) for m in members) if members else 0,
                    'lowest_level': min(m.get('expLevel', 0) for m in members) if members else 0,
                    'avg_level': sum(m.get('expLevel', 0) for m in members) / len(members) if members else 0
                },
                'activity_indicators': {
                    'active_donors': len([m for m in members if m.get('donations', 0) > 0]),
                    'high_level_players': len([m for m in members if m.get('expLevel', 0) > 100]),
                    'leadership_roles': len([m for m in members if m.get('role') in ['leader', 'coLeader', 'admin']])
                }
            }
            
            return member_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing members for {clan_tag}: {e}")
            return {'error': str(e)}


# Глобальная функция для получения менеджера анализа
def get_clan_analysis_manager() -> ClanAnalysisManager:
    """Получить экземпляр менеджера анализа кланов"""
    return ClanAnalysisManager()