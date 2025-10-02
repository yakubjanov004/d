# database/call_technician_queries.py
from config import settings  # settings.DB_URL
from typing import List, Dict, Any, Optional
import os
import asyncpg

__all__ = ["list_technicians_by_region",]

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


async def list_technicians_by_region(region_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Optional helper if you later want region-filtered list.
    Requires a mapping table 'technician_regions(technician_id, region_id)'.
    Adjust query if your schema differs.
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT u.id, u.full_name, u.phone
            FROM users u
            JOIN technician_regions tr ON tr.technician_id = u.id
            WHERE u.role = 'technician'
              AND COALESCE(u.is_blocked, false) = false
              AND tr.region_id = $1
            ORDER BY u.full_name NULLS LAST, u.id
            LIMIT $2
            """,
            region_id, limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

  # adjust import if needed

async def staff_orders_create(
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
            INSERT INTO staff_orders (
                user_id, phone, region, abonent_id,
                address, description, status, type_of_zayavka, is_active
            )
            VALUES ($1, $2, $3, $4,
                    $5, $6, 'in_call_center_supervisor', 'technician', TRUE)
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
