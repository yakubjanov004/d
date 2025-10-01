# handlers/warehouse_statistics.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, timedelta
import html

from keyboards.warehouse_buttons import (
    get_warehouse_statistics_keyboard,
    get_stats_period_keyboard,
    get_warehouse_main_menu
)
from database.warehouse_queries import (
    get_warehouse_statistics,
    get_warehouse_daily_statistics,
    get_warehouse_weekly_statistics,
    get_warehouse_monthly_statistics,
    get_warehouse_yearly_statistics,
    get_low_stock_materials,
    get_warehouse_financial_report,
    get_warehouse_range_statistics,
)
from filters.role_filter import RoleFilter

router = Router()
router.message.filter(RoleFilter("warehouse"))
router.callback_query.filter(RoleFilter("warehouse"))

# --- State: vaqt oralig'i oynasi uchun
class StatsStates(StatesGroup):
    waiting_range = State()

# --- Helperlar
def format_number(num):
    try:
        n = float(num or 0)
    except Exception:
        return str(num)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{int(n):,}".replace(",", " ")

def format_currency(amount):
    try:
        a = float(amount or 0)
    except Exception:
        a = 0
    return f"{a:,.0f} so'm".replace(",", " ")


# =============================================
# Asosiy Statistika menyusi
# =============================================
@router.message(F.text.in_(["📊 Statistikalar", "📊 Статистика"]))
async def statistics_main_handler(message: Message):
    lang = "uz"
    try:
        stats = await get_warehouse_statistics()
        text = (
            "📊 <b>Ombor Statistikasi</b>\n\n"
            "📦 <b>Umumiy ma'lumotlar:</b>\n"
            f"• Jami mahsulotlar: <b>{stats['total_materials']}</b> ta\n"
            f"• Umumiy zaxira: <b>{format_number(stats['total_quantity'])}</b> dona\n"
            f"• Umumiy qiymat: <b>{format_currency(stats['total_value'])}</b>\n\n"
            "⚠️ <b>Diqqat talab qiladi:</b>\n"
            f"• Kam zaxira: <b>{stats['low_stock_count']}</b> ta mahsulot\n"
            f"• Tugagan: <b>{stats['out_of_stock_count']}</b> ta mahsulot\n\n"
            "👇 Batafsil statistika uchun tugmalardan foydalaning:"
        )
        await message.answer(
            text,
            reply_markup=get_warehouse_statistics_keyboard(lang),
            parse_mode="HTML"
        )
    except Exception:
        await message.answer(
            "❌ Statistika yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=get_warehouse_main_menu(lang)
        )


