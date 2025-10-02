# handlers/call_center_supervisor/inbox.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional, Dict, Any
import asyncpg
from config import settings
from filters.role_filter import RoleFilter
from database.language_queries import get_user_language   # ⬅️ qo‘shildi

# =========================================================
# Router (role: callcenter_supervisor)
# =========================================================
router = Router()
router.message.filter(RoleFilter("callcenter_supervisor"))
router.callback_query.filter(RoleFilter("callcenter_supervisor"))

# =========================================================
# DB helpers (single-file)
# =========================================================
async def _conn():
    return await asyncpg.connect(settings.DB_URL)

async def ccs_count_active() -> int:
    conn = await _conn()
    try:
        row = await conn.fetchrow("""
            SELECT COUNT(*) AS c
            FROM staff_orders
            WHERE status = 'in_call_center_supervisor'
              AND is_active = TRUE
        """)
        return int(row["c"])
    finally:
        await conn.close()

async def ccs_fetch_by_offset(offset: int) -> Optional[Dict[str, Any]]:
    conn = await _conn()
    try:
        row = await conn.fetchrow("""
            SELECT
                so.id, so.phone, so.abonent_id, so.region, so.address,
                so.tarif_id, t.name AS tariff_name, so.description,
                so.created_at, u.full_name
            FROM staff_orders AS so
            LEFT JOIN public.tarif AS t ON t.id = so.tarif_id
            LEFT JOIN public.users AS u ON u.id = NULLIF(so.abonent_id, '')::int
            WHERE so.status = 'in_call_center_supervisor'
              AND so.is_active = TRUE
            ORDER BY so.created_at ASC, so.id ASC   -- ✅ id qo‘shildi
            OFFSET $1
            LIMIT 1
        """, offset)
        return dict(row) if row else None
    finally:
        await conn.close()

async def ccs_send_to_control(order_id: int, supervisor_id: Optional[int] = None) -> None:
    conn = await _conn()
    try:
        # 1️⃣ Controller id sini olish
        controller = await conn.fetchrow("""
            SELECT id
            FROM users
            WHERE role = 'controller'
            ORDER BY id ASC
            LIMIT 1
        """)
        if not controller:
            raise Exception("Controller topilmadi")

        controller_id = controller["id"]

        # 2️⃣ staff_orders dagi user_id ni olish (ya’ni sender_id sifatida ishlatamiz)
        staff_order = await conn.fetchrow("""
            SELECT user_id
            FROM staff_orders
            WHERE id = $1
        """, order_id)

        if not staff_order or not staff_order["user_id"]:
            raise Exception(f"staff_orders.id={order_id} uchun user_id topilmadi")

        sender_user_id = staff_order["user_id"]

        # 3️⃣ staff_orders jadvalini yangilash
        await conn.execute("""
            UPDATE staff_orders
               SET status = 'in_controller',
                   updated_at = NOW()
             WHERE id = $1
        """, order_id)

        # 4️⃣ connections jadvaliga yozuv qo‘shish
        await conn.execute("""
            INSERT INTO connections (
                sender_id, recipient_id, connection_id, technician_id, staff_id,
                created_at, updated_at, sender_status, recipient_status
            )
            VALUES ($1, $2, NULL, NULL, $3, NOW(), NOW(),
                    'in_call_center_supervisor', 'in_controller')
        """, sender_user_id, controller_id, order_id)

    finally:
        await conn.close()



# =========================================================
# Region mapping (id -> human title)
# =========================================================
REGION_CODE_TO_ID = {
    "toshkent_city": 1, "toshkent_region": 2, "andijon": 3, "fergana": 4, "namangan": 5,
    "sirdaryo": 6, "jizzax": 7, "samarkand": 8, "bukhara": 9, "navoi": 10,
    "kashkadarya": 11, "surkhandarya": 12, "khorezm": 13, "karakalpakstan": 14,
}
REGION_TITLES = {
    "toshkent_city": "Toshkent shahri",
    "toshkent_region": "Toshkent viloyati",
    "andijon": "Andijon",
    "fergana": "Farg‘ona",
    "namangan": "Namangan",
    "sirdaryo": "Sirdaryo",
    "jizzax": "Jizzax",
    "samarkand": "Samarqand",
    "bukhara": "Buxoro",
    "navoi": "Navoiy",
    "kashkadarya": "Qashqadaryo",
    "surkhandarya": "Surxondaryo",
    "khorezm": "Xorazm",
    "karakalpakstan": "Qoraqalpog‘iston",
}
ID_TO_REGION_TITLE = {rid: REGION_TITLES[code] for code, rid in REGION_CODE_TO_ID.items()}

def region_title_from_id(rid: Optional[int]) -> str:
    if rid is None:
        return "-"
    try:
        return ID_TO_REGION_TITLE.get(int(rid), str(rid))
    except Exception:
        return str(rid)

# =========================================================
# Tariff name resolver
# =========================================================
def tariff_name_from_row(row: Dict[str, Any]) -> str:
    name = row.get("tariff_name")
    return name if name else "-"

