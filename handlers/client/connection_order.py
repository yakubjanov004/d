from datetime import datetime
import logging
import asyncpg
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
from database.basic.user import ensure_user
from database.basic.tariff import get_or_create_tarif_by_code
from database.basic.language import get_user_language
from database.client.orders import create_connection_order
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

        # Clear state and set defaults for new order
        await state.clear()
        await state.update_data(lang=lang, connection_type='b2c')  # Force B2C for clients

        await message.answer(
            ("🔌 <b>Yangi ulanish arizasi</b>\n\n📍 Qaysi regionda ulanmoqchisiz?" if lang == "uz" else "🔌 <b>Новая заявка на подключение</b>\n\n📍 В каком регионе хотите подключиться?"),
            reply_markup=get_client_regions_keyboard(lang) if callable(get_client_regions_keyboard) else get_client_regions_keyboard(),
            parse_mode='HTML'
        )
        await state.set_state(ConnectionOrderStates.selecting_region)

    except Exception as e:
        logger.error(f"Error in start_connection_order_client: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")  # fallback

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
            ("Ulanish turini tanlang:" if lang == "uz" else "Выберите тип подключения:"),
            reply_markup=zayavka_type_keyboard(lang) if callable(zayavka_type_keyboard) else zayavka_type_keyboard()
        )
        await state.set_state(ConnectionOrderStates.selecting_connection_type)

    except Exception as e:
        logger.error(f"Error in select_region_old_client: {e}")
        await callback.answer(("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if lang == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз."), show_alert=True)

