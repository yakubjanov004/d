import asyncpg
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from config import settings

async def _conn():
    return await asyncpg.connect(settings.DB_URL)

def _as_dicts(rows):
    return [dict(r) for r in rows]

INITIAL_SQL = """
-- Ensure unique constraint on akt_documents
ALTER TABLE akt_documents
  ADD CONSTRAINT IF NOT EXISTS ux_akt_documents 
  UNIQUE (request_id, request_type);

-- Create indexes for material_requests
CREATE INDEX IF NOT EXISTS ix_mr_applications_id 
  ON material_requests(applications_id);

-- Only create these indexes if the columns exist
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns 
             WHERE table_name = 'material_requests' AND column_name = 'connection_order_id') THEN
    CREATE INDEX IF NOT EXISTS ix_mr_connection_order_id 
      ON material_requests(connection_order_id);
  END IF;
  
  IF EXISTS (SELECT 1 FROM information_schema.columns 
             WHERE table_name = 'material_requests' AND column_name = 'technician_order_id') THEN
    CREATE INDEX IF NOT EXISTS ix_mr_technician_order_id 
      ON material_requests(technician_order_id);
  END IF;
  
  IF EXISTS (SELECT 1 FROM information_schema.columns 
             WHERE table_name = 'material_requests' AND column_name = 'saff_order_id') THEN
    CREATE INDEX IF NOT EXISTS ix_mr_saff_order_id 
      ON material_requests(saff_order_id);
  END IF;
END $$;
"""

