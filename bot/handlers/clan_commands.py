"""
Хандлеры команд для работы с кланами
"""
import logging
import aiosqlite
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest

from ..models.clan_models import (
    ClanOperationLog, ClanNotFound, ClanAlreadyRegistered, 
    ApiError, DatabaseError, PermissionDenied
)
from ..services.coc_api_service import get_coc_api_service
from ..services.clan_database_service import get_clan_db_service
from ..services.permission_service import get_permission_service
from ..utils.validators import validate_clan_tag, format_number, format_date
from ..utils.clan_helpers import format_member_list, get_clan_recruitment_message
from ..utils.clan_analysis_manager import get_clan_analysis_manager

logger = logging.getLogger(__name__)

# Создаем роутер для команд кланов
clan_router = Router()


def format_date(dt: datetime) -> str:
    """Форматировать дату для отображения"""
    return dt.strftime("%d.%m.%Y")


def format_number(num: int) -> str:
    """Форматировать число с разделителями"""
    return f"{num:,}".replace(",", " ")


@clan_router.message(Command("register_clan"))
async def register_clan_command(message: Message, command: CommandObject):
    """
    Регистрация клана в чате
    Синтаксис: /register_clan #CLANTAG [описание]
    """
    try:
        # Получаем сервисы
        coc_api = get_coc_api_service()
        db_service = get_clan_db_service()
        permission_service = get_permission_service()
        
        # Проверяем права
        await permission_service.require_clan_registration_permission(
            message.from_user.id, message.chat.id
        )
        
        # Парсим аргументы
        if not command.args:
            await message.reply(
                "❌ **Укажите тег клана!**\n\n"
                "**Использование:** `/register_clan #CLANTAG [описание]`\n\n"
                "**Пример:** `/register_clan #2PP0JCCL Основной клан сообщества`",
                parse_mode="Markdown"
            )
            return
        
        args = command.args.split()
        clan_tag = args[0]
        description = " ".join(args[1:]) if len(args) > 1 else None
        
        # Валидируем тег клана
        if not clan_tag.startswith('#') or len(clan_tag) < 4:
            await message.reply(
                "❌ **Некорректный тег клана!**\n\n"
                "Тег должен начинаться с # и содержать минимум 3 символа\n"
                "**Пример:** `#2PP0JCCL`"
            )
            return
        
        # Отправляем сообщение о процессе
        status_msg = await message.reply(
            f"🔍 **Проверяю клан {clan_tag}...**\n"
            "⏳ Обращаюсь к Clash of Clans API..."
        )
        
        # Получаем данные клана из CoC API
        try:
            async with coc_api:
                clan_data = await coc_api.get_clan(clan_tag)
        except ClanNotFound:
            await status_msg.edit_text(
                f"❌ **Клан {clan_tag} не найден!**\n\n"
                "Проверьте правильность тега клана и убедитесь что клан существует в Clash of Clans."
            )
            return
        except ApiError as e:
            await status_msg.edit_text(
                f"❌ **Ошибка Clash of Clans API**\n\n"
                f"Не удалось получить информацию о клане: {e}\n"
                "Попробуйте позже."
            )
            return
        
        # Обновляем статус
        await status_msg.edit_text(
            f"✅ **Клан найден!**\n"
            f"🏰 {clan_data.name}\n"
            f"⏳ Сохраняю в базу данных..."
        )
        
        # Регистрируем клан в БД
        try:
            clan_id = await db_service.register_clan(
                clan_data=clan_data,
                chat_id=message.chat.id,
                registered_by=message.from_user.id,
                description=description
            )
            
            # Логируем успешную операцию
            log_entry = ClanOperationLog.create_log(
                operation_type='register',
                clan_id=clan_id,
                clan_tag=clan_tag,
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                username=message.from_user.username,
                operation_details={'description': description},
                result='success'
            )
            await db_service.log_operation(log_entry)
            
            # Формируем ответ об успехе
            success_text = (
                f"✅ **Клан успешно зарегистрирован!**\n\n"
                f"🏰 **{clan_data.name}** `{clan_data.tag}`\n"
                f"📊 **Уровень:** {clan_data.level}\n"
                f"👥 **Участников:** {clan_data.member_count}/50\n"
                f"🏆 **Очки:** {format_number(clan_data.points)}\n"
                f"🌍 **Локация:** {clan_data.location}\n"
            )
            
            if clan_data.war_wins > 0:
                success_text += f"⚔️ **Побед в войнах:** {clan_data.war_wins}\n"
            
            if description:
                success_text += f"\n📝 **Описание:** {description}\n"
            
            success_text += (
                f"\n💡 **Что дальше:**\n"
                f"• Участники могут создавать паспорта: `/create_passport`\n"
                f"• Просмотр всех кланов: `/clan_list`\n"
                f"• Информация о клане: `/clan_info {clan_data.tag}`"
            )
            
            await status_msg.edit_text(success_text, parse_mode="Markdown")
            
        except ClanAlreadyRegistered as e:
            await status_msg.edit_text(f"❌ **{e}**")
            
            # Логируем ошибку
            log_entry = ClanOperationLog.create_log(
                operation_type='register',
                clan_tag=clan_tag,
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                username=message.from_user.username,
                result='error',
                error_message=str(e)
            )
            await db_service.log_operation(log_entry)
            
        except DatabaseError as e:
            await status_msg.edit_text(
                f"❌ **Ошибка базы данных**\n\n"
                f"{e}\n\n"
                "Обратитесь к администратору бота."
            )
            
    except PermissionDenied:
        await message.reply(
            "❌ **Недостаточно прав!**\n\n"
            "Только администраторы чата могут регистрировать кланы."
        )
    except Exception as e:
        logger.error(f"Unexpected error in register_clan_command: {e}")
        await message.reply(
            "❌ **Произошла неожиданная ошибка**\n\n"
            "Попробуйте позже или обратитесь к администратору бота."
        )


