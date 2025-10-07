# handlers/call_center/connection_order_cc.py

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

# === Keyboards ===
from keyboards.call_center_supervisor_buttons import (
    get_call_center_supervisor_main_menu,
    zayavka_type_keyboard,                # connection type (b2c/b2b)
    get_client_regions_keyboard,          # region selector
    confirmation_keyboard,                # confirm/resend (confirm_zayavka_call_center / resend_zayavka_call_center)
    get_operator_tariff_selection_keyboard,
)

# === States ===
from states.call_center_states import staffConnectionOrderStates

# === DB ===
from database.call_center_supervisor.orders import (
    find_user_by_phone,
    staff_orders_create,
    get_or_create_tarif_by_code,
)
from database.basic.user import ensure_user
from database.basic.language import get_user_language   # til

# === Role filter ===
from filters.role_filter import RoleFilter

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(RoleFilter("callcenter_supervisor"))
router.callback_query.filter(RoleFilter("callcenter_supervisor"))

# ----------------------- helpers -----------------------
PHONE_RE = re.compile(r"^\+998\d{9}$")

def normalize_phone(phone_raw: str) -> str | None:
    phone_raw = (phone_raw or "").strip()
    digits = re.sub(r"\D", "", phone_raw)
    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 9:
        return "+998" + digits
    return phone_raw if phone_raw.startswith("+998") and len(digits) == 12 else None

def strip_op_prefix_to_tariff(code: str | None) -> str | None:
    return "tariff_" + code[len("op_tariff_"):] if code and code.startswith("op_tariff_") else code

REGION_CODE_TO_ID: dict[str, int] = {
    "toshkent_city": 1, "toshkent_region": 2, "andijon": 3, "fergana": 4, "namangan": 5,
    "sirdaryo": 6, "jizzax": 7, "samarkand": 8, "bukhara": 9, "navoi": 10,
    "kashkadarya": 11, "surkhandarya": 12, "khorezm": 13, "karakalpakstan": 14,
}

def map_region_code_to_id(region_code: str | None) -> int | None:
    return REGION_CODE_TO_ID.get(region_code) if region_code else None

def back_to_phone_kb(lang: str) -> InlineKeyboardMarkup:
    """Tilga mos 'Orqaga/Назад' tugmasi — telefon bosqichiga qaytaradi."""
    label = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data="op_conn_back_to_phone")]]
    )

# ======================= ENTRY =======================
@router.message(F.text.in_(["🔌 Ulanish arizasi yaratish", "🔌 Создать заявку на подключение"]))
async def op_start_text(msg: Message, state: FSMContext):
    await state.clear()
    lang = await get_user_language(msg.from_user.id) or "uz"
    text = (
        "📞 Mijoz telefon raqamini kiriting (masalan, +998901234567):"
        if lang == "uz" else
        "📞 Введите номер телефона клиента (например: +998901234567):"
    )
    await state.set_state(staffConnectionOrderStates.waiting_client_phone)
    await msg.answer(text, reply_markup=ReplyKeyboardRemove())

# ======================= STEP 1: phone lookup =======================
@router.message(StateFilter(staffConnectionOrderStates.waiting_client_phone))
async def op_get_phone(msg: Message, state: FSMContext):
    lang = await get_user_language(msg.from_user.id) or "uz"

    phone_n = normalize_phone(msg.text)
    if not phone_n:
        return await msg.answer(
            "❗️ Noto'g'ri format. Masalan: +998901234567" if lang == "uz"
            else "❗️ Неверный формат. Например: +998901234567",
            reply_markup=back_to_phone_kb(lang)
        )

    user = await find_user_by_phone(phone_n)
    if not user:
        return await msg.answer(
            "❌ Bu raqam bo'yicha foydalanuvchi topilmadi." if lang == "uz"
            else "❌ Пользователь с таким номером не найден.",
            reply_markup=back_to_phone_kb(lang)
        )

    await state.update_data(acting_client=user)

    # Davom etish + Orqaga yonma-yon
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Davom etish ▶️" if lang == "uz" else "Продолжить ▶️",
                callback_data="op_conn_continue"
            ),
            InlineKeyboardButton(
                text="🔙 Orqaga" if lang == "uz" else "🔙 Назад",
                callback_data="op_conn_back_to_phone"
            ),
        ]]
    )
    text = (
        "👤 Mijoz topildi:\n"
        f"• ID: <b>{user.get('id','')}</b>\n"
        f"• F.I.Sh: <b>{user.get('full_name','')}</b>\n"
        f"• Tel: <b>{user.get('phone','')}</b>\n\n"
        "Davom etish yoki orqaga qaytishni tanlang."
        if lang == "uz" else
        "👤 Клиент найден:\n"
        f"• ID: <b>{user.get('id','')}</b>\n"
        f"• ФИО: <b>{user.get('full_name','')}</b>\n"
        f"• Тел: <b>{user.get('phone','')}</b>\n\n"
        "Выберите: продолжить или вернуться назад."
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=kb)

