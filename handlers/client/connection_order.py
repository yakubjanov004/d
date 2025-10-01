from datetime import datetime
import logging
from aiogram import F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from keyboards.client_buttons import (
    get_client_main_menu,
    zayavka_type_keyboard,
    geolocation_keyboard,
    get_client_tariff_selection_keyboard,
    confirmation_keyboard,
    get_client_regions_keyboard
)
from states.client_states import ConnectionOrderStates
from config import settings
from database.client_queries import (
    ensure_user, get_or_create_tarif_by_code, create_connection_order
)
from database.queries import get_user_language  # 👈 tilni olish
from loader import bot

logger = logging.getLogger(__name__)
router = Router()

# --- Lokalizatsiya helperlari ---
REGION_CODE_TO_UZ: dict = {
    "toshkent_city": "Toshkent shahri",
    "toshkent_region": "Toshkent viloyati",
    "andijon": "Andijon",
    "fergana": "Farg'ona",
    "namangan": "Namangan",
    "sirdaryo": "Sirdaryo",
    "jizzax": "Jizzax",
    "samarkand": "Samarqand",
    "bukhara": "Buxoro",
    "navoi": "Navoiy",
    "kashkadarya": "Qashqadaryo",
    "surkhandarya": "Surxondaryo",
    "khorezm": "Xorazm",
    "karakalpakstan": "Qoraqalpog'iston",
}
REGION_CODE_TO_RU: dict = {
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

def t(lang: str, key: str) -> str:
    uz = {
        "start_title": "🔌 <b>Yangi ulanish arizasi</b>\n\n📍 Qaysi regionda ulanmoqchisiz?",
        "ask_type": "Ulanish turini tanlang:",
        "tariff_caption": "📋 <b>Tariflardan birini tanlang:</b>\n\n",
        "ask_address": "📍 Manzilingizni kiriting:",
        "ask_geo_q": "Geolokatsiya yuborasizmi?",
        "send_geo": "📍 Joylashuvingizni yuboring:",
        "geo_ok": "✅ Joylashuv qabul qilindi!",
        "confirm_title": "Ma'lumotlar to'g'rimi?",
        "confirm_wait": "⏳ Zayavka yaratilmoaqda...",
        "not_found_tariff": "❌ Tanlangan tarif topilmadi. Iltimos, quyidagi ro'yxatdan tarifni qayta tanlang.",
        "success_title": "✅ <b>Arizangiz muvaffaqiyatli qabul qilindi!</b>",
        "will_call": "⏰ Menejerlarimiz tez orada siz bilan bog'lanadi!",
        "main_menu": "Bosh menyu:",
        "start_again": "🔌 <b>Yangi ulanish arizasi</b>\n\n📍 Qaysi regionda ulanmoqchisiz?",
        "err_common": "❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
    }
    ru = {
        "start_title": "🔌 <b>Новая заявка на подключение</b>\n\n📍 В каком регионе хотите подключиться?",
        "ask_type": "Выберите тип подключения:",
        "tariff_caption": "📋 <b>Выберите один из тарифов:</b>\n\n",
        "ask_address": "📍 Введите ваш адрес:",
        "ask_geo_q": "Отправите геолокацию?",
        "send_geo": "📍 Отправьте свою локацию:",
        "geo_ok": "✅ Геолокация получена!",
        "confirm_title": "Данные верны?",
        "confirm_wait": "⏳ Заявка создаётся...",
        "not_found_tariff": "❌ Выбранный тариф не найден. Пожалуйста, выберите тариф заново из списка ниже.",
        "success_title": "✅ <b>Ваша заявка успешно принята!</b>",
        "will_call": "⏰ Наши менеджеры свяжутся с вами в ближайшее время!",
        "main_menu": "Главное меню:",
        "start_again": "🔌 <b>Новая заявка на подключение</b>\n\n📍 В каком регионе хотите подключиться?",
        "err_common": "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз.",
    }
    return (ru if lang == "ru" else uz)[key]

def normalize_region(region_code: str, lang: str) -> str:
    if lang == "ru":
        return REGION_CODE_TO_RU.get(region_code, region_code)
    return REGION_CODE_TO_UZ.get(region_code, region_code)

# --- Tarif ko‘rinish nomlari (UZ/RU)
TARIFF_NAMES = {
    "tariff_xammasi_birga_4": {"uz": "Hammasi birga 4", "ru": "Hammasi birga 4"},
    "tariff_xammasi_birga_3_plus": {"uz": "Hammasi birga 3+", "ru": "Hammasi birga 3+"},
    "tariff_xammasi_birga_3": {"uz": "Hammasi birga 3", "ru": "Hammasi birga 3"},
    "tariff_xammasi_birga_2": {"uz": "Hammasi birga 2", "ru": "Hammasi birga 2"},
}

# ================== FLOW ==================

@router.message(F.text.in_(["🔌 Ulanish uchun ariza", "🔌 Заявка на подключение"]))
async def start_connection_order_client(message: Message, state: FSMContext):
    try:
        lang = await get_user_language(message.from_user.id) or "uz"
        await state.update_data(lang=lang)

        await message.answer(
            t(lang, "start_title"),
            reply_markup=get_client_regions_keyboard(lang) if callable(get_client_regions_keyboard) else get_client_regions_keyboard(),
            parse_mode='HTML'
        )
        await state.set_state(ConnectionOrderStates.selecting_region)

    except Exception as e:
        logger.error(f"Error in start_connection_order_client: {e}")
        await message.answer(t("uz", "err_common"))  # fallback

@router.callback_query(F.data.startswith("region_"), StateFilter(ConnectionOrderStates.selecting_region))
async def select_region_old_client(callback: CallbackQuery, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        region_code = callback.data.replace("region_", "", 1)
        region_name = normalize_region(region_code, lang)
        await state.update_data(selected_region=region_name)

        await callback.message.answer(
            t(lang, "ask_type"),
            reply_markup=zayavka_type_keyboard(lang) if callable(zayavka_type_keyboard) else zayavka_type_keyboard()
        )
        await state.set_state(ConnectionOrderStates.selecting_connection_type)

    except Exception as e:
        logger.error(f"Error in select_region_old_client: {e}")
        await callback.answer(t(lang, "err_common"), show_alert=True)

@router.callback_query(F.data.startswith("zayavka_type_"), StateFilter(ConnectionOrderStates.selecting_connection_type))
async def select_connection_type_client(callback: CallbackQuery, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        connection_type = callback.data.split("_")[-1]
        await state.update_data(connection_type=connection_type)

        try:
            photo = FSInputFile("static/image.png")
            await callback.message.answer_photo(
                photo=photo,
                caption=t(lang, "tariff_caption"),
                reply_markup=get_client_tariff_selection_keyboard(lang) if callable(get_client_tariff_selection_keyboard) else get_client_tariff_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as img_error:
            logger.warning(f"Could not send tariff image: {img_error}")
            await callback.message.answer(
                t(lang, "tariff_caption"),
                reply_markup=get_client_tariff_selection_keyboard(lang) if callable(get_client_tariff_selection_keyboard) else get_client_tariff_selection_keyboard(),
                parse_mode='HTML'
            )
        await state.set_state(ConnectionOrderStates.selecting_tariff)

    except Exception as e:
        logger.error(f"Error in select_connection_type_client: {e}")
        await callback.answer(t(lang, "err_common"), show_alert=True)

@router.callback_query(F.data.in_(["tariff_xammasi_birga_4", "tariff_xammasi_birga_3_plus", "tariff_xammasi_birga_3", "tariff_xammasi_birga_2"]))
async def select_tariff_client(callback: CallbackQuery, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        tariff_code = callback.data
        await state.update_data(selected_tariff=tariff_code)

        await callback.message.answer(t(lang, "ask_address"))
        await state.set_state(ConnectionOrderStates.entering_address)

    except Exception as e:
        logger.error(f"Error in select_tariff_client: {e}")
        await callback.answer(t(lang, "err_common"), show_alert=True)

@router.message(StateFilter(ConnectionOrderStates.entering_address))
async def get_connection_address_client(message: Message, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await state.update_data(address=message.text)
        await message.answer(
            t(lang, "ask_geo_q"),
            reply_markup=geolocation_keyboard(lang) if callable(geolocation_keyboard) else geolocation_keyboard('uz')
        )
        await state.set_state(ConnectionOrderStates.asking_for_geo)

    except Exception as e:
        logger.error(f"Error in get_connection_address_client: {e}")
        await message.answer(t(lang, "err_common"))

@router.callback_query(F.data.in_(["send_location_yes", "send_location_no"]), StateFilter(ConnectionOrderStates.asking_for_geo))
async def ask_for_geo_client(callback: CallbackQuery, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        if callback.data == "send_location_yes":
            location_keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish" if lang == "uz" else "📍 Отправить локацию", request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await callback.message.answer(t(lang, "send_geo"), reply_markup=location_keyboard)
            await state.set_state(ConnectionOrderStates.waiting_for_geo)
        else:
            await finish_connection_order_client(callback, state, geo=None)

    except Exception as e:
        logger.error(f"Error in ask_for_geo_client: {e}")
        await callback.answer(t((await state.get_data()).get("lang", "uz"), "err_common"), show_alert=True)

@router.message(StateFilter(ConnectionOrderStates.waiting_for_geo), F.location)
async def get_geo_client(message: Message, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await state.update_data(geo=message.location)
        await message.answer(t(lang, "geo_ok"), reply_markup=ReplyKeyboardRemove())
        await finish_connection_order_client(message, state, geo=message.location)

    except Exception as e:
        logger.error(f"Error in get_geo_client: {e}")
        await message.answer(t(lang, "err_common"))

async def finish_connection_order_client(message_or_callback, state: FSMContext, geo=None):
    """Client uchun complete connection request submission"""
    try:
        data = await state.get_data()
        lang = data.get("lang", "uz")

        region = data.get('selected_region', data.get('region', 'toshkent shahri'))
        connection_type = data.get('connection_type', 'standard')
        tariff_code = data.get('selected_tariff', 'tariff_xammasi_birga_4')
        tariff_display = TARIFF_NAMES.get(tariff_code, {}).get(lang, tariff_code)
        address = data.get('address', '-')

        text = (
            (f"🏛️ <b>Hudud:</b> {region}\n" if lang == "uz" else f"🏛️ <b>Регион:</b> {region}\n") +
            (f"🔌 <b>Ulanish turi:</b> {connection_type.upper()}\n" if lang == "uz" else f"🔌 <b>Тип подключения:</b> {connection_type.upper()}\n") +
            (f"💳 <b>Tarif:</b> {tariff_display}\n" if lang == "uz" else f"💳 <b>Тариф:</b> {tariff_display}\n") +
            (f"🏠 <b>Manzil:</b> {address}\n" if lang == "uz" else f"🏠 <b>Адрес:</b> {address}\n") +
            (f"📍 <b>Geolokatsiya:</b> {'✅ Yuborilgan' if geo else '❌ Yuborilmagan'}\n\n" if lang == "uz" else f"📍 <b>Геолокация:</b> {'✅ Отправлена' if geo else '❌ Не отправлена'}\n\n") +
            t(lang, "confirm_title")
        )

        if hasattr(message_or_callback, "message"):
            await message_or_callback.message.answer(text, parse_mode='HTML', reply_markup=confirmation_keyboard(lang) if callable(confirmation_keyboard) else confirmation_keyboard())
        else:
            await message_or_callback.answer(text, parse_mode='HTML', reply_markup=confirmation_keyboard(lang) if callable(confirmation_keyboard) else confirmation_keyboard())

        await state.set_state(ConnectionOrderStates.confirming_connection)

    except Exception as e:
        logger.error(f"Error in finish_connection_order_client: {e}")
        msg = t((await state.get_data()).get("lang", "uz"), "err_common")
        if hasattr(message_or_callback, "message"):
            await message_or_callback.message.answer(msg)
        else:
            await message_or_callback.answer(msg)

@router.callback_query(F.data == "confirm_zayavka", StateFilter(ConnectionOrderStates.confirming_connection))
async def confirm_connection_order_client(callback: CallbackQuery, state: FSMContext):
    """Client zayavkasini tasdiqlash va database'ga yozish"""
    try:
        data = await state.get_data()
        lang = data.get("lang", "uz")

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer(t(lang, "confirm_wait"))

        region = (data.get('selected_region') or data.get('region') or 'toshkent shahri')
        user_row = await ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
        user_id = user_row["id"]
        user_phone = user_row.get("phone") if isinstance(user_row, dict) else user_row["phone"]

        tariff_code = data.get('selected_tariff')
        tarif_id = await get_or_create_tarif_by_code(tariff_code) if tariff_code else None
        tariff_name = TARIFF_NAMES.get(tariff_code, {}).get(lang, tariff_code) if tariff_code else None

        if tariff_code and not tarif_id:
            await callback.message.answer(
                t(lang, "not_found_tariff"),
                reply_markup=get_client_tariff_selection_keyboard(lang) if callable(get_client_tariff_selection_keyboard) else get_client_tariff_selection_keyboard()
            )
            await state.set_state(ConnectionOrderStates.selecting_tariff)
            return

        geo_data = data.get('geo')
        latitude = getattr(geo_data, 'latitude', None) if geo_data else None
        longitude = getattr(geo_data, 'longitude', None) if geo_data else None

        request_id = await create_connection_order(
            user_id=user_id,
            region=region.lower(),
            address=data.get('address', 'Kiritilmagan' if lang == "uz" else "Не указано"),
            tarif_id=tarif_id,
            latitude=latitude,
            longitude=longitude
        )

        if settings.ZAYAVKA_GROUP_ID:
            try:
                geo_text = ""
                if geo_data:
                    geo_text = f"\n📍 <b>Lokatsiya:</b> <a href='https://maps.google.com/?q={geo_data.latitude},{geo_data.longitude}'>Google Maps</a>"
                phone_for_msg = data.get('phone') or user_phone or '-'
                group_msg = (
                    f"🔌 <b>YANGI ULANISH ARIZASI</b>\n"  # yoki RUga ham o‘zgartirsangiz bo‘ladi
                    f"{'='*30}\n"
                    f"🆔 <b>ID:</b> <code>{request_id}</code>\n"
                    f"👤 <b>Mijoz:</b> {callback.from_user.full_name}\n"
                    f"📞 <b>Tel:</b> {phone_for_msg}\n"
                    f"🏢 <b>Region:</b> {region}\n"
                    f"💳 <b>Tarif:</b> {tariff_name}\n"
                    f"📍 <b>Manzil:</b> {data.get('address')}"
                    f"{geo_text}\n"
                    f"🕐 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                    f"{'='*30}"
                )
                await bot.send_message(chat_id=settings.ZAYAVKA_GROUP_ID, text=group_msg, parse_mode='HTML')
            except Exception:
                pass

        phone_for_msg = data.get('phone') or user_phone or '-'
        success_msg = (
            f"{t(lang, 'success_title')}\n\n" +
            (f"🆔 Ariza raqami: <code>{request_id}</code>\n" if lang == "uz" else f"🆔 Номер заявки: <code>{request_id}</code>\n") +
            (f"📍 Region: {region}\n" if lang == "uz" else f"📍 Регион: {region}\n") +
            (f"💳 Tarif: {tariff_name}\n" if lang == "uz" else f"💳 Тариф: {tariff_name}\n") +
            (f"📞 Telefon: {phone_for_msg}\n" if lang == "uz" else f"📞 Телефон: {phone_for_msg}\n") +
            (f"📍 Manzil: {data.get('address')}\n\n" if lang == "uz" else f"📍 Адрес: {data.get('address')}\n\n") +
            t(lang, "will_call")
        )

        await callback.message.answer(success_msg, parse_mode='HTML')
        await callback.message.answer(
            t(lang, "main_menu"),
            reply_markup=get_client_main_menu(lang) if callable(get_client_main_menu) else get_client_main_menu('uz')
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Error in confirm_connection_order_client: {e}")
        await callback.message.answer(t((await state.get_data()).get("lang", "uz"), "err_common"))

@router.callback_query(F.data == "resend_zayavka", StateFilter(ConnectionOrderStates.confirming_connection))
async def resend_connection_order_client(callback: CallbackQuery, state: FSMContext):
    """Client zayavkasini qayta yuborish"""
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer("..." if lang == "ru" else "Qayta yuborish...")
        await callback.message.edit_reply_markup(reply_markup=None)

        await state.clear()
        await state.update_data(lang=lang)  # tilni saqlab qo'yamiz

        await callback.message.answer(
            t(lang, "start_again"),
            reply_markup=get_client_regions_keyboard(lang) if callable(get_client_regions_keyboard) else get_client_regions_keyboard(),
            parse_mode='HTML'
        )
        await state.set_state(ConnectionOrderStates.selecting_region)

    except Exception as e:
        logger.error(f"Error in resend_connection_order_client: {e}")
        await callback.answer(t((await state.get_data()).get("lang", "uz"), "err_common"), show_alert=True)
