# handlers/manager/smart_service.py

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
import html
import logging

from database.basic.user import get_user_by_telegram_id
from database.basic.language import get_user_language
from database.basic.smart_service import fetch_smart_service_orders
from filters.role_filter import RoleFilter
from keyboards.manager_buttons import get_manager_main_menu

router = Router()
logger = logging.getLogger(__name__)
router.message.filter(RoleFilter("manager"))

# -----------------------------
# 🔤 I18N (UZ/RU tarjimalar)
# -----------------------------
T = {
    "title": {
        "uz": "🎯 <b>SMART SERVICE ARIZALARI</b>",
        "ru": "🎯 <b>ЗАЯВКИ SMART SERVICE</b>",
    },
    "order": {"uz": "📋 <b>Buyurtma:</b>", "ru": "📋 <b>Заявка:</b>"},
    "category": {"uz": "🏷️ <b>Kategoriya:</b>", "ru": "🏷️ <b>Категория:</b>"},
    "service": {"uz": "🔧 <b>Xizmat:</b>", "ru": "🔧 <b>Сервис:</b>"},
    "client": {"uz": "👤 <b>Mijoz:</b>", "ru": "👤 <b>Клиент:</b>"},
    "phone": {"uz": "📞 <b>Telefon:</b>", "ru": "📞 <b>Телефон:</b>"},
    "username": {"uz": "👤 Username:", "ru": "👤 Username:"},  # Username o'zgarmaydi
    "address": {"uz": "📍 <b>Manzil:</b>", "ru": "📍 <b>Адрес:</b>"},
    "gps": {"uz": "📍 GPS:", "ru": "📍 GPS:"},
    "date": {"uz": "📅 <b>Sana:</b>", "ru": "📅 <b>Дата:</b>"},
    "item_idx": {"uz": "📄 <b>Ariza:</b>", "ru": "📄 <b>Заявка:</b>"},
    "empty_title": {
        "uz": "🛜 <b>SmartService Arizalari</b>",
        "ru": "🛜 <b>Заявки SmartService</b>",
    },
    "empty_body": {"uz": "Hozircha arizalar yo'q.", "ru": "Заявок пока нет."},
    "prev": {"uz": "⬅️ Oldingi", "ru": "⬅️ Назад"},
    "next": {"uz": "Keyingi ➡️", "ru": "Вперёд ➡️"},
    "close": {"uz": "❌ Yopish", "ru": "❌ Закрыть"},
    "closed_toast": {"uz": "Yopildi", "ru": "Закрыто"},
}

# Kategoriya nomlari — ikki tilda
CATEGORY_NAMES = {
    "aqlli_avtomatlashtirilgan_xizmatlar": {
        "uz": "🏠 Aqlli uy va avtomatlashtirilgan xizmatlar",
        "ru": "🏠 Умный дом и автоматизированные сервисы",
    },
    "xavfsizlik_kuzatuv_tizimlari": {
        "uz": "🔒 Xavfsizlik va kuzatuv tizimlari",
        "ru": "🔒 Системы безопасности и видеонаблюдения",
    },
    "internet_tarmoq_xizmatlari": {
        "uz": "🌐 Internet va tarmoq xizmatlari",
        "ru": "🌐 Интернет и сетевые услуги",
    },
    "energiya_yashil_texnologiyalar": {
        "uz": "⚡ Energiya va yashil texnologiyalar",
        "ru": "⚡ Энергетика и зелёные технологии",
    },
    "multimediya_aloqa_tizimlari": {
        "uz": "📺 Multimediya va aloqa tizimlari",
        "ru": "📺 Мультимедиа и коммуникации",
    },
    "maxsus_qoshimcha_xizmatlar": {
        "uz": "🔧 Maxsus va qo'shimcha xizmatlar",
        "ru": "🔧 Специальные и дополнительные услуги",
    },
}

# -----------------------------
# 🔧 Util funksiyalar
# -----------------------------
def normalize_lang(value: str | None) -> str:
    """DB qiymatini barqaror 'uz' yoki 'ru' ga keltiradi."""
    if not value:
        return "uz"
    v = value.strip().lower()
    if v in {"ru", "rus", "russian", "ru-ru", "ru_ru"}:
        return "ru"
    if v in {"uz", "uzb", "uzbek", "o'z", "oz", "uz-uz", "uz_uz"}:
        return "uz"
    return "uz"

def t(lang: str, key: str) -> str:
    """Tarjima helperi."""
    lang = normalize_lang(lang)
    return T.get(key, {}).get(lang, T.get(key, {}).get("uz", key))

def cat_name(lang: str, code: str) -> str:
    """Kategoriya kodini (uz/ru) nomiga aylantirish; topilmasa, kodni chiroyli formatlaydi."""
    lang = normalize_lang(lang)
    data = CATEGORY_NAMES.get(code)
    if data:
        return data.get(lang) or data.get("uz")
    # fallback: kod -> Title Case
    return (code or "-").replace("_", " ").title()

def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")

def esc(v) -> str:
    if v is None:
        return "-"
    return html.escape(str(v), quote=False)

async def _lang_from_db(telegram_id: int) -> str:
    """Foydalanuvchi tilini DB’dan oladi; bo‘lmasa 'uz'."""
    user = await get_user_by_telegram_id(telegram_id)
    return normalize_lang((user or {}).get("language"))

