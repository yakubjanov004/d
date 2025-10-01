import asyncpg
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import date, datetime
from config import settings

# ---------- FOYDALANUVCHILAR ----------
async def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    """Warehouse uchun alohida get_users_by_role funksiyasi"""
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, full_name, username, phone, telegram_id
            FROM users
            WHERE role = $1 AND COALESCE(is_blocked, FALSE) = FALSE
            ORDER BY full_name NULLS LAST, id
            """,
            role,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# ---------- MATERIALLAR ASOSIY CRUD / SELEKTLAR ----------
async def create_material(
    name: str,
    quantity: int,
    price: Optional[Decimal] = None,
    description: Optional[str] = None,
    serial_number: Optional[str] = None,
) -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO materials (name, price, description, quantity, serial_number, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            RETURNING id, name, price, description, quantity, serial_number, created_at, updated_at
            """,
            name, price, description, quantity, serial_number
        )
        return dict(row)
    finally:
        await conn.close()

async def search_materials(search_term: str) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, price, description, quantity, serial_number, created_at, updated_at
            FROM materials
            WHERE name ILIKE $1
            ORDER BY name
            LIMIT 20
            """,
            f"%{search_term}%"
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_all_materials() -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, price, description, quantity, serial_number, created_at, updated_at
            FROM materials
            ORDER BY name
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_material_by_id(material_id: int) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT id, name, price, description, quantity, serial_number, created_at, updated_at
            FROM materials
            WHERE id = $1
            """,
            material_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def update_material_quantity(material_id: int, additional_quantity: int) -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            UPDATE materials
            SET quantity = quantity + $2, updated_at = NOW()
            WHERE id = $1
            RETURNING id, name, price, description, quantity, serial_number, created_at, updated_at
            """,
            material_id, additional_quantity
        )
        return dict(row)
    finally:
        await conn.close()

async def update_material_name_description(material_id: int, name: str, description: Optional[str] = None) -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        row = await conn.fetchrow(
            """
            UPDATE materials
            SET name = $2, description = $3, updated_at = NOW()
            WHERE id = $1
            RETURNING id, name, price, description, quantity, serial_number, created_at, updated_at
            """,
            material_id, name, description
        )
        return dict(row)
    finally:
        await conn.close()

async def get_low_stock_materials(threshold: int = 10) -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, price, description, quantity, serial_number, created_at, updated_at
            FROM materials
            WHERE quantity <= $1
            ORDER BY quantity ASC, name
            """,
            threshold
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_out_of_stock_materials() -> List[Dict[str, Any]]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, price, description, quantity, serial_number, created_at, updated_at
            FROM materials
            WHERE quantity = 0
            ORDER BY name
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# ---------- STATISTIKA BOSHLANG'ICH KO'RSATKICHLAR ----------

async def get_warehouse_head_counters() -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        total_materials = await conn.fetchval("SELECT COUNT(*) FROM materials")
        total_quantity = await conn.fetchval("SELECT COALESCE(SUM(quantity),0) FROM materials")
        total_value = await conn.fetchval("SELECT COALESCE(SUM(quantity * COALESCE(price,0)),0) FROM materials")
        low_stock_count = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE quantity <= 10")
        out_of_stock_count = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE quantity = 0")
        # aylanish (mock, joriy oy qo'shilganlarga qarab foiz)
        weekly_added = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE created_at >= date_trunc('week', CURRENT_DATE)")
        turnover_rate = min(100, (weekly_added or 0) * 5)  # ko‘rsatkich uchun oddiy formula
        turnover_rate_week = turnover_rate

        top_stock_material = await conn.fetchrow("SELECT name, quantity FROM materials ORDER BY quantity DESC LIMIT 1")
        most_expensive = await conn.fetchrow("SELECT name, price FROM materials WHERE price IS NOT NULL ORDER BY price DESC LIMIT 1")

        return {
            "total_materials": int(total_materials or 0),
            "total_quantity": int(total_quantity or 0),
            "total_value": float(total_value or 0),
            "low_stock_count": int(low_stock_count or 0),
            "out_of_stock_count": int(out_of_stock_count or 0),
            "turnover_rate": int(turnover_rate),
            "turnover_rate_week": int(turnover_rate_week),
            "top_stock_material": dict(top_stock_material) if top_stock_material else None,
            "most_expensive": dict(most_expensive) if most_expensive else None,
        }
    finally:
        await conn.close()

