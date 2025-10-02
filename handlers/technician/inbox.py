# handlers/technician/inbox.py (refactored with i18n uz/ru)
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from database.queries import find_user_by_telegram_id


async def get_current_status(application_id: int, mode: str = "connection") -> str:
    """Get current status of an application"""
    from database.technician_queries import _conn
    conn = None
    try:
        conn = await _conn()
        if mode == "technician":
            query = """
                SELECT status FROM technician_orders 
                WHERE id = $1
            """
        else:  # connection mode
            query = """
                SELECT status FROM connection_orders 
                WHERE id = $1
            """
        result = await conn.fetchval(query, application_id)
        return result or "noma'lum"
    except Exception as e:
        print(f"Error getting status: {e}")
        return "noma'lum"
    finally:
        if conn:
            await conn.close()

from datetime import datetime
import html

from filters.role_filter import RoleFilter
from database.technician_queries import (
    # Ulanish (connection_orders) oqimi
    fetch_technician_inbox,
    cancel_technician_request,
    accept_technician_work,
    start_technician_work,
    finish_technician_work,
    fetch_selected_materials_for_request,
    fetch_technician_materials,
    create_material_request_and_mark_in_warehouse,

    # Material oqimi (ikkala rejimda ham ishlatiladi)
    fetch_technician_materials,
    fetch_material_by_id,
    fetch_assigned_qty,
    upsert_material_request_and_decrease_stock,

    # Texnik xizmat (technician_orders) oqimi
    fetch_technician_inbox_tech,
    accept_technician_work_for_tech,
    start_technician_work_for_tech,
    save_technician_diagnosis,
    finish_technician_work_for_tech,
    
    # Xodim arizalari (staff_orders) oqimi
    fetch_technician_inbox_staff,
    accept_technician_work_for_staff,
    start_technician_work_for_staff,
    finish_technician_work_for_staff,
)

