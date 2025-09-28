"""
Команды для управления системой приветствий
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Optional

from ..services.greeting_service import greeting_service
from ..utils.keyboards import create_inline_keyboard
from ..utils.permissions import is_admin, is_group_admin
from ..utils.formatters import format_user_mention

logger = logging.getLogger(__name__)

router = Router()


class GreetingStates(StatesGroup):
    """Состояния FSM для настройки приветствий"""
    waiting_for_greeting_text = State()
    waiting_for_rules_text = State()
    waiting_for_delete_delay = State()


# Основная команда настройки приветствий

@router.message(Command("greeting"))
async def cmd_greeting(message: Message, state: FSMContext):
    """Основная команда управления приветствиями"""
    
    # Проверяем, что команда выполняется в группе
    if message.chat.type not in ['group', 'supergroup']:
        await message.reply("❌ Эта команда работает только в группах!")
        return
    
    # Проверяем права администратора
    if not await is_group_admin(message.from_user.id, message.chat.id, message.bot):
        await message.reply("❌ Только администраторы могут управлять приветствиями!")
        return
    
    await state.clear()
    
    # Получаем текущие настройки
    settings = await greeting_service.get_greeting_settings(message.chat.id)
    stats = await greeting_service.get_greeting_stats(message.chat.id)
    
    # Формируем информацию о текущих настройках
    status_emoji = "✅" if settings.is_enabled else "❌"
    status_text = "включены" if settings.is_enabled else "выключены"
    
    text = f"""🤝 **Настройки приветствий**

**Статус:** {status_emoji} Приветствия {status_text}

**Текущие настройки:**
• Текст: {"есть" if settings.greeting_text else "не задан"}
• Упоминание пользователя: {"да" if settings.mention_user else "нет"}
• Стикер: {"есть" if settings.welcome_sticker else "нет"}
• Автоудаление: {"через " + str(settings.delete_after_seconds) + " сек" if settings.delete_after_seconds else "нет"}
• Кнопка правил: {"да" if settings.show_rules_button else "нет"}

**Статистика:**
• Всего приветствий: {stats.total_greetings_sent}
• Среднее в день: {stats.average_new_members_per_day:.1f}
• Самый активный день: {stats.most_active_day or "не определен"}
• Эффективность: {stats.greeting_effectiveness:.1f}%

Выберите действие:"""
    
    keyboard = create_greeting_main_keyboard(settings.is_enabled)
    
    await message.reply(text, reply_markup=keyboard, parse_mode="Markdown")


def create_greeting_main_keyboard(is_enabled: bool) -> InlineKeyboardMarkup:
    """Создание основной клавиатуры приветствий"""
    
    buttons = []
    
    # Кнопка включения/выключения
    if is_enabled:
        buttons.append([InlineKeyboardButton(text="❌ Выключить приветствия", callback_data="greeting_toggle_off")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Включить приветствия", callback_data="greeting_toggle_on")])
    
    # Настройки
    buttons.extend([
        [InlineKeyboardButton(text="📝 Изменить текст", callback_data="greeting_set_text")],
        [InlineKeyboardButton(text="🎨 Выбрать шаблон", callback_data="greeting_templates")],
        [InlineKeyboardButton(text="⚙️ Дополнительные настройки", callback_data="greeting_advanced")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="greeting_stats")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="greeting_close")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Обработка кнопок

@router.callback_query(F.data.startswith("greeting_"))
async def handle_greeting_callbacks(callback: CallbackQuery, state: FSMContext):
    """Обработка callback-запросов приветствий"""
    
    # Проверяем права
    if not await is_group_admin(callback.from_user.id, callback.message.chat.id, callback.bot):
        await callback.answer("❌ Недостаточно прав!", show_alert=True)
        return
    
    action = callback.data.split("_", 1)[1]
    
    if action == "toggle_on":
        await toggle_greeting_status(callback, True)
    
    elif action == "toggle_off":
        await toggle_greeting_status(callback, False)
    
    elif action == "set_text":
        await start_text_input(callback, state)
    
    elif action == "templates":
        await show_greeting_templates(callback)
    
    elif action == "advanced":
        await show_advanced_settings(callback)
    
    elif action == "stats":
        await show_greeting_statistics(callback)
    
    elif action == "close":
        await callback.message.delete()
        await callback.answer()
    
    else:
        await callback.answer("❌ Неизвестное действие")


async def toggle_greeting_status(callback: CallbackQuery, enabled: bool):
    """Переключение статуса приветствий"""
    
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    
    success = await greeting_service.toggle_greeting(chat_id, user_id, enabled)
    
    if success:
        status_text = "включены" if enabled else "выключены"
        await callback.answer(f"✅ Приветствия {status_text}!", show_alert=True)
        
        # Обновляем сообщение
        settings = await greeting_service.get_greeting_settings(chat_id)
        keyboard = create_greeting_main_keyboard(settings.is_enabled)
        
        # Обновляем текст сообщения
        new_text = callback.message.text.replace(
            "❌ Приветствия выключены" if enabled else "✅ Приветствия включены",
            "✅ Приветствия включены" if enabled else "❌ Приветствия выключены"
        )
        
        await callback.message.edit_text(new_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.answer("❌ Ошибка изменения настроек", show_alert=True)


async def start_text_input(callback: CallbackQuery, state: FSMContext):
    """Начало ввода текста приветствия"""
    
    text = """📝 **Ввод текста приветствия**