async def get_warehouse_daily_statistics(date_str: str | None = None) -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if date_str:
            daily_added = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE DATE(created_at) = $1", date_str)
            daily_updated = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE DATE(updated_at) = $1", date_str)
        else:
            daily_added = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE DATE(created_at) = CURRENT_DATE")
            daily_updated = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE DATE(updated_at) = CURRENT_DATE")
        return {"daily_added": int(daily_added or 0), "daily_updated": int(daily_updated or 0)}
    finally:
        await conn.close()

async def get_warehouse_weekly_statistics() -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        weekly_added = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE created_at >= date_trunc('week', CURRENT_DATE)")
        weekly_updated = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE updated_at >= date_trunc('week', CURRENT_DATE)")
        weekly_value = await conn.fetchval("SELECT COALESCE(SUM(quantity * COALESCE(price,0)),0) FROM materials WHERE created_at >= date_trunc('week', CURRENT_DATE)")
        return {
            "weekly_added": int(weekly_added or 0),
            "weekly_updated": int(weekly_updated or 0),
            "weekly_value": float(weekly_value or 0),
        }
    finally:
        await conn.close()

async def get_warehouse_monthly_statistics() -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        monthly_added = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE created_at >= date_trunc('month', CURRENT_DATE)")
        monthly_updated = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE updated_at >= date_trunc('month', CURRENT_DATE)")
        monthly_value = await conn.fetchval("SELECT COALESCE(SUM(quantity * COALESCE(price,0)),0) FROM materials WHERE created_at >= date_trunc('month', CURRENT_DATE)")
        top_materials = await conn.fetch("SELECT name, quantity FROM materials ORDER BY quantity DESC LIMIT 5")
        return {
            "monthly_added": int(monthly_added or 0),
            "monthly_updated": int(monthly_updated or 0),
            "monthly_value": float(monthly_value or 0),
            "top_materials": [dict(r) for r in top_materials],
        }
    finally:
        await conn.close()

async def get_warehouse_yearly_statistics() -> Dict[str, Any]:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        yearly_added = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE created_at >= date_trunc('year', CURRENT_DATE)")
        yearly_updated = await conn.fetchval("SELECT COUNT(*) FROM materials WHERE updated_at >= date_trunc('year', CURRENT_DATE)")
        yearly_value = await conn.fetchval("SELECT COALESCE(SUM(quantity * COALESCE(price,0)),0) FROM materials WHERE created_at >= date_trunc('year', CURRENT_DATE)")
        return {
            "yearly_added": int(yearly_added or 0),
            "yearly_updated": int(yearly_updated or 0),
            "yearly_value": float(yearly_value or 0),
        }
    finally:
        await conn.close()

# ---------- Moliyaviy hisobot / Range statistikalar ----------

