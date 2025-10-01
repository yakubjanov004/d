
import asyncpg
from typing import List, Dict, Any, Optional
from config import settings


async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Foydalanuvchini telegram_id orqali oladi.
    ⚠️ language ustuni ham olinadi (UZ/RU UI uchun zarur).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT
                id,
                telegram_id,
                full_name,
                username,
                phone,
                role,
                language     -- 🔑 TILNI HAM OLAMIZ
            FROM users
            WHERE telegram_id = $1
            LIMIT 1
            """,
            telegram_id,
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_user_language_by_telegram_id(telegram_id: int) -> Optional[str]:
    """
    Faqat til kerak bo'lsa, engil helper.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT language
            FROM users
            WHERE telegram_id = $1
            LIMIT 1
            """,
            telegram_id,
        )
        return row["language"] if row else None
    finally:
        await conn.close()


async def fetch_smart_service_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Smart service arizalarini (mijoz ma'lumotlari bilan) qaytaradi.
    Eng yangi yozuvlar birinchi (created_at DESC, id DESC).
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT
                sso.id,
                sso.user_id,
                sso.category,
                sso.service_type,
                sso.address,
                sso.latitude,
                sso.longitude,
                sso.created_at,
                u.full_name,
                u.phone,
                u.telegram_id,
                u.username
            FROM smart_service_orders sso
            LEFT JOIN users u ON u.id = sso.user_id
            ORDER BY sso.created_at DESC NULLS LAST, sso.id DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()
