from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from datetime import datetime
import html

from database.manager_inbox import (
    get_user_by_telegram_id,
    get_users_by_role,
    fetch_manager_inbox,
    assign_to_junior_manager,
    count_manager_inbox,
    get_juniors_with_load_via_history,
)
from filters.role_filter import RoleFilter

router = Router()
router.message.filter(RoleFilter("manager"))  # 🔒 faqat Manager uchun

# ==========================
# 🔤 IKKI TILLI LUG‘AT (UZ/RU)
# ==========================
T = {
    "title_inbox": {
        "uz": "🔌 <b>Manager Inbox</b>",
        "ru": "🔌 <b>Входящие менеджера</b>",
    },
    "id": {"uz": "🆔 <b>ID:</b>", "ru": "🆔 <b>ID:</b>"},
    "tariff": {"uz": "📊 <b>Tarif:</b>", "ru": "📊 <b>Тариф:</b>"},
    "client": {"uz": "👤 <b>Mijoz:</b>", "ru": "👤 <b>Клиент:</b>"},
    "phone": {"uz": "📞 <b>Telefon:</b>", "ru": "📞 <b>Телефон:</b>"},
    "address": {"uz": "📍 <b>Manzil:</b>", "ru": "📍 <b>Адрес:</b>"},
    "created": {"uz": "📅 <b>Yaratilgan:</b>", "ru": "📅 <b>Создано:</b>"},
    "order_idx": {"uz": "📄 <b>Ariza:</b>", "ru": "📄 <b>Заявка:</b>"},
    "empty": {"uz": "📭 Inbox bo'sh", "ru": "📭 Входящие пусты"},
    "prev": {"uz": "⬅️ Oldingi", "ru": "⬅️ Назад"},
    "next": {"uz": "Keyingi ➡️", "ru": "Вперёд ➡️"},
    "assign_btn": {
        "uz": "📨 Kichik menejerga yuborish",
        "ru": "📨 Отправить младшему менеджеру",
    },
    "pick_jm_title": {
        "uz": "👨‍💼 <b>Kichik menejer tanlang</b>",
        "ru": "👨‍💼 <b>Выберите младшего менеджера</b>",
    },
    "back": {"uz": "🔙 Orqaga", "ru": "🔙 Назад"},
    "no_jm": {
        "uz": "Kichik menejerlar topilmadi ❗",
        "ru": "Младшие менеджеры не найдены ❗",
    },
    "bad_format": {
        "uz": "❌ Noto'g'ri format",
        "ru": "❌ Неверный формат",
    },
    "bad_jm_id": {
        "uz": "❌ Noto'g'ri kichik menejer ID raqami",
        "ru": "❌ Неверный ID младшего менеджера",
    },
    "no_user": {
        "uz": "❌ Foydalanuvchi topilmadi",
        "ru": "❌ Пользователь не найден",
    },
    "no_jm_one": {
        "uz": "❌ Kichik menejer topilmadi",
        "ru": "❌ Младший менеджер не найден",
    },
    "error_generic": {
        "uz": "❌ Xatolik yuz berdi:",
        "ru": "❌ Произошла ошибка:",
    },
    "ok_assigned_title": {
        "uz": "✅ <b>Ariza muvaffaqiyatli yuborildi!</b>",
        "ru": "✅ <b>Заявка успешно отправлена!</b>",
    },
    "order_id": {"uz": "🆔 <b>Ariza ID:</b>", "ru": "🆔 <b>ID заявки:</b>"},
    "jm": {"uz": "👤 <b>Kichik menejer:</b>", "ru": "👤 <b>Младший менеджер:</b>"},
    "sent_time": {"uz": "📅 <b>Yuborilgan vaqt:</b>", "ru": "📅 <b>Время отправки:</b>"},
    "sender": {"uz": "👨‍💼 <b>Yuboruvchi:</b>", "ru": "👨‍💼 <b>Отправитель:</b>"},
}

# ==========================
# 🔧 UTIL
# ==========================
def normalize_lang(value: str | None) -> str:
    """DB qiymatini barqaror 'uz' yoki 'ru' ga keltiradi."""
    if not value:
        return "uz"
    v = value.strip().lower()
    ru_set = {"ru", "rus", "russian", "ru-ru", "ru_ru"}
    uz_set = {"uz", "uzb", "uzbek", "o'z", "oz", "uz-uz", "uz_uz"}
    if v in ru_set:
        return "ru"
    if v in uz_set:
        return "uz"
    return "uz"

def t(lang: str, key: str) -> str:
    """Kiritilgan key uchun lang=uz/ru bo‘yicha matnni qaytaradi."""
    lang = normalize_lang(lang)
    return T.get(key, {}).get(lang, T.get(key, {}).get("uz", key))

