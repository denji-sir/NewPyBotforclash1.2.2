"""
Хандлеры команд для работы с паспортами игроков
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest

from ..models.passport_models import (
    PassportInfo, PassportOperationLog, PassportStatus, PassportAlreadyExists,
    PassportNotFound, PassportValidationError, PassportTheme, PassportSettings
)
from ..services.passport_database_service import get_passport_db_service
from ..services.clan_database_service import get_clan_db_service
from ..utils.validators import format_number, format_date, format_role_emoji, format_role_name

logger = logging.getLogger(__name__)

# Создаем роутер для команд паспортов
passport_router = Router(name="passport_router")


@passport_router.message(Command("create_passport"))
async def create_passport_command(message: Message, command: CommandObject):
    """
    Создание нового паспорта игрока
    Синтаксис: /create_passport [имя]
    """
    try:
        passport_service = get_passport_db_service()
        clan_service = get_clan_db_service()
        
        # Проверяем, нет ли уже паспорта
        existing_passport = await passport_service.get_passport_by_user(
            message.from_user.id, message.chat.id
        )
        
        if existing_passport:
            await message.reply(
                f"📋 **У вас уже есть паспорт!**\n\n"
                f"Используйте `/passport` для просмотра или `/edit_passport` для редактирования.",
                parse_mode="Markdown"
            )
            return
        
        # Получаем отображаемое имя
        display_name = None
        if command.args:
            display_name = command.args.strip()
        else:
            display_name = message.from_user.full_name or message.from_user.username
        
        # Получаем доступные кланы в чате
        available_clans = await clan_service.get_chat_clans(message.chat.id)
        
        if not available_clans:
            # Создаем паспорт без клана
            passport = await passport_service.create_passport(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                username=message.from_user.username,
                display_name=display_name
            )
            
            # Логируем создание
            log_entry = PassportOperationLog.create_log(
                operation_type='create',
                passport_id=passport.id,
                user_id=message.from_user.id,
                username=message.from_user.username,
                operation_details={'display_name': display_name}
            )
            await passport_service.log_operation(log_entry)
            
            await message.reply(
                f"✅ **Паспорт создан!**\n\n"
                f"👤 **Имя:** {display_name}\n"
                f"📅 **Создан:** только что\n\n"
                f"💡 **Совет:** В этом чате пока нет зарегистрированных кланов. "
                f"Администраторы могут добавить кланы через `/register_clan`.\n\n"
                f"Используйте `/passport` для просмотра своего паспорта.",
                parse_mode="Markdown"
            )
            return
        
        # Показываем выбор клана
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        # Кнопки для выбора клана
        for i, clan in enumerate(available_clans, 1):
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"🏰 {i}. {clan.clan_name} ({clan.member_count}/50)",
                    callback_data=f"create_passport_clan:{clan.id}:{display_name}"
                )
            ])
        
        # Кнопка "без клана"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="❌ Создать без клана",
                callback_data=f"create_passport_clan:0:{display_name}"
            )
        ])
        
        # Кнопка отмены
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="🚫 Отменить",
                callback_data="create_passport_cancel"
            )
        ])
        
        await message.reply(
            f"📋 **Создание паспорта**\n\n"
            f"👤 **Имя:** {display_name}\n\n"
            f"🏰 **Выберите предпочитаемый клан:**\n"
            f"(Вы сможете изменить его позже)\n\n"
            f"📝 **Доступные кланы в чате:**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except PassportAlreadyExists:
        await message.reply(
            "📋 **У вас уже есть паспорт!**\n\n"
            "Используйте `/passport` для просмотра."
        )
    except Exception as e:
        logger.error(f"Error in create_passport_command: {e}")
        await message.reply(
            "❌ **Ошибка создания паспорта**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@passport_router.callback_query(F.data.startswith("create_passport_clan:"))
async def create_passport_with_clan_callback(callback: CallbackQuery):
    """Обработка выбора клана при создании паспорта"""
    try:
        data_parts = callback.data.split(":")
        clan_id = int(data_parts[1])
        display_name = data_parts[2] if len(data_parts) > 2 else callback.from_user.full_name
        
        passport_service = get_passport_db_service()
        
        # Создаем паспорт
        preferred_clan_id = clan_id if clan_id > 0 else None
        
        passport = await passport_service.create_passport(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            username=callback.from_user.username,
            display_name=display_name,
            preferred_clan_id=preferred_clan_id
        )
        
        # Логируем создание
        log_entry = PassportOperationLog.create_log(
            operation_type='create',
            passport_id=passport.id,
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            operation_details={
                'display_name': display_name,
                'preferred_clan_id': preferred_clan_id
            }
        )
        await passport_service.log_operation(log_entry)
        
        # Формируем ответ
        response_text = (
            f"✅ **Паспорт создан!**\n\n"
            f"👤 **Имя:** {display_name}\n"
        )
        
        if preferred_clan_id and passport.preferred_clan_name:
            response_text += f"🏰 **Предпочитаемый клан:** {passport.preferred_clan_name}\n"
        else:
            response_text += f"🏰 **Клан:** не выбран\n"
        
        response_text += (
            f"📅 **Создан:** только что\n\n"
            f"🎯 **Следующие шаги:**\n"
            f"• `/passport` - посмотреть паспорт\n"
            f"• `/bind_player <тег>` - привязать игрока CoC\n"
            f"• `/edit_passport` - редактировать информацию"
        )
        
        await callback.message.edit_text(
            response_text,
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Паспорт создан!")
        
    except Exception as e:
        logger.error(f"Error in create_passport_with_clan_callback: {e}")
        await callback.answer("❌ Ошибка создания паспорта", show_alert=True)


@passport_router.callback_query(F.data == "create_passport_cancel")
async def create_passport_cancel_callback(callback: CallbackQuery):
    """Отмена создания паспорта"""
    await callback.message.edit_text("🚫 **Создание паспорта отменено.**")
    await callback.answer("Отменено")


@passport_router.message(Command("passport"))
async def passport_command(message: Message, command: CommandObject):
    """
    Показать паспорт игрока
    Синтаксис: /passport [@пользователь|ID]
    """
    try:
        passport_service = get_passport_db_service()
        
        # Определяем чей паспорт показывать
        target_user_id = message.from_user.id
        target_username = message.from_user.username
        
        if command.args:
            arg = command.args.strip()
            
            # Если указан @username
            if arg.startswith('@'):
                target_username = arg[1:]
                # В реальной реализации нужно получить user_id по username
                # Здесь упрощенная версия
                await message.reply(
                    "❌ **Поиск по username пока не поддерживается**\n\n"
                    "Используйте `/passport` без аргументов для просмотра своего паспорта."
                )
                return
            
            # Если указан ID
            try:
                target_user_id = int(arg)
            except ValueError:
                await message.reply(
                    "❌ **Неверный формат!**\n\n"
                    "Используйте `/passport` для своего паспорта или `/passport @username`"
                )
                return
        
        # Получаем паспорт
        passport = await passport_service.get_passport_by_user(target_user_id, message.chat.id)
        
        if not passport:
            if target_user_id == message.from_user.id:
                await message.reply(
                    "📋 **У вас пока нет паспорта**\n\n"
                    "Создайте его командой `/create_passport`"
                )
            else:
                await message.reply(
                    "📋 **У этого пользователя нет паспорта**"
                )
            return
        
        # Проверяем приватность (если не свой паспорт)
        if target_user_id != message.from_user.id and passport.settings.privacy_level >= 3:
            await message.reply(
                "🔒 **Этот паспорт приватный**\n\n"
                "Владелец скрыл свой паспорт от посторонних."
            )
            return
        
        # Формируем отображение паспорта
        passport_text = await _format_passport_display(passport, is_owner=(target_user_id == message.from_user.id))
        
        # Создаем клавиатуру управления (только для владельца)
        keyboard = None
        if target_user_id == message.from_user.id:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Редактировать",
                        callback_data="passport_edit"
                    ),
                    InlineKeyboardButton(
                        text="⚙️ Настройки",
                        callback_data="passport_settings"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data="passport_refresh"
                    )
                ]
            ])
        
        await message.reply(passport_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in passport_command: {e}")
        await message.reply(
            "❌ **Ошибка получения паспорта**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@passport_router.message(Command("edit_passport"))
async def edit_passport_command(message: Message, command: CommandObject):
    """
    Редактирование паспорта
    Синтаксис: /edit_passport [поле] [значение]
    """
    try:
        passport_service = get_passport_db_service()
        
        # Получаем паспорт пользователя
        passport = await passport_service.get_passport_by_user(
            message.from_user.id, message.chat.id
        )
        
        if not passport:
            await message.reply(
                "📋 **У вас нет паспорта**\n\n"
                "Создайте его командой `/create_passport`"
            )
            return
        
        if not command.args:
            # Показываем меню редактирования
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить имя",
                        callback_data="edit_passport_name"
                    ),
                    InlineKeyboardButton(
                        text="📝 Изменить био",
                        callback_data="edit_passport_bio"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏰 Сменить клан",
                        callback_data="edit_passport_clan"
                    ),
                    InlineKeyboardButton(
                        text="🎨 Сменить тему",
                        callback_data="edit_passport_theme"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔒 Приватность",
                        callback_data="edit_passport_privacy"
                    )
                ]
            ])
            
            await message.reply(
                f"✏️ **Редактирование паспорта**\n\n"
                f"**Текущие данные:**\n"
                f"👤 **Имя:** {passport.display_name}\n"
                f"📝 **Био:** {passport.bio or 'не указано'}\n"
                f"🏰 **Клан:** {passport.preferred_clan_name or 'не выбран'}\n"
                f"🎨 **Тема:** {passport.settings.theme.value}\n"
                f"🔒 **Приватность:** уровень {passport.settings.privacy_level}\n\n"
                f"Выберите что хотите изменить:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return
        
        # Парсим аргументы для быстрого редактирования
        args = command.args.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "❌ **Неверный формат!**\n\n"
                "**Использование:** `/edit_passport <поле> <значение>`\n\n"
                "**Поля:** name, bio, clan\n"
                "**Пример:** `/edit_passport name Новое Имя`"
            )
            return
        
        field, value = args
        field = field.lower()
        
        # Обновляем поле
        update_success = False
        
        if field == "name":
            if len(value) > 50:
                await message.reply("❌ **Имя слишком длинное (максимум 50 символов)**")
                return
            
            update_success = await passport_service.update_passport(
                passport.id, display_name=value
            )
            
        elif field == "bio":
            if len(value) > 200:
                await message.reply("❌ **Био слишком длинное (максимум 200 символов)**")
                return
            
            update_success = await passport_service.update_passport(
                passport.id, bio=value
            )
            
        else:
            await message.reply(
                f"❌ **Неизвестное поле '{field}'**\n\n"
                "Доступные поля: name, bio"
            )
            return
        
        if update_success:
            # Логируем изменение
            log_entry = PassportOperationLog.create_log(
                operation_type='update',
                passport_id=passport.id,
                user_id=message.from_user.id,
                username=message.from_user.username,
                operation_details={field: value}
            )
            await passport_service.log_operation(log_entry)
            
            await message.reply(
                f"✅ **Паспорт обновлен!**\n\n"
                f"**{field.title()}** изменено на: {value}"
            )
        else:
            await message.reply("❌ **Ошибка обновления паспорта**")
            
    except Exception as e:
        logger.error(f"Error in edit_passport_command: {e}")
        await message.reply(
            "❌ **Ошибка редактирования паспорта**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@passport_router.message(Command("passport_list"))
async def passport_list_command(message: Message):
    """
    Список всех паспортов в чате
    """
    try:
        passport_service = get_passport_db_service()
        
        # Получаем все активные паспорты
        passports = await passport_service.get_chat_passports(
            message.chat.id, PassportStatus.ACTIVE
        )
        
        if not passports:
            await message.reply(
                "📋 **В этом чате пока нет паспортов**\n\n"
                "Создайте первый паспорт командой `/create_passport`"
            )
            return
        
        # Получаем статистику
        stats = await passport_service.get_passport_stats_summary(message.chat.id)
        
        # Формируем список
        text = (
            f"📋 **Паспорта чата**\n\n"
            f"📊 **Статистика:**\n"
            f"• 👤 Всего паспортов: {stats['total_passports']}\n"
            f"• ✅ Активных: {stats['active_passports']}\n"
            f"• 🔗 С привязанными игроками: {stats['bound_passports']}\n"
            f"• 🏰 Выбрали кланы: {stats['clan_bound_passports']}\n\n"
            f"👥 **Список участников:**\n"
        )
        
        # Сортируем по времени создания (новые сначала)
        passports.sort(key=lambda p: p.created_at or datetime.min, reverse=True)
        
        for i, passport in enumerate(passports[:20], 1):  # Показываем максимум 20
            # Формируем информацию об участнике
            name = passport.display_name or passport.username or f"User {passport.user_id}"
            
            # Добавляем эмодзи статуса
            status_emoji = "✅" if passport.player_binding else "⏳"
            clan_info = f" | 🏰 {passport.preferred_clan_name[:15]}..." if passport.preferred_clan_name else ""
            
            text += f"{i}. {status_emoji} **{name}**{clan_info}\n"
        
        if len(passports) > 20:
            text += f"\n... и еще {len(passports) - 20} паспортов"
        
        text += f"\n\n💡 **Легенда:** ✅ - игрок привязан, ⏳ - игрок не привязан"
        
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in passport_list_command: {e}")
        await message.reply(
            "❌ **Ошибка получения списка паспортов**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


async def _format_passport_display(passport: PassportInfo, is_owner: bool = False) -> str:
    """
    Форматирование отображения паспорта
    
    Args:
        passport: Информация о паспорте
        is_owner: Является ли просматривающий владельцем
        
    Returns:
        str: Отформатированный текст паспорта
    """
    # Заголовок
    text = f"📋 **Паспорт игрока**\n\n"
    
    # Основная информация
    text += f"👤 **{passport.display_name}**"
    if passport.username:
        text += f" (@{passport.username})"
    text += "\n"
    
    # Статус
    status_emojis = {
        PassportStatus.ACTIVE: "✅ Активный",
        PassportStatus.INACTIVE: "⏸️ Неактивный", 
        PassportStatus.PENDING: "⏳ Ожидание",
        PassportStatus.BLOCKED: "🚫 Заблокирован"
    }
    text += f"📊 **Статус:** {status_emojis.get(passport.status, passport.status.value)}\n"
    
    # Био
    if passport.bio:
        text += f"📝 **О себе:** {passport.bio}\n"
    
    text += "\n"
    
    # Информация о клане
    text += "🏰 **Клан:**\n"
    if passport.preferred_clan_name:
        text += f"• Предпочитаемый: {passport.preferred_clan_name}\n"
        if passport.preferred_clan_tag:
            text += f"• Тег: `{passport.preferred_clan_tag}`\n"
    else:
        text += "• Не выбран\n"
    
    # Привязка игрока
    text += "\n🎮 **Игрок Clash of Clans:**\n"
    if passport.player_binding:
        binding = passport.player_binding
        text += f"• **{binding.player_name}** `{binding.player_tag}`\n"
        
        if binding.verified:
            text += "• ✅ Верифицирован"
            if binding.verified_at:
                text += f" {format_date(binding.verified_at)}"
            text += "\n"
        else:
            text += "• ⏳ Ожидает верификации\n"
            
        if binding.clan_name and binding.clan_name != passport.preferred_clan_name:
            text += f"• 🏰 Текущий клан: {binding.clan_name}\n"
    else:
        text += "• Не привязан\n"
        text += "• Используйте `/bind_player <тег>` для привязки\n"
    
    # Статистика (если разрешено настройками)
    if passport.settings.show_stats:
        text += f"\n📊 **Статистика:**\n"
        text += f"• 💬 Сообщений: {format_number(passport.stats.messages_count)}\n"
        text += f"• 🤖 Команд использовано: {passport.stats.commands_used}\n"
        text += f"• 📅 Дней активности: {passport.stats.days_active}\n"
        
        if passport.stats.last_activity:
            text += f"• 🕐 Последняя активность: {format_date(passport.stats.last_activity)}\n"
    
    # Дополнительная информация для владельца
    if is_owner:
        text += f"\n🔧 **Настройки:**\n"
        text += f"• 🎨 Тема: {passport.settings.theme.value}\n"
        text += f"• 🔒 Приватность: уровень {passport.settings.privacy_level}\n"
    
    # Информация о создании
    text += f"\n📅 **Создан:** {format_date(passport.created_at)}\n"
    if passport.updated_at and passport.updated_at != passport.created_at:
        text += f"🔄 **Обновлен:** {format_date(passport.updated_at)}"
    
    return text


@passport_router.callback_query(F.data == "passport_edit")
async def passport_edit_callback(callback: CallbackQuery):
    """Меню редактирования паспорта"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✏️ Изменить имя",
                callback_data="edit_passport_name"
            ),
            InlineKeyboardButton(
                text="📝 Изменить био",
                callback_data="edit_passport_bio"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏰 Сменить клан",
                callback_data="edit_passport_clan"
            ),
            InlineKeyboardButton(
                text="🎨 Сменить тему",
                callback_data="edit_passport_theme"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к паспорту",
                callback_data="passport_refresh"
            )
        ]
    ])
    
    await callback.message.edit_text(
        "✏️ **Редактирование паспорта**\n\n"
        "Выберите что хотите изменить:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@passport_router.callback_query(F.data == "passport_settings")
async def passport_settings_callback(callback: CallbackQuery):
    """Настройки паспорта"""
    try:
        passport_service = get_passport_db_service()
        passport = await passport_service.get_passport_by_user(
            callback.from_user.id, callback.message.chat.id
        )
        
        if not passport:
            await callback.answer("❌ Паспорт не найден", show_alert=True)
            return
        
        # Эмодзи для настроек
        privacy_emoji = ["🌍", "👥", "🔒"][passport.settings.privacy_level - 1]
        theme_emoji = {
            "default": "🎨",
            "dark": "🌙", 
            "clan": "🏰",
            "achievements": "🏆",
            "minimalist": "⚪"
        }.get(passport.settings.theme.value, "🎨")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{privacy_emoji} Приватность (ур. {passport.settings.privacy_level})",
                    callback_data="settings_privacy"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{theme_emoji} Тема ({passport.settings.theme.value})",
                    callback_data="settings_theme"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Показывать статистику" if passport.settings.show_stats else "📊 Скрыть статистику",
                    callback_data="settings_toggle_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏰 Показывать клан" if passport.settings.show_clan_info else "🏰 Скрыть клан",
                    callback_data="settings_toggle_clan"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к паспорту",
                    callback_data="passport_refresh"
                )
            ]
        ])
        
        await callback.message.edit_text(
            f"⚙️ **Настройки паспорта**\n\n"
            f"**Текущие настройки:**\n"
            f"• {privacy_emoji} **Приватность:** уровень {passport.settings.privacy_level}\n"
            f"• {theme_emoji} **Тема:** {passport.settings.theme.value}\n"
            f"• 📊 **Статистика:** {'показывать' if passport.settings.show_stats else 'скрыть'}\n"
            f"• 🏰 **Информация о клане:** {'показывать' if passport.settings.show_clan_info else 'скрыть'}\n\n"
            f"**Уровни приватности:**\n"
            f"🌍 1 - Публичный (все видят)\n"
            f"👥 2 - Участники чата\n"
            f"🔒 3 - Только я",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in passport_settings_callback: {e}")
        await callback.answer("❌ Ошибка загрузки настроек", show_alert=True)


@passport_router.callback_query(F.data == "settings_privacy")
async def settings_privacy_callback(callback: CallbackQuery):
    """Настройка приватности"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌍 Уровень 1 - Публичный",
                callback_data="privacy_set:1"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Уровень 2 - Участники чата",
                callback_data="privacy_set:2"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔒 Уровень 3 - Только я",
                callback_data="privacy_set:3"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к настройкам",
                callback_data="passport_settings"
            )
        ]
    ])
    
    await callback.message.edit_text(
        "🔒 **Настройка приватности**\n\n"
        "**Выберите уровень приватности:**\n\n"
        "🌍 **Уровень 1 - Публичный**\n"
        "Паспорт видят все участники чата\n\n"
        "👥 **Уровень 2 - Участники чата**\n"
        "Паспорт видят только участники этого чата\n\n"
        "🔒 **Уровень 3 - Только я**\n"
        "Паспорт видите только вы",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@passport_router.callback_query(F.data.startswith("privacy_set:"))
async def privacy_set_callback(callback: CallbackQuery):
    """Установка уровня приватности"""
    try:
        privacy_level = int(callback.data.split(":")[1])
        
        passport_service = get_passport_db_service()
        passport = await passport_service.get_passport_by_user(
            callback.from_user.id, callback.message.chat.id
        )
        
        if not passport:
            await callback.answer("❌ Паспорт не найден", show_alert=True)
            return
        
        # Обновляем настройки
        new_settings = passport.settings
        new_settings.privacy_level = privacy_level
        
        success = await passport_service.update_passport(
            passport.id, settings=new_settings
        )
        
        if success:
            privacy_names = {1: "Публичный", 2: "Участники чата", 3: "Только я"}
            await callback.answer(f"✅ Приватность: {privacy_names[privacy_level]}")
            
            # Возвращаемся к настройкам
            await passport_settings_callback(callback)
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in privacy_set_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@passport_router.callback_query(F.data == "settings_toggle_stats")
async def settings_toggle_stats_callback(callback: CallbackQuery):
    """Переключение отображения статистики"""
    try:
        passport_service = get_passport_db_service()
        passport = await passport_service.get_passport_by_user(
            callback.from_user.id, callback.message.chat.id
        )
        
        if not passport:
            await callback.answer("❌ Паспорт не найден", show_alert=True)
            return
        
        # Переключаем настройку
        new_settings = passport.settings
        new_settings.show_stats = not new_settings.show_stats
        
        success = await passport_service.update_passport(
            passport.id, settings=new_settings
        )
        
        if success:
            status = "показывать" if new_settings.show_stats else "скрывать"
            await callback.answer(f"✅ Статистика: {status}")
            
            # Возвращаемся к настройкам
            await passport_settings_callback(callback)
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in settings_toggle_stats_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@passport_router.callback_query(F.data == "settings_toggle_clan")
async def settings_toggle_clan_callback(callback: CallbackQuery):
    """Переключение отображения информации о клане"""
    try:
        passport_service = get_passport_db_service()
        passport = await passport_service.get_passport_by_user(
            callback.from_user.id, callback.message.chat.id
        )
        
        if not passport:
            await callback.answer("❌ Паспорт не найден", show_alert=True)
            return
        
        # Переключаем настройку
        new_settings = passport.settings
        new_settings.show_clan_info = not new_settings.show_clan_info
        
        success = await passport_service.update_passport(
            passport.id, settings=new_settings
        )
        
        if success:
            status = "показывать" if new_settings.show_clan_info else "скрывать"
            await callback.answer(f"✅ Информация о клане: {status}")
            
            # Возвращаемся к настройкам
            await passport_settings_callback(callback)
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in settings_toggle_clan_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@passport_router.callback_query(F.data == "passport_refresh")
async def passport_refresh_callback(callback: CallbackQuery):
    """Обновление отображения паспорта"""
    try:
        passport_service = get_passport_db_service()
        passport = await passport_service.get_passport_by_user(
            callback.from_user.id, callback.message.chat.id
        )
        
        if not passport:
            await callback.answer("❌ Паспорт не найден", show_alert=True)
            return
        
        # Формируем обновленное отображение
        passport_text = await _format_passport_display(passport, is_owner=True)
        
        # Клавиатура управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data="passport_edit"
                ),
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="passport_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="passport_refresh"
                )
            ]
        ])
        
        await callback.message.edit_text(
            passport_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer("🔄 Обновлено")
        
    except Exception as e:
        logger.error(f"Error in passport_refresh_callback: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)


@passport_router.message(Command("delete_passport"))
async def delete_passport_command(message: Message):
    """
    Удаление паспорта (с подтверждением)
    """
    try:
        passport_service = get_passport_db_service()
        
        # Получаем паспорт пользователя
        passport = await passport_service.get_passport_by_user(
            message.from_user.id, message.chat.id
        )
        
        if not passport:
            await message.reply(
                "📋 **У вас нет паспорта для удаления**"
            )
            return
        
        # Запрашиваем подтверждение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"confirm_delete_passport:{passport.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="cancel_delete_passport"
                )
            ]
        ])
        
        await message.reply(
            f"⚠️ **Подтвердите удаление паспорта**\n\n"
            f"👤 **Имя:** {passport.display_name}\n"
            f"📅 **Создан:** {format_date(passport.created_at)}\n\n"
            f"**⚠️ Внимание!** Это действие нельзя отменить.\n"
            f"Все данные паспорта будут безвозвратно удалены.\n\n"
            f"Вы уверены?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in delete_passport_command: {e}")
        await message.reply(
            "❌ **Ошибка при удалении паспорта**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@passport_router.callback_query(F.data.startswith("confirm_delete_passport:"))
async def confirm_delete_passport_callback(callback: CallbackQuery):
    """Подтверждение удаления паспорта"""
    try:
        passport_id = int(callback.data.split(":")[1])
        
        passport_service = get_passport_db_service()
        
        # Получаем паспорт для логирования
        passport = await passport_service.get_passport_by_id(passport_id)
        if not passport or passport.user_id != callback.from_user.id:
            await callback.answer("❌ Паспорт не найден или не принадлежит вам", show_alert=True)
            return
        
        # Логируем удаление
        log_entry = PassportOperationLog.create_log(
            operation_type='delete',
            passport_id=passport_id,
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            operation_details={'display_name': passport.display_name}
        )
        await passport_service.log_operation(log_entry)
        
        # Удаляем паспорт
        success = await passport_service.delete_passport(passport_id)
        
        if success:
            await callback.message.edit_text(
                f"✅ **Паспорт удален**\n\n"
                f"Паспорт **{passport.display_name}** был успешно удален.\n\n"
                f"Вы можете создать новый паспорт командой `/create_passport`",
                parse_mode="Markdown"
            )
            await callback.answer("✅ Паспорт удален")
        else:
            await callback.answer("❌ Ошибка удаления паспорта", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in confirm_delete_passport_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@passport_router.callback_query(F.data == "cancel_delete_passport")
async def cancel_delete_passport_callback(callback: CallbackQuery):
    """Отмена удаления паспорта"""
    await callback.message.edit_text("🚫 **Удаление паспорта отменено.**")
    await callback.answer("Отменено")