@clan_router.message(Command("clan_list"))
async def clan_list_command(message: Message):
    """Показать список зарегистрированных кланов в чате"""
    try:
        db_service = get_clan_db_service()
        
        clans = await db_service.get_chat_clans(message.chat.id, active_only=True)
        
        if not clans:
            await message.reply(
                "📝 **В этом чате нет зарегистрированных кланов**\n\n"
                "Администраторы могут добавить клан командой:\n"
                "`/register_clan #CLANTAG`\n\n"
                "💡 **Примеры команд:**\n"
                "• `/register_clan #2PP0JCCL`\n"
                "• `/register_clan #ABC123 Описание клана`",
                parse_mode="Markdown"
            )
            return
        
        # Получаем настройки чата для определения основного клана
        settings = await db_service.get_chat_settings(message.chat.id)
        default_clan_id = settings.default_clan_id
        
        # Формируем список
        text = "🏰 **Зарегистрированные кланы:**\n\n"
        
        for i, clan in enumerate(clans, 1):
            # Определяем статус клана
            status_emoji = "✅"
            default_mark = ""
            
            if clan.id == default_clan_id:
                default_mark = " ⭐"
            
            # Добавляем информацию о клане
            text += (
                f"**{i}.** {status_emoji} **{clan.clan_name}**{default_mark}\n"
                f"    🏷️ `{clan.clan_tag}`\n"
                f"    📊 Уровень {clan.clan_level} | "
                f"👥 {clan.member_count} чел. | "
                f"🏆 {format_number(clan.clan_points)}\n"
                f"    📅 Добавлен {format_date(clan.registered_at)}\n\n"
            )
        
        # Добавляем итоговую информацию
        text += (
            f"📊 **Всего кланов:** {len(clans)}/{settings.max_clans_per_chat}\n\n"
            f"💡 **Доступные команды:**\n"
            f"• `/clan_info <номер>` - подробная информация\n"
            f"• `/set_default_clan <номер>` - установить основной\n"
            f"• `/update_clan <номер>` - обновить данные из CoC API"
        )
        
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in clan_list_command: {e}")
        await message.reply(
            "❌ **Ошибка получения списка кланов**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("clan_info"))
async def clan_info_command(message: Message, command: CommandObject):
    """
    Показать информацию о клане
    Синтаксис: /clan_info [номер|тег]
    """
    try:
        db_service = get_clan_db_service()
        
        clan = None
        
        if command.args:
            arg = command.args.strip()
            
            # Пробуем найти по тегу
            if arg.startswith('#'):
                clan = await db_service.get_clan_by_tag(arg, message.chat.id)
            else:
                # Пробуем найти по номеру из списка
                try:
                    clan_number = int(arg)
                    clans = await db_service.get_chat_clans(message.chat.id)
                    
                    if 1 <= clan_number <= len(clans):
                        clan = clans[clan_number - 1]
                    else:
                        await message.reply(
                            f"❌ **Неверный номер клана!**\n\n"
                            f"Доступные кланы: 1-{len(clans)}\n"
                            "Используйте `/clan_list` для просмотра всех кланов."
                        )
                        return
                except ValueError:
                    await message.reply(
                        "❌ **Неверный формат!**\n\n"
                        "**Использование:** `/clan_info [номер|тег]`\n\n"
                        "**Примеры:**\n"
                        "• `/clan_info 1` - первый клан из списка\n"
                        "• `/clan_info #2PP0JCCL` - по тегу клана"
                    )
                    return
        else:
            # Если аргумент не указан, показываем основной клан чата
            settings = await db_service.get_chat_settings(message.chat.id)
            if settings.default_clan_id:
                clan = await db_service.get_clan_by_id(settings.default_clan_id)
            else:
                await message.reply(
                    "❌ **Основной клан не установлен!**\n\n"
                    "Используйте:\n"
                    "• `/clan_info <номер>` - информация о конкретном клане\n"
                    "• `/clan_list` - список всех кланов\n"
                    "• `/set_default_clan <номер>` - установить основной клан"
                )
                return
        
        if not clan:
            await message.reply(
                "❌ **Клан не найден!**\n\n"
                "Проверьте правильность тега или номера клана.\n"
                "Используйте `/clan_list` для просмотра всех кланов."
            )
            return
        
        # Парсим метаданные
        metadata = clan.clan_metadata
        
        # Формируем детальную информацию
        text = (
            f"🏰 **{clan.clan_name}**\n"
            f"🏷️ **Тег:** `{clan.clan_tag}`\n\n"
            
            f"📊 **Основная информация:**\n"
            f"• **Уровень клана:** {clan.clan_level}\n"
            f"• **Участников:** {clan.member_count}/50\n"
            f"• **Очки клана:** {format_number(clan.clan_points)}\n"
        )
        
        if metadata.get('location'):
            text += f"• **Локация:** {metadata['location']}\n"
        
        if metadata.get('war_wins', 0) > 0:
            text += f"• **Побед в войнах:** {metadata['war_wins']}\n"
            
        if metadata.get('war_win_streak', 0) > 0:
            text += f"• **Текущая серия:** {metadata['war_win_streak']} побед\n"
        
        text += f"\n📅 **Информация о регистрации:**\n"
        text += f"• **Зарегистрирован:** {format_date(clan.registered_at)}\n"
        text += f"• **Последнее обновление:** {format_date(clan.last_updated)}\n"
        
        if clan.clan_description:
            text += f"\n📝 **Описание:**\n{clan.clan_description}\n"
        
        # Проверяем является ли этот клан основным
        settings = await db_service.get_chat_settings(message.chat.id)
        if settings.default_clan_id == clan.id:
            text += f"\n⭐ **Основной клан чата**\n"
        
        text += (
            f"\n💡 **Команды для этого клана:**\n"
            f"• `/update_clan {clan.clan_tag}` - обновить данные\n"
            f"• `/clan_members {clan.clan_tag}` - список участников"
        )
        
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in clan_info_command: {e}")
        await message.reply(
            "❌ **Ошибка получения информации о клане**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("set_default_clan"))
async def set_default_clan_command(message: Message, command: CommandObject):
    """
    Установить основной клан чата
    Синтаксис: /set_default_clan <номер>
    """
    try:
        db_service = get_clan_db_service()
        permission_service = get_permission_service()
        
        # Проверяем права администратора
        await permission_service.require_admin(
            message.from_user.id, message.chat.id, "setting default clan"
        )
        
        if not command.args:
            await message.reply(
                "❌ **Укажите номер клана!**\n\n"
                "**Использование:** `/set_default_clan <номер>`\n\n"
                "Используйте `/clan_list` для просмотра всех кланов."
            )
            return
        
        try:
            clan_number = int(command.args.strip())
        except ValueError:
            await message.reply(
                "❌ **Некорректный номер клана!**\n\n"
                "Номер должен быть числом. Пример: `/set_default_clan 2`"
            )
            return
        
        # Получаем список кланов
        clans = await db_service.get_chat_clans(message.chat.id)
        
        if not clans:
            await message.reply(
                "❌ **В чате нет зарегистрированных кланов!**\n\n"
                "Сначала зарегистрируйте клан: `/register_clan #CLANTAG`"
            )
            return
        
        if not (1 <= clan_number <= len(clans)):
            await message.reply(
                f"❌ **Неверный номер клана!**\n\n"
                f"Доступные кланы: 1-{len(clans)}\n"
                "Используйте `/clan_list` для просмотра."
            )
            return
        
        # Получаем выбранный клан
        selected_clan = clans[clan_number - 1]
        
        # Устанавливаем как основной
        success = await db_service.set_default_clan(message.chat.id, selected_clan.id)
        
        if success:
            await message.reply(
                f"✅ **Основной клан установлен!**\n\n"
                f"🏰 **{selected_clan.clan_name}** `{selected_clan.clan_tag}`\n\n"
                "Теперь команды без указания клана будут работать с этим кланом."
            )
            
            # Логируем операцию
            log_entry = ClanOperationLog.create_log(
                operation_type='set_default',
                clan_id=selected_clan.id,
                clan_tag=selected_clan.clan_tag,
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                username=message.from_user.username,
                result='success'
            )
            await db_service.log_operation(log_entry)
        else:
            await message.reply(
                "❌ **Ошибка установки основного клана**\n\n"
                "Попробуйте позже или обратитесь к администратору."
            )
        
    except PermissionDenied:
        await message.reply(
            "❌ **Недостаточно прав!**\n\n"
            "Только администраторы чата могут устанавливать основной клан."
        )
    except Exception as e:
        logger.error(f"Error in set_default_clan_command: {e}")
        await message.reply(
            "❌ **Произошла ошибка**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("clan_members"))
async def clan_members_command(message: Message, command: CommandObject):
    """
    Показать список участников клана
    Синтаксис: /clan_members [номер|тег]
    """
    try:
        db_service = get_clan_db_service()
        coc_api = get_coc_api_service()
        
        clan = None
        
        if command.args:
            arg = command.args.strip()
            
            # Пробуем найти по тегу
            if arg.startswith('#'):
                clan = await db_service.get_clan_by_tag(arg, message.chat.id)
            else:
                # Пробуем найти по номеру из списка
                try:
                    clan_number = int(arg)
                    clans = await db_service.get_chat_clans(message.chat.id)
                    
                    if 1 <= clan_number <= len(clans):
                        clan = clans[clan_number - 1]
                    else:
                        await message.reply(
                            f"❌ **Неверный номер клана!**\n\n"
                            f"Доступные кланы: 1-{len(clans)}\n"
                            "Используйте `/clan_list` для просмотра всех кланов."
                        )
                        return
                except ValueError:
                    await message.reply(
                        "❌ **Неверный формат!**\n\n"
                        "**Использование:** `/clan_members [номер|тег]`\n\n"
                        "**Примеры:**\n"
                        "• `/clan_members 1` - участники первого клана\n"
                        "• `/clan_members #2PP0JCCL` - участники по тегу"
                    )
                    return
        else:
            # Показываем участников основного клана
            settings = await db_service.get_chat_settings(message.chat.id)
            if settings.default_clan_id:
                clan = await db_service.get_clan_by_id(settings.default_clan_id)
            else:
                await message.reply(
                    "❌ **Основной клан не установлен!**\n\n"
                    "Используйте:\n"
                    "• `/clan_members <номер>` - участники конкретного клана\n"
                    "• `/set_default_clan <номер>` - установить основной клан"
                )
                return
        
        if not clan:
            await message.reply(
                "❌ **Клан не найден!**\n\n"
                "Проверьте правильность тега или номера клана.\n"
                "Используйте `/clan_list` для просмотра всех кланов."
            )
            return
        
        # Отправляем сообщение о загрузке
        status_msg = await message.reply(
            f"🔍 **Получаю список участников клана {clan.clan_name}...**\n"
            "⏳ Обращаюсь к Clash of Clans API..."
        )
        
        try:
            # Получаем участников из CoC API
            async with coc_api:
                members = await coc_api.get_clan_members(clan.clan_tag)
            
            if not members:
                await status_msg.edit_text(
                    f"📝 **Клан {clan.clan_name} пуст**\n\n"
                    "В клане нет участников или данные недоступны."
                )
                return
            
            # Сортируем по роли и донату
            role_order = {'leader': 0, 'coLeader': 1, 'admin': 2, 'member': 3}
            members.sort(key=lambda x: (role_order.get(x.get('role', 'member'), 4), -x.get('donations', 0)))
            
            # Формируем список участников
            text = f"👥 **Участники клана {clan.clan_name}**\n\n"
            
            role_emojis = {
                'leader': '👑',
                'coLeader': '🌟', 
                'admin': '⭐',
                'member': '👤'
            }
            
            current_role = None
            for member in members:
                member_role = member.get('role', 'member')
                member_name = member.get('name', 'Unknown')
                member_tag = member.get('tag', '')
                member_level = member.get('expLevel', 0)
                member_donations = member.get('donations', 0)
                member_received = member.get('donationsReceived', 0)
                
                # Добавляем заголовок роли
                if current_role != member_role:
                    current_role = member_role
                    role_name = {
                        'leader': 'Лидер',
                        'coLeader': 'Со-лидер',
                        'admin': 'Старейшина',
                        'member': 'Участник'
                    }.get(member_role, 'Участник')
                    
                    text += f"\n**{role_emojis.get(member_role, '👤')} {role_name}:**\n"
                
                # Добавляем участника
                text += (
                    f"• **{member_name}** `{member_tag}`\n"
                    f"  🎯 Уровень {member_level} | "
                    f"💝 {format_number(member_donations)} | "
                    f"📥 {format_number(member_received)}\n"
                )
                
                # Проверяем лимит символов Telegram
                if len(text) > 3500:
                    text += f"\n... и еще {len(members) - members.index(member) - 1} участников\n"
                    break
            
            text += f"\n📊 **Всего участников:** {len(members)}/50"
            
            await status_msg.edit_text(text, parse_mode="Markdown")
            
        except ApiError as e:
            await status_msg.edit_text(
                f"❌ **Ошибка CoC API**\n\n"
                f"Не удалось получить список участников: {e}"
            )
            
    except Exception as e:
        logger.error(f"Error in clan_members_command: {e}")
        await message.reply(
            "❌ **Ошибка получения участников клана**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("update_clan"))
async def update_clan_command(message: Message, command: CommandObject):
    """
    Обновить данные клана из CoC API
    Синтаксис: /update_clan [номер|тег]
    """
    try:
        db_service = get_clan_db_service()
        coc_api = get_coc_api_service()
        permission_service = get_permission_service()
        
        clan = None
        
        if command.args:
            arg = command.args.strip()
            
            # Пробуем найти по тегу
            if arg.startswith('#'):
                clan = await db_service.get_clan_by_tag(arg, message.chat.id)
            else:
                # Пробуем найти по номеру из списка
                try:
                    clan_number = int(arg)
                    clans = await db_service.get_chat_clans(message.chat.id)
                    
                    if 1 <= clan_number <= len(clans):
                        clan = clans[clan_number - 1]
                    else:
                        await message.reply(
                            f"❌ **Неверный номер клана!**\n\n"
                            f"Доступные кланы: 1-{len(clans)}\n"
                            "Используйте `/clan_list` для просмотра всех кланов."
                        )
                        return
                except ValueError:
                    await message.reply(
                        "❌ **Неверный формат!**\n\n"
                        "**Использование:** `/update_clan [номер|тег]`\n\n"
                        "**Примеры:**\n"
                        "• `/update_clan 1` - обновить первый клан\n"
                        "• `/update_clan #2PP0JCCL` - обновить по тегу"
                    )
                    return
        else:
            # Обновляем основной клан
            settings = await db_service.get_chat_settings(message.chat.id)
            if settings.default_clan_id:
                clan = await db_service.get_clan_by_id(settings.default_clan_id)
            else:
                await message.reply(
                    "❌ **Основной клан не установлен!**\n\n"
                    "Используйте:\n"
                    "• `/update_clan <номер>` - обновить конкретный клан\n"
                    "• `/set_default_clan <номер>` - установить основной клан"
                )
                return
        
        if not clan:
            await message.reply(
                "❌ **Клан не найден!**\n\n"
                "Проверьте правильность тега или номера клана."
            )
            return
        
        # Проверяем права на управление кланом
        if not await permission_service.can_manage_clan(message.from_user.id, clan.id):
            await message.reply(
                "❌ **Недостаточно прав!**\n\n"
                "Обновлять данные клана могут только администраторы чата "
                "или тот кто зарегистрировал клан."
            )
            return
        
        # Показываем процесс обновления
        status_msg = await message.reply(
            f"🔄 **Обновляю данные клана {clan.clan_name}...**\n"
            "⏳ Получаю актуальные данные из CoC API..."
        )
        
        try:
            # Получаем свежие данные из CoC API
            async with coc_api:
                fresh_clan_data = await coc_api.get_clan(clan.clan_tag)
            
            # Сохраняем старые данные для сравнения
            old_level = clan.clan_level
            old_points = clan.clan_points
            old_members = clan.member_count
            
            # Обновляем в БД
            success = await db_service.update_clan_data(clan.id, fresh_clan_data)
            
            if success:
                # Формируем отчет об изменениях
                changes = []
                
                if fresh_clan_data.level != old_level:
                    changes.append(f"🆙 Уровень: {old_level} → {fresh_clan_data.level}")
                
                if fresh_clan_data.points != old_points:
                    diff = fresh_clan_data.points - old_points
                    sign = "+" if diff > 0 else ""
                    changes.append(f"🏆 Очки: {format_number(old_points)} → {format_number(fresh_clan_data.points)} ({sign}{format_number(diff)})")
                
                if fresh_clan_data.member_count != old_members:
                    diff = fresh_clan_data.member_count - old_members
                    sign = "+" if diff > 0 else ""
                    changes.append(f"👥 Участников: {old_members} → {fresh_clan_data.member_count} ({sign}{diff})")
                
                # Формируем ответ
                text = f"✅ **Данные клана обновлены!**\n\n"
                text += f"🏰 **{fresh_clan_data.name}** `{fresh_clan_data.tag}`\n\n"
                
                if changes:
                    text += "📈 **Изменения:**\n"
                    for change in changes:
                        text += f"• {change}\n"
                else:
                    text += "📊 **Изменений нет** - все данные актуальны\n"
                
                text += f"\n⏰ **Последнее обновление:** только что"
                
                await status_msg.edit_text(text, parse_mode="Markdown")
                
                # Логируем операцию
                log_entry = ClanOperationLog.create_log(
                    operation_type='update',
                    clan_id=clan.id,
                    clan_tag=clan.clan_tag,
                    chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    username=message.from_user.username,
                    operation_details={'changes': changes},
                    result='success'
                )
                await db_service.log_operation(log_entry)
                
            else:
                await status_msg.edit_text(
                    "❌ **Ошибка обновления данных**\n\n"
                    "Не удалось сохранить изменения в базе данных."
                )
                
        except ClanNotFound:
            await status_msg.edit_text(
                f"❌ **Клан {clan.clan_tag} больше не существует!**\n\n"
                "Клан был удален из Clash of Clans или изменил тег.\n"
                "Рассмотрите возможность деактивации клана в боте."
            )
        except ApiError as e:
            await status_msg.edit_text(
                f"❌ **Ошибка CoC API**\n\n"
                f"Не удалось получить данные клана: {e}"
            )
            
    except Exception as e:
        logger.error(f"Error in update_clan_command: {e}")
        await message.reply(
            "❌ **Ошибка обновления клана**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("deactivate_clan"))
async def deactivate_clan_command(message: Message, command: CommandObject):
    """
    Деактивировать клан (скрыть из списков, но сохранить данные)
    Синтаксис: /deactivate_clan <номер|тег>
    """
    try:
        db_service = get_clan_db_service()
        permission_service = get_permission_service()
        
        # Проверяем права администратора
        await permission_service.require_admin(
            message.from_user.id, message.chat.id, "deactivating clan"
        )
        
        if not command.args:
            await message.reply(
                "❌ **Укажите клан для деактивации!**\n\n"
                "**Использование:** `/deactivate_clan <номер|тег>`\n\n"
                "⚠️ **Внимание:** Деактивация скроет клан из списков, "
                "но сохранит все данные и историю."
            )
            return
        
        arg = command.args.strip()
        clan = None
        
        # Пробуем найти по тегу
        if arg.startswith('#'):
            clan = await db_service.get_clan_by_tag(arg, message.chat.id)
        else:
            # Пробуем найти по номеру
            try:
                clan_number = int(arg)
                clans = await db_service.get_chat_clans(message.chat.id)
                
                if 1 <= clan_number <= len(clans):
                    clan = clans[clan_number - 1]
                else:
                    await message.reply(
                        f"❌ **Неверный номер клана!**\n\n"
                        f"Доступные кланы: 1-{len(clans)}"
                    )
                    return
            except ValueError:
                await message.reply(
                    "❌ **Неверный формат!**\n\n"
                    "Используйте номер клана или тег: `/deactivate_clan 2` или `/deactivate_clan #ABC123`"
                )
                return
        
        if not clan:
            await message.reply(
                "❌ **Клан не найден!**\n\n"
                "Проверьте правильность номера или тега клана."
            )
            return
        
        # Подтверждение деактивации
        await message.reply(
            f"⚠️ **Подтвердите деактивацию клана**\n\n"
            f"🏰 **{clan.clan_name}** `{clan.clan_tag}`\n\n"
            f"**Что произойдет:**\n"
            f"• Клан исчезнет из списков\n"
            f"• Нельзя будет создавать новые паспорта с этим кланом\n"
            f"• Существующие паспорта сохранятся\n"
            f"• Все данные останутся в базе\n\n"
            f"**Для подтверждения введите:** `/confirm_deactivate {clan.id}`",
            parse_mode="Markdown"
        )
        
    except PermissionDenied:
        await message.reply(
            "❌ **Недостаточно прав!**\n\n"
            "Деактивировать кланы могут только администраторы чата."
        )
    except Exception as e:
        logger.error(f"Error in deactivate_clan_command: {e}")
        await message.reply(
            "❌ **Произошла ошибка**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("confirm_deactivate"))
async def confirm_deactivate_clan_command(message: Message, command: CommandObject):
    """
    Подтверждение деактивации клана
    Синтаксис: /confirm_deactivate <id_клана>
    """
    try:
        db_service = get_clan_db_service()
        permission_service = get_permission_service()
        
        # Проверяем права администратора
        await permission_service.require_admin(
            message.from_user.id, message.chat.id, "confirming clan deactivation"
        )
        
        if not command.args:
            await message.reply("❌ **Не указан ID клана для подтверждения**")
            return
        
        try:
            clan_id = int(command.args.strip())
        except ValueError:
            await message.reply("❌ **Неверный ID клана**")
            return
        
        # Получаем клан
        clan = await db_service.get_clan_by_id(clan_id)
        
        if not clan or clan.chat_id != message.chat.id:
            await message.reply("❌ **Клан не найден или принадлежит другому чату**")
            return
        
        # Деактивируем клан в БД
        async with aiosqlite.connect(db_service.db_path) as db:
            await db.execute(
                "UPDATE registered_clans SET is_active = 0 WHERE id = ?",
                (clan_id,)
            )
            await db.commit()
        
        # Логируем операцию
        log_entry = ClanOperationLog.create_log(
            operation_type='deactivate',
            clan_id=clan_id,
            clan_tag=clan.clan_tag,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            username=message.from_user.username,
            result='success'
        )
        await db_service.log_operation(log_entry)
        
        await message.reply(
            f"✅ **Клан деактивирован**\n\n"
            f"🏰 {clan.clan_name} `{clan.clan_tag}` больше не отображается в списках.\n\n"
            f"💡 **Для восстановления клана обратитесь к разработчику бота.**",
            parse_mode="Markdown"
        )
        
    except PermissionDenied:
        await message.reply(
            "❌ **Недостаточно прав!**\n\n"
            "Деактивировать кланы могут только администраторы чата."
        )
    except Exception as e:
        logger.error(f"Error in confirm_deactivate_clan_command: {e}")
        await message.reply("❌ **Ошибка деактивации клана**")


@clan_router.message(Command("clan_stats"))  
async def clan_stats_command(message: Message, command: CommandObject):
    """
    Показать расширенную статистику клана
    Синтаксис: /clan_stats [номер|тег]
    """
    try:
        db_service = get_clan_db_service()
        coc_api = get_coc_api_service()
        
        clan = None
        
        if command.args:
            arg = command.args.strip()
            
            # Пробуем найти по тегу
            if arg.startswith('#'):
                clan = await db_service.get_clan_by_tag(arg, message.chat.id)
            else:
                # Пробуем найти по номеру из списка
                try:
                    clan_number = int(arg)
                    clans = await db_service.get_chat_clans(message.chat.id)
                    
                    if 1 <= clan_number <= len(clans):
                        clan = clans[clan_number - 1]
                    else:
                        await message.reply(
                            f"❌ **Неверный номер клана!**\n\n"
                            f"Доступные кланы: 1-{len(clans)}"
                        )
                        return
                except ValueError:
                    await message.reply(
                        "❌ **Неверный формат!**\n\n"
                        "**Использование:** `/clan_stats [номер|тег]`"
                    )
                    return
        else:
            # Показываем статистику основного клана
            settings = await db_service.get_chat_settings(message.chat.id)
            if settings.default_clan_id:
                clan = await db_service.get_clan_by_id(settings.default_clan_id)
            else:
                await message.reply(
                    "❌ **Основной клан не установлен!**\n\n"
                    "Используйте `/clan_stats <номер>` для конкретного клана."
                )
                return
        
        if not clan:
            await message.reply("❌ **Клан не найден!**")
            return
        
        # Загружаем данные
        status_msg = await message.reply(
            f"📊 **Собираю статистику клана {clan.clan_name}...**\n"
            "⏳ Это может занять несколько секунд..."
        )
        
        try:
            # Получаем свежие данные и участников
            async with coc_api:
                clan_data = await coc_api.get_clan(clan.clan_tag)
                members = await coc_api.get_clan_members(clan.clan_tag)
            
            # Анализируем участников
            total_donations = sum(member.get('donations', 0) for member in members)
            total_received = sum(member.get('donationsReceived', 0) for member in members)
            avg_level = sum(member.get('expLevel', 0) for member in members) / len(members) if members else 0
            
            # Подсчитываем роли
            roles = {}
            for member in members:
                role = member.get('role', 'member')
                roles[role] = roles.get(role, 0) + 1
            
            # Топ донаторы (топ 5)
            top_donors = sorted(members, key=lambda x: x.get('donations', 0), reverse=True)[:5]
            
            # Формируем статистику
            metadata = clan.clan_metadata
            
            text = (
                f"📊 **Расширенная статистика клана**\n\n"
                f"🏰 **{clan_data.name}** `{clan_data.tag}`\n"
                f"📝 {clan_data.description}\n\n"
                
                f"**🎯 Основные показатели:**\n"
                f"• 🏆 Очки клана: {format_number(clan_data.points)}\n"
                f"• 📊 Уровень клана: {clan_data.level}\n"
                f"• 👥 Участников: {len(members)}/50\n"
                f"• 🌍 Локация: {metadata.get('location', 'Неизвестно')}\n\n"
                
                f"**⚔️ Военная статистика:**\n"
                f"• 🏅 Побед в войнах: {metadata.get('war_wins', 0)}\n"
                f"• 🔥 Текущая серия: {metadata.get('war_win_streak', 0)}\n\n"
                
                f"**💝 Донаты:**\n"
                f"• 📤 Всего отдано: {format_number(total_donations)}\n"
                f"• 📥 Всего получено: {format_number(total_received)}\n"
                f"• 📊 Средний уровень: {avg_level:.1f}\n\n"
                
                f"**👑 Распределение ролей:**\n"
            )
            
            role_emojis = {
                'leader': '👑 Лидер',
                'coLeader': '🌟 Со-лидер', 
                'admin': '⭐ Старейшина',
                'member': '👤 Участник'
            }
            
            for role, emoji_name in role_emojis.items():
                count = roles.get(role, 0)
                if count > 0:
                    text += f"• {emoji_name}: {count}\n"
            
            if top_donors:
                text += f"\n**🏆 Топ донаторы:**\n"
                for i, donor in enumerate(top_donors, 1):
                    donations = donor.get('donations', 0)
                    name = donor.get('name', 'Unknown')
                    text += f"{i}. **{name}** - {format_number(donations)} 💝\n"
            
            text += f"\n📅 **Последнее обновление:** {format_date(clan.last_updated)}"
            
            await status_msg.edit_text(text, parse_mode="Markdown")
            
        except ApiError as e:
            await status_msg.edit_text(
                f"❌ **Ошибка CoC API**\n\n"
                f"Не удалось получить статистику: {e}"
            )
            
    except Exception as e:
        logger.error(f"Error in clan_stats_command: {e}")
        await message.reply(
            "❌ **Ошибка получения статистики клана**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("update_all_clans"))
async def update_all_clans_command(message: Message):
    """
    Обновить данные всех кланов в чате
    """
    try:
        db_service = get_clan_db_service()
        coc_api = get_coc_api_service()
        permission_service = get_permission_service()
        
        # Проверяем права администратора
        await permission_service.require_admin(
            message.from_user.id, message.chat.id, "updating all clans"
        )
        
        # Получаем все кланы чата
        clans = await db_service.get_chat_clans(message.chat.id)
        
        if not clans:
            await message.reply(
                "❌ **В этом чате нет зарегистрированных кланов**\n\n"
                "Используйте `/register_clan <тег>` для регистрации первого клана."
            )
            return
        
        # Показываем процесс обновления
        status_msg = await message.reply(
            f"🔄 **Обновляю данные всех кланов...**\n\n"
            f"📊 Кланов к обновлению: {len(clans)}\n"
            "⏳ Это может занять до минуты..."
        )
        
        updated_count = 0
        failed_count = 0
        failed_clans = []
        
        async with coc_api:
            for i, clan in enumerate(clans, 1):
                try:
                    # Обновляем статус
                    await status_msg.edit_text(
                        f"🔄 **Обновляю данные кланов...**\n\n"
                        f"📊 Прогресс: {i}/{len(clans)}\n"
                        f"🏰 Обновляю: {clan.clan_name}\n"
                        f"✅ Обновлено: {updated_count}\n"
                        f"❌ Ошибок: {failed_count}",
                        parse_mode="Markdown"
                    )
                    
                    # Получаем свежие данные
                    fresh_data = await coc_api.get_clan(clan.clan_tag)
                    
                    # Обновляем в БД
                    success = await db_service.update_clan_data(clan.id, fresh_data)
                    
                    if success:
                        updated_count += 1
                    else:
                        failed_count += 1
                        failed_clans.append(clan.clan_name)
                        
                except Exception as e:
                    failed_count += 1
                    failed_clans.append(f"{clan.clan_name}: {str(e)}")
                    logger.error(f"Failed to update clan {clan.clan_tag}: {e}")
        
        # Финальный результат
        result_text = f"✅ **Обновление завершено!**\n\n"
        result_text += f"📊 **Результаты:**\n"
        result_text += f"• ✅ Успешно обновлено: {updated_count}\n"
        result_text += f"• ❌ Ошибок: {failed_count}\n"
        result_text += f"• 📈 Всего кланов: {len(clans)}\n\n"
        
        if failed_clans:
            result_text += "**❌ Ошибки обновления:**\n"
            for failed in failed_clans[:5]:  # Показываем максимум 5 ошибок
                result_text += f"• {failed}\n"
            
            if len(failed_clans) > 5:
                result_text += f"... и еще {len(failed_clans) - 5} ошибок\n"
        
        result_text += f"\n⏰ **Время обновления:** только что"
        
        await status_msg.edit_text(result_text, parse_mode="Markdown")
        
    except PermissionDenied:
        await message.reply(
            "❌ **Недостаточно прав!**\n\n"
            "Обновлять все кланы могут только администраторы чата."
        )
    except Exception as e:
        logger.error(f"Error in update_all_clans_command: {e}")
        await message.reply(
            "❌ **Ошибка массового обновления кланов**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("clan_analysis"))
async def clan_analysis_command(message: Message, command: CommandObject):
    """
    Глубокий анализ клана с рекомендациями
    Синтаксис: /clan_analysis [номер|тег]
    """
    try:
        db_service = get_clan_db_service()
        analysis_manager = get_clan_analysis_manager()
        
        clan = None
        
        if command.args:
            arg = command.args.strip()
            
            # Пробуем найти по тегу
            if arg.startswith('#'):
                clan = await db_service.get_clan_by_tag(arg, message.chat.id)
            else:
                # Пробуем найти по номеру из списка
                try:
                    clan_number = int(arg)
                    clans = await db_service.get_chat_clans(message.chat.id)
                    
                    if 1 <= clan_number <= len(clans):
                        clan = clans[clan_number - 1]
                    else:
                        await message.reply(
                            f"❌ **Неверный номер клана!**\n\n"
                            f"Доступные кланы: 1-{len(clans)}"
                        )
                        return
                except ValueError:
                    await message.reply(
                        "❌ **Неверный формат!**\n\n"
                        "**Использование:** `/clan_analysis [номер|тег]`"
                    )
                    return
        else:
            # Анализируем основной клан
            settings = await db_service.get_chat_settings(message.chat.id)
            if settings.default_clan_id:
                clan = await db_service.get_clan_by_id(settings.default_clan_id)
            else:
                await message.reply(
                    "❌ **Основной клан не установлен!**\n\n"
                    "Используйте `/clan_analysis <номер>` для конкретного клана."
                )
                return
        
        if not clan:
            await message.reply("❌ **Клан не найден!**")
            return
        
        # Показываем процесс анализа
        status_msg = await message.reply(
            f"🔍 **Анализирую клан {clan.clan_name}...**\n\n"
            "⏳ Собираю данные и провожу анализ...\n"
            "📊 Это займет несколько секунд..."
        )
        
        # Проводим анализ
        analysis = await analysis_manager.analyze_clan_performance(
            clan.clan_tag, message.chat.id
        )
        
        if 'error' in analysis:
            await status_msg.edit_text(
                f"❌ **Ошибка анализа**\n\n{analysis['error']}"
            )
            return
        
        # Получаем рекомендации
        recommendations = await analysis_manager.get_clan_recommendations(
            clan.clan_tag, message.chat.id
        )
        
        # Формируем результат анализа
        clan_info = analysis['clan_info']
        activity = analysis['activity']
        health = analysis['health']
        donations = analysis['donations']
        
        text = (
            f"🔬 **Глубокий анализ клана**\n\n"
            f"🏰 **{clan_info['name']}** `{clan_info['tag']}`\n\n"
            
            f"**🎯 Общая оценка:**\n"
            f"• {health['status_emoji']} Статус: {health['status']}\n"
            f"• 📊 Здоровье клана: {health['health_score']}/100\n"
            f"• ⚡ Активность: {activity['activity_score']}/100\n\n"
            
            f"**👥 Состав клана:**\n"
            f"• 👤 Участников: {clan_info['member_count']}/50\n"
            f"• 🎯 Средний уровень: {activity['avg_level']}\n"
            f"• 🔥 Активных игроков: {activity['active_members']}\n\n"
            
            f"**💝 Донаты:**\n"
            f"• 📤 Отдано: {format_number(donations['total_donated'])}\n"
            f"• 📥 Получено: {format_number(donations['total_received'])}\n"
            f"• 📊 Эффективность: {donations['efficiency_ratio']:.2f}\n\n"
        )
        
        # Добавляем проблемы
        if health['issues']:
            text += "**⚠️ Выявленные проблемы:**\n"
            for issue in health['issues'][:3]:
                text += f"• {issue}\n"
            text += "\n"
        
        # Добавляем рекомендации
        if recommendations:
            text += "**💡 Рекомендации:**\n"
            for rec in recommendations[:5]:  # Топ 5 рекомендаций
                text += f"• {rec}\n"
        
        text += f"\n📅 **Дата анализа:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        await status_msg.edit_text(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in clan_analysis_command: {e}")
        await message.reply(
            "❌ **Ошибка анализа клана**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )


@clan_router.message(Command("compare_clans"))
async def compare_clans_command(message: Message, command: CommandObject):
    """
    Сравнить два клана
    Синтаксис: /compare_clans <номер1|тег1> <номер2|тег2>
    """
    try:
        if not command.args:
            await message.reply(
                "❌ **Укажите два клана для сравнения!**\n\n"
                "**Использование:** `/compare_clans <клан1> <клан2>`\n\n"
                "**Примеры:**\n"
                "• `/compare_clans 1 2` - сравнить первый и второй кланы\n"
                "• `/compare_clans #ABC123 #DEF456` - по тегам\n"
                "• `/compare_clans 1 #DEF456` - смешанный формат"
            )
            return
        
        args = command.args.strip().split()
        if len(args) != 2:
            await message.reply(
                "❌ **Нужно указать ровно два клана!**\n\n"
                "Пример: `/compare_clans 1 2`"
            )
            return
        
        db_service = get_clan_db_service()
        analysis_manager = get_clan_analysis_manager()
        
        # Функция для поиска клана
        async def find_clan(arg: str):
            if arg.startswith('#'):
                return await db_service.get_clan_by_tag(arg, message.chat.id)
            else:
                try:
                    clan_number = int(arg)
                    clans = await db_service.get_chat_clans(message.chat.id)
                    if 1 <= clan_number <= len(clans):
                        return clans[clan_number - 1]
                except ValueError:
                    pass
            return None
        
        clan1 = await find_clan(args[0])
        clan2 = await find_clan(args[1])
        
        if not clan1:
            await message.reply(f"❌ **Клан '{args[0]}' не найден!**")
            return
        
        if not clan2:
            await message.reply(f"❌ **Клан '{args[1]}' не найден!**")
            return
        
        if clan1.id == clan2.id:
            await message.reply("❌ **Нельзя сравнить клан с самим собой!**")
            return
        
        # Показываем процесс сравнения
        status_msg = await message.reply(
            f"⚔️ **Сравниваю кланы...**\n\n"
            f"🏰 {clan1.clan_name} vs {clan2.clan_name}\n"
            "⏳ Анализирую данные..."
        )
        
        # Проводим сравнение
        comparison = await analysis_manager.compare_clans(
            clan1.clan_tag, clan2.clan_tag, message.chat.id
        )
        
        if 'error' in comparison:
            await status_msg.edit_text(f"❌ **Ошибка сравнения:** {comparison['error']}")
            return
        
        # Формируем результат
        clan1_info = comparison['clan1']
        clan2_info = comparison['clan2']
        winners = comparison['winner_categories']
        
        text = f"⚔️ **Сравнение кланов**\n\n"
        
        # Эмодзи для победителей
        def get_winner_emoji(category):
            winner = winners.get(category, 0)
            if winner == 1:
                return "🥇", "🥈"
            elif winner == 2:
                return "🥈", "🥇"
            else:
                return "🤝", "🤝"
        
        # Сравниваем основные показатели
        categories = [
            ('points', 'Очки клана', clan1_info['points'], clan2_info['points']),
            ('level', 'Уровень', clan1_info['level'], clan2_info['level']),
            ('members', 'Участников', clan1_info['member_count'], clan2_info['member_count'])
        ]
        
        for cat_key, cat_name, val1, val2 in categories:
            emoji1, emoji2 = get_winner_emoji(cat_key)
            text += f"**🏆 {cat_name}:**\n"
            text += f"{emoji1} {clan1_info['name']}: {format_number(val1) if cat_key == 'points' else val1}\n"
            text += f"{emoji2} {clan2_info['name']}: {format_number(val2) if cat_key == 'points' else val2}\n\n"
        
        # Общий результат
        summary = comparison['summary']
        overall_winner = comparison.get('overall_winner', 0)
        
        if overall_winner == 1:
            text += f"🎉 **Общий победитель:** {clan1_info['name']}\n"
        elif overall_winner == 2:
            text += f"🎉 **Общий победитель:** {clan2_info['name']}\n"
        else:
            text += f"🤝 **Результат:** Ничья!\n"
        
        text += f"📊 **Счет:** {summary['clan1_wins']} - {summary['clan2_wins']}"
        
        await status_msg.edit_text(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in compare_clans_command: {e}")
        await message.reply(
            "❌ **Ошибка сравнения кланов**\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )