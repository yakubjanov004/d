import asyncpg
from config import settings
from typing import Optional, List, Dict, Any


async def get_all_users_paginated(page: int = 1, per_page: int = 5) -> Dict[str, Any]:
    """Barcha foydalanuvchilarni paginatsiya bilan olish.
    
    Args:
        page: Sahifa raqami (1 dan boshlanadi)
        per_page: Har sahifada ko'rsatiladigan foydalanuvchilar soni
        
    Returns:
        Dict: {
            'users': List[Dict] - foydalanuvchilar ro'yxati,
            'total': int - jami foydalanuvchilar soni,
            'page': int - joriy sahifa,
            'per_page': int - sahifadagi elementlar soni,
            'total_pages': int - jami sahifalar soni,
            'has_next': bool - keyingi sahifa mavjudligi,
            'has_prev': bool - oldingi sahifa mavjudligi
        }
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Jami foydalanuvchilar sonini olish
        total_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        
        # Sahifalar sonini hisoblash
        total_pages = (total_count + per_page - 1) // per_page
        
        # Offset hisoblash
        offset = (page - 1) * per_page
        
        # Foydalanuvchilarni olish
        users = await conn.fetch(
            """
            SELECT id, telegram_id, username, full_name, phone, role, 
                   created_at, updated_at, is_blocked
            FROM users 
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            per_page, offset
        )
        
        # Natijani dict formatiga o'tkazish
        users_list = [dict(user) for user in users]
        
        return {
            'users': users_list,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    finally:
        await conn.close()


async def get_users_by_role_paginated(role: str, page: int = 1, per_page: int = 5) -> Dict[str, Any]:
    """Rol bo'yicha foydalanuvchilarni paginatsiya bilan olish.
    
    Args:
        role: Foydalanuvchi roli
        page: Sahifa raqami (1 dan boshlanadi)
        per_page: Har sahifada ko'rsatiladigan foydalanuvchilar soni
        
    Returns:
        Dict: Paginatsiya ma'lumotlari bilan foydalanuvchilar
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Jami foydalanuvchilar sonini olish
        total_count = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE role = $1", role
        )
        
        # Sahifalar sonini hisoblash
        total_pages = (total_count + per_page - 1) // per_page
        
        # Offset hisoblash
        offset = (page - 1) * per_page
        
        # Foydalanuvchilarni olish
        users = await conn.fetch(
            """
            SELECT id, telegram_id, username, full_name, phone, role, 
                   created_at, updated_at, is_blocked
            FROM users 
            WHERE role = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            role, per_page, offset
        )
        
        # Natijani dict formatiga o'tkazish
        users_list = [dict(user) for user in users]
        
        return {
            'users': users_list,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'role': role
        }
    finally:
        await conn.close()


async def search_users_paginated(search_term: str, page: int = 1, per_page: int = 5) -> Dict[str, Any]:
    """Foydalanuvchilarni qidirish (ism, telefon, username bo'yicha) paginatsiya bilan.
    
    Args:
        search_term: Qidiruv so'zi
        page: Sahifa raqami (1 dan boshlanadi)
        per_page: Har sahifada ko'rsatiladigan foydalanuvchilar soni
        
    Returns:
        Dict: Paginatsiya ma'lumotlari bilan qidiruv natijalari
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        search_pattern = f"%{search_term}%"
        
        # Jami topilgan foydalanuvchilar sonini olish
        total_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM users 
            WHERE full_name ILIKE $1 OR username ILIKE $1 OR phone ILIKE $1
            """,
            search_pattern
        )
        
        # Sahifalar sonini hisoblash
        total_pages = (total_count + per_page - 1) // per_page
        
        # Offset hisoblash
        offset = (page - 1) * per_page
        
        # Foydalanuvchilarni qidirish
        users = await conn.fetch(
            """
            SELECT id, telegram_id, username, full_name, phone, role, 
                   created_at, updated_at, is_blocked
            FROM users 
            WHERE full_name ILIKE $1 OR username ILIKE $1 OR phone ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            search_pattern, per_page, offset
        )
        
        # Natijani dict formatiga o'tkazish
        users_list = [dict(user) for user in users]
        
        return {
            'users': users_list,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'search_term': search_term
        }
    finally:
        await conn.close()


async def get_user_statistics() -> Dict[str, Any]:
    """Foydalanuvchilar statistikasini olish.
    
    Returns:
        Dict: Har xil rol bo'yicha foydalanuvchilar soni
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Jami foydalanuvchilar soni
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        
        # Rol bo'yicha statistika
        role_stats = await conn.fetch(
            "SELECT role, COUNT(*) as count FROM users GROUP BY role ORDER BY count DESC"
        )
        
        # Bloklangan foydalanuvchilar soni
        blocked_users = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE is_blocked = true"
        )
        
        # Faol foydalanuvchilar soni
        active_users = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE is_blocked = false OR is_blocked IS NULL"
        )
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'blocked_users': blocked_users,
            'role_statistics': [dict(stat) for stat in role_stats]
        }
    finally:
        await conn.close()


async def toggle_user_block_status(telegram_id: int) -> bool:
    """Foydalanuvchini bloklash yoki blokdan chiqarish.
    
    Args:
        telegram_id: Telegram foydalanuvchi IDsi
        
    Returns:
        bool: Operatsiya muvaffaqiyatli bo'lsa True
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Hozirgi holatni olish
        current_status = await conn.fetchval(
            "SELECT is_blocked FROM users WHERE telegram_id = $1",
            telegram_id
        )
        
        if current_status is None:
            return False  # Foydalanuvchi topilmadi
        
        # Holatni o'zgartirish
        new_status = not (current_status or False)
        result = await conn.execute(
            "UPDATE users SET is_blocked = $1 WHERE telegram_id = $2",
            new_status, telegram_id
        )
        
        return result != 'UPDATE 0'
    finally:
        await conn.close()