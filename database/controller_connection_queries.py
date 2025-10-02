# database/controller_queries.py

import asyncpg
import re
from typing import List, Dict, Any, Optional
from config import settings

# =========================================================
#  Konfiguratsiya / konstantalar
# =========================================================

STATUS_IN_CONTROLLER = "in_controller"      # controller inbox statusi
DEFAULT_STATUS_ON_CREATE = STATUS_IN_CONTROLLER

_PHONE_RE = re.compile(
    r"^\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}$|^\+?998\d{9}$|^\d{9,12}$"
)

async def _conn() -> asyncpg.Connection:
    return await asyncpg.connect(settings.DB_URL)

# =========================================================
#  Telefon util
# =========================================================

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

# =========================================================
#  Foydalanuvchini telefon bo‘yicha topish
# =========================================================

async def find_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    UZ: Telefon bo‘yicha users dagi yozuvni qidiradi (faqat raqamlar bo‘yicha).
    RU: Поиск пользователя по телефону (сравнение по цифрам).
    """
    phone_n = _normalize_phone(phone)
    if not phone_n:
        return None
    conn = await _conn()
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

# =========================================================
#  Tarif: kod -> nom, va get_or_create
# =========================================================

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
    UZ: Jadvalda 'code' yo‘q. Shuning uchun 'name' bo‘yicha izlaymiz/yaratamiz.
    RU: В таблице тарифов нет поля 'code' — ищем/создаём по 'name'.
    """
    if not tariff_code:
        return None

    name = _code_to_name(tariff_code)
    if not name:
        base = re.sub(r"^tariff_", "", tariff_code)  # tariff_xxx -> xxx
        name = re.sub(r"_+", " ", base).title()

    conn = await _conn()
    try:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT id FROM public.tarif WHERE name = $1 LIMIT 1", name)
            if row:
                return row["id"]
            row = await conn.fetchrow(
                "INSERT INTO public.tarif (name) VALUES ($1) RETURNING id",
                name,
            )
            return row["id"]
    finally:
        await conn.close()

# =========================================================
#  Controller → staff_orders yaratish (connection/technician)
# =========================================================

async def staff_orders_create_by_controller(
    *,
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    tarif_id: Optional[int] = None,
    description: Optional[str] = "",
    type_of_zayavka: str = "connection",             # 'connection' | 'technician'
    initial_status: str = DEFAULT_STATUS_ON_CREATE,  # 'in_controller'
    connection_type: Optional[str] = None,           # IGNORE
) -> int:
    if type_of_zayavka not in ("connection", "technician"):
        raise ValueError("type_of_zayavka must be 'connection' or 'technician'")

    # 🔒 connection uchun description majburan bo'sh
    desc_text = "" if type_of_zayavka == "connection" else (description or "")

    conn = await _conn()
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO staff_orders (
                    user_id, phone, abonent_id, region, address, tarif_id,
                    description, type_of_zayavka, status, is_active, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6,
                        $7, $8, $9, TRUE, NOW(), NOW())
                RETURNING id
                """,
                user_id,
                phone,
                abonent_id,
                region,
                address,
                tarif_id,
                desc_text,
                type_of_zayavka,
                initial_status,
            )
            return row["id"]
    finally:
        await conn.close()


async def staff_orders_technician_create_by_controller(
    *,
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    description: Optional[str] = "",
    initial_status: str = DEFAULT_STATUS_ON_CREATE,
) -> int:
    """
    UZ: Controller texnik xizmat arizasini (type_of_zayavka='technician') yaratadi.
    RU: Создание заявки на техобслуживание контроллером.
    """
    return await staff_orders_create_by_controller(
        user_id=user_id,
        phone=phone,
        abonent_id=abonent_id,
        region=region,
        address=address,
        tarif_id=None,
        description=description,
        type_of_zayavka="technician",
        initial_status=initial_status,
    )
