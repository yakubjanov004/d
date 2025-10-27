# database/call_center/orders.py
import re
import asyncpg
from typing import Optional, Dict, Any
from config import settings

# ---------- TELEFON NORMALIZATSIYA ----------

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
                   abonent_id
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
        # B2C Plans
        "tariff_b2c_plan_0": "Oddiy-20",
        "tariff_b2c_plan_1": "Oddiy-50",
        "tariff_b2c_plan_2": "Oddiy-100",
        "tariff_b2c_plan_3": "XIT-200",
        "tariff_b2c_plan_4": "VIP-500",
        "tariff_b2c_plan_5": "PREMIUM",
        # BizNET-Pro Plans
        "tariff_biznet_plan_0": "BizNET-Pro-1",
        "tariff_biznet_plan_1": "BizNET-Pro-2",
        "tariff_biznet_plan_2": "BizNET-Pro-3",
        "tariff_biznet_plan_3": "BizNET-Pro-4",
        "tariff_biznet_plan_4": "BizNET-Pro-5",
        "tariff_biznet_plan_5": "BizNET-Pro-6",
        "tariff_biznet_plan_6": "BizNET-Pro-7+",
        # Tijorat Plans
        "tariff_tijorat_plan_0": "Tijorat-1",
        "tariff_tijorat_plan_1": "Tijorat-2",
        "tariff_tijorat_plan_2": "Tijorat-3",
        "tariff_tijorat_plan_3": "Tijorat-4",
        "tariff_tijorat_plan_4": "Tijorat-5",
        "tariff_tijorat_plan_5": "Tijorat-100",
        "tariff_tijorat_plan_6": "Tijorat-300",
        "tariff_tijorat_plan_7": "Tijorat-500",
        "tariff_tijorat_plan_8": "Tijorat-1000",
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

# ---------- ORDER YARATISH ----------

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
        # Region ID ni region nomiga aylantirish (agar regions jadvali mavjud bo'lsa)
        region_name = f"Region_{region}"  # Default fallback
        
        try:
            region_name = await conn.fetchval(
                "SELECT name FROM regions WHERE id = $1",
                region
            )
            if not region_name:
                region_name = f"Region_{region}"  
        except Exception:
            # Agar regions jadvali mavjud bo'lmasa, fallback ishlatamiz
            region_name = f"Region_{region}"
        
        # Application number generatsiya qilish - business_type ga qarab
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
            application_number, user_id, phone, abonent_id, region_name, address, tarif_id, business_type
        )
        return row["application_number"]
    finally:
        await conn.close()
