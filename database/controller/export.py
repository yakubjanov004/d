# database/controller/export.py

from typing import List, Dict, Any
import asyncpg
import logging
from config import settings

logger = logging.getLogger(__name__)

# =========================================================
#  Controller Export Functions
# =========================================================

async def get_controller_orders_for_export() -> List[Dict[str, Any]]:
    """
    Controller orders ro'yxatini export uchun olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status,
                       c.created_at as assigned_at
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
            SELECT 
                so.id,
                so.application_number,
                so.user_id,
                so.phone,
                so.abonent_id,
                so.region,
                so.address,
                so.tarif_id,
                so.description,
                so.business_type,
                so.type_of_zayavka,
                so.status,
                so.is_active,
                so.created_at,
                so.updated_at,
                la.assigned_at,
                u.full_name as client_name,
                u.phone as client_phone,
                t.name as tariff,
                r.name as region_name,
                creator.full_name as staff_name,
                creator.phone as staff_phone,
                creator.role as staff_role,
                CASE 
                    WHEN so.status = 'in_controller' THEN 'Controller da'
                    WHEN so.status = 'between_controller_technician' THEN 'Technician ga yuborilgan'
                    WHEN so.status = 'in_technician' THEN 'Technician da'
                    WHEN so.status = 'completed' THEN 'Bajarilgan'
                    WHEN so.status = 'cancelled' THEN 'Bekor qilingan'
                    ELSE so.status
                END as status_text
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            LEFT JOIN regions r ON r.id = so.region
            LEFT JOIN users creator ON creator.id = so.user_id
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician')
              AND COALESCE(so.is_active, TRUE) = TRUE
            ORDER BY so.created_at DESC
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_controller_statistics_for_export() -> Dict[str, Any]:
    """
    Controller uchun statistika export.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # 1. Asosiy statistika
        stats = {}
        
        # 2. Umumiy arizalar statistikasi
        stats['general'] = await conn.fetchrow(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN so.status = 'in_controller' THEN 1 END) as in_controller,
                COUNT(CASE WHEN so.status = 'between_controller_technician' THEN 1 END) as between_controller_technician,
                COUNT(CASE WHEN so.status = 'in_technician' THEN 1 END) as in_technician,
                COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN so.status = 'cancelled' THEN 1 END) as cancelled,
                COUNT(DISTINCT so.user_id) as unique_clients,
                COUNT(DISTINCT so.tarif_id) as unique_tariffs_used
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician')
              AND COALESCE(so.is_active, TRUE) = TRUE
            """
        )
        
        # 3. Oylik ariza statistikasi (oxirgi 6 oy)
        stats['monthly'] = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
            SELECT 
                TO_CHAR(so.created_at, 'YYYY-MM') as month,
                COUNT(*) as total_orders,
                COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN so.status = 'in_controller' THEN 1 END) as new_orders
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician')
              AND COALESCE(so.is_active, TRUE) = TRUE
              AND so.created_at >= NOW() - INTERVAL '6 months'
            GROUP BY TO_CHAR(so.created_at, 'YYYY-MM')
            ORDER BY month DESC
            """
        )
        
        # 4. Technicianlar bo'yicha statistika
        stats['by_technician'] = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
            SELECT 
                u.full_name as technician_name,
                u.phone as technician_phone,
                COUNT(so.id) as total_orders,
                COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN so.status IN ('between_controller_technician', 'in_technician') THEN 1 END) as in_progress_orders,
                COUNT(DISTINCT so.user_id) as unique_clients
            FROM users u
            LEFT JOIN last_assign la ON la.recipient_id = u.id
            LEFT JOIN staff_orders so ON so.id = la.staff_id
            WHERE u.role = 'technician'
            GROUP BY u.id, u.full_name, u.phone
            ORDER BY total_orders DESC
            """
        )
        
        # 5. Tarif rejalari bo'yicha statistika
        stats['by_tariff'] = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
            SELECT 
                t.name as tariff_name,
                COUNT(so.id) as total_orders,
                COUNT(DISTINCT so.user_id) as unique_clients,
                TO_CHAR(AVG(EXTRACT(EPOCH FROM so.created_at)) * INTERVAL '1 second', 'YYYY-MM-DD') as avg_order_date
            FROM tarif t
            LEFT JOIN staff_orders so ON t.id = so.tarif_id
            LEFT JOIN last_assign la ON la.staff_id = so.id
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician')
              AND COALESCE(so.is_active, TRUE) = TRUE
            GROUP BY t.id, t.name
            ORDER BY total_orders DESC
            """
        )
        
        # 6. So'ngi 30 kun ichidagi faol technicianlar
        stats['recent_activity'] = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status,
                       c.created_at
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            )
            SELECT 
                u.full_name as technician_name,
                u.phone as technician_phone,
                COUNT(so.id) as recent_orders,
                MAX(so.created_at) as last_order_date
            FROM users u
            LEFT JOIN last_assign la ON la.recipient_id = u.id
            LEFT JOIN staff_orders so ON so.id = la.staff_id
            WHERE u.role = 'technician'
              AND so.created_at >= NOW() - INTERVAL '30 days'
              AND la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician')
            GROUP BY u.id, u.full_name, u.phone
            ORDER BY recent_orders DESC
            LIMIT 10
            """
        )
        
        return stats
    finally:
        await conn.close()

async def get_controller_employees_for_export() -> List[Dict[str, Any]]:
    """
    Controller uchun xodimlar ro'yxatini export uchun olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                u.id,
                u.full_name,
                u.phone,
                u.username,
                u.telegram_id,
                u.role,
                u.is_blocked,
                u.created_at,
                COUNT(so.id) as total_orders,
                COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as completed_orders
            FROM users u
            LEFT JOIN staff_orders so ON so.user_id = u.id AND COALESCE(so.is_active, TRUE) = TRUE
            WHERE u.role IN ('controller', 'technician')
            GROUP BY u.id, u.full_name, u.phone, u.username, u.telegram_id, u.role, u.is_blocked, u.created_at
            ORDER BY u.role, u.full_name
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()
