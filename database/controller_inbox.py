# database/controller_inbox.py
import asyncpg
from typing import List, Dict, Any, Optional
from config import settings


# ===========================
#  Users helpers
# ===========================
async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT id, telegram_id, full_name, username, phone, role
            FROM users
            WHERE telegram_id = $1
            """,
            telegram_id,
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    """
    role kolonkasi enum bo‘lsa ham, text bo‘lsa ham ishlashi uchun role::text = $1
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, full_name, username, phone, telegram_id
            FROM users
            WHERE role::text = $1
              AND COALESCE(is_blocked, FALSE) = FALSE
            ORDER BY full_name NULLS LAST, id
            """,
            role,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# Moslik uchun wrapper (ImportError bo‘lmasin)
async def get_callcenter_operators() -> List[Dict[str, Any]]:  # <— YANGI
    return await get_users_by_role("callcenter_operator")


# ===========================
#  Controller inbox (connection_orders)
# ===========================
async def fetch_controller_inbox(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                co.id,
                co.address,
                co.region,
                co.status,
                co.created_at,
                u.full_name AS client_name,
                u.phone      AS client_phone,
                t.name       AS tariff
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.is_active = TRUE
              AND co.status = 'in_controller'
            ORDER BY co.created_at DESC, co.id DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def assign_to_technician(request_id: int | str, tech_id: int, actor_id: int) -> None:
    """
    connection_orders: in_controller -> between_controller_technician
    connections: controller -> technician (connection_id)
    """
    req_id = int(str(request_id).split("_")[0]) if isinstance(request_id, str) else int(request_id)
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            ok = await conn.fetchval(
                """
                SELECT 1 FROM users
                WHERE id = $1
                  AND role::text = 'technician'
                  AND COALESCE(is_blocked, FALSE) = FALSE
                """,
                tech_id,
            )
            if not ok:
                raise ValueError("Technician not found or blocked")

            row_old = await conn.fetchrow(
                "SELECT status FROM connection_orders WHERE id=$1 FOR UPDATE",
                req_id,
            )
            if not row_old or row_old["status"] != "in_controller":
                raise ValueError("Order is not in 'in_controller' status")
            old_status = row_old["status"]

            await conn.execute(
                """
                UPDATE connection_orders
                   SET status='between_controller_technician'::connection_order_status,
                       updated_at=NOW()
                 WHERE id=$1 AND status='in_controller'::connection_order_status
                """,
                req_id,
            )

            await conn.execute(
                """
                INSERT INTO connections(
                    connection_id,
                    sender_id,
                    recipient_id,
                    sender_status,
                    recipient_status,
                    created_at,
                    updated_at
                )
                VALUES ($1,$2,$3,$4,'between_controller_technician',NOW(),NOW())
                """,
                req_id, actor_id, tech_id, old_status,
            )
    finally:
        await conn.close()


# ===========================
#  Controller inbox (technician_orders)
# ===========================
async def fetch_controller_inbox_tech(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                to2.id,
                to2.address,
                to2.region,
                to2.status,
                to2.created_at,
                u.full_name AS client_name,
                u.phone     AS client_phone,
                NULL        AS tariff
            FROM technician_orders AS to2
            LEFT JOIN users u ON u.id = to2.user_id
            WHERE to2.is_active = TRUE
              AND to2.status = 'in_controller'
            ORDER BY to2.created_at DESC, to2.id DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def assign_to_technician_for_tech(request_id: int | str, tech_id: int, actor_id: int) -> None:
    """
    technician_orders: in_controller -> between_controller_technician
    connections: controller -> technician (technician_id)
    """
    req_id = int(str(request_id).split("_")[0]) if isinstance(request_id, str) else int(request_id)
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            ok = await conn.fetchval(
                """
                SELECT 1 FROM users
                WHERE id = $1
                  AND role::text = 'technician'
                  AND COALESCE(is_blocked, FALSE) = FALSE
                """,
                tech_id,
            )
            if not ok:
                raise ValueError("Technician not found or blocked")

            row_old = await conn.fetchrow(
                "SELECT status FROM technician_orders WHERE id=$1 FOR UPDATE",
                req_id,
            )
            if not row_old or row_old["status"] != "in_controller":
                raise ValueError("Order is not in 'in_controller' status")
            old_status = row_old["status"]

            await conn.execute(
                """
                UPDATE technician_orders
                   SET status='between_controller_technician'::technician_order_status,
                       updated_at=NOW()
                 WHERE id=$1 AND status='in_controller'::technician_order_status
                """,
                req_id,
            )

            await conn.execute(
                """
                INSERT INTO connections(
                    technician_id,
                    sender_id,
                    recipient_id,
                    sender_status,
                    recipient_status,
                    created_at,
                    updated_at
                )
                VALUES ($1,$2,$3,$4,'between_controller_technician',NOW(),NOW())
                """,
                req_id, actor_id, tech_id, old_status,
            )
    finally:
        await conn.close()


# ===========================
#  Controller inbox (staff_orders)
# ===========================
async def fetch_controller_inbox_staff(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                so.id,
                so.address,
                so.region,
                so.status,
                so.type_of_zayavka AS req_type,
                so.description,
                so.created_at,

                st.full_name  AS staff_name,
                st.phone      AS staff_phone,
                st.role       AS staff_role,

                ab.full_name  AS client_name,
                ab.phone      AS client_phone,

                t.name        AS tariff
            FROM staff_orders AS so
            LEFT JOIN users st ON st.id = so.user_id::bigint
            LEFT JOIN users ab ON ab.id = so.abonent_id::bigint
            LEFT JOIN tarif  t ON t.id  = so.tarif_id::bigint
            WHERE COALESCE(so.is_active, TRUE) = TRUE
              AND so.status = 'in_controller'
            ORDER BY so.created_at DESC, so.id DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def assign_to_technician_for_staff(request_id: int | str, tech_id: int, actor_id: int) -> None:
    """
    staff_orders: in_controller -> between_controller_technician
    connections: controller -> technician (staff_id)
    """
    req_id = int(str(request_id).split("_")[0]) if isinstance(request_id, str) else int(request_id)
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            ok = await conn.fetchval(
                """
                SELECT 1 FROM users
                WHERE id = $1
                  AND role::text = 'technician'
                  AND COALESCE(is_blocked, FALSE) = FALSE
                """,
                tech_id,
            )
            if not ok:
                raise ValueError("Technician not found or blocked")

            row_old = await conn.fetchrow(
                "SELECT status FROM staff_orders WHERE id=$1 FOR UPDATE",
                req_id,
            )
            if not row_old or row_old["status"] != "in_controller":
                raise ValueError("Order is not in 'in_controller' status")
            old_status = row_old["status"]

            await conn.execute(
                """
                UPDATE staff_orders
                   SET status = 'between_controller_technician',
                       updated_at = NOW()
                 WHERE id = $1 AND status = 'in_controller'
                """,
                req_id,
            )

            await conn.execute(
                """
                INSERT INTO connections(
                    staff_id,
                    sender_id,
                    recipient_id,
                    sender_status,
                    recipient_status,
                    created_at,
                    updated_at
                )
                VALUES ($1,$2,$3,$4,'between_controller_technician',NOW(),NOW())
                """,
                req_id, actor_id, tech_id, old_status,
            )
    finally:
        await conn.close()


# ===========================
#  Technician workload (with mode)
# ===========================
async def get_technicians_with_load_via_history(mode: Optional[str] = None) -> List[Dict[str, Any]]:

    sql_connection = """
    WITH last_conn AS (
        SELECT
            c.connection_id,
            c.recipient_id,
            c.recipient_status,
            c.created_at,
            c.id,
            ROW_NUMBER() OVER (
                PARTITION BY c.connection_id
                ORDER BY c.created_at DESC, c.id DESC
            ) AS rn
        FROM connections c
        WHERE c.connection_id IS NOT NULL
    ),
    workloads AS (
        SELECT lc.recipient_id AS tech_id, COUNT(*) AS cnt
        FROM last_conn lc
        JOIN connection_orders co ON co.id = lc.connection_id
        WHERE lc.rn = 1
          AND lc.recipient_status = 'between_controller_technician'
          AND co.is_active = TRUE
          AND co.status = 'between_controller_technician'
        GROUP BY lc.recipient_id
    )
    SELECT u.id, u.full_name, u.username, u.phone, u.telegram_id,
           COALESCE(w.cnt, 0) AS load_count
    FROM users u
    LEFT JOIN workloads w ON w.tech_id = u.id
    WHERE u.role::text = 'technician'
      AND COALESCE(u.is_blocked, FALSE) = FALSE
    ORDER BY u.full_name NULLS LAST, u.id;
    """

    sql_technician = """
    WITH last_tech AS (
        SELECT
            c.technician_id,
            c.recipient_id,
            c.recipient_status,
            c.created_at,
            c.id,
            ROW_NUMBER() OVER (
                PARTITION BY c.technician_id
                ORDER BY c.created_at DESC, c.id DESC
            ) AS rn
        FROM connections c
        WHERE c.technician_id IS NOT NULL
    ),
    workloads AS (
        SELECT lt.recipient_id AS tech_id, COUNT(*) AS cnt
        FROM last_tech lt
        JOIN technician_orders t2 ON t2.id = lt.technician_id
        WHERE lt.rn = 1
          AND lt.recipient_status = 'between_controller_technician'
          AND t2.is_active = TRUE
          AND t2.status = 'between_controller_technician'
        GROUP BY lt.recipient_id
    )
    SELECT u.id, u.full_name, u.username, u.phone, u.telegram_id,
           COALESCE(w.cnt, 0) AS load_count
    FROM users u
    LEFT JOIN workloads w ON w.tech_id = u.id
    WHERE u.role::text = 'technician'
      AND COALESCE(u.is_blocked, FALSE) = FALSE
    ORDER BY u.full_name NULLS LAST, u.id;
    """

    sql_staff = """
    WITH last_staff AS (
        SELECT
            c.staff_id,
            c.recipient_id,
            c.recipient_status,
            c.created_at,
            c.id,
            ROW_NUMBER() OVER (
                PARTITION BY c.staff_id
                ORDER BY c.created_at DESC, c.id DESC
            ) AS rn
        FROM connections c
        WHERE c.staff_id IS NOT NULL
    ),
    workloads AS (
        SELECT ls.recipient_id AS tech_id, COUNT(*) AS cnt
        FROM last_staff ls
        JOIN staff_orders so ON so.id = ls.staff_id
        WHERE ls.rn = 1
          AND ls.recipient_status = 'between_controller_technician'
          AND COALESCE(so.is_active, TRUE) = TRUE
          AND so.status = 'between_controller_technician'
        GROUP BY ls.recipient_id
    )
    SELECT u.id, u.full_name, u.username, u.phone, u.telegram_id,
           COALESCE(w.cnt, 0) AS load_count
    FROM users u
    LEFT JOIN workloads w ON w.tech_id = u.id
    WHERE u.role::text = 'technician'
      AND COALESCE(u.is_blocked, FALSE) = FALSE
    ORDER BY u.full_name NULLS LAST, u.id;
    """

    sql_all = """
    WITH
    last_conn AS (
        SELECT c.connection_id, c.recipient_id, c.recipient_status, c.created_at, c.id,
               ROW_NUMBER() OVER (PARTITION BY c.connection_id ORDER BY c.created_at DESC, c.id DESC) rn
        FROM connections c WHERE c.connection_id IS NOT NULL
    ),
    last_tech AS (
        SELECT c.technician_id, c.recipient_id, c.recipient_status, c.created_at, c.id,
               ROW_NUMBER() OVER (PARTITION BY c.technician_id ORDER BY c.created_at DESC, c.id DESC) rn
        FROM connections c WHERE c.technician_id IS NOT NULL
    ),
    last_staff AS (
        SELECT c.staff_id, c.recipient_id, c.recipient_status, c.created_at, c.id,
               ROW_NUMBER() OVER (PARTITION BY c.staff_id ORDER BY c.created_at DESC, c.id DESC) rn
        FROM connections c WHERE c.staff_id IS NOT NULL
    ),
    work_conn AS (
        SELECT lc.recipient_id AS tech_id, COUNT(*) AS cnt
        FROM last_conn lc
        JOIN connection_orders co ON co.id = lc.connection_id
        WHERE lc.rn = 1
          AND lc.recipient_status = 'between_controller_technician'
          AND co.is_active = TRUE
          AND co.status = 'between_controller_technician'
        GROUP BY lc.recipient_id
    ),
    work_tech AS (
        SELECT lt.recipient_id AS tech_id, COUNT(*) AS cnt
        FROM last_tech lt
        JOIN technician_orders t2 ON t2.id = lt.technician_id
        WHERE lt.rn = 1
          AND lt.recipient_status = 'between_controller_technician'
          AND t2.is_active = TRUE
          AND t2.status = 'between_controller_technician'
        GROUP BY lt.recipient_id
    ),
    work_staff AS (
        SELECT ls.recipient_id AS tech_id, COUNT(*) AS cnt
        FROM last_staff ls
        JOIN staff_orders so ON so.id = ls.staff_id
        WHERE ls.rn = 1
          AND ls.recipient_status = 'between_controller_technician'
          AND COALESCE(so.is_active, TRUE) = TRUE
          AND so.status = 'between_controller_technician'
        GROUP BY ls.recipient_id
    ),
    workloads AS (
        SELECT tech_id, SUM(cnt) AS cnt
        FROM (
            SELECT * FROM work_conn
            UNION ALL
            SELECT * FROM work_tech
            UNION ALL
            SELECT * FROM work_staff
        ) u
        GROUP BY tech_id
    )
    SELECT u.id, u.full_name, u.username, u.phone, u.telegram_id,
           COALESCE(w.cnt, 0) AS load_count
    FROM users u
    LEFT JOIN workloads w ON w.tech_id = u.id
    WHERE u.role::text = 'technician'
      AND COALESCE(u.is_blocked, FALSE) = FALSE
    ORDER BY u.full_name NULLS LAST, u.id;
    """

    sql = (
        sql_connection if mode == "connection" else
        sql_technician if mode == "technician" else
        sql_staff if mode == "staff" else
        sql_all
    )

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(sql)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# =======================================================
#  Operatorga biriktirish (technician_orders)
# =======================================================
async def ensure_in_call_center_operator_enum() -> None:
    """
    technician_order_status ENUM ichida 'in_call_center_operator' borligini kafolatlaydi.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_enum e ON t.oid = e.enumtypid
                    WHERE t.typname = 'technician_order_status'
                      AND e.enumlabel = 'in_call_center_operator'
                ) THEN
                    ALTER TYPE technician_order_status ADD VALUE 'in_call_center_operator';
                END IF;
            END$$;
            """
        )
    finally:
        await conn.close()


async def assign_to_operator_for_tech(request_id: int | str, operator_id: int, actor_id: int) -> None:
    """
    technician_orders:  status -> 'in_call_center_operator'
    connections:        controller -> operator yozuvi
                        ✅ technician_id = technician_orders.id (TO‘G‘RI)
    """
    req_id = int(str(request_id).split("_")[0]) if isinstance(request_id, str) else int(request_id)

    # ENUM borligini kafolatlaymiz
    await ensure_in_call_center_operator_enum()

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # operator tekshirish
            ok = await conn.fetchval(
                """
                SELECT 1
                FROM users
                WHERE id = $1
                  AND COALESCE(is_blocked,FALSE) = FALSE
                  AND role::text = 'callcenter_operator'
                """,
                operator_id,
            )
            if not ok:
                raise ValueError("Operator not found or blocked")

            row_old = await conn.fetchrow(
                "SELECT status FROM technician_orders WHERE id=$1 FOR UPDATE",
                req_id,
            )
            if not row_old:
                raise ValueError("Technician order not found")
            old_status: str = row_old["status"]

            # technician_orders statusini operatorga o‘tkazamiz
            await conn.execute(
                """
                UPDATE technician_orders
                   SET status = 'in_call_center_operator'::technician_order_status,
                       updated_at = NOW()
                 WHERE id = $1
                """,
                req_id,
            )

            # ✅ connections.ga technician_id ga ariza id sini yozamiz
            await conn.execute(
                """
                INSERT INTO connections(
                    technician_id,         -- ← shu yerga yoziladi
                    sender_id,
                    recipient_id,
                    sender_status,
                    recipient_status,
                    created_at,
                    updated_at
                )
                VALUES ($1,$2,$3,$4,'in_call_center_operator',NOW(),NOW())
                """,
                req_id, actor_id, operator_id, old_status,
            )
    finally:
        await conn.close()

