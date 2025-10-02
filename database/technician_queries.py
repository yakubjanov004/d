# database/technician_queries.py
import asyncpg
from typing import List, Dict, Any, Optional
from config import settings


# ----------------- YORDAMCHI -----------------
async def _conn():
    return await asyncpg.connect(settings.DB_URL)

def _as_dicts(rows):
    return [dict(r) for r in rows]


# ======================= INBOX: CONNECTION_ORDERS =======================
async def fetch_technician_inbox(
    technician_user_id: Optional[int] = None,
    *,
    technician_id: Optional[int] = None,   # alias
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Connection orders: oxirgi biriktirish (connections) bo‘yicha texnikka tegishli faol arizalar.
    E’TIBOR: connections.connection_id (sic) — connection_orders.id ni bildiradi.
    """
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("fetch_technician_inbox(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            WITH last_conn AS (
                SELECT
                    c.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.connection_id, c.recipient_id
                        ORDER BY c.created_at DESC, c.id DESC
                    ) AS rn
                FROM connections c
                WHERE c.recipient_id = $1
                  AND c.connection_id IS NOT NULL
            )
            SELECT
                co.id,
                co.address,
                co.region,
                co.status,
                co.created_at,
                u.full_name AS client_name,
                u.phone     AS client_phone,
                t.name      AS tariff
            FROM last_conn c
            JOIN connection_orders co ON co.id = c.connection_id
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE
                c.rn = 1
                AND co.is_active = TRUE
                AND co.status IN (
                    'between_controller_technician'::connection_order_status,
                    'in_technician'::connection_order_status,
                    'in_technician_work'::connection_order_status
                )
            ORDER BY
                CASE co.status
                    WHEN 'between_controller_technician'::connection_order_status THEN 0
                    WHEN 'in_technician'::connection_order_status                 THEN 1
                    WHEN 'in_technician_work'::connection_order_status            THEN 2
                    ELSE 3
                END,
                co.created_at DESC,
                co.id DESC
            LIMIT $2 OFFSET $3
            """,
            uid, limit, offset
        )
        return _as_dicts(rows)
    finally:
        await conn.close()


async def count_technician_inbox(
    technician_user_id: Optional[int] = None,
    *,
    technician_id: Optional[int] = None  # alias
) -> int:
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("count_technician_inbox(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        cnt = await conn.fetchval(
            """
            WITH last_conn AS (
                SELECT
                    c.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.connection_id, c.recipient_id
                        ORDER BY c.created_at DESC, c.id DESC
                    ) AS rn
                FROM connections c
                WHERE c.recipient_id = $1
                  AND c.connection_id IS NOT NULL
            )
            SELECT COUNT(*)
            FROM last_conn c
            JOIN connection_orders co ON co.id = c.connection_id
            WHERE
                c.rn = 1
                AND co.is_active = TRUE
                AND co.status IN (
                    'between_controller_technician'::connection_order_status,
                    'in_technician'::connection_order_status,
                    'in_technician_work'::connection_order_status
                )
            """,
            uid
        )
        return int(cnt or 0)
    finally:
        await conn.close()


