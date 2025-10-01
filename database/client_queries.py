import asyncpg
from config import settings
from typing import Optional

async def find_user_by_telegram_id(telegram_id: int) -> Optional[asyncpg.Record]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        result = await conn.fetchrow(
            """
            SELECT * FROM users WHERE telegram_id = $1
            """
        , telegram_id)
        return result
    finally:
        await conn.close()

# Region name to ID mapping
REGION_NAME_TO_ID = {
    'toshkent_city': 1,
    'toshkent_region': 2,
    'andijon': 3,
    'fergana': 4,
    'namangan': 5,
    'sirdaryo': 6,
    'jizzax': 7,
    'samarkand': 8,
    'bukhara': 9,
    'navoi': 10,
    'navoiy': 10,  # Alternative spelling
    'kashkadarya': 11,
    'surkhandarya': 12,
    'khorezm': 13,
    'karakalpakstan': 14,
}

# Region ID to name mapping (reverse mapping)
REGION_ID_TO_NAME = {
    1: 'Toshkent shahri',
    2: 'Toshkent viloyati',
    3: 'Andijon viloyati',
    4: 'Farg\'ona viloyati',
    5: 'Namangan viloyati',
    6: 'Sirdaryo viloyati',
    7: 'Jizzax viloyati',
    8: 'Samarqand viloyati',
    9: 'Buxoro viloyati',
    10: 'Navoiy viloyati',
    11: 'Qashqadaryo viloyati',
    12: 'Surxondaryo viloyati',
    13: 'Xorazm viloyati',
    14: 'Qoraqalpog\'iston Respublikasi',
}

# Function to get region name by ID
def get_region_name_by_id(region_id):
    """Convert region ID to human-readable name"""
    try:
        region_id = int(region_id)
        return REGION_ID_TO_NAME.get(region_id, f'Hudud #{region_id}')
    except (ValueError, TypeError):
        return str(region_id) if region_id else 'Noma\'lum hudud'

async def create_service_order(user_id: int, region: str, abonent_id: str, address: str, description: str, media: str, geo: str) -> int:
    """Create a service order in technician_orders table.

    technician_orders schema:
      user_id BIGINT, region INTEGER, abonent_id TEXT, address TEXT,
      media TEXT, longitude DOUBLE PRECISION, latitude DOUBLE PRECISION,
      description TEXT, status technician_order_status DEFAULT 'new', ...
    """
    latitude = None
    longitude = None
    if geo:
        try:
            lat_str, lon_str = geo.split(",", 1)
            latitude = float(lat_str)
            longitude = float(lon_str)
        except Exception:
            latitude = None
            longitude = None

    # Convert region string to integer ID
    region_id = REGION_NAME_TO_ID.get(region.lower(), 1)  # Default to Toshkent city if not found

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO technician_orders (user_id, region, abonent_id, address, media, longitude, latitude, description, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            user_id, region_id, abonent_id, address, media, longitude, latitude, description, 'in_controller'
        )
        return row["id"]
    finally:
        await conn.close()

# -----------------------------
# Connection order helpers
# -----------------------------

