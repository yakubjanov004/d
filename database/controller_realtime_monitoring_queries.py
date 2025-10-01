# database/manager_realtime_monitoring_queries.py
from typing import List, Dict, Any
import asyncpg
from datetime import timedelta
from config import settings

# === OVERVIEW COUNTS (faqat connection_orders) ===
async def get_realtime_counts() -> Dict[str, int]:
    sql = """
    SELECT
      COUNT(*) FILTER (WHERE (status)::text <> 'completed' AND is_active = true) AS active_total,
      COUNT(*) FILTER (
         WHERE (status)::text <> 'completed'
           AND is_active = true
           AND now() - created_at > INTERVAL '1 day'
      ) AS urgent_total
    FROM technician_orders;
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(sql)
        return {
            "active_total": int(row["active_total"] or 0),
            "urgent_total": int(row["urgent_total"] or 0),
            "normal_total": max(int(row["active_total"] or 0) - int(row["urgent_total"] or 0), 0),
        }
    finally:
        await conn.close()

# === LISTS for cards (faqat technician_orders) ===
def _select_block() -> str:
    # user_id -> users.full_name AS creator_name; address to‘g‘ridan-to‘g‘ri technician_orders dan.
    return """
    SELECT
        co.id,
        co.created_at,
        (co.status)::text AS status_text,
        co.address,
        u.full_name AS creator_name
    FROM technician_orders co
    LEFT JOIN users u ON u.id = co.user_id
    WHERE co.is_active = true AND (co.status)::text <> 'completed'
    """

async def _list_detailed(limit: int, urgent_only: bool) -> List[Dict[str, Any]]:
    base = _select_block()
    order_dir = "ASC" if urgent_only else "DESC"
    where_urgent = " AND (now() - co.created_at > INTERVAL '1 day')" if urgent_only else ""
    sql = f"""
    {base}
    {where_urgent}
    ORDER BY co.created_at {order_dir}
    LIMIT $1;
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_active_detailed(limit: int = 50) -> List[Dict[str, Any]]:
    return await _list_detailed(limit=limit, urgent_only=False)

async def list_urgent_detailed(limit: int = 50) -> List[Dict[str, Any]]:
    return await _list_detailed(limit=limit, urgent_only=True)

# === WORKFLOW HISTORY (connections jadvalidan) ===
async def get_workflow_history(order_id: int) -> Dict[str, Any]:
    """
    connections jadvalidan berilgan order_id bo‘yicha barcha o'tishlar.
    sender_id/recipient_id -> users.full_name
    Bosqich davomiyligi: navbatdagi yozuvning created_at - joriy created_at.
    Oxirgisi tugamagan bo‘lsa end_time = NULL (UI: 'hali tugamagan').
    Eslatma: ayrim bazalarda ustun nomi 'connection_id' o‘rniga 'connecion_id' bo‘lishi mumkin.
    """
    # Avval normal nom bilan urinamiz:
    sql1 = """
    SELECT c.id,
           c.sender_id, su.full_name AS sender_name,
           c.recipient_id, ru.full_name AS recipient_name,
           c.sender_status::text AS sender_status,
           c.recipient_status::text AS recipient_status,
           c.created_at
    FROM connections c
    LEFT JOIN users su ON su.id = c.sender_id
    LEFT JOIN users ru ON ru.id = c.recipient_id
    WHERE c.technician_id = $1
    ORDER BY c.created_at ASC;
    """
    # Keyin alternativ nom bilan (agar yuqoridagi ustun mavjud bo‘lmasa)
    sql2 = """
    SELECT c.id,
           c.sender_id, su.full_name AS sender_name,
           c.recipient_id, ru.full_name AS recipient_name,
           c.sender_status::text AS sender_status,
           c.recipient_status::text AS recipient_status,
           c.created_at
    FROM connections c
    LEFT JOIN users su ON su.id = c.sender_id
    LEFT JOIN users ru ON ru.id = c.recipient_id
    WHERE c.connecion_id = $1
    ORDER BY c.created_at ASC;
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        try:
            rows = await conn.fetch(sql1, order_id)
        except asyncpg.UndefinedColumnError:
            rows = await conn.fetch(sql2, order_id)

        steps = []
        for i, r in enumerate(rows):
            start_at = r["created_at"]
            end_at = rows[i + 1]["created_at"] if i + 1 < len(rows) else None
            dur = (end_at - start_at) if end_at else None
            duration_str = _fmt_duration(dur) if dur else "—"
            steps.append({
                "idx": i + 1,
                "from_name": r["sender_name"] or (r["sender_status"] or "—"),
                "to_name": r["recipient_name"] or (r["recipient_status"] or "—"),
                "from_status": r["sender_status"],
                "to_status": r["recipient_status"],
                "start_at": start_at,
                "end_at": end_at,
                "duration_str": duration_str if end_at else "hali tugamagan",
            })
        return {"steps": steps}
    finally:
        await conn.close()

def _fmt_duration(delta) -> str:
    if not delta:
        return "—"
    secs = int(delta.total_seconds())
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if not parts: parts.append(f"{s}s")
    return " ".join(parts)
