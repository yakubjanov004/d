# database/admin/queries.py

import asyncpg
from typing import List, Dict, Any, Optional
from config import settings

async def get_user_statistics() -> Dict[str, Any]:
    """Foydalanuvchilar statistikasi"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        stats = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN role = 'client' THEN 1 END) as clients,
                COUNT(CASE WHEN role = 'manager' THEN 1 END) as managers,
                COUNT(CASE WHEN role = 'junior_manager' THEN 1 END) as junior_managers,
                COUNT(CASE WHEN role = 'controller' THEN 1 END) as controllers,
                COUNT(CASE WHEN role = 'technician' THEN 1 END) as technicians,
                COUNT(CASE WHEN role = 'callcenter_operator' THEN 1 END) as operators,
                COUNT(CASE WHEN role = 'callcenter_supervisor' THEN 1 END) as supervisors,
                COUNT(CASE WHEN role = 'warehouse' THEN 1 END) as warehouse_staff,
                COUNT(CASE WHEN is_blocked = TRUE THEN 1 END) as blocked_users
            FROM users
            """
        )
        return dict(stats) if stats else {}
    finally:
        await conn.close()

async def get_system_overview() -> Dict[str, Any]:
    """Tizim umumiy ko'rinishi"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        overview = await conn.fetchrow(
            """
            SELECT 
                (SELECT COUNT(*) FROM connection_orders WHERE is_active = TRUE) as active_connections,
                (SELECT COUNT(*) FROM technician_orders WHERE is_active = TRUE) as active_technician,
                (SELECT COUNT(*) FROM staff_orders WHERE is_active = TRUE) as active_staff,
                (SELECT COUNT(*) FROM materials) as total_materials,
                (SELECT COUNT(*) FROM connections) as total_connections,
                (SELECT COUNT(*) FROM akt_ratings) as total_ratings
            """
        )
        return dict(overview) if overview else {}
    finally:
        await conn.close()

async def get_recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
    """So'nggi faoliyat"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                'connection' as type,
                application_number,
                created_at,
                status
            FROM connection_orders
            WHERE is_active = TRUE
            UNION ALL
            SELECT 
                'technician' as type,
                application_number,
                created_at,
                status
            FROM technician_orders
            WHERE is_active = TRUE
            UNION ALL
            SELECT 
                'staff' as type,
                application_number,
                created_at,
                status
            FROM staff_orders
            WHERE is_active = TRUE
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_performance_metrics() -> Dict[str, Any]:
    """Ishlash ko'rsatkichlari"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        metrics = await conn.fetchrow(
            """
            SELECT 
                (SELECT AVG(rating) FROM akt_ratings WHERE rating > 0) as avg_rating,
                (SELECT COUNT(*) FROM connection_orders WHERE status = 'completed' AND created_at >= NOW() - INTERVAL '30 days') as completed_connections_30d,
                (SELECT COUNT(*) FROM technician_orders WHERE status = 'completed' AND created_at >= NOW() - INTERVAL '30 days') as completed_technician_30d,
                (SELECT COUNT(*) FROM staff_orders WHERE status = 'completed' AND created_at >= NOW() - INTERVAL '30 days') as completed_staff_30d
            """
        )
        return dict(metrics) if metrics else {}
    finally:
        await conn.close()

async def get_database_info() -> Dict[str, Any]:
    """Database ma'lumotlari"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        info = await conn.fetchrow(
            """
            SELECT 
                pg_database_size(current_database()) as database_size,
                (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as table_count
            """
        )
        return dict(info) if info else {}
    finally:
        await conn.close()