# =========================================================
# UI (keyboards + card formatter) with multi-language
# =========================================================
def _kb(idx: int, total: int, order_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    prev_cb = f"ccs_prev:{idx}"
    next_cb = f"ccs_next:{idx}"
    send_cb = f"ccs_send:{order_id}:{idx}"
    cancel_cb = f"ccs_cancel:{order_id}:{idx}"

    texts = {
        "uz": {
            "back": "◀️ Orqaga",
            "next": "▶️ Oldinga",
            "send": "📤 Controlga jo'natish",
            "cancel": "❌ Bekor qilish",
        },
        "ru": {
            "back": "◀️ Назад",
            "next": "▶️ Далее",
            "send": "📤 Отправить в Control",
            "cancel": "❌ Отменить",
        }
    }
    t = texts[lang]

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t["back"], callback_data=prev_cb),
            InlineKeyboardButton(text=t["next"], callback_data=next_cb),
        ],
        [InlineKeyboardButton(text=t["send"], callback_data=send_cb)],
        [InlineKeyboardButton(text=t["cancel"], callback_data=cancel_cb)],
    ])

def _format_card(row: dict, idx: int, total: int, lang: str = "uz") -> str:
    region_text = region_title_from_id(row.get("region"))
    full_name   = row.get("full_name") or "-"
    phone_text  = row.get("phone") or "-"
    abonent_id  = row.get("abonent_id") or "-"

    description = row.get("description")
    tariff = row.get("tariff_name")

    texts = {
        "uz": {
            "inbox": "📥 <b>Call Center Supervisor Inbox</b>",
            "id": "🆔",
            "tel": "📞 <b>Tel:</b>",
            "client": "👤 <b>Mijoz:</b>",
            "region": "📍 <b>Region:</b>",
            "tariff": "💳 <b>Tarif:</b>",
            "address": "🏠 <b>Manzil:</b>",
            "issue": "📝 <b>Muammo:</b>",
        },
        "ru": {
            "inbox": "📥 <b>Входящие (Супервайзер Call Center)</b>",
            "id": "🆔",
            "tel": "📞 <b>Тел:</b>",
            "client": "👤 <b>Клиент:</b>",
            "region": "📍 <b>Регион:</b>",
            "tariff": "💳 <b>Тариф:</b>",
            "address": "🏠 <b>Адрес:</b>",
            "issue": "📝 <b>Проблема:</b>",
        }
    }
    t = texts[lang]

    description_text = f"{t['issue']} {description}\n" if description else ""
    tariff_text = f"{t['tariff']} {tariff}\n" if tariff else ""

    return (
        f"{t['inbox']}\n"
        f"{t['id']} <b>#{row['id']}</b>\n<i>{idx+1}/{total}</i>\n"
        f"{t['tel']} {phone_text}\n"
        f"{t['client']} {full_name}\n"
        f"{t['region']} {region_text}\n"
        f"{tariff_text}"
        f"{t['address']} {row.get('address') or '-'}\n"
        f"{description_text}"
    )

# =========================================================
# Show item (multi-lang)
# =========================================================
async def _show_item(target, idx: int, user_id: int):
    lang = await get_user_language(user_id) or "uz"

    total = await ccs_count_active()
    if total == 0:
        text = "📭 Inbox bo'sh." if lang == "uz" else "📭 Инбокс пуст."
        if isinstance(target, Message):
            return await target.answer(text, parse_mode="HTML")
        return await target.message.edit_text(text, parse_mode="HTML")

    idx = max(0, min(idx, total - 1))
    row = await ccs_fetch_by_offset(idx)
    if not row:
        idx = max(0, total - 1)
        row = await ccs_fetch_by_offset(idx)

    kb = _kb(idx, total, row["id"], lang)
    text = _format_card(row, idx, total, lang)

    if isinstance(target, Message):
        return await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        return await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

# =========================================================
# Handlers (lang dynamic from DB)
# =========================================================
@router.message(F.text.in_(["📥 Inbox", "📥 Входящие"]))
async def ccs_inbox(message: Message):
    await _show_item(message, idx=0, user_id=message.from_user.id)

@router.callback_query(F.data.startswith("ccs_prev:"))
async def ccs_prev(cb: CallbackQuery):
    cur = int(cb.data.split(":")[1])
    await _show_item(cb, idx=cur - 1, user_id=cb.from_user.id)
    await cb.answer()

@router.callback_query(F.data.startswith("ccs_next:"))
async def ccs_next(cb: CallbackQuery):
    cur = int(cb.data.split(":")[1])
    await _show_item(cb, idx=cur + 1, user_id=cb.from_user.id)
    await cb.answer()

@router.callback_query(F.data.startswith("ccs_send:"))
async def ccs_send(cb: CallbackQuery):
    _, order_id, cur = cb.data.split(":")
    order_id = int(order_id)
    cur = int(cur)

    await ccs_send_to_control(order_id, supervisor_id=cb.from_user.id)
    await _show_item(cb, idx=cur, user_id=cb.from_user.id)

    lang = await get_user_language(cb.from_user.id) or "uz"
    msg = "Controlga yuborildi" if lang == "uz" else "Отправлено в Control"
    await cb.answer(msg)

async def ccs_cancel(order_id: int) -> None:
    conn = await _conn()
    try:
        await conn.execute("""
            UPDATE staff_orders
               SET status = 'cancelled',
                   is_active = FALSE,
                   updated_at = NOW()
             WHERE id = $1
        """, order_id)
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("ccs_cancel:"))
async def ccs_cancel_cb(cb: CallbackQuery):
    _, order_id, cur = cb.data.split(":")
    order_id = int(order_id)
    cur = int(cur)

    await ccs_cancel(order_id)
    await _show_item(cb, idx=cur, user_id=cb.from_user.id)

    lang = await get_user_language(cb.from_user.id) or "uz"
    msg = "Ariza bekor qilindi" if lang == "uz" else "Заявка отменена"
    await cb.answer(msg)
