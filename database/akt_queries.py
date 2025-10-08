# database/akt_queries.py
"""
AKT hujjatlari bilan ishlash uchun database query funksiyalari
"""

import asyncpg
from typing import Dict, Any, List, Optional
from config import settings
from datetime import datetime

async def get_akt_data_by_request_id(request_id: int, request_type: str) -> Optional[Dict[str, Any]]:
    """
    AKT yaratish uchun kerakli ma'lumotlarni olish.
    Barcha ariza turlari uchun umumiy funksiya.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi ('connection', 'technician', 'staff')
        
    Returns:
        Dict: AKT uchun kerakli ma'lumotlar yoki None
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if request_type == 'connection':
            return await _get_connection_akt_data(conn, request_id)
        elif request_type == 'technician':
            return await _get_technician_akt_data(conn, request_id)
        elif request_type == 'staff':
            return await _get_staff_akt_data(conn, request_id)
        else:
            return None
    finally:
        await conn.close()

async def _get_connection_akt_data(conn, request_id: int) -> Optional[Dict[str, Any]]:
    """Connection order uchun AKT ma'lumotlari"""
    row = await conn.fetchrow(
        """
        SELECT 
            co.id,
            co.application_number,
            co.address,
            co.region,
            co.created_at,
            co.updated_at,
            
            -- Client ma'lumotlari
            u.full_name AS client_name,
            u.phone AS client_phone,
            u.telegram_id AS client_telegram_id,
            u.language AS client_lang,
            
            -- Tarif ma'lumotlari
            t.name AS tariff_name,
            
            -- Texnik ma'lumotlari (agar mavjud bo'lsa)
            tech.full_name AS technician_name
            
        FROM connection_orders co
        LEFT JOIN users u ON u.id = co.user_id
        LEFT JOIN tarif t ON t.id = co.tarif_id
        LEFT JOIN users tech ON tech.id = (
            SELECT c.recipient_id 
            FROM connections c 
            WHERE c.connection_id = co.id 
            AND c.recipient_id IN (
                SELECT id FROM users WHERE role = 'technician'
            )
            LIMIT 1
        )
        WHERE co.id = $1 AND co.is_active = TRUE
        """,
        request_id
    )
    return dict(row) if row else None

async def _get_technician_akt_data(conn, request_id: int) -> Optional[Dict[str, Any]]:
    """Technician order uchun AKT ma'lumotlari"""
    row = await conn.fetchrow(
        """
        SELECT 
            t.id,
            t.application_number,
            t.address,
            t.region,
            t.description,
            t.description_ish AS diagnostics,
            t.created_at,
            t.updated_at,
            
            -- Client ma'lumotlari
            u.full_name AS client_name,
            u.phone AS client_phone,
            u.telegram_id AS client_telegram_id,
            u.language AS client_lang,
            
            -- Texnik ma'lumotlari
            tech.full_name AS technician_name
            
        FROM technician_orders t
        LEFT JOIN users u ON u.id = t.user_id
        LEFT JOIN users tech ON tech.id = (
            SELECT c.recipient_id 
            FROM connections c 
            WHERE c.technician_id = t.id 
            AND c.recipient_id IN (
                SELECT id FROM users WHERE role = 'technician'
            )
            LIMIT 1
        )
        WHERE t.id = $1 AND t.is_active = TRUE
        """,
        request_id
    )
    return dict(row) if row else None

async def _get_staff_akt_data(conn, request_id: int) -> Optional[Dict[str, Any]]:
    """Staff order uchun AKT ma'lumotlari"""
    row = await conn.fetchrow(
        """
        SELECT 
            so.id,
            so.application_number,
            so.address,
            so.region,
            so.description,
            so.created_at,
            so.updated_at,
            
            -- Client ma'lumotlari
            u.full_name AS client_name,
            u.phone AS client_phone,
            u.telegram_id AS client_telegram_id,
            u.language AS client_lang,
            
            -- Tarif ma'lumotlari (agar connection turi bo'lsa)
            t.name AS tariff_name,
            
            -- Texnik ma'lumotlari
            tech.full_name AS technician_name
            
        FROM staff_orders so
        LEFT JOIN users u ON u.id = so.user_id
        LEFT JOIN tarif t ON t.id = so.tarif_id
        LEFT JOIN users tech ON tech.id = (
            SELECT c.recipient_id 
            FROM connections c 
            WHERE c.staff_id = so.id 
            AND c.recipient_id IN (
                SELECT id FROM users WHERE role = 'technician'
            )
            LIMIT 1
        )
        WHERE so.id = $1 AND so.is_active = TRUE
        """,
        request_id
    )
    return dict(row) if row else None

