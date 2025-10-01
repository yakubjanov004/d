# handlers/junior_manager/orders.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import json
import html

from filters.role_filter import RoleFilter

# --- DB: ro'yxatlar ---
from database.junior_manager_orders_queries import (
    list_new_for_jm,
    list_inprogress_for_jm,
    list_completed_for_jm,
)

# --- Foydalanuvchi tilini olish (users.language) ---
from database.jm_inbox_queries import db_get_user_by_telegram_id

router = Router()
router.message.filter(RoleFilter("junior_manager"))
router.callback_query.filter(RoleFilter("junior_manager"))

# ===================== i18n helpers =====================
def _norm_lang(s: str | None) -> str:
    s = (s or "uz").lower()
    return "ru" if s.startswith("ru") else "uz"

def _L(lang: str) -> dict:
    lang = _norm_lang(lang)
    if lang == "ru":
        return {
            "menu_title": "📋 <b>Просмотр заявок</b>\nВыберите раздел ниже:",
            "empty": "Ничего не найдено.",
            "new": "🆕 <b>Новые заявки</b>",
            "wip": "⏳ <b>В работе</b>",
            "done": "✅ <b>Завершённые</b>",
            "type_connection": "📦 connection",
            "ago_now": "только что",
            "ago_min": "{} минут назад",
            "ago_hour": "{} часов назад",
            "ago_day": "{} дней назад",
            "prev": "⬅️ Назад",
            "next": "➡️ Вперёд",
            "back": "🔙 Назад",
            "nochange": "Без изменений ✅",
            "btn_new": "🆕 Новые заявки",
            "btn_wip": "⏳ В работе",
            "btn_done": "✅ Завершённые",
        }
    return {
        "menu_title": "📋 <b>Arizalarni ko‘rish</b>\nQuyidan bo‘limni tanlang:",
        "empty": "Hech narsa topilmadi.",
        "new": "🆕 <b>Yangi buyurtma</b>",
        "wip": "⏳ <b>Jarayonda</b>",
        "done": "✅ <b>Tugatilgan</b>",
        "type_connection": "📦 connection",
        "ago_now": "hozirgina",
        "ago_min": "{} daqiqa oldin",
        "ago_hour": "{} soat oldin",
        "ago_day": "{} kun oldin",
        "prev": "⬅️ Oldingi",
        "next": "➡️ Keyingi",
        "back": "🔙 Orqaga",
        "nochange": "Yangilanish yo‘q ✅",
        "btn_new": "🆕 Yangi buyurtmalar",
        "btn_wip": "⏳ Jarayondagilar",
        "btn_done": "✅ Tugatilganlari",
    }

# ===================== TZ & time =====================
def _tz():
    try:
        return ZoneInfo("Asia/Tashkent")
    except Exception:
        return timezone(timedelta(hours=5))

def _ago_text(dt: datetime, L: dict) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    if d:
        return L["ago_day"].format(d)
    if h:
        return L["ago_hour"].format(h)
    if m:
        return L["ago_min"].format(m)
    return L["ago_now"]

# ===================== Keyboards =====================
def _kb_root(lang: str) -> InlineKeyboardMarkup:
    L = _L(lang)
    kb = InlineKeyboardBuilder()
    kb.button(text=L["btn_new"],  callback_data="jm_list:new")
    kb.button(text=L["btn_wip"],  callback_data="jm_list:wip")
    kb.button(text=L["btn_done"], callback_data="jm_list:done")
    kb.adjust(1)
    return kb.as_markup()

def _kb_pager(idx: int, total: int, kind: str, lang: str) -> InlineKeyboardMarkup:
    L = _L(lang)
    kb = InlineKeyboardBuilder()
    kb.button(text=L["prev"], callback_data=f"jm_nav:{kind}:prev")
    kb.button(text=f"{idx+1}/{total}", callback_data="noop")
    kb.button(text=L["next"], callback_data=f"jm_nav:{kind}:next")
    kb.row()
    kb.button(text=L["back"], callback_data="jm_back")
    return kb.as_markup()

