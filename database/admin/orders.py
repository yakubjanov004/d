# database/admin/orders.py

import asyncpg
from typing import List, Dict, Any
from config import settings

async def get_connection_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Connection orders ro'yxati"""
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
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_technician_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Technician orders ro'yxati"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                to.id,
                to.application_number,
                to.address,
                to.region,
                to.status,
                to.is_active,
                to.description,
                to.created_at,
                to.updated_at,
                u.full_name as client_name,
                u.phone as client_phone
            FROM technician_orders to
            LEFT JOIN users u ON u.id = to.user_id
            ORDER BY to.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_staff_orders(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Staff orders ro'yxati"""
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
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()
