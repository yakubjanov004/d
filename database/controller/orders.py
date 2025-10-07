# database/controller/orders.py

from typing import Dict, Any, Optional, List
import asyncpg
import logging
from config import settings

logger = logging.getLogger(__name__)

# =========================================================
#  Controller Orders yaratish
# =========================================================

async def ensure_user_controller(telegram_id: int, full_name: str, username: str) -> Dict[str, Any]:
    """
    Controller uchun user yaratish/yangilash.
    """
    from database.basic.user import ensure_user
    return await ensure_user(telegram_id, full_name, username, 'controller')

async def staff_orders_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    tarif_id: Optional[int],
    business_type: str = "B2C",
) -> Dict[str, Any]:
    """
    Controller TOMONIDAN ulanish arizasini yaratish.
    Ulanish arizasi menejerga yuboriladi (status: 'in_manager').
    Connections jadvaliga ham yozuv qo'shadi.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # Application number generatsiya qilamiz - har bir business_type uchun alohida ketma-ketlikda
            next_number = await conn.fetchval(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(application_number FROM '\\d+$') AS INTEGER)), 0) + 1 FROM staff_orders WHERE application_number LIKE $1",
                f"STAFF-CONN-{business_type}-%"
            )
            application_number = f"STAFF-CONN-{business_type}-{next_number:04d}"
            
            row = await conn.fetchrow(
                """
                INSERT INTO staff_orders (
                    application_number, user_id, phone, abonent_id, region, address, tarif_id,
                    description, business_type, type_of_zayavka, status, is_active, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7,
                        '', $8, 'connection', 'in_manager'::staff_order_status, TRUE, NOW(), NOW())
                RETURNING id, application_number
                """,
                application_number, user_id, phone, abonent_id, region, address, tarif_id, business_type
            )
            
            staff_order_id = row["id"]
            
            # Connections jadvaliga yozuv qo'shamiz (controller -> manager)
            await conn.execute(
                """
                INSERT INTO connections (
                    staff_id,
                    sender_id,
                    recipient_id,
                    sender_status,
                    recipient_status,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, 'new', 'in_manager', NOW(), NOW())
                """,
                staff_order_id, user_id, user_id  # sender: controller, recipient: manager (hozircha bir xil)
            )
            
            return {"id": staff_order_id, "application_number": row["application_number"]}
    finally:
        await conn.close()

async def staff_orders_technician_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    description: Optional[str],
    business_type: str = "B2C",
) -> Dict[str, Any]:
    """
    Controller TOMONIDAN texnik xizmat arizasini yaratish.
    Default status: 'in_controller'.
    Connections jadvaliga ham yozuv qo'shadi.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # Application number generatsiya qilamiz - TECH uchun alohida ketma-ketlikda
            next_number = await conn.fetchval(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(application_number FROM '\\d+$') AS INTEGER)), 0) + 1 FROM staff_orders WHERE application_number LIKE $1",
                f"STAFF-TECH-{business_type}-%"
            )
            application_number = f"STAFF-TECH-{business_type}-{next_number:04d}"
            
            row = await conn.fetchrow(
                """
                INSERT INTO staff_orders (
                    application_number, user_id, phone, abonent_id, region, address,
                    description, business_type, type_of_zayavka, status, is_active, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6,
                        $7, $8, 'technician', 'in_controller'::staff_order_status, TRUE, NOW(), NOW())
                RETURNING id, application_number
                """,
                application_number, user_id, phone, abonent_id, region, address, description, business_type
            )
            
            staff_order_id = row["id"]
            
            # Connections jadvaliga yozuv qo'shamiz (yaratilganda to'g'ridan-to'g'ri controller'da)
            await conn.execute(
                """
                INSERT INTO connections (
                    staff_id,
                    sender_id,
                    recipient_id,
                    sender_status,
                    recipient_status,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $2, 'new', 'in_controller', NOW(), NOW())
                """,
                staff_order_id, user_id  # sender va recipient bir xil (controller yaratdi)
            )
            
            return {"id": staff_order_id, "application_number": row["application_number"]}
    finally:
        await conn.close()

# =========================================================
#  Controller Orders ro'yxatlari
# =========================================================

async def list_my_created_orders_by_type(user_id: int, order_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Controller tomonidan yaratilgan orders ro'yxatini type bo'yicha olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                so.id,
                so.application_number,
                so.user_id,
                so.phone,
                so.abonent_id,
                so.region,
                so.address,
                so.tarif_id,
                so.description,
                so.business_type,
                so.type_of_zayavka,
                so.status,
                so.is_active,
                so.created_at,
                so.updated_at,
                u.full_name as client_name,
                u.phone as client_phone,
                t.name as tariff,
                r.name as region_name
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            LEFT JOIN regions r ON r.id = so.region
            WHERE so.user_id = $1
              AND so.type_of_zayavka = $2
              AND COALESCE(so.is_active, TRUE) = TRUE
            ORDER BY so.created_at DESC
            LIMIT $3
            """,
            user_id, order_type, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def fetch_staff_activity() -> List[Dict[str, Any]]:
    """Xodimlar faoliyati - barcha xodimlar va ularning arizalari."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                u.id,
                u.full_name,
                u.phone,
                u.role,
                u.created_at,
                COUNT(so.id) as total_orders,
                COUNT(CASE WHEN so.status = 'in_controller' THEN 1 END) as new_orders,
                COUNT(CASE WHEN so.status IN ('between_controller_technician', 'in_technician') THEN 1 END) as in_progress_orders,
                COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN so.status = 'cancelled' THEN 1 END) as cancelled_orders,
                MAX(so.created_at) as last_order_date
            FROM users u
            LEFT JOIN staff_orders so ON so.user_id = u.id AND COALESCE(so.is_active, TRUE) = TRUE
            WHERE u.role IN ('junior_manager', 'manager', 'controller', 'technician')
            GROUP BY u.id, u.full_name, u.phone, u.role, u.created_at
            ORDER BY total_orders DESC, u.full_name
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()
