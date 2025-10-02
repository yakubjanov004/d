from datetime import datetime
import html
import logging
from aiogram import F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from keyboards.client_buttons import (
    get_client_main_menu,
    zayavka_type_keyboard,
    geolocation_keyboard,
    media_attachment_keyboard,
    get_client_regions_keyboard,
    get_contact_keyboard,
)
from states.client_states import ServiceOrderStates
from database.basic.language import get_user_language
from database.client.queries import (
    find_user_by_telegram_id,
    get_user_phone_by_telegram_id,
    update_user_phone_by_telegram_id
)
from database.client.orders import create_service_order
from config import settings
from loader import bot

logger = logging.getLogger(__name__)
router = Router()

# ---------- Region nomlarini normallashtirish ----------
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

CAT_CODE_TO_ENUM = {
    "cat_smart_home": "aqlli_avtomatlashtirilgan_xizmatlar",
    "cat_security": "xavfsizlik_kuzatuv_tizimlari",
    "cat_internet": "internet_tarmoq_xizmatlari",
    "cat_energy": "energiya_yashil_texnologiyalar",
    "cat_multimedia": "multimediya_aloqa_tizimlari",
    "cat_special": "maxsus_qoshimcha_xizmatlar",
}
SERVICE_CODE_TO_ENUM = {
    "srv_smart_home_setup": "aqlli_uy_tizimlarini_ornatish_sozlash",
    "srv_smart_lighting": "aqlli_yoritish_smart_lighting_tizimlari",
    "srv_smart_thermostat": "aqlli_termostat_iqlim_nazarati_tizimlari",
    "srv_smart_lock": "smart_lock_internet_boshqariladigan_eshik_qulfi",
    "srv_smart_outlets": "aqlli_rozetalar_energiya_monitoring_tizimlari",
    "srv_remote_control": "uyni_masofadan_boshqarish_qurilmalari_uzim",
    "srv_smart_curtains": "aqlli_pardalari_jaluz_tizimlari",
    "srv_appliance_integration": "aqlli_malahiy_texnika_integratsiyasi",

    "srv_cctv_cameras": "videokuzatuv_kameralarini_ornatish_ip_va_analog",
    "srv_camera_storage": "kamera_arxiv_tizimlari_bulutli_saqlash_xizmatlari",
    "srv_intercom": "domofon_tizimlari_ornatish",
    "srv_security_alarm": "xavfsizlik_signalizatsiyasi_harakat_sensorlari",
    "srv_fire_alarm": "yong_signalizatsiyasi_tizimlari",
    "srv_gas_flood_protection": "gaz_sizish_sav_toshqinliqqa_qarshi_tizimlar",
    "srv_face_recognition": "yuzni_tanish_face_recognition_tizimlari",
    "srv_automatic_gates": "avtomatik_eshik_darvoza_boshqaruv_tizimlari",

    "srv_wifi_setup": "wi_fi_tarmoqlarini_ornatish_sozlash",
    "srv_wifi_extender": "wi_fi_qamrov_zonasini_kengaytirish_access_point",
    "srv_signal_booster": "mobil_aloqa_signalini_kuchaytirish_repeater",
    "srv_lan_setup": "ofis_va_uy_uchun_lokal_tarmoq_lan_qurish",
    "srv_internet_provider": "internet_provayder_xizmatlarini_ulash",
    "srv_server_nas": "server_va_nas_qurilmalarini_ornatish",
    "srv_cloud_storage": "bulutli_fayl_almashish_zaxira_tizimlari",
    "srv_vpn_setup": "vpn_va_xavfsiz_internet_ulanishlarini_tashkil",

    "srv_solar_panels": "quyosh_panellarini_ornatish_ulash",
    "srv_solar_batteries": "quyosh_batareyalari_orqali_energiya_saqlash",
    "srv_wind_generators": "shamol_generatorlarini_ornatish",
    "srv_energy_saving_lighting": "elektr_energiyasini_tejovchi_yoritish_tizimlari",
    "srv_smart_irrigation": "avtomatik_suv_orish_tizimlari_smart_irrigation",

    "srv_smart_tv": "smart_tv_ornatish_ulash",
    "srv_home_cinema": "uy_kinoteatri_tizimlari_ornatish",
    "srv_multiroom_audio": "audio_tizimlar_multiroom",
    "srv_ip_telephony": "ip_telefoniya_mini_ats_tizimlarini_tashkil",
    "srv_video_conference": "video_konferensiya_tizimlari",
    "srv_presentation_systems": "interaktiv_taqdimot_tizimlari_proyektor_led",

    "srv_smart_office": "aqlli_ofis_tizimlarini_ornatish",
    "srv_data_center": "data_markaz_server_room_loyihalash_montaj",
    "srv_technical_support": "qurilma_tizimlar_uchun_texnik_xizmat_korsatish",
    "srv_software_install": "dasturiy_taminotni_ornatish_yangilash",
    "srv_iot_integration": "iot_internet_of_things_qurilmalarini_integratsiya",
    "srv_remote_management": "qurilmalarni_masofadan_boshqarish_tizimlarini_sozlash",
    "srv_ai_management": "sun'iy_intellekt_asosidagi_uy_ofis_boshqaruv",
}

