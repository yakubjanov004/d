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
    Faqat texnik arizalar: technician_orders va staff_orders (type_of_zayavka = 'technician').
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Technician orders (mijozlar yaratgan texnik arizalar)
        tech_rows = await conn.fetch(
            """
            SELECT 
                t.id,
                t.application_number,
                t.region,
                t.address,
                t.description,
                'technician' as type_of_zayavka,
                t.status,
                t.created_at,
                u.full_name as client_name,
                u.phone as client_phone,
                NULL as tariff,
                t.region as region_name,
                'mijoz' as creator_type,
                a.akt_number,
                tech_user.full_name as technician_name,
                controller_user.full_name as controller_name
            FROM technician_orders t
            LEFT JOIN users u ON u.id = t.user_id
            LEFT JOIN akt_documents a ON a.request_id = t.id AND a.request_type = 'technician'
            LEFT JOIN connections c ON c.technician_id = t.id 
                AND c.sender_id IN (SELECT id FROM users WHERE role = 'controller')
                AND c.recipient_id IN (SELECT id FROM users WHERE role = 'technician')
            LEFT JOIN users tech_user ON tech_user.id = c.recipient_id AND tech_user.role = 'technician'
            LEFT JOIN users controller_user ON controller_user.id = c.sender_id AND controller_user.role = 'controller'
            WHERE COALESCE(t.is_active, TRUE) = TRUE
            ORDER BY t.created_at DESC
            """
        )
        
        # Staff orders (xodimlar yaratgan texnik xizmat arizalari)
        # Eski database bilan mos kelishi uchun cancellation_note maydonini ixtiyoriy qildik
        staff_rows = await conn.fetch(
            """
            SELECT 
                s.id,
                s.application_number,
                s.region,
                s.address,
                s.description,
                s.type_of_zayavka,
                s.status,
                s.created_at,
                u.full_name as client_name,
                u.phone as client_phone,
                NULL as tariff,
                s.region as region_name,
                'xodim' as creator_type,
                a.akt_number,
                tech_user.full_name as technician_name,
                controller_user.full_name as controller_name
            FROM staff_orders s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN akt_documents a ON a.request_id = s.id AND a.request_type = 'staff'
            LEFT JOIN connections c ON c.staff_id = s.id 
                AND c.sender_id IN (SELECT id FROM users WHERE role = 'controller')
                AND c.recipient_id IN (SELECT id FROM users WHERE role = 'technician')
            LEFT JOIN users tech_user ON tech_user.id = c.recipient_id AND tech_user.role = 'technician'
            LEFT JOIN users controller_user ON controller_user.id = c.sender_id AND controller_user.role = 'controller'
            WHERE COALESCE(s.is_active, TRUE) = TRUE
              AND s.type_of_zayavka = 'technician'
            ORDER BY s.created_at DESC
            """
        )
        
        # Birlashtirish
        all_orders = []
        for row in tech_rows:
            all_orders.append(dict(row))
        for row in staff_rows:
            all_orders.append(dict(row))
            
        # Created_at bo'yicha tartiblash
        all_orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        return all_orders
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
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician', 'in_technician_work')
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
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician', 'in_technician_work')
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
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician', 'in_technician_work')
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
        
        # Summary qo'shish
        total_requests = stats['general']['total_orders'] if stats['general'] else 0
        completed_requests = stats['general']['completed'] if stats['general'] else 0
        
        stats['summary'] = {
            'total_requests': total_requests,
            'new_requests': stats['general']['in_controller'] if stats['general'] else 0,
            'in_progress_requests': (stats['general']['between_controller_technician'] + stats['general']['in_technician']) if stats['general'] else 0,
            'completed_requests': completed_requests,
            'cancelled_requests': stats['general']['cancelled'] if stats['general'] else 0,
            'unique_clients': stats['general']['unique_clients'] if stats['general'] else 0,
            'unique_tariffs': stats['general']['unique_tariffs_used'] if stats['general'] else 0,
            'completion_rate': round((completed_requests / total_requests * 100), 2) if total_requests > 0 else 0
        }
        
        return stats
    finally:
        await conn.close()

async def get_controller_employees_for_export() -> List[Dict[str, Any]]:
    """
    Controller uchun xodimlar ro'yxatini export uchun olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # First get all controller and technician users
        users = await conn.fetch(
            """
            SELECT 
                u.id,
                u.full_name,
                u.phone,
                u.username,
                u.telegram_id,
                u.role,
                u.is_blocked,
                u.created_at
            FROM users u
            WHERE u.role IN ('controller', 'technician')
            ORDER BY u.role, u.full_name
            """
        )
        
        # Then get order counts for each user
        result = []
        for user in users:
            user_dict = dict(user)
            
            # Get order counts for this user
            order_stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders
                FROM staff_orders 
                WHERE user_id = $1 AND COALESCE(is_active, TRUE) = TRUE
                """,
                user['id']
            )
            
            user_dict['total_orders'] = order_stats['total_orders'] if order_stats else 0
            user_dict['completed_orders'] = order_stats['completed_orders'] if order_stats else 0
            
            result.append(user_dict)
        
        return result
    finally:
        await conn.close()
