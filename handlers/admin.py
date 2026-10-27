from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config, is_admin
import database
from keyboards import (
    get_admin_keyboard,
    get_cancel_keyboard,
    get_portfolio_keyboard,
    get_empty_portfolio_keyboard,
    get_work_order_keyboard
)

router = Router()

class AddWorkState(StatesGroup):
    waiting_for_media = State()
    waiting_for_caption = State()

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user):
        await callback.answer("⛔️ У вас нет доступа к этому разделу.", show_alert=True)
        return

    await callback.answer()
    users_cnt = await database.get_users_count()
    works_cnt = await database.get_works_count()

    text = (
        "👑 <b>Панель управления портфолио</b>\n\n"
        f"📊 <b>Пользователей открывали бота:</b> {users_cnt}\n"
        f"🎬 <b>Работ в портфолио:</b> {works_cnt}\n\n"
        "Выбери действие:"
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_cancel")
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Действие отменено.")
    await cb_admin_panel(callback, state)

@router.callback_query(F.data == "admin_add")
async def cb_admin_add(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user):
        return

    await callback.answer()
    await state.set_state(AddWorkState.waiting_for_media)

    text = (
        "🎬 <b>Шаг 1 из 2: Отправка видео</b>\n\n"
        "Пришли видеофайл роликом или документом (.mp4 / .mov).\n\n"
        "💡 <i>Подсказка: если прикрепить текст прямо к видео при отправке, "
        "он автоматически станет описанием работы!</i>"
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AddWorkState.waiting_for_media, F.video | F.document)
async def process_media_upload(message: Message, state: FSMContext):
    if not is_admin(message.from_user):
        return

    if message.video:
        file_id = message.video.file_id
        media_type = "video"
    else:
        file_id = message.document.file_id
        media_type = "document"

    # Check if caption was sent with the video
    if message.caption:
        caption = message.html_text
        work_id = await database.add_work(file_id, media_type, caption)
        total = await database.get_works_count()
        await state.clear()
        
        await message.answer(
            f"✅ <b>Работа #{work_id} успешно добавлена в портфолио!</b>\n\n"
            f"Всего работ: <b>{total}</b>. Она сразу доступна клиентам со стрелками переключения.",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
        return

    # If no caption attached, ask for it
    await state.update_data(file_id=file_id, media_type=media_type)
    await state.set_state(AddWorkState.waiting_for_caption)

    text = (
        "✍️ <b>Шаг 2 из 2: Описание к ролику</b>\n\n"
        "Отправь текст описания. Ты можешь использовать стандартную разметку Telegram "
        "(жирный, курсив, ссылки).\n\n"
        "<i>Если описание не нужно, отправь «-» или напиши «Пропустить».</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())

@router.message(AddWorkState.waiting_for_caption, F.text)
async def process_caption_upload(message: Message, state: FSMContext):
    if not is_admin(message.from_user):
        return

    data = await state.get_data()
    file_id = data.get("file_id")
    media_type = data.get("media_type")

    text = message.text.strip().lower()
    if text in ["-", "пропустить", "нет", "skip"]:
        caption = ""
    else:
        caption = message.html_text

    work_id = await database.add_work(file_id, media_type, caption)
    total = await database.get_works_count()
    await state.clear()

    await message.answer(
        f"✅ <b>Работа #{work_id} успешно добавлена в портфолио!</b>\n\n"
        f"Всего работ: <b>{total}</b>. Она сразу доступна клиентам со стрелками переключения.",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data == "admin_list")
async def cb_admin_list(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        return

    await callback.answer()
    works = await database.get_all_works()
    if not works:
        await callback.message.answer(
            "В портфолио пока нет добавленных работ.",
            reply_markup=get_admin_keyboard()
        )
        return

    buttons = []
    for i, w in enumerate(works, start=1):
        cap = (w["caption"] or "Без описания").replace("\n", " ").strip()
        if len(cap) > 28:
            cap = cap[:28] + "..."
        buttons.append([
            InlineKeyboardButton(
                text=f"№{i} • {cap}",
                callback_data=f"admin_order_work:{w['id']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="➕ Добавить ещё работу", callback_data="admin_add")])
    buttons.append([InlineKeyboardButton(text="🏠 В панель управления", callback_data="admin_panel")])

    text = (
        "🔢 <b>Управление списком и порядком работ:</b>\n\n"
        "Нажми на любую работу, чтобы переместить её на 1-е место, "
        "поднять выше/опустить ниже или удалить 👇"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("admin_order_work:"))
async def cb_admin_order_work(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        return

    await callback.answer()
    work_id = int(callback.data.split(":")[1])
    work = await database.get_work_by_id(work_id)
    if not work:
        await callback.answer("Работа не найдена.", show_alert=True)
        return

    works = await database.get_all_works()
    pos = next((i + 1 for i, w in enumerate(works) if w["id"] == work_id), 1)
    total = len(works)

    caption = work["caption"] or "<i>(без описания)</i>"
    text = (
        f"🎬 <b>Настройка работы ID #{work_id}</b>\n\n"
        f"📍 Текущее место в портфолио: <b>№ {pos} из {total}</b>\n"
        f"📝 <b>Описание:</b>\n{caption}\n\n"
        "Куда переместить эту работу?"
    )
    kb = get_work_order_keyboard(work_id=work_id, position=pos, total=total)

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("order_up:"))
async def cb_order_up(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        return
    work_id = int(callback.data.split(":")[1])
    await database.move_work_up(work_id)
    await callback.answer("⬆️ Перемещено выше!")
    callback.data = f"admin_order_work:{work_id}"
    await cb_admin_order_work(callback)

@router.callback_query(F.data.startswith("order_down:"))
async def cb_order_down(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        return
    work_id = int(callback.data.split(":")[1])
    await database.move_work_down(work_id)
    await callback.answer("⬇️ Перемещено ниже!")
    callback.data = f"admin_order_work:{work_id}"
    await cb_admin_order_work(callback)

@router.callback_query(F.data.startswith("order_top:"))
async def cb_order_top(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        return
    work_id = int(callback.data.split(":")[1])
    await database.move_work_to_top(work_id)
    await callback.answer("🔝 Теперь это работа № 1!")
    callback.data = f"admin_order_work:{work_id}"
    await cb_admin_order_work(callback)

@router.callback_query(F.data.startswith("order_bottom:"))
async def cb_order_bottom(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        return
    work_id = int(callback.data.split(":")[1])
    await database.move_work_to_bottom(work_id)
    await callback.answer("🔚 Перемещено в самый конец!")
    callback.data = f"admin_order_work:{work_id}"
    await cb_admin_order_work(callback)

@router.callback_query(F.data.startswith("admin_del:"))
async def cb_admin_del(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        return

    parts = callback.data.split(":")
    work_id = int(parts[1])
    current_index = int(parts[2]) if len(parts) > 2 else 0

    deleted = await database.delete_work(work_id)
    if deleted:
        await callback.answer("🗑 Работа успешно удалена!", show_alert=True)
    else:
        await callback.answer("Ошибка: работа не найдена.", show_alert=True)

    # Redirect to updated portfolio index or list
    total = await database.get_works_count()
    if total == 0:
        callback.data = "portfolio:0"
        from handlers.client import cb_portfolio
        await cb_portfolio(callback)
    else:
        new_index = max(0, min(current_index, total - 1))
        callback.data = f"portfolio:{new_index}"
        from handlers.client import cb_portfolio
        await cb_portfolio(callback)
