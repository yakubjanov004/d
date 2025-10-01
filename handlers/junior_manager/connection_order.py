# handlers/junior_manager/connection_order_jm.py

from datetime import datetime
import re
import logging
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import html

# === Keyboards (i18n) ===
from keyboards.junior_manager_buttons import (
    get_junior_manager_main_menu,            # lang qo'llab-quvvatlaydi
    zayavka_type_keyboard,                   # lang qo'llab-quvvatlaydi (UZ/RU)
    get_client_regions_keyboard,             # lang param bor
    confirmation_keyboard,                   # lang qo'llab-quvvatlaydi (UZ/RU)
    get_operator_tariff_selection_keyboard,  # hozircha UZ-only callback: op_tariff_*
)

# === States ===
from states.junior_manager_states import SaffConnectionOrderStates

# === DB functions ===
# !!! Import yo'lini loyihangizga moslang (oldin "conection" deb yozilgan bo'lishi mumkin).
from database.junior_manager_conection_queries import (
    find_user_by_phone,
    saff_orders_create,
    get_or_create_tarif_by_code,
)
from database.client_queries import ensure_user

# 🔑 Foydalanuvchi tilini olish (users jadvalidan)
# Importni loyihangizga moslang:
from database.jm_inbox_queries import db_get_user_by_telegram_id

# === Role filter ===
from filters.role_filter import RoleFilter

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(RoleFilter("junior_manager"))
router.callback_query.filter(RoleFilter("junior_manager"))

# -------------------------------------------------------
# 🔤 Tarjima lug'ati (UZ/RU) + helpers
# -------------------------------------------------------
T = {
    "entry_uz": "🔌 Ulanish arizasi yaratish",
    "entry_ru": "🔌 Создать заявку",

    "phone_prompt": {
        "uz": "📞 Mijoz telefon raqamini kiriting (masalan, +998901234567):",
        "ru": "📞 Введите номер телефона клиента (например, +998901234567):",
    },
    "phone_bad_format": {
        "uz": "❗️ Noto'g'ri format. Masalan: +998901234567",
        "ru": "❗️ Неверный формат. Например: +998901234567",
    },
    "user_not_found": {
        "uz": "❌ Bu raqam bo'yicha foydalanuvchi topilmadi. To'g'ri raqam yuboring.",
        "ru": "❌ Клиент с таким номером не найден. Отправьте корректный номер.",
    },
    "client_found": {
        "uz": "👤 Mijoz topildi:",
        "ru": "👤 Клиент найден:",
    },
    "continue": {"uz": "Davom etish ▶️", "ru": "Продолжить ▶️"},
    "back": {"uz": "🔙 Orqaga", "ru": "🔙 Назад"},
    "back_to_phone_notice": {
        "uz": "Telefon bosqichiga qaytdik",
        "ru": "Вернулись к вводу телефона",
    },

    "choose_region": {
        "uz": "🌍 Regionni tanlang:",
        "ru": "🌍 Выберите регион:",
    },
    "choose_conn_type": {
        "uz": "🔌 Ulanish turini tanlang:",
        "ru": "🔌 Выберите тип подключения:",
    },
    "choose_tariff": {
        "uz": "📋 <b>Tariflardan birini tanlang:</b>",
        "ru": "📋 <b>Выберите один из тарифов:</b>",
    },
    "enter_address": {
        "uz": "🏠 Manzilingizni kiriting:",
        "ru": "🏠 Введите адрес:",
    },
    "address_required": {
        "uz": "❗️ Iltimos, manzilni kiriting.",
        "ru": "❗️ Пожалуйста, введите адрес.",
    },

    "summary_region": {"uz": "🗺️ <b>Hudud:</b>", "ru": "🗺️ <b>Регион:</b>"},
    "summary_type":   {"uz": "🔌 <b>Ulanish turi:</b>", "ru": "🔌 <b>Тип подключения:</b>"},
    "summary_tariff": {"uz": "💳 <b>Tarif:</b>", "ru": "💳 <b>Тариф:</b>"},
    "summary_addr":   {"uz": "🏠 <b>Manzil:</b>", "ru": "🏠 <b>Адрес:</b>"},
    "summary_ok":     {"uz": "Ma'lumotlar to‘g‘rimi?", "ru": "Данные верны?"},

    "no_client": {"uz": "Mijoz tanlanmagan", "ru": "Клиент не выбран"},
    "error_generic": {"uz": "Xatolik yuz berdi", "ru": "Произошла ошибка"},
    "resend_restart": {"uz": "🔄 Qaytadan boshladik", "ru": "🔄 Начали заново"},

    "ok_created_title": {
        "uz": "✅ <b>Ariza yaratildi (mijoz nomidan)</b>",
        "ru": "✅ <b>Заявка создана (от имени клиента)</b>",
    },
    "lbl_req_id": {"uz": "🆔 Ariza raqami:", "ru": "🆔 Номер заявки:"},
    "lbl_region": {"uz": "📍 Region:", "ru": "📍 Регион:"},
    "lbl_tariff": {"uz": "💳 Tarif:", "ru": "💳 Тариф:"},
    "lbl_phone":  {"uz": "📞 Tel:", "ru": "📞 Телефон:"},
    "lbl_addr":   {"uz": "🏠 Manzil:", "ru": "🏠 Адрес:"},
}