def normalize_region(region_code: str) -> str:
    return REGION_CODE_TO_UZ.get(region_code, region_code)

# ---------- i18n helper ----------
def t(key: str, lang: str = "uz") -> str:
    M = {
        "start_title": {
            "uz": "🔧 <b>Texnik xizmat arizasi</b>\n\n📍 Qaysi hududda xizmat kerak?",
            "ru": "🔧 <b>Заявка в техподдержку</b>\n\n📍 В каком регионе требуется обслуживание?",
        },
        "ask_phone": {
            "uz": "Iltimos, raqamingizni jo'nating (tugma orqali).",
            "ru": "Пожалуйста, отправьте свой номер телефона (через кнопку).",
        },
        "phone_saved_next_region": {
            "uz": "✅ Raqam qabul qilindi. Endi xizmat kerak bo'lgan hududni tanlang:",
            "ru": "✅ Номер получен. Теперь выберите регион, где требуется обслуживание:",
        },
        "ask_abonent_type": {
            "uz": "Abonent turini tanlang:",
            "ru": "Выберите тип абонента:",
        },
        "ask_abonent_id": {
            "uz": "🆔 Abonent ID raqamingizni kiriting:",
            "ru": "🆔 Введите ваш ID абонента:",
        },
        "ask_problem": {
            "uz": "📝 Muammoni batafsil yozing:",
            "ru": "📝 Опишите проблему подробнее:",
        },
        "ask_address": {
            "uz": "📍 Manzilingizni kiriting:",
            "ru": "📍 Введите ваш адрес:",
        },
        "ask_media": {
            "uz": "📷 Muammo rasmi yoki videosini yuborasizmi?",
            "ru": "📷 Прикрепите фото или видео проблемы?",
        },
        "ask_geo": {
            "uz": "📍 Geolokatsiya yuborasizmi?",
            "ru": "📍 Отправите геолокацию?",
        },
        "send_location_btn": {
            "uz": "📍 Joylashuvni yuborish",
            "ru": "📍 Отправить локацию",
        },
        "send_location_prompt": {
            "uz": "📍 Joylashuvingizni yuboring:",
            "ru": "📍 Отправьте вашу локацию:",
        },
        "location_ok": {
            "uz": "✅ Joylashuv qabul qilindi!",
            "ru": "✅ Геолокация получена!",
        },
        "summary_title": {
            "uz": "📋 <b>Texnik xizmat arizasi ma'lumotlari:</b>\n\n",
            "ru": "📋 <b>Данные по заявке в техподдержку:</b>\n\n",
        },
        "summary_region": {
            "uz": "🌍 <b>Hudud:</b> {val}\n",
            "ru": "🌍 <b>Регион:</b> {val}\n",
        },
        "summary_abonent": {
            "uz": "👤 <b>Abonent turi:</b> {val}\n",
            "ru": "👤 <b>Тип абонента:</b> {val}\n",
        },
        "summary_abonent_id": {
            "uz": "🆔 <b>Abonent ID:</b> {val}\n",
            "ru": "🆔 <b>ID абонента:</b> {val}\n",
        },
        "summary_phone": {
            "uz": "📞 <b>Telefon:</b> {val}\n",
            "ru": "📞 <b>Телефон:</b> {val}\n",
        },
        "summary_reason": {
            "uz": "📝 <b>Muammo:</b> {val}\n",
            "ru": "📝 <b>Проблема:</b> {val}\n",
        },
        "summary_address": {
            "uz": "📍 <b>Manzil:</b> {val}\n",
            "ru": "📍 <b>Адрес:</b> {val}\n",
        },
        "summary_geo": {
            "uz": "🗺 <b>Joylashuv:</b> {val}\n",
            "ru": "🗺 <b>Локация:</b> {val}\n",
        },
        "summary_media": {
            "uz": "📷 <b>Media:</b> {val}\n\n",
            "ru": "📷 <b>Медиа:</b> {val}\n\n",
        },
        "summary_confirm_q": {
            "uz": "Ma'lumotlar to‘g‘rimi?",
            "ru": "Все верно?",
        },
        "confirm_yes": {
            "uz": "✅ Tasdiqlash",
            "ru": "✅ Подтвердить",
        },
        "confirm_no": {
            "uz": "🔁 Qayta yuborish",
            "ru": "🔁 Заполнить заново",
        },
        "restart_flow": {
            "uz": "🔄 Ariza qayta boshlanmoqda...\n\nIltimos, hududni tanlang:",
            "ru": "🔄 Заявка начинается заново...\n\nПожалуйста, выберите регион:",
        },
        "success_user": {
            "uz": (
                "✅ <b>Texnik xizmat arizangiz qabul qilindi!</b>\n\n"
                "🆔 Ariza raqami: <code>{id}</code>\n"
                "📍 Hudud: {region}\n"
                "🏢 Abonent ID: {abonent_id}\n"
                "📍 Manzil: {address}\n"
                "⏰ Texnik mutaxassis tez orada bog'lanadi!\n"
            ),
            "ru": (
                "✅ <b>Ваша заявка в техподдержку принята!</b>\n\n"
                "🆔 Номер: <code>{id}</code>\n"
                "📍 Регион: {region}\n"
                "🏢 ID абонента: {abonent_id}\n"
                "📍 Адрес: {address}\n"
                "⏰ Специалист свяжется с вами в ближайшее время!\n"
            ),
        },
        "cancelled": {
            "uz": "❌ Texnik xizmat arizasi bekor qilindi",
            "ru": "❌ Заявка в техподдержку отменена",
        },
        "error": {
            "uz": "❌ Xatolik yuz berdi.",
            "ru": "❌ Произошла ошибка.",
        },
        "error_try_again": {
            "uz": "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
            "ru": "❌ Произошла ошибка. Попробуйте еще раз.",
        },
        "only_own_phone": {
            "uz": "Iltimos, faqat o'zingizning raqamingizni yuboring.",
            "ru": "Пожалуйста, отправьте только свой номер телефона.",
        },
        "send_photo_video": {
            "uz": "📷 Rasm yoki video yuboring:",
            "ru": "📷 Отправьте фото или видео:",
        },
        "media_yes": {"uz": "✅ Mavjud", "ru": "✅ Есть"},
        "media_no": {"uz": "❌ Yo‘q", "ru": "❌ Нет"},
        "geo_none": {"uz": "Berilmagan", "ru": "Не указана"},
        "cancel_btn_answer": {"uz": "Bekor qilindi", "ru": "Отменено"},
    }
    return M.get(key, {}).get(lang, M.get(key, {}).get("uz", ""))

