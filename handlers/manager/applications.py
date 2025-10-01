# handlers/manager/applications.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
import html
from datetime import datetime
from typing import Optional, List, Dict, Any

from filters.role_filter import RoleFilter
from database.manager_inbox import get_user_by_telegram_id

from database.manager_application import (
    get_total_orders_count,
    get_in_progress_count,
    get_completed_today_count,
    get_cancelled_count,
    get_new_orders_today_count,
    list_new_orders,
    list_in_progress_orders,
    list_completed_today_orders,
    list_cancelled_orders,
    # 🆕 yangi import:
    list_my_created_orders_by_type,
)

router = Router()
router.message.filter(RoleFilter("manager"))
router.callback_query.filter(RoleFilter("manager"))

T = {
    # Titles
    "title_panel":    {"uz": "🗂 <b>Buyurtmalar nazorati</b>", "ru": "🗂 <b>Контроль заявок</b>"},
    "title_choose":   {"uz": "Quyidagini tanlang:",             "ru": "Выберите категорию:"},
    "title_new":      {"uz": "🆕 <b>Yangi buyurtmalar</b>",     "ru": "🆕 <b>Новые заявки</b>"},
    "title_progress": {"uz": "⏳ <b>Jarayondagilar</b>",         "ru": "⏳ <b>В процессе</b>"},
    "title_done":     {"uz": "✅ <b>Bugun bajarilgan</b>",       "ru": "✅ <b>Выполнено сегодня</b>"},
    "title_cancel":   {"uz": "🚫 <b>Bekor qilinganlar</b>",      "ru": "🚫 <b>Отменённые</b>"},
    "title_fallback": {"uz": "🗂 <b>Buyurtmalar</b>",            "ru": "🗂 <b>Заявки</b>"},
    # 🆕 My created titles
    "title_my":       {"uz": "👤 <b>Men yaratgan arizalar</b>", "ru": "👤 <b>Мои заявки</b>"},
    "title_my_choose":{"uz": "Ariza turini tanlang:",           "ru": "Выберите тип заявки:"},
    "title_my_conn":  {"uz": "🔌 <b>Ulanish arizalari</b>",      "ru": "🔌 <b>Заявки на подключение</b>"},
    "title_my_tech":  {"uz": "🛠️ <b>Texnik arizalar</b>",       "ru": "🛠️ <b>Технические заявки</b>"},

    # Stats
    "stats":          {"uz": "📊 <b>Statistika:</b>",           "ru": "📊 <b>Статистика:</b>"},
    "total":          {"uz": "• Jami:",                         "ru": "• Всего:"},
    "new":            {"uz": "• Yangi:",                        "ru": "• Новые:"},
    "in_progress":    {"uz": "• Jarayonda:",                    "ru": "• В процессе:"},
    "done_today":     {"uz": "• Bugun bajarilgan:",             "ru": "• Выполнено сегодня:"},
    "cancelled":      {"uz": "• Bekor qilinganlar:",            "ru": "• Отменённые:"},

    # Buttons (menu)
    "btn_new":        {"uz": "🆕 Yangi buyurtmalar",             "ru": "🆕 Новые заявки"},
    "btn_progress":   {"uz": "⏳ Jarayondagilar",                 "ru": "⏳ В процессе"},
    "btn_done":       {"uz": "✅ Bugun bajarilgan",              "ru": "✅ Выполнено сегодня"},
    "btn_cancel":     {"uz": "🚫 Bekor qilinganlar",             "ru": "🚫 Отменённые"},
    "btn_refresh":    {"uz": "♻️ Yangilash",                    "ru": "♻️ Обновить"},
    "btn_close":      {"uz": "❌ Yopish",                        "ru": "❌ Закрыть"},
    "btn_back":       {"uz": "🔙 Orqaga",                        "ru": "🔙 Назад"},
    "btn_prev":       {"uz": "⬅️ Oldingi",                       "ru": "⬅️ Назад"},
    "btn_next":       {"uz": "Keyingi ➡️",                       "ru": "Вперёд ➡️"},
    # 🆕 My created (menu)
    "btn_my":         {"uz": "👤 Men yaratgan arizalar",         "ru": "👤 Мои заявки"},
    "btn_my_conn":    {"uz": "🔌 Ulanish arizalari",             "ru": "🔌 Заявки на подключение"},
    "btn_my_tech":    {"uz": "🛠️ Texnik arizalar",              "ru": "🛠️ Технические заявки"},

    # Labels in item card
    "card_title":     {"uz": "🗂 <b>Buyurtma</b>",               "ru": "🗂 <b>Заявка</b>"},
    "id":             {"uz": "🆔 <b>ID:</b>",                    "ru": "🆔 <b>ID:</b>"},
    "tariff":         {"uz": "📊 <b>Tarif:</b>",                 "ru": "📊 <b>Тариф:</b>"},
    "client":         {"uz": "👤 <b>Mijoz:</b>",                 "ru": "👤 <b>Клиент:</b>"},
    "phone":          {"uz": "📞 <b>Telefon:</b>",               "ru": "📞 <b>Телефон:</b>"},
    "address":        {"uz": "📍 <b>Manzil:</b>",                "ru": "📍 <b>Адрес:</b>"},
    "status":         {"uz": "🛈 <b>Status:</b>",                "ru": "🛈 <b>Статус:</b>"},
    "created":        {"uz": "🗓 <b>Yaratilgan:</b>",            "ru": "🗓 <b>Создано:</b>"},
    "updated":        {"uz": "🗓 <b>Yangilangan:</b>",           "ru": "🗓 <b>Обновлено:</b>"},
    "item_idx":       {"uz": "📄 <b>Ariza:</b>",                 "ru": "📄 <b>Заявка:</b>"},

    # Misc
    "closed":         {"uz": "Yopildi",                          "ru": "Закрыто"},
    "updating":       {"uz": "Yangilanmoqda…",                   "ru": "Обновляем…"},
    "updated_short":  {"uz": "Yangilandi ✅",                    "ru": "Обновлено ✅"},
    "not_found":      {"uz": "— Hech narsa topilmadi.",          "ru": "— Ничего не найдено."},
}