# ------ Status o‘zgartirish (CONNECTION_ORDERS) ------
async def cancel_technician_request(applications_id: int,
                                    technician_user_id: Optional[int] = None, *,
                                    technician_id: Optional[int] = None) -> None:
    _ = technician_user_id if technician_user_id is not None else technician_id  # alias, bu yerda ishlatilmaydi
    conn = await _conn()
    try:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE connection_orders
                   SET is_active = FALSE,
                       updated_at = NOW()
                 WHERE id = $1
                """,
                applications_id
            )
    finally:
        await conn.close()


async def accept_technician_work(applications_id: int,
                                 technician_user_id: Optional[int] = None, *,
                                 technician_id: Optional[int] = None) -> bool:
    """between_controller_technician -> in_technician"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("accept_technician_work(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM connection_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'between_controller_technician':
                return False

            row_new = await conn.fetchrow(
                """
                UPDATE connection_orders
                   SET status = 'in_technician'::connection_order_status,
                       updated_at = NOW()
                 WHERE id=$1 AND status='between_controller_technician'::connection_order_status
             RETURNING status
                """,
                applications_id
            )
            if not row_new:
                return False

            await conn.execute(
                """
                INSERT INTO connections (
                    connection_id, sender_id, recipient_id,
                    sender_status, recipient_status, created_at, updated_at
                )
                VALUES ($1, $2, $2,
                        'between_controller_technician'::connection_order_status,
                        'in_technician'::connection_order_status,
                        NOW(), NOW())
                """,
                applications_id, uid
            )
            return True
    finally:
        await conn.close()


async def start_technician_work(applications_id: int,
                                technician_user_id: Optional[int] = None, *,
                                technician_id: Optional[int] = None) -> bool:
    """in_technician -> in_technician_work"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("start_technician_work(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM connection_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'in_technician':
                return False

            row_new = await conn.fetchrow(
                """
                UPDATE connection_orders
                   SET status='in_technician_work'::connection_order_status,
                       updated_at=NOW()
                 WHERE id=$1 AND status='in_technician'::connection_order_status
             RETURNING status
                """,
                applications_id
            )
            if not row_new:
                return False

            await conn.execute(
                """
                INSERT INTO connections(
                    connection_id, sender_id, recipient_id,
                    sender_status, recipient_status,
                    created_at, updated_at
                )
                VALUES ($1, $2, $2,
                        'in_technician'::connection_order_status,
                        'in_technician_work'::connection_order_status,
                        NOW(), NOW())
                """,
                applications_id, uid
            )
            return True
    finally:
        await conn.close()


async def finish_technician_work(applications_id: int,
                                 technician_user_id: Optional[int] = None, *,
                                 technician_id: Optional[int] = None) -> bool:
    """in_technician_work -> completed"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("finish_technician_work(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM connection_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'in_technician_work':
                return False

            ok = await conn.fetchrow(
                """
                UPDATE connection_orders
                   SET status = 'completed'::connection_order_status,
                       updated_at = NOW()
                 WHERE id = $1 AND status = 'in_technician_work'::connection_order_status
             RETURNING id
                """,
                applications_id
            )
            if not ok:
                return False

            await conn.execute(
                """
                INSERT INTO connections (
                    connection_id, sender_id, recipient_id,
                    sender_status, recipient_status, created_at, updated_at
                )
                VALUES ($1, $2, $2,
                        'in_technician_work'::connection_order_status,
                        'completed'::connection_order_status,
                        NOW(), NOW())
                """,
                applications_id, uid
            )
            return True
    finally:
        await conn.close()


# ======================= MATERIALLAR (SELECTION) =======================
async def fetch_technician_materials(user_id: int = None, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    conn = await _conn()
    try:
        if user_id is not None:
            rows = await conn.fetch(
                """
                SELECT
                  m.id          AS material_id,
                  m.name,
                  m.price,
                  m.serial_number,
                  t.quantity    AS stock_quantity
                FROM material_and_technician t
                JOIN materials m ON m.id = t.material_id
                WHERE t.user_id = $1
                  AND t.quantity > 0
                ORDER BY m.name
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                  m.id          AS material_id,
                  m.name,
                  m.price,
                  m.serial_number,
                  t.quantity    AS stock_quantity
                FROM material_and_technician t
                JOIN materials m ON m.id = t.material_id
                WHERE t.quantity > 0
                ORDER BY m.name
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
        return _as_dicts(rows)
    finally:
        await conn.close()



async def fetch_all_materials(limit: int = 200, offset: int = 0) -> list[dict]:
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                m.id   AS material_id,
                m.name,
                COALESCE(m.price, 0) AS price
            FROM materials m
            ORDER BY m.name
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def fetch_material_by_id(material_id: int) -> Optional[Dict[str, Any]]:
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            "SELECT id, name, price, serial_number FROM materials WHERE id=$1",
            material_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def fetch_assigned_qty(user_id: int, material_id: int) -> int:
    """Texnikka biriktirilgan joriy qoldiq."""
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            """
            SELECT COALESCE(quantity, 0) AS qty
            FROM material_and_technician
            WHERE user_id = $1 AND material_id = $2
            """,
            user_id, material_id
        )
        return int(row["qty"]) if row else 0
    finally:
        await conn.close()


# --- MUHIM: Tanlovni jamlamay, aynan o‘rnatuvchi upsert (OVERWRITE) ---

async def _has_column(conn, table: str, column: str) -> bool:
    """
    Checks if a column exists in a given table.
    """
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = $1 AND column_name = $2
        )
    """
    return await conn.fetchval(sql, table, column)

async def upsert_material_selection(
    user_id: int,
    applications_id: int,
    material_id: int,
    qty: int,
) -> None:
    """
    Tanlangan miqdorni to'g'ridan-to'g'ri o'rnatadi (jamlamaydi).
    material_requests da UNIQUE (user_id, applications_id, material_id) tavsiya etiladi.
    """
    if qty <= 0:
        raise ValueError("Miqdor 0 dan katta bo‘lishi kerak")

    conn = await _conn()
    try:
        async with conn.transaction():
            price = await conn.fetchval(
                "SELECT COALESCE(price, 0) FROM materials WHERE id=$1",
                material_id
            ) or 0
            total = price * qty

            has_updated_at = await _has_column(conn, "material_requests", "updated_at")

            if has_updated_at:
                sql = """
                    INSERT INTO material_requests (user_id, applications_id, material_id, quantity, price, total_price)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id, applications_id, material_id)
                    DO UPDATE SET
                        quantity    = EXCLUDED.quantity,
                        price       = EXCLUDED.price,
                        total_price = EXCLUDED.total_price,
                        updated_at  = NOW()
                """
            else:
                sql = """
                    INSERT INTO material_requests (user_id, applications_id, material_id, quantity, price, total_price)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id, applications_id, material_id)
                    DO UPDATE SET
                        quantity    = EXCLUDED.quantity,
                        price       = EXCLUDED.price,
                        total_price = EXCLUDED.total_price
                """

            await conn.execute(sql, user_id, applications_id, material_id, qty, price, total)
    finally:
        await conn.close()


# async def upsert_material_selection(
#     user_id: int,
#     applications_id: int,
#     material_id: int,
#     qty: int,
# ) -> None:
#     """
#     Tanlangan miqdorni to‘g‘ridan-to‘g‘ri o‘rnatadi (jamlamaydi).
#     material_requests da UNIQUE (user_id, applications_id, material_id) bo‘lishi tavsiya etiladi.
#     """
#     if qty <= 0:
#         raise ValueError("Miqdor 0 dan katta bo‘lishi kerak")

#     conn = await _conn()
#     try:
#         async with conn.transaction():
#             price = await conn.fetchval(
#                 "SELECT COALESCE(price, 0) FROM materials WHERE id=$1",
#                 material_id
#             ) or 0
#             total = price * qty

#             await conn.execute(
#                 """
#                 INSERT INTO material_requests (user_id, applications_id, material_id, quantity, price, total_price)
#                 VALUES ($1, $2, $3, $4, $5, $6)
#                 ON CONFLICT (user_id, applications_id, material_id)
#                 DO UPDATE SET
#                     quantity    = EXCLUDED.quantity,
#                     price       = EXCLUDED.price,
#                     total_price = EXCLUDED.total_price,
#                 """,
#                 user_id, applications_id, material_id, qty, price, total
#             )
#     finally:
#         await conn.close()


# Orqa-ward compat: eski nomli funksiya ham shu mantiqqa yo‘naltiriladi
async def upsert_material_request_and_decrease_stock(
    user_id: int,
    applications_id: int,
    material_id: int,
    add_qty: int,
) -> None:
    await upsert_material_selection(user_id, applications_id, material_id, add_qty)


async def fetch_selected_materials_for_request(
    user_id: int,
    applications_id: int
) -> list[dict]:
    """
    Tanlangan materiallar ro‘yxati.
    Eski testlarda dublikat yozuvlar bo‘lishi mumkinligi uchun SUM(...) qilib jamlaymiz.
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.material_id,
                m.name,
                COALESCE(m.price, 0) AS price,
                SUM(
                    COALESCE(mr.quantity, 0)
                    + COALESCE(NULLIF(mr.description, '')::int, 0)
                ) AS qty
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            WHERE mr.user_id = $1
              AND mr.applications_id = $2
            GROUP BY mr.material_id, m.name, m.price
            ORDER BY m.name
            """,
            user_id, applications_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# --- Omborga jo‘natish: material_requests’ga QAYTA yozmaydi! ---
async def pick_warehouse_user_rr(seed: int) -> int | None:
    """
    Omborchilar orasidan bitta foydalanuvchini round-robin usulida tanlaydi.
    seed odatda applications_id bo'ladi.
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT id
            FROM users
            WHERE role = 'warehouse'
            ORDER BY id
            """
        )
        if not rows:
            return None
        ids = [r["id"] for r in rows]
        return ids[seed % len(ids)]
    finally:
        await conn.close()


async def send_selection_to_warehouse(
    applications_id: int,
    technician_user_id: Optional[int] = None, *,
    technician_id: Optional[int] = None,
    request_type: str = "connection",  # 'connection' | 'technician' | 'staff'
) -> bool:
    """
    Tanlangan materiallarni omborga jo‘natish.
    - material_requests ga QAYTA insert qilinmaydi (dublikatning ildizi shu edi).
    - faqat statusni 'in_warehouse' ga o‘tkazamiz va connections ga tarix yozamiz (to‘g‘ri id-ustun bilan).
    """
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("send_selection_to_warehouse(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            # 1) status -> in_warehouse
            if request_type == "technician":
                await conn.execute(
                    "UPDATE technician_orders SET status='in_warehouse', updated_at=NOW() WHERE id=$1",
                    applications_id
                )
            elif request_type == "staff":
                await conn.execute(
                    "UPDATE staff_orders SET status='in_warehouse', updated_at=NOW() WHERE id=$1",
                    applications_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE connection_orders
                       SET status='in_warehouse'::connection_order_status,
                           updated_at=NOW()
                     WHERE id=$1
                    """,
                    applications_id
                )

            # 2) connections ga tarix yozish: recipient — omborchi
            warehouse_id = await pick_warehouse_user_rr(applications_id)
            if warehouse_id is not None:
                conn_id  = applications_id if request_type == "connection"  else None
                tech_oid = applications_id if request_type == "technician" else None
                staff_oid = applications_id if request_type == "staff"       else None

                await conn.execute(
                    """
                    INSERT INTO connections(
                        sender_id, recipient_id,
                        connection_id, technician_id, staff_id,
                        sender_status, recipient_status,
                        created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5,
                            'in_technician_work', 'in_warehouse',
                            NOW(), NOW())
                    """,
                    uid, warehouse_id, conn_id, tech_oid, staff_oid
                )

            return True
    finally:
        await conn.close()


# Eski nom bilan chaqirilsa ham yangi mantiqqa yo‘naltirish
async def create_material_request_and_mark_in_warehouse(
    applications_id: int,
    technician_user_id: Optional[int] = None, *,
    technician_id: Optional[int] = None,
    material_id: int = 0,
    qty: int = 0,
    request_type: str = "connection",
) -> bool:
    # material_requests ga QAYTA yozmaymiz; tanlov bosqichida upsert_material_selection ishlatiladi.
    uid = technician_user_id if technician_user_id is not None else technician_id
    return await send_selection_to_warehouse(applications_id, technician_user_id=uid, request_type=request_type)


# ======================= INBOX: TECHNICIAN_ORDERS =======================
async def fetch_technician_inbox_tech(
    technician_user_id: Optional[int] = None,  # eski nom (asosiy)
    *,
    technician_id: Optional[int] = None,       # yangi nom (alias)
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Technician orders: oxirgi biriktirish bo‘yicha texnikka tegishli faol arizalar.
    DIQQAT: Ba'zi eski yozuvlarda connections.technician_id NULL, lekin connection_id
    (imlo bilan) ichida technician_orders.id turgan — shu holatni ham qo‘llab-quvvatlaymiz.
    """
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("fetch_technician_inbox_tech(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            WITH last_conn AS (
                SELECT
                    c.id,
                    c.recipient_id,
                    /* Eski xatolarni ham ushlash uchun fallback: */
                    COALESCE(c.technician_id, c.connection_id) AS tech_order_id,
                    c.created_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY COALESCE(c.technician_id, c.connection_id), c.recipient_id
                        ORDER BY c.created_at DESC, c.id DESC
                    ) AS rn
                FROM connections c
                WHERE c.recipient_id = $1
                  AND (c.technician_id IS NOT NULL OR c.connection_id IS NOT NULL)
            )
            SELECT
                to2.id,
                to2.address,
                to2.region,
                to2.status,
                to2.created_at,
                to2.description,
                to2.media,
                to2.description_operator,
                to2.description_ish,
                u.full_name AS client_name,
                u.phone     AS client_phone,
                NULL        AS tariff
            FROM last_conn lc
            JOIN technician_orders to2 ON to2.id = lc.tech_order_id
            LEFT JOIN users u ON u.id = to2.user_id
            WHERE
                lc.rn = 1
                AND to2.is_active = TRUE
                AND to2.status IN ('between_controller_technician','in_technician','in_technician_work')
            ORDER BY
                CASE to2.status
                    WHEN 'between_controller_technician' THEN 0
                    WHEN 'in_technician'                 THEN 1
                    WHEN 'in_technician_work'            THEN 2
                    ELSE 3
                END,
                to2.created_at DESC,
                to2.id DESC
            LIMIT $2 OFFSET $3
            """,
            uid, limit, offset
        )
        return _as_dicts(rows)
    finally:
        await conn.close()


async def accept_technician_work_for_tech(applications_id: int,
                                          technician_user_id: Optional[int] = None, *,
                                          technician_id: Optional[int] = None) -> bool:
    """Technician_orders: between_controller_technician -> in_technician (connections.technician_id to‘ldiriladi)"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("accept_technician_work_for_tech(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM technician_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'between_controller_technician':
                return False

            row_new = await conn.fetchrow(
                """
                UPDATE technician_orders
                   SET status = 'in_technician',
                       updated_at = NOW()
                 WHERE id=$1 AND status='between_controller_technician'
             RETURNING status
                """,
                applications_id
            )
            if not row_new:
                return False

            try:
                await conn.execute(
                    """
                    INSERT INTO connections(
                        technician_id, sender_id, recipient_id,
                        sender_status, recipient_status, created_at, updated_at
                    )
                    VALUES ($1, $2, $2, 'between_controller_technician', 'in_technician', NOW(), NOW())
                    """,
                    applications_id, uid
                )
            except Exception:
                pass
            return True
    finally:
        await conn.close()


async def start_technician_work_for_tech(applications_id: int,
                                         technician_user_id: Optional[int] = None, *,
                                         technician_id: Optional[int] = None) -> bool:
    """Technician_orders: in_technician -> in_technician_work"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("start_technician_work_for_tech(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM technician_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'in_technician':
                return False

            row_new = await conn.fetchrow(
                """
                UPDATE technician_orders
                   SET status='in_technician_work',
                       updated_at=NOW()
                 WHERE id=$1 AND status='in_technician'
             RETURNING status
                """,
                applications_id
            )
            if not row_new:
                return False

            try:
                await conn.execute(
                    """
                    INSERT INTO connections(
                        technician_id, sender_id, recipient_id,
                        sender_status, recipient_status, created_at, updated_at
                    )
                    VALUES ($1, $2, $2, 'in_technician', 'in_technician_work', NOW(), NOW())
                    """,
                    applications_id, uid
                )
            except Exception:
                pass
            return True
    finally:
        await conn.close()


async def save_technician_diagnosis(applications_id: int,
                                    technician_user_id: Optional[int] = None, *,
                                    technician_id: Optional[int] = None,
                                    text: str = "") -> None:
    _ = technician_user_id if technician_user_id is not None else technician_id  # alias, bu yerda ishlatilmaydi
    conn = await _conn()
    try:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE technician_orders
                   SET description_ish = $2,
                       updated_at = NOW()
                 WHERE id = $1
                """,
                applications_id, text
            )
    finally:
        await conn.close()


async def cancel_technician_request_for_tech(applications_id: int,
                                             technician_user_id: Optional[int] = None, *,
                                             technician_id: Optional[int] = None) -> None:
    _ = technician_user_id if technician_user_id is not None else technician_id  # alias, bu yerda ishlatilmaydi
    conn = await _conn()
    try:
        async with conn.transaction():
            await conn.execute(
                "UPDATE technician_orders SET is_active = FALSE, updated_at = NOW() WHERE id=$1",
                applications_id
            )
    finally:
        await conn.close()


async def finish_technician_work_for_tech(applications_id: int,
                                          technician_user_id: Optional[int] = None, *,
                                          technician_id: Optional[int] = None) -> bool:
    """Technician_orders: in_technician_work -> completed (connections.technician_id to‘ldiriladi)"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("finish_technician_work_for_tech(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM technician_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'in_technician_work':
                return False

            ok = await conn.fetchrow(
                """
                UPDATE technician_orders
                   SET status='completed',
                       updated_at=NOW()
                 WHERE id=$1 AND status='in_technician_work'
             RETURNING id
                """,
                applications_id
            )
            if not ok:
                return False

            try:
                await conn.execute(
                    """
                    INSERT INTO connections(
                        technician_id, sender_id, recipient_id,
                        sender_status, recipient_status, created_at, updated_at
                    )
                    VALUES ($1, $2, $2, 'in_technician_work', 'completed', NOW(), NOW())
                    """,
                    applications_id, uid
                )
            except Exception:
                pass

            return True
    finally:
        await conn.close()


# ======================= INBOX: staff_ORDERS =======================
async def fetch_technician_inbox_staff(
    technician_user_id: Optional[int] = None,
    *,
    technician_id: Optional[int] = None,  # alias
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    staff orders: oxirgi biriktirish bo‘yicha texnikka tegishli faol arizalar.
    Eslatma: connections.staff_id — staff_orders.id ni bildiradi.
    Filtr: recipient_id = texnik foydalanuvchi.
    """
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("fetch_technician_inbox_staff(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            WITH last_conn AS (
                SELECT
                    c.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.staff_id, c.recipient_id
                        ORDER BY c.created_at DESC, c.id DESC
                    ) AS rn
                FROM connections c
                WHERE c.recipient_id = $1
                  AND c.staff_id IS NOT NULL
            )
            SELECT 
                so.id,
                so.phone,
                so.region,
                so.abonent_id,
                so.address,
                so.description,
                so.status,
                so.created_at,
                u.full_name     AS client_name,
                u.telegram_id,
                NULL AS tariff
            FROM last_conn c
            JOIN staff_orders so ON so.id = c.staff_id
            LEFT JOIN users u ON u.id = so.user_id
            WHERE
                c.rn = 1
                AND so.is_active = TRUE
                AND so.status IN ('between_controller_technician','in_technician','in_technician_work')
            ORDER BY
                CASE so.status
                    WHEN 'between_controller_technician' THEN 0
                    WHEN 'in_technician'                 THEN 1
                    WHEN 'in_technician_work'            THEN 2
                    ELSE 3
                END,
                so.created_at DESC,
                so.id DESC
            LIMIT $2 OFFSET $3
            """,
            uid, limit, offset
        )
        return _as_dicts(rows)
    finally:
        await conn.close()


async def accept_technician_work_for_staff(applications_id: int,
                                          technician_user_id: Optional[int] = None, *,
                                          technician_id: Optional[int] = None) -> bool:
    """staff order: between_controller_technician -> in_technician (connections.staff_id = applications_id)"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("accept_technician_work_for_staff(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM staff_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'between_controller_technician':
                return False

            row_new = await conn.fetchrow(
                """
                UPDATE staff_orders
                   SET status = 'in_technician',
                       updated_at = NOW()
                 WHERE id=$1 AND status='between_controller_technician'
             RETURNING status
                """,
                applications_id
            )
            if not row_new:
                return False

            await conn.execute(
                """
                INSERT INTO connections(
                    staff_id, sender_id, recipient_id,
                    sender_status, recipient_status, created_at, updated_at
                )
                VALUES ($1, $2, $2, 'between_controller_technician', 'in_technician', NOW(), NOW())
                """,
                applications_id, uid
            )

            return True
    finally:
        await conn.close()


async def start_technician_work_for_staff(applications_id: int,
                                         technician_user_id: Optional[int] = None, *,
                                         technician_id: Optional[int] = None) -> bool:
    """staff order: in_technician -> in_technician_work"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("start_technician_work_for_staff(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM staff_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'in_technician':
                return False

            row_new = await conn.fetchrow(
                """
                UPDATE staff_orders
                   SET status='in_technician_work',
                       updated_at=NOW()
                 WHERE id=$1 AND status='in_technician'
             RETURNING status
                """,
                applications_id
            )
            if not row_new:
                return False

            await conn.execute(
                """
                INSERT INTO connections(
                    staff_id, sender_id, recipient_id,
                    sender_status, recipient_status, created_at, updated_at
                )
                VALUES ($1, $2, $2, 'in_technician', 'in_technician_work', NOW(), NOW())
                """,
                applications_id, uid
            )

            return True
    finally:
        await conn.close()


async def finish_technician_work_for_staff(applications_id: int,
                                          technician_user_id: Optional[int] = None, *,
                                          technician_id: Optional[int] = None) -> bool:
    """staff order: in_technician_work -> completed"""
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("finish_technician_work_for_staff(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM staff_orders WHERE id=$1 FOR UPDATE",
                applications_id
            )
            if not row_old or row_old["status"] != 'in_technician_work':
                return False

            row_new = await conn.fetchrow(
                """
                UPDATE staff_orders
                   SET status = 'completed',
                       updated_at = NOW()
                 WHERE id = $1 AND status = 'in_technician_work'
             RETURNING id
                """,
                applications_id
            )
            if not row_new:
                return False

            try:
                await conn.execute(
                    """
                    INSERT INTO connections(
                        staff_id, sender_id, recipient_id,
                        sender_status, recipient_status, created_at, updated_at
                    )
                    VALUES ($1, $2, $2, 'in_technician_work', 'completed', NOW(), NOW())
                    """,
                    applications_id, uid
                )
            except Exception:
                pass

            return True
    finally:
        await conn.close()