# -----------------------------
# 🪧 Karta matni + klaviatura
# -----------------------------
def short_view_text(item: dict, index: int, total: int, lang: str) -> str:
    """
    Bitta arizaning karta ko‘rinishini chiqaradi (tilga mos).
    Dinamik maydonlar HTML-escape qilinadi.
    """
    order_id = item["id"]
    # Bazadan application_number ni olamiz
    application_number = item.get("application_number")
    if application_number:
        formatted_order_id = application_number
    else:
        # Fallback: agar application_number yo'q bo'lsa, oddiy ID
        formatted_order_id = str(order_id)
    category = cat_name(lang, item.get("category") or "-")

    # Xizmat nomlarini bazadan ru/uzga alohida tarjima qilmasak,
    # hech bo‘lmaganda kodni chiroyli formatlaymiz.
    service_raw = item.get("service_type", "-") or "-"
    service_name = service_raw.replace("_", " ").title()

    created = item.get("created_at")
    created_dt = datetime.fromisoformat(created) if isinstance(created, str) else created

    full_name = esc(item.get("full_name", "-"))
    phone = esc(item.get("phone", "-"))
    username = esc(item.get("username", ""))  # @username uchun escape ham qildik
    address = esc(item.get("address", "-"))

    username_text = f"\n{t(lang,'username')} @{username}" if username else ""

    # GPS havola (raqamlar bo'lgani uchun escape shart emas)
    location_text = ""
    if item.get("latitude") and item.get("longitude"):
        lat = item["latitude"]
        lon = item["longitude"]
        location_text = f"\n{t(lang,'gps')} https://maps.google.com/?q={lat},{lon}"

    return (
        f"{t(lang,'title')}\n\n"
        f"{t(lang,'order')} {esc(formatted_order_id)}\n"
        f"{t(lang,'category')} {esc(category)}\n"
        f"{t(lang,'service')} {esc(service_name)}\n"
        f"{t(lang,'client')} {full_name}\n"
        f"{t(lang,'phone')} {phone}{username_text}\n"
        f"{t(lang,'address')} {address}{location_text}\n"
        f"{t(lang,'date')} {fmt_dt(created_dt)}\n"
        f"{t(lang,'item_idx')} {index + 1}/{total}"
    )

def nav_keyboard(index: int, total: int, lang: str) -> InlineKeyboardMarkup:
    """
    Navigatsiya klaviaturasi (Oldingi/Keyingi/Yopish) — tilga mos.
    """
    rows = []
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text=t(lang, "prev"), callback_data=f"smart_prev_{index}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text=t(lang, "next"), callback_data=f"smart_next_{index}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=t(lang, "close"), callback_data="smart_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# -----------------------------
# 📨 Kirish (reply button)
# -----------------------------
@router.message(F.text.in_(["🛜 SmartService arizalari", "🛜 SmartService заявки"]))
async def open_smart_service_orders(message: Message, state: FSMContext):
    """
    Manager uchun SmartService arizalarini ochish:
      - user.language’ni DB’dan oladi;
      - 50 ta yozuvni yuklaydi;
      - karta + navi klaviatura (UZ/RU).
    """
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.get("role") != "manager":
        return

    lang = normalize_lang(user.get("language"))
    items = await fetch_smart_service_orders(limit=50, offset=0)

    if not items:
        await message.answer(
            f"{t(lang,'empty_title')}\n\n{t(lang,'empty_body')}",
            parse_mode="HTML",
            reply_markup=get_manager_main_menu(lang)  # 🔑 menu ham tilga mos
        )
        return

    await state.update_data(smart_orders=items, idx=0)
    total = len(items)
    text = short_view_text(items[0], index=0, total=total, lang=lang)
    kb = nav_keyboard(0, total, lang)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# -----------------------------
# ⬅️ Oldingi / ➡️ Keyingi
#  (har safar tilni DB’dan yangidan olamiz — user tilni o‘zgartirsa ham darhol aks etadi)
# -----------------------------
@router.callback_query(F.data.startswith("smart_prev_"))
async def prev_smart_order(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    lang = await _lang_from_db(cb.from_user.id)

    data = await state.get_data()
    items = data.get("smart_orders", []) or []
    total = len(items)
    idx = int(cb.data.replace("smart_prev_", "")) - 1

    if idx < 0 or idx >= total:
        return

    await state.update_data(idx=idx)
    text = short_view_text(items[idx], index=idx, total=total, lang=lang)
    kb = nav_keyboard(idx, total, lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("smart_next_"))
async def next_smart_order(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    lang = await _lang_from_db(cb.from_user.id)

    data = await state.get_data()
    items = data.get("smart_orders", []) or []
    total = len(items)
    idx = int(cb.data.replace("smart_next_", "")) + 1

    if idx < 0 or idx >= total:
        return

    await state.update_data(idx=idx)
    text = short_view_text(items[idx], index=idx, total=total, lang=lang)
    kb = nav_keyboard(idx, total, lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# -----------------------------
# ❌ Yopish
# -----------------------------
@router.callback_query(F.data == "smart_close")
async def smart_close(cb: CallbackQuery, state: FSMContext):
    lang = await _lang_from_db(cb.from_user.id)
    await cb.answer(t(lang, "closed_toast"))
    try:
        await cb.message.delete()  # matn + tugmalarni o'chiradi
    except TelegramBadRequest:
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
    # ixtiyoriy: state tozalash
    await state.update_data(smart_orders=None, idx=None)

# (ixtiyoriy) Agar ro‘yxatga qaytish tugmasi bo‘lsa foydalanish mumkin
@router.callback_query(F.data.startswith("smart_back_"))
async def back_to_smart_list(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    lang = await _lang_from_db(cb.from_user.id)

    data = await state.get_data()
    items = data.get("smart_orders", []) or []
    idx = data.get("idx", 0) or 0

    if not items:
        await cb.message.edit_text(f"{t(lang,'empty_title')}\n\n{t(lang,'empty_body')}", parse_mode="HTML")
        return

    total = len(items)
    text = short_view_text(items[idx], index=idx, total=total, lang=lang)
    kb = nav_keyboard(idx, total, lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
