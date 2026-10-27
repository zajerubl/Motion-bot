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
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"portfolio:{prev_idx}"),
            InlineKeyboardButton(text=f"📍 {current_index + 1} / {total_count}", callback_data="noop"),
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"portfolio:{next_idx}")
        ])
    
    rows.append([
        InlineKeyboardButton(text="📩 Заказать подобный ролик", url=f"https://t.me/{config.CONTACT_USERNAME}")
    ])
    
    if is_admin:
        rows.append([
            InlineKeyboardButton(text="🗑 Удалить эту работу", callback_data=f"admin_del:{work_id}:{current_index}")
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
        [InlineKeyboardButton(text="📋 Список работ", callback_data="admin_list")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ])