def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")

def esc(v) -> str:
    if v is None:
        return "-"
    return html.escape(str(v), quote=False)

# ==========================
# 🧩 VIEW + KEYBOARDS
# ==========================
def short_view_text(item: dict, index: int, total: int, lang: str) -> str:
    """Bitta arizaning qisqa ko‘rinishini (tilga mos) tayyorlaydi."""
    lang = normalize_lang(lang)

    full_id = str(item["id"])
    parts = full_id.split("_")
    short_id = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else full_id

    created = item["created_at"]
    created_dt = datetime.fromisoformat(created) if isinstance(created, str) else created

    tariff = esc(item.get("tariff", "-"))
    client_name = esc(item.get("client_name", "-"))
    client_phone = esc(item.get("client_phone", "-"))
    address = esc(item.get("address", "-"))
    short_id_safe = esc(short_id)

    return (
        f"{t(lang,'title_inbox')}\n"
        f"{t(lang,'id')} {short_id_safe}\n"
        f"{t(lang,'tariff')} {tariff}\n"
        f"{t(lang,'client')} {client_name}\n"
        f"{t(lang,'phone')} {client_phone}\n"
        f"{t(lang,'address')} {address}\n"
        f"{t(lang,'created')} {fmt_dt(created_dt)}\n"
        f"{t(lang,'order_idx')} {index + 1}/{total}"
    )

def nav_keyboard(index: int, total_loaded: int, current_id: str, lang: str) -> InlineKeyboardMarkup:
    lang = normalize_lang(lang)
    rows = []
    if index > 0:
        rows.append([InlineKeyboardButton(text=t(lang, "prev"), callback_data=f"mgr_inbox_prev_{index}")])

    row2 = [InlineKeyboardButton(
        text=t(lang, "assign_btn"),
        callback_data=f"mgr_inbox_assign_{current_id}"
    )]
    if index < total_loaded - 1:
        row2.append(InlineKeyboardButton(text=t(lang, "next"), callback_data=f"mgr_inbox_next_{index}"))
    rows.append(row2)

    return InlineKeyboardMarkup(inline_keyboard=rows)

def jm_list_keyboard(full_id: str, juniors: list, lang: str) -> InlineKeyboardMarkup:
    lang = normalize_lang(lang)
    rows = []
    for jm in juniors:
        load = jm.get("load_count", 0)
        title = (
            f"👤 {jm['full_name']} • {load} шт."   # RU
            if lang == "ru"
            else f"👤 {jm['full_name']} • {load} ta"  # UZ
        )
        rows.append([
            InlineKeyboardButton(
                text=title,
                callback_data=f"mgr_inbox_pick_{full_id}_{jm['id']}"
            )
        ])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data=f"mgr_inbox_back_{full_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==========================
# 🧠 HANDLERS
# ==========================
@router.message(F.text.in_(["📥 Inbox", "📥 Входящие"]))
async def open_inbox(message: Message, state: FSMContext):
    """
    Menedjer uchun Inbox'ni ochadi:
    1) Foydalanuvchini DB’dan oladi va uning `language` maydonini aniqlaydi (uz/ru).
    2) Umumiy arizalar sonini `count_manager_inbox()` orqali oladi.
    3) Birinchi 50 ta yozuvni `fetch_manager_inbox()` bilan yuklab, holatga saqlaydi.
    4) Matn va tugmalarni `language` ga mos holda ko‘rsatadi.
    """
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.get("role") not in ("manager", "controller"):
        return

    # 🔑 TILNI DB’DAN NORMALIZATSIYA QILIB OLYAPMIZ
    lang = normalize_lang(user.get("language"))

    total_all = await count_manager_inbox()
    items = await fetch_manager_inbox(limit=50, offset=0)

    if not items:
        await message.answer(t(lang, "empty"))
        return

    await state.update_data(inbox=items, idx=0, total=total_all, lang=lang)

    text = short_view_text(items[0], index=0, total=total_all, lang=lang)
    kb = nav_keyboard(0, len(items), str(items[0]["id"]), lang)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("mgr_inbox_prev_"))
