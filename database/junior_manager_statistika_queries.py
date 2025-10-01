# database/junior_manager_stats_queries.py
from __future__ import annotations
from typing import Dict, Optional, Tuple
import asyncpg
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from config import settings

# ===================== UTIL: DB yordamchilar =====================
async def _detect_conn_fk_col(conn: asyncpg.Connection) -> str:
    """
    connections -> connection_orders FK ustuni nomini autodetect qiladi:
    'connection_id' yoki typo: 'connecion_id'.
    Topilmasa 'connecion_id' (typo) qaytariladi.
    """
    q = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='connections' AND column_name = ANY($1::text[])
    """
    rows = await conn.fetch(q, ['connection_id', 'connecion_id'])
    cols = [r['column_name'] for r in rows]
    return cols[0] if cols else 'connecion_id'

async def _resolve_app_user_id(conn: asyncpg.Connection, telegram_id: int) -> Optional[int]:
    """
    users jadvalida telegram ustunini autodetect: telegram_id | tg_id | chat_id
    """
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

# ===================== UTIL: vaqt oynalari =====================
def _today_utc_range(tz: ZoneInfo) -> tuple[datetime, datetime]:
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

def _since_utc_range(days: int) -> tuple[datetime, datetime]:
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(days=days)
    return start_utc, now_utc

# ===================== CORE: eski pipeline (connections + connection_orders) =====================
async def _window_counts_pipeline(
    conn: asyncpg.Connection,
    user_id: int,
    fk_col: str,
    start_utc: datetime,
    end_utc: datetime,
) -> Dict[str, int]:
    """
    JM qabul qilgan / controllerga yuborgan / yuborganlaridan completed bo‘lganlari
    eski pipeline bo‘yicha (connections + connection_orders).
    """
    sql = f"""
    WITH received AS (
        SELECT id
        FROM connections
        WHERE recipient_id = $1
          AND recipient_status = 'in_junior_manager'
          AND created_at >= $2 AND created_at < $3
    ),
    sent AS (
        SELECT DISTINCT {fk_col} AS order_id
        FROM connections
        WHERE sender_id = $1
          AND sender_status = 'in_junior_manager'
          AND recipient_status = 'in_controller'
          AND created_at >= $2 AND created_at < $3
    )
    SELECT
      (SELECT COUNT(*) FROM received)                         AS received_cnt,
      (SELECT COUNT(*) FROM sent)                             AS sent_cnt,
      (SELECT COUNT(*)
         FROM connection_orders co
         JOIN sent s ON s.order_id = co.id
        WHERE (co.status)::text = 'completed')                AS completed_cnt;
    """
    row = await conn.fetchrow(sql, user_id, start_utc, end_utc)
    return {
        "received": int(row["received_cnt"] or 0),
        "sent_to_controller": int(row["sent_cnt"] or 0),
        "completed_from_sent": int(row["completed_cnt"] or 0),
    }

# ===================== YANGI: saff_orders (JM o‘zi yaratgan arizalar) =====================
async def _window_counts_saff_orders(
    conn: asyncpg.Connection,
    user_id: int,
    start_utc: datetime,
    end_utc: datetime,
) -> Dict[str, int]:
    """
    JM tomonidan yaratilgan connection arizalar (saff_orders):
      - created_by_me:   created_at oynasida yaratilganlar
      - created_completed: status='completed' va updated_at oynasida
    Eslatma: type_of_zayavka = 'connection' bo‘yicha filtr.
    """
    q_created = """
        SELECT COUNT(*) AS c
        FROM saff_orders
        WHERE user_id = $1
          AND type_of_zayavka = 'connection'
          AND is_active = TRUE
          AND created_at >= $2 AND created_at < $3
    """
    row_created = await conn.fetchrow(q_created, user_id, start_utc, end_utc)
    created_cnt = int(row_created["c"] or 0)

    q_completed = """
        SELECT COUNT(*) AS c
        FROM saff_orders
        WHERE user_id = $1
          AND type_of_zayavka = 'connection'
          AND status = 'completed'
          AND updated_at >= $2 AND updated_at < $3
    """
    row_completed = await conn.fetchrow(q_completed, user_id, start_utc, end_utc)
    completed_cnt = int(row_completed["c"] or 0)

    # bu blok connections metrikalariga qo‘shilmaydi, alohida ko‘rsatiladi
    return {
        "created_by_me": created_cnt,
        "created_completed": completed_cnt,
    }

def _merge_windows(base: Dict[str, int], saff: Dict[str, int]) -> Dict[str, int]:
    """
    connections pipeline metrikalarini + saff_orders alohida metrikalarini bitta dictga birlashtiradi.
    """
    out = {
        "received": base.get("received", 0),
        "sent_to_controller": base.get("sent_to_controller", 0),
        "completed_from_sent": base.get("completed_from_sent", 0),
    }
    # alohida ko‘rsatish uchun:
    out["created_by_me"] = saff.get("created_by_me", 0)
    out["created_completed"] = saff.get("created_completed", 0)
    return out

# ===================== PUBLIC API =====================
async def get_jm_stats_for_telegram(
    telegram_id: int,
    tz: ZoneInfo,
) -> Optional[Dict[str, Dict[str, int]]]:
    """
    Birlashtirilgan statistika:
      - Eski pipeline (connections + connection_orders)
      - JM yaratgan arizalar (saff_orders, type_of_zayavka='connection') — ALOHIDA ko‘rsatiladi
    Qaytadi:
    {
      "today": {"received": X, "sent_to_controller": Y, "completed_from_sent": Z,
                "created_by_me": A, "created_completed": B},
      "7d":    {...}, "10d": {...}, "30d": {...}
    }
    """
    tz = tz or ZoneInfo("Asia/Tashkent")

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        user_id = await _resolve_app_user_id(conn, telegram_id)
        if user_id is None:
            return None

        fk_col = await _detect_conn_fk_col(conn)

        # vaqt oynalari (UTC)
        t_start, t_end = _today_utc_range(tz)
        d7 = _since_utc_range(7)
        d10 = _since_utc_range(10)
        d30 = _since_utc_range(30)

        # --- TODAY ---
        base_today = await _window_counts_pipeline(conn, user_id, fk_col, t_start, t_end)
        saff_today = await _window_counts_saff_orders(conn, user_id, t_start, t_end)
        today = _merge_windows(base_today, saff_today)

        # --- 7 DAYS ---
        base_7 = await _window_counts_pipeline(conn, user_id, fk_col, *d7)
        saff_7 = await _window_counts_saff_orders(conn, user_id, *d7)
        last7 = _merge_windows(base_7, saff_7)

        # --- 10 DAYS ---
        base_10 = await _window_counts_pipeline(conn, user_id, fk_col, *d10)
        saff_10 = await _window_counts_saff_orders(conn, user_id, *d10)
        last10 = _merge_windows(base_10, saff_10)

        # --- 30 DAYS ---
        base_30 = await _window_counts_pipeline(conn, user_id, fk_col, *d30)
        saff_30 = await _window_counts_saff_orders(conn, user_id, *d30)
        last30 = _merge_windows(base_30, saff_30)

        return {
            "today": today,
            "7d": last7,
            "10d": last10,
            "30d": last30,
        }
    finally:
        await conn.close()
