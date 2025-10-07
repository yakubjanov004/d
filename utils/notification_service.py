# utils/notification_service.py

from aiogram import Bot
from typing import Optional, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def send_role_notification(
    bot: Bot,
    recipient_telegram_id: int,
    order_id: str,
    order_type: str,  # 'connection' | 'technician' | 'staff'
    current_load: int,
    lang: str = "uz"
) -> bool:
    """
    Rol o'zgarishida recipient'ga notification yuborish.
    State'ga ta'sir qilmaydi - faqat oddiy xabar yuboradi.
    
    Args:
        bot: Aiogram Bot instance
        recipient_telegram_id: Qabul qiluvchining telegram ID'si
        order_id: Ariza ID'si (masalan: CONN-B2B-0029)
        order_type: Ariza turi
        current_load: Hozirgi yuklama (qancha ariza bor)
        lang: Til (uz/ru)
    
    Returns:
        True - yuborildi, False - xatolik
    """
    try:
        # Ariza turini til bo'yicha formatlash
        if lang == "ru":
            if order_type == "connection":
                order_type_text = "подключения"
            elif order_type == "technician":
                order_type_text = "технической"
            else:
                order_type_text = "сотрудника"
        else:
            if order_type == "connection":
                order_type_text = "ulanish"
            elif order_type == "technician":
                order_type_text = "texnik xizmat"
            else:
                order_type_text = "xodim"
        
        # Notification matnini tayyorlash
        if lang == "ru":
            message = f"📬 <b>Новая заявка {order_type_text}</b>\n\n🆔 {order_id}\n\n📊 У вас теперь <b>{current_load}</b> активных заявок"
        else:
            message = f"📬 <b>Yangi {order_type_text} arizasi</b>\n\n🆔 {order_id}\n\n📊 Sizda yana <b>{current_load}ta</b> ariza bor"
        
        # Xabarni yuborish (state'ga ta'sir qilmaydi)
        await bot.send_message(
            chat_id=recipient_telegram_id,
            text=message,
            parse_mode="HTML"
        )
        
        logger.info(f"Notification sent to {recipient_telegram_id} for order {order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send notification to {recipient_telegram_id}: {e}")
        return False


async def send_group_notification_for_staff_order(
    bot: Bot,
    order_id: str,
    order_type: str,  # 'connection' | 'technician' | 'staff'
    client_name: str,
    client_phone: str,
    creator_name: str,
    creator_role: str,  # 'junior_manager' | 'manager' | 'controller' | 'call_center' | 'call_center_supervisor'
    region: str,
    address: str,
    tariff_name: str = None,
    description: str = None,  # Texnik xizmat uchun muammo tavsifi
    business_type: str = "B2C"
) -> bool:
    """
    Xodimlar tomonidan yaratilgan arizalar uchun guruhga xabar yuborish.
    Faqat o'zbek tilida yuboriladi.
    
    Args:
        bot: Aiogram Bot instance
        order_id: Ariza ID'si (masalan: STAFF-CONN-B2B-0034)
        order_type: Ariza turi
        client_name: Mijoz ismi
        client_phone: Mijoz telefoni
        creator_name: Ariza yaratgan xodim ismi
        creator_role: Ariza yaratgan xodim roli
        region: Viloyat
        address: Manzil
        tariff_name: Tarif nomi (ixtiyoriy)
        description: Muammo tavsifi (texnik xizmat uchun)
        business_type: Biznes turi (B2C/B2B)
    
    Returns:
        True - yuborildi, False - xatolik
    """
    try:
        from config import settings
        
        if not settings.ZAYAVKA_GROUP_ID:
            logger.warning("ZAYAVKA_GROUP_ID not configured")
            return False
        
        # Ariza turini formatlash
        if order_type == "connection":
            order_type_text = "ulanish"
        elif order_type == "technician":
            order_type_text = "texnik xizmat"
        else:
            order_type_text = "xodim"
        
        # Yaratgan xodim roli
        role_texts = {
            'junior_manager': 'Junior Manager',
            'manager': 'Manager',
            'controller': 'Controller',
            'call_center': 'Call Center',
            'call_center_supervisor': 'Call Center Supervisor'
        }
        
        creator_role_text = role_texts.get(creator_role, creator_role)
        
        # Tarif qismini tayyorlash
        tariff_section = ""
        if tariff_name:
            tariff_section = f"💳 <b>Tarif:</b> {tariff_name}\n"
        
        # Xabar matnini tayyorlash (faqat o'zbek tilida)
        if order_type == "connection":
            message = (
                f"🔌 <b>YANGI ULANISH ARIZASI</b>\n"
                f"👨‍💼 <b>Xodim yaratgan ariza</b>\n"
                f"{'='*30}\n"
                f"🆔 <b>ID:</b> <code>{order_id}</code>\n"
                f"👤 <b>Mijoz:</b> {client_name}\n"
                f"📞 <b>Tel:</b> {client_phone}\n"
                f"👨‍💼 <b>Yaratdi:</b> {creator_name} ({creator_role_text})\n"
                f"🏢 <b>Region:</b> {region}\n"
                f"{tariff_section}"
                f"📍 <b>Manzil:</b> {address}\n"
                f"🕐 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"{'='*30}"
            )
        elif order_type == "technician":
            # Muammo qismini tayyorlash
            problem_section = ""
            if description:
                problem_section = f"🔧 <b>Muammo:</b> {description}\n"
            
            message = (
                f"🔧 <b>YANGI TEKNIK XIZMAT ARIZASI</b>\n"
                f"👨‍💼 <b>Xodim yaratgan ariza</b>\n"
                f"{'='*30}\n"
                f"🆔 <b>ID:</b> <code>{order_id}</code>\n"
                f"👤 <b>Mijoz:</b> {client_name}\n"
                f"📞 <b>Tel:</b> {client_phone}\n"
                f"👨‍💼 <b>Yaratdi:</b> {creator_name} ({creator_role_text})\n"
                f"🏢 <b>Region:</b> {region}\n"
                f"{problem_section}"
                f"📍 <b>Manzil:</b> {address}\n"
                f"🕐 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"{'='*30}"
            )
        else:
            message = (
                f"👥 <b>YANGI XODIM ARIZASI</b>\n"
                f"👨‍💼 <b>Xodim yaratgan ariza</b>\n"
                f"{'='*30}\n"
                f"🆔 <b>ID:</b> <code>{order_id}</code>\n"
                f"👤 <b>Mijoz:</b> {client_name}\n"
                f"📞 <b>Tel:</b> {client_phone}\n"
                f"👨‍💼 <b>Yaratdi:</b> {creator_name} ({creator_role_text})\n"
                f"🏢 <b>Region:</b> {region}\n"
                f"📍 <b>Manzil:</b> {address}\n"
                f"🕐 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"{'='*30}"
            )
        
        # Xabarni guruhga yuborish
        await bot.send_message(
            chat_id=settings.ZAYAVKA_GROUP_ID,
            text=message,
            parse_mode="HTML"
        )
        
        logger.info(f"Group notification sent for staff order {order_id} created by {creator_role}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send group notification for staff order {order_id}: {e}")
        return False


