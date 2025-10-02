# database/jm_inbox_queries.py
import asyncpg
from typing import Any, Dict, List, Optional
from config import settings

# 1) Telegram ID -> users
async def db_get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
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

# 2) connections (recipient_id bo‘yicha) — Eslatma: connections jadvalida user_id yo‘q!
async def db_get_connections_by_recipient(recipient_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                id,
                sender_id,
                recipient_id,
                connection_id AS connection_id,  -- = order_id (connection_orders.id)
                technician_id,
                staff_id       AS staff_id,
                created_at,
                updated_at
            FROM connections
            WHERE recipient_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            recipient_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# 3) connection_orders: id bo‘yicha olish
async def db_get_connection_order_by_connection_id(order_id: int) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT
                id,
                user_id,
                region,
                address,
                status,
                created_at,
                updated_at
            FROM connection_orders
            WHERE id = $1
            LIMIT 1
            """,
            order_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()

# 4) users.id -> user (F.I.O, telefon va h.k.)
async def db_get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT id, full_name, phone, language, role
            FROM users
            WHERE id = $1
            LIMIT 1
            """,
            user_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()

# ==================== JM oqimi ====================

# JM Inbox: faqat 'in_junior_manager' dagi arizalar
# connections(recipient_id = JM id) JOIN connection_orders(id = connection_id) LEFT JOIN users(order.user_id)
# ... db_get_jm_inbox_items() ichidagi SELECTni shu ko‘rinishga keltiring:
async def db_get_jm_inbox_items(recipient_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                c.id                   AS connection_record_id,
                c.sender_id,
                c.recipient_id,
                c.connection_id         AS connection_id,      -- order_id
                c.technician_id,
                c.staff_id              AS staff_id,
                c.created_at           AS connection_created_at,

                co.id                  AS order_id,           -- = connection_id
                co.created_at          AS order_created_at,
                co.region              AS order_region,
                co.address             AS order_address,
                co.status              AS order_status,
                co.user_id             AS order_user_id,
                co.jm_notes            AS order_jm_notes,     -- 🆕 qo‘shildi

                u.full_name            AS client_full_name,
                u.phone                AS client_phone
            FROM connections c
            JOIN connection_orders co ON co.id = c.connection_id
            LEFT JOIN users u         ON u.id  = co.user_id
            WHERE c.recipient_id = $1
              AND co.status = 'in_junior_manager'::connection_order_status
            ORDER BY co.created_at DESC
            LIMIT $2
            """,
            recipient_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# Order JM ga tegishli-yo'qligini tekshirish
async def db_check_order_ownership(order_id: int, jm_id: int) -> bool:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT 1
            FROM connections c
            WHERE c.recipient_id = $2
              AND c.connection_id = $1
            LIMIT 1
            """,
            order_id, jm_id
        )
        return bool(row)
    finally:
        await conn.close()

# Controller'ga yuborish: statusni 'in_controller' ga o'zgartirish (faqat hozir 'in_junior_manager' bo'lsa)
async def db_move_order_to_controller(order_id: int) -> bool:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            UPDATE connection_orders
               SET status    = 'in_controller'::connection_order_status,
                   updated_at = NOW()
             WHERE id        = $1
               AND status    = 'in_junior_manager'::connection_order_status
         RETURNING id
            """,
            order_id
        )
        return bool(row)
    finally:
        await conn.close()

# Ichki yordamchi: ixtiyoriy controller tanlash
async def db_pick_any_controller(conn) -> Optional[int]:
    row = await conn.fetchrow(
        """
        SELECT id
        FROM users
        WHERE role = 'controller' AND COALESCE(is_blocked, FALSE) = FALSE
        ORDER BY id
        LIMIT 1
        """
    )
    return row["id"] if row else None

# JM -> Controller: status logi bilan
async def db_jm_send_to_controller(order_id: int, jm_id: int, controller_id: Optional[int] = None) -> bool:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            row_old = await conn.fetchrow(
                "SELECT status FROM connection_orders WHERE id=$1 FOR UPDATE", order_id
            )
            if not row_old or row_old["status"] != "in_junior_manager":
                return False
            old_status = row_old["status"]

            row_new = await conn.fetchrow("""
                UPDATE connection_orders
                   SET status='in_controller'::connection_order_status,
                       updated_at=NOW()
                 WHERE id=$1 AND status='in_junior_manager'::connection_order_status
             RETURNING status
            """, order_id)
            if not row_new:
                return False
            new_status = row_new["status"]

            if controller_id is None:
                row = await conn.fetchrow("""
                    SELECT id FROM users
                    WHERE role='controller' AND COALESCE(is_blocked,false)=false
                    ORDER BY id LIMIT 1
                """)
                if not row:
                    raise ValueError("Controller topilmadi")
                controller_id = row["id"]

            # 👉 Faqat INSERT
            await conn.execute("""
                INSERT INTO connections(
                    connection_id, sender_id, recipient_id,
                    sender_status, recipient_status,
                    created_at, updated_at
                )
                VALUES ($1,$2,$3,$4::connection_order_status,$5::connection_order_status,NOW(),NOW())
            """, order_id, jm_id, controller_id, old_status, new_status)

            return True
    finally:
        await conn.close()


async def db_set_jm_notes(order_id: int, jm_id: int, note_text: str) -> bool:
    """
    JM izohini saqlaydi:
      - faqat shu ariza hozir 'in_junior_manager' bo‘lsa
      - va aynan shu JM (recipient)ga biriktirilgan bo‘lsa (connections orqali)
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # egalikni tekshiramiz
            owns = await conn.fetchrow(
                """
                SELECT 1
                  FROM connections
                 WHERE connection_id = $1
                   AND recipient_id = $2
                 LIMIT 1
                """,
                order_id, jm_id
            )
            if not owns:
                return False

            # statusni tekshirib, update qilamiz
            row = await conn.fetchrow(
                """
                UPDATE connection_orders
                   SET jm_notes  = $2,
                       updated_at = NOW()
                 WHERE id = $1
                   AND status = 'in_junior_manager'::connection_order_status
             RETURNING id
                """,
                order_id, note_text.strip()
            )
            return bool(row)
    finally:
        await conn.close()