@router.callback_query(F.data.startswith("zayavka_type_"), StateFilter(ConnectionOrderStates.selecting_connection_type))
async def select_connection_type_client(callback: CallbackQuery, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        connection_type = callback.data.split("_")[-1]
        await state.update_data(connection_type=connection_type)

        try:
            photo = FSInputFile("static/images/image.png")
            await callback.message.answer_photo(
                photo=photo,
                caption=("📋 <b>Tariflardan birini tanlang:</b>\n\n" if lang == "uz" else "📋 <b>Выберите один из тарифов:</b>\n\n"),
                reply_markup=get_client_tariff_selection_keyboard(lang) if callable(get_client_tariff_selection_keyboard) else get_client_tariff_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as img_error:
            logger.warning(f"Could not send tariff image: {img_error}")
            await callback.message.answer(
                ("📋 <b>Tariflardan birini tanlang:</b>\n\n" if lang == "uz" else "📋 <b>Выберите один из тарифов:</b>\n\n"),
                reply_markup=get_client_tariff_selection_keyboard(lang) if callable(get_client_tariff_selection_keyboard) else get_client_tariff_selection_keyboard(),
                parse_mode='HTML'
            )
        await state.set_state(ConnectionOrderStates.selecting_tariff)

    except Exception as e:
        logger.error(f"Error in select_connection_type_client: {e}")
        await callback.answer(("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if lang == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз."), show_alert=True)

@router.callback_query(F.data.in_(["tariff_xammasi_birga_4", "tariff_xammasi_birga_3_plus", "tariff_xammasi_birga_3", "tariff_xammasi_birga_2"]))
async def select_tariff_client(callback: CallbackQuery, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        tariff_code = callback.data
        await state.update_data(selected_tariff=tariff_code)

        await callback.message.answer("📍 Manzilingizni kiriting:" if lang == "uz" else "📍 Введите ваш адрес:")
        await state.set_state(ConnectionOrderStates.entering_address)

    except Exception as e:
        logger.error(f"Error in select_tariff_client: {e}")
        await callback.answer(("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if lang == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз."), show_alert=True)

@router.message(StateFilter(ConnectionOrderStates.entering_address))
async def get_connection_address_client(message: Message, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await state.update_data(address=message.text)
        await message.answer(
            ("Geolokatsiya yuborasizmi?" if lang == "uz" else "Отправите геолокацию?"),
            reply_markup=geolocation_keyboard(lang) if callable(geolocation_keyboard) else geolocation_keyboard('uz')
        )
        await state.set_state(ConnectionOrderStates.asking_for_geo)

    except Exception as e:
        logger.error(f"Error in get_connection_address_client: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if lang == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз.")

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
            await callback.message.answer(("📍 Joylashuvingizni yuboring:" if lang == "uz" else "📍 Отправьте свою локацию:"), reply_markup=location_keyboard)
            await state.set_state(ConnectionOrderStates.waiting_for_geo)
        else:
            await finish_connection_order_client(callback, state, geo=None)

    except Exception as e:
        logger.error(f"Error in ask_for_geo_client: {e}")
        await callback.answer(("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if (await state.get_data()).get("lang", "uz") == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз."), show_alert=True)

@router.message(StateFilter(ConnectionOrderStates.waiting_for_geo), F.location)
async def get_geo_client(message: Message, state: FSMContext):
    try:
        lang = (await state.get_data()).get("lang", "uz")
        await state.update_data(geo=message.location)
        await message.answer(("✅ Joylashuv qabul qilindi!" if lang == "uz" else "✅ Геолокация получена!"), reply_markup=ReplyKeyboardRemove())
        await finish_connection_order_client(message, state, geo=message.location)

    except Exception as e:
        logger.error(f"Error in get_geo_client: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if lang == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз.")

async def finish_connection_order_client(message_or_callback, state: FSMContext, geo=None):
    """Client uchun complete connection request submission"""
    try:
        data = await state.get_data()
        lang = data.get("lang", "uz")

        region = data.get('selected_region', data.get('region', 'toshkent shahri'))
        connection_type = data.get('connection_type', 'b2c')
        tariff_code = data.get('selected_tariff', 'tariff_xammasi_birga_4')
        tariff_display = TARIFF_NAMES.get(tariff_code, {}).get(lang, tariff_code)
        address = data.get('address', '-')

        text = (
            (f"🏛️ <b>Hudud:</b> {region}\n" if lang == "uz" else f"🏛️ <b>Регион:</b> {region}\n") +
            (f"🔌 <b>Ulanish turi:</b> {connection_type.upper()}\n" if lang == "uz" else f"🔌 <b>Тип подключения:</b> {connection_type.upper()}\n") +
            (f"💳 <b>Tarif:</b> {tariff_display}\n" if lang == "uz" else f"💳 <b>Тариф:</b> {tariff_display}\n") +
            (f"🏠 <b>Manzil:</b> {address}\n" if lang == "uz" else f"🏠 <b>Адрес:</b> {address}\n") +
            (f"📍 <b>Geolokatsiya:</b> {'✅ Yuborilgan' if geo else '❌ Yuborilmagan'}\n\n" if lang == "uz" else f"📍 <b>Геолокация:</b> {'✅ Отправлена' if geo else '❌ Не отправлена'}\n\n") +
            ("Ma'lumotlar to'g'rimi?" if lang == "uz" else "Данные верны?")
        )

        if hasattr(message_or_callback, "message"):
            await message_or_callback.message.answer(text, parse_mode='HTML', reply_markup=confirmation_keyboard(lang) if callable(confirmation_keyboard) else confirmation_keyboard())
        else:
            await message_or_callback.answer(text, parse_mode='HTML', reply_markup=confirmation_keyboard(lang) if callable(confirmation_keyboard) else confirmation_keyboard())

        await state.set_state(ConnectionOrderStates.confirming_connection)

    except Exception as e:
        logger.error(f"Error in finish_connection_order_client: {e}")
        msg = ("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if (await state.get_data()).get("lang", "uz") == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз.")
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
        await callback.answer("⏳ Zayavka yaratilmoaqda..." if lang == "uz" else "⏳ Заявка создаётся...")

        region = (data.get('selected_region') or data.get('region') or 'toshkent shahri')
        user_row = await ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
        user_id = user_row["id"]
        user_phone = user_row.get("phone") if isinstance(user_row, dict) else user_row["phone"]

        tariff_code = data.get('selected_tariff')
        tarif_id = await get_or_create_tarif_by_code(tariff_code) if tariff_code else None
        tariff_name = TARIFF_NAMES.get(tariff_code, {}).get(lang, tariff_code) if tariff_code else None

        if tariff_code and not tarif_id:
            await callback.message.answer(
                ("❌ Tanlangan tarif topilmadi. Iltimos, quyidagi ro'yxatdan tarifni qayta tanlang." if lang == "uz" else "❌ Выбранный тариф не найден. Пожалуйста, выберите тариф заново из списка ниже."),
                reply_markup=get_client_tariff_selection_keyboard(lang) if callable(get_client_tariff_selection_keyboard) else get_client_tariff_selection_keyboard()
            )
            await state.set_state(ConnectionOrderStates.selecting_tariff)
            return

        geo_data = data.get('geo')
        latitude = getattr(geo_data, 'latitude', None) if geo_data else None
        longitude = getattr(geo_data, 'longitude', None) if geo_data else None

        # Force B2C for clients - always default to B2C
        connection_type = data.get('connection_type', 'b2c')

        # Force B2C unless explicitly B2B
        if connection_type != 'b2b':
            connection_type = 'b2c'

        business_type = connection_type.upper()
        
        
        request_id = await create_connection_order(
            user_id=user_id,
            region=region.lower(),
            address=data.get('address', 'Kiritilmagan' if lang == "uz" else "Не указано"),
            tarif_id=tarif_id,
            latitude=latitude,
            longitude=longitude,
            business_type=business_type
        )

        # Get the full application number from the database first
        conn = await asyncpg.connect(settings.DB_URL)
        try:
            # Fetch the application number using the request_id
            result = await conn.fetchrow(
                "SELECT application_number FROM connection_orders WHERE id = $1", 
                request_id
            )
            app_number = result['application_number'] if result else f"CONN-{request_id:04d}"
        except Exception as e:
            logger.error(f"Error fetching application number: {e}")
            app_number = f"CONN-{request_id:04d}"
        finally:
            await conn.close()

        if settings.ZAYAVKA_GROUP_ID:
            try:
                geo_text = ""
                if geo_data:
                    geo_text = f"\n📍 <b>Lokatsiya:</b> <a href='https://maps.google.com/?q={geo_data.latitude},{geo_data.longitude}'>Google Maps</a>"
                phone_for_msg = data.get('phone') or user_phone or '-'
                group_msg = (
                    f"🔌 <b>YANGI ULANISH ARIZASI</b>\n" 
                    f"{'='*30}\n"
                    f"🆔 <b>ID:</b> <code>{app_number}</code>\n"
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

        # Yuborish muvaffaqiyatli bo'lsa, foydalanuvchiga xabar bering
        success_msg = (
            f"✅ {'<b>Arizangiz muvaffaqiyatli qabul qilindi!</b>' if lang == 'uz' else '<b>Ваша заявка успешно принята!</b>'}\n\n"
            f"🆔 {'Ariza raqami' if lang == 'uz' else 'Номер заявки'}: {app_number}\n"
            f"📍 {'Hudud' if lang == 'uz' else 'Регион'}: {normalize_region(region, lang)}\n"
            f"💳 {'Tarif' if lang == 'uz' else 'Тариф'}: {tariff_name}\n"
            f"📞 {'Telefon' if lang == 'uz' else 'Телефон'}: {user_phone or '-'}\n"
            f"📍 {'Manzil' if lang == 'uz' else 'Адрес'}: {data.get('address', '-')}\n\n"
            f"⏰ {'Menejerlarimiz tez orada siz bilan bog\'lanadi!' if lang == 'uz' else 'Наши менеджеры свяжутся с вами в ближайшее время!'}"
        )
        
        # Send the success message
        await callback.message.answer(
            success_msg,
            reply_markup=get_client_main_menu(lang) if callable(get_client_main_menu) else get_client_main_menu('uz')
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Error in confirm_connection_order_client: {e}")
        await callback.message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if (await state.get_data()).get("lang", "uz") == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз.")

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
            ("🔌 <b>Yangi ulanish arizasi</b>\n\n📍 Qaysi regionda ulanmoqchisiz?" if lang == "uz" else "🔌 <b>Новая заявка на подключение</b>\n\n📍 В каком регионе хотите подключиться?"),
            reply_markup=get_client_regions_keyboard(lang) if callable(get_client_regions_keyboard) else get_client_regions_keyboard(),
            parse_mode='HTML'
        )
        await state.set_state(ConnectionOrderStates.selecting_region)

    except Exception as e:
        logger.error(f"Error in resend_connection_order_client: {e}")
        await callback.answer(("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring." if (await state.get_data()).get("lang", "uz") == "uz" else "❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз."), show_alert=True)
