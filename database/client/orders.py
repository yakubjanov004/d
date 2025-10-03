import asyncpg
from config import settings
from typing import Optional

# Valid region names (matching database schema)
VALID_REGIONS = {
    'tashkent_city', 'tashkent_region', 'andijon', 'fergana', 
    'namangan', 'sirdaryo', 'jizzax', 'samarkand', 'bukhara',
    'navoi', 'kashkadarya', 'surkhandarya', 'khorezm', 'karakalpakstan'
}

def _tariff_code_to_name(code: str) -> str:
    mapping = {
        "tariff_xammasi_birga_4": "Hammasi birga 4",
        "tariff_xammasi_birga_3_plus": "Hammasi birga 3+",
        "tariff_xammasi_birga_3": "Hammasi birga 3",
        "tariff_xammasi_birga_2": "Hammasi birga 2",
    }
    return mapping.get(code, code)

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

async def get_or_create_tarif_by_code(code: str) -> int:
    """Return existing tarif id by code. Does NOT create new rows."""
    name = _tariff_code_to_name(code)
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        tid = await conn.fetchval("SELECT id FROM tarif WHERE name = $1", name)
        return tid
    finally:
        await conn.close()

async def create_service_order(user_id: int, region: str, abonent_id: str, address: str, description: str, media: str, geo: str, business_type: str = 'B2C') -> int:
    """Create a service order in technician_orders table.

    technician_orders schema:
      user_id BIGINT, region TEXT, abonent_id TEXT, address TEXT,
      media TEXT, longitude DOUBLE PRECISION, latitude DOUBLE PRECISION,
      description TEXT, status technician_order_status DEFAULT 'in_controller', ...
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

    # Validate and normalize region name
    region_normalized = region.lower().strip()
    if region_normalized not in VALID_REGIONS:
        region_normalized = 'tashkent_city'  # Default to Toshkent city if not found

    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Generate application number
        # Get next number for this business type
        next_num = await conn.fetchval(
            """
            SELECT COALESCE(MAX(
                CASE 
                    WHEN application_number ~ '^TECH-B2C-[0-9]+$' AND $1 = 'B2C' THEN 
                        CAST(SUBSTRING(application_number FROM 'TECH-B2C-([0-9]+)$') AS INTEGER)
                    WHEN application_number ~ '^TECH-B2B-[0-9]+$' AND $1 = 'B2B' THEN 
                        CAST(SUBSTRING(application_number FROM 'TECH-B2B-([0-9]+)$') AS INTEGER)
                    ELSE 0
                END
            ), 0) + 1
            FROM technician_orders 
            WHERE application_number IS NOT NULL
            """,
            business_type
        )
        
        application_number = f"TECH-{business_type}-{next_num:04d}"
        
        row = await conn.fetchrow(
            """
            INSERT INTO technician_orders (application_number, user_id, region, abonent_id, address, media, business_type, longitude, latitude, description, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
            """,
            application_number, user_id, region_normalized, abonent_id, address, media, business_type, longitude, latitude, description, 'in_controller'
        )
        return row["id"]
    finally:
        await conn.close()

async def create_connection_order(user_id: int, region: str, address: str, tarif_id: Optional[int], latitude: Optional[float], longitude: Optional[float], business_type: str = 'B2C') -> int:
    # Validate and normalize region name
    region_normalized = region.lower().strip()
    if region_normalized not in VALID_REGIONS:
        region_normalized = 'tashkent_city'  # Default to Toshkent city if not found
    
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Generate application number
        # Get next number for this business type
        next_num = await conn.fetchval(
            """
            SELECT COALESCE(MAX(
                CASE 
                    WHEN application_number ~ '^CONN-B2C-[0-9]+$' AND $1 = 'B2C' THEN 
                        CAST(SUBSTRING(application_number FROM 'CONN-B2C-([0-9]+)$') AS INTEGER)
                    WHEN application_number ~ '^CONN-B2B-[0-9]+$' AND $1 = 'B2B' THEN 
                        CAST(SUBSTRING(application_number FROM 'CONN-B2B-([0-9]+)$') AS INTEGER)
                    ELSE 0
                END
            ), 0) + 1
            FROM connection_orders 
            WHERE application_number IS NOT NULL
            """,
            business_type
        )
        
        application_number = f"CONN-{business_type}-{next_num:04d}"
        
        row = await conn.fetchrow(
            """
            INSERT INTO connection_orders (application_number, user_id, region, address, tarif_id, business_type, latitude, longitude, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            application_number, user_id, region_normalized, address, tarif_id, business_type, latitude, longitude, 'in_manager'
        )
        return row["id"]
    finally:
        await conn.close()

async def create_smart_service_order(order_data: dict) -> int:
    """Create a smart service order in smart_service_orders table."""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # Generate application number for smart service
        # Get next number for smart service orders
        next_num = await conn.fetchval(
            """
            SELECT COALESCE(MAX(
                CASE 
                    WHEN application_number ~ '^SMA-[0-9]+$' THEN 
                        CAST(SUBSTRING(application_number FROM 'SMA-([0-9]+)$') AS INTEGER)
                    ELSE 0
                END
            ), 0) + 1
            FROM smart_service_orders 
            WHERE application_number IS NOT NULL
            """
        )
        
        application_number = f"SMA-{next_num:04d}"
        
        row = await conn.fetchrow(
            """
            INSERT INTO smart_service_orders (application_number, user_id, category, service_type, address, latitude, longitude, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            application_number,
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
