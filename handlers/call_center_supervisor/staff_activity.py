from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from filters.role_filter import RoleFilter
from database.queries import find_user_by_telegram_id
from database.call_supervisor_static_queries import get_operator_orders_stat
from database.language_queries import get_user_language

router = Router()
router.message.filter(RoleFilter("callcenter_supervisor"))
router.callback_query.filter(RoleFilter("callcenter_supervisor"))

# --- UI ---
async def _back_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    lang = await get_user_language(telegram_id) or "uz"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                callback_data="staff:back"
            )]
        ]
    )

# --- Asosiy handler ---
@router.message(F.text.in_(["👥 Xodimlar faoliyati", "👥 Активность сотрудников"]))
async def staff_activity_entry(message: Message, state: FSMContext):
    """Hodimlar faoliyatini tanlaganda — darhol hodimlar kesimi chiqadi."""
    lang = await get_user_language(message.from_user.id) or "uz"

    operator_stats = await get_operator_orders_stat()
    if not operator_stats:
        text = (
            "📊 Hozircha hech bir operator ariza yaratmagan."
            if lang == "uz"
            else "📊 Пока что ни один оператор не создал заявку."
        )
    else:
        text = (
            "📊 Hodimlar kesimi:\n\n"
            if lang == "uz" else
            "📊 Срез по сотрудникам:\n\n"
        )
        for i, op in enumerate(operator_stats, 1):
            if lang == "uz":
                text += (
                    f"{i}. {op['full_name']}\n"
                    f"   ├ Connection: {op['connection_count']} ta\n"
                    f"   └ Technician: {op['technician_count']} ta\n\n"
                )
            else:
                text += (
                    f"{i}. {op['full_name']}\n"
                    f"   ├ Подключение: {op['connection_count']} заявок\n"
                    f"   └ Техник: {op['technician_count']} заявок\n\n"
                )

    await message.answer(text, )
