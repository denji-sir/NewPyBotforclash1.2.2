"""
Интерактивные команды для привязки игроков к паспортам
Фаза 4: Расширенная система привязки с UI выбора из списка участников клана
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging
import re
from typing import Optional, List, Dict, Any

from ..services.player_binding_service import PlayerBindingService
from ..services.passport_database_service import PassportDatabaseService
from ..services.passport_system_manager import PassportSystemManager
from ..services.clan_database_service import ClanDatabaseService
from ..services.coc_api_service import CoCAPIService
from ..models.passport_models import PlayerBinding, PassportOperationLog
from ..utils.permissions import check_admin_permission, get_user_permissions
from ..utils.formatting import format_player_info, format_clan_info
from ..utils.validators import validate_player_tag

router = Router()
logger = logging.getLogger(__name__)

# Инициализация сервисов
player_binding_service = PlayerBindingService()
passport_service = PassportDatabaseService()
passport_manager = PassportSystemManager()
clan_service = ClanDatabaseService()
coc_api = CoCAPIService()


@router.message(Command("bind_player"))
async def bind_player_command(message: Message):
    """
    Интерактивная команда для привязки игрока к паспорту
    Usage: /bind_player [player_tag]
    """
    try:
        # Проверяем наличие паспорта
        passport = await passport_service.get_passport_by_user(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        if not passport:
            await message.reply(
                "❌ У вас нет паспорта!\n"
                "Создайте его командой /create_passport"
            )
            return
        
        # Проверяем, есть ли уже привязанный игрок
        if passport.player_binding and passport.player_binding.player_tag:
            current_player = passport.player_binding
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Сменить игрока", 
                    callback_data=f"change_player:{message.from_user.id}"
                )],
                [InlineKeyboardButton(
                    text="👀 Просмотреть привязку", 
                    callback_data=f"view_binding:{message.from_user.id}"
                )],
                [InlineKeyboardButton(
                    text="❌ Отвязать игрока", 
                    callback_data=f"unbind_player:{message.from_user.id}"
                )]
            ])
            
            status_emoji = "✅" if current_player.is_verified else "⏳"
            await message.reply(
                f"🎮 **Текущая привязка:**\n"
                f"{status_emoji} Игрок: `{current_player.player_name}` ({current_player.player_tag})\n"
                f"🏰 Клан: {current_player.player_clan_name or 'Не в клане'}\n"
                f"📅 Привязан: {current_player.binding_date.strftime('%d.%m.%Y')}\n\n"
                f"Выберите действие:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return
        
        # Получаем аргументы команды
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if args:
            # Прямая привязка по тегу
            player_tag = args[0].upper().replace('O', '0')
            if not validate_player_tag(player_tag):
                await message.reply(
                    "❌ Неверный формат тега игрока!\n"
                    "Тег должен начинаться с # и содержать 8-9 символов\n"
                    "Пример: #2PP"
                )
                return
            
            await _bind_player_by_tag(message, player_tag)
        else:
            # Показываем интерактивное меню выбора
            await _show_binding_options(message)
            
    except Exception as e:
        logger.error(f"Ошибка в bind_player_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при привязке игрока. Попробуйте позже."
        )


async def _show_binding_options(message: Message):
    """Показать опции привязки игрока"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🏰 Выбрать из клана", 
            callback_data=f"select_from_clan:{message.from_user.id}"
        )],
        [InlineKeyboardButton(
            text="🔍 Найти по тегу", 
            callback_data=f"search_by_tag:{message.from_user.id}"
        )],
        [InlineKeyboardButton(
            text="📝 Ввести тег вручную", 
            callback_data=f"manual_tag_input:{message.from_user.id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена", 
            callback_data=f"cancel_binding:{message.from_user.id}"
        )]
    ])
    
    await message.reply(
        "🎮 **Выберите способ привязки игрока:**\n\n"
        "🏰 **Из клана** - выберите игрока из участников клана\n"
        "🔍 **По тегу** - найдите игрока по его тегу\n"
        "📝 **Вручную** - введите тег игрока самостоятельно\n\n"
        "💡 Рекомендуется выбирать из клана для автоматической верификации",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("select_from_clan:"))
