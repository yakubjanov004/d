# database/admin/export.py

import asyncpg
from typing import List, Dict, Any
from config import settings

async def get_admin_users_for_export(user_type: str = "all") -> List[Dict[str, Any]]:
    """Admin uchun foydalanuvchilar ro'yxatini export qilish"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Build query based on user type
        if user_type == "clients":
            where_clause = "WHERE role = 'client'"
        elif user_type == "staff":
            where_clause = "WHERE role IN ('admin', 'manager', 'controller', 'technician', 'callcenter_supervisor', 'callcenter_operator', 'junior_manager', 'warehouse')"
        else:
            where_clause = ""
        
        rows = await conn.fetch(
            f"""
            SELECT 
                id,
                telegram_id,
                username,
                full_name,
                phone,
                role,
                language,
                is_blocked,
                created_at,
                updated_at
            FROM users
            {where_clause}
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_admin_connection_orders_for_export() -> List[Dict[str, Any]]:
    """Admin uchun connection orders ro'yxatini export qilish"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                co.id,
                co.application_number,
                co.address,
                co.region,
                co.status,
                co.is_active,
                co.created_at,
                co.updated_at,
                u.full_name as client_name,
                u.phone as client_phone,
                t.name as tariff_name
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            ORDER BY co.created_at DESC
            """
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_admin_technician_orders_for_export() -> List[Dict[str, Any]]:
    """Admin uchun technician orders ro'yxatini export qilish"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                tech_orders.id,
                tech_orders.application_number,
                tech_orders.address,
                tech_orders.region,
                tech_orders.status,
                tech_orders.is_active,
                tech_orders.description,
                tech_orders.created_at,
                tech_orders.updated_at,
                u.full_name as client_name,
                u.phone as client_phone
            FROM technician_orders tech_orders
            LEFT JOIN users u ON u.id = tech_orders.user_id
            ORDER BY tech_orders.created_at DESC
            """
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_admin_staff_orders_for_export() -> List[Dict[str, Any]]:
    """Admin uchun staff orders ro'yxatini export qilish"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                so.id,
                so.application_number,
                so.address,
                so.region,
                so.status,
                so.is_active,
                so.description,
                so.phone,
                so.created_at,
                so.updated_at,
                u.full_name as client_name,
                u.phone as client_phone
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            ORDER BY so.created_at DESC
            """
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_admin_statistics_for_export() -> Dict[str, Any]:
    """Admin uchun statistikalar"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        stats = await conn.fetchrow(
            """
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM connection_orders WHERE is_active = TRUE) as active_connections,
                (SELECT COUNT(*) FROM technician_orders WHERE is_active = TRUE) as active_technician,
                (SELECT COUNT(*) FROM staff_orders WHERE is_active = TRUE) as active_staff,
                (SELECT COUNT(*) FROM materials) as total_materials
            """
        )
        return dict(stats) if stats else {}
    finally:
        await conn.close()