# =============================================
# Inventarizatsiya statistikasi
# =============================================
@router.message(F.text.in_(["📊 Inventarizatsiya statistikasi", "📊 Статистика инвентаризации"]))
async def inventory_statistics_handler(message: Message):
    try:
        stats = await get_warehouse_statistics()
        daily_stats = await get_warehouse_daily_statistics()
        text = (
            "📊 <b>Inventarizatsiya Statistikasi</b>\n\n"
            "📦 <b>Mahsulotlar taqsimoti:</b>\n"
            f"• Jami mahsulot turlari: <b>{stats['total_materials']}</b>\n"
            f"• Jami dona: <b>{format_number(stats['total_quantity'])}</b>\n"
            f"• O'rtacha zaxira: <b>{stats['total_quantity'] // max(stats['total_materials'], 1)}</b> dona/tur\n\n"
            "📅 <b>Bugungi faollik:</b>\n"
            f"• Qo'shilgan: <b>{daily_stats['daily_added']}</b> ta\n"
            f"• Yangilangan: <b>{daily_stats['daily_updated']}</b> ta\n\n"
            "⚠️ <b>Ehtiyot bo'lish kerak:</b>\n"
            f"• Kam zaxira (≤10): <b>{stats['low_stock_count']}</b> ta\n"
            f"• Tugagan (0): <b>{stats['out_of_stock_count']}</b> ta\n\n"
            "💰 <b>Qiymat taqsimoti:</b>\n"
            f"• Umumiy qiymat: <b>{format_currency(stats['total_value'])}</b>\n"
            f"• O'rtacha qiymat: <b>{format_currency(stats['total_value'] / max(stats['total_materials'], 1))}</b>/tur"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception:
        await message.answer("❌ Inventarizatsiya statistikasini yuklashda xatolik yuz berdi.")


# =============================================
# 📦 Buyurtmalar statistikasi (haftalik jamlama)
# =============================================
@router.message(F.text.in_(["📦 Buyurtmalar statistikasi", "📦 Статистика заказов"]))
async def orders_stats(message: Message):
    try:
        week = await get_warehouse_weekly_statistics()
        text = (
            "📦 <b>Buyurtmalar statistikasi (hafta):</b>\n\n"
            f"📥 Qo'shilgan mahsulotlar: <b>{week['weekly_added']}</b>\n"
            f"✏️ Yangilangan mahsulotlar: <b>{week['weekly_updated']}</b>\n"
            f"💰 Umumiy qiymat: <b>{format_currency(week['weekly_value'])}</b>"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception:
        await message.answer("❌ Buyurtmalar statistikasini yuklashda xatolik yuz berdi.")


# =============================================
# ⚠️ Kam zaxira statistikasi
# =============================================
@router.message(F.text.in_(["⚠️ Kam zaxira statistikasi", "⚠️ Статистика низких запасов"]))
async def low_stock_stats(message: Message):
    try:
        lows = await get_low_stock_materials(10)
        if not lows:
            return await message.answer("✅ Kam zaxira yo‘q.", parse_mode="HTML")
        lines = []
        for i, m in enumerate(lows[:10], 1):
            lines.append(f"{i}. <b>{html.escape(m['name'])}</b> — {m['quantity']} dona (min: 10)")
        await message.answer("⚠️ <b>Kam zaxira statistikasi:</b>\n\n" + "\n".join(lines), parse_mode="HTML")
    except Exception:
        await message.answer("❌ Kam zaxira statistikasi yuklashda xatolik yuz berdi.")


# =============================================
# 💰 Moliyaviy hisobot (oy)
# =============================================
@router.message(F.text.in_(["💰 Moliyaviy hisobot", "💰 Финансовый отчет"]))
async def financial_report_handler(message: Message):
    try:
        rep = await get_warehouse_financial_report()
        text = (
            "💰 <b>Moliyaviy hisobot (oy):</b>\n\n"
            f"🏬 Omborga kiritilgan mahsulotlar: <b>{format_number(rep['in_count'])}</b> dona\n"
            f"📦 Ombordan chiqarilgan mahsulotlar: <b>{format_number(rep['out_count'])}</b> dona\n"
            f"💵 Umumiy qiymat: <b>{format_currency(rep['total_value_month'])}</b>\n"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception:
        await message.answer("❌ Moliyaviy hisobotni yuklashda xatolik yuz berdi.")


# =============================================
# 📊 Vaqt oralig'idagi statistika — STATE bilan
# =============================================
@router.message(F.text.in_(["📊 Vaqt oralig'idagi statistika", "📊 Статистика за период"]))
async def range_stats_start(message: Message, state: FSMContext):
    await state.set_state(StatsStates.waiting_range)
    await message.answer(
        "Qaysi davr uchun statistikani ko‘rmoqchisiz?\n"
        "Format: <code>YYYY-MM-DD YYYY-MM-DD</code> (boshlanish va tugash sanasi).",
        parse_mode="HTML",
        reply_markup=get_stats_period_keyboard("uz"),
    )

@router.message(
    StateFilter(StatsStates.waiting_range),
    F.text.in_(["🔙 Orqaga", "◀️ Orqaga", "🔙 Назад", "◀️ Назад"])
)
async def range_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=get_warehouse_main_menu("uz"))

@router.message(StateFilter(StatsStates.waiting_range))
async def range_stats_capture(message: Message, state: FSMContext):
    """
    State ichidamiz:
    - Oylik/Kunlik/Haftalik/Yillik tugmalari qayta-qayta ishlaydi (state saqlanadi)
    - Agar foydalanuvchi boshqa bo‘lim tugmalarini bossachi? -> state tozalanadi va o‘sha bo‘lim ishga tushadi
    - Qo‘lda interval kiritilsa, natija ko‘rsatiladi, state saqlanadi (istasa yana davr kiritishi mumkin)
    """
    txt = (message.text or "").strip()
    low = txt.lower()

    # ---- Agar boshqa bo‘lim tugmalari bosilgan bo‘lsa: state -> clear va tegishli bo‘limga o'tkazamiz
    if low in ("📦 buyurtmalar statistikasi".lower(), "📦 статистика заказов".lower()):
        await state.clear()
        return await orders_stats(message)

    if low in ("⚠️ kam zaxira statistikasi".lower(), "⚠️ статистика низких запасов".lower()):
        await state.clear()
        return await low_stock_stats(message)

    if low in ("💰 moliyaviy hisobot".lower(), "💰 финансовый отчет".lower()):
        await state.clear()
        return await financial_report_handler(message)

    if low in ("📊 inventarizatsiya statistikasi".lower(), "📊 статистика инвентаризации".lower()):
        await state.clear()
        return await inventory_statistics_handler(message)

    if low in ("📊 statistikalar".lower(), "📊 статистика".lower()):
        await state.clear()
        return await statistics_main_handler(message)

    # ---- Tez tugmalar (state saqlanadi: foydalanuvchi yana tanlay oladi)
    if "kunlik statistika" in low:
        data = await get_warehouse_daily_statistics()
        return await message.answer(
            f"📊 <b>Kunlik statistika</b>\n"
            f"• Qo‘shilgan: <b>{data['daily_added']}</b>\n"
            f"• Yangilangan: <b>{data['daily_updated']}</b>",
            parse_mode="HTML",
        )

    if "haftalik statistika" in low:
        ws = await get_warehouse_weekly_statistics()
        return await message.answer(
            f"📅 <b>Haftalik statistika</b>\n"
            f"• Qo‘shilgan: <b>{ws['weekly_added']}</b>\n"
            f"• Yangilangan: <b>{ws['weekly_updated']}</b>\n"
            f"• Qiymat: <b>{format_currency(ws['weekly_value'])}</b>",
            parse_mode="HTML",
        )

    if "oylik statistika" in low:
        ms = await get_warehouse_monthly_statistics()
        return await message.answer(
            f"🗓️ <b>Oylik statistika</b>\n"
            f"• Qo‘shilgan: <b>{ms['monthly_added']}</b>\n"
            f"• Yangilangan: <b>{ms['monthly_updated']}</b>\n"
            f"• Qiymat: <b>{format_currency(ms['monthly_value'])}</b>",
            parse_mode="HTML",
        )

    if "yillik statistika" in low:
        ys = await get_warehouse_yearly_statistics()
        return await message.answer(
            f"📈 <b>Yillik statistika</b>\n"
            f"• Qo‘shilgan: <b>{ys['yearly_added']}</b>\n"
            f"• Yangilangan: <b>{ys['yearly_updated']}</b>\n"
            f"• Qiymat: <b>{format_currency(ys['yearly_value'])}</b>",
            parse_mode="HTML",
        )

    # ---- Qo‘lda kiritilgan interval: "YYYY-MM-DD YYYY-MM-DD"
    try:
        a, b = txt.split()
        start = datetime.strptime(a, "%Y-%m-%d").date()
        end = datetime.strptime(b, "%Y-%m-%d").date()
        if end < start:
            start, end = end, start
    except Exception:
        return await message.answer(
            "❗ Format xato. Masalan: <code>2025-09-01 2025-09-30</code>",
            parse_mode="HTML",
        )

    rng = await get_warehouse_range_statistics(str(start), str(end))
    await message.answer(
        f"📊 <b>Statistika ({start} — {end})</b>\n"
        f"• Qo‘shilgan: <b>{rng['added']}</b>\n"
        f"• Yangilangan: <b>{rng['updated']}</b>\n"
        f"• Qiymat: <b>{format_currency(rng['value'])}</b>",
        parse_mode="HTML",
    )
    # state NI SAQLAYMIZ — foydalanuvchi yana davr kiritishi yoki tez tugmalardan birini bosishi mumkin


# =============================================
# Orqaga (umumiy)
# =============================================
@router.message(F.text.in_(["◀️ Orqaga", "◀️ Назад", "🔙 Orqaga", "🔙 Назад"]))
async def back_to_main_handler(message: Message):
    lang = "uz"
    await message.answer("🏠 Asosiy menyu", reply_markup=get_warehouse_main_menu(lang))


# =============================================
# Inline callbacklar (avvalgi kabi)
# =============================================
@router.callback_query(F.data == "warehouse_stats_daily")
async def daily_stats_callback(callback: CallbackQuery):
    await callback.answer()
    try:
        daily_stats = await get_warehouse_daily_statistics()
        text = (
            "📊 <b>Bugungi Statistika</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
            "📦 <b>Bugungi faollik:</b>\n"
            f"• Qo'shilgan mahsulotlar: <b>{daily_stats['daily_added']}</b> ta\n"
            f"• Yangilangan mahsulotlar: <b>{daily_stats['daily_updated']}</b> ta\n\n"
            "⏰ <b>Vaqt bo'yicha taqsimot:</b>\n"
            "• Ertalab (06:00-12:00): <b>Hisoblanmoqda...</b>\n"
            "• Kunduzi (12:00-18:00): <b>Hisoblanmoqda...</b>\n"
            "• Kechqurun (18:00-00:00): <b>Hisoblanmoqda...</b>\n\n"
            "🎯 <b>Bugungi maqsad:</b>\n"
            "• Rejalashtirgan: <b>10</b> ta mahsulot\n"
            f"• Bajarildi: <b>{daily_stats['daily_added']}</b> ta\n"
            f"• Foiz: <b>{min(100, (daily_stats['daily_added'] * 100) // 10)}%</b>"
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_warehouse_statistics_keyboard("uz"),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer("❌ Kunlik statistikani yuklashda xatolik yuz berdi.")

@router.callback_query(F.data == "warehouse_stats_refresh")
async def refresh_stats_callback(callback: CallbackQuery):
    await callback.answer("🔄 Statistika yangilanmoqda...")
    await statistics_main_handler(callback.message)
