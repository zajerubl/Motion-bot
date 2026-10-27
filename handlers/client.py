import os
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

from config import config, is_admin
import database
from keyboards import (
    get_main_menu_keyboard,
    get_about_keyboard,
    get_contacts_keyboard,
    get_portfolio_keyboard,
    get_empty_portfolio_keyboard
)

router = Router()

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

MAIN_MENU_IMG = ASSETS_DIR / "main_menu.png"
ABOUT_IMG = ASSETS_DIR / "about.jpg"
CONTACTS_IMG = ASSETS_DIR / "contacts.png"

MAIN_TEXT = (
    "👋 <b>Привет! Я бот-портфолио 2D моушн-дизайнера.</b>\n\n"
    "Здесь собраны мои работы по анимации, эксплейнерам и динамической 2D-графике.\n\n"
    "👇 <b>Выбирай нужный раздел в меню ниже:</b>"
)

ABOUT_TEXT = (
    "👨‍💻 <b>Обо мне | 2D Motion Designer</b>\n\n"
    "Привет! Я создаю сочную и продуманную 2D-анимацию для брендов, бизнеса и продуктов.\n\n"
    "<b>Чем могу помочь:</b>\n"
    "• 🎬 Эксплейнеры и презентационные ролики\n"
    "• ⚡️ Анимация для соцсетей, сайтов и приложений\n"
    "• 🔤 Кинетическая типографика и динамичный моушен\n"
    "• 🎨 Оживление векторных иллюстраций и логотипов\n\n"
    "🛠 <b>Инструменты:</b>\n"
    "Adobe After Effects, Illustrator, Photoshop.\n\n"
    "Всегда открыт к крутым проектам и коммерческим заказам!"
)

CONTACTS_TEXT = (
    "📩 <b>Контакты & Сотрудничество</b>\n\n"
    "Готов обсудить твою задачу, рассчитать сроки и стоимость проекта или предложить идеи сценария.\n\n"
    f"💬 <b>Telegram:</b> @{config.CONTACT_USERNAME}\n"
    "⚡️ <i>На связи, отвечу максимально быстро!</i>"
)

async def clean_and_send_photo(call_or_msg, photo_path: Path, caption: str, reply_markup):
    bot = call_or_msg.bot
    chat_id = call_or_msg.chat.id if isinstance(call_or_msg, Message) else call_or_msg.message.chat.id
    msg_id = call_or_msg.message_id if isinstance(call_or_msg, Message) else call_or_msg.message.message_id
    
    # Try deleting old message to keep chat neat
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass
    
    if photo_path.exists():
        photo = FSInputFile(str(photo_path))
        return await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        return await bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    await database.add_user(user_id, username, first_name)
    user_is_admin = is_admin(message.from_user)
    
    await clean_and_send_photo(
        call_or_msg=message,
        photo_path=MAIN_MENU_IMG,
        caption=MAIN_TEXT,
        reply_markup=get_main_menu_keyboard(user_is_admin)
    )

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.answer()
    user_is_admin = is_admin(callback.from_user)
    await clean_and_send_photo(
        call_or_msg=callback,
        photo_path=MAIN_MENU_IMG,
        caption=MAIN_TEXT,
        reply_markup=get_main_menu_keyboard(user_is_admin)
    )

@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.answer()
    await clean_and_send_photo(
        call_or_msg=callback,
        photo_path=ABOUT_IMG,
        caption=ABOUT_TEXT,
        reply_markup=get_about_keyboard()
    )

@router.callback_query(F.data == "contacts")
async def cb_contacts(callback: CallbackQuery):
    await callback.answer()
    await clean_and_send_photo(
        call_or_msg=callback,
        photo_path=CONTACTS_IMG,
        caption=CONTACTS_TEXT,
        reply_markup=get_contacts_keyboard()
    )

@router.callback_query(F.data.startswith("portfolio:"))
async def cb_portfolio(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split(":")
    index = int(parts[1]) if len(parts) > 1 else 0
    
    total = await database.get_works_count()
    user_is_admin = is_admin(callback.from_user)
    
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    
    if total == 0:
        empty_text = (
            "🎬 <b>Портфолио наполняется</b>\n\n"
            "Здесь скоро появятся свежие видеоролики!\n\n"
            f"А пока ты можешь написать мне напрямую: @{config.CONTACT_USERNAME}"
        )
        await clean_and_send_photo(
            call_or_msg=callback,
            photo_path=MAIN_MENU_IMG,
            caption=empty_text,
            reply_markup=get_empty_portfolio_keyboard(user_is_admin)
        )
        return

    # Bound index
    if index < 0:
        index = total - 1
    elif index >= total:
        index = 0
        
    work = await database.get_work_by_index(index)
    if not work:
        return
    
    kb = get_portfolio_keyboard(
        current_index=index,
        total_count=total,
        work_id=work["id"],
        is_admin=user_is_admin
    )
    
    # Try deleting previous message
    try:
        await callback.bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass
    
    caption = work["caption"] or "🎬 <b>2D Motion Design</b>"
    
    if work["media_type"] == "document":
        await callback.bot.send_document(
            chat_id=chat_id,
            document=work["file_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await callback.bot.send_video(
            chat_id=chat_id,
            video=work["file_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb
        )

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
