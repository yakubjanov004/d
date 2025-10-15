from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging

from filters.role_filter import RoleFilter
from database.basic.user import find_user_by_telegram_id
from database.manager.orders import fetch_staff_activity
from database.basic.language import get_user_language

router = Router()
logger = logging.getLogger(__name__)
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

    operator_stats = await fetch_staff_activity()
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
                    f"   ├ Connection: {op['conn_count']} ta\n"
                    f"   └ Technician: {op['tech_count']} ta\n\n"
                )
            else:
                text += (
                    f"{i}. {op['full_name']}\n"
                    f"   ├ Подключение: {op['conn_count']} заявок\n"
                    f"   └ Техник: {op['tech_count']} заявок\n\n"
                )

    await message.answer(text, )
