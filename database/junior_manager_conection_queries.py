import asyncpg
from config import settings  # settings.DB_URL
import re
from typing import List, Dict, Any, Optional
import os

# Faqat supervisor inbox sharti bo'yicha nechta aktiv ariza borligini olamiz
async def ccs_count_active() -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow("""
            SELECT COUNT(*) AS c
            FROM saff_orders
            WHERE status = 'junior_manager'
              AND is_active = TRUE
        """)
        return int(row["c"])
    finally:
        await conn.close()

# OFFSET bo'yicha bitta arizani olib kelamiz (karta ko'rinishida ko'rsatamiz)
async def ccs_fetch_by_offset(offset: int) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow("""
            SELECT id, user_id, phone, abonent_id, region, address, tarif_id,
                   description, created_at
            FROM saff_orders
            WHERE status = 'junior_manager'
              AND is_active = TRUE
            ORDER BY created_at ASC
            OFFSET $1 LIMIT 1
        """, offset)
        return dict(row) if row else None
    finally:
        await conn.close()

# Controlga jo'natish: status -> in_control
async def ccs_send_to_control(order_id: int, supervisor_id: Optional[int] = None) -> None:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute("""
            UPDATE saff_orders
               SET status = 'in_controller',
                   updated_at = NOW()
             WHERE id = $1
        """, order_id)
        # TODO (ixtiyoriy): audit_log ga yozish, supervisor_id ni ham log qilish
    finally:
        await conn.close()

# Bekor qilish: is_active -> false
async def ccs_cancel(order_id: int) -> None:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute("""
            UPDATE saff_orders
               SET is_active = FALSE,
                   updated_at = NOW()
             WHERE id = $1
        """, order_id)
    finally:
        await conn.close()


_PHONE_RE = re.compile(r"^\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}$|^\+?998\d{9}$|^\d{9,12}$")

def _normalize_phone(raw: str) -> Optional[str]:
    raw = (raw or "").strip()
    if not _PHONE_RE.match(raw):
        return None
    digits = re.sub(r"[^\d]", "", raw)
    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 9:
        return "+998" + digits
    return raw if raw.startswith("+") else ("+" + digits if digits else None)

async def find_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    phone_n = _normalize_phone(phone)
    if not phone_n:
        return None
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT id, telegram_id, full_name, username, phone, language, region, address,
                   abonent_id, is_blocked
            FROM users
            WHERE regexp_replace(phone, '[^0-9]', '', 'g')
                  = regexp_replace($1,   '[^0-9]', '', 'g')
            LIMIT 1
            """,
            phone_n,
        )
        return dict(row) if row else None
    finally:
        await conn.close()

def _code_to_name(tariff_code: Optional[str]) -> Optional[str]:
    if not tariff_code:
        return None
    mapping = {
        "tariff_xammasi_birga_4": "Hammasi birga 4",
        "tariff_xammasi_birga_3_plus": "Hammasi birga 3+",
        "tariff_xammasi_birga_3": "Hammasi birga 3",
        "tariff_xammasi_birga_2": "Hammasi birga 2",
    }
    return mapping.get(tariff_code)

async def get_or_create_tarif_by_code(tariff_code: Optional[str]) -> Optional[int]:
    """
    PATCH: jadvalda 'code' yo‘q. Shu sabab 'name' bo‘yicha ishlaymiz.
    """
    if not tariff_code:
        return None

    name = _code_to_name(tariff_code)
    if not name:
        # Agar mappingda bo‘lmasa, kodni sarlavhaga aylantiramiz
        # tariff_xammasi_birga_3_plus -> "Xammasi Birga 3 Plus"
        base = re.sub(r"^tariff_", "", tariff_code)
        name = re.sub(r"_+", " ", base).title()

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow("SELECT id FROM public.tarif WHERE name = $1 LIMIT 1", name)
        if row:
            return row["id"]

        row = await conn.fetchrow(
            "INSERT INTO public.tarif (name) VALUES ($1) RETURNING id",
            name
        )
        return row["id"]
    finally:
        await conn.close()

async def saff_orders_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    tarif_id: Optional[int]
) -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO saff_orders (
                user_id, phone, abonent_id, region, address, tarif_id,
                description, type_of_zayavka, status, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6, '', 'connection', 'in_controller', TRUE)
            RETURNING id
            """,
            user_id, phone, abonent_id, region, address, tarif_id
        )
        return row["id"]
    finally:
        await conn.close()


# database/call_technician_queries.py


# --- Minimal connection helper (no pool) ---
# Uses DATABASE_URL if set, else falls back to local default.
_DSN = os.getenv(
    "DATABASE_URL",
    # CHANGE THIS IF NEEDED:
    "postgresql://postgres:postgres@localhost:5432/alfa_db"
)

async def _conn() -> asyncpg.Connection:
    """
    Open a single asyncpg connection. Caller is responsible for closing it.
    We keep this minimal to avoid importing unknown project-specific helpers.
    """
    return await asyncpg.connect(_DSN)

# --- Public API ---


async def _conn() -> asyncpg.Connection:
    # Endi fallback DSN YO'Q. Faqat settings.DB_URL ishlatiladi.
    return await asyncpg.connect(settings.DB_URL)



  # adjust import if needed

async def saff_orders_technician_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    description: Optional[str],
) -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO saff_orders (
                user_id, phone, region, abonent_id,
                address, description, status, type_of_zayavka, is_active
            )
            VALUES ($1, $2, $3, $4,
                    $5, $6, 'in_controller', 'technician', TRUE)
            RETURNING id
            """,
            user_id,
            phone,
            # note: region first, then abonent_id (order doesn't matter as long as names match)
            region,
            abonent_id,
            address,
            (description or ""),
        )
        return row["id"]
    finally:
        await conn.close()