def normalize_lang(v: str | None) -> str:
    if not v:
        return "uz"
    s = v.strip().lower()
    if s in {"ru", "rus", "russian", "ru-ru", "ru_ru"}:
        return "ru"
    if s in {"uz", "uzb", "uzbek", "uz-uz", "uz_uz", "o'z", "oz"}:
        return "uz"
    return "uz"

def t(lang: str, key: str) -> str:
    lang = normalize_lang(lang)
    val = T.get(key)
    if isinstance(val, dict):
        return val.get(lang, val.get("uz", key))
    return val

def esc(x: str | None) -> str:
    return html.escape(x or "-", quote=False)

def conn_type_display(lang: str, ctype: str | None) -> str:
    lang = normalize_lang(lang)
    key = (ctype or "b2c").lower()
    if lang == "ru":
        return "Физическое лицо" if key == "b2c" else "Юридическое лицо"
    return "Jismoniy shaxs" if key == "b2c" else "Yuridik shaxs"

REGION_CODE_TO_ID: dict[str, int] = {
    "toshkent_city": 1,
    "toshkent_region": 2,
    "andijon": 3,
    "fergana": 4,
    "namangan": 5,
    "sirdaryo": 6,
    "jizzax": 7,
    "samarkand": 8,
    "bukhara": 9,
    "navoi": 10,
    "kashkadarya": 11,
    "surkhandarya": 12,
    "khorezm": 13,
    "karakalpakstan": 14,
}
REGION_CODE_TO_NAME = {
    "uz": {
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
    },
    "ru": {
        "toshkent_city": "г. Ташкент",
        "toshkent_region": "Ташкентская область",
        "andijon": "Андижан",
        "fergana": "Фергана",
        "namangan": "Наманган",
        "sirdaryo": "Сырдарья",
        "jizzax": "Джизак",
        "samarkand": "Самарканд",
        "bukhara": "Бухара",
        "navoi": "Навои",
        "kashkadarya": "Кашкадарья",
        "surkhandarya": "Сурхандарья",
        "khorezm": "Хорезм",
        "karakalpakstan": "Каракалпакстан",
    }
}
def map_region_code_to_id(region_code: str | None) -> int | None:
    return REGION_CODE_TO_ID.get((region_code or "").lower()) if region_code else None
def region_display(lang: str, region_code: str | None) -> str:
    lang = normalize_lang(lang)
    return REGION_CODE_TO_NAME.get(lang, {}).get(region_code or "", region_code or "-")

TARIFF_DISPLAY = {
    "uz": {
        "tariff_xammasi_birga_4": "Hammasi birga 4",
        "tariff_xammasi_birga_3_plus": "Hammasi birga 3+",
        "tariff_xammasi_birga_3": "Hammasi birga 3",
        "tariff_xammasi_birga_2": "Hammasi birga 2",
    },
    "ru": {
        "tariff_xammasi_birga_4": "Всё вместе 4",
        "tariff_xammasi_birga_3_plus": "Всё вместе 3+",
        "tariff_xammasi_birga_3": "Всё вместе 3",
        "tariff_xammasi_birga_2": "Всё вместе 2",
    }
}
def tariff_display(lang: str, code: str | None) -> str:
    lang = normalize_lang(lang)
    if not code:
        return "-"
    return TARIFF_DISPLAY.get(lang, {}).get(code, code)

# -------------------------------------------------------
# 🔧 Telefon raqam normalizatsiyasi
# -------------------------------------------------------
PHONE_RE = re.compile(r"^\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}$|^\+?998\d{9}$|^\d{9,12}$")

def normalize_phone(phone_raw: str) -> str | None:
    phone_raw = (phone_raw or "").strip()
    if not PHONE_RE.match(phone_raw):
        return None
    digits = re.sub(r"\D", "", phone_raw)
    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 9:
        return "+998" + digits
    return phone_raw if phone_raw.startswith("+") else ("+" + digits if digits else None)

def strip_op_prefix_to_tariff(code: str | None) -> str | None:
    if not code:
        return None
    return "tariff_" + code[len("op_tariff_"):] if code.startswith("op_tariff_") else code