# =====================
# I18N
# =====================
T = {
    "title_inbox": {
        "uz": "👨‍🔧 <b>Texnik — Inbox</b>",
        "ru": "👨‍🔧 <b>Техник — Входящие</b>",
    },
    "id": {"uz": "🆔 <b>ID:</b>", "ru": "🆔 <b>ID:</b>"},
    "status": {"uz": "📌 <b>Status:</b>", "ru": "📌 <b>Статус:</b>"},
    "client": {"uz": "👤 <b>Mijoz:</b>", "ru": "👤 <b>Клиент:</b>"},
    "phone": {"uz": "📞 <b>Telefon:</b>", "ru": "📞 <b>Телефон:</b>"},
    "address": {"uz": "📍 <b>Manzil:</b>", "ru": "📍 <b>Адрес:</b>"},
    "tariff": {"uz": "📊 <b>Tarif:</b>", "ru": "📊 <b>Тариф:</b>"},
    "created": {"uz": "📅 <b>Yaratilgan:</b>", "ru": "📅 <b>Создано:</b>"},
    "desc": {"uz": "📝 <b>Tavsif:</b>", "ru": "📝 <b>Описание:</b>"},
    "media_yes": {"uz": "📎 <b>Media:</b> bor", "ru": "📎 <b>Медиа:</b> есть"},
    "pager": {"uz": "🗂️ <i>Ariza {i} / {n}</i>", "ru": "🗂️ <i>Заявка {i} / {n}</i>"},
    "empty_connection": {"uz": "📭 Ulanish arizalari bo‘sh", "ru": "📭 Заявок на подключение нет"},
    "empty_tech": {"uz": "📭 Texnik xizmat arizalari bo‘sh", "ru": "📭 Заявок на техобслуживание нет"},
    "empty_staff": {"uz": "📭 Xodim arizalari bo‘sh", "ru": "📭 Заявок от сотрудников нет"},
    "choose_section": {"uz": "📂 Qaysi bo‘limni ko‘ramiz?", "ru": "📂 Какой раздел откроем?"},
    "no_perm": {"uz": "❌ Ruxsat yo‘q", "ru": "❌ Нет доступа"},
    "prev": {"uz": "⬅️ Oldingi", "ru": "⬅️ Предыдущая"},
    "next": {"uz": "Keyingi ➡️", "ru": "Следующая ➡️"},
    "cancel": {"uz": "🗑️ Bekor qilish", "ru": "🗑️ Отменить"},
    "accept": {"uz": "✅ Ishni qabul qilish", "ru": "✅ Принять работу"},
    "start": {"uz": "▶️ Ishni boshlash", "ru": "▶️ Начать работу"},
    "diagnostics": {"uz": "🩺 Diagnostika", "ru": "🩺 Диагностика"},
    "finish": {"uz": "✅ Yakunlash", "ru": "✅ Завершить"},
    "warehouse": {"uz": "📦 Ombor", "ru": "📦 Склад"},
    "review": {"uz": "📋 Yakuniy ko‘rinish", "ru": "📋 Итоговый вид"},
    "reached_start": {"uz": "❗️ Boshlanishga yetib keldingiz.", "ru": "❗️ Достигли начала списка."},
    "reached_end": {"uz": "❗️ Oxiriga yetib keldingiz.", "ru": "❗️ Достигли конца списка."},
    "ok_started": {"uz": "✅ Ish boshlandi", "ru": "✅ Работа начата"},
    "ok_cancelled": {"uz": "🗑️ Ariza bekor qilindi", "ru": "🗑️ Заявка отменена"},
    "empty_inbox": {"uz": "📭 Inbox bo‘sh", "ru": "📭 Входящие пусты"},
    "format_err": {"uz": "❌ Xato format", "ru": "❌ Неверный формат"},
    "not_found_mat": {"uz": "❌ Material topilmadi", "ru": "❌ Материал не найден"},
    "enter_qty": {"uz": "📦 <b>Miqdorni kiriting</b>", "ru": "📦 <b>Введите количество</b>"},
    "order_id": {"uz": "🆔 <b>Ariza ID:</b>", "ru": "🆔 <b>ID заявки:</b>"},
    "chosen_prod": {"uz": "📦 <b>Tanlangan mahsulot:</b>", "ru": "📦 <b>Выбранный товар:</b>"},
    "price": {"uz": "💰 <b>Narx:</b>", "ru": "💰 <b>Цена:</b>"},
    "assigned_left": {"uz": "📊 <b>Sizga biriktirilgan qoldiq:</b>", "ru": "📊 <b>Ваш закреплённый остаток:</b>"},
    "enter_qty_hint": {
        "uz": "📝 Iltimos, olinadigan miqdorni kiriting:\n• Faqat raqam (masalan: 2)\n\n<i>Maksimal: {max} dona</i>",
        "ru": "📝 Введите количество:\n• Только число (например: 2)\n\n<i>Максимум: {max} шт</i>",
    },
    "btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена"},
    "only_int": {"uz": "❗️ Faqat butun son kiriting (masalan: 2).", "ru": "❗️ Введите целое число (например: 2)."},
    "gt_zero": {"uz": "❗️ Iltimos, 0 dan katta butun son kiriting.", "ru": "❗️ Введите целое число больше 0."},
    "max_exceeded": {
        "uz": "❗️ Sizga biriktirilgan miqdor: {max} dona. {max} dan oshiq kiritib bo‘lmaydi.",
        "ru": "❗️ Ваш лимит: {max} шт. Нельзя вводить больше {max}.",
    },
    "saved_selection": {"uz": "✅ <b>Tanlov saqlandi</b>", "ru": "✅ <b>Выбор сохранён</b>"},
    "selected_products": {"uz": "📦 <b>Tanlangan mahsulotlar:</b>", "ru": "📦 <b>Выбранные материалы:</b>"},
    "add_more": {"uz": "➕ Yana material tanlash", "ru": "➕ Добавить ещё материал"},
    "final_view": {"uz": "📋 Yakuniy ko‘rinish", "ru": "📋 Итоговый вид"},
    "store_header": {
        "uz": "📦 <b>Ombor jihozlari</b>\n🆔 <b>Ariza ID:</b> {id}\nKerakli jihozlarni tanlang yoki boshqa mahsulot kiriting:",
        "ru": "📦 <b>Складские позиции</b>\n🆔 <b>ID заявки:</b> {id}\nВыберите нужное или введите другой товар:",
    },
    "diag_begin_prompt": {
        "uz": "🩺 <b>Diagnostika matnini kiriting</b>\n\nMasalan: <i>Modem moslamasi ishdan chiqqan</i>.",
        "ru": "🩺 <b>Введите текст диагностики</b>\n\nНапример: <i>Неисправен модем</i>.",
    },
    "diag_saved": {"uz": "✅ <b>Diagnostika qo‘yildi!</b>", "ru": "✅ <b>Диагностика сохранена!</b>"},
    "diag_text": {"uz": "🧰 <b>Diagnostika:</b>", "ru": "🧰 <b>Диагностика:</b>"},
    "go_store_q": {
        "uz": "🧑‍🏭 <b>Ombor bilan ishlaysizmi?</b>\n<i>Agar kerakli jihozlar omborda bo‘lsa, ularni olish kerak.</i>",
        "ru": "🧑‍🏭 <b>Перейти к складу?</b>\n<i>Если нужны материалы — забираем со склада.</i>",
    },
    "yes": {"uz": "✅ Ha", "ru": "✅ Да"},
    "no": {"uz": "❌ Yo‘q", "ru": "❌ Нет"},
    "diag_cancelled": {"uz": "ℹ️ Omborga murojaat qilinmadi. Davom etishingiz mumkin.", "ru": "ℹ️ К складу не обращались. Можно продолжать."},
    "catalog_empty": {"uz": "📦 Katalog bo‘sh.", "ru": "📦 Каталог пуст."},
    "catalog_header": {"uz": "📦 <b>Mahsulot katalogi</b>\nKeraklisini tanlang:", "ru": "📦 <b>Каталог материалов</b>\nВыберите нужное:"},
    "back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "qty_title": {"uz": "✍️ <b>Miqdorni kiriting</b>", "ru": "✍️ <b>Введите количество</b>"},
    "order": {"uz": "🆔 Ariza:", "ru": "🆔 Заявка:"},
    "product": {"uz": "📦 Mahsulot:", "ru": "📦 Материал:"},
    "price_line": {"uz": "💰 Narx:", "ru": "💰 Цена:"},
    "ctx_lost": {"uz": "❗️ Kontekst yo‘qolgan, qaytadan urinib ko‘ring.", "ru": "❗️ Контекст потерян, попробуйте снова."},
    "req_not_found": {"uz": "❗️ Ariza aniqlanmadi.", "ru": "❗️ Заявка не найдена."},
    "x_error": {"uz": "❌ Xatolik:", "ru": "❌ Ошибка:"},
    "state_cleared": {"uz": "Bekor qilindi", "ru": "Отменено"},
    "status_mismatch": {"uz": "⚠️ Holat mos emas", "ru": "⚠️ Некорректный статус"},
    "status_mismatch_detail": {
        "uz": "⚠️ Holat mos emas (faqat 'in_technician').",
        "ru": "⚠️ Некорректный статус (только 'in_technician').",
    },
    "status_mismatch_finish": {
        "uz": "⚠️ Holat mos emas (faqat 'in_technician_work').",
        "ru": "⚠️ Некорректный статус (только 'in_technician_work').",
    },
    "work_finished": {"uz": "✅ <b>Ish yakunlandi</b>", "ru": "✅ <b>Работа завершена</b>"},
    "used_materials": {"uz": "📦 <b>Ishlatilgan mahsulotlar:</b>", "ru": "📦 <b>Использованные материалы:</b>"},
    "none": {"uz": "• (mahsulot tanlanmadi)", "ru": "• (материалы не выбраны)"},
    "akt_err_ignored": {"uz": "AKT xatoligi ishni to'xtatmaydi", "ru": "Ошибка АКТ не останавливает процесс"},
    "store_request_sent": {
        "uz": "📨 <b>Omborga so‘rov yuborildi</b>",
        "ru": "📨 <b>Заявка на склад отправлена</b>",
    },
    "req_type_info": {
        "uz": "⏳ Ariza holati endi <b>in_warehouse</b>. Omborchi tasdiqlagach yana <b>in_technician_work</b> bo‘ladi.",
        "ru": "⏳ Статус теперь <b>in_warehouse</b>. После подтверждения склада вернётся в <b>in_technician_work</b>.",
    },
    "sections_keyboard": {
        "uz": ["🔌 Ulanish arizalari", "🔧 Texnik xizmat arizalari", "📞 Operator arizalari"],
        "ru": ["🔌 Заявки на подключение", "🔧 Заявки на техобслуживание", "📞 Заявки от операторов"],
    },
}

