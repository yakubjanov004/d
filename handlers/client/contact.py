from aiogram import Router, F
from aiogram.types import Message
from keyboards.client_buttons import get_contact_options_keyboard, get_client_main_menu
from database.basic.language import get_user_language

router = Router()

@router.message(F.text.in_(["📞 Operator bilan bog'lanish", "📞 Связаться с оператором"]))
async def contact_handler(message: Message):
    user_lang = await get_user_language(message.from_user.id)

    if user_lang == "ru":
        contact_text = (
            "📞 <b>Связаться с нами</b>\n\n"
            "📱 <b>Телефон:</b> +998 71 123 45 67\n"
            "📧 <b>Email:</b> info@alfaconnect.uz\n"
            "🌐 <b>Веб-сайт:</b> www.alfaconnect.uz\n"
            "📍 <b>Адрес:</b> г. Ташкент, Юнусабадский район\n"
            "⏰ <b>Рабочее время:</b> Понедельник - Суббота, 9:00 - 18:00\n\n"
            "💬 <b>Telegram канал:</b> @alfaconnect_uz"
        )
    else:
        contact_text = (
            "📞 <b>Biz bilan bog'lanish</b>\n\n"
            "📱 <b>Telefon:</b> +998 71 123 45 67\n"
            "📧 <b>Email:</b> info@alfaconnect.uz\n"
            "🌐 <b>Veb-sayt:</b> www.alfaconnect.uz\n"
            "📍 <b>Manzil:</b> Toshkent shahri, Yunusobod tumani\n"
            "⏰ <b>Ish vaqti:</b> Dushanba - Shanba, 9:00 - 18:00\n\n"
            "💬 <b>Telegram kanal:</b> @alfaconnect_uz"
        )

    keyboard = get_contact_options_keyboard(user_lang)
    await message.answer(contact_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text.in_(["📞 Qo'ng'iroq qilish", "📞 Позвонить"]))
async def call_operator_handler(message: Message):
    user_lang = await get_user_language(message.from_user.id)

    call_text = (
        "📞 Qo'ng'iroq qilish\n\n"
        "Operator bilan bog'lanish uchun quyidagi raqamga qo'ng'iroq qiling:\n\n"
        "📱 +998 71 200 08 00\n\n"
        "⏰ Ish vaqti: 09:00 - 18:00 (Dushanba-Juma)"
    ) if user_lang == "uz" else (
        "📞 Позвонить\n\n"
        "Для связи с оператором позвоните по номеру:\n\n"
        "📱 +998 71 200 08 00\n\n"
        "⏰ Рабочее время: 09:00 - 18:00 (Понедельник-Пятница)"
    )

    await message.answer(call_text)


@router.message(F.text.in_(["◀️ Orqaga", "◀️ Назад"]))
async def back_to_main_menu_handler(message: Message):
    user_lang = await get_user_language(message.from_user.id)

    back_text = (
        "🏠 Bosh menyu\n\n"
        "Kerakli bo'limni tanlang:"
    ) if user_lang == "uz" else (
        "🏠 Главное меню\n\n"
        "Выберите нужный раздел:"
    )

    keyboard = get_client_main_menu(user_lang)
    await message.answer(back_text, reply_markup=keyboard)