async def get_warehouse_financial_report() -> Dict[str, Any]:
    """
    Minimum talab: rasmga o‘xshash ko‘rsatkichlar.
    in_count: shu oy yaratilgan materiallar quantity yig‘indisi (taxminiy kirim)
    out_count: 0 (log jadvallari bo‘lmasa), yoki quantity kamayganlarini aniqlash uchun keyingi bosqichda
    total_value_month: shu oy created bo‘lganlar quantity*price yig‘indisi
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        in_count = await conn.fetchval(
            "SELECT COALESCE(SUM(quantity),0) FROM materials WHERE created_at >= date_trunc('month', CURRENT_DATE)"
        )
        total_value_month = await conn.fetchval(
            "SELECT COALESCE(SUM(quantity * COALESCE(price,0)),0) FROM materials WHERE created_at >= date_trunc('month', CURRENT_DATE)"
        )
        out_count = 0  # agar harakatlar jadvallari yo‘q bo‘lsa, nolga tenglaymiz
        return {
            "in_count": int(in_count or 0),
            "out_count": int(out_count),
            "total_value_month": float(total_value_month or 0),
        }
    finally:
        await conn.close()

# Add the missing function
async def get_warehouse_statistics() -> Dict[str, Any]:
    """
    Alias for get_warehouse_head_counters to maintain compatibility
    """
    return await get_warehouse_head_counters()

async def get_warehouse_range_statistics(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Interval bo'yicha: [start_date, end_date]
    """
    from datetime import datetime
    
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        # String sanalarni datetime obyektlariga o'tkazish
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        added = await conn.fetchval(
            "SELECT COUNT(*) FROM materials WHERE DATE(created_at) BETWEEN $1 AND $2",
            start_dt, end_dt
        )
        updated = await conn.fetchval(
            "SELECT COUNT(*) FROM materials WHERE DATE(updated_at) BETWEEN $1 AND $2",
            start_dt, end_dt
        )
        value = await conn.fetchval(
            "SELECT COALESCE(SUM(quantity * COALESCE(price,0)),0) FROM materials WHERE DATE(created_at) BETWEEN $1 AND $2",
            start_dt, end_dt
        )
        return {"added": int(added or 0), "updated": int(updated or 0), "value": float(value or 0)}
    finally:
        await conn.close()

# ========== EXPORT QUERIES ==========

async def get_warehouse_inventory_for_export() -> List[Dict[str, Any]]:
    """
    Export uchun barcha inventarizatsiya ma'lumotlarini olish
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        query = """
        SELECT 
            id,
            name,
            quantity,
            price,
            serial_number,
            description,
            created_at,
            updated_at
        FROM materials 
        ORDER BY name ASC
        """
        
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    finally:
        await conn.close()

# ---------- MATERIAL BERISH FUNKSIYASI ----------
async def give_material_to_technician(user_id: int, material_id: int, quantity: int) -> Dict[str, Any]:
    """
    Texnikga material berish funksiyasi.
    Xavfsiz UPSERT va manfiy miqdordan himoyalanish bilan.
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        async with conn.transaction():
            # Xavfsiz material yangilash va texnikga berish
            result = await conn.fetchrow(
                """
                WITH upd AS (
                    UPDATE materials 
                    SET quantity = quantity - $3
                    WHERE id = $2 AND quantity >= $3
                    RETURNING id, name, quantity
                )
                INSERT INTO material_and_technician (user_id, material_id, quantity)
                SELECT $1, $2, $3
                FROM upd
                ON CONFLICT (user_id, material_id)
                DO UPDATE SET quantity = material_and_technician.quantity + EXCLUDED.quantity
                RETURNING (SELECT name FROM materials WHERE id = $2) as material_name,
                         quantity as given_quantity;
                """,
                user_id, material_id, quantity
            )
            
            if not result:
                # Omborda yetarli material yo'q
                material_info = await conn.fetchrow(
                    "SELECT name, quantity FROM materials WHERE id = $1",
                    material_id
                )
                if material_info:
                    raise ValueError(f"Omborda yetarli {material_info['name']} yo'q. Mavjud: {material_info['quantity']}")
                else:
                    raise ValueError("Material topilmadi")
            
            return {
                "success": True,
                "material_name": result["material_name"],
                "given_quantity": result["given_quantity"],
                "message": f"{result['material_name']} materialidan {quantity} dona texnikga berildi"
            }
    finally:
        await conn.close()

