"""
Команды для работы с расширенным функционалом CoC API - рейды, войны, ЛВК
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest
from typing import Optional
from datetime import datetime

from ..services.extended_clash_api import ExtendedClashAPI
from ..services.clan_database_service import ClanDatabaseService
from ..models.extended_clan_models import (
    WarState, MemberRole, war_state_to_emoji, role_to_emoji, format_duration
)
from ..utils.clan_helpers import get_clan_from_args, format_clan_selector_text
from ..utils.formatters import format_war_info, format_raid_info, format_cwl_info
from ..utils.error_handler import error_handler

logger = logging.getLogger(__name__)

extended_router = Router(name="extended_clash_router")

# Инициализируем сервисы (будут настроены при регистрации)
extended_api: Optional[ExtendedClashAPI] = None
db_service: Optional[ClanDatabaseService] = None


def init_extended_services(api: ExtendedClashAPI, database: ClanDatabaseService):
    """Инициализация сервисов"""
    global extended_api, db_service
    extended_api = api
    db_service = database


# Команда для получения расширенной информации о клане

@extended_router.message(Command("clan_extended"))
async def cmd_clan_extended_info(message: Message, command: CommandObject):
    """Расширенная информация о клане"""
    
    if not extended_api:
        await message.reply("❌ Сервис временно недоступен")
        return
    
    clan_tag = None
    
    # Получаем тег клана из аргументов или используем привязанный клан
    if command.args:
        clan_tag = command.args.strip()
    else:
        # Пытаемся получить привязанный клан для чата
        try:
            registered_clans = await db_service.get_chat_clans(message.chat.id)
            if registered_clans:
                clan_tag = registered_clans[0].clan_tag
        except Exception as e:
            logger.error(f"Error getting chat clans: {e}")
    
    if not clan_tag:
        await message.reply(
            "❌ Укажите тег клана или зарегистрируйте клан для чата\n"
            "Использование: `/clan_extended #CLANTAG`"
        )
        return
    
    try:
        # Показываем индикатор загрузки
        status_msg = await message.reply("🔄 Загружаю расширенную информацию о клане...")
        
        # Получаем расширенную информацию
        async with extended_api:
            clan_info = await extended_api.get_extended_clan_info(clan_tag)
        
        # Форматируем сообщение
        text = format_extended_clan_info(clan_info)
        keyboard = create_clan_extended_keyboard(clan_tag)
        
        await status_msg.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except ValueError as e:
        await message.reply(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.error(f"Error in clan_extended command: {e}")
        await message.reply("❌ Произошла ошибка при получении данных")


def format_extended_clan_info(clan_info) -> str:
    """Форматировать расширенную информацию о клане"""
    
    text = f"🏰 **{clan_info.name}** `{clan_info.tag}`\n\n"
    
    # Основная информация
    text += f"📊 **Основная информация:**\n"
    text += f"• Уровень клана: {clan_info.clan_level}\n"
    text += f"• Участников: {clan_info.members}/50\n"
    text += f"• 🏆 Очки: {format_large_number(clan_info.clan_points)}\n"
    text += f"• ⚔️ Очки ВС: {format_large_number(clan_info.clan_versus_points)}\n"
    text += f"• 🏛️ Очки столицы: {format_large_number(clan_info.clan_capital_points)}\n"
    text += f"• 🎯 Требуемые кубки: {format_large_number(clan_info.required_trophies)}\n\n"
    
    # Статистика войн
    text += f"⚔️ **Статистика войн:**\n"
    text += f"• Побед: {clan_info.war_wins} ({clan_info.war_win_rate:.1f}%)\n"
    text += f"• Поражений: {clan_info.war_losses}\n"
    text += f"• Ничьих: {clan_info.war_ties}\n"
    text += f"• Серия побед: {clan_info.war_win_streak}\n"
    text += f"• Частота войн: {clan_info.war_frequency}\n\n"
    
    # Руководство
    if clan_info.leadership:
        text += f"👑 **Руководство:**\n"
        if clan_info.leadership.leader:
            text += f"• Лидер: {clan_info.leadership.leader.name}\n"
        text += f"• Со-лидеров: {len(clan_info.leadership.co_leaders)}\n"
        text += f"• Старейшин: {len(clan_info.leadership.elders)}\n"
        text += f"• Всего руководителей: {clan_info.leadership.total_leaders}\n\n"
    
    # Средние показатели
    text += f"📈 **Средние показатели:**\n"
    text += f"• Средние кубки: {clan_info.average_trophies:.0f}\n"
    
    if clan_info.donation_stats:
        text += f"• Всего донатов: {format_large_number(clan_info.donation_stats.total_donations)}\n"
        text += f"• Активных донатеров: {clan_info.donation_stats.active_members}\n"
    
    return text


def create_clan_extended_keyboard(clan_tag: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру для расширенной информации о клане"""
    
    buttons = [
        [
            InlineKeyboardButton(
                text="⚔️ Текущая война", 
                callback_data=f"war_current:{clan_tag}"
            ),
            InlineKeyboardButton(
                text="🏛️ Рейды", 
                callback_data=f"raids:{clan_tag}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👑 Руководство", 
                callback_data=f"leadership:{clan_tag}"
            ),
            InlineKeyboardButton(
                text="🎁 Топ донатеров", 
                callback_data=f"top_donors:{clan_tag}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 История войн", 
                callback_data=f"war_history:{clan_tag}"
            ),
            InlineKeyboardButton(
                text="🏆 ЛВК", 
                callback_data=f"cwl:{clan_tag}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить", 
                callback_data=f"clan_refresh:{clan_tag}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Обработчики callback запросов

@extended_router.callback_query(F.data.startswith("war_current:"))
async def handle_current_war(callback: CallbackQuery):
    """Обработчик текущей войны"""
    
    clan_tag = callback.data.split(":", 1)[1]
    
    try:
        await callback.answer("🔄 Загружаю информацию о войне...")
        
        async with extended_api:
            war_info = await extended_api.get_current_war(clan_tag)
        
        if not war_info:
            text = f"✅ **Клан не участвует в войне**\n\n"
            text += f"Клан `{clan_tag}` сейчас не участвует в клановой войне."
        else:
            text = format_war_info(war_info)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"clan_refresh:{clan_tag}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling current war: {e}")
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)


@extended_router.callback_query(F.data.startswith("raids:"))
async def handle_capital_raids(callback: CallbackQuery):
    """Обработчик капитальных рейдов"""
    
    clan_tag = callback.data.split(":", 1)[1]
    
    try:
        await callback.answer("🔄 Загружаю данные рейдов...")
        
        async with extended_api:
            raids = await extended_api.get_capital_raid_seasons(clan_tag, limit=5)
        
        if not raids:
            text = f"🏛️ **Капитальные рейды**\n\n"
            text += f"Данные о рейдах для клана `{clan_tag}` недоступны."
        else:
            text = format_raids_info(raids, clan_tag)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"clan_refresh:{clan_tag}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling capital raids: {e}")
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)


