from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🎬 Смотреть портфолио", callback_data="portfolio:0")],
        [
            InlineKeyboardButton(text="👨‍💻 Обо мне", callback_data="about"),
            InlineKeyboardButton(text="📩 Контакты", callback_data="contacts")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👑 Панель управления", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_about_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Смотреть работы", callback_data="portfolio:0")],
        [InlineKeyboardButton(text="✈️ Написать в Telegram", url=f"https://t.me/{config.CONTACT_USERNAME}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_contacts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✈️ Написать @{config.CONTACT_USERNAME}", url=f"https://t.me/{config.CONTACT_USERNAME}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_portfolio_keyboard(current_index: int, total_count: int, work_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if total_count > 1:
        prev_idx = (current_index - 1) % total_count
        next_idx = (current_index + 1) % total_count
        rows.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"portfolio:{prev_idx}"),
            InlineKeyboardButton(text=f"📍 {current_index + 1} из {total_count}", callback_data="noop"),
            InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"portfolio:{next_idx}")
        ])
    else:
        rows.append([
            InlineKeyboardButton(text=f"📍 Работа 1 из 1", callback_data="noop")
        ])
    
    rows.append([
        InlineKeyboardButton(text="📩 Заказать подобный ролик", url=f"https://t.me/{config.CONTACT_USERNAME}")
    ])
    
    if is_admin:
        rows.append([
            InlineKeyboardButton(text=f"🔢 Поменять порядок (сейчас №{current_index + 1})", callback_data=f"admin_order_work:{work_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_del:{work_id}:{current_index}")
        ])
        
    rows.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_empty_portfolio_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if is_admin:
        rows.append([InlineKeyboardButton(text="➕ Добавить первую работу", callback_data="admin_add")])
    rows.append([InlineKeyboardButton(text="📩 Написать @shantrapaev", url=f"https://t.me/{config.CONTACT_USERNAME}")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить работу", callback_data="admin_add")],
        [InlineKeyboardButton(text="🔢 Порядок и список работ", callback_data="admin_list")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_work_order_keyboard(work_id: int, position: int, total: int) -> InlineKeyboardMarkup:
    rows = []
    # Up / Down buttons
    nav_row = []
    if position > 1:
        nav_row.append(InlineKeyboardButton(text="⬆️ Поднять на 1", callback_data=f"order_up:{work_id}"))
    if position < total:
        nav_row.append(InlineKeyboardButton(text="⬇️ Опустить на 1", callback_data=f"order_down:{work_id}"))
    if nav_row:
        rows.append(nav_row)

    # First / Last buttons
    extremes_row = []
    if position > 1:
        extremes_row.append(InlineKeyboardButton(text="🔝 Сделать 1-й", callback_data=f"order_top:{work_id}"))
    if position < total:
        extremes_row.append(InlineKeyboardButton(text="🔚 В самый конец", callback_data=f"order_bottom:{work_id}"))
    if extremes_row:
        rows.append(extremes_row)

    rows.append([
        InlineKeyboardButton(text="👁 Посмотреть в портфолио", callback_data=f"portfolio:{position - 1}")
    ])
    rows.append([
        InlineKeyboardButton(text="🗑 Удалить эту работу", callback_data=f"admin_del:{work_id}:0")
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад ко всем работам", callback_data="admin_list")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ])
