# utils/completion_notification.py
"""
Ariza yakunlanganda clientga notification yuborish va rating so'rash.
Barcha ariza turlari uchun ishlatiladi.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from database.basic.user import get_user_by_telegram_id
from keyboards.client_buttons import get_rating_keyboard

logger = logging.getLogger(__name__)

async def send_completion_notification_to_client(bot, request_id: int, request_type: str):
    """
    Texnik ishni yakunlagandan so'ng clientga ariza haqida to'liq ma'lumot yuborish va rating so'rash.
    AKT yuborilmaydi - faqat ma'lumot va rating tizimi.
    
    Args:
        bot: Aiogram Bot instance
        request_id: Ariza IDsi
        request_type: Ariza turi ('connection', 'technician', 'staff')
    """
    try:
        # Client ma'lumotlarini olish
        client_data = await get_client_data_for_notification(request_id, request_type)
        if not client_data or not client_data.get('client_telegram_id'):
            logger.warning(f"No client data found for {request_type} request {request_id}")
            return

        client_telegram_id = client_data['client_telegram_id']
        client_lang = client_data.get('client_lang', 'uz')
        
        # Ariza turini til bo'yicha formatlash
        if client_lang == "ru":
            if request_type == "connection":
                order_type_text = "подключения"
            elif request_type == "technician":
                order_type_text = "технической"
            else:
                order_type_text = "сотрудника"
        else:
            if request_type == "connection":
                order_type_text = "ulanish"
            elif request_type == "technician":
                order_type_text = "texnik xizmat"
            else:
                order_type_text = "xodim"

        # Ishlatilgan materiallarni olish
        materials_info = await get_used_materials_info(request_id, request_type, client_lang)
        
        # Diagnostika ma'lumotini olish (texnik xizmat uchun)
        diagnosis_info = await get_diagnosis_info(request_id, request_type, client_lang)

        # Notification matnini tayyorlash
        if client_lang == "ru":
            message = (
                "✅ <b>Работа завершена!</b>\n\n"
                f"📋 Заявка {order_type_text}: #{request_id}\n"
                f"📅 Дата завершения: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            )
            
            if diagnosis_info:
                message += f"🔧 <b>Выполненные работы:</b>\n{diagnosis_info}\n\n"
            
            if materials_info:
                message += f"📦 <b>Использованные материалы:</b>\n{materials_info}\n\n"
            
            message += "<i>Пожалуйста, оцените качество нашей работы:</i>"
        else:
            message = (
                "✅ <b>Ish yakunlandi!</b>\n\n"
                f"📋 {order_type_text} arizasi: #{request_id}\n"
                f"📅 Yakunlangan sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            )
            
            if diagnosis_info:
                message += f"🔧 <b>Bajarilgan ishlar:</b>\n{diagnosis_info}\n\n"
            
            if materials_info:
                message += f"📦 <b>Ishlatilgan materiallar:</b>\n{materials_info}\n\n"
            
            message += "<i>Iltimos, xizmatimizni baholang:</i>"

        # Rating keyboard yaratish
        rating_keyboard = get_rating_keyboard(request_id, request_type)
        
        # Xabarni yuborish
        await bot.send_message(
            chat_id=client_telegram_id,
            text=message,
            parse_mode='HTML',
            reply_markup=rating_keyboard
        )
        
        logger.info(f"Completion notification sent to client {client_telegram_id} for {request_type} request {request_id}")
        
    except Exception as e:
        logger.error(f"Error sending completion notification to client: {e}")
        raise

async def get_client_data_for_notification(request_id: int, request_type: str):
    """
    Client ma'lumotlarini olish notification uchun.
    """
    from database.connections import get_connection_url
    import asyncpg
    
    try:
        conn = await asyncpg.connect(get_connection_url())
        try:
            if request_type == "connection":
                query = """
                    SELECT 
                        u.telegram_id AS client_telegram_id,
                        u.language as client_lang,
                        u.full_name AS client_name,
                        u.phone AS client_phone,
                        co.address
                    FROM connection_orders co
                    LEFT JOIN users u ON u.id = co.user_id
                    WHERE co.id = $1
                """
            elif request_type == "technician":
                query = """
                    SELECT 
                        u.telegram_id AS client_telegram_id,
                        u.language as client_lang,
                        u.full_name AS client_name,
                        u.phone AS client_phone,
                        t.address
                    FROM technician_orders t
                    LEFT JOIN users u ON u.id = t.user_id
                    WHERE t.id = $1
                """
            elif request_type == "staff":
                query = """
                    SELECT 
                        u.telegram_id AS client_telegram_id,
                        u.language as client_lang,
                        u.full_name AS client_name,
                        u.phone AS client_phone,
                        s.address
                    FROM staff_orders s
                    LEFT JOIN users u ON u.id = s.user_id
                    WHERE s.id = $1
                """
            else:
                return None
                
            result = await conn.fetchrow(query, request_id)
            return dict(result) if result else None
            
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error getting client data: {e}")
        return None

async def get_used_materials_info(request_id: int, request_type: str, client_lang: str = "uz"):
    """
    Ishlatilgan materiallar haqida ma'lumot olish.
    """
    try:
        from database.connections import get_connection_url
        import asyncpg
        
        conn = await asyncpg.connect(get_connection_url())
        try:
            if request_type == "connection":
                query = """
                    SELECT 
                        mr.material_name,
                        mr.quantity,
                        mr.price
                    FROM material_requests mr
                    WHERE mr.connection_id = $1
                    ORDER BY mr.created_at
                """
            elif request_type == "technician":
                query = """
                    SELECT 
                        mr.material_name,
                        mr.quantity,
                        mr.price
                    FROM material_requests mr
                    WHERE mr.technician_id = $1
                    ORDER BY mr.created_at
                """
            elif request_type == "staff":
                query = """
                    SELECT 
                        mr.material_name,
                        mr.quantity,
                        mr.price
                    FROM material_requests mr
                    WHERE mr.staff_id = $1
                    ORDER BY mr.created_at
                """
            else:
                return ""
                
            materials = await conn.fetch(query, request_id)
            
            if not materials:
                return "• Hech qanday material ishlatilmagan" if client_lang == "uz" else "• Материалы не использовались"
            
            materials_text = []
            for mat in materials:
                name = mat['material_name'] or "Noma'lum"
                qty = mat['quantity'] or 0
                price = mat['price'] or 0
                total_price = qty * price
                
                if client_lang == "ru":
                    materials_text.append(f"• {name} — {qty} шт. (💰 {_fmt_price_uzs(total_price)} сум)")
                else:
                    materials_text.append(f"• {name} — {qty} dona (💰 {_fmt_price_uzs(total_price)} so'm)")
            
            return "\n".join(materials_text)
            
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error getting materials info: {e}")
        return ""

async def get_diagnosis_info(request_id: int, request_type: str, client_lang: str = "uz"):
    """
    Diagnostika ma'lumotini olish (faqat texnik xizmat uchun).
    """
    try:
        if request_type != "technician":
            return ""
            
        from database.connections import get_connection_url
        import asyncpg
        
        conn = await asyncpg.connect(get_connection_url())
        try:
            query = """
                SELECT diagnosis_text
                FROM technician_orders
                WHERE id = $1 AND diagnosis_text IS NOT NULL
            """
            
            result = await conn.fetchval(query, request_id)
            
            if not result:
                return ""
            
            # Diagnostika matnini qisqartirish
            diagnosis = result.strip()
            if len(diagnosis) > 200:
                diagnosis = diagnosis[:200] + "..."
            
            return diagnosis
            
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error getting diagnosis info: {e}")
        return ""

def _fmt_price_uzs(val) -> str:
    try:
        s = f"{int(val):,}"
        return s.replace(",", " ")
    except Exception:
        return str(val)

async def ensure_akt_for_all_order_types():
    """
    Barcha ariza turlari uchun AKT yuborishni ta'minlash.
    Bu funksiya barcha joylarda ariza yakunlanganda chaqiriladi.
    """
    # Bu funksiya barcha ariza turlari uchun umumiy AKT yuborishni ta'minlaydi
    # Hozirgi holatda faqat technician va CC operator uchun ishlatiladi
    pass