Отправьте новый текст приветствия. Вы можете использовать специальные переменные:

• `{name}` - имя пользователя
• `{username}` - юзернейм пользователя
• `{mention}` - упоминание пользователя
• `{first_name}` - имя пользователя

**Пример:**
Привет, {mention}! Добро пожаловать в наш чат! 👋

Отправьте /cancel для отмены."""
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(GreetingStates.waiting_for_greeting_text)
    await state.update_data(original_message_id=callback.message.message_id)
    await callback.answer()


@router.message(StateFilter(GreetingStates.waiting_for_greeting_text))
async def process_greeting_text(message: Message, state: FSMContext):
    """Обработка введенного текста приветствия"""
    
    # Проверяем права
    if not await is_group_admin(message.from_user.id, message.chat.id, message.bot):
        await message.reply("❌ Недостаточно прав!")
        return
    
    new_text = message.text.strip()
    
    if len(new_text) > 1000:
        await message.reply("❌ Текст слишком длинный! Максимум 1000 символов.")
        return
    
    # Сохраняем новый текст
    success = await greeting_service.set_greeting_text(
        chat_id=message.chat.id,
        admin_user_id=message.from_user.id,
        text=new_text
    )
    
    if success:
        await message.reply("✅ Текст приветствия обновлен!")
        
        # Показываем пример
        example = await greeting_service.get_greeting_settings(message.chat.id)
        formatted_example = example.format_greeting_for_user(
            first_name="Пример",
            username="example_user"
        )
        
        await message.reply(
            f"📋 **Пример приветствия:**\n\n{formatted_example}",
            parse_mode="Markdown"
        )
    else:
        await message.reply("❌ Ошибка сохранения текста")
    
    await state.clear()


async def show_greeting_templates(callback: CallbackQuery):
    """Показ доступных шаблонов приветствий"""
    
    templates = greeting_service.get_greeting_templates()
    
    text = "🎨 **Выберите шаблон приветствия:**\n\n"
    
    buttons = []
    for template_name, template_text in templates.items():
        # Показываем превью шаблона (первые 50 символов)
        preview = template_text[:50] + "..." if len(template_text) > 50 else template_text
        text += f"**{template_name.title()}:**\n{preview}\n\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"📋 {template_name.title()}", 
                callback_data=f"template_{template_name}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="greeting_back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("template_"))
async def apply_greeting_template(callback: CallbackQuery):
    """Применение шаблона приветствия"""
    
    # Проверяем права
    if not await is_group_admin(callback.from_user.id, callback.message.chat.id, callback.bot):
        await callback.answer("❌ Недостаточно прав!", show_alert=True)
        return
    
    template_name = callback.data.split("_", 1)[1]
    
    success = await greeting_service.apply_greeting_template(
        chat_id=callback.message.chat.id,
        admin_user_id=callback.from_user.id,
        template_name=template_name
    )
    
    if success:
        await callback.answer(f"✅ Шаблон '{template_name}' применен!", show_alert=True)
        
        # Возвращаемся к главному меню
        await cmd_greeting_refresh(callback)
    else:
        await callback.answer("❌ Ошибка применения шаблона", show_alert=True)


async def show_advanced_settings(callback: CallbackQuery):
    """Показ дополнительных настроек"""
    
    settings = await greeting_service.get_greeting_settings(callback.message.chat.id)
    
    text = f"""⚙️ **Дополнительные настройки**

**Текущие настройки:**
• Упоминание: {"✅" if settings.mention_user else "❌"}
• Автоудаление: {"✅ " + str(settings.delete_after_seconds) + " сек" if settings.delete_after_seconds else "❌"}
• Кнопка правил: {"✅" if settings.show_rules_button else "❌"}
• Стикер: {"✅" if settings.welcome_sticker else "❌"}

