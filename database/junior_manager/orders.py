# database/junior_manager/orders.py
# Junior Manager roli uchun orders bilan bog'liq queries

import asyncpg
import re
from typing import List, Dict, Any, Optional
from config import settings

# Umumiy funksiyalarni import qilamiz
from database.basic.user import ensure_user
from database.basic.tariff import get_or_create_tarif_by_code
from database.basic.phone import normalize_phone

# =========================================================
#  Junior Manager uchun user yaratish
# =========================================================

async def ensure_user_junior_manager(telegram_id: int, full_name: str, username: str) -> Dict[str, Any]:
    """
    Junior Manager uchun user yaratish/yangilash.
    """
    return await ensure_user(telegram_id, full_name, username, 'junior_manager')

# =========================================================
#  Staff Orders yaratish
# =========================================================

async def staff_orders_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    tarif_id: Optional[int],
    business_type: str = "B2C",
) -> int:
    """
    Junior Manager TOMONIDAN ulanish arizasini yaratish.
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
                staff_order_id, user_id  # sender va recipient bir xil (junior manager yaratdi)
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
) -> int:
    """
    Junior Manager TOMONIDAN texnik xizmat arizasini yaratish.
    Default status: 'in_manager'.
    Connections jadvaliga ham yozuv qo'shadi.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
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
                        $7, $8, 'technician', 'in_manager'::staff_order_status, TRUE, NOW(), NOW())
                RETURNING id, application_number
                """,
                application_number, user_id, phone, abonent_id, region, address, description, business_type
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
                staff_order_id, user_id  # sender va recipient bir xil (junior manager yaratdi)
            )
            
            return {"id": staff_order_id, "application_number": row["application_number"]}
    finally:
        await conn.close()

# =========================================================
#  Junior Manager Orders ro'yxatlari
# =========================================================

async def list_new_for_jm(jm_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Junior Manager uchun yangi arizalar ro'yxati.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
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
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff_name
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.status = 'in_junior_manager'
              AND so.is_active = TRUE
            ORDER BY so.created_at ASC
            LIMIT $1
            """,
            limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_inprogress_for_jm(jm_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Junior Manager uchun jarayondagi arizalar ro'yxati (connection + staff orders, completed bo'lmaganlar).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            -- Connection Orders (mijozlar arizalari)
            SELECT
                co.id,
                co.user_id,
                co.region,
                co.address,
                co.tarif_id,
                NULL as phone,
                NULL as abonent_id,
                NULL as description,
                'connection' as type_of_zayavka,
                co.status::text,
                co.created_at,
                co.updated_at,
                u.full_name AS user_name,
                u.phone AS client_phone,
                t.name AS tariff_name,
                'connection' as order_type
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.status != 'completed'
              AND co.is_active = TRUE
            
            UNION ALL
            
            -- Staff Orders (xodimlar arizalari)
            SELECT
                so.id,
                so.user_id,
                so.region,
                so.address,
                so.tarif_id,
                so.phone,
                so.abonent_id,
                so.description,
                so.type_of_zayavka,
                so.status::text,
                so.created_at,
                so.updated_at,
                u.full_name AS user_name,
                u.phone AS client_phone,
                t.name AS tariff_name,
                'staff' as order_type
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.status != 'completed'
              AND so.is_active = TRUE
            
            ORDER BY updated_at DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_assigned_for_jm(jm_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Junior Manager uchun biriktirilgan arizalar ro'yxati (faqat o'ziga biriktirilganlar).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            -- Connection Orders (mijozlar arizalari) - faqat o'ziga biriktirilganlar
            SELECT
                co.id,
                co.user_id,
                co.region,
                co.address,
                co.tarif_id,
                NULL as phone,
                NULL as abonent_id,
                NULL as description,
                'connection' as type_of_zayavka,
                co.status::text,
                co.created_at,
                co.updated_at,
                u.full_name AS user_name,
                u.phone AS client_phone,
                t.name AS tariff_name,
                'connection' as order_type
            FROM connections c
            JOIN connection_orders co ON co.id = c.connection_id
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE c.recipient_id = $1
              AND c.connection_id IS NOT NULL
              AND co.is_active = TRUE
              AND co.status IN ('in_junior_manager', 'in_controller', 'in_technician', 'in_technician_work', 'in_manager')
            
            UNION ALL
            
            -- Staff Orders (xodimlar arizalari) - faqat o'ziga biriktirilganlar
            SELECT
                so.id,
                so.user_id,
                so.region,
                so.address,
                so.tarif_id,
                so.phone,
                so.abonent_id,
                so.description,
                so.type_of_zayavka,
                so.status::text,
                so.created_at,
                so.updated_at,
                u.full_name AS user_name,
                u.phone AS client_phone,
                t.name AS tariff_name,
                'staff' as order_type
            FROM connections c
            JOIN staff_orders so ON so.id = c.staff_id
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE c.recipient_id = $1
              AND c.staff_id IS NOT NULL
              AND so.is_active = TRUE
              AND so.status IN ('in_junior_manager', 'in_progress', 'assigned_to_technician', 'in_manager', 'in_controller')
            
            ORDER BY updated_at DESC
            LIMIT $2
            """,
            jm_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_completed_for_jm(jm_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Junior Manager uchun tugallangan arizalar ro'yxati (connection + staff orders).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            -- Connection Orders (mijozlar arizalari)
            SELECT
                co.id,
                co.user_id,
                co.region,
                co.address,
                co.tarif_id,
                NULL as phone,
                NULL as abonent_id,
                NULL as description,
                'connection' as type_of_zayavka,
                co.status::text,
                co.created_at,
                co.updated_at,
                u.full_name AS user_name,
                u.phone AS client_phone,
                t.name AS tariff_name,
                'connection' as order_type
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.status = 'completed'
              AND co.is_active = TRUE
            
            UNION ALL
            
            -- Staff Orders (xodimlar arizalari)
            SELECT
                so.id,
                so.user_id,
                so.region,
                so.address,
                so.tarif_id,
                so.phone,
                so.abonent_id,
                so.description,
                so.type_of_zayavka,
                so.status::text,
                so.created_at,
                so.updated_at,
                u.full_name AS user_name,
                u.phone AS client_phone,
                t.name AS tariff_name,
                'staff' as order_type
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.status = 'completed'
              AND so.is_active = TRUE
            
            ORDER BY updated_at DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# =========================================================
#  Junior Manager Inbox queries (staff_orders uchun)
# =========================================================

async def count_active_jm_orders() -> int:
    """
    Junior Manager inboxdagi aktiv arizalar soni.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM staff_orders
            WHERE status = 'in_junior_manager'
              AND is_active = TRUE
            """
        )
    finally:
        await conn.close()

async def fetch_jm_order_by_offset(offset: int) -> Optional[Dict[str, Any]]:
    """
    Junior Manager inboxdan offset bo'yicha bitta arizani olish.
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
                so.created_at,
                so.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff_name
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.status = 'in_junior_manager'
              AND so.is_active = TRUE
            ORDER BY so.created_at ASC
            OFFSET $1 LIMIT 1
            """,
            offset
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def send_to_controller(order_id: int, jm_id: int) -> bool:
    """
    Junior Manager -> Controller: order yuborish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # Staff order statusini yangilash
            await conn.execute(
                """
                UPDATE staff_orders
                SET status = 'in_controller',
                    updated_at = NOW()
                WHERE id = $1
                """,
                order_id
            )
            
            # Connection yozuvini yaratish
            await conn.execute(
                """
                INSERT INTO connections (sender_id, recipient_id, connection_id, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                jm_id, 0, order_id  # recipient_id = 0 (controller)
            )
            
            return True
    except Exception:
        return False
    finally:
        await conn.close()

# =========================================================
#  Mijoz qidiruv funksiyalari
# =========================================================

async def search_client_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Telefon raqam bo'yicha mijozni qidirish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Telefon raqamni normalize qilamiz
        normalized_phone = normalize_phone(phone)
        
        row = await conn.fetchrow(
            """
            SELECT 
                id, telegram_id, full_name, phone, username, 
                region, address, abonent_id, created_at
            FROM users 
            WHERE phone = $1 
            LIMIT 1
            """,
            normalized_phone
        )
        
        return dict(row) if row else None
    finally:
        await conn.close()

async def search_client_by_name(name: str) -> List[Dict[str, Any]]:
    """
    Ism bo'yicha mijozlarni qidirish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                id, telegram_id, full_name, phone, username, 
                region, address, abonent_id, created_at
            FROM users 
            WHERE LOWER(full_name) LIKE LOWER($1)
            ORDER BY full_name
            LIMIT 10
            """,
            f"%{name}%"
        )
        
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_client_order_history(user_id: int) -> List[Dict[str, Any]]:
    """
    Mijozning oldingi arizalarini olish (barcha turdagi arizalar).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            -- Connection Orders (mijozlar arizalari)
            SELECT
                co.id,
                co.application_number,
                co.status::text,
                co.created_at,
                co.updated_at,
                'connection' as order_type,
                t.name AS tariff_name,
                co.address,
                co.region,
                co.business_type
            FROM connection_orders co
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.user_id = $1
              AND co.is_active = TRUE
            
            UNION ALL
            
            -- Staff Orders (xodimlar arizalari)
            SELECT
                so.id,
                so.application_number,
                so.status::text,
                so.created_at,
                so.updated_at,
                'staff' as order_type,
                t.name AS tariff_name,
                so.address,
                so.region,
                so.business_type
            FROM staff_orders so
            LEFT JOIN tarif t ON t.id = so.tarif_id
            WHERE so.user_id = $1
              AND so.is_active = TRUE
            
            UNION ALL
            
            -- SmartService arizalari
            SELECT
                ss.id,
                ss.application_number,
                'active' as status,
                ss.created_at,
                ss.updated_at,
                'smartservice' as order_type,
                NULL AS tariff_name,
                ss.address,
                NULL as region,
                NULL as business_type
            FROM smart_service_orders ss
            WHERE ss.user_id = $1
              AND ss.is_active = TRUE
            
            ORDER BY created_at DESC
            LIMIT 25
            """,
            user_id
        )
        
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_client_order_count(user_id: int) -> Dict[str, int]:
    """
    Mijozning arizalar sonini olish (barcha turdagi arizalar).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE order_type = 'connection') AS connection_orders,
                COUNT(*) FILTER (WHERE order_type = 'staff') AS staff_orders,
                COUNT(*) FILTER (WHERE order_type = 'smartservice') AS smartservice_orders,
                COUNT(*) AS total_orders
            FROM (
                SELECT 'connection' as order_type FROM connection_orders WHERE user_id = $1 AND is_active = TRUE
                UNION ALL
                SELECT 'staff' as order_type FROM staff_orders WHERE user_id = $1 AND is_active = TRUE
                UNION ALL
                SELECT 'smartservice' as order_type FROM smart_service_orders WHERE user_id = $1 AND is_active = TRUE
            ) t
            """,
            user_id
        )
        
        return {
            "connection_orders": int(row["connection_orders"] or 0),
            "staff_orders": int(row["staff_orders"] or 0),
            "smartservice_orders": int(row["smartservice_orders"] or 0),
            "total_orders": int(row["total_orders"] or 0)
        }
    finally:
        await conn.close()