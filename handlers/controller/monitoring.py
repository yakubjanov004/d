from aiogram import Router, F
from aiogram.types import Message
from filters.role_filter import RoleFilter

router = Router()

@router.message(RoleFilter("controller"), F.text.in_(["📊 Monitoring", "📊 Мониторинг"]))
async def monitoring_handler(message: Message):
    await message.answer("📊 Monitoring\n\nBu yerda monitoring ko'rsatiladi.\n\n👤 Rol: Controller")