# ---------- Lokal tasdiqlash inline klaviaturasi ----------
def confirmation_inline_kb(lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("confirm_yes", lang), callback_data="confirm_service_yes"),
        InlineKeyboardButton(text=t("confirm_no",  lang), callback_data="confirm_service_no"),
    ]])

# ---------- Start: Texnik xizmat oqimi ----------
@router.message(F.text.in_(["🔧 Texnik xizmat", "🔧 Техническая служба"]))
async def start_service_order(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        await state.update_data(telegram_id=message.from_user.id)

        phone = await get_user_phone_by_telegram_id(message.from_user.id)
        if not phone:
            await message.answer(t("ask_phone", lang), reply_markup=get_contact_keyboard(lang))
            return
        else:
            await state.update_data(phone=phone)

        await message.answer(
            t("start_title", lang),
            reply_markup=get_client_regions_keyboard(lang),
            parse_mode='HTML'
        )
        await state.set_state(ServiceOrderStates.selecting_region)

    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(t("error", lang))

# ---------- Contact qabul qilish ----------
@router.message(F.contact)
async def handle_contact_for_service_order(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        if not message.contact:
            return
        if message.contact.user_id and message.contact.user_id != message.from_user.id:
            await message.answer(t("only_own_phone", lang), reply_markup=get_contact_keyboard(lang))
            return

        phone_number = message.contact.phone_number
        await update_user_phone_by_telegram_id(message.from_user.id, phone_number)
        await state.update_data(phone=phone_number, telegram_id=message.from_user.id)

        await message.answer(t("phone_saved_next_region", lang), reply_markup=get_client_regions_keyboard(lang))
        await state.set_state(ServiceOrderStates.selecting_region)

    except Exception as e:
        logger.error(f"Error in handle_contact_for_service_order: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Region tanlash ----------
@router.callback_query(F.data.startswith("region_"), StateFilter(ServiceOrderStates.selecting_region))
async def select_region(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    try:
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        region_code = callback.data.replace("region_", "", 1)
        region_name = normalize_region(region_code)

        await state.update_data(selected_region=region_name, region=region_name)

        await callback.message.answer(
            t("ask_abonent_type", lang),
            reply_markup=zayavka_type_keyboard(lang),
            parse_mode='HTML'
        )
        await state.set_state(ServiceOrderStates.selecting_abonent_type)

    except Exception as e:
        logger.error(f"Error: {e}")
        await callback.answer(t("error", lang), show_alert=True)

# ---------- Abonent turini tanlash ----------
@router.callback_query(F.data.startswith("zayavka_type_"), StateFilter(ServiceOrderStates.selecting_abonent_type))
async def select_abonent_type(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    try:
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        abonent_type = callback.data.split("_")[-1].upper()
        await state.update_data(abonent_type=abonent_type)

        await callback.message.answer(t("ask_abonent_id", lang))
        await state.set_state(ServiceOrderStates.waiting_for_contact)

    except Exception as e:
        logger.error(f"Error: {e}")
        await callback.answer(t("error", lang), show_alert=True)

# ---------- Abonent ID kiritish ----------
@router.message(StateFilter(ServiceOrderStates.waiting_for_contact), F.text)
async def get_abonent_id(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        await state.update_data(abonent_id=message.text)
        await message.answer(t("ask_problem", lang))
        await state.set_state(ServiceOrderStates.entering_reason)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Sabab / Muammo matni ----------
@router.message(StateFilter(ServiceOrderStates.entering_reason), F.text)
async def get_reason(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        await state.update_data(reason=message.text)
        await message.answer(t("ask_address", lang))
        await state.set_state(ServiceOrderStates.entering_address)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Manzil ----------
@router.message(StateFilter(ServiceOrderStates.entering_address), F.text)
async def get_address(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        await state.update_data(address=message.text)
        await message.answer(t("ask_media", lang), reply_markup=media_attachment_keyboard(lang))
        await state.set_state(ServiceOrderStates.asking_for_media)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Media yuborish qarori ----------
@router.callback_query(F.data.in_(["attach_media_yes", "attach_media_no"]), StateFilter(ServiceOrderStates.asking_for_media))
async def ask_for_media(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    try:
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        if callback.data == "attach_media_yes":
            await callback.message.answer(t("send_photo_video", lang))
            await state.set_state(ServiceOrderStates.waiting_for_media)
        else:
            await ask_for_geolocation(callback.message, state, lang)
    except Exception as e:
        logger.error(f"Error: {e}")
        await callback.answer(t("error", lang), show_alert=True)

# ---------- Media qabul qilish ----------
@router.message(StateFilter(ServiceOrderStates.waiting_for_media), F.photo | F.video)
async def get_media(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        if message.photo:
            media_id = message.photo[-1].file_id
            media_type = 'photo'
        elif message.video:
            media_id = message.video.file_id
            media_type = 'video'
        else:
            media_id = None
            media_type = None

        await state.update_data(media_id=media_id, media_type=media_type)
        await ask_for_geolocation(message, state, lang)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Geolokatsiya so‘rash ----------
async def ask_for_geolocation(message: Message, state: FSMContext, lang: str):
    await message.answer(t("ask_geo", lang), reply_markup=geolocation_keyboard(lang))
    await state.set_state(ServiceOrderStates.asking_for_location)

# ---------- Geolokatsiya qarori ----------
@router.callback_query(F.data.in_(["send_location_yes", "send_location_no"]), StateFilter(ServiceOrderStates.asking_for_location))
async def geo_decision(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    try:
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        if callback.data == "send_location_yes":
            location_keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=t("send_location_btn", lang), request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await callback.message.answer(t("send_location_prompt", lang), reply_markup=location_keyboard)
            await state.set_state(ServiceOrderStates.waiting_for_location)
        else:
            await show_service_order_confirmation(callback.message, state, lang)
    except Exception as e:
        logger.error(f"Error: {e}")
        await callback.answer(t("error", lang), show_alert=True)

# ---------- Lokatsiyani qabul qilish ----------
@router.message(StateFilter(ServiceOrderStates.waiting_for_location), F.location)
async def get_geo(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        await state.update_data(geo=message.location)
        await message.answer(t("location_ok", lang), reply_markup=ReplyKeyboardRemove())
        await show_service_order_confirmation(message, state, lang)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Lokatsiyani matn bilan kiritish ----------
@router.message(StateFilter(ServiceOrderStates.waiting_for_location), F.text)
async def get_location_text(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    try:
        await state.update_data(location=message.text)
        await message.answer(t("location_ok", lang), reply_markup=ReplyKeyboardRemove())
        await show_service_order_confirmation(message, state, lang)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Tasdiqlash oynasi ----------
async def show_service_order_confirmation(message: Message, state: FSMContext, lang: str):
    try:
        data = await state.get_data()
        region = data.get('selected_region') or data.get('region')
        geo = data.get('geo')
        location_text = data.get('location')

        if geo:
            geo_text = f"{geo.latitude}, {geo.longitude}"
        elif location_text:
            geo_text = location_text
        else:
            geo_text = t("geo_none", lang)

        summary_msg = (
            t("summary_title", lang) +
            t("summary_region", lang).format(val=region) +
            t("summary_abonent", lang).format(val=data.get('abonent_type')) +
            t("summary_abonent_id", lang).format(val=data.get('abonent_id')) +
            t("summary_phone", lang).format(val=data.get('phone')) +
            t("summary_reason", lang).format(val=data.get('reason')) +
            t("summary_address", lang).format(val=data.get('address')) +
            t("summary_geo", lang).format(val=geo_text) +
            t("summary_media", lang).format(val=t("media_yes", lang) if data.get('media_id') else t("media_no", lang)) +
            t("summary_confirm_q", lang)
        )
        await message.answer(summary_msg, reply_markup=confirmation_inline_kb(lang), parse_mode="HTML")
        await state.set_state(ServiceOrderStates.confirming_service)
    except Exception as e:
        logger.error(f"Error in show_service_order_confirmation: {e}")
        await message.answer(t("error_try_again", lang))

# ---------- Yakuniy tasdiqlash / Qayta boshlash ----------
@router.callback_query(F.data.in_(["confirm_service_yes", "confirm_service_no"]), StateFilter(ServiceOrderStates.confirming_service))
async def handle_service_confirmation(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    try:
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)

        if callback.data == "confirm_service_yes":
            data = await state.get_data()
            geo = data.get('geo')
            await finish_service_order(callback.message, state, lang, geo=geo)
        else:
            await callback.message.answer(t("restart_flow", lang), reply_markup=get_client_regions_keyboard(lang))
            await state.clear()
            await state.set_state(ServiceOrderStates.selecting_region)
    except Exception as e:
        logger.error(f"Error in handle_service_confirmation: {e}")
        await callback.answer(t("error", lang), show_alert=True)

# ---------- Yaratish (finish) ----------
async def finish_service_order(message: Message, state: FSMContext, lang: str, geo=None):
    try:
        data = await state.get_data()
        region = data.get('selected_region') or data.get('region')
        region_db_value = (region or '').lower()

        user_record = await find_user_by_telegram_id(data['telegram_id'])
        user = dict(user_record) if user_record is not None else {}

        if geo:
            geo_str = f"{geo.latitude},{geo.longitude}"
        elif data.get('location'):
            geo_str = data.get('location')
        else:
            geo_str = None

        request_id = await create_service_order(
            user.get('id'),
            region_db_value,
            data.get('abonent_id'),
            data.get('address'),
            data.get('reason'),
            data.get('media_id'),
            geo_str
        )

        # Guruhga xabar (hozir UZda; xohlasangiz ru versiyasini ham shunday qo‘shamiz)
        if settings.ZAYAVKA_GROUP_ID:
            try:
                geo_text = ""
                if geo:
                    geo_text = f"\n📍 <b>Lokatsiya:</b> <a href='https://maps.google.com/?q={geo.latitude},{geo.longitude}'>Google Maps</a>"
                elif data.get('location'):
                    geo_text = f"\n📍 <b>Lokatsiya:</b> {data.get('location')}"

                phone_for_msg = data.get('phone') or user.get('phone') or '-'
                group_msg = (
                    f"🔧 <b>YANGI TEXNIK XIZMAT ARIZASI</b>\n"
                    f"{'='*30}\n"
                    f"🆔 <b>ID:</b> <code>{request_id}</code>\n"
                    f"👤 <b>Mijoz:</b> {user.get('full_name', '-')}\n"
                    f"📞 <b>Tel:</b> {phone_for_msg}\n"
                    f"🏢 <b>Region:</b> {region}\n"
                    f"🏢 <b>Abonent:</b> {data.get('abonent_type')} - {data.get('abonent_id')}\n"
                    f"📍 <b>Manzil:</b> {data.get('address')}\n"
                    f"📝 <b>Muammo:</b> {((data.get('reason') or data.get('description') or '')[:100])}...\n"
                    f"{geo_text}\n"
                    f"📷 <b>Media:</b> {'✅ Mavjud' if data.get('media_id') else '❌ Yo‘q'}\n"
                    f"🕐 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                    f"{'='*30}"
                )

                await bot.send_message(
                    chat_id=settings.ZAYAVKA_GROUP_ID,
                    text=group_msg,
                    parse_mode='HTML'
                )

                if data.get('media_id'):
                    if data.get('media_type') == 'photo':
                        await bot.send_photo(
                            chat_id=settings.ZAYAVKA_GROUP_ID,
                            photo=data['media_id'],
                            caption=None,
                            parse_mode='HTML'
                        )
                    elif data.get('media_type') == 'video':
                        await bot.send_video(
                            chat_id=settings.ZAYAVKA_GROUP_ID,
                            video=data['media_id'],
                            caption=None,
                            parse_mode='HTML'
                        )

                if geo:
                    await bot.send_location(
                        settings.ZAYAVKA_GROUP_ID,
                        latitude=geo.latitude,
                        longitude=geo.longitude
                    )

            except Exception as group_error:
                logger.error(f"Group notification error: {group_error}")
                try:
                    await bot.send_message(
                        chat_id=settings.ADMIN_GROUP_ID,
                        text=f"⚠️ Guruhga xabar yuborishda xato:\n{group_msg}\n\nXato: {group_error}",
                        parse_mode='HTML'
                    )
                except:
                    pass

        # Foydalanuvchiga muvaffaqiyat xabari — tilga mos
        success_msg = t("success_user", lang).format(
            id=request_id,
            region=region,
            abonent_id=data.get('abonent_id'),
            address=data.get('address')
        )

        await message.answer(success_msg, parse_mode='HTML', reply_markup=get_client_main_menu(lang))
        await state.clear()

    except Exception as e:
        logger.error(f"Error in finish_service_order: {e}")
        await message.answer(t("error_try_again", lang), reply_markup=get_client_main_menu(lang))
        await state.clear()

# ---------- Bekor qilish ----------
@router.callback_query(F.data == "service_cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_language(callback.from_user.id) or "uz"
    try:
        await callback.answer(t("cancel_btn_answer", lang))
        await callback.message.edit_reply_markup(reply_markup=None)

        await state.clear()
        await callback.message.answer(t("cancelled", lang), reply_markup=get_client_main_menu(lang))
    except Exception as e:
        logger.error(f"Error in cancel_order: {e}")
        await callback.answer(t("error", lang), show_alert=True)
