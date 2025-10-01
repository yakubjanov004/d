# database/manager_realtime_monitoring_queries.py
from typing import List, Dict, Any, Optional
import asyncpg
from asyncpg.exceptions import UndefinedColumnError  # ✅ to'g'ri import
from config import settings

# === OVERVIEW COUNTS (faqat connection_orders) ===
async def get_realtime_counts() -> Dict[str, int]:
    """
    Faol va shoshilinch (24 soatdan oshgan) connection_orders sonlari.
    """
    sql = """
    SELECT
      COUNT(*) FILTER (
        WHERE status <> 'completed'::connection_order_status
          AND is_active = TRUE
      ) AS active_total,
      COUNT(*) FILTER (
         WHERE status <> 'completed'::connection_order_status
           AND is_active = TRUE
           AND now() - created_at > INTERVAL '1 day'
      ) AS urgent_total
    FROM connection_orders;
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(sql)
        active = int(row["active_total"] or 0)
        urgent = int(row["urgent_total"] or 0)
        return {
            "active_total": active,
            "urgent_total": urgent,
            "normal_total": max(active - urgent, 0),
        }
    finally:
        await conn.close()


# === LISTS for cards (faqat connection_orders) ===
def _select_block() -> str:
    # user_id -> users.full_name AS creator_name
    # (UI’da “Yaratgan” sifatida ko‘rsatiladi)
    return """
    SELECT
        co.id,
        co.created_at,
        co.status::text AS status_text,
        co.address,
        u.full_name AS creator_name
    FROM connection_orders co
    LEFT JOIN users u ON u.id = co.user_id
    WHERE co.is_active = TRUE
      AND co.status <> 'completed'::connection_order_status
    """

async def _list_detailed(limit: int, urgent_only: bool) -> List[Dict[str, Any]]:
    base = _select_block()
    # Shoshilinchlar: eng eski (ko‘proq kutgan) oldinda bo‘lishi uchun ASC
    order_dir = "ASC" if urgent_only else "DESC"
    where_urgent = " AND (now() - co.created_at > INTERVAL '1 day')" if urgent_only else ""
    sql = f"""
    {base}
    {where_urgent}
    ORDER BY co.created_at {order_dir}, co.id {order_dir}
    LIMIT $1;
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_active_detailed(limit: int = 50) -> List[Dict[str, Any]]:
    """Faol (completed emas, is_active=TRUE) arizalar."""
    return await _list_detailed(limit=limit, urgent_only=False)

async def list_urgent_detailed(limit: int = 50) -> List[Dict[str, Any]]:
    """Shoshilinch (24 soatdan oshgan) arizalar."""
    return await _list_detailed(limit=limit, urgent_only=True)


# === WORKFLOW HISTORY (connections jadvalidan) ===
def _fmt_duration(delta) -> str:
    """
    Tilga bog‘liq bo‘lmagan, neytral yozuv (1d 2h 3m).
    Handler umumiy vaqtni o‘zi UZ/RU ga moslab formatlaydi.
    """
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

async def get_workflow_history(order_id: int) -> Dict[str, Any]:
    """
    connections jadvalidan berilgan order_id bo‘yicha barcha o'tishlar.
    - sender_id/recipient_id -> users.full_name
    - Qadam davomiyligi: keyingi yozuv.created_at - joriy.created_at
    - Tugallanmagan bosqichda end_at = NULL, duration_str = "—" (handler UZ/RU matnini o‘zi qo‘yadi).
    Ustun nomi ba'zi bazalarda 'connection_id' o‘rniga 'connecion_id' bo‘lishi mumkin,
    shuning uchun ikki xil SELECT bilan urinamiz.
    """
    sql_connection_id = """
    SELECT c.id,
           c.sender_id, su.full_name AS sender_name,
           c.recipient_id, ru.full_name AS recipient_name,
           c.sender_status::text   AS sender_status,
           c.recipient_status::text AS recipient_status,
           c.created_at
      FROM connections c
      LEFT JOIN users su ON su.id = c.sender_id
      LEFT JOIN users ru ON ru.id = c.recipient_id
     WHERE c.connection_id = $1
     ORDER BY c.created_at ASC, c.id ASC;
    """
    sql_connecion_id = """
    SELECT c.id,
           c.sender_id, su.full_name AS sender_name,
           c.recipient_id, ru.full_name AS recipient_name,
           c.sender_status::text   AS sender_status,
           c.recipient_status::text AS recipient_status,
           c.created_at
      FROM connections c
      LEFT JOIN users su ON su.id = c.sender_id
      LEFT JOIN users ru ON ru.id = c.recipient_id
     WHERE c.connecion_id = $1
     ORDER BY c.created_at ASC, c.id ASC;
    """

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Avval normal nom bilan, bo‘lmasa alternativ nom bilan
        try:
            rows = await conn.fetch(sql_connection_id, order_id)
        except UndefinedColumnError:
            rows = await conn.fetch(sql_connecion_id, order_id)

        steps: List[Dict[str, Any]] = []
        for i, r in enumerate(rows):
            start_at = r["created_at"]
            end_at = rows[i + 1]["created_at"] if i + 1 < len(rows) else None
            duration_str = _fmt_duration(end_at - start_at) if end_at else "—"

            # FIO bo‘lmasa, status nomini ko‘rsatamiz (fallback)
            from_name = r["sender_name"] or (r["sender_status"] or "—")
            to_name   = r["recipient_name"] or (r["recipient_status"] or "—")

            steps.append({
                "idx": i + 1,
                "from_name": from_name,
                "to_name": to_name,
                "from_status": r["sender_status"],
                "to_status": r["recipient_status"],
                "start_at": start_at,
                "end_at": end_at,
                "duration_str": duration_str,  # tilga bog‘liq emas
            })

        return {"steps": steps}
    finally:
        await conn.close()