def t(key: str, lang: str = "uz", **kwargs) -> str:
    val = T.get(key, {}).get(lang, "")
    return val.format(**kwargs) if kwargs else val

async def resolve_lang(user_id: int, fallback: str = "uz") -> str:
    """Foydalanuvchi tilini DB'dan olish: users.lang ('uz'|'ru') bo‘lsa ishlatiladi."""
    try:
        u = await find_user_by_telegram_id(user_id)
        if u:
            lang = (u.get("lang") or u.get("user_lang") or u.get("language") or "").lower()
            if lang in ("uz", "ru"):
                return lang
    except Exception:
        pass
    return fallback

# ====== STATE-lar ======
class QtyStates(StatesGroup):
    waiting_qty = State()
class CustomQtyStates(StatesGroup):
    waiting_qty = State()
class DiagStates(StatesGroup):
    waiting_text = State()

# ====== Router ======
router = Router()
router.message.filter(RoleFilter("technician"))
router.callback_query.filter(RoleFilter("technician"))

# =====================
# Helperlar
# =====================
def _preserve_mode_clear(state: FSMContext, keep_keys: list[str] | None = None):
    async def _inner():
        data = await state.get_data()
        mode = data.get("tech_mode")
        kept: dict = {}
        if keep_keys:
            for k in keep_keys:
                if k in data:
                    kept[k] = data[k]
        await state.clear()
        payload = {"tech_mode": mode}
        payload.update(kept)
        await state.update_data(**payload)
    return _inner()

def fmt_dt(dt) -> str:
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return html.escape(dt, quote=False)
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y %H:%M")
    return "-"

def esc(v) -> str:
    return "-" if v is None else html.escape(str(v), quote=False)

def _qty_of(it: dict) -> str:
    q = it.get('qty')
    if q is None:
        q = it.get('quantity', it.get('description'))
    return str(q) if q is not None else "-"

def status_emoji(s: str) -> str:
    m = {
        "between_controller_technician": "🆕",
        "in_technician": "🧰",
        "in_technician_work": "🟢",
        "in_warehouse": "📦",
        "completed": "✅",
    }
    return m.get(s, "📌")

