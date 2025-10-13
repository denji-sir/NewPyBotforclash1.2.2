"""
Тесты для системы донатов с сезонным сбросом
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.services.donation_history_service import DonationHistoryService


def test_last_monday_calculation():
    """Тест расчета последнего понедельника месяца"""
    print("=" * 70)
    print("ТЕСТ: Расчет последнего понедельника месяца в 05:00 UTC")
    print("=" * 70)
    
    # Тестовые случаи для разных месяцев 2024-2025
    test_cases = [
        (2024, 10),  # Октябрь 2024
        (2024, 11),  # Ноябрь 2024
        (2024, 12),  # Декабрь 2024
        (2025, 1),   # Январь 2025
        (2025, 2),   # Февраль 2025
        (2025, 3),   # Март 2025
        (2025, 4),   # Апрель 2025
        (2025, 5),   # Май 2025
    ]
    
    for year, month in test_cases:
        last_monday = DonationHistoryService.get_last_monday_of_month(year, month)
        print(f"\n{year}-{month:02d}:")
        print(f"  Последний понедельник: {last_monday.strftime('%Y-%m-%d (%A) %H:%M:%S %Z')}")
        print(f"  Это {last_monday.day} число месяца")


def test_next_season_end():
    """Тест получения следующего конца сезона"""
    print("\n" + "=" * 70)
    print("ТЕСТ: Следующий конец сезона")
    print("=" * 70)
    
    now = datetime.now(timezone.utc)
    next_end = DonationHistoryService.get_next_season_end()
    
    print(f"\nТекущее время UTC: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Следующий конец сезона: {next_end.strftime('%Y-%m-%d (%A) %H:%M:%S %Z')}")
    
    time_until = next_end - now
    days = time_until.days
    hours = time_until.seconds // 3600
    minutes = (time_until.seconds % 3600) // 60
    
    print(f"Время до конца сезона: {days} дней, {hours} часов, {minutes} минут")


def test_season_end_detection():
    """Тест определения времени конца сезона"""
    print("\n" + "=" * 70)
    print("ТЕСТ: Определение времени конца сезона")
    print("=" * 70)
    
    # Получаем последний понедельник текущего месяца
    now = datetime.now(timezone.utc)
    season_end = DonationHistoryService.get_last_monday_of_month(now.year, now.month)
    
    # Проверяем текущее время
    is_season_end_now = DonationHistoryService.is_season_end_time(now)
    print(f"\nСейчас время конца сезона? {is_season_end_now}")
    
    # Проверяем время конца сезона
    is_season_end = DonationHistoryService.is_season_end_time(season_end)
    print(f"В момент конца сезона ({season_end.strftime('%Y-%m-%d %H:%M:%S')}): {is_season_end}")


def display_season_schedule():
    """Показать расписание концов сезонов на год вперед"""
    print("\n" + "=" * 70)
    print("РАСПИСАНИЕ КОНЦОВ СЕЗОНОВ (следующие 12 месяцев)")
    print("=" * 70)
    
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month
    
    print(f"\n{'Месяц':<15} {'Дата конца сезона':<30} {'День недели':<15}")
    print("-" * 70)
    
    for i in range(12):
        year = current_year
        month = current_month + i
        
        if month > 12:
            month = month - 12
            year += 1
        
        season_end = DonationHistoryService.get_last_monday_of_month(year, month)
        month_name = season_end.strftime('%B %Y')
        date_str = season_end.strftime('%Y-%m-%d %H:%M UTC')
        day_name = season_end.strftime('%A')
        
        print(f"{month_name:<15} {date_str:<30} {day_name:<15}")


def show_donation_system_info():
    """Показать общую информацию о системе донатов"""
    print("\n" + "=" * 70)
    print("ИНФОРМАЦИЯ О СИСТЕМЕ ДОНАТОВ")
    print("=" * 70)
    
    print("""
📊 Система архивирования донатов с сезонным сбросом

🕐 ВРЕМЯ СБРОСА СЕЗОНА:
   • Последний понедельник каждого месяца
   • В 05:00 UTC (08:00 МСК)
   
📦 ЧТО СОХРАНЯЕТСЯ:
   • История донатов каждого игрока (год + месяц)
   • Статистика получения донатов
   • Коэффициент донатов (donations/received)
   • Топ донаторы клана за сезон
   • Сводная статистика клана
   
💾 БАЗА ДАННЫХ:
   • monthly_donation_history - детальная история по игрокам
   • season_donation_summary - сводная статистика по кланам
   
🔄 АВТОМАТИЧЕСКАЯ ОЧИСТКА:
   • Старые записи (> 12 месяцев) удаляются автоматически
   
⚡ ПЛАНИРОВЩИК:
   • Автоматически архивирует донаты всех активных кланов
   • Запускается в конце каждого сезона
   • Можно запустить принудительно для тестирования
    """)


if __name__ == "__main__":
    print("\n" + "🎯" * 35)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ ДОНАТОВ С СЕЗОННЫМ СБРОСОМ")
    print("🎯" * 35 + "\n")
    
    show_donation_system_info()
    test_last_monday_calculation()
    test_next_season_end()
    test_season_end_detection()
    display_season_schedule()
    
    print("\n" + "✅" * 35)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("✅" * 35 + "\n")
