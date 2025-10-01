import asyncpg
from config import settings
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

async def get_controller_tech_requests_for_export() -> List[Dict[str, Any]]:
    """Fetch all technical service requests for controller export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            to2.id,
            to2.id as request_number,
            COALESCE(u.full_name, 'Nomalum') as client_name,
            COALESCE(u.phone, '') as phone_number,
            COALESCE(u.abonent_id, '') as client_abonent_id,
            to2.region,
            to2.abonent_id,
            to2.address,
            COALESCE(to2.media, '') as media,
            to2.longitude,
            to2.latitude,
            COALESCE(to2.description, '') as description,
            COALESCE(to2.description_ish, '') as description_ish,
            to2.status,
            to2.rating,
            COALESCE(to2.notes, '') as notes,
            to2.created_at,
            to2.updated_at,
            COALESCE(u2.full_name, 'Mavjud emas') as assigned_technician,
            COALESCE(u2.phone, '') as technician_phone,
            COALESCE(u3.full_name, 'Mavjud emas') as controller_name,
            COALESCE(u3.phone, '') as controller_phone,
            COALESCE(ad.akt_number, '') as akt_number,
            COALESCE(ad.file_path, '') as akt_file_path,
            ad.created_at as akt_created_at,
            ad.sent_to_client_at,
            COALESCE(ar.rating, 0) as akt_rating,
            COALESCE(ar.comment, '') as akt_comment
        FROM technician_orders to2
        LEFT JOIN users u ON to2.user_id = u.id
        LEFT JOIN (
            SELECT DISTINCT ON (connecion_id) 
                connecion_id, 
                technician_id,
                recipient_id
            FROM connections 
            WHERE connecion_id IS NOT NULL
            ORDER BY connecion_id, created_at DESC
        ) c ON to2.id = c.connecion_id
        LEFT JOIN users u2 ON c.technician_id = u2.id
        LEFT JOIN users u3 ON c.recipient_id = u3.id
        LEFT JOIN akt_documents ad ON to2.id = ad.request_id AND ad.request_type = 'technician'
        LEFT JOIN akt_ratings ar ON to2.id = ar.request_id AND ar.request_type = 'technician'
        WHERE to2.is_active = TRUE
        ORDER BY 
            CASE 
                WHEN to2.status = 'between_controller_technician' THEN 1
                WHEN to2.status = 'in_technician' THEN 2
                WHEN to2.status = 'in_technician_work' THEN 3
                WHEN to2.status = 'completed' THEN 4
                ELSE 5
            END,
            to2.created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching tech requests for export: {e}")
        return []
    finally:
        await conn.close()

async def get_controller_material_requests_for_export() -> List[Dict[str, Any]]:
    """Fetch material requests for controller export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            mr.id,
            mr.description,
            u.full_name as requester_name,
            u.phone as requester_phone,
            mr.applications_id,
            m.name as material_name,
            m.description as material_description,
            m.serial_number,
            mr.quantity,
            mr.price,
            mr.total_price,
            mr.connection_order_id,
            mr.technician_order_id,
            mr.saff_order_id,
            co.address as connection_address,
            to2.address as technician_address,
            so.address as saff_address
        FROM material_requests mr
        LEFT JOIN users u ON mr.user_id = u.id
        LEFT JOIN materials m ON mr.material_id = m.id
        LEFT JOIN connection_orders co ON mr.connection_order_id = co.id
        LEFT JOIN technician_orders to2 ON mr.technician_order_id = to2.id
        LEFT JOIN saff_orders so ON mr.saff_order_id = so.id
        WHERE u.role IN ('controller', 'technician') OR mr.technician_order_id IS NOT NULL
        ORDER BY mr.id DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching material requests for export: {e}")
        return []
    finally:
        await conn.close()

async def get_controller_smart_service_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch smart service orders for controller export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            sso.id,
            u.full_name as client_name,
            u.phone as phone_number,
            u.abonent_id as client_abonent_id,
            sso.category,
            sso.service_type,
            sso.address,
            sso.longitude,
            sso.latitude,
            sso.is_active,
            sso.created_at,
            sso.updated_at
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