def short_view_text(item: dict, idx: int, total: int, lang: str = "uz") -> str:
    base = (
        f"{t('title_inbox', lang)}\n"
        f"{t('id', lang)} {esc(item.get('id'))}\n"
        f"{status_emoji(item.get('status',''))} {t('status', lang)} {esc(item.get('status'))}\n"
        f"{t('client', lang)} {esc(item.get('client_name'))}\n"
        f"{t('phone', lang)} {esc(item.get('client_phone'))}\n"
        f"{t('address', lang)} {esc(item.get('address'))}\n"
    )
    if item.get("tariff"):
        base += f"{t('tariff', lang)} {esc(item.get('tariff'))}\n"
    if item.get("created_at"):
        base += f"{t('created', lang)} {fmt_dt(item.get('created_at'))}\n"
    desc = (item.get("description") or "").strip()
    if desc:
        short_desc = (desc[:140] + "…") if len(desc) > 140 else desc
        base += f"{t('desc', lang)} {html.escape(short_desc, quote=False)}\n"
    media = (item.get("media") or "").strip()
    if media:
        base += t("media_yes", lang) + "\n"
    base += "\n" + t("pager", lang, i=idx + 1, n=total)
    return base

def _short(s: str, n: int = 48) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"

def _fmt_price_uzs(val) -> str:
    try:
        s = f"{int(val):,}"
        return s.replace(",", " ")
    except Exception:
        return str(val)

