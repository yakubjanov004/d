# database/call_center_statistic_queries.py
import asyncpg
from typing import Dict
from config import settings

async def get_connection():
    return await asyncpg.connect(settings.DB_URL)

async def get_user_id_by_telegram_id(tg_id: int) -> int | None:
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1 LIMIT 1",
            tg_id
        )
        return row["id"] if row else None
    finally:
        await conn.close()

async def get_operator_stats_by_range(operator_id: int, range_key: str) -> Dict[str, int]:
    """
    range_key: 'day' | 'week' | 'month' | 'year'
    """
    interval_map = {
        "day":   "1 day",
        "week":  "7 days",
        "month": "1 month",
        "year":  "1 year",
    }
    interval = interval_map.get(range_key, "1 day")

    # ⚠️ interval parametr bo‘lib bormaydi — whitelistdan olinib literal bo‘lib qo‘yilyapti
    co_sql = f"""
        SELECT COUNT(*)::int
        FROM saff_orders
        WHERE user_id = $1
          AND type_of_zayavka = 'connection'
          AND is_active = TRUE
          AND created_at >= NOW() - INTERVAL '{interval}'
    """
    to_sql = f"""
        SELECT COUNT(*)::int
        FROM saff_orders
        WHERE user_id = $1
          AND type_of_zayavka = 'technician'
          AND created_at >= NOW() - INTERVAL '{interval}'
    """
    sent_sql = f"""
        SELECT COUNT(*)::int
        FROM connections
        WHERE sender_id = $1
          AND sender_status = 'in_call_center_operator'
          AND recipient_status = 'in_controller'
          AND created_at >= NOW() - INTERVAL '{interval}'
    """
    closed_sql = f"""
        SELECT COUNT(*)::int
        FROM connections
        WHERE sender_id = $1
          AND recipient_status = 'completed'
          AND created_at >= NOW() - INTERVAL '{interval}'
    """

    conn = await get_connection()
    try:
        connection_orders_total = await conn.fetchval(co_sql, operator_id)
        technician_orders_total = await conn.fetchval(to_sql, operator_id)
        sent_to_controller_total = await conn.fetchval(sent_sql, operator_id)
        closed_by_operator_total = await conn.fetchval(closed_sql, operator_id)
    finally:
        await conn.close()

    return {
        "connection_orders_total": connection_orders_total or 0,
        "technician_orders_total": technician_orders_total or 0,
        "sent_to_controller_total": sent_to_controller_total or 0,
        "closed_by_operator_total": closed_by_operator_total or 0,
    }