import asyncpg
from typing import Optional
from datetime import datetime
from config import settings

async def _conn():
    return await asyncpg.connect(settings.DB_URL)

async def save_rating(request_id: int, request_type: str, rating: int, comment: str = None) -> bool:
    """
    Reyting va izohni saqlash (3 ta tur uchun)
    """
    conn = await _conn()
    try:
        query = """
            INSERT INTO akt_ratings (request_id, request_type, rating, comment, created_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (request_id, request_type) DO UPDATE SET
                rating = EXCLUDED.rating,
                comment = EXCLUDED.comment,
                created_at = EXCLUDED.created_at
        """
        await conn.execute(query, request_id, request_type, rating, comment, datetime.now())
        return True
    except Exception as e:
        print(f"Error saving rating: {e}")
        return False
    finally:
        await conn.close()

async def get_rating(request_id: int, request_type: str) -> Optional[dict]:
    """
    Reyting ma'lumotlarini olish
    """
    conn = await _conn()
    try:
        query = """
            SELECT rating, comment, created_at
            FROM akt_ratings
            WHERE request_id = $1 AND request_type = $2
        """
        row = await conn.fetchrow(query, request_id, request_type)
        return dict(row) if row else None
    finally:
        await conn.close()

async def get_rating_stats(request_type: str = None) -> dict:
    """
    Reyting statistikalarini olish
    """
    conn = await _conn()
    try:
        if request_type:
            query = """
                SELECT 
                    AVG(rating) as avg_rating,
                    COUNT(*) as total_ratings,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as five_stars,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as four_stars,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as three_stars,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as two_stars,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as one_stars
                FROM akt_ratings
                WHERE request_type = $1
            """
            row = await conn.fetchrow(query, request_type)
        else:
            query = """
                SELECT 
                    AVG(rating) as avg_rating,
                    COUNT(*) as total_ratings,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as five_stars,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as four_stars,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as three_stars,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as two_stars,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as one_stars
                FROM akt_ratings
            """
            row = await conn.fetchrow(query)
        
        return dict(row) if row else {}
    finally:
        await conn.close()
