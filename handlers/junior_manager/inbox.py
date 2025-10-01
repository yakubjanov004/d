# handlers/junior_manager/inbox.py  (yoki siz ishlatayotgan fayl nomi)

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from typing import List, Dict, Any
from datetime import datetime
import html

from filters.role_filter import RoleFilter
from database.jm_inbox_queries import (
    db_get_user_by_telegram_id,
    db_get_jm_inbox_items,
    db_move_order_to_controller,  # hozircha ishlatmayapmiz, kerak bo'lsa o'zgartirasiz
)
from keyboards.junior_manager_buttons import get_junior_manager_main_menu
from aiogram.fsm.state import StatesGroup, State

router = Router()
router.message.filter(RoleFilter("junior_manager"))
router.callback_query.filter(RoleFilter("junior_manager"))

# =========================
# I18N helper
# =========================
def _norm_lang(v: str | None) -> str:
    v = (v or "uz").lower()
    return "ru" if v.startswith("ru") else "uz"

TR = {
    "user_not_found": {
        "uz": "❌ Foydalanuvchi topilmadi.",
        "ru": "❌ Пользователь не найден.",
    },
    "blocked": {
        "uz": "🚫 Profil bloklangan.",
        "ru": "🚫 Профиль заблокирован.",
    },
    "inbox_empty": {
        "uz": "📭 Inbox bo‘sh.",
        "ru": "📭 Входящие пусты.",
    },
    "contacted_choose": {
        "uz": "☎️ Mijoz bilan bog‘lanildi.\nQuyidagidan birini tanlang:",
        "ru": "☎️ Связались с клиентом.\nВыберите действие:",
    },
    "nav_prev": {
        "uz": "⬅️ Oldingi",
        "ru": "⬅️ Предыдущий",
    },
    "nav_next": {
        "uz": "Keyingi ➡️",
        "ru": "Следующий ➡️",
    },
    "btn_contact": {
        "uz": "📞 Mijoz bilan bog'lanish",
        "ru": "📞 Связаться с клиентом",
    },
    "btn_send_to_controller": {
        "uz": "📤 Controller'ga yuborish",
        "ru": "📤 Отправить контроллеру",
    },
    "note_add": {
        "uz": "✍️ Qo‘shimcha ma'lumot kiritish",
        "ru": "✍️ Добавить доп. информацию",
    },
    "back": {
        "uz": "🔙 Orqaga",
        "ru": "🔙 Назад",
    },
    "card_title": {
        "uz": "🛠 <b>Ulanish arizasi — To‘liq ma'lumot</b>",
        "ru": "🛠 <b>Заявка на подключение — Полные данные</b>",
    },
    "card_id": {
        "uz": "🆔 <b>Ariza ID:</b>",
        "ru": "🆔 <b>ID:</b>",
    },
    "card_date": {
        "uz": "📅 <b>Sana:</b>",
        "ru": "📅 <b>Дата:</b>",
    },
    "card_client": {
        "uz": "👤 <b>Mijoz:</b>",
        "ru": "👤 <b>Клиент:</b>",
    },
    "card_phone": {
        "uz": "📞 <b>Telefon:</b>",
        "ru": "📞 <b>Телефон:</b>",
    },
    "card_region": {
        "uz": "🏙 <b>Hudud:</b>",
        "ru": "🏙 <b>Регион:</b>",
    },
    "card_address": {
        "uz": "📍 <b>Manzil:</b>",
        "ru": "📍 <b>Адрес:</b>",
    },
    "card_notes_title": {
        "uz": "📝 <b>Qo‘shimcha ma'lumotlar:</b>",
        "ru": "📝 <b>Доп. информация:</b>",
    },
    "card_pager": {
        "uz": "📄 <i>Ariza #{idx} / {total}</i>",
        "ru": "📄 <i>Заявка #{idx} / {total}</i>",
    },
    "send_ok": {
        "uz": "✅ Controller’ga yuborildi.",
        "ru": "✅ Отправлено контроллёру.",
    },
    "send_fail": {
        "uz": "❌ Yuborishning iloji yo‘q (status mos emas).",
        "ru": "❌ Не удалось отправить (некорректный статус).",
    },
    "note_prompt": {
        "uz": "✍️ Qo‘shimcha ma'lumot kiriting (matn yuboring).",
        "ru": "✍️ Отправьте текст доп. информации.",
    },
    "note_current": {
        "uz": "<b>Joriy matn:</b>",
        "ru": "<b>Текущий текст:</b>",
    },
    "note_too_short": {
        "uz": "Matn juda qisqa.",
        "ru": "Текст слишком короткий.",
    },
    "note_preview_title": {
        "uz": "📝 Kiritilgan matn:",
        "ru": "📝 Введённый текст:",
    },
    "note_confirm": {
        "uz": "✅ Tasdiqlash",
        "ru": "✅ Подтвердить",
    },
    "note_edit": {
        "uz": "✏️ Tahrirlash",
        "ru": "✏️ Редактировать",
    },
    "note_edit_prompt": {
        "uz": "✍️ Yangi matn yuboring.\n\n<b>Avvalgi:</b>",
        "ru": "✍️ Отправьте новый текст.\n\n<b>Предыдущий:</b>",
    },
    "error_generic": {
        "uz": "Xatolik.",
        "ru": "Ошибка.",
    },
    "note_save_fail": {
        "uz": "❌ Saqlash imkoni yo‘q (ehtimol, ariza sizga tegishli emas yoki status mos emas).",
        "ru": "❌ Не удалось сохранить (возможно, не ваша заявка или некорректный статус).",
    },
    "note_saved": {
        "uz": "✅ Saqlandi.",
        "ru": "✅ Сохранено.",
    },
}