@extended_router.callback_query(F.data.startswith("leadership:"))
async def handle_leadership(callback: CallbackQuery):
    """Обработчик руководства клана"""
    
    clan_tag = callback.data.split(":", 1)[1]
    
    try:
        await callback.answer("🔄 Загружаю список руководителей...")
        
        async with extended_api:
            clan_info = await extended_api.get_extended_clan_info(clan_tag)
        
        text = format_leadership_info(clan_info)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"clan_refresh:{clan_tag}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling leadership: {e}")
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)


@extended_router.callback_query(F.data.startswith("top_donors:"))
async def handle_top_donors(callback: CallbackQuery):
    """Обработчик топа донатеров"""
    
    clan_tag = callback.data.split(":", 1)[1]
    
    try:
        await callback.answer("🔄 Загружаю статистику донатов...")
        
        async with extended_api:
            donation_stats = await extended_api.calculate_monthly_donation_stats(clan_tag)
        
        text = format_donation_stats(donation_stats)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"clan_refresh:{clan_tag}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling top donors: {e}")
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)


@extended_router.callback_query(F.data.startswith("war_history:"))
async def handle_war_history(callback: CallbackQuery):
    """Обработчик истории войн"""
    
    clan_tag = callback.data.split(":", 1)[1]
    
    try:
        await callback.answer("🔄 Загружаю историю войн...")
        
        async with extended_api:
            war_history = await extended_api.get_war_log(clan_tag, limit=10)
        
        text = format_war_history(war_history)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"clan_refresh:{clan_tag}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling war history: {e}")
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)


@extended_router.callback_query(F.data.startswith("cwl:"))
async def handle_cwl_info(callback: CallbackQuery):
    """Обработчик информации о ЛВК"""
    
    clan_tag = callback.data.split(":", 1)[1]
    
    try:
        await callback.answer("🔄 Загружаю информацию о ЛВК...")
        
        async with extended_api:
            cwl_info = await extended_api.get_cwl_info(clan_tag)
        
        if not cwl_info:
            text = f"🏆 **Лига Войн Кланов**\n\n"
            text += f"Клан `{clan_tag}` сейчас не участвует в ЛВК."
        else:
            text = format_cwl_info(cwl_info)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"clan_refresh:{clan_tag}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling CWL info: {e}")
        await callback.answer("❌ Ошибка загрузки данных", show_alert=True)


