# database/controller_staff_activity.py
import asyncpg
from typing import List, Dict, Any, Optional
from config import settings

async def get_user_language_by_telegram_id(telegram_id: int) -> str:
    """
    users.language ni olib 'uz'/'ru' qaytaradi (default 'uz')
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT language
              FROM users
             WHERE telegram_id = $1
            """,
            telegram_id,
        )
        lang = (row["language"] if row else None) or "uz"
        lang = str(lang).strip().lower()
        return "ru" if lang in {"ru", "rus", "russian", "ru-ru", "ru_ru"} else "uz"
    finally:
        await conn.close()


async def fetch_staff_activity() -> List[Dict[str, Any]]:
    """
    Controller uchun xodimlar faoliyati:
    — xodim sifatida TEXNIKLAR olinadi (users.role='technician')
    — conn_count: connection_orders dagi hozirda 'between_controller_technician' bo‘lgan,
                  oxirgi connections.recipient_id = texnik
    — tech_count: technician_orders dagi hozirda 'between_controller_technician' bo‘lgan,
                  oxirgi connections.recipient_id = texnik
    — active_count = conn_count + tech_count
    """
    sql = r"""
    WITH
    -- connection_orders bo‘yicha oxirgi yozuv
    last_conn AS (
        SELECT
            c.connecion_id,
            c.recipient_id,
            c.recipient_status,
            c.created_at,
            c.id,
            ROW_NUMBER() OVER (
                PARTITION BY c.connecion_id
                ORDER BY c.created_at DESC, c.id DESC
            ) AS rn
        FROM connections c
        WHERE c.connecion_id IS NOT NULL
    ),
    conn_agg AS (
        SELECT
            lc.recipient_id AS tech_id,
            COUNT(*) AS conn_count
        FROM last_conn lc
        JOIN connection_orders co ON co.id = lc.connecion_id
        WHERE lc.rn = 1
          AND lc.recipient_status = 'between_controller_technician'
          AND co.is_active = TRUE
          AND co.status = 'between_controller_technician'
        GROUP BY lc.recipient_id
    ),

    -- technician_orders bo‘yicha oxirgi yozuv
    last_tech AS (
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
    tech_agg AS (
        SELECT
            lt.recipient_id AS tech_id,
            COUNT(*) AS tech_count
        FROM last_tech lt
        JOIN technician_orders t2 ON t2.id = lt.technician_id
        WHERE lt.rn = 1
          AND lt.recipient_status = 'between_controller_technician'
          AND t2.is_active = TRUE
          AND t2.status = 'between_controller_technician'
        GROUP BY lt.recipient_id
    )

    SELECT
        u.id,
        u.full_name,
        u.username,
        u.phone,
        u.telegram_id,
        COALESCE(ca.conn_count, 0) AS conn_count,
        COALESCE(ta.tech_count, 0) AS tech_count,
        COALESCE(ca.conn_count, 0) + COALESCE(ta.tech_count, 0) AS active_count,
        COALESCE(ca.conn_count, 0) + COALESCE(ta.tech_count, 0) AS total_count
    FROM users u
    LEFT JOIN conn_agg ca ON ca.tech_id = u.id
    LEFT JOIN tech_agg ta ON ta.tech_id = u.id
    WHERE u.role = 'technician'
      AND COALESCE(u.is_blocked, FALSE) = FALSE
    ORDER BY total_count DESC, u.full_name NULLS LAST, u.id
    ;
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(sql)
        return [dict(r) for r in rows]
    finally:
        await conn.close()