async def get_technician_materials(user_id: int) -> List[Dict[str, Any]]:
    """
    Texnikda mavjud materiallar ro'yxatini olish
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT 
                mt.material_id,
                m.name as material_name,
                mt.quantity,
                m.description,
                mt.created_at,
                mt.updated_at
            FROM material_and_technician mt
            JOIN materials m ON m.id = mt.material_id
            WHERE mt.user_id = $1 AND mt.quantity > 0
            ORDER BY m.name
            """,
            user_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_warehouse_statistics_for_export(period: str = 'all') -> List[Dict[str, Any]]:
    """
    Export uchun statistika ma'lumotlarini olish
    period: 'daily', 'weekly', 'monthly', 'yearly', 'all'
    """
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        statistics_data = []
        
        if period in ['daily', 'all']:
            # Kunlik statistika
            daily_stats = await get_warehouse_daily_statistics()
            statistics_data.extend([
                {'metric': 'Kunlik Qo\'shilgan Materiallar', 'value': daily_stats['daily_added'], 'period': 'Kunlik', 'date': datetime.now().date()},
                {'metric': 'Kunlik Yangilangan Materiallar', 'value': daily_stats['daily_updated'], 'period': 'Kunlik', 'date': datetime.now().date()}
            ])
        
        if period in ['weekly', 'all']:
            # Haftalik statistika
            weekly_stats = await get_warehouse_weekly_statistics()
            statistics_data.extend([
                {'metric': 'Haftalik Qo\'shilgan Materiallar', 'value': weekly_stats['weekly_added'], 'period': 'Haftalik', 'date': datetime.now().date()},
                {'metric': 'Haftalik Yangilangan Materiallar', 'value': weekly_stats['weekly_updated'], 'period': 'Haftalik', 'date': datetime.now().date()},
                {'metric': 'Haftalik Umumiy Qiymat', 'value': f"{weekly_stats['weekly_value']:.2f}", 'period': 'Haftalik', 'date': datetime.now().date()}
            ])
        
        if period in ['monthly', 'all']:
            # Oylik statistika
            monthly_stats = await get_warehouse_monthly_statistics()
            statistics_data.extend([
                {'metric': 'Oylik Qo\'shilgan Materiallar', 'value': monthly_stats['monthly_added'], 'period': 'Oylik', 'date': datetime.now().date()},
                {'metric': 'Oylik Yangilangan Materiallar', 'value': monthly_stats['monthly_updated'], 'period': 'Oylik', 'date': datetime.now().date()},
                {'metric': 'Oylik Umumiy Qiymat', 'value': f"{monthly_stats['monthly_value']:.2f}", 'period': 'Oylik', 'date': datetime.now().date()}
            ])
        
        if period in ['yearly', 'all']:
            # Yillik statistika
            yearly_stats = await get_warehouse_yearly_statistics()
            statistics_data.extend([
                {'metric': 'Yillik Qo\'shilgan Materiallar', 'value': yearly_stats['yearly_added'], 'period': 'Yillik', 'date': datetime.now().date()},
                {'metric': 'Yillik Yangilangan Materiallar', 'value': yearly_stats['yearly_updated'], 'period': 'Yillik', 'date': datetime.now().date()},
                {'metric': 'Yillik Umumiy Qiymat', 'value': f"{yearly_stats['yearly_value']:.2f}", 'period': 'Yillik', 'date': datetime.now().date()}
            ])
        
        # Umumiy statistika
        if period == 'all':
            head_stats = await get_warehouse_head_counters()
            statistics_data.extend([
                {'metric': 'Total Materials Count', 'value': head_stats['total_materials'], 'period': 'Overall', 'date': datetime.now().date()},
                {'metric': 'Total Inventory Value', 'value': f"{head_stats['total_value']:.2f}", 'period': 'Overall', 'date': datetime.now().date()},
                {'metric': 'Low Stock Count', 'value': head_stats['low_stock_count'], 'period': 'Overall', 'date': datetime.now().date()},
                {'metric': 'Out of Stock Count', 'value': head_stats['out_of_stock_count'], 'period': 'Overall', 'date': datetime.now().date()}
            ])
        
        return statistics_data
    finally:
        await conn.close()





async def get_warehouse_materials_by_date_range_for_export(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Export uchun ma'lum vaqt oralig'idagi materiallar ro'yxatini olish
    """
    from datetime import datetime
    
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        query = """
        SELECT 
            id,
            name,
            quantity,
            price,
            serial_number,
            description,
            created_at,
            updated_at
        FROM materials 
        WHERE DATE(created_at) BETWEEN $1 AND $2
        ORDER BY created_at DESC, name ASC
        """
        
        rows = await conn.fetch(query, start_dt, end_dt)
        return [dict(row) for row in rows]
    finally:
        await conn.close()
