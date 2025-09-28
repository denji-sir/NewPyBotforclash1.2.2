"""
Вспомогательные функции для работы с кланами
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def calculate_clan_activity_score(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Рассчитывает показатель активности клана на основе участников
    
    Args:
        members: Список участников клана
        
    Returns:
        Словарь с показателями активности
    """
    if not members:
        return {
            'activity_score': 0,
            'donation_ratio': 0,
            'avg_level': 0,
            'active_members': 0
        }
    
    total_donations = sum(member.get('donations', 0) for member in members)
    total_received = sum(member.get('donationsReceived', 0) for member in members)
    total_levels = sum(member.get('expLevel', 0) for member in members)
    
    # Считаем активных участников (с донатами > 0)
    active_members = len([m for m in members if m.get('donations', 0) > 0])
    
    # Средний уровень
    avg_level = total_levels / len(members) if members else 0
    
    # Соотношение донатов
    donation_ratio = total_donations / total_received if total_received > 0 else 0
    
    # Показатель активности (0-100)
    activity_score = min(100, (
        (active_members / len(members) * 40) +  # 40% - доля активных
        (min(avg_level / 100, 1) * 30) +       # 30% - средний уровень
        (min(donation_ratio, 1) * 30)          # 30% - соотношение донатов
    ))
    
    return {
        'activity_score': round(activity_score, 1),
        'donation_ratio': round(donation_ratio, 2),
        'avg_level': round(avg_level, 1),
        'active_members': active_members,
        'total_donations': total_donations,
        'total_received': total_received
    }


