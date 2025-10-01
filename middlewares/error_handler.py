from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from utils.universal_error_logger import log_error
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
            
            # Xatolikni log qilish
            log_error(
                error=e,
                context=context,
                user_id=user_id,
                additional_data={
                    "event_type": type(event).__name__,
                    "traceback": traceback.format_exc()
                }
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
                log_error(
                    error=notify_error,
                    context="Error while notifying user about error",
                    user_id=user_id
                )
            
            # Xatolikni qayta ko'tarmaslik uchun None qaytaramiz
            return None