@extended_router.callback_query(F.data.startswith("clan_refresh:"))
async def handle_clan_refresh(callback: CallbackQuery):
    """Обработчик обновления информации о клане"""
    
    clan_tag = callback.data.split(":", 1)[1]
    
    try:
        await callback.answer("🔄 Обновляю информацию...")
        
        # Очищаем кеш
        if extended_api:
            extended_api.clear_cache()
        
        async with extended_api:
            clan_info = await extended_api.get_extended_clan_info(clan_tag)
        
        text = format_extended_clan_info(clan_info)
        keyboard = create_clan_extended_keyboard(clan_tag)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error refreshing clan info: {e}")
        await callback.answer("❌ Ошибка обновления данных", show_alert=True)


# Вспомогательные функции форматирования

def format_war_info(war_info) -> str:
    """Форматировать информацию о войне"""
    
    state_emoji = war_state_to_emoji(war_info.state)
    state_text = {
        WarState.PREPARATION: "Подготовка",
        WarState.IN_WAR: "Идет война",
        WarState.WAR_ENDED: "Война окончена",
        WarState.NOT_IN_WAR: "Не в войне"
    }.get(war_info.state, "Неизвестно")
    
    text = f"⚔️ **Клановая война** {state_emoji}\n\n"
    text += f"**Статус:** {state_text}\n"
    text += f"**Размер:** {war_info.team_size} vs {war_info.team_size}\n\n"
    
    # Информация о кланах
    text += f"🏰 **{war_info.clan_name}**\n"
    text += f"• Атак: {war_info.clan_attacks}/{war_info.team_size * war_info.attacks_per_member}\n"
    text += f"• Звезд: {war_info.clan_stars}\n"
    text += f"• Разрушения: {war_info.clan_destruction_percentage:.1f}%\n\n"
    
    text += f"🏰 **{war_info.opponent_name}**\n"
    text += f"• Атак: {war_info.opponent_attacks}/{war_info.team_size * war_info.attacks_per_member}\n"
    text += f"• Звезд: {war_info.opponent_stars}\n"
    text += f"• Разрушения: {war_info.opponent_destruction_percentage:.1f}%\n\n"
    
    # Время
    if war_info.start_time:
        text += f"🕐 **Начало:** {war_info.start_time.strftime('%d.%m %H:%M')}\n"
    if war_info.end_time:
        text += f"🕐 **Конец:** {war_info.end_time.strftime('%d.%m %H:%M')}\n"
    
    # Результат
    if war_info.state == WarState.WAR_ENDED:
        victory = war_info.is_victory
        if victory is True:
            text += f"\n🎉 **ПОБЕДА!**"
        elif victory is False:
            text += f"\n😞 **Поражение**"
        else:
            text += f"\n🤝 **Ничья**"
    
    return text


def format_raids_info(raids, clan_tag: str) -> str:
    """Форматировать информацию о рейдах"""
    
    text = f"🏛️ **Капитальные рейды** `{clan_tag}`\n\n"
    
    if not raids:
        text += "Нет данных о рейдах"
        return text
    
    text += f"📊 **Последние {len(raids)} рейдов:**\n\n"
    
    for i, raid in enumerate(raids[:5], 1):
        text += f"**{i}. Рейд {raid.end_time.strftime('%d.%m')}**\n"
        text += f"• 💰 Лут: {format_large_number(raid.capital_total_loot)}\n"
        text += f"• 🏛️ Завершено: {raid.raids_completed}\n"
        text += f"• ⚔️ Атак: {raid.total_attacks}\n"
        text += f"• 🏆 Награды: {format_large_number(raid.offensive_reward + raid.defensive_reward)}\n\n"
    
    # Общая статистика
    total_loot = sum(raid.capital_total_loot for raid in raids)
    total_attacks = sum(raid.total_attacks for raid in raids)
    total_raids_completed = sum(raid.raids_completed for raid in raids)
    
    text += f"📈 **Общая статистика:**\n"
    text += f"• Всего лута: {format_large_number(total_loot)}\n"
    text += f"• Всего атак: {total_attacks}\n"
    text += f"• Рейдов завершено: {total_raids_completed}\n"
    
    return text


