# database/staff_activity_queries.py
import asyncpg
from config import settings

async def get_active_connection_tasks_count() -> int:
    """
    Aktiv vazifalar soni:
      saff_orders jadvalidan is_active = TRUE
      va status 'completed' EMAS
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM saff_orders
             WHERE is_active = TRUE
               AND status <> 'completed'
            """
        )
    finally:
        await conn.close()

async def get_callcenter_operator_count() -> int:
    """
    Umumiy xodimlar soni:
      users jadvalidan role = 'callcenter_operator'
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM users
             WHERE role = 'callcenter_operator'
            """
        )
    finally:
        await conn.close()

async def get_canceled_connection_tasks_count() -> int:
    """
    Bekor qilingan vazifalar soni:
      saff_orders jadvalidan is_active = False
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM saff_orders
             WHERE is_active = FALSE
            """
        )
    finally:
        await conn.close()

async def get_operator_orders_stat() -> list[dict]:
    """
    Call center operatorlar kesimi bo'yicha statistikani olish
    Har bir operator nechta technician va connection ariza yaratganini qaytaradi
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                u.full_name,
                COUNT(*) FILTER (WHERE o.type_of_zayavka = 'technician') AS technician_count,
                COUNT(*) FILTER (WHERE o.type_of_zayavka = 'connection') AS connection_count
            FROM saff_orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.is_active = TRUE
            GROUP BY u.id, u.full_name
            ORDER BY (COUNT(*)) DESC
            """
        )
        return [
            {
                "full_name": r["full_name"],
                "technician_count": r["technician_count"],
                "connection_count": r["connection_count"],
            }
            for r in rows
        ]
    finally:
        await conn.close()
