from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from database.basic.rating import save_rating
from states.client_states import RatingStates
from keyboards.client_buttons import get_rating_keyboard, get_skip_comment_keyboard
from utils.akt_service import AKTService
import logging

logger = logging.getLogger(__name__)
router = Router()

async def create_and_send_akt_after_rating(request_id: int, request_type: str):
    """
    Rating qilgandan so'ng AKT yaratish va yuborish.
    """
    try:
        from loader import bot
        
        # AKT service orqali AKT yaratish va yuborish
        akt_service = AKTService()
        await akt_service.post_completion_pipeline(bot, request_id, request_type)
        
        logger.info(f"AKT created and sent after rating for {request_type} request {request_id}")
        
    except Exception as e:
        logger.error(f"Error creating AKT after rating: {e}")
        # AKT xatosi clientga ko'rinmaydi, faqat log qilinadi

@router.callback_query(F.data.startswith("rate:") | F.data.startswith("skip_comment:"))
async def handle_rating_callback(callback: types.CallbackQuery, state: FSMContext):
    """
    Reyting callback ni boshqarish
    """
    try:
        data = callback.data.split(":")
        action = data[0]
        
        if action == "rate":
            request_id = int(data[1])
            request_type = data[2]
            rating = int(data[3])
            
            # Reytingni saqlash
            await save_rating(request_id, request_type, rating)
            
            # Inline keyboard ni o'chirish va yangi xabar yuborish
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer("✅ Reyting saqlandi!", show_alert=False)
            await callback.message.answer(
                "✅ <b>Reyting saqlandi!</b>\n\n"
                "💬 Ixtiyoriy izoh qoldiring (yoki 'O'tkazib yuborish' tugmasini bosing):",
                parse_mode='HTML',
                reply_markup=get_skip_comment_keyboard(request_id, request_type)
            )
            
            # State ga o'tish
            await state.set_state(RatingStates.waiting_for_comment)
            await state.update_data(request_id=request_id, request_type=request_type, rating=rating)
            
        elif action == "skip_comment":
            request_id = int(data[1])
            request_type = data[2]
            
            # Izohsiz saqlash - rating 0 o'rniga hech narsa saqlamaymiz
            # yoki oldindan saqlangan ratingni izohsiz qoldiramiz
            
            # Inline keyboard ni o'chirish
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer("✅ Reyting saqlandi!", show_alert=True)
            await callback.message.answer(
                "✅ <b>Reyting saqlandi!</b>\n\n"
                "Tashakkur! Sizning bahoingiz biz uchun muhim.",
                parse_mode='HTML'
            )
            
            # Rating qilgandan so'ng AKT yaratish va yuborish
            await create_and_send_akt_after_rating(request_id, request_type)
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in handle_rating_callback: {e}")
        await callback.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)

@router.message(RatingStates.waiting_for_comment)
async def handle_comment_message(message: types.Message, state: FSMContext):
    """
    Izoh xabarini boshqarish
    """
    try:
        data = await state.get_data()
        request_id = data['request_id']
        request_type = data['request_type']
        rating = data['rating']
        comment = message.text
        
        # Reyting va izohni saqlash
        await save_rating(request_id, request_type, rating, comment)
        
        await message.answer(
            "✅ <b>Reyting saqlandi!</b>\n\n"
            "Tashakkur! Sizning bahoingiz va izohingiz biz uchun muhim.",
            parse_mode='HTML'
        )
        
        # Rating va comment qilgandan so'ng AKT yaratish va yuborish
        await create_and_send_akt_after_rating(request_id, request_type)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in handle_comment_message: {e}")
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")

@router.callback_query(F.data == "rating_stats")
async def handle_rating_stats_callback(callback: types.CallbackQuery):
    """
    Reyting statistikalarini ko'rsatish
    """
    try:
        from database.basic.rating import get_rating_stats
        
        stats = await get_rating_stats()
        
        if not stats or stats.get('total_ratings', 0) == 0:
            await callback.message.edit_text(
                "📊 <b>Reyting statistikasi</b>\n\n"
                "Hozircha hech qanday reyting yo'q.",
                parse_mode='HTML'
            )
            return
        
        avg_rating = stats.get('avg_rating', 0)
        total_ratings = stats.get('total_ratings', 0)
        
        text = f"📊 <b>Reyting statistikasi</b>\n\n"
        text += f"⭐ O'rtacha reyting: {avg_rating:.1f}/5\n"
        text += f"📈 Jami baholar: {total_ratings}\n\n"
        
        # Yulduzlar taqsimoti
        for i in range(5, 0, -1):
            count = stats.get(f'{i}_stars', 0)
            percentage = (count / total_ratings * 100) if total_ratings > 0 else 0
            stars = "⭐" * i
            text += f"{stars}: {count} ({percentage:.1f}%)\n"
        
        await callback.message.edit_text(text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in handle_rating_stats_callback: {e}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)

@router.callback_query(F.data == "my_ratings")
async def handle_my_ratings_callback(callback: types.CallbackQuery):
    """
    Foydalanuvchining o'z reytinglarini ko'rsatish
    """
    try:
        from database.basic.user import find_user_by_telegram_id
        from database.basic.rating import get_rating
        
        user = await find_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
            return
        
        # Bu yerda foydalanuvchining reytinglarini olish kerak
        # Hozircha oddiy xabar
        await callback.message.edit_text(
            "📝 <b>Sizning reytinglaringiz</b>\n\n"
            "Bu funksiya hozir ishlab chiqilmoqda...",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in handle_my_ratings_callback: {e}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