async def ensure_user(telegram_id: int, full_name: Optional[str], username: Optional[str]) -> asyncpg.Record:
    """Create user if not exists with sequential ID; return row."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Avval mavjud userni tekshirish
        existing_user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            telegram_id
        )
        
        if existing_user:
            # Mavjud userni yangilash
            row = await conn.fetchrow(
                """
                UPDATE users 
                SET full_name = $2, username = $3, updated_at = NOW()
                WHERE telegram_id = $1
                RETURNING *
                """,
                telegram_id, full_name, username
            )
            return row
        else:
            # Ketma-ket ID bilan yangi user yaratish
            row = await conn.fetchrow(
                """
                SELECT * FROM create_user_sequential($1, $2, $3, NULL, 'client'::user_role)
                """,
                telegram_id, username, full_name
            )
            return row
    finally:
        await conn.close()

def _tariff_code_to_name(code: str) -> str:
    mapping = {
        "tariff_xammasi_birga_4": "Hammasi birga 4",
        "tariff_xammasi_birga_3_plus": "Hammasi birga 3+",
        "tariff_xammasi_birga_3": "Hammasi birga 3",
        "tariff_xammasi_birga_2": "Hammasi birga 2",
    }
    return mapping.get(code, code)

async def get_or_create_tarif_by_code(code: str) -> int:
    """Return existing tarif id by code. Does NOT create new rows."""
    name = _tariff_code_to_name(code)
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        tid = await conn.fetchval("SELECT id FROM tarif WHERE name = $1", name)
        return tid
    finally:
        await conn.close()

async def create_connection_order(user_id: int, region: str, address: str, tarif_id: Optional[int], latitude: Optional[float], longitude: Optional[float]) -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO connection_orders (user_id, region, address, tarif_id, latitude, longitude, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            user_id, region, address, tarif_id, latitude, longitude, 'in_manager'
        )
        return row["id"]
    finally:
        await conn.close()

# -----------------------------
# Phone helpers
# -----------------------------

async def get_user_phone_by_telegram_id(telegram_id: int) -> Optional[str]:
    """Return user's phone by telegram_id or None."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval(
            "SELECT phone FROM users WHERE telegram_id = $1",
            telegram_id
        )
    finally:
        await conn.close()

async def update_user_phone_by_telegram_id(telegram_id: int, phone: str) -> bool:
    """Update user's phone by telegram_id; return True if updated."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        result = await conn.execute(
            "UPDATE users SET phone = $1 WHERE telegram_id = $2",
            phone, telegram_id
        )
        return result != 'UPDATE 0'
    finally:
        await conn.close()

# -----------------------------
# Order history helpers
# -----------------------------

async def get_user_orders_count(telegram_id: int) -> int:
    """Get total count of user orders (connection + technician orders)."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )
        if not user:
            return 0
        
        user_id = user['id']
        
        connection_count = await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE user_id = $1",
            user_id
        )
        
        technician_count = await conn.fetchval(
            "SELECT COUNT(*) FROM technician_orders WHERE user_id = $1",
            user_id
        )
        
        return (connection_count or 0) + (technician_count or 0)
    finally:
        await conn.close()

async def get_user_orders_paginated(telegram_id: int, offset: int = 0, limit: int = 1) -> list:
    """Get user orders with pagination (connection + technician orders)."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )
        if not user:
            return []
        
        user_id = user['id']
        
        # Union connection_orders va technician_orders
        orders = await conn.fetch(
            """
            (
                SELECT 
                    id, 
                    'connection' as order_type,
                    region::text as region,
                    address,
                    status::text as status,
                    created_at,
                    updated_at,
                    tarif_id,
                    NULL as abonent_id,
                    NULL as description
                FROM connection_orders 
                WHERE user_id = $1
            )
            UNION ALL
            (
                SELECT 
                    id,
                    'technician' as order_type,
                    region::text as region,
                    address,
                    status::text as status,
                    created_at,
                    updated_at,
                    NULL as tarif_id,
                    abonent_id,
                    description
                FROM technician_orders 
                WHERE user_id = $1
            )
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset
        )
        
        return orders
    finally:
        await conn.close()

async def create_smart_service_order(order_data: dict) -> int:
    """Create a smart service order in smart_service_orders table."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO smart_service_orders (user_id, category, service_type, address, latitude, longitude, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            order_data['user_id'], 
            order_data['category'], 
            order_data['service_type'], 
            order_data['address'], 
            order_data.get('latitude'), 
            order_data.get('longitude'),
            order_data.get('is_active', True)
        )
        return row["id"]
    finally:
        await conn.close()

async def get_smart_service_orders_by_user(user_id: int, limit: int = 10, offset: int = 0):
    """Get smart service orders for a specific user."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        orders = await conn.fetch(
            """
            SELECT 
                id,
                'smart_service' as order_type,
                category,
                service_type,
                address,
                created_at,
                updated_at
            FROM smart_service_orders 
            WHERE user_id = $1 AND is_active = true
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset
        )
        
        return orders
    finally:
        await conn.close()