async def select_from_clan_callback(callback: CallbackQuery):
    """Выбор игрока из списка участников клана"""
    try:
        user_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Получаем паспорт пользователя
        passport = await passport_service.get_passport_by_user(
            user_id=user_id,
            chat_id=callback.message.chat.id
        )
        
        if not passport or not passport.preferred_clan_id:
            await callback.message.edit_text(
                "❌ У вас не выбран предпочитаемый клан!\n"
                "Сначала установите клан в настройках паспорта.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="⚙️ Настроить клан", 
                        callback_data=f"edit_passport_clan:{user_id}"
                    )]
                ])
            )
            return
        
        # Получаем информацию о клане
        clan = await clan_service.get_clan_by_id(passport.preferred_clan_id)
        if not clan:
            await callback.message.edit_text(
                "❌ Клан не найден в базе данных!"
            )
            return
        
        # Получаем участников клана через CoC API
        try:
            clan_members = await player_binding_service.get_clan_members_for_binding(clan.clan_tag)
            
            if not clan_members:
                await callback.message.edit_text(
                    f"❌ Не удалось получить список участников клана {clan.clan_name}\n"
                    "Попробуйте привязать игрока по тегу."
                )
                return
            
            # Создаем клавиатуру с участниками (по 1 в ряду для лучшей читаемости)
            keyboard_buttons = []
            
            for member in clan_members[:20]:  # Ограничиваем 20 участниками
                role_emoji = {
                    'leader': '👑',
                    'coLeader': '🔥', 
                    'elder': '⭐',
                    'member': '👤'
                }.get(member.get('role', 'member'), '👤')
                
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"{role_emoji} {member['name']} (💎{member.get('trophies', 0)})",
                    callback_data=f"bind_clan_member:{user_id}:{member['tag']}"
                )])
            
            # Добавляем кнопки управления
            keyboard_buttons.extend([
                [InlineKeyboardButton(
                    text="🔍 Поиск по имени", 
                    callback_data=f"search_clan_member:{user_id}:{clan.clan_tag}"
                )],
                [InlineKeyboardButton(
                    text="🔙 Назад", 
                    callback_data=f"select_from_clan_back:{user_id}"
                )]
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(
                f"🏰 **Участники клана {clan.clan_name}:**\n"
                f"📊 Всего: {len(clan_members)} игроков\n\n"
                f"Выберите игрока для привязки:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения участников клана: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при получении списка участников клана\n"
                "Попробуйте привязать игрока по тегу."
            )
            
    except Exception as e:
        logger.error(f"Ошибка в select_from_clan_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("bind_clan_member:"))
async def bind_clan_member_callback(callback: CallbackQuery):
    """Привязка выбранного участника клана"""
    try:
        _, user_id_str, player_tag = callback.data.split(":", 2)
        user_id = int(user_id_str)
        
        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Привязываем игрока
        await _bind_player_by_tag(callback.message, player_tag, edit_message=True)
        
    except Exception as e:
        logger.error(f"Ошибка в bind_clan_member_callback: {e}")
        await callback.answer("❌ Произошла ошибка при привязке", show_alert=True)


async def _bind_player_by_tag(message_or_callback, player_tag: str, edit_message: bool = False):
    """Привязка игрока по тегу"""
    try:
        if hasattr(message_or_callback, 'from_user'):
            # Это Message
            user_id = message_or_callback.from_user.id
            chat_id = message_or_callback.chat.id
            send_func = message_or_callback.reply
        else:
            # Это CallbackQuery
            user_id = message_or_callback.from_user.id
            chat_id = message_or_callback.message.chat.id
            send_func = message_or_callback.message.edit_text if edit_message else message_or_callback.message.reply
        
        # Нормализуем тег
        if not player_tag.startswith('#'):
            player_tag = f"#{player_tag}"
        
        # Привязываем игрока через сервис
        result = await player_binding_service.bind_player_to_passport(
            user_id=user_id,
            chat_id=chat_id,
            player_tag=player_tag,
            requester_id=user_id
        )
        
        if result['success']:
            binding = result['binding']
            
            # Создаем клавиатуру с действиями
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="👀 Просмотреть паспорт", 
                    callback_data=f"view_passport:{user_id}"
                )],
                [InlineKeyboardButton(
                    text="⚙️ Настройки паспорта", 
                    callback_data=f"edit_passport_menu:{user_id}"
                )]
            ])
            
            # Определяем статус верификации
            if binding.is_verified:
                status_text = "✅ **Автоматически верифицирован**"
                status_reason = "Игрок состоит в зарегистрированном клане"
            else:
                status_text = "⏳ **Ожидает верификации администратором**"
                status_reason = "Игрок не состоит в зарегистрированном клане или клан не найден"
            
            success_message = (
                f"🎉 **Игрок успешно привязан!**\n\n"
                f"🎮 **Игрок:** `{binding.player_name}`\n"
                f"🏷️ **Тег:** `{binding.player_tag}`\n"
                f"🏰 **Клан:** {binding.player_clan_name or 'Не в клане'}\n"
                f"💎 **Кубки:** {binding.player_trophies:,}\n"
                f"📅 **Дата привязки:** {binding.binding_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"{status_text}\n"
                f"💡 {status_reason}"
            )
            
            await send_func(
                success_message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        else:
            error_message = f"❌ **Ошибка привязки игрока:**\n{result['error']}"
            await send_func(error_message, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Ошибка в _bind_player_by_tag: {e}")
        error_message = "❌ Произошла ошибка при привязке игрока"
        if hasattr(message_or_callback, 'from_user'):
            await message_or_callback.reply(error_message)
        else:
            await message_or_callback.message.reply(error_message)


@router.callback_query(F.data.startswith("search_by_tag:"))
async def search_by_tag_callback(callback: CallbackQuery):
    """Поиск игрока по тегу"""
    try:
        user_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        await callback.message.edit_text(
            "🔍 **Поиск игрока по тегу**\n\n"
            "Введите тег игрока в формате: `#2PP`\n"
            "Или отправьте сообщение: `/bind_player #тег_игрока`\n\n"
            "💡 Тег можно найти в профиле игрока в Clash of Clans",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔙 Назад к выбору", 
                    callback_data=f"back_to_binding_options:{user_id}"
                )]
            ]),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в search_by_tag_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(Command("verify_player"))