async def get_controller_statistics_for_export() -> Dict[str, Any]:
    """Fetch detailed statistics for controller export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        stats = {}
        
        # 1. Umumiy texnik xizmat statistikasi
        stats['general'] = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_requests,
                SUM(CASE WHEN status = 'in_controller' THEN 1 ELSE 0 END) as new_requests,
                SUM(CASE WHEN status IN ('in_controller', 'in_technician', 'in_diagnostics', 'in_repairs', 'in_warehouse') THEN 1 ELSE 0 END) as in_progress_requests,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_requests,
                COUNT(DISTINCT user_id) as unique_clients,
                COUNT(DISTINCT description_ish) as unique_problem_types
            FROM technician_orders
        """)
        
        # 2. Oylik texnik xizmat statistikasi (oxirgi 6 oy)
        stats['monthly_trends'] = await conn.fetch("""
            SELECT 
                TO_CHAR(created_at, 'YYYY-MM') as month,
                COUNT(*) as total_requests,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_requests,
                SUM(CASE WHEN status = 'in_controller' THEN 1 ELSE 0 END) as new_requests
            FROM technician_orders
            WHERE created_at >= NOW() - INTERVAL '6 months'
            GROUP BY TO_CHAR(created_at, 'YYYY-MM')
            ORDER BY month DESC
        """)
        
        # 3. Texniklar bo'yicha statistika
        stats['by_technician'] = await conn.fetch("""
            SELECT 
                u.full_name as technician_name,
                u.phone as technician_phone,
                COUNT(to2.id) as total_requests,
                SUM(CASE WHEN to2.status = 'completed' THEN 1 ELSE 0 END) as completed_requests,
                SUM(CASE WHEN to2.status IN ('in_technician', 'in_diagnostics', 'in_repairs') THEN 1 ELSE 0 END) as in_progress_requests,
                COUNT(DISTINCT to2.user_id) as unique_clients
            FROM users u
            LEFT JOIN technician_orders to2 ON u.id = to2.user_id
            WHERE u.role = 'technician'
            GROUP BY u.id, u.full_name, u.phone
            ORDER BY total_requests DESC
        """)
        
        # 4. Muammo turlari bo'yicha statistika
        stats['by_problem_type'] = await conn.fetch("""
            SELECT 
                description_ish as problem_type,
                COUNT(*) as total_requests,
                COUNT(DISTINCT user_id) as unique_clients,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_requests
            FROM technician_orders
            WHERE description_ish IS NOT NULL
            GROUP BY description_ish
            ORDER BY total_requests DESC
        """)
        
        # 5. So'ngi 30 kun ichidagi faol texniklar
        stats['recent_activity'] = await conn.fetch("""
            SELECT 
                u.full_name as technician_name,
                COUNT(to2.id) as recent_requests,
                MAX(to2.updated_at) as last_activity
            FROM users u
            LEFT JOIN technician_orders to2 ON u.id = to2.user_id 
                AND to2.updated_at >= NOW() - INTERVAL '30 days'
            WHERE u.role = 'technician'
            GROUP BY u.id, u.full_name
            ORDER BY recent_requests DESC
            LIMIT 10
        """)
        
        # 6. Handle empty results
        if not stats['general']:
            return {
                'summary': {
                    'total_requests': 0,
                    'new_requests': 0,
                    'in_progress_requests': 0,
                    'completed_requests': 0,
                    'unique_clients': 0,
                    'unique_problem_types': 0,
                    'completion_rate': 0,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'monthly_trends': [],
                'by_technician': [],
                'by_problem_type': [],
                'recent_activity': []
            }
            
        # 7. Umumiy statistika
        result = {
            'summary': {
                'total_requests': stats['general']['total_requests'] or 0,
                'new_requests': stats['general']['new_requests'] or 0,
                'in_progress_requests': stats['general']['in_progress_requests'] or 0,
                'completed_requests': stats['general']['completed_requests'] or 0,
                'unique_clients': stats['general']['unique_clients'] or 0,
                'unique_problem_types': stats['general']['unique_problem_types'] or 0,
                'completion_rate': round((stats['general']['completed_requests'] or 0) / 
                                      (stats['general']['total_requests'] or 1) * 100, 2),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'monthly_trends': [dict(row) for row in stats['monthly_trends']],
            'by_technician': [dict(row) for row in stats['by_technician']],
            'by_problem_type': [dict(row) for row in stats['by_problem_type']],
            'recent_activity': [dict(row) for row in stats['recent_activity']]
        }
        
        return result
    except Exception as e:
        logger.error(f"Error fetching controller statistics for export: {e}")
        return {}
    finally:
        await conn.close()

async def get_controller_employees_for_export() -> List[Dict[str, Any]]:
    """Fetch employees list for controller export (technicians and controllers)"""
    logger.info("Starting to fetch employees for export")
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            full_name,
            COALESCE(phone, '') as phone,
            role,
            created_at
        FROM users
        WHERE role IN ('controller', 'technician', 'manager', 'junior_manager')
        ORDER BY 
            CASE role
                WHEN 'manager' THEN 1
                WHEN 'junior_manager' THEN 2
                WHEN 'controller' THEN 3
                WHEN 'technician' THEN 4
                ELSE 5
            END,
            created_at DESC
        """
        logger.info(f"Executing query: {query}")
        rows = await conn.fetch(query)
        logger.info(f"Fetched {len(rows)} employees from database")
        
        # Translate roles to Uzbek
        role_translations = {
            'controller': 'Kontroller',
            'technician': 'Texnik',
            'manager': 'Menejer',
            'junior_manager': 'Yordamchi menejer'
        }
        
        # Format the results with translated roles
        result = []
        for row in rows:
            row_dict = dict(row)
            result.append({
                "Ism-sharif": row_dict['full_name'],
                "Telefon": row_dict['phone'],
                "Lavozim": role_translations.get(row_dict['role'], row_dict['role']),
                "Qo'shilgan sana": row_dict['created_at'].strftime('%Y-%m-%d %H:%M')
            })
        
        logger.info(f"Formatted {len(result)} employees for export")
        return result
    except Exception as e:
        logger.error(f"Error fetching employees for export: {e}")
        return []
    finally:
        await conn.close()


async def get_controller_connection_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch connection orders handled by controllers for export"""
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
            NULL as controller_name,
            NULL as controller_phone,
            ad.akt_number,
            ad.file_path as akt_file_path,
            ad.created_at as akt_created_at,
            ad.sent_to_client_at,
            ar.rating as akt_rating,
            ar.comment as akt_comment
        FROM connection_orders co
        LEFT JOIN users u ON co.user_id = u.id
        -- No controller_id column exists in connection_orders table
        LEFT JOIN tarif t ON co.tarif_id = t.id
        LEFT JOIN akt_documents ad ON co.id = ad.request_id AND ad.request_type = 'connection'
        LEFT JOIN akt_ratings ar ON co.id = ar.request_id AND ar.request_type = 'connection'
        WHERE co.status IN ('in_controller', 'completed')
        ORDER BY co.created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching connection orders for export: {e}")
        return []
    finally:
        await conn.close()