async def initialize_database():
    """Initialize database with required indexes and constraints"""
    conn = await _conn()
    try:
        await conn.execute(INITIAL_SQL)
        print("Database initialization completed successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        await conn.close()

async def get_akt_data_by_request_id(request_id: int, request_type: str) -> Optional[Dict[str, Any]]:
    """
    AKT uchun kerakli ma'lumotlarni olish (3 ta tur uchun)
    """
    conn = await _conn()
    try:
        if request_type == "connection":
            # Connection orders uchun
            query = """
                SELECT 
                    co.id as request_id,
                    'connection' as workflow_type,
                    co.created_at,
                    co.updated_at as closed_at,
                    co.address,
                    co.region,
                    co.notes as description_ish,
                    u.full_name as client_name,
                    u.phone as client_phone,
                    u.telegram_id as client_telegram_id,
                    COALESCE(t.full_name, '-') as technician_name,
                    tar.name as tariff_name
                FROM connection_orders co
                LEFT JOIN users u ON co.user_id = u.id
                LEFT JOIN LATERAL (
                    SELECT mr.user_id
                    FROM material_requests mr
                    WHERE mr.applications_id = co.id
                    LIMIT 1
                ) mru ON TRUE
                LEFT JOIN users t ON t.id = mru.user_id
                LEFT JOIN tarif tar ON co.tarif_id = tar.id
                WHERE co.id = $1 AND co.is_active = true
            """
        elif request_type == "technician":
            # Technician orders uchun
            query = """
                SELECT 
                    to2.id as request_id,
                    'technician' as workflow_type,
                    to2.created_at,
                    to2.updated_at as closed_at,
                    to2.address,
                    to2.region::text,
                    to2.description_ish,
                    u.full_name as client_name,
                    u.phone as client_phone,
                    u.telegram_id as client_telegram_id,
                    COALESCE(t.full_name, '-') as technician_name,
                    NULL as tariff_name
                FROM technician_orders to2
                LEFT JOIN users u ON to2.user_id = u.id
                LEFT JOIN LATERAL (
                    SELECT mr.user_id
                    FROM material_requests mr
                    WHERE mr.applications_id = to2.id
                    LIMIT 1
                ) mru ON TRUE
                LEFT JOIN users t ON t.id = mru.user_id
                WHERE to2.id = $1 AND to2.is_active = true
            """
        elif request_type == "saff":
            # Saff orders uchun
            query = """
                SELECT 
                    so.id as request_id,
                    'saff' as workflow_type,
                    so.created_at,
                    so.updated_at as closed_at,
                    so.address,
                    so.region::text,
                    so.description as description_ish,
                    u.full_name as client_name,
                    u.phone as client_phone,
                    u.telegram_id as client_telegram_id,
                    COALESCE(t.full_name, '-') as technician_name,
                    tar.name as tariff_name
                FROM saff_orders so
                LEFT JOIN users u ON so.user_id = u.id
                LEFT JOIN LATERAL (
                    SELECT mr.user_id
                    FROM material_requests mr
                    WHERE mr.applications_id = so.id
                    LIMIT 1
                ) mru ON TRUE
                LEFT JOIN users t ON t.id = mru.user_id
                LEFT JOIN tarif tar ON so.tarif_id = tar.id
                WHERE so.id = $1 AND so.is_active = true
            """
        else:
            return None
            
        row = await conn.fetchrow(query, request_id)
        return dict(row) if row else None
    finally:
        await conn.close()

async def get_materials_for_akt(request_id: int, request_type: str) -> List[Dict[str, Any]]:
    """
    AKT uchun materiallar ro'yxatini olish (3 ta tur uchun)
    """
    conn = await _conn()
    try:
        if request_type == "connection":
            query = """
                SELECT 
                    m.name as material_name,
                    COALESCE(mr.quantity, 1) as quantity,
                    m.price as price,
                    (COALESCE(mr.quantity, 1) * m.price) as total_price
                FROM material_requests mr
                JOIN materials m ON mr.material_id = m.id
                WHERE mr.applications_id = $1 OR mr.connection_order_id = $1
            """
        elif request_type == "technician":
            query = """
                SELECT 
                    m.name as material_name,
                    COALESCE(mr.quantity, 1) as quantity,
                    m.price as price,
                    (COALESCE(mr.quantity, 1) * m.price) as total_price
                FROM material_requests mr
                JOIN materials m ON mr.material_id = m.id
                WHERE mr.applications_id = $1 OR mr.technician_order_id = $1
            """
        elif request_type == "saff":
            query = """
                SELECT 
                    m.name as material_name,
                    COALESCE(mr.quantity, 1) as quantity,
                    m.price as price,
                    (COALESCE(mr.quantity, 1) * m.price) as total_price
                FROM material_requests mr
                JOIN materials m ON mr.material_id = m.id
                WHERE mr.applications_id = $1 OR mr.saff_order_id = $1
            """
        else:
            return []
        
        rows = await conn.fetch(query, request_id)
        return _as_dicts(rows)
    finally:
        await conn.close()

async def create_akt_document(request_id: int, request_type: str, akt_number: str, file_path: str, file_hash: str) -> bool:
    """
    AKT hujjatini bazaga yozish
    """
    conn = await _conn()
    try:
        query = """
            INSERT INTO akt_documents (request_id, request_type, akt_number, file_path, file_hash, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (request_id, request_type) DO UPDATE SET
                akt_number = EXCLUDED.akt_number,
                file_path = EXCLUDED.file_path,
                file_hash = EXCLUDED.file_hash,
                created_at = EXCLUDED.created_at
        """
        await conn.execute(query, request_id, request_type, akt_number, file_path, file_hash, datetime.now())
        return True
    except Exception as e:
        print(f"Error creating AKT document: {e}")
        return False
    finally:
        await conn.close()

async def mark_akt_sent(request_id: int, request_type: str, sent_to_client_at: datetime) -> bool:
    """
    AKT yuborilganini belgilash
    """
    conn = await _conn()
    try:
        query = """
            UPDATE akt_documents 
            SET sent_to_client_at = $1
            WHERE request_id = $2 AND request_type = $3
        """
        await conn.execute(query, sent_to_client_at, request_id, request_type)
        return True
    except Exception as e:
        print(f"Error marking AKT as sent: {e}")
        return False
    finally:
        await conn.close()

async def check_akt_exists(request_id: int, request_type: str) -> bool:
    """
    AKT mavjudligini tekshirish (idempotent)
    """
    conn = await _conn()
    try:
        query = """
            SELECT id FROM akt_documents 
            WHERE request_id = $1 AND request_type = $2
        """
        row = await conn.fetchrow(query, request_id, request_type)
        return row is not None
    finally:
        await conn.close()

async def get_technician_id_by_request(request_id: int, request_type: str) -> Optional[int]:
    """
    Zayavka bo'yicha texnik ID ni olish
    """
    conn = await _conn()
    try:
        if request_type == "connection":
            query = """
                SELECT 
                    co.id as request_id,
                    co.address as client_address,
                    co.created_at as request_date,
                    u.full_name as client_name,
                    u.phone as client_phone,
                    u.telegram_id as client_telegram_id,
                    COALESCE(t.full_name, '-') as technician_name,
                    t.id as technician_id,
                    tar.name as tariff_name
                FROM connection_orders co
                LEFT JOIN users u ON co.user_id = u.id
                LEFT JOIN LATERAL (
                    SELECT mr.user_id
                    FROM material_requests mr
                    WHERE mr.applications_id = co.id
                    LIMIT 1
                ) mru ON TRUE
                LEFT JOIN users t ON t.id = mru.user_id
                LEFT JOIN tarif tar ON co.tarif_id = tar.id
                WHERE co.id = $1 AND co.is_active = true
            """
        elif request_type == "technician":
            query = """
                SELECT 
                    to2.id as request_id,
                    to2.address as client_address,
                    to2.created_at as request_date,
                    u.full_name as client_name,
                    u.phone as client_phone,
                    u.telegram_id as client_telegram_id,
                    COALESCE(t.full_name, '-') as technician_name,
                    t.id as technician_id,
                    tar.name as tariff_name
                FROM technician_orders to2
                LEFT JOIN users u ON to2.user_id = u.id
                LEFT JOIN LATERAL (
                    SELECT mr.user_id
                    FROM material_requests mr
                    WHERE mr.applications_id = to2.id
                    LIMIT 1
                ) mru ON TRUE
                LEFT JOIN users t ON t.id = mru.user_id
                LEFT JOIN tarif tar ON to2.tarif_id = tar.id
                WHERE to2.id = $1 AND to2.is_active = true
            """
        elif request_type == "saff":
            query = """
                SELECT 
                    so.id as request_id,
                    so.address as client_address,
                    so.created_at as request_date,
                    u.full_name as client_name,
                    u.phone as client_phone,
                    u.telegram_id as client_telegram_id,
                    COALESCE(t.full_name, '-') as technician_name,
                    t.id as technician_id,
                    tar.name as tariff_name
                FROM saff_orders so
                LEFT JOIN users u ON so.user_id = u.id
                LEFT JOIN LATERAL (
                    SELECT mr.user_id
                    FROM material_requests mr
                    WHERE mr.applications_id = so.id
                    LIMIT 1
                ) mru ON TRUE
                LEFT JOIN users t ON t.id = mru.user_id
                LEFT JOIN tarif tar ON so.tarif_id = tar.id
                WHERE so.id = $1 AND so.is_active = true
            """
        else:
            return None
            
        row = await conn.fetchrow(query, request_id)
        return row['technician_id'] if row and 'technician_id' in row else None
    finally:
        await conn.close()
