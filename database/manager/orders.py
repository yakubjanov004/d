import asyncpg
import re
from typing import List, Dict, Any, Optional
from config import settings

from database.basic.user import ensure_user
from database.basic.tariff import get_or_create_tarif_by_code
from database.basic.phone import normalize_phone

async def ensure_user_manager(telegram_id: int, full_name: str, username: str) -> Dict[str, Any]:
    """
    Manager uchun user yaratish/yangilash.
    """
    return await ensure_user(telegram_id, full_name, username, 'manager')

async def staff_orders_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: str,  # TEXT tipida
    address: str,
    tarif_id: Optional[int],
    business_type: str = "B2C",
) -> int:
    """
    Manager TOMONIDAN ulanish arizasini yaratish.
    Default status: 'in_manager'.
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
            
            # Connections jadvaliga yozuv qo'shamiz (yaratilish)
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
                VALUES ($1, $2, $2, 'new', 'in_manager', NOW(), NOW())
                """,
                staff_order_id, user_id  # sender va recipient bir xil (manager yaratdi)
            )
            
            return {"id": staff_order_id, "application_number": row["application_number"]}
    finally:
        await conn.close()

async def staff_orders_technician_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: str,  # TEXT tipida
    address: str,
    description: Optional[str],
    business_type: str = "B2C",
) -> int:
    """
    Manager TOMONIDAN texnik xizmat arizasini yaratish.
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
            
            # Connections jadvaliga yozuv qo'shamiz (yaratilganda to'g'ridan-to'g'ri controller'ga)
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
                staff_order_id, user_id  # sender va recipient bir xil (manager yaratdi)
            )
            
            return {"id": staff_order_id, "application_number": row["application_number"]}
    finally:
        await conn.close()

# =========================================================
#  Manager Orders ro'yxatlari
# =========================================================

async def fetch_manager_orders(user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Manager yaratgan arizalarni olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                so.id,
                so.application_number,
                so.address,
                so.region,
                so.status,
                so.type_of_zayavka,
                so.description,
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.abonent_id::bigint
            LEFT JOIN tarif t ON t.id = so.tarif_id::bigint
            WHERE so.user_id = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
            ORDER BY so.created_at DESC, so.id DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def count_manager_orders(user_id: int) -> int:
    """
    Manager yaratgan arizalar soni.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM staff_orders so
             WHERE so.user_id = $1
               AND COALESCE(so.is_active, TRUE) = TRUE
            """,
            user_id
        )
    finally:
        await conn.close()

# =========================================================
#  Manager Statistics funksiyalari
# =========================================================

async def get_total_orders_count(user_id: int) -> int:
    """Manager yaratgan jami arizalar soni."""
    return await count_manager_orders(user_id)

async def get_in_progress_count(user_id: int) -> int:
    """Manager yaratgan ish jarayonidagi arizalar soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM staff_orders so
             WHERE so.user_id = $1
               AND COALESCE(so.is_active, TRUE) = TRUE
               AND so.status IN ('in_junior_manager', 'in_controller', 'in_technician')
            """,
            user_id
        )
    finally:
        await conn.close()

async def get_completed_today_count(user_id: int) -> int:
    """Manager yaratgan bugun yakunlangan arizalar soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM staff_orders so
             WHERE so.user_id = $1
               AND COALESCE(so.is_active, TRUE) = TRUE
               AND so.status = 'completed'
               AND DATE(so.updated_at) = CURRENT_DATE
            """,
            user_id
        )
    finally:
        await conn.close()

async def get_cancelled_count(user_id: int) -> int:
    """Manager yaratgan bekor qilingan arizalar soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM staff_orders so
             WHERE so.user_id = $1
               AND COALESCE(so.is_active, TRUE) = TRUE
               AND so.status = 'cancelled'
            """,
            user_id
        )
    finally:
        await conn.close()

async def get_new_orders_today_count(user_id: int) -> int:
    """Manager yaratgan bugungi yangi arizalar soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM staff_orders so
             WHERE so.user_id = $1
               AND COALESCE(so.is_active, TRUE) = TRUE
               AND so.status = 'in_manager'
               AND DATE(so.created_at) = CURRENT_DATE
            """,
            user_id
        )
    finally:
        await conn.close()

# =========================================================
#  Manager Orders ro'yxatlari
# =========================================================

async def list_new_orders(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Manager yaratgan yangi arizalar."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                so.id,
                so.application_number,
                so.address,
                so.status,
                so.type_of_zayavka,
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.abonent_id::bigint
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.user_id = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND so.status = 'in_manager'
            ORDER BY so.created_at DESC
            LIMIT $2
            """,
            user_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_in_progress_orders(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Manager yaratgan ish jarayonidagi arizalar."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                so.id,
                so.application_number,
                so.address,
                so.status,
                so.type_of_zayavka,
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.abonent_id::bigint
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.user_id = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND so.status IN ('in_junior_manager', 'in_controller', 'in_technician')
            ORDER BY so.created_at DESC
            LIMIT $2
            """,
            user_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_completed_today_orders(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Manager yaratgan bugun yakunlangan arizalar."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                so.id,
                so.application_number,
                so.address,
                so.status,
                so.type_of_zayavka,
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.abonent_id::bigint
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.user_id = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND so.status = 'completed'
              AND DATE(so.updated_at) = CURRENT_DATE
            ORDER BY so.updated_at DESC
            LIMIT $2
            """,
            user_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_cancelled_orders(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Manager yaratgan bekor qilingan arizalar."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                so.id,
                so.application_number,
                so.address,
                so.status,
                so.type_of_zayavka,
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.abonent_id::bigint
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.user_id = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND so.status = 'cancelled'
            ORDER BY so.updated_at DESC
            LIMIT $2
            """,
            user_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_my_created_orders_by_type(user_id: int, order_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Manager yaratgan arizalar turi bo'yicha."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                so.id,
                so.application_number,
                so.address,
                so.status,
                so.type_of_zayavka,
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.abonent_id::bigint
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.user_id = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND so.type_of_zayavka = $2
            ORDER BY so.created_at DESC
            LIMIT $3
            """,
            user_id, order_type, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# =========================================================
#  Connection Orders uchun funksiyalar (Manager applications uchun)
# =========================================================

async def get_connection_orders_count() -> int:
    """Barcha connection orders soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        count = await conn.fetchval("SELECT COUNT(*) FROM connection_orders WHERE is_active = TRUE")
        return int(count or 0)
    finally:
        await conn.close()

async def get_connection_orders_in_progress_count() -> int:
    """Jarayondagi connection orders soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE is_active = TRUE AND status IN ('in_junior_manager', 'in_controller', 'in_technician', 'in_warehouse', 'in_repairs', 'in_technician_work')"
        )
        return int(count or 0)
    finally:
        await conn.close()

async def get_connection_orders_completed_today_count() -> int:
    """Bugun bajarilgan connection orders soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE is_active = TRUE AND status = 'completed' AND DATE(updated_at) = CURRENT_DATE"
        )
        return int(count or 0)
    finally:
        await conn.close()

async def get_connection_orders_cancelled_count() -> int:
    """Bekor qilingan connection orders soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE is_active = TRUE AND status = 'cancelled'"
        )
        return int(count or 0)
    finally:
        await conn.close()

