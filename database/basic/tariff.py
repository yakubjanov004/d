# database/basic/tariff.py
# Umumiy tariff bilan bog'liq funksiyalar

import asyncpg
import re
from typing import Optional, Dict, Any
from config import settings

def _code_to_name(tariff_code: Optional[str]) -> Optional[str]:
    """Tarif kodini nomga aylantirish."""
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
    Jadvalda 'code' yo'q. Shuning uchun 'name' bo'yicha izlaymiz/yaratamiz.
    """
    if not tariff_code:
        return None

    name = _code_to_name(tariff_code)
    if not name:
        # fallback: kodni sarlavhaga aylantiramiz
        base = re.sub(r"^tariff_", "", tariff_code)  # tariff_xxx -> xxx
        name = re.sub(r"_+", " ", base).title()

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT id FROM public.tarif WHERE name = $1 LIMIT 1",
                name,
            )
            if row:
                return row["id"]
            row = await conn.fetchrow(
                """
                INSERT INTO public.tarif (name, created_at, updated_at)
                VALUES ($1, NOW(), NOW())
                RETURNING id
                """,
                name,
            )
            return row["id"]
    finally:
        await conn.close()

async def get_tariff_by_id(tariff_id: int) -> Optional[Dict[str, Any]]:
    """Tarif ma'lumotlarini ID bo'yicha olish."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            "SELECT * FROM tarif WHERE id = $1",
            tariff_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def get_all_tariffs() -> list[Dict[str, Any]]:
    """Barcha tariflarni olish."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch("SELECT * FROM tarif ORDER BY name")
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def search_tariffs_by_name(name_pattern: str) -> list[Dict[str, Any]]:
    """Tarif nomi bo'yicha qidirish."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            "SELECT * FROM tarif WHERE name ILIKE $1 ORDER BY name",
            f"%{name_pattern}%"
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()