def materials_keyboard(materials: list[dict], applications_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    rows = []
    if materials:
        for mat in materials:
            name = _short(mat.get('name', 'NO NAME'))
            price = _fmt_price_uzs(mat.get('price', 0))
            stock = mat.get('stock_quantity', '0')
            title = f"📦 {name} — {price} so'm ({stock} dona)" if lang == "uz" else f"📦 {name} — {price} сум ({stock} шт)"
            rows.append([InlineKeyboardButton(
                text=title[:64],
                callback_data=f"tech_mat_select_{mat.get('material_id')}_{applications_id}"
            )])
    rows.append([InlineKeyboardButton(text=("➕ Boshqa mahsulot" if lang == "uz" else "➕ Другой материал"),
                                      callback_data=f"tech_mat_custom_{applications_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def action_keyboard(item_id: int, index: int, total: int, status: str, mode: str = "connection", lang: str = "uz") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if total > 1:
        nav = []
        if index > 0:
            nav.append(InlineKeyboardButton(text=t("prev", lang), callback_data=f"tech_inbox_prev_{index}"))
        if index < total - 1:
            nav.append(InlineKeyboardButton(text=t("next", lang), callback_data=f"tech_inbox_next_{index}"))
        if nav:
            rows.append(nav)
    if status == "between_controller_technician":
        rows.append([
            InlineKeyboardButton(text=t("cancel", lang), callback_data=f"tech_cancel_{item_id}"),
            InlineKeyboardButton(text=t("accept", lang), callback_data=f"tech_accept_{item_id}"),
        ])
    elif status == "in_technician":
        rows.append([InlineKeyboardButton(text=t("start", lang), callback_data=f"tech_start_{item_id}")])
    elif status == "in_technician_work":
        if mode == "technician":
            rows.append([InlineKeyboardButton(text=t("diagnostics", lang), callback_data=f"tech_diag_begin_{item_id}")])
            rows.append([InlineKeyboardButton(text=t("finish", lang), callback_data=f"tech_finish_{item_id}")])
        else:
            rows.append([
                InlineKeyboardButton(text=t("warehouse", lang), callback_data=f"tech_add_more_{item_id}"),
                InlineKeyboardButton(text=t("review", lang), callback_data=f"tech_review_{item_id}"),
            ])
            rows.append([InlineKeyboardButton(text=t("finish", lang), callback_data=f"tech_finish_{item_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _dedup_by_id(items: list[dict]) -> list[dict]:
    seen = set(); out = []
    for it in items:
        i = it.get("id")
        if i in seen: continue
        seen.add(i); out.append(it)
    return out

def tech_category_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    a, b, c = T["sections_keyboard"][lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="tech_inbox_cat_connection")],
        [InlineKeyboardButton(text=b, callback_data="tech_inbox_cat_tech")],
        [InlineKeyboardButton(text=c, callback_data="tech_inbox_cat_operator")],
    ])

async def _safe_edit(message, text: str, kb: InlineKeyboardMarkup):
    try:
        if message.text == text:
            try:
                await message.edit_reply_markup(reply_markup=kb)
                return
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    return
                raise
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise

# ====== Inbox ochish: avval kategoriya ======
@router.message(F.text.in_(["📥 Inbox", "Inbox", "📥 Входящие"]))
async def tech_open_inbox(message: Message, state: FSMContext):
    user = await find_user_by_telegram_id(message.from_user.id)
    if not user or user.get("role") != "technician":
        return
    lang = await resolve_lang(message.from_user.id, fallback=("ru" if message.text == "📥 Входящие" else "uz"))
    await state.update_data(tech_mode=None, tech_inbox=[], tech_idx=0, lang=lang)
    await message.answer(t("choose_section", lang), reply_markup=tech_category_keyboard(lang))

# ====== Kategoriya handlerlari ======
@router.callback_query(F.data == "tech_inbox_cat_connection")
async def tech_cat_connection(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    items = _dedup_by_id(await fetch_technician_inbox(technician_id=user["id"], limit=50, offset=0))
    await state.update_data(tech_mode="connection", tech_inbox=items, tech_idx=0, lang=lang)
    if not items:
        return await cb.message.edit_text(t("empty_connection", lang))
    item = items[0]; total = len(items)
    text = short_view_text(item, 0, total, lang)
    kb = action_keyboard(item.get("id"), 0, total, item.get("status", ""), mode="connection", lang=lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "tech_inbox_cat_tech")
async def tech_cat_tech(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    items = _dedup_by_id(await fetch_technician_inbox_tech(technician_id=user["id"], limit=50, offset=0))
    await state.update_data(tech_mode="technician", tech_inbox=items, tech_idx=0, lang=lang)
    if not items:
        return await cb.message.edit_text(t("empty_tech", lang))
    item = items[0]; total = len(items)
    text = short_view_text(item, 0, total, lang)
    kb = action_keyboard(item.get("id"), 0, total, item.get("status", ""), mode="technician", lang=lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "tech_inbox_cat_operator")
async def tech_cat_operator(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    items = _dedup_by_id(await fetch_technician_inbox_staff(technician_id=user["id"], limit=50, offset=0))
    await state.update_data(tech_mode="staff", tech_inbox=items, tech_idx=0, lang=lang)
    if not items:
        return await cb.message.edit_text(t("empty_staff", lang))
    item = items[0]; total = len(items)
    text = short_view_text(item, 0, total, lang)
    kb = action_keyboard(item.get("id"), 0, total, item.get("status", ""), mode="staff", lang=lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# ====== Navigatsiya (prev/next) ======
@router.callback_query(F.data.startswith("tech_inbox_prev_"))
async def tech_prev(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    items = _dedup_by_id(st.get("tech_inbox", []))
    if not items:
        return await cb.answer(t("empty_inbox", lang))
    total = len(items)
    idx = int(cb.data.replace("tech_inbox_prev_", "")) - 1
    if idx < 0 or idx >= total:
        return await cb.answer(t("reached_start", lang))
    await state.update_data(tech_inbox=items, tech_idx=idx)
    item = items[idx]
    text = short_view_text(item, idx, total, lang)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)

@router.callback_query(F.data.startswith("tech_inbox_next_"))
async def tech_next(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    items = _dedup_by_id(st.get("tech_inbox", []))
    if not items:
        return await cb.answer(t("empty_inbox", lang))
    total = len(items)
    idx = int(cb.data.replace("tech_inbox_next_", "")) + 1
    if idx < 0 or idx >= total:
        return await cb.answer(t("reached_end", lang))
    await state.update_data(tech_inbox=items, tech_idx=idx)
    item = items[idx]
    text = short_view_text(item, idx, total, lang)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)

# ====== Qabul qilish / Bekor qilish / Boshlash ======
@router.callback_query(F.data.startswith("tech_accept_"))
async def tech_accept(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    req_id = int(cb.data.replace("tech_accept_", ""))
    try:
        if mode == "technician":
            ok = await accept_technician_work_for_tech(applications_id=req_id, technician_id=user["id"])
        elif mode == "staff":
            ok = await accept_technician_work_for_staff(applications_id=req_id, technician_id=user["id"])
        else:
            ok = await accept_technician_work(applications_id=req_id, technician_id=user["id"])
        if not ok:
            return await cb.answer(t("status_mismatch", lang), show_alert=True)
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    items = _dedup_by_id((await state.get_data()).get("tech_inbox", []))
    idx = int((await state.get_data()).get("tech_idx", 0))
    for it in items:
        if it.get("id") == req_id:
            it["status"] = "in_technician"
            break
    await state.update_data(tech_inbox=items)
    total = len(items)
    item = items[idx] if 0 <= idx < total else items[0]
    text = short_view_text(item, idx, total, lang)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("tech_cancel_"))
async def tech_cancel(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    req_id = int(cb.data.replace("tech_cancel_", ""))
    try:
        await cancel_technician_request(applications_id=req_id, technician_id=user["id"])
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    items = _dedup_by_id(st.get("tech_inbox", []))
    idx = int(st.get("tech_idx", 0))
    items = [it for it in items if it.get("id") != req_id]

    if not items:
        await state.update_data(tech_inbox=[], tech_idx=0)
        await cb.answer(t("ok_cancelled", lang))
        return await _safe_edit(cb.message, t("empty_inbox", lang), InlineKeyboardMarkup(inline_keyboard=[]))

    if idx >= len(items):
        idx = len(items) - 1

    await state.update_data(tech_inbox=items, tech_idx=idx)
    total = len(items); item = items[idx]
    text = short_view_text(item, idx, total, lang)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)

@router.callback_query(F.data.startswith("tech_start_"))
async def tech_start(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    req_id = int(cb.data.replace("tech_start_", ""))
    try:
        if mode == "technician":
            ok = await start_technician_work_for_tech(applications_id=req_id, technician_id=user["id"])
        elif mode == "staff":
            ok = await start_technician_work_for_staff(applications_id=req_id, technician_id=user["id"])
        else:
            ok = await start_technician_work(applications_id=req_id, technician_id=user["id"])
        if not ok:
            current_status = await get_current_status(req_id, mode)
            error_msg = f"⚠️ Xatolik! Avval 'Qabul qilish' tugmasini bosing.\n\n"
            error_msg += f"Joriy holat: {current_status or 'noma\'lum'}\n"
            error_msg += "Kerakli holat: in_technician"
            return await cb.answer(error_msg, show_alert=True)
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    items = _dedup_by_id((await state.get_data()).get("tech_inbox", []))
    idx = int((await state.get_data()).get("tech_idx", 0))
    for it in items:
        if it.get("id") == req_id:
            it["status"] = "in_technician_work"
            break
    await state.update_data(tech_inbox=items)

    total = len(items)
    item = items[idx] if 0 <= idx < total else items[0]
    text = short_view_text(item, idx, total, lang)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)

    if mode == "technician":
        diag_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("diagnostics", lang), callback_data=f"tech_diag_begin_{req_id}")]
        ])
        await cb.message.answer(
            t("ok_started", lang) + "\n\n" + t("diag_begin_prompt", lang),
            reply_markup=diag_kb
        )
        await cb.answer(t("ok_started", lang))
        return

    mats = await fetch_technician_materials()
    header_text = t("store_header", lang, id=req_id)
    await cb.message.answer(header_text, reply_markup=materials_keyboard(mats, applications_id=req_id, lang=lang), parse_mode="HTML")

# ====== DIAGNOSTIKA ======
@router.callback_query(F.data.startswith("tech_diag_begin_"))
async def tech_diag_begin(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_diag_begin_", ""))
    except Exception:
        return
    await state.update_data(diag_req_id=req_id, lang=lang)
    await cb.message.answer(t("diag_begin_prompt", lang), parse_mode="HTML")
    await state.set_state(DiagStates.waiting_text)

@router.message(StateFilter(DiagStates.waiting_text))
async def tech_diag_text(msg: Message, state: FSMContext):
    user = await find_user_by_telegram_id(msg.from_user.id)
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(msg.from_user.id)
    if not user or user.get("role") != "technician":
        return await msg.answer(t("no_perm", lang))

    data = await state.get_data()
    req_id = int(data.get("diag_req_id", 0))
    if req_id <= 0:
        await _preserve_mode_clear(state)
        return await msg.answer(t("req_not_found", lang))

    text = (msg.text or "").strip()
    if not text:
        return await msg.answer(t("only_int", lang))  # qisqa validatsiya xabari sifatida qayta ishlatildi

    try:
        await save_technician_diagnosis(applications_id=req_id, technician_id=user["id"], text=text)
    except Exception as e:
        await _preserve_mode_clear(state)
        return await msg.answer(f"{t('x_error', lang)} {e}")

    await _preserve_mode_clear(state)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("yes", lang),  callback_data=f"tech_diag_go_store_{req_id}")],
        [InlineKeyboardButton(text=t("no", lang), callback_data=f"tech_diag_cancel_{req_id}")],
    ])
    await msg.answer(
        f"{t('diag_saved', lang)}\n\n"
        f"{t('order_id', lang)} {esc(req_id)}\n"
        f"{t('diag_text', lang)}\n<code>{html.escape(text, quote=False)}</code>\n\n"
        f"{t('go_store_q', lang)}",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("tech_diag_go_store_"))
async def tech_diag_go_store(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_diag_go_store_", ""))
    except Exception:
        return
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mats = await fetch_technician_materials()
    header_text = t("store_header", lang, id=req_id)
    await cb.message.answer(header_text, reply_markup=materials_keyboard(mats, applications_id=req_id, lang=lang), parse_mode="HTML")

@router.callback_query(F.data.startswith("tech_diag_cancel_"))
async def tech_diag_cancel(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    await cb.answer(t("state_cleared", lang))
    await _preserve_mode_clear(state)
    await cb.message.answer(t("diag_cancelled", lang))

# ====== Materiallar oqimi ======
@router.callback_query(F.data.startswith("tech_mat_select_"))
async def tech_mat_select(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        payload = cb.data[len("tech_mat_select_"):]
        material_id, req_id = map(int, payload.split("_", 1))
    except Exception:
        return await cb.answer(t("format_err", lang), show_alert=True)

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mat = await fetch_material_by_id(material_id)
    if not mat:
        return await cb.answer(t("not_found_mat", lang), show_alert=True)

    assigned_left = await fetch_assigned_qty(user["id"], material_id)
    assigned_left = int(assigned_left or 0)

    text = (
        f"{t('enter_qty', lang)}\n\n"
        f"{t('order_id', lang)} {req_id}\n"
        f"{t('chosen_prod', lang)} {esc(mat['name'])}\n"
        f"{t('price', lang)} {_fmt_price_uzs(mat['price'])} {'so\'m' if lang=='uz' else 'сум'}\n"
        f"{t('assigned_left', lang)} {assigned_left} {'dona' if lang=='uz' else 'шт'}\n\n"
        + t("enter_qty_hint", lang, max=assigned_left)
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"tech_qty_cancel_{req_id}")]
    ])

    await state.update_data(
        qty_ctx={
            "applications_id": req_id,
            "material_id": material_id,
            "material_name": mat["name"],
            "price": mat["price"],
            "max_qty": assigned_left,
            "lang": lang,
        }
    )

    await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(QtyStates.waiting_qty)
    await cb.answer()

@router.callback_query(F.data.startswith("tech_qty_cancel_"))
async def tech_qty_cancel(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_qty_cancel_", ""))
    except Exception:
        return await cb.answer()

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mats = await fetch_technician_materials()
    header_text = t("store_header", lang, id=req_id)
    await cb.message.answer(header_text, reply_markup=materials_keyboard(mats, applications_id=req_id, lang=lang), parse_mode="HTML")
    await _preserve_mode_clear(state)
    await cb.answer(t("state_cleared", lang))

@router.message(StateFilter(QtyStates.waiting_qty))
async def tech_qty_entered(msg: Message, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(msg.from_user.id)
    user = await find_user_by_telegram_id(msg.from_user.id)
    if not user or user.get("role") != "technician":
        return await msg.answer(t("no_perm", lang))

    ctx = st.get("qty_ctx") or {}
    req_id = int(ctx.get("applications_id", 0))
    material_id = int(ctx.get("material_id", 0))
    max_qty = int(ctx.get("max_qty", 0))

    try:
        qty = int((msg.text or "").strip())
        if qty <= 0:
            return await msg.answer(t("gt_zero", lang))
    except Exception:
        return await msg.answer(t("only_int", lang))

    if qty > max_qty:
        return await msg.answer(t("max_exceeded", lang, max=max_qty))

    try:
        await upsert_material_request_and_decrease_stock(
            user_id=user["id"],
            applications_id=req_id,
            material_id=material_id,
            add_qty=qty
        )
    except ValueError as ve:
        return await msg.answer(f"❌ {ve}")
    except Exception as e:
        return await msg.answer(f"{t('x_error', lang)} {e}")

    selected = await fetch_selected_materials_for_request(user["id"], req_id)
    lines = [t("saved_selection", lang) + "\n", f"{t('order_id', lang)} {req_id}", t("selected_products", lang)]
    for it in selected:
        qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
        price_txt = f"{_fmt_price_uzs(it['price'])} {'so\'m' if lang=='uz' else 'сум'}"
        lines.append(f"• {esc(it['name'])} — {qty_txt} (💰 {price_txt})")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("add_more", lang), callback_data=f"tech_add_more_{req_id}")],
        [InlineKeyboardButton(text=t("final_view", lang), callback_data=f"tech_review_{req_id}")]
    ])
    await msg.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    await _preserve_mode_clear(state)

