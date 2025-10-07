# database/call_center_supervisor/orders.py
import asyncpg
from config import settings
import re
from typing import List, Dict, Any, Optional

# ---------- ORDER YARATISH VA YANGILASH ----------

async def staff_orders_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    tarif_id: Optional[int],
    business_type: str = "B2C"
) -> str:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Parametrlarni to'g'ri formatlash - region integer bo'lsa string'ga aylantirish
        region_str = str(region) if region is not None else None
        
        # Application number generatsiya qilish - connection arizalar uchun business_type ga qarab
        next_number = await conn.fetchval(
            "SELECT COALESCE(MAX(CAST(SUBSTRING(application_number FROM '\\d+$') AS INTEGER)), 0) + 1 FROM staff_orders WHERE application_number LIKE $1",
            f"STAFF-CONN-{business_type}-%"
        )
        application_number = f"STAFF-CONN-{business_type}-{next_number:04d}"
        
        row = await conn.fetchrow(
            """
            INSERT INTO staff_orders (
                application_number, user_id, phone, abonent_id, region, address, tarif_id,
                description, business_type, type_of_zayavka, status, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, '', $8, 'connection', 'in_controller', TRUE)
            RETURNING id, application_number
            """,
            application_number, user_id, phone, abonent_id, region_str, address, tarif_id, business_type
        )
        return row["application_number"]
    finally:
        await conn.close()

async def staff_orders_technician_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    description: Optional[str],
    media: Optional[str] = None,
    business_type: str = "B2C"
) -> str:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Application number generatsiya qilish - texnik arizalar uchun business_type ga qarab
        next_number = await conn.fetchval(
            "SELECT COALESCE(MAX(CAST(SUBSTRING(application_number FROM '\\d+$') AS INTEGER)), 0) + 1 FROM staff_orders WHERE application_number LIKE $1",
            f"STAFF-TECH-{business_type}-%"
        )
        application_number = f"STAFF-TECH-{business_type}-{next_number:04d}"
        
        row = await conn.fetchrow(
            """
            INSERT INTO staff_orders (
                application_number, user_id, phone, abonent_id, region, address,
                description, media, business_type, type_of_zayavka, status, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'technician', 'in_controller', TRUE)
            RETURNING id, application_number
            """,
            application_number, user_id, phone, abonent_id, region, address, description, media, business_type
        )
        return row["application_number"]
    finally:
        await conn.close()

# ---------- ORDER STATUS YANGILASH ----------

async def ccs_send_to_control(order_id: int, supervisor_id: Optional[int] = None) -> None:
    """Controlga jo'natish: status -> in_controller"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute("""
            UPDATE staff_orders
               SET status = 'in_controller',
                   updated_at = NOW()
             WHERE id = $1
        """, order_id)
        # TODO (ixtiyoriy): audit_log ga yozish, supervisor_id ni ham log qilish
    finally:
        await conn.close()

async def ccs_cancel(order_id: int) -> None:
    """Bekor qilish: is_active -> false"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute("""
            UPDATE staff_orders
               SET is_active = FALSE,
                   updated_at = NOW()
             WHERE id = $1
        """, order_id)
    finally:
        await conn.close()

# ---------- FOYDALANUVCHI QIDIRISH ----------

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

# ---------- TARIF BILAN ISHLASH ----------

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
    PATCH: jadvalda 'code' yo'q. Shu sabab 'name' bo'yicha ishlaymiz.
    """
    if not tariff_code:
        return None

    name = _code_to_name(tariff_code)
    if not name:
        # Agar mappingda bo'lmasa, kodni sarlavhaga aylantiramiz
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
