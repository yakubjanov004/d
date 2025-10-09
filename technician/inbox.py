# handlers/technician/inbox.py (refactored - main entry point only)
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from filters.role_filter import RoleFilter
from database.basic.user import find_user_by_telegram_id
from .shared_utils import t, resolve_lang, tech_category_keyboard
import logging

logger = logging.getLogger(__name__)

# ====== Router ======
router = Router()
router.message.filter(RoleFilter("technician"))

# =====================
# Main Inbox Handler
# =====================
@router.message(F.text.in_(["📥 Inbox", "Inbox", "📥 Входящие"]))
async def tech_open_inbox(message: Message, state: FSMContext):
    user = await find_user_by_telegram_id(message.from_user.id)
    if not user or user.get("role") != "technician":
        return
    lang = await resolve_lang(message.from_user.id, fallback=("ru" if message.text == "📥 Входящие" else "uz"))
    await state.update_data(tech_mode=None, tech_inbox=[], tech_idx=0, lang=lang)
    await message.answer(t("choose_section", lang), reply_markup=tech_category_keyboard(lang))