async def verify_player_command(message: Message):
    """
    Команда для верификации привязанного игрока (только для администраторов)
    Usage: /verify_player [@user|user_id]
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
        
        # Получаем аргументы команды
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        target_user_id = None
        
        if args:
            # Парсим упоминание или ID пользователя
            if message.reply_to_message:
                target_user_id = message.reply_to_message.from_user.id
            elif args[0].startswith('@'):
                # Обработка упоминания (нужно найти пользователя по username)
                await message.reply(
                    "❌ Упоминания пользователей не поддерживаются\n"
                    "Используйте ID пользователя или ответьте на сообщение"
                )
                return
            else:
                try:
                    target_user_id = int(args[0])
                except ValueError:
                    await message.reply(
                        "❌ Неверный формат ID пользователя!\n"
                        "Используйте числовой ID или ответьте на сообщение пользователя"
                    )
                    return
        elif message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            # Показываем список неверифицированных привязок
            await _show_unverified_bindings(message)
            return
        
        # Получаем паспорт пользователя
        passport = await passport_service.get_passport_by_user(
            user_id=target_user_id,
            chat_id=message.chat.id
        )
        
        if not passport or not passport.player_binding:
            await message.reply(
                "❌ У указанного пользователя нет привязанного игрока!"
            )
            return
        
        # Верифицируем привязку
        result = await player_binding_service.verify_player_binding(
            user_id=target_user_id,
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            admin_username=message.from_user.username
        )
        
        if result['success']:
            binding = passport.player_binding
            await message.reply(
                f"✅ **Привязка верифицирована!**\n\n"
                f"👤 **Пользователь:** {passport.display_name}\n"
                f"🎮 **Игрок:** `{binding.player_name}` ({binding.player_tag})\n"
                f"🏰 **Клан:** {binding.player_clan_name or 'Не в клане'}\n"
                f"👨‍💼 **Верифицировал:** {message.from_user.full_name}",
                parse_mode="Markdown"
            )
        else:
            await message.reply(f"❌ **Ошибка верификации:** {result['error']}")
            
    except Exception as e:
        logger.error(f"Ошибка в verify_player_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при верификации. Попробуйте позже."
        )


async def _show_unverified_bindings(message: Message):
    """Показать список неверифицированных привязок в чате"""
    try:
        # Получаем все паспорта чата
        passports = await passport_service.get_chat_passports(
            chat_id=message.chat.id,
            include_stats=True
        )
        
        # Фильтруем неверифицированные привязки
        unverified = [
            p for p in passports 
            if p.player_binding and not p.player_binding.is_verified
        ]
        
        if not unverified:
            await message.reply(
                "✅ **Все привязки в чате верифицированы!**\n\n"
                "Нет ожидающих верификации привязок игроков."
            )
            return
        
        # Создаем клавиатуру с неверифицированными привязками
        keyboard_buttons = []
        
        for passport in unverified[:10]:  # Ограничиваем 10 записями
            binding = passport.player_binding
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"✅ {passport.display_name} → {binding.player_name}",
                callback_data=f"verify_binding:{passport.user_id}:{message.from_user.id}"
            )])
        
        # Добавляем кнопку обновления
        keyboard_buttons.append([InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data=f"refresh_unverified:{message.from_user.id}"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.reply(
            f"⏳ **Неверифицированные привязки ({len(unverified)}):**\n\n"
            f"Нажмите на кнопку с именем пользователя для верификации его привязки:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в _show_unverified_bindings: {e}")
        await message.reply("❌ Ошибка при получении списка привязок")


@router.callback_query(F.data.startswith("verify_binding:"))
async def verify_binding_callback(callback: CallbackQuery):
    """Верификация привязки через callback"""
    try:
        _, target_user_id_str, admin_id_str = callback.data.split(":")
        target_user_id = int(target_user_id_str)
        admin_id = int(admin_id_str)
        
        if callback.from_user.id != admin_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Проверяем права администратора
        is_admin = await check_admin_permission(
            user_id=admin_id,
            chat_id=callback.message.chat.id
        )
        
        if not is_admin:
            await callback.answer(
                "❌ У вас нет прав для верификации!", 
                show_alert=True
            )
            return
        
        # Верифицируем привязку
        result = await player_binding_service.verify_player_binding(
            user_id=target_user_id,
            chat_id=callback.message.chat.id,
            admin_id=admin_id,
            admin_username=callback.from_user.username
        )
        
        if result['success']:
            await callback.answer("✅ Привязка верифицирована!", show_alert=True)
            # Обновляем список
            await _refresh_unverified_list(callback)
        else:
            await callback.answer(f"❌ Ошибка: {result['error']}", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в verify_binding_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def _refresh_unverified_list(callback: CallbackQuery):
    """Обновить список неверифицированных привязок"""
    try:
        # Получаем все паспорта чата
        passports = await passport_service.get_chat_passports(
            chat_id=callback.message.chat.id,
            include_stats=True
        )
        
        # Фильтруем неверифицированные привязки
        unverified = [
            p for p in passports 
            if p.player_binding and not p.player_binding.is_verified
        ]
        
        if not unverified:
            await callback.message.edit_text(
                "✅ **Все привязки в чате верифицированы!**\n\n"
                "Нет ожидающих верификации привязок игроков."
            )
            return
        
        # Создаем обновленную клавиатуру
        keyboard_buttons = []
        
        for passport in unverified[:10]:
            binding = passport.player_binding
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"✅ {passport.display_name} → {binding.player_name}",
                callback_data=f"verify_binding:{passport.user_id}:{callback.from_user.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data=f"refresh_unverified:{callback.from_user.id}"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            f"⏳ **Неверифицированные привязки ({len(unverified)}):**\n\n"
            f"Нажмите на кнопку с именем пользователя для верификации его привязки:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в _refresh_unverified_list: {e}")


@router.message(Command("unbind_player"))
async def unbind_player_command(message: Message):
    """
    Команда для отвязки игрока от паспорта
    Usage: /unbind_player
    """
    try:
        # Получаем паспорт пользователя
        passport = await passport_service.get_passport_by_user(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        if not passport or not passport.player_binding:
            await message.reply(
                "❌ У вас нет привязанного игрока!"
            )
            return
        
        binding = passport.player_binding
        
        # Создаем клавиатуру подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Да, отвязать", 
                callback_data=f"confirm_unbind:{message.from_user.id}"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена", 
                callback_data=f"cancel_unbind:{message.from_user.id}"
            )]
        ])
        
        await message.reply(
            f"⚠️ **Подтверждение отвязки игрока**\n\n"
            f"🎮 **Игрок:** `{binding.player_name}` ({binding.player_tag})\n"
            f"🏰 **Клан:** {binding.player_clan_name or 'Не в клане'}\n"
            f"📅 **Привязан:** {binding.binding_date.strftime('%d.%m.%Y')}\n\n"
            f"❗ **Внимание:** После отвязки вам потребуется заново привязать игрока "
            f"и пройти верификацию у администратора.\n\n"
            f"Вы уверены, что хотите отвязать игрока?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в unbind_player_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при отвязке игрока. Попробуйте позже."
        )


@router.callback_query(F.data.startswith("confirm_unbind:"))
async def confirm_unbind_callback(callback: CallbackQuery):
    """Подтверждение отвязки игрока"""
    try:
        user_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        # Отвязываем игрока
        result = await player_binding_service.unbind_player_from_passport(
            user_id=user_id,
            chat_id=callback.message.chat.id,
            requester_id=user_id
        )
        
        if result['success']:
            await callback.message.edit_text(
                "✅ **Игрок успешно отвязан от паспорта!**\n\n"
                "🎮 Теперь вы можете привязать нового игрока командой `/bind_player`\n"
                "💡 При привязке нового игрока потребуется верификация администратором",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                f"❌ **Ошибка отвязки игрока:**\n{result['error']}"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в confirm_unbind_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(Command("binding_stats"))
async def binding_stats_command(message: Message):
    """
    Команда для просмотра статистики привязок в чате
    Usage: /binding_stats
    """
    try:
        # Получаем статистику привязок
        stats = await player_binding_service.get_binding_statistics(
            chat_id=message.chat.id
        )
        
        if not stats:
            await message.reply(
                "📊 **Статистика привязок не найдена**\n\n"
                "В чате еще нет привязанных игроков."
            )
            return
        
        # Форматируем сообщение со статистикой
        total = stats['total_bindings']
        verified = stats['verified_bindings']
        unverified = total - verified
        verification_rate = (verified / total * 100) if total > 0 else 0
        
        stats_message = (
            f"📊 **Статистика привязок игроков**\n\n"
            f"👥 **Всего привязок:** {total}\n"
            f"✅ **Верифицировано:** {verified} ({verification_rate:.1f}%)\n"
            f"⏳ **Ожидает верификации:** {unverified}\n\n"
        )
        
        # Добавляем распределение по кланам
        if stats['clan_distribution']:
            stats_message += "🏰 **Распределение по кланам:**\n"
            for clan_name, count in stats['clan_distribution'].items():
                stats_message += f"   • {clan_name}: {count} игроков\n"
            stats_message += "\n"
        
        # Добавляем последние привязки
        if stats['recent_bindings']:
            stats_message += "🕒 **Последние привязки:**\n"
            for binding_info in stats['recent_bindings'][:5]:
                date_str = binding_info['binding_date'].strftime('%d.%m.%Y')
                verified_emoji = "✅" if binding_info['is_verified'] else "⏳"
                stats_message += f"   {verified_emoji} {binding_info['player_name']} - {date_str}\n"
        
        # Создаем клавиатуру для администраторов
        keyboard = None
        is_admin = await check_admin_permission(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )
        
        if is_admin and unverified > 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"⏳ Верифицировать привязки ({unverified})",
                    callback_data=f"show_unverified_for_admin:{message.from_user.id}"
                )]
            ])
        
        await message.reply(
            stats_message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в binding_stats_command: {e}")
        await message.reply(
            "❌ Произошла ошибка при получении статистики. Попробуйте позже."
        )


# Дополнительные callback handlers
@router.callback_query(F.data.startswith("cancel_binding:"))
async def cancel_binding_callback(callback: CallbackQuery):
    """Отмена привязки игрока"""
    user_id = int(callback.data.split(":")[1])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваше меню!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "❌ **Привязка игрока отменена**\n\n"
        "Используйте команду `/bind_player` для повторной попытки.",
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("back_to_binding_options:"))
async def back_to_binding_options_callback(callback: CallbackQuery):
    """Возврат к опциям привязки"""
    user_id = int(callback.data.split(":")[1])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваше меню!", show_alert=True)
        return
    
    # Показываем меню опций привязки заново
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🏰 Выбрать из клана", 
            callback_data=f"select_from_clan:{user_id}"
        )],
        [InlineKeyboardButton(
            text="🔍 Найти по тегу", 
            callback_data=f"search_by_tag:{user_id}"
        )],
        [InlineKeyboardButton(
            text="📝 Ввести тег вручную", 
            callback_data=f"manual_tag_input:{user_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена", 
            callback_data=f"cancel_binding:{user_id}"
        )]
    ])
    
    await callback.message.edit_text(
        "🎮 **Выберите способ привязки игрока:**\n\n"
        "🏰 **Из клана** - выберите игрока из участников клана\n"
        "🔍 **По тегу** - найдите игрока по его тегу\n"
        "📝 **Вручную** - введите тег игрока самостоятельно\n\n"
        "💡 Рекомендуется выбирать из клана для автоматической верификации",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# Регистрируем все обработчики callback-запросов для существующих функций из паспортов
@router.callback_query(F.data.startswith("view_binding:"))
async def view_binding_callback(callback: CallbackQuery):
    """Просмотр текущей привязки игрока"""
    try:
        user_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваше меню!", show_alert=True)
            return
        
        passport = await passport_service.get_passport_by_user(
            user_id=user_id,
            chat_id=callback.message.chat.id
        )
        
        if not passport or not passport.player_binding:
            await callback.message.edit_text(
                "❌ Привязанный игрок не найден!"
            )
            return
        
        binding = passport.player_binding
        
        # Получаем дополнительную информацию об игроке из CoC API
        try:
            player_info = await coc_api.get_player(binding.player_tag)
            
            if player_info:
                detailed_info = (
                    f"🎮 **Детальная информация об игроке**\n\n"
                    f"👤 **Имя:** `{player_info.get('name', binding.player_name)}`\n"
                    f"🏷️ **Тег:** `{binding.player_tag}`\n"
                    f"🏆 **Кубки:** {player_info.get('trophies', 0):,}\n"
                    f"💎 **Лучший результат:** {player_info.get('bestTrophies', 0):,}\n"
                    f"⭐ **Уровень:** {player_info.get('expLevel', 'N/A')}\n"
                    f"🏰 **Клан:** {player_info.get('clan', {}).get('name', 'Не в клане')}\n"
                    f"📅 **Дата привязки:** {binding.binding_date.strftime('%d.%m.%Y %H:%M')}\n"
                    f"✅ **Статус:** {'Верифицирован' if binding.is_verified else 'Ожидает верификации'}\n\n"
                    f"🔗 **Привязан к паспорту:** {passport.display_name}"
                )
            else:
                detailed_info = f"❌ Не удалось получить информацию об игроке из CoC API"
                
        except Exception as e:
            logger.error(f"Ошибка получения информации об игроке: {e}")
            detailed_info = (
                f"🎮 **Информация об игроке**\n\n"
                f"👤 **Имя:** `{binding.player_name}`\n"
                f"🏷️ **Тег:** `{binding.player_tag}`\n"
                f"🏰 **Клан:** {binding.player_clan_name or 'Не в клане'}\n"
                f"💎 **Кубки:** {binding.player_trophies:,}\n"
                f"📅 **Дата привязки:** {binding.binding_date.strftime('%d.%m.%Y %H:%M')}\n"
                f"✅ **Статус:** {'Верифицирован' if binding.is_verified else 'Ожидает верификации'}\n\n"
                f"⚠️ Актуальная информация временно недоступна"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Сменить игрока", 
                callback_data=f"change_player:{user_id}"
            )],
            [InlineKeyboardButton(
                text="❌ Отвязать игрока", 
                callback_data=f"unbind_player:{user_id}"
            )],
            [InlineKeyboardButton(
                text="👀 Просмотреть паспорт", 
                callback_data=f"view_passport:{user_id}"
            )]
        ])
        
        await callback.message.edit_text(
            detailed_info,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в view_binding_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("change_player:"))
async def change_player_callback(callback: CallbackQuery):
    """Смена привязанного игрока"""
    user_id = int(callback.data.split(":")[1])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваше меню!", show_alert=True)
        return
    
    # Показываем опции привязки нового игрока
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🏰 Выбрать из клана", 
            callback_data=f"select_from_clan:{user_id}"
        )],
        [InlineKeyboardButton(
            text="🔍 Найти по тегу", 
            callback_data=f"search_by_tag:{user_id}"
        )],
        [InlineKeyboardButton(
            text="📝 Ввести тег вручную", 
            callback_data=f"manual_tag_input:{user_id}"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад", 
            callback_data=f"view_binding:{user_id}"
        )]
    ])
    
    await callback.message.edit_text(
        "🔄 **Смена привязанного игрока**\n\n"
        "Выберите способ привязки нового игрока:\n\n"
        "⚠️ **Внимание:** Текущая привязка будет заменена на новую",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )