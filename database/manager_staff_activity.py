# database/manager_staff_activity_queries.py
# Xodimlar (manager/junior_manager) kesimida nechta connection / technician ariza
# ochganini bitta so'rovda chiqarib beradi.

from typing import List, Dict, Any
import asyncpg
from config import settings


async def fetch_staff_activity() -> List[Dict[str, Any]]:
    """
    UZ: users jadvalidan role IN ('manager','junior_manager') bo'lgan xodimlarni oladi
        va staff_ordersdagi arizalarini hisoblaydi: connection/technician/total/active.
    RU: Берет сотрудников с ролями ('manager','junior_manager') и считает заявки.

    Qaytadi: [
      {
        "user_id": 63,
        "full_name": "Ism Familya",
        "role": "manager" | "junior_manager",
        "conn_count": 7,
        "tech_count": 4,
        "total_count": 11,
        "active_count": 5
      }, ...
    ]
    """
    sql = """
    SELECT
        u.id                           AS user_id,
        COALESCE(NULLIF(u.full_name, ''), '—') AS full_name,
        u.role,
        COALESCE(SUM(CASE WHEN s.type_of_zayavka = 'connection' THEN 1 ELSE 0 END), 0) AS conn_count,
        COALESCE(SUM(CASE WHEN s.type_of_zayavka = 'technician' THEN 1 ELSE 0 END), 0) AS tech_count,
        COALESCE(COUNT(s.id), 0)                                                    AS total_count,
        COALESCE(SUM(CASE WHEN s.is_active = TRUE AND (s.status)::text <> 'completed' THEN 1 ELSE 0 END), 0)
            AS active_count
    FROM users u
    LEFT JOIN staff_orders s
           ON s.user_id = u.id
    WHERE u.role IN ('manager','junior_manager')
    GROUP BY u.id, u.full_name, u.role
    ORDER BY total_count DESC, conn_count DESC, tech_count DESC, u.full_name ASC;
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(sql)
        return [dict(r) for r in rows]
    finally:
        await conn.close()