async def get_connection_orders_new_today_count() -> int:
    """Bugun yaratilgan connection orders soni."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE is_active = TRUE AND status = 'in_manager' AND DATE(created_at) = CURRENT_DATE"
        )
        return int(count or 0)
    finally:
        await conn.close()

async def list_connection_orders_new(limit: int = 10) -> List[Dict[str, Any]]:
    """Yangi connection orders."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                co.id,
                co.application_number,
                co.address,
                co.status,
                co.created_at,
                co.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.is_active = TRUE
              AND co.status = 'in_manager'
            ORDER BY co.created_at DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_connection_orders_in_progress(limit: int = 10) -> List[Dict[str, Any]]:
    """Jarayondagi connection orders."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                co.id,
                co.application_number,
                co.address,
                co.status,
                co.created_at,
                co.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.is_active = TRUE
              AND co.status IN ('in_junior_manager', 'in_controller', 'in_technician', 'in_warehouse', 'in_repairs', 'in_technician_work')
            ORDER BY co.created_at DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_connection_orders_completed_today(limit: int = 10) -> List[Dict[str, Any]]:
    """Bugun bajarilgan connection orders."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                co.id,
                co.application_number,
                co.address,
                co.status,
                co.created_at,
                co.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.is_active = TRUE
              AND co.status = 'completed'
              AND DATE(co.updated_at) = CURRENT_DATE
            ORDER BY co.updated_at DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_connection_orders_cancelled(limit: int = 10) -> List[Dict[str, Any]]:
    """Bekor qilingan connection orders."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                co.id,
                co.application_number,
                co.address,
                co.status,
                co.created_at,
                co.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.is_active = TRUE
              AND co.status = 'cancelled'
            ORDER BY co.updated_at DESC
            LIMIT $1
            """,
            limit
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
                COUNT(CASE WHEN so.type_of_zayavka = 'connection' THEN 1 END) as conn_count,
                COUNT(CASE WHEN so.type_of_zayavka = 'technician' THEN 1 END) as tech_count,
                COUNT(CASE WHEN so.status IN ('in_junior_manager', 'in_controller', 'in_technician') THEN 1 END) as active_count,
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