# 🔙 Orqaga — har qayerdan telefon kiritishga qaytarish
@router.callback_query(F.data == "op_conn_back_to_phone")
async def op_back_to_phone(cq: CallbackQuery, state: FSMContext):
    lang = await get_user_language(cq.from_user.id) or "uz"
    await cq.answer("Telefon bosqichiga qaytdik" if lang == "uz" else "Вернулись к вводу телефона")
    try:
        await cq.message.edit_reply_markup()
    except Exception:
        pass
    await state.clear()
    await state.set_state(staffConnectionOrderStates.waiting_client_phone)
    await cq.message.answer(
        "📞 Mijoz telefon raqamini kiriting (masalan, +998901234567):"
        if lang == "uz" else
        "📞 Введите номер телефона клиента (например: +998901234567):",
        reply_markup=ReplyKeyboardRemove()
    )

# ======================= STEP 2: region =======================
@router.callback_query(StateFilter(staffConnectionOrderStates.waiting_client_phone), F.data == "op_conn_continue")
async def op_after_confirm_user(cq: CallbackQuery, state: FSMContext):
    lang = await get_user_language(cq.from_user.id) or "uz"
    await cq.message.edit_reply_markup()
    text = "🌍 Regionni tanlang:" if lang == "uz" else "🌍 Выберите регион:"
    await cq.message.answer(text, reply_markup=get_client_regions_keyboard())
    await state.set_state(staffConnectionOrderStates.selecting_region)
    await cq.answer()