async def get_materials_for_akt(request_id: int, request_type: str) -> List[Dict[str, Any]]:
    """
    AKT uchun ishlatilgan materiallarni olish.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi
        
    Returns:
        List: Materiallar ro'yxati
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if request_type == 'connection':
            materials = await conn.fetch(
                """
                SELECT 
                    m.name AS material_name,
                    mr.quantity,
                    mr.price,
                    mr.total_price,
                    'шт' AS unit
                FROM material_requests mr
                JOIN materials m ON m.id = mr.material_id
                WHERE mr.connection_order_id = $1
                ORDER BY mr.created_at
                """,
                request_id
            )
        elif request_type == 'technician':
            materials = await conn.fetch(
                """
                SELECT 
                    m.name AS material_name,
                    mr.quantity,
                    mr.price,
                    mr.total_price,
                    'шт' AS unit
                FROM material_requests mr
                JOIN materials m ON m.id = mr.material_id
                WHERE mr.technician_order_id = $1
                ORDER BY mr.created_at
                """,
                request_id
            )
        elif request_type == 'staff':
            materials = await conn.fetch(
                """
                SELECT 
                    m.name AS material_name,
                    mr.quantity,
                    mr.price,
                    mr.total_price,
                    'шт' AS unit
                FROM material_requests mr
                JOIN materials m ON m.id = mr.material_id
                WHERE mr.staff_order_id = $1
                ORDER BY mr.created_at
                """,
                request_id
            )
        else:
            materials = []
            
        return [dict(m) for m in materials]
    finally:
        await conn.close()

async def get_rating_for_akt(request_id: int, request_type: str) -> Optional[Dict[str, Any]]:
    """
    AKT uchun client rating va komentini olish.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi
        
    Returns:
        Dict: Rating ma'lumotlari yoki None
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
    finally:
        await conn.close()

async def create_akt_document(request_id: int, request_type: str, akt_number: str, file_path: str, file_hash: str) -> bool:
    """
    AKT hujjatini database'ga saqlash.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi
        akt_number: AKT raqami
        file_path: Fayl yo'li
        file_hash: Fayl hash
        
    Returns:
        bool: Muvaffaqiyatli saqlangan bo'lsa True
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute(
            """
            INSERT INTO akt_documents (request_id, request_type, akt_number, file_path, file_hash, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (request_id, request_type) 
            DO UPDATE SET 
                akt_number = $3, 
                file_path = $4, 
                file_hash = $5, 
                updated_at = NOW()
            """,
            request_id, request_type, akt_number, file_path, file_hash
        )
        return True
    except Exception as e:
        print(f"Error creating AKT document: {e}")
        return False
    finally:
        await conn.close()

async def mark_akt_sent(request_id: int, request_type: str, sent_at: datetime) -> bool:
    """
    AKT yuborilganini belgilash.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi
        sent_at: Yuborilgan vaqt
        
    Returns:
        bool: Muvaffaqiyatli yangilangan bo'lsa True
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute(
            """
            UPDATE akt_documents 
            SET sent_to_client_at = $3, updated_at = NOW()
            WHERE request_id = $1 AND request_type = $2
            """,
            request_id, request_type, sent_at
        )
        return True
    except Exception as e:
        print(f"Error marking AKT as sent: {e}")
        return False
    finally:
        await conn.close()

async def check_akt_exists(request_id: int, request_type: str) -> bool:
    """
    AKT mavjudligini tekshirish.
    
    Args:
        request_id: Ariza IDsi
        request_type: Ariza turi
        
    Returns:
        bool: AKT mavjud bo'lsa True
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        result = await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM akt_documents 
                WHERE request_id = $1 AND request_type = $2
            )
            """,
            request_id, request_type
        )
        return bool(result)
    finally:
        await conn.close()
