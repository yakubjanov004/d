# database/basic/rating.py

import asyncpg
from typing import Optional, Dict, Any
from config import settings

async def save_rating(request_id: int, request_type: str, rating: int, comment: Optional[str] = None) -> bool:
    """
    Reyting va izohni saqlash.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi ('connection', 'technician', 'staff')
        rating: Reyting (1-5)
        comment: Izoh (ixtiyoriy)
        
    Returns:
        bool: Muvaffaqiyatli saqlangan bo'lsa True
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute(
            """
            INSERT INTO akt_ratings (request_id, request_type, rating, comment)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (request_id, request_type) 
            DO UPDATE SET rating = $3, comment = $4, created_at = NOW()
            """,
            request_id, request_type, rating, comment
        )
        return True
    except Exception as e:
        print(f"Error saving rating: {e}")
        return False
    finally:
        await conn.close()

async def get_rating_stats() -> Dict[str, Any]:
    """
    Reyting statistikalarini olish.
    
    Returns:
        Dict: Reyting statistikasi
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        stats = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_ratings,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating = 5 THEN 1 END) as "5_stars",
                COUNT(CASE WHEN rating = 4 THEN 1 END) as "4_stars",
                COUNT(CASE WHEN rating = 3 THEN 1 END) as "3_stars",
                COUNT(CASE WHEN rating = 2 THEN 1 END) as "2_stars",
                COUNT(CASE WHEN rating = 1 THEN 1 END) as "1_stars"
            FROM akt_ratings
            """
        )
        return dict(stats) if stats else {}
    except Exception as e:
        print(f"Error getting rating stats: {e}")
        return {}
    finally:
        await conn.close()

async def get_rating(request_id: int, request_type: str) -> Optional[Dict[str, Any]]:
    """
    Belgilangan ariza uchun reytingni olish.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi
        
    Returns:
        Dict: Reyting ma'lumotlari yoki None
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rating = await conn.fetchrow(
            """
            SELECT rating, comment, created_at
            FROM akt_ratings
            WHERE request_id = $1 AND request_type = $2
            """,
            request_id, request_type
        )
        return dict(rating) if rating else None
    except Exception as e:
        print(f"Error getting rating: {e}")
        return None
    finally:
        await conn.close()
