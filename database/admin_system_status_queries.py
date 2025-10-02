import asyncpg
from config import settings
from typing import Dict, Any, List
from datetime import datetime, timedelta

async def get_system_overview() -> Dict[str, Any]:
    """Tizimning umumiy ko'rinishi"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Umumiy statistika
        stats = {}
        
        # Foydalanuvchilar soni
        stats['total_users'] = await conn.fetchval("SELECT COUNT(*) FROM users")
        stats['active_users'] = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_blocked = false")
        stats['blocked_users'] = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_blocked = true")
        
        # Rollar bo'yicha foydalanuvchilar (barcha rollarni ko'rsatish)
        role_stats = await conn.fetch("""
            WITH all_roles AS (
                SELECT unnest(enum_range(NULL::user_role)) as role
            )
            SELECT 
                ar.role,
                COALESCE(COUNT(u.role), 0) as count
            FROM all_roles ar
            LEFT JOIN users u ON ar.role = u.role AND u.is_blocked = false
            GROUP BY ar.role
            ORDER BY count DESC
        """)
        stats['users_by_role'] = {row['role']: row['count'] for row in role_stats}
        
        # Zayavkalar statistikasi
        stats['total_connection_orders'] = await conn.fetchval("SELECT COUNT(*) FROM connection_orders WHERE is_active = true")
        stats['total_technician_orders'] = await conn.fetchval("SELECT COUNT(*) FROM technician_orders WHERE is_active = true")
        stats['total_staff_orders'] = await conn.fetchval("SELECT COUNT(*) FROM staff_orders WHERE is_active = true")
        
        # Bugungi zayavkalar
        today = datetime.now().date()
        stats['today_connection_orders'] = await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE DATE(created_at) = $1 AND is_active = true", 
            today
        )
        stats['today_technician_orders'] = await conn.fetchval(
            "SELECT COUNT(*) FROM technician_orders WHERE DATE(created_at) = $1 AND is_active = true", 
            today
        )
        
        return stats
    finally:
        await conn.close()

async def get_orders_by_status() -> Dict[str, Any]:
    """Zayavkalarni status bo'yicha guruhlash"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        result = {}
        
        # Ulanish zayavkalari statuslari
        connection_status = await conn.fetch("""
            SELECT status, COUNT(*) as count 
            FROM connection_orders 
            WHERE is_active = true 
            GROUP BY status 
            ORDER BY count DESC
        """)
        result['connection_orders'] = {row['status']: row['count'] for row in connection_status}
        
        # Texnik zayavkalar statuslari
        technician_status = await conn.fetch("""
            SELECT status, COUNT(*) as count 
            FROM technician_orders 
            WHERE is_active = true 
            GROUP BY status 
            ORDER BY count DESC
        """)
        result['technician_orders'] = {row['status']: row['count'] for row in technician_status}
        
        # Xodim zayavkalari statuslari
        staff_status = await conn.fetch("""
            SELECT status, COUNT(*) as count 
            FROM staff_orders 
            WHERE is_active = true 
            GROUP BY status 
            ORDER BY count DESC
        """)
        result['staff_orders'] = {row['status']: row['count'] for row in staff_status}
        
        return result
    finally:
        await conn.close()

async def get_recent_activity() -> List[Dict[str, Any]]:
    """So'nggi faoliyat"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # So'nggi 24 soat ichidagi faoliyat
        last_24h = datetime.now() - timedelta(hours=24)
        
        activities = await conn.fetch("""
            SELECT 
                'connection_order' as type,
                id,
                status::text as status,
                created_at,
                updated_at
            FROM connection_orders 
            WHERE updated_at >= $1 AND is_active = true
            
            UNION ALL
            
            SELECT 
                'technician_order' as type,
                id,
                status::text as status,
                created_at,
                updated_at
            FROM technician_orders 
            WHERE updated_at >= $1 AND is_active = true
            
            UNION ALL
            
            SELECT 
                'staff_order' as type,
                id,
                status::text as status,
                created_at,
                updated_at
            FROM staff_orders 
            WHERE updated_at >= $1 AND is_active = true
            
            ORDER BY updated_at DESC
            LIMIT 10
        """, last_24h)
        
        return [dict(row) for row in activities]
    finally:
        await conn.close()

async def get_performance_metrics() -> Dict[str, Any]:
    """Tizim ishlash ko'rsatkichlari"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        metrics = {}
        
        # Bajarilgan zayavkalar foizi
        total_connection = await conn.fetchval("SELECT COUNT(*) FROM connection_orders WHERE is_active = true")
        completed_connection = await conn.fetchval("SELECT COUNT(*) FROM connection_orders WHERE status = 'completed' AND is_active = true")
        
        total_technician = await conn.fetchval("SELECT COUNT(*) FROM technician_orders WHERE is_active = true")
        completed_technician = await conn.fetchval("SELECT COUNT(*) FROM technician_orders WHERE status = 'completed' AND is_active = true")
        
        metrics['connection_completion_rate'] = (completed_connection / total_connection * 100) if total_connection > 0 else 0
        metrics['technician_completion_rate'] = (completed_technician / total_technician * 100) if total_technician > 0 else 0
        
        # O'rtacha bajarilish vaqti (soatlarda)
        avg_completion_time = await conn.fetchrow("""
            SELECT 
                AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_hours
            FROM connection_orders 
            WHERE status = 'completed' AND is_active = true
        """)
        metrics['avg_completion_hours'] = float(avg_completion_time['avg_hours']) if avg_completion_time['avg_hours'] else 0
        
        # Eng faol xodimlar
        active_staff = await conn.fetch("""
            SELECT 
                u.full_name,
                u.role,
                COUNT(c.id) as activity_count
            FROM users u
            LEFT JOIN connections c ON u.id = c.sender_id OR u.id = c.recipient_id
            WHERE u.role != 'client' AND u.is_blocked = false
            GROUP BY u.id, u.full_name, u.role
            ORDER BY activity_count DESC
            LIMIT 10
        """)
        metrics['active_staff'] = [dict(row) for row in active_staff]
        
        return metrics
    finally:
        await conn.close()

async def get_database_info() -> Dict[str, Any]:
    """Ma'lumotlar bazasi haqida ma'lumot"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        info = {}
        
        # Jadvallar hajmi
        table_sizes = await conn.fetch("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)
        info['table_sizes'] = [dict(row) for row in table_sizes]
        
        # Umumiy ma'lumotlar bazasi hajmi
        db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
        info['database_size'] = db_size
        
        # Ulanishlar soni
        connections_count = await conn.fetchval("SELECT count(*) FROM pg_stat_activity")
        info['active_connections'] = connections_count
        
        return info
    finally:
        await conn.close()