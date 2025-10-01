import asyncpg
from typing import List, Dict, Any
from config import settings

SELECT_BASE = """
    SELECT
        co.id,
        co.address,
        co.region,
        co.status,
        co.created_at,
        co.updated_at,
        u.full_name AS client_name,
        u.phone      AS client_phone,
        t.name       AS tariff
    FROM connection_orders co
    LEFT JOIN users  u ON u.id = co.user_id
    LEFT JOIN tarif  t ON t.id = co.tarif_id
"""

# ---------- Helpers ----------
# Kun boshi/oxiri (Asia/Tashkent) ni bir marta hisoblab, UTCga qayta hisoblaymiz.
# Bu usul indeksga do‘st: co.created_at >= start_utc AND co.created_at < end_utc
BOUNDS_TZ_SQL = """
WITH bounds AS (
    SELECT
        date_trunc('day', (now() AT TIME ZONE 'Asia/Tashkent'))                   AS day_start_local,
        date_trunc('day', (now() AT TIME ZONE 'Asia/Tashkent')) + interval '1 day' AS day_end_local
),
utc_bounds AS (
    SELECT
        (day_start_local AT TIME ZONE 'Asia/Tashkent') AS day_start_utc,
        (day_end_local   AT TIME ZONE 'Asia/Tashkent') AS day_end_utc
    FROM bounds
)
"""

# ================== RO'YXATLAR ==================

async def list_new_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    UZ: 🆕 BUGUN YARATILGAN BUYURTMALAR (faol), Toshkent kuni bo‘yicha.
        is_active=TRUE va created_at bugungi [00:00, 24:00) oralig‘i (Asia/Tashkent).
    RU: 🆕 ЗАЯВКИ, СОЗДАННЫЕ СЕГОДНЯ (активные), по ташкентскому дню.

    Diqqat: agar “yangi” deganda status='new' ni nazarda tutsangiz,
            AND co.status = 'new' shartini qo‘shing.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            f"""
            {BOUNDS_TZ_SQL}
            , filtered AS (
                {SELECT_BASE}
                JOIN utc_bounds b ON TRUE
                WHERE co.is_active = TRUE
                  AND co.created_at >= b.day_start_utc
                  AND co.created_at <  b.day_end_utc
            )
            SELECT *
              FROM filtered
             ORDER BY created_at DESC, id DESC
             LIMIT $1 OFFSET $2;
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_in_progress_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    UZ: ⏳ JARAYONDAGILAR — is_active=TRUE va status <> 'completed'.
        (Agar “yangi” larni ham chiqarib yubormoqchi bo‘lsangiz: AND co.status <> 'new'.)
    RU: ⏳ В ПРОЦЕССЕ — активные и статус <> 'completed'.
        (Чтобы исключить «новые»: добавьте AND co.status <> 'new'.)
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            f"""
            WITH filtered AS (
                {SELECT_BASE}
                WHERE co.is_active = TRUE
                  AND co.status <> 'completed'::connection_order_status
                  -- AND co.status <> 'new'::connection_order_status   -- ixtiyoriy
            )
            SELECT *
              FROM filtered
             ORDER BY created_at DESC, id DESC
             LIMIT $1 OFFSET $2;
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_completed_today_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    UZ: ✅ BUGUN BAJARILGAN — status='completed' va updated_at bugungi [00:00, 24:00) (Asia/Tashkent).
    RU: ✅ ВЫПОЛНЕНО СЕГОДНЯ — status='completed' и updated_at в интервале дня (Ташкент).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            f"""
            {BOUNDS_TZ_SQL}
            , filtered AS (
                {SELECT_BASE}
                JOIN utc_bounds b ON TRUE
                WHERE co.status = 'completed'::connection_order_status
                  AND co.updated_at >= b.day_start_utc
                  AND co.updated_at <  b.day_end_utc
            )
            SELECT *
              FROM filtered
             ORDER BY updated_at DESC, id DESC
             LIMIT $1 OFFSET $2;
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_cancelled_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    UZ: 🚫 BEKOR QILINGAN — is_active=FALSE (updated_at bo‘yicha so‘nggilari yuqorida).
    RU: 🚫 ОТМЕНЁННЫЕ — is_active=FALSE (сортировка по updated_at).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            f"""
            WITH filtered AS (
                {SELECT_BASE}
                WHERE co.is_active = FALSE
            )
            SELECT *
              FROM filtered
             ORDER BY updated_at DESC NULLS LAST, id DESC
             LIMIT $1 OFFSET $2;
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# ================== STAT COUNT’LAR ==================

