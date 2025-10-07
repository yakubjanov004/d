from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from filters.role_filter import RoleFilter
from database.call_center_supervisor.statistics import (
    get_active_connection_tasks_count,
    get_callcenter_operator_count,
    get_canceled_connection_tasks_count,
)
from database.basic.language import get_user_language

router = Router()
router.message.filter(RoleFilter("callcenter_supervisor"))
router.callback_query.filter(RoleFilter("callcenter_supervisor"))

# --- UI ---
async def _menu_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    lang = await get_user_language(telegram_id) or "uz"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="♻️ Yangilash" if lang == "uz" else "♻️ Обновить",
                callback_data="stats:refresh"
            )]
        ]
    )

async def _card_text(active_tasks: int, co_count: int, canceled_tasks: int, telegram_id: int) -> str:
    lang = await get_user_language(telegram_id) or "uz"
    if lang == "uz":
        return (
            "📊 Statistikalar\n\n"
            f"🧾 Aktiv arizalar: {active_tasks}\n"
            f"🧑‍💼 Umumiy xodimlar: {co_count}\n"
            f"❌ Bekor qilingan arizalar: {canceled_tasks}\n"
        )
    else:
        return (
            "📊 Статистика\n\n"
            f"🧾 Активные заявки: {active_tasks}\n"
            f"🧑‍💼 Всего сотрудников: {co_count}\n"
            f"❌ Отмененные заявки: {canceled_tasks}\n"
        )

# --- Asosiy handler ---
@router.message(F.text.in_(["📊 Statistikalar", "📊 Статистика"]))
async def statistics_entry(message: Message, state: FSMContext):
    active_tasks = await get_active_connection_tasks_count()
    co_count = await get_callcenter_operator_count()
    canceled_tasks = await get_canceled_connection_tasks_count()

    await message.answer(
        await _card_text(active_tasks, co_count, canceled_tasks, message.from_user.id),
        reply_markup=await _menu_keyboard(message.from_user.id)
    )

# --- Callback yangilash ---
@router.callback_query(F.data == "stats:refresh")
async def stats_refresh(call: CallbackQuery, state: FSMContext):
    lang = await get_user_language(call.from_user.id) or "uz"
    await call.answer("Yangilanmoqda…" if lang == "uz" else "Обновляется…")

    active_tasks = await get_active_connection_tasks_count()
    co_count = await get_callcenter_operator_count()
    canceled_tasks = await get_canceled_connection_tasks_count()

    try:
        await call.message.edit_text(
            await _card_text(active_tasks, co_count, canceled_tasks, call.from_user.id),
            reply_markup=await _menu_keyboard(call.from_user.id)
        )
    except TelegramBadRequest:
        await call.message.answer(
            await _card_text(active_tasks, co_count, canceled_tasks, call.from_user.id),
            reply_markup=await _menu_keyboard(call.from_user.id)
        )