def normalize_lang(v: str | None) -> str:
    if not v:
        return "uz"
    s = v.strip().lower()
    if s in {"ru", "rus", "ru-ru", "ru_ru", "russian"}:
        return "ru"
    if s in {"uz", "uzb", "uz-uz", "uz_uz", "uzbek", "o'z", "oz"}:
        return "uz"
    return "uz"

def t(lang: str, key: str) -> str:
    lang = normalize_lang(lang)
    return T.get(key, {}).get(lang, T.get(key, {}).get("uz", key))

STATUS_T = {
    "new":               {"uz": "Yangi",             "ru": "Новая"},
    "in_progress":       {"uz": "Jarayonda",         "ru": "В процессе"},
    "done":              {"uz": "Bajarilgan",        "ru": "Выполнена"},
    "completed":         {"uz": "Bajarilgan",        "ru": "Выполнена"},
    "done_today":        {"uz": "Bugun bajarilgan",  "ru": "Выполнено сегодня"},
    "cancelled":         {"uz": "Bekor qilingan",    "ru": "Отменена"},
    "in_manager":        {"uz": "Managerda",         "ru": "У менеджера"},
    "in_junior_manager": {"uz": "Kichik menejerda",  "ru": "У младшего менеджера"},
}
def t_status(lang: str, status: str | None) -> str:
    key = (status or "").strip().lower()
    if key in STATUS_T:
        return STATUS_T[key].get(normalize_lang(lang), key)
    return status or "-"

def _esc(x: str | None) -> str:
    return html.escape(x or "-", quote=False)

def _fmt_dt(dt) -> str:
    try:
        if isinstance(dt, str):
            return dt
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt) if dt else "-"

# ---------- UI helpers ----------

def _apps_menu_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t(lang, "btn_new"),      callback_data="apps:new")],
        [InlineKeyboardButton(text=t(lang, "btn_progress"), callback_data="apps:progress")],
        [InlineKeyboardButton(text=t(lang, "btn_done"),     callback_data="apps:done_today")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"),   callback_data="apps:cancelled")],
        # 🆕 "Men yaratgan arizalar"
        [InlineKeyboardButton(text=t(lang, "btn_my"),       callback_data="apps:my_created")],
        [InlineKeyboardButton(text=t(lang, "btn_refresh"),  callback_data="apps:refresh")],
        [InlineKeyboardButton(text=t(lang, "btn_close"),    callback_data="apps:close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _my_created_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_my_conn"), callback_data="apps:my_type:connection")],
            [InlineKeyboardButton(text=t(lang, "btn_my_tech"), callback_data="apps:my_type:technician")],
            [InlineKeyboardButton(text=t(lang, "btn_back"),    callback_data="apps:back")],
        ]
    )

def _back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="apps:back")]]
    )

def _list_nav_kb(index: int, total_loaded: int, lang: str) -> InlineKeyboardMarkup:
    rows = []
    row = []
    if index > 0:
        row.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data="apps:nav:prev"))
    if index < total_loaded - 1:
        row.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data="apps:nav:next"))
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="apps:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _card_text(lang: str, total: int, new_today: int, in_progress: int, done_today: int, cancelled: int) -> str:
    return (
        f"{t(lang, 'title_panel')}\n\n"
        f"{t(lang, 'stats')}\n"
        f"{t(lang, 'total')} <b>{total}</b>\n"
        f"{t(lang, 'new')} <b>{new_today}</b>\n"
        f"{t(lang, 'in_progress')} <b>{in_progress}</b>\n"
        f"{t(lang, 'done_today')} <b>{done_today}</b>\n"
        f"{t(lang, 'cancelled')} <b>{cancelled}</b>\n\n"
        f"{t(lang, 'title_choose')}"
    )