@router.callback_query(F.data.startswith("tech_back_to_materials_"))
async def tech_back_to_materials(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_back_to_materials_", ""))
    except Exception:
        return await cb.answer()
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mats = await fetch_technician_materials()
    header_text = t("store_header", lang, id=req_id)
    await cb.message.answer(header_text, reply_markup=materials_keyboard(mats, applications_id=req_id, lang=lang), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("tech_finish_"))
async def tech_finish(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_finish_", ""))
    except Exception:
        return await cb.answer()

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mode = st.get("tech_mode", "connection")
    selected = await fetch_selected_materials_for_request(user["id"], req_id)

    try:
        if mode == "technician":
            ok = await finish_technician_work_for_tech(applications_id=req_id, technician_id=user["id"])
            request_type = "technician"
        elif mode == "staff":
            ok = await finish_technician_work_for_staff(applications_id=req_id, technician_id=user["id"])
            request_type = "staff"
        else:
            ok = await finish_technician_work(applications_id=req_id, technician_id=user["id"])
            request_type = "connection"
        if not ok:
            return await cb.answer(t("status_mismatch_finish", lang), show_alert=True)
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    lines = [t("work_finished", lang) + "\n", f"{t('order_id', lang)} {req_id}", t("used_materials", lang)]
    if selected:
        for it in selected:
            qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
            lines.append(f"• {esc(it['name'])} — {qty_txt}")
    else:
        lines.append(T["none"][lang])

    await cb.message.answer("\n".join(lines), parse_mode="HTML")
    await cb.answer(t("finish", lang) + " ✅")

    try:
        from utils.akt_service import AKTService
        akt_service = AKTService()
        await akt_service.post_completion_pipeline(cb.bot, req_id, request_type)
    except Exception:
        pass  # AKT xatosi jarayonni to‘xtatmaydi

@router.callback_query(F.data.startswith("tech_add_more_"))
async def tech_add_more(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    req_id = int(cb.data.replace("tech_add_more_", ""))
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mats = await fetch_technician_materials()
    header_text = t("store_header", lang, id=req_id)
    await cb.message.answer(header_text, reply_markup=materials_keyboard(mats, applications_id=req_id, lang=lang), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("tech_review_"))
async def tech_review(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    req_id = int(cb.data.replace("tech_review_", ""))    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    selected = await fetch_selected_materials_for_request(user["id"], req_id)
    lines = [t("final_view", lang) + "\n", f"{t('order_id', lang)} {req_id}", (t("used_materials", lang) if lang=='ru' else "📦 <b>Ishlatiladigan mahsulotlar:</b>")]
    if selected:
        for it in selected:
            qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
            price_txt = f"{_fmt_price_uzs(it['price'])} {'so\'m' if lang=='uz' else 'сум'}"
            lines.append(f"• {esc(it['name'])} — {qty_txt} (💰 {price_txt})")
    else:
        lines.append("• (tanlanmagan)" if lang == "uz" else "• (не выбрано)")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("finish", lang), callback_data=f"tech_finish_{req_id}")],
        [InlineKeyboardButton(text=t("back", lang), callback_data=f"tech_back_to_materials_{req_id}")]
    ])
    await cb.message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("tech_mat_custom_"))
