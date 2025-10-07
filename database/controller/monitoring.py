# database/controller/monitoring.py

from typing import Dict, Any, List
import asyncpg
import logging
from config import settings

logger = logging.getLogger(__name__)

# =========================================================
#  Controller Real-time Monitoring
# =========================================================

async def get_realtime_counts() -> Dict[str, int]:
    """
    Controller uchun real-time counts olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        stats = await conn.fetchrow(
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
                COUNT(CASE WHEN so.status = 'in_controller' THEN 1 END) as in_controller,
                COUNT(CASE WHEN so.status = 'between_controller_technician' THEN 1 END) as between_controller_technician,
                COUNT(CASE WHEN so.status = 'in_technician' THEN 1 END) as in_technician,
                COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN so.status = 'cancelled' THEN 1 END) as cancelled,
                COUNT(*) as total_active
            FROM staff_orders so
            JOIN last_assign la ON la.staff_id = so.id
            WHERE la.recipient_status IN ('in_controller', 'between_controller_technician', 'in_technician')
              AND COALESCE(so.is_active, TRUE) = TRUE
            """
        )
        return dict(stats) if stats else {}
    finally:
        await conn.close()

async def list_active_orders_detailed(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Controller uchun aktiv orders ro'yxatini batafsil olish.
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
              AND so.status IN ('in_controller', 'between_controller_technician', 'in_technician')
              AND COALESCE(so.is_active, TRUE) = TRUE
            ORDER BY so.created_at DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_controller_workflow_history(order_id: int) -> Dict[str, Any]:
    """
    Controller uchun workflow history olish.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Order ma'lumotlarini olamiz
        order_info = await conn.fetchrow(
            """
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
                u.full_name as client_name,
                u.phone as client_phone,
                t.name as tariff,
                r.name as region_name
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN tarif t ON t.id = so.tarif_id
            LEFT JOIN regions r ON r.id = so.region
            WHERE so.id = $1
            """,
            order_id
        )
        
        if not order_info:
            return {}
        
        # Workflow history olamiz
        workflow = await conn.fetch(
            """
            SELECT 
                c.id,
                c.staff_id,
                c.sender_id,
                c.recipient_id,
                c.sender_status,
                c.recipient_status,
                c.created_at,
                sender.full_name as sender_name,
                sender.role as sender_role,
                recipient.full_name as recipient_name,
                recipient.role as recipient_role
            FROM connections c
            LEFT JOIN users sender ON sender.id = c.sender_id
            LEFT JOIN users recipient ON recipient.id = c.recipient_id
            WHERE c.staff_id = $1
            ORDER BY c.created_at ASC
            """,
            order_id
        )
        
        return {
            "order": dict(order_info),
            "workflow": [dict(w) for w in workflow]
        }
    finally:
        await conn.close()

async def get_controller_technician_load() -> List[Dict[str, Any]]:
    """
    Controller uchun technician load monitoring.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            WITH last_assign AS (
                SELECT DISTINCT ON (c.staff_id)
                       c.staff_id,
                       c.recipient_id,
                       c.recipient_status
                FROM connections c
                WHERE c.staff_id IS NOT NULL
                ORDER BY c.staff_id, c.created_at DESC
            ),
            technician_loads AS (
                SELECT
                    la.recipient_id AS technician_id,
                    COUNT(*) AS active_orders,
                    COUNT(CASE WHEN so.status = 'between_controller_technician' THEN 1 END) as pending_orders,
                    COUNT(CASE WHEN so.status = 'in_technician' THEN 1 END) as in_progress_orders
                FROM last_assign la
                JOIN staff_orders so ON so.id = la.staff_id
                WHERE la.recipient_status IN ('between_controller_technician', 'in_technician')
                  AND so.status IN ('between_controller_technician', 'in_technician')
                  AND COALESCE(so.is_active, TRUE) = TRUE
                GROUP BY la.recipient_id
            )
            SELECT 
                u.id,
                u.full_name,
                u.phone,
                u.telegram_id,
                COALESCE(tl.active_orders, 0) as active_orders,
                COALESCE(tl.pending_orders, 0) as pending_orders,
                COALESCE(tl.in_progress_orders, 0) as in_progress_orders
            FROM users u
            LEFT JOIN technician_loads tl ON tl.technician_id = u.id
            WHERE u.role = 'technician'
              AND COALESCE(u.is_blocked, FALSE) = FALSE
            ORDER BY active_orders DESC, u.full_name
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()
