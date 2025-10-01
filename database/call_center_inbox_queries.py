import asyncpg
from typing import List, Dict, Any
from config import settings


# === Ulash funksiyasi ===
async def get_connection():
    return await asyncpg.connect(settings.DB_URL)


# === Operator uchun arizalar ===
async def get_operator_orders(operator_id: int) -> List[Dict[str, Any]]:
    conn = await get_connection()
    rows = await conn.fetch(
        """
        SELECT
            t.id,
            t.region,
            t.address,
            t.description,
            t.status,
            t.description_operator AS comments,  -- 👈 alias
            u.full_name AS user_full_name
        FROM technician_orders t
        JOIN users u ON u.id = t.user_id
        WHERE t.is_active = TRUE
          AND t.status = 'in_call_center_operator'
        ORDER BY t.created_at ASC
        """
    )
    await conn.close()
    return [dict(r) for r in rows]



# === Status yangilash ===
async def update_order_status(order_id: int, status: str, is_active: bool = True) -> None:
    conn = await get_connection()
    await conn.execute(
        """
        UPDATE technician_orders
        SET status = $1, is_active = $2, updated_at = NOW()
        WHERE id = $3
        """,
        status, is_active, order_id,
    )
    await conn.close()


# === Operator izoh qo‘shish ===
async def add_order_comment(order_id: int, comment: str) -> None:
    conn = await get_connection()
    await conn.execute(
        """
        UPDATE technician_orders
        SET description_operator = $1, updated_at = NOW()
        WHERE id = $2
        """,
        comment, order_id,
    )
    await conn.close()


# --- YANGI: controller id ni olish ---
async def get_any_controller_id(conn=None) -> int | None:
    need_close = False
    if conn is None:
        conn = await get_connection()
        need_close = True
    row = await conn.fetchrow("""
        SELECT id
        FROM users
        WHERE role = 'controller'
        ORDER BY id ASC
        LIMIT 1
    """)
    if need_close:
        await conn.close()
    return row["id"] if row else None


# --- YANGI: connections ga yozish ---
async def log_connection_from_operator(
    sender_id: int,
    recipient_id: int,
    technician_order_id: int,
) -> int:
    """
    connections(sender_id, recipient_id, technician_id, sender_status, recipient_status)
    technician_id ustuniga ariza_id yoziladi (talabingiz bo‘yicha).
    """
    conn = await get_connection()
    row = await conn.fetchrow(
        """
        INSERT INTO connections (
            sender_id, recipient_id, technician_id, sender_status, recipient_status
        )
        VALUES ($1, $2, $3, 'in_call_center_operator', 'in_controller')
        RETURNING id
        """,
        sender_id, recipient_id, technician_order_id
    )
    await conn.close()
    return row["id"]

async def get_user_id_by_telegram_id(telegram_id: int) -> int | None:
    conn = await get_connection()
    row = await conn.fetchrow(
        """
        SELECT id
        FROM users
        WHERE telegram_id = $1
        LIMIT 1
        """,
        telegram_id,
    )
    await conn.close()
    return row["id"] if row else None

async def log_connection_completed_from_operator(
    sender_id: int,          # users.id (operator)
    recipient_id: int,       # users.id (controller)
    technician_order_id: int # technician_orders.id
) -> int:
    """
    Operator arizani YOPGANIDA (completed):
    connections ga yozamiz:
      - sender_id, recipient_id (users.id)
      - technician_id = technician_orders.id
      - sender_status = 'in_call_center_operator'
      - recipient_status = 'completed'
    """
    conn = await get_connection()
    row = await conn.fetchrow(
        """
        INSERT INTO connections (
            sender_id,
            recipient_id,
            technician_id,
            sender_status,
            recipient_status
        )
        VALUES ($1, $2, $3, 'in_call_center_operator', 'completed')
        RETURNING id
        """,
        sender_id, recipient_id, technician_order_id
    )
    await conn.close()
    return row["id"]
