# database/controller/queries.py

from typing import List, Dict, Any, Optional
import asyncpg
import logging
from config import settings

logger = logging.getLogger(__name__)

# =========================================================
#  Controller uchun asosiy funksiyalar
# =========================================================

async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Telegram ID orqali user ma'lumotlarini olish."""
    from database.basic.user import get_user_by_telegram_id as basic_get_user
    return await basic_get_user(telegram_id)

async def ensure_user_controller(telegram_id: int, full_name: str, username: str) -> Dict[str, Any]:
    """
    Controller uchun user yaratish/yangilash.
    """
    from database.basic.user import ensure_user
    return await ensure_user(telegram_id, full_name, username, 'controller')

# =========================================================
#  Controller Inbox - Staff Orders bilan ishlash
# =========================================================

async def fetch_controller_inbox_staff(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Controller inbox - staff orders ro'yxatini olish.
    Faqat 'in_controller' statusdagi staff orders.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status,
                       c.created_at
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
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
                COALESCE(client.full_name, 'Mijoz') as client_name,
                so.phone as client_phone,
                CASE 
                    WHEN so.type_of_zayavka = 'connection' THEN t.name
                    WHEN so.type_of_zayavka = 'technician' THEN so.description
                    ELSE NULL
                END as tariff_or_problem,
                so.region as region_name,
                creator.full_name as staff_name,
                creator.phone as staff_phone,
                creator.role as staff_role,
                CASE 
                    WHEN so.type_of_zayavka = 'technician' THEN tech_ord.media
                    ELSE NULL
                END as media_file_id,
                CASE 
                    WHEN so.type_of_zayavka = 'technician' AND tech_ord.media IS NOT NULL THEN 'photo'
                    ELSE NULL
                END as media_type
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            LEFT JOIN users creator ON creator.id = so.user_id
            LEFT JOIN users client ON client.id::text = so.abonent_id
            LEFT JOIN technician_orders tech_ord ON tech_ord.id = so.id AND so.type_of_zayavka = 'technician'
            WHERE la.recipient_status = 'in_controller'
              AND so.status = 'in_controller'
              AND COALESCE(so.is_active, TRUE) = TRUE
            ORDER BY so.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def count_controller_inbox_staff() -> int:
    """
    Controller inbox - staff orders sonini olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
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
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            WHERE la.recipient_status = 'in_controller'
              AND so.status = 'in_controller'
              AND COALESCE(so.is_active, TRUE) = TRUE
            """
        )
        return count or 0
    finally:
        await conn.close()

# =========================================================
#  Controller -> Technician assignment
# =========================================================