def _item_card(lang: str, item: dict, index: int, total: int) -> str:
    full_id     = _esc(str(item.get("id", "-")))
    client_name = _esc(item.get("client_name"))
    client_phone= _esc(item.get("client_phone"))
    address     = _esc(item.get("address"))
    tariff      = _esc(item.get("tariff"))
    status_raw  = item.get("status")
    status_txt  = _esc(t_status(lang, status_raw))
    created_at  = _fmt_dt(item.get("created_at"))
    updated_at  = _fmt_dt(item.get("updated_at"))

    return (
        f"{t(lang,'card_title')}\n\n"
        f"{t(lang,'id')} {full_id}\n"
        f"{t(lang,'tariff')} {tariff}\n"
        f"{t(lang,'client')} {client_name}\n"
        f"{t(lang,'phone')} {client_phone}\n"
        f"{t(lang,'address')} {address}\n"
        f"{t(lang,'status')} {status_txt}\n"
        f"{t(lang,'created')} {created_at}\n"
        f"{t(lang,'updated')} {updated_at}\n"
        f"{t(lang,'item_idx')} {index + 1}/{total}"
    )

async def _load_stats():
    total      = await get_total_orders_count()
    new_today  = await get_new_orders_today_count()
    in_prog    = await get_in_progress_count()
    done_today = await get_completed_today_count()
    cancelled  = await get_cancelled_count()
    return total, new_today, in_prog, done_today, cancelled