async def prev_item(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    # 🔑 Har doim eng so‘nggi tilni DB’dan olamiz
    user = await get_user_by_telegram_id(cb.from_user.id)
    lang = normalize_lang(user.get("language"))

    data = await state.get_data()
    items = data.get("inbox", [])
    total_all = data.get("total", len(items))

    idx = int(cb.data.replace("mgr_inbox_prev_", "")) - 1
    if idx < 0 or idx >= len(items):
        return
    await state.update_data(idx=idx, lang=lang)  # tilni yangilab qo‘yamiz

    text = short_view_text(items[idx], index=idx, total=total_all, lang=lang)
    kb = nav_keyboard(idx, len(items), str(items[idx]["id"]), lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("mgr_inbox_next_"))
async def next_item(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    # 🔑 Har doim eng so‘nggi tilni DB’dan olamiz
    user = await get_user_by_telegram_id(cb.from_user.id)
    lang = normalize_lang(user.get("language"))

    data = await state.get_data()
    items = data.get("inbox", [])
    total_all = data.get("total", len(items))

    idx = int(cb.data.replace("mgr_inbox_next_", "")) + 1
    if idx < 0 or idx >= len(items):
        return
    await state.update_data(idx=idx, lang=lang)

    text = short_view_text(items[idx], index=idx, total=total_all, lang=lang)
    kb = nav_keyboard(idx, len(items), str(items[idx]["id"]), lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("mgr_inbox_assign_"))
async def assign_open(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    user = await get_user_by_telegram_id(cb.from_user.id)
    lang = normalize_lang(user.get("language"))

    full_id = cb.data.replace("mgr_inbox_assign_", "")

    juniors = await get_users_by_role("junior_manager")
    juniors = await get_juniors_with_load_via_history()  # ⬅️ yuklama bilan

    if not juniors:
        await cb.message.edit_text(t(lang, "no_jm"))
        return

    text = f"{t(lang,'pick_jm_title')}\n🆔 {esc(full_id)}"
    kb = jm_list_keyboard(full_id, juniors, lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("mgr_inbox_back_"))
async def assign_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    # 🔑 Tilni DB’dan aniqlaymiz
    user = await get_user_by_telegram_id(cb.from_user.id)
    lang = normalize_lang(user.get("language"))

    data = await state.get_data()
    items = data.get("inbox", [])
    idx = data.get("idx", 0)
    total_all = data.get("total", len(items))

    if not items:
        await cb.message.edit_text(t(lang, "empty"))
        return

    text = short_view_text(items[idx], index=idx, total=total_all, lang=lang)
    kb = nav_keyboard(idx, len(items), str(items[idx]["id"]), lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("mgr_inbox_pick_"))
async def assign_pick(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    # 🔑 Tilni DB’dan aniqlaymiz
    user = await get_user_by_telegram_id(cb.from_user.id)
    lang = normalize_lang(user.get("language"))

    parts = cb.data.split("_")
    # format: mgr_inbox_pick_[request_id]_[jm_id]
    if len(parts) < 5:
        await cb.answer(t(lang, "bad_format"), show_alert=True)
        return

    full_id = parts[3]
    jm_id_str = "_".join(parts[4:])
    try:
        jm_id = int(jm_id_str)
    except ValueError:
        await cb.answer(t(lang, "bad_jm_id"), show_alert=True)
        return

    if not user:
        await cb.answer(t(lang, "no_user"), show_alert=True)
        return

    juniors = await get_users_by_role("junior_manager")
    selected_jm = next((jm for jm in juniors if jm["id"] == jm_id), None)
    if not selected_jm:
        await cb.answer(t(lang, "no_jm_one"), show_alert=True)
        return

    try:
        # full_id "2_9" bo‘lishi mumkin — birinchi bo‘lakni request_id deb olamiz
        id_parts = full_id.split("_")
        request_id = int(id_parts[0]) if id_parts else int(full_id)

        await assign_to_junior_manager(
            request_id=request_id,
            jm_id=jm_id,
            actor_id=user["id"]
        )
    except Exception as e:
        await cb.answer(f"{t(lang,'error_generic')} {str(e)}", show_alert=True)
        return

    # short_id ni doimiy ko‘rinishga keltiramiz
    sp = full_id.split("_")
    short_id = f"{sp[0]}-{sp[1]}" if len(sp) >= 2 else full_id

    confirmation_text = (
        f"{t(lang,'ok_assigned_title')}\n\n"
        f"{t(lang,'order_id')} {esc(short_id)}\n"
        f"{t(lang,'jm')} {esc(selected_jm['full_name'])}\n"
        f"{t(lang,'sent_time')} {esc(fmt_dt(datetime.now()))}\n"
        f"{t(lang,'sender')} {esc(user.get('full_name', 'Manager'))}"
    )
    await cb.message.edit_text(confirmation_text, parse_mode="HTML")

    # State'dagi ro‘yxatdan tayinlangan itemni olib tashlaymiz
    data = await state.get_data()
    items = data.get("inbox", [])
    items = [it for it in items if str(it["id"]) != full_id]
    await state.update_data(inbox=items, lang=lang)