async def assign_to_technician_for_staff(request_id: int | str, tech_id: int, actor_id: int) -> Dict[str, Any]:
    """
    Controller -> Technician (staff_orders uchun):
      1) staff_orders.status: old -> 'between_controller_technician'
      2) connections: HAR DOIM yangi qator INSERT
         sender_id=controller(actor_id), recipient_id=tech_id,
         sender_status=old_status, recipient_status=new_status
      3) Technician'ga notification yuboradi
    
    Returns:
        Dict with recipient info for notification
    """
    # '8_2025' kabi bo'lsa ham 8 ni olamiz
    try:
        request_id_int = int(str(request_id).split("_")[0])
    except Exception:
        request_id_int = int(request_id)

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # Technician mavjudmi? + uning ma'lumotlarini olamiz
            tech_info = await conn.fetchrow(
                "SELECT id, telegram_id, language FROM users WHERE id = $1 AND role = 'technician'",
                tech_id,
            )
            if not tech_info:
                raise ValueError("Technician topilmadi")

            # 1) Eski statusni va application_number'ni lock bilan o'qiymiz
            row_old = await conn.fetchrow(
                """
                SELECT status, application_number, type_of_zayavka
                  FROM staff_orders
                 WHERE id = $1
                 FOR UPDATE
                """,
                request_id_int
            )
            if not row_old:
                raise ValueError("Staff order topilmadi")

            old_status: str = row_old["status"]
            app_number: str = row_old["application_number"]
            order_type: str = row_old["type_of_zayavka"] or "staff"

            # 2) Yangi statusga o'tkazamiz
            row_new = await conn.fetchrow(
                """
                UPDATE staff_orders
                   SET status     = 'between_controller_technician',
                       updated_at = NOW()
                 WHERE id = $1
             RETURNING status
                """,
                request_id_int
            )
            new_status: str = row_new["status"]  # 'between_controller_technician'

            # 3) Connections yozamiz - Controller -> Technician
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
                VALUES (
                    $1,
                    $2,
                    $3,
                    $4,
                    $5,
                    NOW(),
                    NOW()
                )
                """,
                request_id_int,
                actor_id,          # controller
                tech_id,           # technician
                old_status,        # masalan: 'in_controller'
                new_status         # 'between_controller_technician'
            )
            
            # 4) Hozirgi yuklamani hisoblaymiz
            current_load = await conn.fetchval(
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
                tech_id
            )
            
            return {
                "telegram_id": tech_info["telegram_id"],
                "language": tech_info["language"] or "uz",
                "application_number": app_number,
                "order_type": order_type,
                "current_load": current_load or 0
            }
    finally:
        await conn.close()

async def get_technicians_with_load_via_history() -> List[Dict[str, Any]]:
    """
    Technicianlarni hozirgi yuklamasi (ochiq staff arizalar soni) bilan olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status,
                       c.created_at
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            ),
            workloads AS (
                SELECT
                    la.recipient_id AS technician_id,
                    COUNT(*) AS cnt
                FROM last_assign la
                JOIN staff_orders so
                  ON so.id = la.staff_id
                WHERE COALESCE(so.is_active, TRUE) = TRUE
                  AND so.status IN ('between_controller_technician', 'in_technician')
                  AND la.recipient_status IN ('between_controller_technician', 'in_technician')
                GROUP BY la.recipient_id
            )
            SELECT 
                u.id,
                u.full_name,
                u.username,
                u.phone,
                u.telegram_id,
                COALESCE(w.cnt, 0) AS load_count
            FROM users u
            LEFT JOIN workloads w ON w.technician_id = u.id
            WHERE u.role = 'technician'
              AND COALESCE(u.is_blocked, FALSE) = FALSE
            ORDER BY u.full_name NULLS LAST, u.id
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# =========================================================
#  Controller Orders ro'yxatlari
# =========================================================