def analyze_clan_roles(members: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Анализирует распределение ролей в клане
    
    Args:
        members: Список участников клана
        
    Returns:
        Словарь с количеством участников по ролям
    """
    roles = {
        'leader': 0,
        'coLeader': 0,
        'admin': 0,
        'member': 0
    }
    
    for member in members:
        role = member.get('role', 'member')
        if role in roles:
            roles[role] += 1
        else:
            roles['member'] += 1
    
    return roles


def get_clan_health_status(clan_data: Dict[str, Any], activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Определяет "здоровье" клана на основе различных показателей
    
    Args:
        clan_data: Основные данные клана
        activity_data: Данные активности
        
    Returns:
        Словарь со статусом здоровья клана
    """
    health_score = 0
    issues = []
    recommendations = []
    
    # Проверяем заполненность клана (20%)
    member_ratio = clan_data.get('member_count', 0) / 50
    if member_ratio > 0.9:
        health_score += 20
    elif member_ratio > 0.7:
        health_score += 15
        recommendations.append("Recruit more members to fill the clan")
    elif member_ratio > 0.5:
        health_score += 10
        issues.append("Low member count")
        recommendations.append("Focus on recruiting new members")
    else:
        issues.append("Very low member count")
        recommendations.append("Urgent: recruit new members")
    
    # Проверяем активность (30%)
    activity_score = activity_data.get('activity_score', 0)
    if activity_score > 80:
        health_score += 30
    elif activity_score > 60:
        health_score += 20
        recommendations.append("Encourage more donation activity")
    elif activity_score > 40:
        health_score += 15
        issues.append("Low clan activity")
        recommendations.append("Organize clan events to boost activity")
    else:
        issues.append("Very low clan activity")
        recommendations.append("Consider removing inactive members")
    
    # Проверяем баланс ролей (25%)
    roles = analyze_clan_roles([])  # Заглушка, в реальности передавать members
    leader_count = roles.get('leader', 0)
    coleader_count = roles.get('coLeader', 0)
    admin_count = roles.get('admin', 0)
    
    if leader_count == 1 and coleader_count >= 1 and admin_count >= 2:
        health_score += 25
    elif leader_count == 1 and (coleader_count >= 1 or admin_count >= 1):
        health_score += 20
        recommendations.append("Consider promoting more co-leaders/elders")
    elif leader_count == 1:
        health_score += 15
        recommendations.append("Promote trusted members to leadership roles")
    else:
        issues.append("Leadership structure issues")
        recommendations.append("Fix leadership hierarchy")
    
    # Проверяем уровень клана (25%)
    clan_level = clan_data.get('level', 1)
    if clan_level >= 15:
        health_score += 25
    elif clan_level >= 10:
        health_score += 20
    elif clan_level >= 5:
        health_score += 15
        recommendations.append("Focus on clan games and activities")
    else:
        health_score += 10
        issues.append("Low clan level")
        recommendations.append("Participate actively in clan games")
    
    # Определяем статус
    if health_score >= 80:
        status = "Excellent"
        status_emoji = "🟢"
    elif health_score >= 60:
        status = "Good"
        status_emoji = "🟡"
    elif health_score >= 40:
        status = "Fair"
        status_emoji = "🟠"
    else:
        status = "Poor"
        status_emoji = "🔴"
    
    return {
        'health_score': health_score,
        'status': status,
        'status_emoji': status_emoji,
        'issues': issues,
        'recommendations': recommendations[:3]  # Топ 3 рекомендации
    }


def format_member_list(members: List[Dict[str, Any]], max_members: int = 10) -> str:
    """
    Форматирует список участников для отображения в Telegram
    
    Args:
        members: Список участников
        max_members: Максимальное количество участников для отображения
        
    Returns:
        Отформатированная строка со списком участников
    """
    if not members:
        return "Нет участников"
    
    # Сортируем по роли и донатам
    role_order = {'leader': 0, 'coLeader': 1, 'admin': 2, 'member': 3}
    members_sorted = sorted(
        members, 
        key=lambda x: (role_order.get(x.get('role', 'member'), 4), -x.get('donations', 0))
    )
    
    role_emojis = {
        'leader': '👑',
        'coLeader': '🌟',
        'admin': '⭐',
        'member': '👤'
    }
    
    result = ""
    current_role = None
    shown_count = 0
    
    for member in members_sorted:
        if shown_count >= max_members:
            remaining = len(members) - shown_count
            result += f"\n... и еще {remaining} участников"
            break
        
        member_role = member.get('role', 'member')
        member_name = member.get('name', 'Unknown')
        member_tag = member.get('tag', '')
        member_level = member.get('expLevel', 0)
        member_donations = member.get('donations', 0)
        
        # Добавляем заголовок роли
        if current_role != member_role:
            current_role = member_role
            role_names = {
                'leader': 'Лидер',
                'coLeader': 'Со-лидер', 
                'admin': 'Старейшина',
                'member': 'Участник'
            }
            
            if result:  # Добавляем отступ между группами
                result += "\n"
            result += f"\n**{role_emojis.get(member_role, '👤')} {role_names.get(member_role, 'Участник')}:**\n"
        
        # Добавляем участника
        result += (
            f"• **{member_name}** `{member_tag}`\n"
            f"  🎯 Lv.{member_level} | 💝 {member_donations:,}\n"
        )
        
        shown_count += 1
    
    return result.strip()


def generate_clan_comparison(clan1_data: Dict[str, Any], clan2_data: Dict[str, Any]) -> str:
    """
    Генерирует сравнение двух кланов
    
    Args:
        clan1_data: Данные первого клана
        clan2_data: Данные второго клана
        
    Returns:
        Отформатированное сравнение
    """
    def get_winner_emoji(val1, val2):
        if val1 > val2:
            return "🥇", "🥈"
        elif val2 > val1:
            return "🥈", "🥇"
        else:
            return "🤝", "🤝"
    
    # Сравниваем основные показатели
    points1 = clan1_data.get('points', 0)
    points2 = clan2_data.get('points', 0)
    points_emoji1, points_emoji2 = get_winner_emoji(points1, points2)
    
    members1 = clan1_data.get('member_count', 0)
    members2 = clan2_data.get('member_count', 0)
    members_emoji1, members_emoji2 = get_winner_emoji(members1, members2)
    
    level1 = clan1_data.get('level', 0)
    level2 = clan2_data.get('level', 0)
    level_emoji1, level_emoji2 = get_winner_emoji(level1, level2)
    
    comparison = f"""
📊 **Сравнение кланов**

🏰 **{clan1_data.get('name', 'Unknown')}** vs **{clan2_data.get('name', 'Unknown')}**

**🏆 Очки клана:**
{points_emoji1} {clan1_data.get('name', 'Клан 1')}: {points1:,}
{points_emoji2} {clan2_data.get('name', 'Клан 2')}: {points2:,}

**👥 Участники:**
{members_emoji1} {clan1_data.get('name', 'Клан 1')}: {members1}/50
{members_emoji2} {clan2_data.get('name', 'Клан 2')}: {members2}/50

**📊 Уровень клана:**
{level_emoji1} {clan1_data.get('name', 'Клан 1')}: {level1}
{level_emoji2} {clan2_data.get('name', 'Клан 2')}: {level2}
"""
    
    return comparison.strip()


def get_clan_recruitment_message(clan_data: Dict[str, Any], activity_data: Dict[str, Any]) -> str:
    """
    Генерирует сообщение для рекрутинга в клан
    
    Args:
        clan_data: Данные клана
        activity_data: Данные активности
        
    Returns:
        Сообщение для рекрутинга
    """
    name = clan_data.get('name', 'Unknown')
    tag = clan_data.get('tag', '')
    level = clan_data.get('level', 1)
    points = clan_data.get('points', 0)
    members = clan_data.get('member_count', 0)
    
    activity_score = activity_data.get('activity_score', 0)
    
    # Определяем тип клана по активности
    if activity_score >= 80:
        clan_type = "🔥 Активный"
    elif activity_score >= 60:
        clan_type = "⚡ Развивающийся"
    else:
        clan_type = "🌱 Дружелюбный"
    
    message = f"""
🏰 **Приглашаем в клан {name}!**

📋 **Информация:**
• 🏷️ Тег: `{tag}`
• 📊 Уровень: {level}
• 🏆 Очки: {points:,}
• 👥 Участников: {members}/50
• ⚡ Тип: {clan_type}

🎯 **Что мы предлагаем:**
• Активные донаты
• Регулярные войны кланов
• Дружелюбное сообщество
• Помощь в развитии

🔍 **Ищем:**
• Активных игроков
• Участие в войнах
• Регулярные донаты

📝 Заявки рассматриваются быстро!
"""
    
    return message.strip()


def calculate_donation_efficiency(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Рассчитывает эффективность донатов в клане
    
    Args:
        members: Список участников клана
        
    Returns:
        Данные об эффективности донатов
    """
    if not members:
        return {
            'total_donated': 0,
            'total_received': 0,
            'efficiency_ratio': 0,
            'top_donors': [],
            'donation_balance': 'neutral'
        }
    
    total_donated = sum(member.get('donations', 0) for member in members)
    total_received = sum(member.get('donationsReceived', 0) for member in members)
    
    # Топ донаторы
    top_donors = sorted(
        members,
        key=lambda x: x.get('donations', 0),
        reverse=True
    )[:5]
    
    # Коэффициент эффективности
    efficiency_ratio = total_donated / total_received if total_received > 0 else 0
    
    # Баланс донатов
    if efficiency_ratio > 1.2:
        donation_balance = 'surplus'  # Излишек
    elif efficiency_ratio < 0.8:
        donation_balance = 'deficit'  # Дефицит
    else:
        donation_balance = 'balanced'  # Сбалансировано
    
    return {
        'total_donated': total_donated,
        'total_received': total_received,
        'efficiency_ratio': round(efficiency_ratio, 2),
        'top_donors': [
            {
                'name': donor.get('name', 'Unknown'),
                'tag': donor.get('tag', ''),
                'donations': donor.get('donations', 0)
            }
            for donor in top_donors
        ],
        'donation_balance': donation_balance
    }