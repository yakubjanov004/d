from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
import logging
import traceback

class ErrorHandlingMiddleware(BaseMiddleware):
    """Xatoliklarni ushlab, log qiluvchi va foydalanuvchiga xabar beruvchi middleware"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            # Asosiy handler'ni chaqirish
            return await handler(event, data)
        except Exception as e:
            # Logger'ni olish
            logger = logging.getLogger(__name__)
            
            # Xatolikni log qilish
            user_id = None
            chat_id = None
            
            # Event turini aniqlash va tegishli ma'lumotlarni olish
            if isinstance(event, Message):
                user_id = event.from_user.id if event.from_user else None
                chat_id = event.chat.id
                context = f"Message handler: {event.text}"
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id if event.from_user else None
                chat_id = event.message.chat.id if event.message else None
                context = f"Callback handler: {event.data}"
            else:
                context = f"Unknown event type: {type(event).__name__}"
            
            # Xatolikni log qilish - logger.exception() ishlatish
            logger.exception(
                f"Handler error - {context} | User: {user_id} | Chat: {chat_id}",
                exc_info=True
            )
            
            # Foydalanuvchiga xatolik haqida xabar berish
            try:
                if chat_id:
                    if isinstance(event, Message):
                        # Message obyektida to'g'ridan-to'g'ri answer metodi yo'q
                        # bot obyekti orqali xabar yuboramiz
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text="❌ Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring. "
                            "Agar muammo davom etsa, administratorga murojaat qiling."
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer(
                            "❌ Xatolik yuz berdi",
                            show_alert=True
                        )
                        if event.message:
                            await self.bot.send_message(
                                chat_id=chat_id,
                                text="❌ Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring. "
                                "Agar muammo davom etsa, administratorga murojaat qiling."
                            )
            except Exception as notify_error:
                # Foydalanuvchiga xabar berishda ham xatolik yuz bersa, uni ham log qilamiz
                logger.exception(
                    f"Error while notifying user about error | User: {user_id}",
                    exc_info=True
                )
            
            # Xatolikni qayta ko'tarmaslik uchun None qaytaramiz
            return None