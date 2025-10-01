# handlers/junior_manager/client_search.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
import html
import re

from filters.role_filter import RoleFilter
from database.jm_inbox_queries import db_get_user_by_telegram_id
from database.jm_client_search_queries import jm_find_user_by_phone

router = Router()
router.message.filter(RoleFilter("junior_manager"))

# --- State ---
class JMClientSearchStates(StatesGroup):
    waiting_client_phone = State()

# --- i18n helpers ---
def _norm_lang(v: str | None) -> str:
    v = (v or "uz").lower()
    return "ru" if v.startswith("ru") else "uz"

TR = {
    "prompt": {
        "uz": "📞 Qidirish uchun mijoz telefon raqamini kiriting (masalan, +998901234567):",
        "ru": "📞 Введите номер телефона клиента для поиска (например: +998901234567):",
    },
    "bad_format": {
        "uz": "❗️ Noto‘g‘ri format. Masalan: +998901234567",
        "ru": "❗️ Неверный формат. Например: +998901234567",
    },
    "not_found": {
        "uz": "❌ Bu raqam bo‘yicha mijoz topilmadi. Qayta urinib ko‘ring.",
        "ru": "❌ Клиент с таким номером не найден. Попробуйте снова.",
    },
    "found_title": {"uz": "✅ Mijoz topildi:", "ru": "✅ Клиент найден:"},
    "id": {"uz": "🆔 ID", "ru": "🆔 ID"},
    "fio": {"uz": "👤 F.I.Sh", "ru": "👤 ФИО"},
    "phone": {"uz": "📞 Telefon", "ru": "📞 Телефон"},
    "username": {"uz": "🌐 Username", "ru": "🌐 Username"},
    "region": {"uz": "📍 Region", "ru": "📍 Регион"},
    "address": {"uz": "🏠 Manzil", "ru": "🏠 Адрес"},
    "abonent": {"uz": "🔑 Abonent ID", "ru": "🔑 Abonent ID"},
}

def t(lang: str, key: str) -> str:
    lang = _norm_lang(lang)
    val = TR.get(key)
    if isinstance(val, dict):
        return val.get(lang, val.get("uz", key))
    return val or key

def _esc(v) -> str:
    return html.escape(str(v) if v is not None else "-", quote=False)

# --- Local format validator (oddiy feedback uchun) ---
_PHONE_RE = re.compile(
    r"^\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}$|^\+?998\d{9}$|^\d{9,12}$"
)
def _looks_like_phone(raw: str) -> bool:
    return bool(_PHONE_RE.match((raw or "").strip()))

# ===================== ENTRY (reply button) =====================
@router.message(F.text.in_(["🔍 Mijoz qidiruv", "🔍 Поиск клиентов"]))
async def jm_client_search_start(message: Message, state: FSMContext):
    u = await db_get_user_by_telegram_id(message.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")

    await state.set_state(JMClientSearchStates.waiting_client_phone)
    await message.answer(t(lang, "prompt"))

# ===================== STEP: phone input =====================
@router.message(StateFilter(JMClientSearchStates.waiting_client_phone))
async def jm_client_search_process_phone(message: Message, state: FSMContext):
    u = await db_get_user_by_telegram_id(message.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")

    phone = (message.text or "").strip()

    # Avval formatni tekshirib, foydalanuvchiga tezkor javob beramiz
    if not _looks_like_phone(phone):
        await message.answer(t(lang, "bad_format"))
        return

    user = await jm_find_user_by_phone(phone)
    if not user:
        await message.answer(t(lang, "not_found"))
        return

    # Mijoz ma'lumotini chiqaramiz
    text = (
        f"{t(lang,'found_title')}\n\n"
        f"{t(lang,'id')}: <b>{_esc(user.get('id'))}</b>\n"
        f"{t(lang,'fio')}: <b>{_esc(user.get('full_name'))}</b>\n"
        f"{t(lang,'phone')}: <b>{_esc(user.get('phone'))}</b>\n"
        f"{t(lang,'username')}: <b>@{_esc(user.get('username'))}</b>\n"
        f"{t(lang,'region')}: <b>{_esc(user.get('region'))}</b>\n"
        f"{t(lang,'address')}: <b>{_esc(user.get('address'))}</b>\n"
        f"{t(lang,'abonent')}: <b>{_esc(user.get('abonent_id'))}</b>\n"
    )
    await message.answer(text, parse_mode="HTML")

    # Istasangiz state'ni ochiq qoldirib, “yana raqam yuboring” rejimini qo‘yishingiz mumkin.
    # Hozircha tozalaymiz:
    await state.clear()