Выберите настройку для изменения:"""
    
    buttons = [
        [InlineKeyboardButton(
            text="👤 Упоминание: " + ("✅" if settings.mention_user else "❌"),
            callback_data="advanced_mention"
        )],
        [InlineKeyboardButton(
            text="⏰ Автоудаление: " + ("✅" if settings.delete_after_seconds else "❌"),
            callback_data="advanced_delete"
        )],
        [InlineKeyboardButton(
            text="📋 Кнопка правил: " + ("✅" if settings.show_rules_button else "❌"),
            callback_data="advanced_rules"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="greeting_back")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("advanced_"))
async def handle_advanced_settings(callback: CallbackQuery, state: FSMContext):
    """Обработка дополнительных настроек"""
    
    # Проверяем права
    if not await is_group_admin(callback.from_user.id, callback.message.chat.id, callback.bot):
        await callback.answer("❌ Недостаточно прав!", show_alert=True)
        return
    
    setting = callback.data.split("_", 1)[1]
    settings = await greeting_service.get_greeting_settings(callback.message.chat.id)
    
    if setting == "mention":
        # Переключаем упоминание
        new_value = not settings.mention_user
        success = await greeting_service.update_greeting_settings(
            chat_id=callback.message.chat.id,
            admin_user_id=callback.from_user.id,
            mention_user=new_value
        )
        
        if success:
            status = "включено" if new_value else "выключено"
            await callback.answer(f"✅ Упоминание пользователя {status}!")
            await show_advanced_settings(callback)
        else:
            await callback.answer("❌ Ошибка изменения настройки", show_alert=True)
    
    elif setting == "delete":
        # Настройка автоудаления
        text = """⏰ **Настройка автоудаления**

Введите время в секундах, через которое сообщение приветствия будет удалено.

Введите 0 для отключения автоудаления.
Максимальное время: 3600 секунд (1 час).

Отправьте /cancel для отмены."""
        
        await callback.message.edit_text(text, parse_mode="Markdown")
        await state.set_state(GreetingStates.waiting_for_delete_delay)
        await callback.answer()
    
    elif setting == "rules":
        # Настройка кнопки правил
        if settings.show_rules_button:
            # Выключаем кнопку правил
            success = await greeting_service.update_greeting_settings(
                chat_id=callback.message.chat.id,
                admin_user_id=callback.from_user.id,
                show_rules_button=False
            )
            
            if success:
                await callback.answer("✅ Кнопка правил выключена!")
                await show_advanced_settings(callback)
        else:
            # Включаем кнопку правил - нужен текст
            text = """📋 **Настройка кнопки правил**

Отправьте текст правил, который будет показан при нажатии на кнопку.

Отправьте /cancel для отмены."""
            
            await callback.message.edit_text(text, parse_mode="Markdown")
            await state.set_state(GreetingStates.waiting_for_rules_text)
            await callback.answer()


@router.message(StateFilter(GreetingStates.waiting_for_delete_delay))
async def process_delete_delay(message: Message, state: FSMContext):
    """Обработка времени автоудаления"""
    
    # Проверяем права
    if not await is_group_admin(message.from_user.id, message.chat.id, message.bot):
        await message.reply("❌ Недостаточно прав!")
        return
    
    try:
        delay = int(message.text.strip())
        
        if delay < 0 or delay > 3600:
            await message.reply("❌ Время должно быть от 0 до 3600 секунд!")
            return
        
        # Сохраняем настройку
        success = await greeting_service.update_greeting_settings(
            chat_id=message.chat.id,
            admin_user_id=message.from_user.id,
            delete_after_seconds=delay if delay > 0 else None
        )
        
        if success:
            if delay > 0:
                await message.reply(f"✅ Автоудаление установлено на {delay} секунд!")
            else:
                await message.reply("✅ Автоудаление отключено!")
        else:
            await message.reply("❌ Ошибка сохранения настройки")
        
    except ValueError:
        await message.reply("❌ Введите корректное число!")
        return
    
    await state.clear()


@router.message(StateFilter(GreetingStates.waiting_for_rules_text))
async def process_rules_text(message: Message, state: FSMContext):
    """Обработка текста правил"""
    
    # Проверяем права
    if not await is_group_admin(message.from_user.id, message.chat.id, message.bot):
        await message.reply("❌ Недостаточно прав!")
        return
    
    rules_text = message.text.strip()
    
    if len(rules_text) > 2000:
        await message.reply("❌ Текст правил слишком длинный! Максимум 2000 символов.")
        return
    
    # Сохраняем правила и включаем кнопку
    success = await greeting_service.update_greeting_settings(
        chat_id=message.chat.id,
        admin_user_id=message.from_user.id,
        show_rules_button=True,
        rules_text=rules_text
    )
    
    if success:
        await message.reply("✅ Кнопка правил включена и текст сохранен!")
    else:
        await message.reply("❌ Ошибка сохранения правил")
    
    await state.clear()


async def show_greeting_statistics(callback: CallbackQuery):
    """Показ статистики приветствий"""
    
    stats = await greeting_service.get_greeting_stats(callback.message.chat.id)
    
    # Получаем историю
    history = await greeting_service.get_greeting_history(callback.message.chat.id, 10)
    
    text = f"""📊 **Статистика приветствий**

