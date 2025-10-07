

import asyncpg
from typing import Any, Dict, List, Optional
from config import settings

# =========================================================
#  User ma'lumotlari bilan ishlash
# =========================================================

async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Telegram ID orqali user ma'lumotlarini olish.
    Junior Manager uchun umumiy funksiya.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT id, telegram_id, role, language, full_name, username, phone, region, address,
                   abonent_id, is_blocked, created_at, updated_at
            FROM users
            WHERE telegram_id = $1
            LIMIT 1
            """,
            telegram_id,
        )
        return dict(row) if row else None
    finally:
        await conn.close()

# =========================================================
#  Junior Manager Inbox queries
# =========================================================

async def get_connections_by_recipient(recipient_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Junior Manager inboxdagi connections ro'yxati.
    Connection_orders va staff_orders bilan join qilib to'liq ma'lumot olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                c.id,
                c.sender_id,
                c.recipient_id,
                c.connection_id,
                c.technician_id,
                c.staff_id,
                c.created_at,
                c.updated_at,
                -- Connection orders ma'lumotlari
                co.id AS order_id,
                co.application_number,
                co.user_id AS order_user_id,
                co.region AS order_region,
                co.address AS order_address,
                co.status AS order_status,
                co.created_at AS order_created_at,
                co.updated_at AS order_updated_at,
                co.jm_notes AS order_jm_notes,
                -- Staff orders ma'lumotlari
                so.id AS staff_order_id,
                so.user_id AS staff_user_id,
                so.phone AS staff_phone,
                so.abonent_id AS staff_abonent_id,
                so.region AS staff_region,
                so.address AS staff_address,
                so.tarif_id AS staff_tarif_id,
                so.description AS staff_description,
                so.type_of_zayavka AS staff_type,
                so.status AS staff_status,
                so.created_at AS staff_created_at,
                so.updated_at AS staff_updated_at,
                so.jm_notes AS staff_jm_notes,
                -- Client ma'lumotlari (connection_orders uchun)
                u_co.full_name AS client_full_name,
                u_co.phone AS client_phone,
                -- Client ma'lumotlari (staff_orders uchun)
                u_so.full_name AS staff_client_full_name,
                u_so.phone AS staff_client_phone,
                -- Tariff ma'lumotlari
                t_co.name AS tariff_name,
                t_so.name AS staff_tariff_name
            FROM connections c
            LEFT JOIN connection_orders co ON co.id = c.connection_id
            LEFT JOIN staff_orders so ON so.id = c.staff_id
            LEFT JOIN users u_co ON u_co.id = co.user_id
            LEFT JOIN users u_so ON u_so.id = so.user_id
            LEFT JOIN tarif t_co ON t_co.id = co.tarif_id
            LEFT JOIN tarif t_so ON t_so.id = so.tarif_id
            WHERE c.recipient_id = $1
            ORDER BY c.created_at DESC
            LIMIT $2
            """,
            recipient_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_connection_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """
    Connection order ma'lumotlarini ID bo'yicha olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT
                co.id,
                co.application_number,
                co.user_id,
                co.region,
                co.address,
                co.status,
                co.created_at,
                co.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff_name
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.id = $1
            """,
            order_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def get_staff_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """
    Staff order ma'lumotlarini ID bo'yicha olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT
                so.id,
                so.user_id,
                so.phone,
                so.abonent_id,
                so.region,
                so.address,
                so.tarif_id,
                so.description,
                so.type_of_zayavka,
                so.status,
                so.is_active,
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff_name
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.id = $1
            """,
            order_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def move_order_to_controller(order_id: int, jm_id: int) -> Dict[str, Any]:
    """
    Junior Manager -> Controller: order statusini yangilash.
    Both connection_orders and staff_orders ni qo'llab-quvvatlaydi.
    
    Returns:
        Dict with controller info for notification
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # Controller ma'lumotlarini olamiz
            controller_info = await conn.fetchrow(
                "SELECT id, telegram_id, language FROM users WHERE role = 'controller' ORDER BY id ASC LIMIT 1"
            )
            if not controller_info:
                raise ValueError("Controller topilmadi")
            
            controller_id = controller_info["id"]
            
            # Check if it's a connection order
            connection_order = await conn.fetchrow(
                "SELECT id, application_number FROM connection_orders WHERE id = $1", order_id
            )
            
            app_number = None
            order_type = "staff"
            
            if connection_order:
                # Update connection order status
                await conn.execute(
                    """
                    UPDATE connection_orders
                    SET status = 'in_controller',
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    order_id
                )
                app_number = connection_order["application_number"]
                order_type = "connection"
            else:
                # Check if it's a staff order
                staff_order = await conn.fetchrow(
                    "SELECT id, application_number FROM staff_orders WHERE id = $1", order_id
                )
                
                if staff_order:
                    # Update staff order status
                    await conn.execute(
                        """
                        UPDATE staff_orders
                        SET status = 'in_controller',
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        order_id
                    )
                    app_number = staff_order["application_number"]
                    order_type = "staff"
                else:
                    raise ValueError("Order topilmadi")
            
            # Connection yozuvini yaratish
            await conn.execute(
                """
                INSERT INTO connections (sender_id, recipient_id, connection_id, staff_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                """,
                jm_id, controller_id, order_id if order_type == "connection" else None, order_id if order_type == "staff" else None
            )
            
            # Controller'ning hozirgi yuklamasini hisoblaymiz
            current_load = await conn.fetchval(
                """
                WITH last_conn AS (
                    SELECT DISTINCT ON (COALESCE(c.connection_id, c.staff_id))
                           COALESCE(c.connection_id, c.staff_id) as order_id,
                           c.recipient_id,
                           c.recipient_status
                    FROM connections c
                    WHERE COALESCE(c.connection_id, c.staff_id) IS NOT NULL
                    ORDER BY COALESCE(c.connection_id, c.staff_id), c.created_at DESC
                )
                SELECT COUNT(*)
                FROM last_conn lc
                LEFT JOIN connection_orders co ON co.id = lc.order_id AND co.is_active = TRUE AND co.status = 'in_controller'
                LEFT JOIN staff_orders so ON so.id = lc.order_id AND COALESCE(so.is_active, TRUE) = TRUE AND so.status = 'in_controller'
                WHERE lc.recipient_id = $1
                  AND (co.id IS NOT NULL OR so.id IS NOT NULL)
                  AND lc.recipient_status = 'in_controller'
                """,
                controller_id
            )
            
            return {
                "telegram_id": controller_info["telegram_id"],
                "language": controller_info["language"] or "uz",
                "application_number": app_number,
                "order_type": order_type,
                "current_load": current_load or 0
            }
    except Exception as e:
        raise e
    finally:
        await conn.close()

async def set_jm_notes(order_id: int, notes: str) -> bool:
    """
    Junior Manager notes qo'shish.
    Both connection_orders and staff_orders ni qo'llab-quvvatlaydi.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Check if it's a connection order
        connection_order = await conn.fetchrow(
            "SELECT id FROM connection_orders WHERE id = $1", order_id
        )
        
        if connection_order:
            # Update connection order notes
            await conn.execute(
                """
                UPDATE connection_orders
                SET jm_notes = $1,
                    updated_at = NOW()
                WHERE id = $2
                """,
                notes, order_id
            )
        else:
            # Check if it's a staff order
            staff_order = await conn.fetchrow(
                "SELECT id FROM staff_orders WHERE id = $1", order_id
            )
            
            if staff_order:
                # Update staff order notes
                await conn.execute(
                    """
                    UPDATE staff_orders
                    SET jm_notes = $1,
                        updated_at = NOW()
                    WHERE id = $2
                    """,
                    notes, order_id
                )
            else:
                return False  # Order not found
        
        return True
    except Exception:
        return False
    finally:
        await conn.close()