async def _safe_edit(call: CallbackQuery, lang: str, text: str, kb: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "not modified" in str(e).lower():
            await call.answer(t(lang, "updated_short"), show_alert=False)
        else:
            try:
                await call.message.edit_reply_markup(reply_markup=kb)
            except TelegramBadRequest:
                pass

# --------- Kirish (reply tugmadan) ---------

@router.message(F.text.in_(["📋 Arizalarni ko'rish", "📋 Все заявки"]))
async def applications_handler(message: Message, state: FSMContext):
    user = await get_user_by_telegram_id(message.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")

    total, new_today, in_prog, done_today, cancelled = await _load_stats()
    await message.answer(
        _card_text(lang, total, new_today, in_prog, done_today, cancelled),
        reply_markup=_apps_menu_kb(lang),
        parse_mode="HTML"
    )

# --------- Kategoriya bo'yicha ro'yxat ---------

CAT_NEW        = "new"
CAT_PROGRESS   = "progress"
CAT_DONE_TODAY = "done_today"
CAT_CANCELLED  = "cancelled"
CAT_MY_CREATED = "my_created"     # 🆕

async def _load_items_by_cat(cat: str, manager_user_id: Optional[int] = None, my_type: Optional[str] = None) -> list[dict]:
    if cat == CAT_NEW:
        return await list_new_orders(limit=50)
    if cat == CAT_PROGRESS:
        return await list_in_progress_orders(limit=50)
    if cat == CAT_DONE_TODAY:
        return await list_completed_today_orders(limit=50)
    if cat == CAT_CANCELLED:
        return await list_cancelled_orders(limit=50)
    if cat == CAT_MY_CREATED and manager_user_id and my_type in {"connection", "technician"}:
        return await list_my_created_orders_by_type(manager_user_id, my_type, limit=50)
    return []

async def _open_category(call: CallbackQuery, state: FSMContext, lang: str, cat: str, title: str,
                         manager_user_id: Optional[int] = None, my_type: Optional[str] = None):
    await call.answer()
    items = await _load_items_by_cat(cat, manager_user_id=manager_user_id, my_type=my_type)
    if not items:
        await _safe_edit(call, lang, f"{title}\n\n{t(lang,'not_found')}", _back_kb(lang))
        return

    idx = 0
    total_loaded = len(items)
    await state.update_data(apps_cat=cat, apps_items=items, apps_idx=idx, apps_total=total_loaded)

    text = f"{title}\n\n" + _item_card(lang, items[idx], idx, total_loaded)
    kb = _list_nav_kb(idx, total_loaded, lang)
    await _safe_edit(call, lang, text, kb)

@router.callback_query(F.data == "apps:new")
async def apps_new(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")
    await _open_category(call, state, lang, CAT_NEW, t(lang, "title_new"))

@router.callback_query(F.data == "apps:progress")
async def apps_progress(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")
    await _open_category(call, state, lang, CAT_PROGRESS, t(lang, "title_progress"))

@router.callback_query(F.data == "apps:done_today")
async def apps_done_today(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")
    await _open_category(call, state, lang, CAT_DONE_TODAY, t(lang, "title_done"))

@router.callback_query(F.data == "apps:cancelled")
async def apps_cancelled(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")
    await _open_category(call, state, lang, CAT_CANCELLED, t(lang, "title_cancel"))

# --------- 🆕 Men yaratgan arizalar: submenu ---------

@router.callback_query(F.data == "apps:my_created")
async def apps_my_created_root(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")
    await _safe_edit(
        call,
        lang,
        f"{t(lang,'title_my')}\n{t(lang,'title_my_choose')}",
        _my_created_kb(lang)
    )

@router.callback_query(F.data.startswith("apps:my_type:"))
async def apps_my_created_by_type(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")
    manager_id = int(user["id"]) if user and user.get("id") else None

    _type = call.data.split(":", 2)[2]  # connection | technician
    title = t(lang, "title_my_conn") if _type == "connection" else t(lang, "title_my_tech")
    await _open_category(
        call, state, lang,
        CAT_MY_CREATED, title,
        manager_user_id=manager_id,
        my_type=_type
    )

# --------- Oldingi / Keyingi ---------

@router.callback_query(F.data == "apps:nav:prev")
async def apps_nav_prev(call: CallbackQuery, state: FSMContext):
    await call.answer()
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")

    data = await state.get_data()
    items = data.get("apps_items", [])
    idx   = max(0, int(data.get("apps_idx", 0)) - 1)
    total_loaded = len(items)
    if not items:
        await _safe_edit(call, lang, t(lang, "not_found"), _back_kb(lang)); return

    await state.update_data(apps_idx=idx)
    text = _item_card(lang, items[idx], idx, total_loaded)

    cat = data.get("apps_cat", "")
    title = {
        CAT_NEW:        t(lang, "title_new"),
        CAT_PROGRESS:   t(lang, "title_progress"),
        CAT_DONE_TODAY: t(lang, "title_done"),
        CAT_CANCELLED:  t(lang, "title_cancel"),
        CAT_MY_CREATED: t(lang, "title_my"),   # umumiy title (typeda keldingiz)
    }.get(cat, t(lang, "title_fallback"))

    kb = _list_nav_kb(idx, total_loaded, lang)
    await _safe_edit(call, lang, f"{title}\n\n{text}", kb)

@router.callback_query(F.data == "apps:nav:next")
async def apps_nav_next(call: CallbackQuery, state: FSMContext):
    await call.answer()
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")

    data = await state.get_data()
    items = data.get("apps_items", [])
    idx   = min(len(items)-1, int(data.get("apps_idx", 0)) + 1)
    total_loaded = len(items)
    if not items:
        await _safe_edit(call, lang, t(lang, "not_found"), _back_kb(lang)); return

    await state.update_data(apps_idx=idx)
    text = _item_card(lang, items[idx], idx, total_loaded)

    cat = data.get("apps_cat", "")
    title = {
        CAT_NEW:        t(lang, "title_new"),
        CAT_PROGRESS:   t(lang, "title_progress"),
        CAT_DONE_TODAY: t(lang, "title_done"),
        CAT_CANCELLED:  t(lang, "title_cancel"),
        CAT_MY_CREATED: t(lang, "title_my"),
    }.get(cat, t(lang, "title_fallback"))

    kb = _list_nav_kb(idx, total_loaded, lang)
    await _safe_edit(call, lang, f"{title}\n\n{text}", kb)

# --------- Yangilash / Orqaga / Yopish ---------

@router.callback_query(F.data == "apps:refresh")
async def apps_refresh(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")

    await call.answer(t(lang, "updating"))
    total, new_today, in_prog, done_today, cancelled = await _load_stats()
    await _safe_edit(
        call,
        lang,
        _card_text(lang, total, new_today, in_prog, done_today, cancelled),
        _apps_menu_kb(lang)
    )

@router.callback_query(F.data == "apps:back")
async def apps_back(call: CallbackQuery, state: FSMContext):
    await call.answer()
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")

    total, new_today, in_prog, done_today, cancelled = await _load_stats()
    await _safe_edit(
        call,
        lang,
        _card_text(lang, total, new_today, in_prog, done_today, cancelled),
        _apps_menu_kb(lang)
    )

@router.callback_query(F.data == "apps:close")
async def apps_close(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(call.from_user.id)
    lang = normalize_lang(user.get("language") if user else "uz")

    await call.answer(t(lang, "closed"))
    await state.update_data(apps_cat=None, apps_items=None, apps_idx=None, apps_total=None)
    try:
        await call.message.delete()
    except TelegramBadRequest:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