def format_leadership_info(clan_info) -> str:
    """Форматировать информацию о руководстве"""
    
    text = f"👑 **Руководство клана** `{clan_info.tag}`\n\n"
    
    if not clan_info.leadership:
        text += "Нет данных о руководстве"
        return text
    
    # Лидер
    if clan_info.leadership.leader:
        leader = clan_info.leadership.leader
        text += f"👑 **ЛИДЕР**\n"
        text += f"• {leader.name}\n"
        text += f"• 🏆 {format_large_number(leader.trophies)} кубков\n"
        text += f"• 🎁 {format_large_number(leader.donations)} донатов\n"
        text += f"• #{leader.clan_rank} в клане\n\n"
    
    # Со-лидеры
    if clan_info.leadership.co_leaders:
        text += f"🔱 **СО-ЛИДЕРЫ** ({len(clan_info.leadership.co_leaders)})\n"
        for co_leader in clan_info.leadership.co_leaders[:10]:  # Показываем топ-10
            text += f"• {co_leader.name} - 🏆 {format_large_number(co_leader.trophies)}\n"
        
        if len(clan_info.leadership.co_leaders) > 10:
            text += f"• ... и еще {len(clan_info.leadership.co_leaders) - 10}\n"
        text += "\n"
    
    # Старейшины
    if clan_info.leadership.elders:
        text += f"⭐ **СТАРЕЙШИНЫ** ({len(clan_info.leadership.elders)})\n"
        for elder in clan_info.leadership.elders[:15]:  # Показываем топ-15
            text += f"• {elder.name} - 🏆 {format_large_number(elder.trophies)}\n"
        
        if len(clan_info.leadership.elders) > 15:
            text += f"• ... и еще {len(clan_info.leadership.elders) - 15}\n"
    
    text += f"\n📊 **Всего руководителей:** {clan_info.leadership.total_leaders}/{clan_info.members}"
    
    return text


def format_donation_stats(donation_stats) -> str:
    """Форматировать статистику донатов"""
    
    text = f"🎁 **Статистика донатов**\n"
    text += f"**{donation_stats.month:02d}.{donation_stats.year}** `{donation_stats.clan_tag}`\n\n"
    
    text += f"📊 **Общая статистика:**\n"
    text += f"• Всего донатов: {format_large_number(donation_stats.total_donations)}\n"
    text += f"• Всего получено: {format_large_number(donation_stats.total_received)}\n"
    text += f"• Активных участников: {donation_stats.active_members}\n"
    text += f"• В среднем на участника: {donation_stats.average_donations:.0f}\n\n"
    
    if donation_stats.top_donors:
        text += f"🏆 **Топ-{min(15, len(donation_stats.top_donors))} донатеров:**\n\n"
        
        for i, donor in enumerate(donation_stats.top_donors[:15], 1):
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            ratio_text = ""
            if donor.donations_received > 0:
                ratio = donor.donations / donor.donations_received
                ratio_text = f" (↗️{ratio:.1f})"
            
            text += f"{medal}`{i}.` **{donor.player_name}**\n"
            text += f"     🎁 {format_large_number(donor.donations)}{ratio_text}\n\n"
    
    return text


def format_war_history(war_history) -> str:
    """Форматировать историю войн"""
    
    text = f"📊 **История войн** `{war_history.clan_tag}`\n\n"
    
    if not war_history.wars:
        text += "Нет данных об истории войн"
        return text
    
    text += f"**Общая статистика:**\n"
    text += f"• Всего войн: {war_history.total_wars}\n"
    text += f"• Побед: {war_history.victories} ({war_history.win_rate:.1f}%)\n"
    text += f"• Поражений: {war_history.defeats}\n"
    text += f"• Ничьих: {war_history.draws}\n\n"
    
    text += f"🏆 **Последние {min(10, len(war_history.wars))} войн:**\n\n"
    
    for i, war in enumerate(war_history.wars[:10], 1):
        result_emoji = ""
        if war.is_victory is True:
            result_emoji = "✅"
        elif war.is_victory is False:
            result_emoji = "❌"
        else:
            result_emoji = "🤝"
        
        date_str = war.end_time.strftime('%d.%m') if war.end_time else "???"
        
        text += f"{result_emoji} **{i}.** {date_str} vs **{war.opponent_name}**\n"
        text += f"     {war.clan_stars}⭐ vs {war.opponent_stars}⭐ ({war.team_size}v{war.team_size})\n\n"
    
    return text