def back_to_phone_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "back"), callback_data="jm_conn_back_to_phone")]]
    )

# ======================= ENTRY (reply buttons) =======================
# ❗️ Triggerlarni tugmalarga aynan mos qilib qo'ydik
ENTRY_TEXTS_CONN = [
    "🔌 Ulanish arizasi yaratish",  # UZ tugma
    "🔌 Создать заявку",            # RU tugma
]

# ======================= ENTRY (reply buttons) =======================
@router.message(F.text.in_(ENTRY_TEXTS_CONN))
async def jm_start_text(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SaffConnectionOrderStates.waiting_client_phone)

    u = await db_get_user_by_telegram_id(msg.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    await msg.answer(
        t(lang, "phone_prompt"),
        reply_markup=ReplyKeyboardRemove(),
    )

# ======================= STEP 1: phone lookup =======================
@router.message(StateFilter(SaffConnectionOrderStates.waiting_client_phone))
async def jm_get_phone(msg: Message, state: FSMContext):
    u = await db_get_user_by_telegram_id(msg.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    phone_n = normalize_phone(msg.text)
    if not phone_n:
        return await msg.answer(
            t(lang, "phone_bad_format"),
            reply_markup=back_to_phone_kb(lang)
        )

    client = await find_user_by_phone(phone_n)
    if not client:
        return await msg.answer(
            t(lang, "user_not_found"),
            reply_markup=back_to_phone_kb(lang)
        )

    await state.update_data(acting_client=client)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "continue"), callback_data="jm_conn_continue"),
            InlineKeyboardButton(text=t(lang, "back"),     callback_data="jm_conn_back_to_phone"),
        ]
    ])
    text = (
        f"{t(lang,'client_found')}\n"
        f"• ID: <b>{esc(str(client.get('id','')))}</b>\n"
        f"• F.I.Sh: <b>{esc(client.get('full_name',''))}</b>\n"
        f"• Tel: <b>{esc(client.get('phone',''))}</b>\n\n"
        f"{t(lang,'continue')} / {t(lang,'back')}"
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=kb)