async def get_total_orders_count() -> int:
    """
    UZ: JAMI buyurtmalar soni (filtrsiz).
    RU: Общее количество заявок (без фильтров).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval("SELECT COUNT(*) FROM connection_orders;")
    finally:
        await conn.close()


async def get_new_orders_today_count() -> int:
    """
    UZ: BUGUN YARATILGAN (faol) buyurtmalar soni, Toshkent kuni bo‘yicha.
    RU: Кол-во созданных сегодня (активных), по ташкентскому дню.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            f"""
            {BOUNDS_TZ_SQL}
            SELECT COUNT(*)
              FROM connection_orders co
              JOIN utc_bounds b ON TRUE
             WHERE co.is_active = TRUE
               AND co.created_at >= b.day_start_utc
               AND co.created_at <  b.day_end_utc;
            """
        )
    finally:
        await conn.close()


async def get_in_progress_count() -> int:
    """
    UZ: JARAYONDA: is_active=TRUE va status <> 'completed'.
        (Xohlasangiz: AND status <> 'new' ham berishingiz mumkin.)
    RU: В ПРОЦЕССЕ: is_active=TRUE и status <> 'completed'.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM connection_orders
             WHERE is_active = TRUE
               AND status <> 'completed'::connection_order_status
               -- AND status <> 'new'::connection_order_status   -- ixtiyoriy
            """
        )
    finally:
        await conn.close()


async def get_completed_today_count() -> int:
    """
    UZ: BUGUN BAJARILGAN: status='completed' va updated_at bugungi (Toshkent) kun oralig‘ida.
    RU: ВЫПОЛНЕНО СЕГОДНЯ: status='completed' и updated_at в интервале дня (Ташкент).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            f"""
            {BOUNDS_TZ_SQL}
            SELECT COUNT(*)
              FROM connection_orders co
              JOIN utc_bounds b ON TRUE
             WHERE co.status = 'completed'::connection_order_status
               AND co.updated_at >= b.day_start_utc
               AND co.updated_at <  b.day_end_utc;
            """
        )
    finally:
        await conn.close()


async def get_cancelled_count() -> int:
    """
    UZ: BEKOR QILINGANLAR: is_active=FALSE.
    RU: ОТМЕНЁННЫЕ: is_active=FALSE.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE is_active = FALSE;"
        )
    finally:
        await conn.close()


