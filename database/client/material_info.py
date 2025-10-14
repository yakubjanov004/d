# database/client/material_info.py
import asyncpg
from typing import List, Dict, Any, Optional
from config import settings

async def _conn():
    """Database connection helper"""
    return await asyncpg.connect(settings.DB_URL)

async def get_user_orders_with_materials(telegram_id: int, offset: int = 0, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Client arizalarini material_issued ma'lumotlari bilan birga olish
    """
    conn = await _conn()
    try:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )
        if not user:
            return []
        
        user_id = user['id']
        
        # Union connection_orders va technician_orders with material info
        orders = await conn.fetch(
            """
            (
                SELECT 
                    co.id, 
                    'connection' as order_type,
                    co.region,
                    co.address,
                    co.status::text as status,
                    co.created_at,
                    co.updated_at,
                    co.tarif_id,
                    NULL as abonent_id,
                    NULL as description,
                    co.application_number,
                    NULL as media_file_id,
                    NULL as media_type,
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM material_issued mi 
                            WHERE mi.application_number = co.application_number 
                            AND mi.request_type = 'connection'
                        ) THEN true
                        ELSE false
                    END as has_materials_used,
                    (
                        SELECT COUNT(*) 
                        FROM material_issued mi 
                        WHERE mi.application_number = co.application_number 
                        AND mi.request_type = 'connection'
                    ) as materials_count,
                    (
                        SELECT SUM(mi.total_price) 
                        FROM material_issued mi 
                        WHERE mi.application_number = co.application_number 
                        AND mi.request_type = 'connection'
                    ) as materials_total_cost
                FROM connection_orders co 
                WHERE co.user_id = $1
            )
            UNION ALL
            (
                SELECT 
                    tech_orders.id,
                    'technician' as order_type,
                    tech_orders.region,
                    tech_orders.address,
                    tech_orders.status::text as status,
                    tech_orders.created_at,
                    tech_orders.updated_at,
                    NULL as tarif_id,
                    tech_orders.abonent_id,
                    tech_orders.description,
                    tech_orders.application_number,
                    -- Use media_files table for proper file type detection
                    CASE 
                        WHEN mf.file_path IS NOT NULL AND mf.file_path != '' THEN mf.file_path
                        WHEN tech_orders.media IS NOT NULL AND tech_orders.media != '' THEN tech_orders.media
                        ELSE NULL
                    END as media_file_id,
                    CASE 
                        WHEN mf.file_type IS NOT NULL AND mf.file_type != '' THEN mf.file_type
                        WHEN tech_orders.media IS NOT NULL AND tech_orders.media != '' THEN 'photo'
                        ELSE NULL
                    END as media_type,
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM material_issued mi 
                            WHERE mi.application_number = tech_orders.application_number 
                            AND mi.request_type = 'technician'
                        ) THEN true
                        ELSE false
                    END as has_materials_used,
                    (
                        SELECT COUNT(*) 
                        FROM material_issued mi 
                        WHERE mi.application_number = tech_orders.application_number 
                        AND mi.request_type = 'technician'
                    ) as materials_count,
                    (
                        SELECT SUM(mi.total_price) 
                        FROM material_issued mi 
                        WHERE mi.application_number = tech_orders.application_number 
                        AND mi.request_type = 'technician'
                    ) as materials_total_cost
                FROM technician_orders tech_orders 
                LEFT JOIN media_files mf ON mf.related_table = 'technician_orders' 
                                        AND mf.related_id = tech_orders.id 
                                        AND mf.is_active = TRUE
                WHERE tech_orders.user_id = $1
            )
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset
        )
        
        return [dict(order) for order in orders]
    finally:
        await conn.close()

async def get_materials_for_user_order(application_number: str, request_type: str) -> List[Dict[str, Any]]:
    """
    Muayyan client arizasi uchun ishlatilgan materiallarni olish
    """
    conn = await _conn()
    try:
        materials = await conn.fetch(
            """
            SELECT 
                mi.material_name,
                mi.quantity,
                mi.price,
                mi.total_price,
                mi.issued_at,
                u.full_name as technician_name
            FROM material_issued mi
            JOIN users u ON u.id = mi.issued_by
            WHERE mi.application_number = $1 
              AND mi.request_type = $2
            ORDER BY mi.issued_at
            """,
            application_number, request_type
        )
        return [dict(mat) for mat in materials]
    finally:
        await conn.close()
