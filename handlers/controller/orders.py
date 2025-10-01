# handlers/controller/applications.py
# Controller uchun "📋 Arizalarni ko'rish" — INLINE menyu va statistika.

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from filters.role_filter import RoleFilter

from database.controller_orders import (
    ctrl_total_tech_orders_count,
    ctrl_new_in_controller_count,
    ctrl_in_progress_count,
    ctrl_completed_today_count,
    ctrl_cancelled_count,
)

router = Router()
router.message.filter(RoleFilter("controller"))
router.callback_query.filter(RoleFilter("controller"))

# ---------- UI ----------
def _ctrl_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🆕 Yangi buyurtmalar", callback_data="ctrl:new")],
        [InlineKeyboardButton(text="⏳ Jarayondagilar", callback_data="ctrl:progress")],
        [InlineKeyboardButton(text="✅ Bugun bajarilgan", callback_data="ctrl:done_today")],
        [InlineKeyboardButton(text="❌ Bekor qilinganlar", callback_data="ctrl:cancelled")],
        [InlineKeyboardButton(text="♻️ Yangilash", callback_data="ctrl:refresh")],
        [InlineKeyboardButton(text="📑 Hisobot", callback_data="ctrl:report")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _card_text(total:int, new_cnt:int, in_prog:int, done_today:int, cancelled:int) -> str:
    return (
        "🗂 <b>Buyurtmalar nazorati</b>\n\n"
        "📊 <b>Statistika:</b>\n"
        f"• Jami: <b>{total}</b>\n"
        f"• Yangi: <b>{new_cnt}</b>\n"
        f"• Jarayonda: <b>{in_prog}</b>\n"
        f"• Bugun bajarilgan: <b>{done_today}</b>\n"
        f"• Bekor qilinganlar: <b>{cancelled}</b>\n\n"
        "Quyidagini tanlang:"
    )

async def _load_stats():
    total = await ctrl_total_tech_orders_count()
    new_cnt = await ctrl_new_in_controller_count()
    in_prog = await ctrl_in_progress_count()
    done_today = await ctrl_completed_today_count()
    cancelled = await ctrl_cancelled_count()
    return total, new_cnt, in_prog, done_today, cancelled

async def _safe_edit(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=kb)

# ---------- Kirish (reply tugmadan) ----------
@router.message(F.text.in_(["📋 Arizalarni ko'rish", "📋 Просмотр заявок"]))
async def orders_handler(message: Message, state: FSMContext):
    """
    Controller menyusidagi "📋 Arizalarni ko'rish" bosilganda — statistik kartochka va inline menyu.
    """
    total, new_cnt, in_prog, done_today, cancelled = await _load_stats()
    await message.answer(
        _card_text(total, new_cnt, in_prog, done_today, cancelled),
        reply_markup=_ctrl_menu_kb()
    )

# ---------- Tugmalar (hozircha placeholder) ----------
@router.callback_query(F.data == "ctrl:new")
async def ctrl_new(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await _safe_edit(
        call,
        "🆕 <b>Yangi buyurtmalar</b>\n\nRo'yxat keyin qo'shiladi.",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="ctrl:back")]])
    )

@router.callback_query(F.data == "ctrl:progress")
async def ctrl_progress(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await _safe_edit(
        call,
        "⏳ <b>Jarayondagilar</b>\n\nRo'yxat keyin qo'shiladi.",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="ctrl:back")]])
    )

@router.callback_query(F.data == "ctrl:done_today")
async def ctrl_done_today(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await _safe_edit(
        call,
        "✅ <b>Bugun bajarilgan</b>\n\nRo'yxat keyin qo'shiladi.",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="ctrl:back")]])
    )

@router.callback_query(F.data == "ctrl:cancelled")
async def ctrl_cancelled(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await _safe_edit(
        call,
        "❌ <b>Bekor qilinganlar</b>\n\nRo'yxat keyin qo'shiladi.",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="ctrl:back")]])
    )

@router.callback_query(F.data == "ctrl:refresh")
async def ctrl_refresh(call: CallbackQuery, state: FSMContext):
    await call.answer("Yangilanmoqda…")
    total, new_cnt, in_prog, done_today, cancelled = await _load_stats()
    await _safe_edit(call, _card_text(total, new_cnt, in_prog, done_today, cancelled),
                     _ctrl_menu_kb())

@router.callback_query(F.data.in_(["ctrl:back", "ctrl:report"]))
async def ctrl_back_or_report(call: CallbackQuery, state: FSMContext):
    """
    Orqaga/Hisobot — hozircha asosiy kartochkani qayta ko'rsatamiz.
    """
    await call.answer()
    total, new_cnt, in_prog, done_today, cancelled = await _load_stats()
    await _safe_edit(call, _card_text(total, new_cnt, in_prog, done_today, cancelled),
                     _ctrl_menu_kb())