def _t(lang: str, key: str) -> str:
    lang = _norm_lang(lang)
    return TR.get(key, {}).get(lang, key)

# =========================
# States
# =========================
class JMNoteStates(StatesGroup):
    waiting_text = State()   # matn yuborilishini kutish
    confirming   = State()   # tasdiqlash/tahrirlash

# =========================
# Utilities
# =========================
def _esc(v) -> str:
    if v is None:
        return "—"
    return html.escape(str(v), quote=False)

def _fmt_dt(dt) -> str:
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y %H:%M")
    return (str(dt)[:16]) if dt else "—"

# =========================
# Entry: 📥 Inbox (tugma o'zgarmaydi)
# =========================
@router.message(F.text == "📥 Inbox")
async def handle_inbox(msg: Message, state: FSMContext):
    user = await db_get_user_by_telegram_id(msg.from_user.id)
    if not user:
        # til ma'lum bo'lmagani uchun UZ default
        return await msg.answer(_t("uz", "user_not_found"))
    lang = _norm_lang(user.get("language"))

    if user.get("is_blocked"):
        return await msg.answer(_t(lang, "blocked"))

    items = await db_get_jm_inbox_items(recipient_id=user["id"], limit=50)
    if not items:
        return await msg.answer(_t(lang, "inbox_empty"), reply_markup=get_junior_manager_main_menu(lang))

    await state.update_data(items=items, idx=0, lang=lang)
    await _render_card(target=msg, items=items, idx=0, lang=lang)

# =========================
# Card renderer
# =========================
async def _render_card(target: Message | CallbackQuery, items: List[Dict[str, Any]], idx: int, lang: str):
    total = len(items)
    it = items[idx]

    conn_id_raw      = it.get("connection_id")
    order_created    = _fmt_dt(it.get("order_created_at"))
    client_name_raw  = it.get("client_full_name")
    client_phone_raw = it.get("client_phone")
    region_raw       = it.get("order_region")
    address_raw      = it.get("order_address")
    jm_notes_raw     = it.get("order_jm_notes") or it.get("jm_notes")  # lokal yangilanish bo‘lishi mumkin

    # escape
    conn_id_txt  = _esc(conn_id_raw)
    client_name  = _esc(client_name_raw)
    client_phone = _esc(client_phone_raw)
    region       = _esc(region_raw)
    address      = _esc(address_raw)

    notes_block = ""
    if jm_notes_raw:
        notes_block = f"\n\n{_t(lang,'card_notes_title')}\n" + _esc(jm_notes_raw)

    text = (
        f"{_t(lang,'card_title')}\n\n"
        f"{_t(lang,'card_id')} {conn_id_txt}\n"
        f"{_t(lang,'card_date')} {order_created}\n"
        f"{_t(lang,'card_client')} {client_name}\n"
        f"{_t(lang,'card_phone')} {client_phone}\n"
        f"{_t(lang,'card_region')} {region}\n"
        f"{_t(lang,'card_address')} {address}\n"
        f"{notes_block}\n\n"
        f"{_t(lang,'card_pager').format(idx=idx+1, total=total)}"
    )

    kb = _kb(idx, total, conn_id=conn_id_raw, lang=lang)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# =========================