async def list_controller_orders_by_status(status: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Controller arizalarini status bo'yicha olish."""
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
                so.created_at
            FROM staff_orders so
            WHERE so.status = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
            ORDER BY so.created_at DESC
            LIMIT $2
            """,
            status, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# =========================================================
#  Controller Inbox - Connection Orders
# =========================================================

async def fetch_controller_inbox_connection(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Controller inbox - connection orders (ulanish arizalari).
    Faqat 'in_controller' statusdagi connection orders.
    jm_notes ni ham olamiz.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                co.id,
                co.application_number,
                co.address,
                co.region,
                co.status,
                co.jm_notes,
                co.created_at,
                co.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone,
                t.name AS tariff
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.is_active = TRUE
              AND co.status = 'in_controller'
            ORDER BY co.created_at DESC, co.id DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# =========================================================
#  Controller Inbox - Tech Orders (Service Orders)
# =========================================================

async def fetch_controller_inbox_tech(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Controller inbox - tech service orders (texnik xizmat arizalari).
    Client tomonidan yaratilgan, 'in_controller' statusdagi technician orders.
    media va description ni ham olamiz.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                tech_ord.id,
                tech_ord.application_number,
                tech_ord.address,
                tech_ord.region,
                tech_ord.status,
                tech_ord.description,
                tech_ord.media AS media_file_id,
                CASE 
                    WHEN tech_ord.media IS NOT NULL THEN 'photo'
                    ELSE NULL
                END AS media_type,
                tech_ord.created_at,
                tech_ord.updated_at,
                u.full_name AS client_name,
                u.phone AS client_phone
            FROM technician_orders tech_ord
            LEFT JOIN users u ON u.id = tech_ord.user_id
            WHERE COALESCE(tech_ord.is_active, TRUE) = TRUE
              AND tech_ord.status = 'in_controller'
            ORDER BY tech_ord.created_at DESC, tech_ord.id DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# =========================================================
#  Assignment Functions
# =========================================================

async def assign_to_technician_connection(request_id: int, tech_id: int, actor_id: int) -> Dict[str, Any]:
    """
    Connection order ni texnikka yuborish.
    Status: in_controller -> in_technician
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Update connection_orders
        await conn.execute(
            """
            UPDATE connection_orders
            SET status = 'in_technician',
                updated_at = NOW()
            WHERE id = $1
            """,
            request_id
        )
        
        # Get application info
        app_info = await conn.fetchrow(
            """
            SELECT application_number FROM connection_orders WHERE id = $1
            """,
            request_id
        )
        
        # Insert into connections table
        await conn.execute(
            """
            INSERT INTO connections (
                connection_id, sender_id, recipient_id,
                sender_status, recipient_status, created_at
            ) VALUES ($1, $2, $3, 'in_controller', 'in_technician', NOW())
            """,
            request_id, actor_id, tech_id
        )
        
        # Get technician info and current load
        tech_info = await conn.fetchrow(
            """
            SELECT u.telegram_id, u.language, u.full_name
            FROM users u
            WHERE u.id = $1
            """,
            tech_id
        )
        
        # Calculate current load
        load_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM connection_orders co
            WHERE co.status = 'in_technician'
              AND co.is_active = TRUE
              AND EXISTS (
                  SELECT 1 FROM connections c
                  WHERE c.connection_id = co.id
                    AND c.recipient_id = $1
                    AND c.recipient_status = 'in_technician'
              )
            """,
            tech_id
        ) or 0
        
        return {
            "telegram_id": tech_info["telegram_id"],
            "language": tech_info["language"],
            "application_number": app_info["application_number"],
            "current_load": load_count
        }
    finally:
        await conn.close()

async def assign_to_technician_tech(request_id: int, tech_id: int, actor_id: int) -> Dict[str, Any]:
    """
    Tech service order ni texnikka yuborish.
    Status: in_controller -> in_technician
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Update technician_orders
        await conn.execute(
            """
            UPDATE technician_orders
            SET status = 'in_technician',
                updated_at = NOW()
            WHERE id = $1
            """,
            request_id
        )
        
        # Get application info
        app_info = await conn.fetchrow(
            """
            SELECT application_number FROM technician_orders WHERE id = $1
            """,
            request_id
        )
        
        # Insert into connections table (technician_id)
        await conn.execute(
            """
            INSERT INTO connections (
                technician_id, sender_id, recipient_id,
                sender_status, recipient_status, created_at
            ) VALUES ($1, $2, $3, 'in_controller', 'in_technician', NOW())
            """,
            request_id, actor_id, tech_id
        )
        
        # Get technician info and current load
        tech_info = await conn.fetchrow(
            """
            SELECT u.telegram_id, u.language, u.full_name
            FROM users u
            WHERE u.id = $1
            """,
            tech_id
        )
        
        # Calculate current load for technician orders
        load_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM technician_orders tech_ord
            WHERE tech_ord.status = 'in_technician'
              AND COALESCE(tech_ord.is_active, TRUE) = TRUE
              AND EXISTS (
                  SELECT 1 FROM connections c
                  WHERE c.technician_id = tech_ord.id
                    AND c.recipient_id = $1
                    AND c.recipient_status = 'in_technician'
              )
            """,
            tech_id
        ) or 0
        
        return {
            "telegram_id": tech_info["telegram_id"],
            "language": tech_info["language"],
            "application_number": app_info["application_number"],
            "current_load": load_count
        }
    finally:
        await conn.close()

async def assign_to_technician_staff(request_id: int, tech_id: int, actor_id: int) -> Dict[str, Any]:
    """
    Staff order ni texnikka yuborish (xodim yaratgan ariza).
    Status: in_controller -> in_technician
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Update staff_orders
        await conn.execute(
            """
            UPDATE staff_orders
            SET status = 'in_technician',
                updated_at = NOW()
            WHERE id = $1
            """,
            request_id
        )
        
        # Get application info
        app_info = await conn.fetchrow(
            """
            SELECT application_number FROM staff_orders WHERE id = $1
            """,
            request_id
        )
        
        # Insert into connections table (staff_id)
        await conn.execute(
            """
            INSERT INTO connections (
                staff_id, sender_id, recipient_id,
                sender_status, recipient_status, created_at
            ) VALUES ($1, $2, $3, 'in_controller', 'in_technician', NOW())
            """,
            request_id, actor_id, tech_id
        )
        
        # Get technician info and current load
        tech_info = await conn.fetchrow(
            """
            SELECT u.telegram_id, u.language, u.full_name
            FROM users u
            WHERE u.id = $1
            """,
            tech_id
        )
        
        # Calculate current load for staff orders
        load_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM staff_orders so
            WHERE so.status = 'in_technician'
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND EXISTS (
                  SELECT 1 FROM connections c
                  WHERE c.staff_id = so.id
                    AND c.recipient_id = $1
                    AND c.recipient_status = 'in_technician'
              )
            """,
            tech_id
        ) or 0
        
        return {
            "telegram_id": tech_info["telegram_id"],
            "language": tech_info["language"],
            "application_number": app_info["application_number"],
            "current_load": load_count
        }
    finally:
        await conn.close()

async def assign_to_ccs_tech(request_id: int, ccs_id: int, actor_id: int) -> Dict[str, Any]:
    """
    Tech service order ni CCS Supervisorga yuborish.
    Status: in_controller -> in_call_center_supervisor
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Update technician_orders
        await conn.execute(
            """
            UPDATE technician_orders
            SET status = 'in_call_center_supervisor',
                updated_at = NOW()
            WHERE id = $1
            """,
            request_id
        )
        
        # Get application info
        app_info = await conn.fetchrow(
            """
            SELECT application_number FROM technician_orders WHERE id = $1
            """,
            request_id
        )
        
        # Insert into connections table
        await conn.execute(
            """
            INSERT INTO connections (
                technician_id, sender_id, recipient_id,
                sender_status, recipient_status, created_at
            ) VALUES ($1, $2, $3, 'in_controller', 'in_call_center_supervisor', NOW())
            """,
            request_id, actor_id, ccs_id
        )
        
        # Get CCS info and current load
        ccs_info = await conn.fetchrow(
            """
            SELECT u.telegram_id, u.language, u.full_name
            FROM users u
            WHERE u.id = $1
            """,
            ccs_id
        )
        
        # Calculate current load for CCS
        load_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM technician_orders tech_ord
            WHERE tech_ord.status = 'in_call_center_supervisor'
              AND COALESCE(tech_ord.is_active, TRUE) = TRUE
              AND EXISTS (
                  SELECT 1 FROM connections c
                  WHERE c.technician_id = tech_ord.id
                    AND c.recipient_id = $1
                    AND c.recipient_status = 'in_call_center_supervisor'
              )
            """,
            ccs_id
        ) or 0
        
        return {
            "telegram_id": ccs_info["telegram_id"],
            "language": ccs_info["language"],
            "application_number": app_info["application_number"],
            "current_load": load_count
        }
    finally:
        await conn.close()

async def assign_to_ccs_staff(request_id: int, ccs_id: int, actor_id: int) -> Dict[str, Any]:
    """
    Staff order ni CCS Supervisorga yuborish.
    Status: in_controller -> in_call_center_supervisor
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Update staff_orders
        await conn.execute(
            """
            UPDATE staff_orders
            SET status = 'in_call_center_supervisor',
                updated_at = NOW()
            WHERE id = $1
            """,
            request_id
        )
        
        # Get application info
        app_info = await conn.fetchrow(
            """
            SELECT application_number FROM staff_orders WHERE id = $1
            """,
            request_id
        )
        
        # Insert into connections table
        await conn.execute(
            """
            INSERT INTO connections (
                staff_id, sender_id, recipient_id,
                sender_status, recipient_status, created_at
            ) VALUES ($1, $2, $3, 'in_controller', 'in_call_center_supervisor', NOW())
            """,
            request_id, actor_id, ccs_id
        )
        
        # Get CCS info and current load
        ccs_info = await conn.fetchrow(
            """
            SELECT u.telegram_id, u.language, u.full_name
            FROM users u
            WHERE u.id = $1
            """,
            ccs_id
        )
        
        # Calculate current load for CCS (staff orders)
        load_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM staff_orders so
            WHERE so.status = 'in_call_center_supervisor'
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND EXISTS (
                  SELECT 1 FROM connections c
                  WHERE c.staff_id = so.id
                    AND c.recipient_id = $1
                    AND c.recipient_status = 'in_call_center_supervisor'
              )
            """,
            ccs_id
        ) or 0
        
        return {
            "telegram_id": ccs_info["telegram_id"],
            "language": ccs_info["language"],
            "application_number": app_info["application_number"],
            "current_load": load_count
        }
    finally:
        await conn.close()

# =========================================================
#  Load calculation functions
# =========================================================

async def get_ccs_supervisors_with_load() -> List[Dict[str, Any]]:
    """
    CCS Supervisorlar ro'yxatini yuklama bilan olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                u.id,
                u.full_name,
                u.telegram_id,
                u.language,
                COALESCE(
                    (SELECT COUNT(*)
                     FROM connections c
                     WHERE c.recipient_id = u.id
                       AND c.recipient_status = 'in_call_center_supervisor'
                       AND (
                           EXISTS (SELECT 1 FROM technician_orders tech_ord WHERE tech_ord.id = c.technician_id AND tech_ord.status = 'in_call_center_supervisor' AND COALESCE(tech_ord.is_active, TRUE) = TRUE)
                           OR
                           EXISTS (SELECT 1 FROM staff_orders so WHERE so.id = c.staff_id AND so.status = 'in_call_center_supervisor' AND COALESCE(so.is_active, TRUE) = TRUE)
                       )
                    ), 0
                ) AS load_count
            FROM users u
            WHERE u.role = 'callcenter_supervisor'
              AND u.is_blocked = FALSE
            ORDER BY load_count ASC, u.full_name ASC
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_controller_orders_by_status(status: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Controller orders ro'yxatini status bo'yicha olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status,
                       c.created_at
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
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
                creator.full_name as staff_name,
                creator.phone as staff_phone,
                creator.role as staff_role
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            LEFT JOIN users creator ON creator.id = so.user_id
            WHERE la.recipient_status = $1
              AND so.status = $1
              AND COALESCE(so.is_active, TRUE) = TRUE
            ORDER BY so.created_at DESC
            LIMIT $2
            """,
            status, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_controller_statistics() -> Dict[str, Any]:
    """
    Controller uchun statistika olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        stats = await conn.fetchrow(
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
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN so.status = 'in_controller' THEN 1 END) as in_controller,
                COUNT(CASE WHEN so.status = 'between_controller_technician' THEN 1 END) as between_controller_technician,
                COUNT(CASE WHEN so.status = 'in_technician' THEN 1 END) as in_technician,
                COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN so.status = 'cancelled' THEN 1 END) as cancelled
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician')
              AND COALESCE(so.is_active, TRUE) = TRUE
            """
        )
        return dict(stats) if stats else {}
    finally:
        await conn.close()
