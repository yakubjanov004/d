# database/manager/export.py
# Manager roli uchun export queries

import asyncpg
from config import settings
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# =========================================================
#  Connection Orders Export
# =========================================================

async def get_manager_connection_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch all connection orders for manager export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            co.id, 
            co.id as order_number,
            u.full_name as client_name,
            u.phone as phone_number,
            u.abonent_id as client_abonent_id,
            co.region,
            co.address,
            co.longitude,
            co.latitude,
            t.name as plan_name,
            t.picture as plan_picture,
            co.created_at as connection_date,
            co.updated_at,
            co.status,
            co.rating,
            co.notes,
            co.jm_notes,
            co.controller_notes,
            ad.akt_number,
            ad.file_path as akt_file_path,
            ad.created_at as akt_created_at,
            ad.sent_to_client_at,
            ar.rating as akt_rating,
            ar.comment as akt_comment
        FROM connection_orders co
        LEFT JOIN users u ON co.user_id = u.id
        LEFT JOIN tarif t ON co.tarif_id = t.id
        LEFT JOIN akt_documents ad ON co.id = ad.request_id AND ad.request_type = 'connection'
        LEFT JOIN akt_ratings ar ON co.id = ar.request_id AND ar.request_type = 'connection'
        ORDER BY co.created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching connection orders for export: {e}")
        return []
    finally:
        await conn.close()

# =========================================================
#  Statistics Export
# =========================================================