# Inline keyboards
# =========================
def _kb_contact(lang: str, conn_id: int) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(
            text=_t(lang, "note_add"),
            callback_data=f"jm_note_start:{conn_id}"
        ),
        InlineKeyboardButton(
            text=_t(lang, "back"),
            callback_data="jm_note_back"
        ),
    ]]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _kb(idx: int, total: int, conn_id: int | None, lang: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

    if total > 1:
        nav: List[InlineKeyboardButton] = []
        if idx > 0:
            nav.append(InlineKeyboardButton(text=_t(lang, "nav_prev"), callback_data="jm_conn_prev"))
        if idx < total - 1:
            nav.append(InlineKeyboardButton(text=_t(lang, "nav_next"), callback_data="jm_conn_next"))
        if nav:
            rows.append(nav)

    rows.append([
        InlineKeyboardButton(text=_t(lang, "btn_contact"), callback_data=f"jm_contact_client:{conn_id}"),
        InlineKeyboardButton(text=_t(lang, "btn_send_to_controller"), callback_data=f"jm_send_to_controller:{conn_id}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

# =========================
# Navigation
# =========================
@router.callback_query(F.data == "jm_conn_prev")
async def jm_conn_prev(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    items = data.get("items", [])
    lang  = data.get("lang", "uz")
    idx   = max(0, (data.get("idx") or 0) - 1)
    await state.update_data(idx=idx)
    await _render_card(target=cb, items=items, idx=idx, lang=lang)

@router.callback_query(F.data == "jm_conn_next")
async def jm_conn_next(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    items = data.get("items", [])
    lang  = data.get("lang", "uz")
    idx   = data.get("idx") or 0
    if idx < len(items) - 1:
        idx += 1
    await state.update_data(idx=idx)
    await _render_card(target=cb, items=items, idx=idx, lang=lang)

# =========================
# Contact client (submenu)
# =========================
@router.callback_query(F.data.startswith("jm_contact_client:"))
async def jm_contact_client(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data  = await state.get_data()
    lang  = data.get("lang", "uz")
    conn_id = int(cb.data.split(":")[1])
    await cb.message.answer(_t(lang, "contacted_choose"), reply_markup=_kb_contact(lang, conn_id))

# =========================
# Send to controller
# =========================
@router.callback_query(F.data.startswith("jm_send_to_controller:"))
async def jm_send_to_controller(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    order_id = int(cb.data.split(":")[1])  # = connection_id (order_id)

    # JM foydalanuvchi ID sini olamiz
    jm_user = await db_get_user_by_telegram_id(cb.from_user.id)
    if not jm_user:
        return await cb.answer(_t("uz", "user_not_found"), show_alert=True)
    lang = _norm_lang(jm_user.get("language"))

    # Status + connections yozuvi
    from database.jm_inbox_queries import db_jm_send_to_controller as _jm_send
    ok = await _jm_send(order_id=order_id, jm_id=jm_user["id"])  # controller_id bermasak, o'zi tanlaydi

    if not ok:
        return await cb.answer(_t(lang, "send_fail"), show_alert=True)

    # Ro'yxatdan olib tashlab, sahifani yangilaymiz
    data  = await state.get_data()
    items = data.get("items", [])
    idx   = data.get("idx", 0)

    items = [x for x in items if x.get("connection_id") != order_id]

    if not items:
        await state.clear()
        return await cb.message.edit_text(f"{_t(lang,'send_ok')}\n\n{_t(lang,'inbox_empty')}")

    if idx >= len(items):
        idx = len(items) - 1

    await state.update_data(items=items, idx=idx, lang=lang)
    await cb.message.answer(_t(lang, "send_ok"))
    await _render_card(target=cb, items=items, idx=idx, lang=lang)

# =========================
# Notes flow
# =========================
class JMNoteStates(StatesGroup):
    waiting_text = State()
    confirming   = State()

@router.callback_query(F.data.startswith("jm_note_start:"))
async def jm_note_start(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    lang = data.get("lang", "uz")
    order_id = int(cb.data.split(":")[1])

    # oldingi matn bo‘lsa ko‘rsatamiz (state yoki items’dan)
    pending = data.get("pending_note")
    if not pending:
        items = data.get("items", [])
        idx   = data.get("idx", 0)
        if 0 <= idx < len(items) and items[idx].get("connection_id") == order_id:
            pending = items[idx].get("order_jm_notes") or items[idx].get("jm_notes")

    await state.update_data(note_order_id=order_id, pending_note=(pending or ""))

    prompt = _t(lang, "note_prompt")
    if pending:
        prompt += "\n\n" + _t(lang, "note_current") + "\n" + html.escape(pending)
    await cb.message.answer(prompt, parse_mode="HTML")
    await state.set_state(JMNoteStates.waiting_text)

@router.message(JMNoteStates.waiting_text)
async def jm_note_got_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    note = (msg.text or "").strip()
    if len(note) < 3:
        return await msg.answer(_t(lang, "note_too_short"))

    await state.update_data(pending_note=note)
    preview = _t(lang, "note_preview_title") + "\n" + html.escape(note)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=_t(lang, "note_confirm"), callback_data="jm_note_confirm"),
        InlineKeyboardButton(text=_t(lang, "note_edit"),    callback_data="jm_note_edit_again"),
    ]])
    await msg.answer(preview, parse_mode="HTML", reply_markup=kb)
    await state.set_state(JMNoteStates.confirming)

@router.callback_query(JMNoteStates.confirming, F.data == "jm_note_edit_again")
async def jm_note_edit_again(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    lang = data.get("lang", "uz")
    current = data.get("pending_note") or ""
    prompt = _t(lang, "note_edit_prompt") + "\n" + html.escape(current)
    await cb.message.answer(prompt, parse_mode="HTML")
    await state.set_state(JMNoteStates.waiting_text)

from database.jm_inbox_queries import db_set_jm_notes  # saqlash uchun

@router.callback_query(JMNoteStates.confirming, F.data == "jm_note_confirm")
async def jm_note_confirm(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data  = await state.get_data()
    lang  = data.get("lang", "uz")
    note  = (data.get("pending_note") or "").strip()
    order_id = int(data.get("note_order_id") or 0)

    if not note or not order_id:
        return await cb.answer(_t(lang, "error_generic"), show_alert=True)

    # JM foydalanuvchini tekshiramiz
    jm_user = await db_get_user_by_telegram_id(cb.from_user.id)
    if not jm_user:
        return await cb.answer(_t("uz", "user_not_found"), show_alert=True)

    ok = await db_set_jm_notes(order_id=order_id, jm_id=jm_user["id"], note_text=note)
    if not ok:
        return await cb.answer(_t(lang, "note_save_fail"), show_alert=True)

    # Lokal ro‘yxatni ham yangilab qo‘yamiz (kartochka qayta chizilganda ko‘rinsin)
    items = data.get("items", [])
    idx   = data.get("idx", 0)
    if 0 <= idx < len(items) and items[idx].get("connection_id") == order_id:
        items[idx]["jm_notes"] = note
        items[idx]["order_jm_notes"] = note
        await state.update_data(items=items)

    await cb.message.answer(_t(lang, "note_saved"))
    # Viewing holatini qayta tiklaymiz (state ni to'liq tozalamasdan)
    await state.update_data(items=items, idx=idx, lang=lang)
    await _render_card(target=cb, items=items, idx=idx, lang=lang)

@router.callback_query(F.data == "jm_note_back")
async def jm_note_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    items = data.get("items", [])
    idx   = data.get("idx", 0)
    lang  = data.get("lang", "uz")
    if not items:
        return await cb.message.answer(_t(lang, "inbox_empty"))
    await _render_card(target=cb, items=items, idx=idx, lang=lang)
