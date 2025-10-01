# database/call_center_supervisor_queries.py

import asyncpg
import re
from typing import List, Dict, Any, Optional
from config import settings

# =========================================================
#  Konfiguratsiya / konstantalar
# =========================================================

# ENUM connection_order_status tarkibida 'manager' yo‘q,
# shu sabab "supervisor inbox" sifatida 'in_controller'dan foydalanamiz.
STATUS_SUPERVISOR_INBOX = "in_controller"
STATUS_IN_CONTROLLER    = "in_controller"

# Yangi arizalar ham darhol controller/inboxda ko‘rinishi uchun:
DEFAULT_STATUS_ON_CREATE = STATUS_SUPERVISOR_INBOX  # 'in_controller'

# Telefon normalizatsiyasi (rag‘batlantirilgan format: +99890xxxxxxx)
_PHONE_RE = re.compile(
    r"^\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}$|^\+?998\d{9}$|^\d{9,12}$"
)

async def _conn() -> asyncpg.Connection:
    """Bitta asyncpg connection qaytaradi."""
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
#  Supervisor Inbox (saff_orders)
# =========================================================

async def ccs_count_active(status: str = STATUS_SUPERVISOR_INBOX) -> int:
    """
    UZ: Supervisor inbox uchun aktiv arizalar soni (saff_orders).
    RU: Кол-во активных заявок в inbox (saff_orders) для статуса.
    """
    conn = await _conn()
    try:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM saff_orders
             WHERE status = $1
               AND is_active = TRUE
            """,
            status,
        )
    finally:
        await conn.close()

async def ccs_fetch_by_offset(offset: int, status: str = STATUS_SUPERVISOR_INBOX) -> Optional[Dict[str, Any]]:
    """
    UZ: Supervisor inbox'dan OFFSET bo‘yicha bitta arizani olib keladi.
    RU: Возвращает одну заявку по OFFSET для заданного статуса.
    """
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, phone, abonent_id, region, address, tarif_id,
                   description, status, type_of_zayavka, is_active,
                   created_at, updated_at
              FROM saff_orders
             WHERE status = $1
               AND is_active = TRUE
             ORDER BY created_at ASC, id ASC
             OFFSET $2 LIMIT 1
            """,
            status, offset,
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def ccs_send_to_control(order_id: int, supervisor_id: Optional[int] = None) -> bool:
    """
    UZ: Controllga jo‘natish: status -> 'in_controller'.
        Idempotent: status allaqachon 'in_controller' bo‘lsa ham True qaytaradi.
    RU: Перевод в контроль (idempotent): если уже 'in_controller', вернёт True.
    """
    conn = await _conn()
    try:
        async with conn.transaction():
            # Avval o'zgartirishga urinib ko'ramiz (agar boshqa status bo'lsa)
            updated = await conn.execute(
                """
                UPDATE saff_orders
                   SET status    = $2::saff_order_status,
                       updated_at = NOW()
                 WHERE id = $1
                   AND status <> $2::saff_order_status
                """,
                order_id, STATUS_IN_CONTROLLER,
            )
            if updated.startswith("UPDATE 1"):
                return True

            # O'zgarmagan bo'lsa: mavjudligini va statusni tekshiramiz
            exists = await conn.fetchval(
                "SELECT 1 FROM saff_orders WHERE id = $1 AND status = $2::saff_order_status",
                order_id, STATUS_IN_CONTROLLER
            )
            return bool(exists)
    finally:
        await conn.close()

async def ccs_cancel(order_id: int) -> bool:
    """
    UZ: Bekor qilish: is_active -> FALSE
    RU: Отмена: is_active -> FALSE
    """
    conn = await _conn()
    try:
        async with conn.transaction():
            updated = await conn.execute(
                """
                UPDATE saff_orders
                   SET is_active = FALSE,
                       updated_at = NOW()
                 WHERE id = $1
                """,
                order_id,
            )
            return updated.startswith("UPDATE 1")
    finally:
        await conn.close()

# =========================================================
#  Foydalanuvchini telefon bo‘yicha topish
# =========================================================

async def find_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    UZ: Telefon bo‘yicha users dagi yozuvni qidiradi (raqamlar bo‘yicha taqqoslash).
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
    RU: В таблице нет поля 'code' — ищем/создаём по 'name'.
    """
    if not tariff_code:
        return None

    name = _code_to_name(tariff_code)
    if not name:
        # fallback: kodni sarlavhaga aylantiramiz
        base = re.sub(r"^tariff_", "", tariff_code)  # tariff_xxx -> xxx
        name = re.sub(r"_+", " ", base).title()

    conn = await _conn()
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT id FROM public.tarif WHERE name = $1 LIMIT 1",
                name,
            )
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
#  Yaratish (connection / technician)
# =========================================================

async def saff_orders_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    tarif_id: Optional[int],
) -> int:
    """
    UZ: Call-center operatori TOMONIDAN ulanish arizasini yaratish.
        Default status: 'in_controller' (supervisor/controller inbox).
    RU: Создание заявки на подключение (оператором).
        Статус по умолчанию: 'in_controller'.
    """
    conn = await _conn()
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO saff_orders (
                    user_id, phone, abonent_id, region, address, tarif_id,
                    description, type_of_zayavka, status, is_active, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6,
                        '', 'connection', $7::saff_order_status, TRUE, NOW(), NOW())
                RETURNING id
                """,
                user_id, phone, abonent_id, region, address, tarif_id, DEFAULT_STATUS_ON_CREATE
            )
            return row["id"]
    finally:
        await conn.close()

async def saff_orders_technician_create(
    user_id: int,
    phone: Optional[str],
    abonent_id: Optional[str],
    region: int,
    address: str,
    description: Optional[str],
) -> int:
    """
    UZ: Call-center operatori TOMONIDAN texnik xizmat arizasini yaratish.
        Default status: 'in_controller' (supervisor/controller inbox).
    RU: Создание заявки на техобслуживание (оператором).
        Статус по умолчанию: 'in_controller'.
    """
    conn = await _conn()
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO saff_orders (
                    user_id, phone, region, abonent_id, address, description,
                    status, type_of_zayavka, is_active, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6,
                        $7::saff_order_status, 'technician', TRUE, NOW(), NOW())
                RETURNING id
                """,
                user_id,
                phone,
                region,
                abonent_id,
                address,
                (description or ""),
                DEFAULT_STATUS_ON_CREATE,   # 'in_controller'
            )
            return row["id"]
    finally:
        await conn.close()