# ======================= STEP 3: connection type =======================
@router.callback_query(F.data.startswith("region_"), StateFilter(staffConnectionOrderStates.selecting_region))
async def op_select_region(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    await callback.answer()
    await callback.message.edit_reply_markup()

    region_code = callback.data.replace("region_", "", 1)
    await state.update_data(selected_region=region_code)

    text = "🔌 Ulanish turini tanlang:" if lang == "uz" else "🔌 Выберите тип подключения:"
    await callback.message.answer(text, reply_markup=zayavka_type_keyboard())
    await state.set_state(staffConnectionOrderStates.selecting_connection_type)

# ======================= STEP 4: connection type -> tariff =======================
@router.callback_query(F.data.startswith("zayavka_type_"), StateFilter(staffConnectionOrderStates.selecting_connection_type))
async def op_select_connection_type(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    await callback.answer()
    await callback.message.edit_reply_markup()

    connection_type = callback.data.split("_")[-1]  # 'b2c' or 'b2b'
    await state.update_data(connection_type=connection_type)

    text = "📋 Tariflardan birini tanlang:" if lang == "uz" else "📋 Выберите один из тарифов:"
    await callback.message.answer(text, reply_markup=get_operator_tariff_selection_keyboard(), parse_mode="HTML")
    await state.set_state(staffConnectionOrderStates.selecting_tariff)

# ======================= STEP 5: tariff -> address =======================
@router.callback_query(StateFilter(staffConnectionOrderStates.selecting_tariff), F.data.startswith("op_tariff_"))
async def op_select_tariff(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    await callback.answer()
    await callback.message.edit_reply_markup()

    normalized_code = strip_op_prefix_to_tariff(callback.data)
    await state.update_data(selected_tariff=normalized_code)

    await callback.message.answer("🏠 Manzilni kiriting:" if lang == "uz" else "🏠 Введите адрес:")
    await state.set_state(staffConnectionOrderStates.entering_address)

# ======================= STEP 6: address -> summary =======================
@router.message(StateFilter(staffConnectionOrderStates.entering_address))
async def op_get_address(msg: Message, state: FSMContext):
    lang = await get_user_language(msg.from_user.id) or "uz"
    address = (msg.text or "").strip()
    if not address:
        return await msg.answer("❗️ Iltimos, manzilni kiriting." if lang == "uz" else "❗️ Пожалуйста, укажите адрес.")
    await state.update_data(address=address)
    await op_show_summary(msg, state)

async def op_show_summary(target, state: FSMContext):
    """Localized summary with confirm/resend buttons."""
    # langni targetdan olamiz
    uid = target.from_user.id if hasattr(target, "from_user") else target.message.from_user.id
    lang = await get_user_language(uid) or "uz"

    data = await state.get_data()
    region = (data.get("selected_region") or "-").replace("_", " ").title()
    ctype = (data.get("connection_type") or "b2c").upper()
    tariff_code = data.get("selected_tariff") or "-"
    address = data.get("address", "-")

    text = (
        f"🗺️ <b>Hudud:</b> {region}\n"
        f"🔌 <b>Ulanish turi:</b> {ctype}\n"
        f"💳 <b>Tarif:</b> {tariff_code}\n"
        f"🏠 <b>Manzil:</b> {address}\n\n"
        "Ma'lumotlar to‘g‘rimi?"
        if lang == "uz" else
        f"🗺️ <b>Регион:</b> {region}\n"
        f"🔌 <b>Тип подключения:</b> {ctype}\n"
        f"💳 <b>Тариф:</b> {tariff_code}\n"
        f"🏠 <b>Адрес:</b> {address}\n\n"
        "Всё верно?"
    )

    kb = confirmation_keyboard(lang=lang)  # agar funksiyada lang param. yo'q bo'lsa, oddiy chaqiring
    if hasattr(target, "answer"):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.message.answer(text, parse_mode="HTML", reply_markup=kb)

    await state.set_state(staffConnectionOrderStates.confirming_connection)

# ======================= STEP 7: confirm / resend =======================
@router.callback_query(F.data == "confirm_zayavka_call_center", StateFilter(staffConnectionOrderStates.confirming_connection))
async def op_confirm(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    try:
        await callback.message.edit_reply_markup()
        data = await state.get_data()

        acting_client = data.get("acting_client")
        if not acting_client:
            return await callback.answer("Mijoz tanlanmagan" if lang == "uz" else "Клиент не выбран", show_alert=True)

        client_user_id = acting_client["id"]
        user_row = await ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
        user_id = user_row["id"]

        region_code = (data.get("selected_region") or "toshkent_city").lower()
        region_id = map_region_code_to_id(region_code)
        if region_id is None:
            raise ValueError(f"Unknown region code: {region_code}")

        tariff_code = data.get("selected_tariff")
        tarif_id = await get_or_create_tarif_by_code(tariff_code) if tariff_code else None

        request_id = await staff_orders_create(
            user_id=user_id,
            phone=acting_client.get("phone"),
            abonent_id=str(client_user_id) if client_user_id is not None else None,
            region=region_id,
            address=data.get("address", "Kiritilmagan" if lang == "uz" else "Не указан"),
            tarif_id=tarif_id,
        )

        # Guruhga xabar yuborish
        try:
            from loader import bot
            from utils.notification_service import send_group_notification_for_staff_order
            
            tariff_name = tariff_code or None
            region_name = region_code.replace('_', ' ').title()
            
            await send_group_notification_for_staff_order(
                bot=bot,
                order_id=request_id,
                order_type="connection",
                client_name=acting_client.get('full_name', 'Noma\'lum'),
                client_phone=acting_client.get('phone', '-'),
                creator_name=callback.from_user.full_name,
                creator_role='call_center_supervisor',
                region=region_name,
                address=data.get("address", "Kiritilmagan" if lang == "uz" else "Не указан"),
                tariff_name=tariff_name,
                business_type="B2C"
            )
        except Exception as group_error:
            logger.error(f"Failed to send group notification for Call Center Supervisor order: {group_error}")

        done_text = (
            "✅ <b>Ariza yaratildi</b>\n\n"
            f"🆔 Ariza: <code>{request_id}</code>\n"
            f"📍 Region: {region_code.replace('_', ' ').title()}\n"
            f"💳 Tarif: {tariff_code or '-'}\n"
            f"📞 Tel: {acting_client.get('phone','-')}\n"
            f"🏠 Manzil: {data.get('address','-')}\n"
            if lang == "uz" else
            "✅ <b>Заявка создана</b>\n\n"
            f"🆔 Номер: <code>{request_id}</code>\n"
            f"📍 Регион: {region_code.replace('_', ' ').title()}\n"
            f"💳 Тариф: {tariff_code or '-'}\n"
            f"📞 Тел: {acting_client.get('phone','-')}\n"
            f"🏠 Адрес: {data.get('address','-')}\n"
        )

        await callback.message.answer(done_text, parse_mode="HTML", reply_markup=get_call_center_supervisor_main_menu())
        await state.clear()
    except Exception as e:
        logger.exception("Confirm error: %s", e)
        await callback.answer("Xatolik yuz berdi" if lang == "uz" else "Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "resend_zayavka_call_center", StateFilter(staffConnectionOrderStates.confirming_connection))
async def op_resend(callback: CallbackQuery, state: FSMContext):
    """Qayta yuborish: REGION tanlash bosqichidan davom etadi."""
    lang = await get_user_language(callback.from_user.id) or "uz"
    await callback.answer("🔄 Qaytadan boshladik" if lang == "uz" else "🔄 Начали заново")
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass

    data = await state.get_data()
    acting_client = data.get("acting_client")
    await state.clear()
    if acting_client:
        await state.update_data(acting_client=acting_client)

    await state.set_state(staffConnectionOrderStates.selecting_region)
    await callback.message.answer(
        "🌍 Regionni tanlang:" if lang == "uz" else "🌍 Выберите регион:",
        reply_markup=get_client_regions_keyboard()
    )