# === Orqaga: telefon bosqichiga qaytarish
@router.callback_query(F.data == "jm_conn_back_to_phone")
async def jm_back_to_phone(cq: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(cq.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    await cq.answer(t(lang, "back_to_phone_notice"))
    try:
        await cq.message.edit_reply_markup()
    except Exception:
        pass
    # acting_client ni ham tozalaymiz — toza boshlash uchun
    await state.clear()
    await state.set_state(SaffConnectionOrderStates.waiting_client_phone)
    await cq.message.answer(
        t(lang, "phone_prompt"),
        reply_markup=ReplyKeyboardRemove(),
    )

# ======================= STEP 2: region =======================
@router.callback_query(StateFilter(SaffConnectionOrderStates.waiting_client_phone), F.data == "jm_conn_continue")
async def jm_after_confirm_user(cq: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(cq.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    await cq.message.edit_reply_markup()
    await cq.message.answer(t(lang, "choose_region"), reply_markup=get_client_regions_keyboard(lang=lang))
    await state.set_state(SaffConnectionOrderStates.selecting_region)
    await cq.answer()

@router.callback_query(F.data.startswith("region_"), StateFilter(SaffConnectionOrderStates.selecting_region))
async def jm_select_region(callback: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(callback.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    await callback.answer()
    await callback.message.edit_reply_markup()

    region_code = callback.data.replace("region_", "", 1)
    await state.update_data(selected_region=region_code)

    await callback.message.answer(t(lang, "choose_conn_type"), reply_markup=zayavka_type_keyboard(lang))
    await state.set_state(SaffConnectionOrderStates.selecting_connection_type)

# ======================= STEP 3: connection type =======================
@router.callback_query(F.data.startswith("zayavka_type_"), StateFilter(SaffConnectionOrderStates.selecting_connection_type))
async def jm_select_connection_type(callback: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(callback.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    await callback.answer()
    await callback.message.edit_reply_markup()

    connection_type = callback.data.split("_")[-1]  # 'b2c' or 'b2b'
    await state.update_data(connection_type=connection_type)

    await callback.message.answer(
        t(lang, "choose_tariff"),
        reply_markup=get_operator_tariff_selection_keyboard(),  # op_tariff_* callbacks
        parse_mode="HTML",
    )
    await state.set_state(SaffConnectionOrderStates.selecting_tariff)

# ======================= STEP 4: tariff =======================
@router.callback_query(StateFilter(SaffConnectionOrderStates.selecting_tariff), F.data.startswith("op_tariff_"))
async def jm_select_tariff(callback: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(callback.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    await callback.answer()
    await callback.message.edit_reply_markup()

    normalized_code = strip_op_prefix_to_tariff(callback.data)
    await state.update_data(selected_tariff=normalized_code)

    await callback.message.answer(t(lang, "enter_address"))
    await state.set_state(SaffConnectionOrderStates.entering_address)

# ======================= STEP 5: address =======================
@router.message(StateFilter(SaffConnectionOrderStates.entering_address))
async def jm_get_address(msg: Message, state: FSMContext):
    u = await db_get_user_by_telegram_id(msg.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    address = (msg.text or "").strip()
    if not address:
        return await msg.answer(t(lang, "address_required"))
    await state.update_data(address=address)
    await jm_show_summary(msg, state)

# ======================= STEP 6: summary =======================
async def jm_show_summary(target, state: FSMContext):
    u = await db_get_user_by_telegram_id(target.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    data = await state.get_data()
    region_code = data.get("selected_region", "-")
    ctype = (data.get("connection_type") or "b2c")
    tariff_code = data.get("selected_tariff")
    address = data.get("address", "-")

    text = (
        f"{t(lang,'summary_region')} {region_display(lang, region_code)}\n"
        f"{t(lang,'summary_type')} {conn_type_display(lang, ctype)}\n"
        f"{t(lang,'summary_tariff')} {esc(tariff_display(lang, tariff_code))}\n"
        f"{t(lang,'summary_addr')} {esc(address)}\n\n"
        f"{t(lang,'summary_ok')}"
    )

    kb = confirmation_keyboard(lang)
    if hasattr(target, "answer"):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.message.answer(text, parse_mode="HTML", reply_markup=kb)

    await state.set_state(SaffConnectionOrderStates.confirming_connection)

# ======================= STEP 7: confirm / resend =======================
@router.callback_query(F.data == "confirm_zayavka_call_center", StateFilter(SaffConnectionOrderStates.confirming_connection))
async def jm_confirm(callback: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(callback.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    try:
        await callback.message.edit_reply_markup()
        data = await state.get_data()

        acting_client = data.get("acting_client")
        if not acting_client:
            return await callback.answer(t(lang, "no_client"), show_alert=True)

        # Yaratayotgan JM foydalanuvchi (DB dagi id)
        user_row = await ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
        jm_user_id = user_row["id"]

        client_user_id = acting_client["id"]

        region_code = (data.get("selected_region") or "toshkent_city").lower()
        region_id = map_region_code_to_id(region_code)
        if region_id is None:
            raise ValueError(f"Unknown region code: {region_code}")

        tariff_code = data.get("selected_tariff")  # tariff_* bo'lib keladi
        tarif_id = await get_or_create_tarif_by_code(tariff_code) if tariff_code else None

        request_id = await saff_orders_create(
            user_id=jm_user_id,
            phone=acting_client.get("phone"),
            abonent_id=str(client_user_id),
            region=region_id,
            address=data.get("address", "Kiritilmagan" if lang == "uz" else "Не указан"),
            tarif_id=tarif_id,
            # Eslatma: agar sizda saff_orders_create ichida status 'in_controller' bo'lsa,
            # ccs_* querylaringizni ham shunga moslang. Aks holda bu yerda next statusni
            # parametr sifatida qo'shish tavsiya etiladi.
        )

        await callback.message.answer(
            (
                f"{t(lang,'ok_created_title')}\n\n"
                f"{t(lang,'lbl_req_id')} <code>{request_id}</code>\n"
                f"{t(lang,'lbl_region')} {region_display(lang, region_code)}\n"
                f"{t(lang,'lbl_tariff')} {esc(tariff_display(lang, tariff_code))}\n"
                f"{t(lang,'lbl_phone')} {esc(acting_client.get('phone','-'))}\n"
                f"{t(lang,'lbl_addr')} {esc(data.get('address','-'))}\n"
            ),
            reply_markup=get_junior_manager_main_menu(lang),
            parse_mode="HTML",
        )
        await state.clear()
    except Exception as e:
        logger.exception("JM confirm error: %s", e)
        await callback.answer(t(lang, "error_generic"), show_alert=True)

@router.callback_query(F.data == "resend_zayavka_call_center", StateFilter(SaffConnectionOrderStates.confirming_connection))
async def jm_resend(callback: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(callback.from_user.id)
    lang = normalize_lang(u.get("language") if u else "uz")

    await callback.answer(t(lang, "resend_restart"))
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass

    data = await state.get_data()
    acting_client = data.get("acting_client")
    await state.clear()
    if acting_client:
        await state.update_data(acting_client=acting_client)

    await state.set_state(SaffConnectionOrderStates.selecting_region)
    await callback.message.answer(t(lang, "choose_region"), reply_markup=get_client_regions_keyboard(lang=lang))
