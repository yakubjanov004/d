import asyncpg
from config import settings
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def get_ccs_connection_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch connection orders handled by call center supervisors for export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        
        # Get orders that are handled by call center operators under this supervisor
        query = """
        SELECT 
            co.id,
            co.user_id,
            co.region,
            co.address,
            co.longitude,
            co.latitude,
            co.created_at as connection_date,
            co.updated_at,
            co.status,
            co.rating,
            co.notes as comments,
            co.jm_notes as call_center_comments,
            u.full_name as client_name,
            u.phone as client_phone,
            t.name as tariff_name
        FROM connection_orders co
        LEFT JOIN users u ON co.user_id = u.id
        LEFT JOIN tarif t ON co.tarif_id = t.id
        ORDER BY co.created_at DESC
        """
        
        rows = await conn.fetch(query)
        
        result = []
        for row in rows:
            result.append({
                'ID': row['id'],
                'Buyurtma raqami': str(row['id']),  # Using ID as order number
                'Mijoz ismi': row['client_name'] or '',
                'Telefon': row['client_phone'] or '',
                'Mijoz abonent ID': str(row['user_id']) if row['user_id'] else '',
                'Hudud': row['region'] or '',
                'Manzil': row['address'] or '',
                'Uzunlik': str(row['longitude']) if row['longitude'] else '',
                'Kenglik': str(row['latitude']) if row['latitude'] else '',
                'Tarif': row['tariff_name'] or '',
                'Tarif rasmi': '',  # No tariff image column available
                'Ulanish sanasi': row['connection_date'].strftime('%Y-%m-%d %H:%M:%S') if row['connection_date'] else '',
                'Yangilangan sana': row['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['updated_at'] else '',
                'Holati': row['status'] or '',
                'Reyting': str(row['rating']) if row['rating'] else '',
                'Izohlar': row['comments'] or '',
                'Call Center izohlar': row['call_center_comments'] or '',
                'Operator': '',  # No operator assignment in current schema
                'Operator telefon': ''  # No operator assignment in current schema
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting connection orders for export: {e}")
        return []
    finally:
        await conn.close()

async def get_ccs_statistics_for_export() -> Dict[str, Any]:
    """Get comprehensive statistics for call center supervisor export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        
        # 1. Summary statistics
        summary_query = """
        SELECT 
            COUNT(*) as total_orders,
            COUNT(CASE WHEN status = 'in_manager' THEN 1 END) as new_orders,
            COUNT(CASE WHEN status IN ('in_junior_manager', 'in_controller', 'between_controller_technician', 'in_technician', 'in_warehouse', 'in_technician_work') THEN 1 END) as in_progress_orders,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders,
            COUNT(DISTINCT u.phone) as unique_clients,
            COUNT(DISTINCT t.name) as unique_tariffs_used
        FROM connection_orders co
        LEFT JOIN users u ON co.user_id = u.id
        LEFT JOIN tarif t ON co.tarif_id = t.id
        """
        
        summary_row = await conn.fetchrow(summary_query)
        
        completion_rate = 0
        if summary_row['total_orders'] > 0:
            completion_rate = round((summary_row['completed_orders'] / summary_row['total_orders']) * 100, 2)
        
        summary = {
            'total_orders': summary_row['total_orders'],
            'new_orders': summary_row['new_orders'],
            'in_progress_orders': summary_row['in_progress_orders'],
            'completed_orders': summary_row['completed_orders'],
            'completion_rate': completion_rate,
            'unique_clients': summary_row['unique_clients'],
            'unique_tariffs_used': summary_row['unique_tariffs_used']
        }
        
        # 2. Statistics by operator
        operator_query = """
        SELECT 
            u.full_name as operator_name,
            u.phone as operator_phone,
            COUNT(co.id) as total_orders,
            COUNT(CASE WHEN co.status = 'completed' THEN 1 END) as completed_orders
        FROM users u
        LEFT JOIN connection_orders co ON u.id = co.user_id
        WHERE u.role = 'callcenter_operator'
        GROUP BY u.id, u.full_name, u.phone
        ORDER BY total_orders DESC
        """
        
        operator_rows = await conn.fetch(operator_query)
        by_operator = []
        for row in operator_rows:
            by_operator.append({
                'operator_name': row['operator_name'] or 'Noma\'lum',
                'operator_phone': row['operator_phone'],
                'total_orders': row['total_orders'],
                'completed_orders': row['completed_orders']
            })
        
        # 3. Monthly trends (last 6 months)
        monthly_query = """
        SELECT 
            TO_CHAR(co.created_at, 'YYYY-MM') as month,
            COUNT(*) as total_orders,
            COUNT(CASE WHEN co.status = 'in_manager' THEN 1 END) as new_orders,
            COUNT(CASE WHEN co.status = 'completed' THEN 1 END) as completed_orders
        FROM connection_orders co
        WHERE co.created_at >= NOW() - INTERVAL '6 months'
        GROUP BY TO_CHAR(co.created_at, 'YYYY-MM')
        ORDER BY month DESC
        """
        
        monthly_rows = await conn.fetch(monthly_query)
        monthly_trends = []
        for row in monthly_rows:
            monthly_trends.append({
                'month': row['month'],
                'total_orders': row['total_orders'],
                'new_orders': row['new_orders'],
                'completed_orders': row['completed_orders']
            })
        
        # 4. Statistics by tariff
        tariff_query = """
        SELECT 
            t.name as tariff_name,
            COUNT(*) as total_orders,
            COUNT(DISTINCT u.phone) as unique_clients
        FROM connection_orders co
        LEFT JOIN tarif t ON co.tarif_id = t.id
        LEFT JOIN users u ON co.user_id = u.id
        WHERE t.name IS NOT NULL
        GROUP BY t.name
        ORDER BY total_orders DESC
        LIMIT 10
        """
        
        tariff_rows = await conn.fetch(tariff_query)
        by_tariff = []
        for row in tariff_rows:
            by_tariff.append({
                'tariff_name': row['tariff_name'],
                'total_orders': row['total_orders'],
                'unique_clients': row['unique_clients']
            })
        
        # 5. Recent activity (last 30 days)
        activity_query = """
        SELECT 
            'System' as operator_name,
            COUNT(*) as recent_orders,
            MAX(co.created_at) as last_activity
        FROM connection_orders co
        WHERE co.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY 'System'
        ORDER BY recent_orders DESC
        """
        
        activity_rows = await conn.fetch(activity_query)
        recent_activity = []
        for row in activity_rows:
            recent_activity.append({
                'operator_name': row['operator_name'] or 'Noma\'lum',
                'recent_orders': row['recent_orders'],
                'last_activity': row['last_activity']
            })
        
        return {
            'summary': summary,
            'by_operator': by_operator,
            'monthly_trends': monthly_trends,
            'by_tariff': by_tariff,
            'recent_activity': recent_activity
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics for export: {e}")
        return {
            'summary': {'total_orders': 0, 'new_orders': 0, 'in_progress_orders': 0, 'completed_orders': 0, 'completion_rate': 0, 'unique_clients': 0, 'unique_tariffs_used': 0},
            'by_operator': [],
            'monthly_trends': [],
            'by_tariff': [],
            'recent_activity': []
        }

async def get_ccs_employees_for_export() -> List[Dict[str, Any]]:
    """Get employees data for call center supervisor export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        
        # Get call center operators under this supervisor
        query = """
        SELECT 
            u.id,
            u.full_name,
            u.phone,
            u.telegram_id,
            u.role,
            u.is_blocked,
            u.created_at,
            COUNT(co.id) as total_orders,
            COUNT(CASE WHEN co.status = 'completed' THEN 1 END) as completed_orders
        FROM users u
        LEFT JOIN connection_orders co ON u.id = co.user_id
        WHERE u.role = 'callcenter_operator'
        GROUP BY u.id, u.full_name, u.phone, u.telegram_id, u.role, u.is_blocked, u.created_at
        ORDER BY u.full_name
        """
        
        rows = await conn.fetch(query)
        
        result = []
        for row in rows:
            result.append({
                'ID': row['id'],
                'To\'liq ism': row['full_name'] or '',
                'Telefon': row['phone'] or '',
                'Telegram ID': row['telegram_id'] or '',
                'Rol': row['role'] or '',
                'Jami buyurtmalar': row['total_orders'] or 0,
                'Bajarilgan buyurtmalar': row['completed_orders'] or 0,
                'Holati': 'Nofaol' if row['is_blocked'] else 'Faol',
                'Qo\'shilgan sana': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else ''
            })
        
        return result
        
    finally:
        await conn.close()



async def get_ccs_operator_orders_for_export() -> List[Dict[str, Any]]:
    """Fetch orders/applications opened by call center operators for export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Get orders that were created/handled by call center operators
        query = """
        SELECT 
            co.id,
            co.user_id,
            co.region,
            co.address,
            co.longitude,
            co.latitude,
            co.created_at as connection_date,
            co.updated_at,
            co.status,
            co.rating,
            co.notes as comments,
            co.jm_notes as call_center_comments,
            u.full_name as client_name,
            u.phone as client_phone,
            t.name as tariff_name,
            '' as operator_name,
            '' as operator_phone
        FROM connection_orders co
        LEFT JOIN users u ON co.user_id = u.id
        LEFT JOIN tarif t ON co.tarif_id = t.id
        ORDER BY co.created_at DESC
        """
        
        rows = await conn.fetch(query)
        
        result = []
        for row in rows:
            result.append({
                'ID': row['id'],
                'Ariza raqami': str(row['id']),
                'Mijoz ismi': row['client_name'] or '',
                'Mijoz telefoni': row['client_phone'] or '',
                'Mijoz abonent ID': str(row['user_id']) if row['user_id'] else '',
                'Hudud': row['region'] or '',
                'Manzil': row['address'] or '',
                'Tarif': row['tariff_name'] or '',
                'Yaratilgan sana': row['connection_date'].strftime('%Y-%m-%d %H:%M:%S') if row['connection_date'] else '',
                'Yangilangan sana': row['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['updated_at'] else '',
                'Holati': row['status'] or '',
                'Reyting': str(row['rating']) if row['rating'] else '',
                'Mijoz izohi': row['comments'] or '',
                'Call Center izohi': row['call_center_comments'] or '',
                'Operator ismi': row['operator_name'] or 'Tayinlanmagan',
                'Operator telefoni': row['operator_phone'] or ''
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting operator orders for export: {e}")
        return []
    finally:
        await conn.close()

async def get_ccs_operators_for_export() -> List[Dict[str, Any]]:
    """Get call center operators data for export"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Get call center operators with their performance metrics
        query = """
        SELECT 
            u.id,
            u.full_name,
            u.phone,
            u.telegram_id,
            u.role,
            u.is_blocked,
            u.created_at,
            0 as total_orders,
            0 as completed_orders,
            0 as in_progress_orders,
            0.0 as avg_rating,
            u.created_at as last_activity
        FROM users u
        WHERE u.role = 'callcenter_operator'
        ORDER BY u.full_name
        """
        
        rows = await conn.fetch(query)
        
        result = []
        for row in rows:
            result.append({
                'ID': row['id'],
                'Operator ismi': row['full_name'] or '',
                'Telefon': row['phone'] or '',
                'Telegram ID': str(row['telegram_id']) if row['telegram_id'] else '',
                'Jami arizalar': row['total_orders'] or 0,
                'Bajarilgan arizalar': row['completed_orders'] or 0,
                'Jarayondagi arizalar': row['in_progress_orders'] or 0,
                'O\'rtacha reyting': f"{row['avg_rating']:.2f}" if row['avg_rating'] else '0.00',
                'Holati': 'Nofaol' if row['is_blocked'] else 'Faol',
                'So\'nggi faollik': row['last_activity'].strftime('%Y-%m-%d %H:%M:%S') if row['last_activity'] else 'Hech qachon',
                'Qo\'shilgan sana': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else ''
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting operators for export: {e}")
        return []
    finally:
        await conn.close()