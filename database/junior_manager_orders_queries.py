# database/junior_manager_orders_queries.py
from __future__ import annotations
from typing import List, Dict, Optional
import asyncpg
from datetime import datetime, timezone
from config import settings

# --- Autodetect helpers ---

async def _detect_conn_fk_col(conn) -> str:
    q = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='connections' AND column_name = ANY($1::text[])
    """
    rows = await conn.fetch(q, ['connection_id', 'connection_id'])
    cols = [r['column_name'] for r in rows]
    return cols[0] if cols else 'connection_id'  # sizdagi typo bo‘lishi mumkin

async def _resolve_user_id_by_telegram(conn, telegram_id: int) -> Optional[int]:
    qcols = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='users' AND column_name = ANY($1::text[])
    """
    rows = await conn.fetch(qcols, ['telegram_id', 'tg_id', 'chat_id'])
    cols = [r['column_name'] for r in rows]
    if not cols:
        return None
    where = " OR ".join([f"{c}::text = $1::text" for c in cols])
    sql = f"SELECT id FROM users WHERE {where} LIMIT 1"
    row = await conn.fetchrow(sql, str(telegram_id))
    return int(row['id']) if row and row['id'] is not None else None

# --- Base SELECT qo‘shimcha maydonlar bilan (users join) ---

_BASE_FIELDS = """
    co.id,
    co.created_at,
    (co.status)::text AS status_text,
    co.address,
    u.full_name AS user_name
"""

# --- PUBLIC API ---

async def list_new_for_jm(telegram_id: int, limit: int = 200) -> List[Dict[str, any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        jm_id = await _resolve_user_id_by_telegram(conn, telegram_id)
        if jm_id is None:
            return []
        fk = await _detect_conn_fk_col(conn)

        sql = f"""
        WITH incoming AS (
          SELECT DISTINCT c.{fk} AS order_id
          FROM connections c
          WHERE c.recipient_id = $1 AND c.recipient_status = 'in_junior_manager'
        ),
        sent_by_me AS (
          SELECT DISTINCT c.{fk} AS order_id
          FROM connections c
          WHERE c.sender_id = $1 AND c.sender_status = 'in_junior_manager'
        )
        SELECT {_BASE_FIELDS}
        FROM connection_orders co
        JOIN incoming i ON i.order_id = co.id
        LEFT JOIN sent_by_me s ON s.order_id = co.id
        LEFT JOIN users u ON u.id = co.user_id
        WHERE s.order_id IS NULL
        ORDER BY co.created_at DESC
        LIMIT $2;
        """
        rows = await conn.fetch(sql, jm_id, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_inprogress_for_jm(telegram_id: int, limit: int = 200) -> List[Dict[str, any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        jm_id = await _resolve_user_id_by_telegram(conn, telegram_id)
        if jm_id is None:
            return []
        fk = await _detect_conn_fk_col(conn)

        sql = f"""
        WITH sent_by_me AS (
          SELECT DISTINCT c.{fk} AS order_id
          FROM connections c
          WHERE c.sender_id = $1 AND c.sender_status = 'in_junior_manager'
        ),
        last_hop AS (
          SELECT DISTINCT ON (c.{fk}) c.{fk} AS order_id,
                 c.recipient_status AS flow_status,
                 c.created_at
          FROM connections c
          JOIN sent_by_me s ON s.order_id = c.{fk}
          ORDER BY c.{fk}, c.created_at DESC
        )
        SELECT {_BASE_FIELDS},
               lh.flow_status
        FROM connection_orders co
        JOIN sent_by_me s ON s.order_id = co.id
        LEFT JOIN last_hop lh ON lh.order_id = co.id
        LEFT JOIN users u ON u.id = co.user_id
        WHERE (co.status)::text <> 'completed'
        ORDER BY co.created_at DESC
        LIMIT $2;
        """
        rows = await conn.fetch(sql, jm_id, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_completed_for_jm(telegram_id: int, limit: int = 200) -> List[Dict[str, any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        jm_id = await _resolve_user_id_by_telegram(conn, telegram_id)
        if jm_id is None:
            return []
        fk = await _detect_conn_fk_col(conn)

        sql = f"""
        WITH sent_by_me AS (
          SELECT DISTINCT c.{fk} AS order_id
          FROM connections c
          WHERE c.sender_id = $1 AND c.sender_status = 'in_junior_manager'
        )
        SELECT {_BASE_FIELDS}
        FROM connection_orders co
        JOIN sent_by_me s ON s.order_id = co.id
        LEFT JOIN users u ON u.id = co.user_id
        WHERE (co.status)::text = 'completed'
        ORDER BY co.updated_at DESC, co.created_at DESC
        LIMIT $2;
        """
        rows = await conn.fetch(sql, jm_id, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()