async def get_recipient_load(
    recipient_id: int,
    role: str,
    order_type: str = "connection"
) -> int:
    """
    Recipient'ning hozirgi yuklamasini olish.
    
    Args:
        recipient_id: User database ID
        role: User roli (junior_manager, controller, technician)
        order_type: Ariza turi
    
    Returns:
        Aktiv arizalar soni
    """
    from database.connections import get_connection_url
    import asyncpg
    
    try:
        conn = await asyncpg.connect(get_connection_url())
        try:
            if role == "junior_manager":
                # Junior manager uchun connection_orders hisoblaymiz
                count = await conn.fetchval(
                    """
                    WITH last_assign AS (
                        SELECT DISTINCT ON (c.connection_id)
                               c.connection_id,
                               c.recipient_id,
                               c.recipient_status
                        FROM connections c
                        WHERE c.connection_id IS NOT NULL
                        ORDER BY c.connection_id, c.created_at DESC
                    )
                    SELECT COUNT(*)
                    FROM last_assign la
                    JOIN connection_orders co ON co.id = la.connection_id
                    WHERE la.recipient_id = $1
                      AND co.is_active = TRUE
                      AND co.status = 'in_junior_manager'
                      AND la.recipient_status = 'in_junior_manager'
                    """,
                    recipient_id
                )
            elif role == "controller":
                # Controller uchun staff_orders hisoblaymiz
                count = await conn.fetchval(
                    """
                    WITH last_assign AS (
                        SELECT DISTINCT ON (c.staff_id)
                               c.staff_id,
                               c.recipient_id,
                               c.recipient_status
                        FROM connections c
                        WHERE c.staff_id IS NOT NULL
                        ORDER BY c.staff_id, c.created_at DESC
                    )
                    SELECT COUNT(*)
                    FROM last_assign la
                    JOIN staff_orders so ON so.id = la.staff_id
                    WHERE la.recipient_id = $1
                      AND COALESCE(so.is_active, TRUE) = TRUE
                      AND so.status = 'in_controller'
                      AND la.recipient_status = 'in_controller'
                    """,
                    recipient_id
                )
            elif role == "technician":
                # Technician uchun ham staff_orders hisoblaymiz
                count = await conn.fetchval(
                    """
                    WITH last_assign AS (
                        SELECT DISTINCT ON (c.staff_id)
                               c.staff_id,
                               c.recipient_id,
                               c.recipient_status
                        FROM connections c
                        WHERE c.staff_id IS NOT NULL
                        ORDER BY c.staff_id, c.created_at DESC
                    )
                    SELECT COUNT(*)
                    FROM last_assign la
                    JOIN staff_orders so ON so.id = la.staff_id
                    WHERE la.recipient_id = $1
                      AND COALESCE(so.is_active, TRUE) = TRUE
                      AND so.status IN ('between_controller_technician', 'in_technician')
                      AND la.recipient_status IN ('between_controller_technician', 'in_technician')
                    """,
                    recipient_id
                )
            else:
                return 0
            
            return count or 0
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to get recipient load: {e}")
        return 0

