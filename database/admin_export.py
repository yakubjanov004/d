import asyncpg
from typing import List, Dict, Any
from config import settings


async def _fetch_all(query: str, *params) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_admin_users_for_export(user_type: str = "clients") -> List[Dict[str, Any]]:
    """Export users for admin. user_type: clients | staff | all"""
    where_clause = ""
    if user_type == "clients":
        where_clause = "WHERE role = 'client'"
    elif user_type == "staff":
        where_clause = (
            "WHERE role <> 'client'"
        )
    # else all

    query = f"""
        SELECT id, telegram_id, username, full_name, phone, role,
               created_at, updated_at, COALESCE(is_blocked,false) as is_blocked
        FROM users
        {where_clause}
        ORDER BY created_at DESC
    """
    return await _fetch_all(query)


async def get_admin_connection_orders_for_export() -> List[Dict[str, Any]]:
    query = """
        SELECT co.id, u.full_name, u.phone, u.username, u.telegram_id,
               co.region, co.address, co.latitude, co.longitude,
               t.name as tarif_name, co.status, co.rating, co.notes, co.jm_notes,
               co.created_at, co.updated_at
        FROM connection_orders co
        LEFT JOIN users u ON u.id = co.user_id
        LEFT JOIN tarif t ON t.id = co.tarif_id
        ORDER BY co.created_at DESC
    """
    return await _fetch_all(query)


async def get_admin_technician_orders_for_export() -> List[Dict[str, Any]]:
    query = """
        SELECT to_.id, u.full_name, u.phone, u.username, u.telegram_id,
               to_.abonent_id, to_.region, to_.address, to_.latitude, to_.longitude,
               to_.description, to_.status, to_.rating, to_.notes,
               to_.created_at, to_.updated_at
        FROM technician_orders to_
        LEFT JOIN users u ON u.id = to_.user_id
        ORDER BY to_.created_at DESC
    """
    return await _fetch_all(query)


async def get_admin_saff_orders_for_export() -> List[Dict[str, Any]]:
    query = """
        SELECT so.id, u.full_name, u.username, u.telegram_id, so.phone,
               so.abonent_id, so.region, so.address, so.type_of_zayavka,
               so.description, so.status, so.created_at, so.updated_at,
               t.name as tarif_name
        FROM saff_orders so
        LEFT JOIN users u ON u.id = so.user_id
        LEFT JOIN tarif t ON t.id = so.tarif_id
        ORDER BY so.created_at DESC
    """
    return await _fetch_all(query)


async def get_admin_statistics_for_export() -> Dict[str, Any]:
    """Minimal admin-wide statistics for export."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_clients = await conn.fetchval("SELECT COUNT(*) FROM users WHERE role='client'")
        total_staff = await conn.fetchval("SELECT COUNT(*) FROM users WHERE role<>'client'")

        total_conn_orders = await conn.fetchval("SELECT COUNT(*) FROM connection_orders")
        total_tech_orders = await conn.fetchval("SELECT COUNT(*) FROM technician_orders")
        total_saff_orders = await conn.fetchval("SELECT COUNT(*) FROM saff_orders")

        by_role = await conn.fetch("SELECT role, COUNT(*) cnt FROM users GROUP BY role ORDER BY cnt DESC")
        conn_by_status = await conn.fetch("SELECT status, COUNT(*) cnt FROM connection_orders GROUP BY status ORDER BY cnt DESC")
        tech_by_status = await conn.fetch("SELECT status, COUNT(*) cnt FROM technician_orders GROUP BY status ORDER BY cnt DESC")

        return {
            "users": {
                "total": total_users,
                "clients": total_clients,
                "staff": total_staff,
                "by_role": [dict(r) for r in by_role],
            },
            "orders": {
                "connection_total": total_conn_orders,
                "technician_total": total_tech_orders,
                "saff_total": total_saff_orders,
                "connection_by_status": [dict(r) for r in conn_by_status],
                "technician_by_status": [dict(r) for r in tech_by_status],
            },
        }
    finally:
        await conn.close()