def format_cwl_info(cwl_info) -> str:
    """Форматировать информацию о ЛВК"""
    
    text = f"🏆 **Лига Войн Кланов**\n"
    text += f"**Сезон:** {cwl_info.season}\n\n"
    
    state_text = {
        "preparation": "Подготовка",
        "inWar": "Идет война", 
        "warEnded": "Война окончена",
        "ended": "Сезон завершен"
    }.get(cwl_info.state.value, "Неизвестно")
    
    text += f"**Статус:** {state_text}\n"
    
    if cwl_info.rounds:
        text += f"**Раундов:** {len(cwl_info.rounds)}\n"
        text += f"**Всего звезд:** {cwl_info.total_stars}\n"
    
    return text


# Дополнительные команды

@extended_router.message(Command("war"))
@error_handler
async def cmd_current_war(message: Message, command: CommandObject):
    """Текущая война клана"""
    
    # Получаем клан по аргументу (номер/буквы) или основной
    clan = await get_clan_from_args(db_service, message.chat.id, command.args)
    
    if not clan:
        await message.reply(
            "❌ Клан не найден!\n\n"
            "Используйте:\n"
            "• `/war` - основной клан\n"
            "• `/war 2` - клан №2\n"
            "• `/war wa` - клан по первым буквам\n"
            "• `/clan_list` - список кланов"
        )
        return
    
    clan_tag = clan.clan_tag
    clan_name = clan.clan_name
    
    try:
        async with extended_api:
            war_info = await extended_api.get_current_war(clan_tag)
        
        if not war_info:
            await message.reply(f"✅ Клан **{clan_name}** `{clan_tag}` не участвует в войне")
            return
        
        text = format_war_info(war_info)
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in war command: {e}")
        await message.reply("❌ Ошибка получения данных о войне")


@extended_router.message(Command("raids"))
@error_handler
async def cmd_capital_raids(message: Message, command: CommandObject):
    """Капитальные рейды клана"""
    
    # Получаем клан по аргументу (номер/буквы) или основной
    clan = await get_clan_from_args(db_service, message.chat.id, command.args)
    
    if not clan:
        await message.reply(
            "❌ Клан не найден!\n\n"
            "Используйте:\n"
            "• `/raids` - основной клан\n"
            "• `/raids 2` - клан №2\n"
            "• `/raids wa` - клан по первым буквам\n"
            "• `/clan_list` - список кланов"
        )
        return
    
    clan_tag = clan.clan_tag
    
    try:
        async with extended_api:
            raids = await extended_api.get_capital_raid_seasons(clan_tag, limit=5)
        
        text = format_raids_info(raids, clan_tag)
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in raids command: {e}")
        await message.reply("❌ Ошибка получения данных о рейдах")


@extended_router.message(Command("leadership"))
@error_handler
async def cmd_leadership(message: Message, command: CommandObject):
    """Руководство клана"""
    
    # Получаем клан по аргументу (номер/буквы) или основной
    clan = await get_clan_from_args(db_service, message.chat.id, command.args)
    
    if not clan:
        await message.reply(
            "❌ Клан не найден!\n\n"
            "Используйте:\n"
            "• `/leadership` - основной клан\n"
            "• `/leadership 2` - клан №2\n"
            "• `/leadership wa` - клан по первым буквам\n"
            "• `/clan_list` - список кланов"
        )
        return
    
    clan_tag = clan.clan_tag
    
    try:
        async with extended_api:
            clan_info = await extended_api.get_extended_clan_info(clan_tag)
        
        text = format_leadership_info(clan_info)
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in leadership command: {e}")
        await message.reply("❌ Ошибка получения данных о руководстве")


@extended_router.message(Command("top_donors"))
@error_handler
async def cmd_top_donors(message: Message, command: CommandObject):
    """Топ донатеров клана за текущий месяц"""
    
    # Получаем клан по аргументу (номер/буквы) или основной
    clan = await get_clan_from_args(db_service, message.chat.id, command.args)
    
    if not clan:
        await message.reply(
            "❌ Клан не найден!\n\n"
            "Используйте:\n"
            "• `/top_donors` - основной клан\n"
            "• `/top_donors 2` - клан №2\n"
            "• `/top_donors wa` - клан по первым буквам\n"
            "• `/clan_list` - список кланов"
        )
        return
    
    clan_tag = clan.clan_tag
    
    try:
        async with extended_api:
            donation_stats = await extended_api.calculate_monthly_donation_stats(clan_tag)
        
        text = format_donation_stats(donation_stats)
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in top_donors command: {e}")
        await message.reply("❌ Ошибка получения статистики донатов")