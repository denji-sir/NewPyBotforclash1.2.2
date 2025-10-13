"""
Расширенные административные команды для управления привязками
Фаза 4: Полный набор инструментов администрирования
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..ui.player_binding_ui import PlayerBindingUI
from ..utils.permissions import check_admin_permission
from ..utils.formatting import format_binding_stats, format_admin_report
from ._deps import get_admin_service, get_passport_service

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("apass"))
async def admin_bindings_command(message: Message):
    """
    Главная команда административного управления привязками
    Usage: /admin_bindings
    """
    try:
        # Проверяем права администратора
        is_admin = await check_admin_permission(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        if not is_admin:
            await message.reply(
                "❌ Эта команда доступна только администраторам чата!"
            )
            return
        
        # Получаем базовую статистику
        queue_result = await get_admin_service().get_verification_queue(
            chat_id=message.chat.id,
            admin_id=message.from_user.id
        )
        
        conflicts_result = await get_admin_service().get_binding_conflicts(
            chat_id=message.chat.id,
            admin_id=message.from_user.id
        )
        
        # Формируем главное меню
        unverified_count = len(queue_result.get('queue', []))
        conflicts_count = len(conflicts_result.get('conflicts', []))
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"⏳ Очередь верификации ({unverified_count})",
                callback_data=f"admin_verification_queue:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text=f"⚠️ Конфликты привязок ({conflicts_count})",
                callback_data=f"admin_binding_conflicts:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="📊 Детальная аналитика",
                callback_data=f"admin_detailed_analytics:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="🔧 Массовые операции",
                callback_data=f"admin_bulk_operations:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="📋 Отчеты и экспорт",
                callback_data=f"admin_reports:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="⚙️ Настройки автоверификации",
                callback_data=f"admin_auto_verify_settings:{message.from_user.id}"
            )]
        ])
        
        await message.reply(
            f"🔧 **Административная панель привязок**\n\n"
            f"📊 **Текущий статус:**\n"
            f"⏳ Ожидают верификации: **{unverified_count}**\n"
            f"⚠️ Конфликты: **{conflicts_count}**\n"
            f"👨‍💼 Администратор: {message.from_user.full_name}\n\n"
            f"Выберите действие:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_bindings_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при загрузке административной панели"
        )


@router.callback_query(F.data.startswith("admin_verification_queue:"))
async def admin_verification_queue_callback(callback: CallbackQuery):
    """Просмотр очереди верификации"""
    try:
        admin_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Получаем очередь верификации
        queue_result = await get_admin_service().get_verification_queue(
            chat_id=callback.message.chat.id,
            admin_id=admin_id
        )
        
        if not queue_result['success']:
            await callback.message.edit_text(
                f"❌ Ошибка получения очереди: {queue_result['error']}"
            )
            return
        
        queue = queue_result['queue']
        statistics = queue_result['statistics']
        
        if not queue:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data=f"admin_verification_queue:{admin_id}"
                )],
                [InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin_main_menu:{admin_id}"
                )]
            ])
            
            await callback.message.edit_text(
                "✅ **Очередь верификации пуста!**\n\n"
                "Все привязки в чате верифицированы.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return
        
        # Создаем клавиатуру с очередью
        keyboard = await PlayerBindingUI().create_verification_queue_keyboard(
            queue, admin_id
        )
        
        # Формируем текст с очередью
        queue_text = _format_verification_queue_text(queue, statistics)
        
        await callback.message.edit_text(
            queue_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_verification_queue_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_binding_conflicts:"))
async def admin_binding_conflicts_callback(callback: CallbackQuery):
    """Просмотр конфликтов привязок"""
    try:
        admin_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Получаем конфликты
        conflicts_result = await get_admin_service().get_binding_conflicts(
            chat_id=callback.message.chat.id,
            admin_id=admin_id
        )
        
        if not conflicts_result['success']:
            await callback.message.edit_text(
                f"❌ Ошибка получения конфликтов: {conflicts_result['error']}"
            )
            return
        
        conflicts = conflicts_result['conflicts']
        
        if not conflicts:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data=f"admin_binding_conflicts:{admin_id}"
                )],
                [InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin_main_menu:{admin_id}"
                )]
            ])
            
            await callback.message.edit_text(
                "✅ **Конфликты привязок отсутствуют!**\n\n"
                "Все привязки уникальны.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return
        
        # Показываем список конфликтов
        conflicts_text = _format_conflicts_text(conflicts)
        
        # Создаем клавиатуру для разрешения конфликтов
        keyboard_buttons = []
        
        for i, conflict in enumerate(conflicts[:5]):  # Показываем первые 5
            player_tag = conflict['player_tag']
            bindings_count = conflict['bindings_count']
            
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"⚠️ {player_tag} ({bindings_count} привязок)",
                callback_data=f"resolve_conflict:{admin_id}:{player_tag}"
            )])
        
        if len(conflicts) > 5:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📋 Показать все ({len(conflicts)})",
                callback_data=f"show_all_conflicts:{admin_id}"
            )])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"admin_binding_conflicts:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"admin_main_menu:{admin_id}"
            )]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            conflicts_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_binding_conflicts_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_bulk_operations:"))
async def admin_bulk_operations_callback(callback: CallbackQuery):
    """Меню массовых операций"""
    try:
        admin_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Получаем статистику для массовых операций
        queue_result = await get_admin_service().get_verification_queue(
            chat_id=callback.message.chat.id,
            admin_id=admin_id
        )
        
        unverified_count = len(queue_result.get('queue', []))
        clan_members_count = sum(
            1 for item in queue_result.get('queue', [])
            if item.get('is_clan_member', False)
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"✅ Верифицировать всех ({unverified_count})",
                callback_data=f"bulk_verify_all:{admin_id}"
            )],
            [InlineKeyboardButton(
                text=f"🏰 Верифицировать членов кланов ({clan_members_count})",
                callback_data=f"bulk_verify_clan_members:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="💎 Верифицировать по кубкам",
                callback_data=f"bulk_verify_by_trophies:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="📅 Верифицировать старые привязки",
                callback_data=f"bulk_verify_old:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="🗑️ Массовое удаление",
                callback_data=f"bulk_delete_menu:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"admin_main_menu:{admin_id}"
            )]
        ])
        
        await callback.message.edit_text(
            f"🔧 **Массовые операции с привязками**\n\n"
            f"📊 **Доступно для обработки:**\n"
            f"⏳ Всего неверифицированных: **{unverified_count}**\n"
            f"🏰 Членов зарегистрированных кланов: **{clan_members_count}**\n\n"
            f"⚠️ **Внимание!** Массовые операции необратимы.\n"
            f"Убедитесь в правильности выбора перед выполнением.\n\n"
            f"Выберите операцию:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_bulk_operations_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("bulk_verify_all:"))
async def bulk_verify_all_callback(callback: CallbackQuery):
    """Массовая верификация всех привязок"""
    try:
        admin_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Показываем подтверждение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Подтвердить массовую верификацию",
                callback_data=f"confirm_bulk_verify_all:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"admin_bulk_operations:{admin_id}"
            )]
        ])
        
        await callback.message.edit_text(
            f"⚠️ **Подтверждение массовой верификации**\n\n"
            f"Вы собираетесь верифицировать **ВСЕ** неверифицированные привязки в чате.\n\n"
            f"❗ **Это действие необратимо!**\n\n"
            f"Все игроки получат статус \"верифицирован\" независимо от их клана и кубков.\n\n"
            f"Вы уверены?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в bulk_verify_all_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("confirm_bulk_verify_all:"))
async def confirm_bulk_verify_all_callback(callback: CallbackQuery):
    """Подтверждение массовой верификации всех"""
    try:
        admin_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        await callback.message.edit_text(
            "⏳ **Выполняется массовая верификация...**\n\n"
            "Пожалуйста, подождите. Это может занять несколько секунд."
        )
        
        # Выполняем массовую верификацию
        result = await get_admin_service().bulk_verify_bindings(
            chat_id=callback.message.chat.id,
            admin_id=admin_id
        )
        
        if result['success']:
            verified_count = result['verified_count']
            failed_count = len(result['failed_verifications'])
            
            result_text = (
                f"✅ **Массовая верификация завершена!**\n\n"
                f"📊 **Результаты:**\n"
                f"✅ Успешно верифицировано: **{verified_count}**\n"
            )
            
            if failed_count > 0:
                result_text += f"❌ Ошибки: **{failed_count}**\n"
            
            result_text += (
                f"👨‍💼 **Администратор:** {callback.from_user.full_name}\n"
                f"🕐 **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Все верифицированные пользователи получили соответствующий статус."
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📊 Обновить статистику",
                    callback_data=f"admin_verification_queue:{admin_id}"
                )],
                [InlineKeyboardButton(
                    text="🔙 К админ-панели",
                    callback_data=f"admin_main_menu:{admin_id}"
                )]
            ])
            
        else:
            result_text = f"❌ **Ошибка массовой верификации:**\n{result['error']}"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data=f"bulk_verify_all:{admin_id}"
                )],
                [InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"admin_bulk_operations:{admin_id}"
                )]
            ])
        
        await callback.message.edit_text(
            result_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в confirm_bulk_verify_all_callback: {e}")
        await callback.answer("❌ Произошла ошибка при верификации", show_alert=True)


@router.callback_query(F.data.startswith("bulk_verify_clan_members:"))
async def bulk_verify_clan_members_callback(callback: CallbackQuery):
    """Массовая верификация участников зарегистрированных кланов"""
    try:
        admin_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        await callback.message.edit_text(
            "⏳ **Верификация участников кланов...**"
        )
        
        # Выполняем верификацию с критериями
        criteria = {'auto_verify_clan_members': True}
        result = await get_admin_service().bulk_verify_bindings(
            chat_id=callback.message.chat.id,
            admin_id=admin_id,
            criteria=criteria
        )
        
        if result['success']:
            verified_count = result['verified_count']
            
            result_text = (
                f"✅ **Верификация участников кланов завершена!**\n\n"
                f"🏰 Верифицировано участников зарегистрированных кланов: **{verified_count}**\n"
                f"👨‍💼 Администратор: {callback.from_user.full_name}"
            )
        else:
            result_text = f"❌ **Ошибка:** {result['error']}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 К массовым операциям",
                callback_data=f"admin_bulk_operations:{admin_id}"
            )]
        ])
        
        await callback.message.edit_text(
            result_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в bulk_verify_clan_members_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(Command("areport"))
async def binding_report_command(message: Message):
    """
    Команда для генерации детального отчета по привязкам
    Usage: /binding_report [format]
    """
    try:
        # Проверяем права администратора
        is_admin = await check_admin_permission(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        if not is_admin:
            await message.reply(
                "❌ Эта команда доступна только администраторам чата!"
            )
            return
        
        await message.reply(
            "📊 **Генерация отчета по привязкам...**\n\n"
            "Пожалуйста, подождите..."
        )
        
        # Получаем детальную аналитику
        analytics_result = await get_admin_service().get_binding_analytics(
            chat_id=message.chat.id,
            admin_id=message.from_user.id
        )
        
        if not analytics_result['success']:
            await message.reply(
                f"❌ Ошибка генерации отчета: {analytics_result['error']}"
            )
            return
        
        # Форматируем отчет
        report_text = _format_detailed_report(analytics_result)
        
        # Создаем клавиатуру с опциями
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📋 Экспорт в CSV",
                callback_data=f"export_bindings_csv:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="📊 Графики статистики",
                callback_data=f"binding_charts:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="🔄 Обновить отчет",
                callback_data=f"refresh_binding_report:{message.from_user.id}"
            )]
        ])
        
        await message.reply(
            report_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в binding_report_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при генерации отчета"
        )


def _format_verification_queue_text(queue: List[Dict], statistics: Dict) -> str:
    """Форматирование текста очереди верификации"""
    text = f"⏳ **Очередь верификации ({len(queue)})**\n\n"
    
    if statistics:
        text += (
            f"📊 **Статистика очереди:**\n"
            f"🏰 Участники кланов: {statistics.get('clan_members_count', 0)} "
            f"({statistics.get('clan_members_percentage', 0):.1f}%)\n"
            f"💎 Игроки с высокими кубками: {statistics.get('high_trophy_players', 0)}\n"
            f"📅 Среднее время ожидания: {statistics.get('average_days_waiting', 0):.1f} дней\n"
            f"🚨 Старые запросы (>7 дней): {statistics.get('old_requests', 0)}\n\n"
        )
    
    text += "Нажмите на пользователя для верификации:"
    
    return text


def _format_conflicts_text(conflicts: List[Dict]) -> str:
    """Форматирование текста конфликтов привязок"""
    text = f"⚠️ **Конфликты привязок ({len(conflicts)})**\n\n"
    
    text += (
        f"Найдено {len(conflicts)} игроков, привязанных к нескольким паспортам.\n"
        f"Это может происходить из-за:\n"
        f"• Передачи аккаунта между игроками\n"
        f"• Ошибок при вводе тега\n"
        f"• Дублирования привязок\n\n"
        f"**Требуется ручное разрешение конфликтов.**\n\n"
        f"Выберите конфликт для разрешения:"
    )
    
    return text


def _format_detailed_report(analytics: Dict) -> str:
    """Форматирование детального отчета"""
    basic_stats = analytics.get('basic_stats', {})
    verification_stats = analytics.get('verification_stats', {})
    clan_distribution = analytics.get('clan_distribution', {})
    quality_metrics = analytics.get('quality_metrics', {})
    recommendations = analytics.get('recommendations', [])
    
    report = (
        f"📊 **Детальный отчет по привязкам игроков**\n\n"
        
        f"📈 **Основная статистика:**\n"
        f"• Всего привязок: {basic_stats.get('total_bindings', 0)}\n"
        f"• Верифицировано: {verification_stats.get('verified_count', 0)}\n"
        f"• Ожидает верификации: {verification_stats.get('pending_verification', 0)}\n"
        f"• Процент верификации: {verification_stats.get('verification_rate', 0):.1f}%\n\n"
        
        f"🏰 **Распределение по кланам:**\n"
        f"• В зарегистрированных кланах: {clan_distribution.get('registered_vs_external', {}).get('registered', 0)}\n"
        f"• В других кланах: {clan_distribution.get('registered_vs_external', {}).get('external', 0)}\n"
        f"• Без клана: {clan_distribution.get('registered_vs_external', {}).get('no_clan', 0)}\n"
        f"• Уникальных кланов: {clan_distribution.get('unique_clans', 0)}\n\n"
        
        f"🎯 **Показатели качества:**\n"
        f"• Процент игроков с высокими кубками: {quality_metrics.get('high_trophy_rate', 0):.1f}%\n"
        f"• Процент состоящих в кланах: {quality_metrics.get('clan_membership_rate', 0):.1f}%\n"
        f"• Процент быстрой верификации: {quality_metrics.get('quick_verification_rate', 0):.1f}%\n"
        f"• Общий балл качества: {quality_metrics.get('quality_score', 0):.1f}/100\n\n"
    )
    
    if recommendations:
        report += f"💡 **Рекомендации администратору:**\n"
        for rec in recommendations:
            report += f"• {rec}\n"
    
    return report


# Дополнительные callback handlers для навигации
@router.callback_query(F.data.startswith("admin_main_menu:"))
async def admin_main_menu_callback(callback: CallbackQuery):
    """Возврат к главному меню админ-панели"""
    # Перенаправляем на основную команду
    fake_message = type('obj', (object,), {
        'from_user': callback.from_user,
        'chat': callback.message.chat,
        'reply': callback.message.edit_text
    })()
    
    await admin_bindings_command(fake_message)