def _safe_kb_fp(kb) -> str:
    if kb is None:
        return "NONE"
    try:
        data = kb.model_dump(by_alias=True, exclude_none=True)
        return json.dumps(data, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(kb)

async def _safe_edit(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None, lang: str):
    msg = cb.message
    cur_text = msg.html_text or msg.text or ""
    if cur_text == text and _safe_kb_fp(msg.reply_markup) == _safe_kb_fp(kb):
        await cb.answer(_L(lang)["nochange"], show_alert=False)
        return
    try:
        await msg.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await cb.answer(_L(lang)["nochange"], show_alert=False)
        else:
            raise

# ===================== Card formatter =====================
def _fmt_card(item: dict, kind: str, lang: str) -> str:
    L = _L(lang)
    rid = item.get("id")
    fio = html.escape(item.get("user_name") or "—", quote=False)
    addr = html.escape(item.get("address") or "—", quote=False)
    created_at = item.get("created_at")
    when = html.escape(_ago_text(created_at, L), quote=False)

    if kind == "wip":
        status_line = html.escape(item.get("flow_status") or item.get("status_text") or "—", quote=False)
    elif kind == "done":
        status_line = "completed"  # kerak bo'lsa bu yerda i18n mapping qo'shing
    else:
        status_line = html.escape(item.get("status_text") or "—", quote=False)

    title = {"new": L["new"], "wip": L["wip"], "done": L["done"]}[kind]

    try:
        rid_view = f"{int(rid):03d}"
    except Exception:
        rid_view = html.escape(str(rid or "—"), quote=False)

    return (
        f"{title}\n"
        f"<b>#{rid_view}</b>\n"
        f"👤 {fio}\n"
        f"{L['type_connection']}\n"
        f"📊 <code>{status_line}</code>\n"
        f"📍 {addr}\n"
        f"⏱ {when}"
    )

# ===================== Entry trigger (Reply button) =====================
# Tugmani O'ZGARTIRMAYMIZ: reply keyboarddagi label'lar bilan to'g'ridan-to'g'ri mos.
ENTRY_TEXTS = [
    "📋 Arizalarni ko'rish",  # uz
    "📋 Просмотр заявок",     # ru
    "📋 Arizalarni ko‘rish",  # (ko‘ varianti)
]

@router.message(F.text.in_(ENTRY_TEXTS))
async def jm_orders_menu(msg: Message):
    u = await db_get_user_by_telegram_id(msg.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")
    await msg.answer(_L(lang)["menu_title"], reply_markup=_kb_root(lang))

# ===================== Open list =====================
@router.callback_query(F.data.startswith("jm_list:"))
async def jm_open_list(cb: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(cb.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")

    kind = cb.data.split(":")[1]  # new | wip | done
    tg_id = cb.from_user.id

    if kind == "new":
        items = await list_new_for_jm(tg_id)
    elif kind == "wip":
        items = await list_inprogress_for_jm(tg_id)
    else:
        items = await list_completed_for_jm(tg_id)

    if not items:
        await _safe_edit(cb, _L(lang)["empty"], _kb_root(lang), lang)
        return

    await state.update_data(jm_items=items, jm_idx=0, jm_kind=kind)
    text = _fmt_card(items[0], kind, lang)
    await _safe_edit(cb, text, _kb_pager(0, len(items), kind, lang), lang)

# ===================== Navigation =====================
@router.callback_query(F.data.startswith("jm_nav:"))
async def jm_nav(cb: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(cb.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")

    _, kind, direction = cb.data.split(":")
    data = await state.get_data()
    items = data.get("jm_items") or []
    if not items:
        await cb.answer(_L(lang)["empty"], show_alert=False)
        return

    idx = int(data.get("jm_idx", 0))
    if direction == "prev":
        idx = (idx - 1) % len(items)
    else:
        idx = (idx + 1) % len(items)

    await state.update_data(jm_idx=idx, jm_kind=kind)
    await _safe_edit(cb, _fmt_card(items[idx], kind, lang), _kb_pager(idx, len(items), kind, lang), lang)

@router.callback_query(F.data == "jm_back")
async def jm_back(cb: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(cb.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")

    await state.clear()
    await _safe_edit(cb, _L(lang)["menu_title"], _kb_root(lang), lang)

@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()
