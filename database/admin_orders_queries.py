import asyncpg
from typing import List, Dict, Optional
import asyncio
from config import settings

async def get_connection_orders(limit: int = 50, offset: int = 0) -> List[Dict]:
    """
    Ulanish zayavkalarini olish
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            co.id,
            co.region,
            co.address,
            co.longitude,
            co.latitude,
            co.rating,
            co.notes,
            co.jm_notes,
            co.status,
            co.created_at,
            co.updated_at,
            u.full_name,
            u.phone,
            u.username,
            u.telegram_id,
            t.name as tarif_name
        FROM connection_orders co
        LEFT JOIN users u ON co.user_id = u.id
        LEFT JOIN tarif t ON co.tarif_id = t.id
        WHERE co.is_active = true
        ORDER BY co.created_at DESC
        LIMIT $1 OFFSET $2
        """
        
        rows = await conn.fetch(query, limit, offset)
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_technician_orders(limit: int = 50, offset: int = 0) -> List[Dict]:
    """
    Texnik zayavkalarini olish
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            to_.id,
            to_.region,
            to_.abonent_id,
            to_.address,
            to_.media,
            to_.longitude,
            to_.latitude,
            to_.description,
            to_.status,
            to_.rating,
            to_.notes,
            to_.created_at,
            to_.updated_at,
            u.full_name,
            u.phone,
            u.username,
            u.telegram_id
        FROM technician_orders to_
        LEFT JOIN users u ON to_.user_id = u.id
        WHERE to_.is_active = true
        ORDER BY to_.created_at DESC
        LIMIT $1 OFFSET $2
        """
        
        rows = await conn.fetch(query, limit, offset)
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_staff_orders(limit: int = 50, offset: int = 0) -> List[Dict]:
    """
    Xodim zayavkalarini olish
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            so.id,
            so.phone,
            so.region,
            so.abonent_id,
            so.address,
            so.description,
            so.status,
            so.type_of_zayavka,
            so.created_at,
            so.updated_at,
            u.full_name,
            u.username,
            u.telegram_id,
            t.name as tarif_name
        FROM staff_orders so
        LEFT JOIN users u ON so.user_id = u.id
        LEFT JOIN tarif t ON so.tarif_id = t.id
        WHERE so.is_active = true
        ORDER BY so.created_at DESC
        LIMIT $1 OFFSET $2
        """
        
        rows = await conn.fetch(query, limit, offset)
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """
    Telegram ID orqali foydalanuvchini olish
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT id, telegram_id, full_name, username, phone, role, is_blocked
        FROM users 
        WHERE telegram_id = $1
        """
        
        row = await conn.fetchrow(query, telegram_id)
        return dict(row) if row else None
    finally:
        await conn.close()