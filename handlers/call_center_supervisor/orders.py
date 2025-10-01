from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text.in_(["📝 Buyurtmalar", "📝 Заказы"]))
async def orders_handler(message: Message):
    await message.answer("📝 Buyurtmalar\n\nBu yerda buyurtmalar boshqariladi.\n\n👤 Rol: Call Center Supervisor")