async def list_my_created_orders(manager_user_id: int, limit: int = 50) -> List[Dict]:
    """
    Manager (user_id=manager_user_id) tomonidan saff_orders jadvalida yaratilgan connection arizalar.
    Tarif nomi jadvali mavjud bo'lsa autodetect qilib JOIN qilamiz, bo'lmasa tarif_id ko'rsatiladi.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # --- 1) Tarif jadval nomini autodetect ---
        row = await conn.fetchrow("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_type='BASE TABLE'
              AND table_name = ANY($1::text[])
            LIMIT 1
        """, ['tariffs', 'tarifs', 'operator_tariffs', 'tm_tariffs'])
        tariff_table = row['table_name'] if row else None

        select_tariff_sql = "COALESCE(s.tarif_id::text, '—') AS tariff"   # fallback agar jadval bo'lmasa
        join_tariff_sql = ""

        if tariff_table:
            # --- 2) Tarif jadvali ustunlarini autodetect (name/title, code/tariff_code) ---
            cols = await conn.fetch("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name=$1
            """, tariff_table)
            colset = {r['column_name'] for r in cols}

            name_col = 'name' if 'name' in colset else ('title' if 'title' in colset else None)
            code_col = 'code' if 'code' in colset else ('tariff_code' if 'tariff_code' in colset else None)

            label_parts = []
            if name_col: label_parts.append(f"t.{name_col}::text")
            if code_col: label_parts.append(f"t.{code_col}::text")
            label_parts.append("t.id::text")  # doimo bor bo'ladi

            label_expr = "COALESCE(" + ", ".join(label_parts) + ")"
            select_tariff_sql = f"{label_expr} AS tariff"

            # --- 3) saff_orders dagi FK nomi autodetect (tarif_id/tariff_id) ---
            fkrow = await conn.fetchrow("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='saff_orders'
                  AND column_name = ANY($1::text[])
                LIMIT 1
            """, ['tarif_id', 'tariff_id'])
            fkcol = fkrow['column_name'] if fkrow else None

            if fkcol:
                join_tariff_sql = f"LEFT JOIN {tariff_table} t ON t.id = s.{fkcol}"

        # --- 4) Yakuniy so'rov (mijoz ma'lumotlari abonent_id orqali) ---
        sql = f"""
            SELECT
                s.id,
                s.status,
                s.address,
                s.created_at,
                s.updated_at,
                u.full_name                                   AS client_name,
                COALESCE(u.phone, s.phone, '-')               AS client_phone,
                {select_tariff_sql}
            FROM saff_orders s
            LEFT JOIN users u ON (u.id::text = s.abonent_id)
            {join_tariff_sql}
            WHERE s.user_id = $1
              AND s.type_of_zayavka = 'connection'
              AND COALESCE(s.is_active, TRUE) = TRUE
            ORDER BY s.created_at DESC
            LIMIT $2
        """
        rows = await conn.fetch(sql, manager_user_id, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def list_my_created_orders_by_type(manager_user_id: int, type_of_zayavka: str, limit: int = 50) -> List[Dict]:
    """
    Manager (user_id=manager_user_id) tomonidan saff_orders jadvalida yaratilgan arizalar.
    type_of_zayavka: 'connection' | 'technician'
    Tarif nomi jadvali mavjud bo'lsa autodetect qilib JOIN qilamiz, bo'lmasa tarif_id ko'rsatiladi.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # 1) Tarif jadval nomini autodetect
        row = await conn.fetchrow("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_type='BASE TABLE'
              AND table_name = ANY($1::text[])
            LIMIT 1
        """, ['tariffs', 'tarifs', 'operator_tariffs', 'tm_tariffs'])
        tariff_table = row['table_name'] if row else None

        select_tariff_sql = "COALESCE(s.tarif_id::text, '—') AS tariff"
        join_tariff_sql = ""

        if tariff_table:
            # 2) Tarif jadvali ustunlarini autodetect
            cols = await conn.fetch("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name=$1
            """, tariff_table)
            colset = {r['column_name'] for r in cols}

            name_col = 'name' if 'name' in colset else ('title' if 'title' in colset else None)
            code_col = 'code' if 'code' in colset else ('tariff_code' if 'tariff_code' in colset else None)

            parts = []
            if name_col: parts.append(f"t.{name_col}::text")
            if code_col: parts.append(f"t.{code_col}::text")
            parts.append("t.id::text")
            label_expr = "COALESCE(" + ", ".join(parts) + ")"
            select_tariff_sql = f"{label_expr} AS tariff"

            # 3) saff_orders FK autodetect (tarif_id/tariff_id)
            fkrow = await conn.fetchrow("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='saff_orders'
                  AND column_name = ANY($1::text[])
                LIMIT 1
            """, ['tarif_id', 'tariff_id'])
            fkcol = fkrow['column_name'] if fkrow else None

            if fkcol:
                join_tariff_sql = f"LEFT JOIN {tariff_table} t ON t.id = s.{fkcol}"

        # 4) So'rov (mijoz ma’lumotlari abonent_id orqali, text cast bilan)
        sql = f"""
            SELECT
                s.id,
                s.status,
                s.address,
                s.created_at,
                s.updated_at,
                s.type_of_zayavka,
                u.full_name                                   AS client_name,
                COALESCE(u.phone, s.phone, '-')               AS client_phone,
                {select_tariff_sql}
            FROM saff_orders s
            LEFT JOIN users u ON (u.id::text = s.abonent_id)
            {join_tariff_sql}
            WHERE s.user_id = $1
              AND s.type_of_zayavka = $2
              AND COALESCE(s.is_active, TRUE) = TRUE
            ORDER BY s.created_at DESC
            LIMIT $3
        """
        rows = await conn.fetch(sql, manager_user_id, type_of_zayavka, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()