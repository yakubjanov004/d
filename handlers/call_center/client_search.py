from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from database.call_center_search_query import find_user_by_phone
from filters.role_filter import RoleFilter
from states.call_center_states import clientSearchStates
from database.queries import get_user_language   # tilni olish

router = Router()
router.message.filter(RoleFilter("callcenter_operator"))
router.callback_query.filter(RoleFilter("callcenter_operator"))

# Boshlash tugmasi
@router.message(F.text.in_(["🔍 Mijoz qidirish", "🔍 Поиск клиента"]))
async def client_search_handler(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"

    text = (
        "📞 Qidirish uchun mijoz telefon raqamini kiriting (masalan, +998901234567):"
        if lang == "uz"
        else "📞 Введите номер телефона клиента для поиска (например: +998901234567):"
    )

    await state.set_state(clientSearchStates.waiting_client_phone)
    await message.answer(text)

# Telefon raqamni qabul qilish
@router.message(StateFilter(clientSearchStates.waiting_client_phone))
async def process_client_phone(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id) or "uz"
    phone = message.text.strip()
    user = await find_user_by_phone(phone)

    if not user:
        text = (
            "❌ Bu raqam bo‘yicha mijoz topilmadi. Qayta urinib ko‘ring."
            if lang == "uz"
            else "❌ Клиент с таким номером не найден. Попробуйте снова."
        )
        return await message.answer(text)

    text = (
        "✅ Mijoz topildi:\n\n"
        f"🆔 ID: <b>{user.get('id')}</b>\n"
        f"👤 F.I.Sh: <b>{user.get('full_name') or '-'}</b>\n"
        f"📞 Telefon: <b>{user.get('phone') or '-'}</b>\n"
        f"🌐 Username: <b>@{user.get('username') or '-'}</b>\n"
        f"📍 Region: <b>{user.get('region') or '-'}</b>\n"
        f"🏠 Manzil: <b>{user.get('address') or '-'}</b>\n"
        f"🔑 Abonent ID: <b>{user.get('abonent_id') or '-'}</b>\n"
        if lang == "uz"
        else
        "✅ Клиент найден:\n\n"
        f"🆔 ID: <b>{user.get('id')}</b>\n"
        f"👤 ФИО: <b>{user.get('full_name') or '-'}</b>\n"
        f"📞 Телефон: <b>{user.get('phone') or '-'}</b>\n"
        f"🌐 Username: <b>@{user.get('username') or '-'}</b>\n"
        f"📍 Регион: <b>{user.get('region') or '-'}</b>\n"
        f"🏠 Адрес: <b>{user.get('address') or '-'}</b>\n"
        f"🔑 Абонент ID: <b>{user.get('abonent_id') or '-'}</b>\n"
    )

    await message.answer(text, parse_mode="HTML")
    await state.clear()