async def tech_mat_custom(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_mat_custom_", ""))
    except Exception:
        return
    mats = await fetch_technician_materials(limit=200, offset=0)
    if not mats:
        return await cb.message.answer(T["catalog_empty"][lang])

    rows = []
    for m in mats:
        name = _short(m.get('name', 'NO NAME'))
        title = f"📦 {name} — {_fmt_price_uzs(m.get('price', 0))} {'so\'m' if lang=='uz' else 'сум'}"
        rows.append([InlineKeyboardButton(
            text=title[:64],
            callback_data=f"tech_custom_select_{m.get('material_id')}_{req_id}"
        )])

    rows.append([InlineKeyboardButton(text=T["back"][lang], callback_data=f"tech_back_to_materials_{req_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await cb.message.answer(T["catalog_header"][lang], reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("tech_custom_select_"))
async def tech_custom_select(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        payload = cb.data[len("tech_custom_select_"):]
        material_id, req_id = map(int, payload.split("_", 1))
    except Exception:
        return

    mat = await fetch_material_by_id(material_id)
    if not mat:
        return await cb.answer(t("not_found_mat", lang), show_alert=True)

    await state.update_data(custom_ctx={
        "applications_id": req_id,
        "material_id": material_id,
        "material_name": mat["name"],
        "price": mat.get("price", 0),
        "lang": lang,
    })

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"tech_back_to_materials_{req_id}")]
    ])

    await cb.message.answer(
        f"{t('qty_title', lang)}\n\n"
        f"{t('order', lang)} {req_id}\n"
        f"{t('product', lang)} {esc(mat['name'])}\n"
        f"{t('price_line', lang)} {_fmt_price_uzs(mat.get('price',0))} {'so\'m' if lang=='uz' else 'сум'}\n\n"
        f"{t('only_int', lang)}",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(CustomQtyStates.waiting_qty)

@router.message(StateFilter(CustomQtyStates.waiting_qty))
async def custom_qty_entered(msg: Message, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(msg.from_user.id)
    user = await find_user_by_telegram_id(msg.from_user.id)
    if not user or user.get("role") != "technician":
        return await msg.answer(t("no_perm", lang))

    ctx  = st.get("custom_ctx") or {}
    req_id      = int(ctx.get("applications_id", 0))
    material_id = int(ctx.get("material_id", 0))
    if not (req_id and material_id):
        await _preserve_mode_clear(state)
        return await msg.answer(t("ctx_lost", lang))

    try:
        qty = int((msg.text or "").strip())
        if qty <= 0:
            return await msg.answer(t("gt_zero", lang))
    except Exception:
        return await msg.answer(t("only_int", lang))

    mode = st.get("tech_mode", "connection")
    request_type = "technician" if mode == "technician" else ("staff" if mode == "staff" else "connection")

    try:
        ok = await create_material_request_and_mark_in_warehouse(
            applications_id=req_id,
            technician_id=user["id"],
            material_id=material_id,
            qty=qty,
            request_type=request_type,
        )
        if not ok:
            return await msg.answer(t("status_mismatch", lang))
    except Exception as e:
        return await msg.answer(f"{t('x_error', lang)} {e}")

    data2 = await state.get_data()
    items = _dedup_by_id(data2.get("tech_inbox", []))
    if items:
        try:
            for it in items:
                if it.get("id") == req_id:
                    it["status"] = "in_warehouse"
                    break
            await state.update_data(tech_inbox=items)
        except Exception:
            pass

    await _preserve_mode_clear(state)
    await msg.answer(
        f"{t('store_request_sent', lang)}\n"
        f"{t('order', lang)} {req_id}\n"
        f"📦 ID: {material_id}\n"
        f"🔢 {qty}\n"
        f"{t('req_type_info', lang)}",
        parse_mode="HTML"
    )