async def get_manager_statistics_for_export() -> Dict[str, Any]:
    """Fetch detailed statistics for manager export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # 1. Asosiy statistika
        stats = {}
        
        # 2. Umumiy arizalar statistikasi
        stats['general'] = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'in_manager' THEN 1 ELSE 0 END) as new_orders,
                SUM(CASE WHEN status IN ('in_manager', 'in_junior_manager', 'in_controller', 'in_technician', 'in_diagnostics', 'in_repairs', 'in_warehouse', 'in_technician_work') THEN 1 ELSE 0 END) as in_progress_orders,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                COUNT(DISTINCT user_id) as unique_clients,
                COUNT(DISTINCT tarif_id) as unique_tariffs_used
            FROM connection_orders
        """)
        
        # 3. Oylik ariza statistikasi (oxirgi 6 oy)
        stats['monthly_trends'] = await conn.fetch("""
            SELECT 
                TO_CHAR(created_at, 'YYYY-MM') as month,
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN status = 'in_manager' THEN 1 ELSE 0 END) as new_orders
            FROM connection_orders
            WHERE created_at >= NOW() - INTERVAL '6 months'
            GROUP BY TO_CHAR(created_at, 'YYYY-MM')
            ORDER BY month DESC
        """)
        
        # 4. Menejerlar bo'yicha statistika
        stats['by_manager'] = await conn.fetch("""
            SELECT 
                u.full_name as manager_name,
                u.phone as manager_phone,
                COUNT(co.id) as total_orders,
                SUM(CASE WHEN co.status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN co.status IN ('in_manager', 'in_junior_manager', 'in_controller', 'in_technician', 'in_diagnostics', 'in_repairs', 'in_warehouse', 'in_technician_work') THEN 1 ELSE 0 END) as in_progress_orders,
                COUNT(DISTINCT co.user_id) as unique_clients
            FROM users u
            LEFT JOIN connection_orders co ON u.id = co.user_id
            WHERE u.role IN ('manager', 'junior_manager')
            GROUP BY u.id, u.full_name, u.phone
            ORDER BY total_orders DESC
        """)
        
        # 5. Tarif rejalari bo'yicha statistika
        stats['by_tariff'] = await conn.fetch("""
            SELECT 
                t.name as tariff_name,
                COUNT(co.id) as total_orders,
                COUNT(DISTINCT co.user_id) as unique_clients,
                TO_CHAR(AVG(EXTRACT(EPOCH FROM co.created_at)) * INTERVAL '1 second', 'YYYY-MM-DD') as avg_order_date
            FROM tarif t
            LEFT JOIN connection_orders co ON t.id = co.tarif_id
            GROUP BY t.id, t.name
            ORDER BY total_orders DESC
        """)
        
        # 6. So'ngi 30 kun ichidagi faol menejerlar
        stats['recent_activity'] = await conn.fetch("""
            SELECT 
                u.full_name as manager_name,
                COUNT(co.id) as recent_orders,
                MAX(co.updated_at) as last_activity
            FROM users u
            LEFT JOIN connection_orders co ON u.id = co.user_id 
                AND co.updated_at >= NOW() - INTERVAL '30 days'
            WHERE u.role IN ('manager', 'junior_manager')
            GROUP BY u.id, u.full_name
            ORDER BY recent_orders DESC
            LIMIT 10
        """)
        
        # 7. Handle empty results
        if not stats['general']:
            return {
                'summary': {
                    'total_orders': 0,
                    'new_orders': 0,
                    'in_progress_orders': 0,
                    'completed_orders': 0,
                    'unique_clients': 0,
                    'unique_tariffs_used': 0,
                    'completion_rate': 0,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'monthly_trends': [],
                'by_manager': [],
                'by_tariff': [],
                'recent_activity': []
            }
            
        # 8. Umumiy statistika
        result = {
            'summary': {
                'total_orders': stats['general']['total_orders'] or 0,
                'new_orders': stats['general']['new_orders'] or 0,
                'in_progress_orders': stats['general']['in_progress_orders'] or 0,
                'completed_orders': stats['general']['completed_orders'] or 0,
                'unique_clients': stats['general']['unique_clients'] or 0,
                'unique_tariffs_used': stats['general']['unique_tariffs_used'] or 0,
                'completion_rate': round((stats['general']['completed_orders'] or 0) / 
                                      (stats['general']['total_orders'] or 1) * 100, 2),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'monthly_trends': [dict(row) for row in stats['monthly_trends']],
            'by_manager': [dict(row) for row in stats['by_manager']],
            'by_tariff': [dict(row) for row in stats['by_tariff']],
            'recent_activity': [dict(row) for row in stats['recent_activity']]
        }
        
        return result
    except Exception as e:
        logger.error(f"Error fetching manager statistics for export: {e}")
        return {}
    finally:
        await conn.close()

# =========================================================
#  Employees Export
# =========================================================

async def get_manager_employees_for_export() -> List[Dict[str, Any]]:
    """Fetch employees list for manager export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            telegram_id,
            full_name,
            username,
            phone,
            role,
            is_blocked,
            created_at
        FROM users
        WHERE role IN ('manager', 'junior_manager')
        ORDER BY created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching employees for export: {e}")
        return []
    finally:
        await conn.close()

# =========================================================
#  Staff Orders Export
# =========================================================

async def get_manager_staff_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch staff orders for manager export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            so.id,
            so.user_id,
            so.phone,
            so.abonent_id,
            so.region,
            so.address,
            so.description,
            so.status,
            so.type_of_zayavka,
            so.is_active,
            so.created_at,
            so.updated_at,
            u.full_name as creator_name,
            u.phone as creator_phone,
            client.full_name as client_name,
            client.phone as client_phone
        FROM staff_orders so
        LEFT JOIN users u ON so.user_id = u.id
        LEFT JOIN users client ON client.id::text = so.abonent_id
        ORDER BY so.created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching staff orders for export: {e}")
        return []
    finally:
        await conn.close()

# =========================================================
#  Smart Service Orders Export
# =========================================================

async def get_manager_smart_service_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch smart service orders for manager export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            sso.id,
            sso.user_id,
            sso.category,
            sso.service_type,
            sso.address,
            sso.latitude,
            sso.longitude,
            sso.description,
            sso.is_active,
            sso.created_at,
            sso.updated_at,
            u.full_name as client_name,
            u.phone as client_phone,
            u.username
        FROM smart_service_orders sso
        LEFT JOIN users u ON sso.user_id = u.id
        ORDER BY sso.created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching smart service orders for export: {e}")
        return []
    finally:
        await conn.close()

# =========================================================
#  Technician Orders Export
# =========================================================

async def get_manager_technician_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch technician orders for manager export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            to.id,
            to.user_id,
            to.phone,
            to.abonent_id,
            to.region,
            to.address,
            to.description,
            to.status,
            to.is_active,
            to.created_at,
            to.updated_at,
            to.media,
            u.full_name as creator_name,
            u.phone as creator_phone,
            client.full_name as client_name,
            client.phone as client_phone
        FROM technician_orders to
        LEFT JOIN users u ON to.user_id = u.id
        LEFT JOIN users client ON client.id::text = to.abonent_id
        ORDER BY to.created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching technician orders for export: {e}")
        return []
    finally:
        await conn.close()