**Общая статистика:**
• Всего приветствий отправлено: {stats.total_greetings_sent}
• Среднее количество в день: {stats.average_new_members_per_day:.1f}
• Самый активный день недели: {stats.most_active_day or "не определен"}
• Эффективность ответов: {stats.greeting_effectiveness:.1f}%

**Последние приветствия:**"""
    
    if history:
        for i, entry in enumerate(history[:5], 1):
            date_str = entry['sent_date'].strftime("%d.%m %H:%M")
            name = entry['first_name'] or entry['username'] or f"ID{entry['user_id']}"
            responded = "✅" if entry['user_responded'] else "⏳"
            text += f"\n{i}. {name} - {date_str} {responded}"
    else:
        text += "\nПока нет приветствий"
    
    text += f"\n\n**Последнее приветствие:** {stats.last_greeting_date.strftime('%d.%m.%Y %H:%M') if stats.last_greeting_date else 'никогда'}"
    
    buttons = [
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="greeting_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="greeting_back")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "greeting_back")
async def cmd_greeting_refresh(callback: CallbackQuery):
    """Возврат к главному меню приветствий"""
    
    # Получаем обновленные настройки
    settings = await greeting_service.get_greeting_settings(callback.message.chat.id)
    stats = await greeting_service.get_greeting_stats(callback.message.chat.id)
    
    # Формируем текст как в основной команде
    status_emoji = "✅" if settings.is_enabled else "❌"
    status_text = "включены" if settings.is_enabled else "выключены"
    
    text = f"""🤝 **Настройки приветствий**

**Статус:** {status_emoji} Приветствия {status_text}

**Текущие настройки:**
• Текст: {"есть" if settings.greeting_text else "не задан"}
• Упоминание пользователя: {"да" if settings.mention_user else "нет"}
• Стикер: {"есть" if settings.welcome_sticker else "нет"}
• Автоудаление: {"через " + str(settings.delete_after_seconds) + " сек" if settings.delete_after_seconds else "нет"}
• Кнопка правил: {"да" if settings.show_rules_button else "нет"}

**Статистика:**
• Всего приветствий: {stats.total_greetings_sent}
• Среднее в день: {stats.average_new_members_per_day:.1f}
• Самый активный день: {stats.most_active_day or "не определен"}
• Эффективность: {stats.greeting_effectiveness:.1f}%

Выберите действие:"""
    
    keyboard = create_greeting_main_keyboard(settings.is_enabled)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# Команды быстрого управления

@router.message(Command("greeting_on"))
async def cmd_greeting_on(message: Message):
    """Быстрое включение приветствий"""
    
    if message.chat.type not in ['group', 'supergroup']:
        await message.reply("❌ Эта команда работает только в группах!")
        return
    
    if not await is_group_admin(message.from_user.id, message.chat.id, message.bot):
        await message.reply("❌ Только администраторы могут управлять приветствиями!")
        return
    
    success = await greeting_service.toggle_greeting(
        chat_id=message.chat.id,
        admin_user_id=message.from_user.id,
        enabled=True
    )
    
    if success:
        await message.reply("✅ Приветствия включены!")
    else:
        await message.reply("❌ Ошибка включения приветствий")


@router.message(Command("greeting_off"))
async def cmd_greeting_off(message: Message):
    """Быстрое выключение приветствий"""
    
    if message.chat.type not in ['group', 'supergroup']:
        await message.reply("❌ Эта команда работает только в группах!")
        return
    
    if not await is_group_admin(message.from_user.id, message.chat.id, message.bot):
        await message.reply("❌ Только администраторы могут управлять приветствиями!")
        return
    
    success = await greeting_service.toggle_greeting(
        chat_id=message.chat.id,
        admin_user_id=message.from_user.id,
        enabled=False
    )
    
    if success:
        await message.reply("✅ Приветствия выключены!")
    else:
        await message.reply("❌ Ошибка выключения приветствий")


# Обработка отмены

@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    
    current_state = await state.get_state()
    
    if current_state is None:
        await message.reply("Нет активных действий для отмены.")
        return
    
    await state.clear()
    await message.reply("✅ Действие отменено.")


# Обработка кнопки правил

@router.callback_query(F.data == "show_rules")
async def show_chat_rules(callback: CallbackQuery):
    """Показ правил чата"""
    
    settings = await greeting_service.get_greeting_settings(callback.message.chat.id)
    
    if settings.rules_text:
        await callback.answer(settings.rules_text, show_alert=True)
    else:
        await callback.answer("Правила не установлены", show_alert=True)