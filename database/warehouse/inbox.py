# database/warehouse/inbox.py
import asyncpg
from typing import List, Dict, Any, Optional
from config import settings

async def _conn():
    """Database connection helper"""
    return await asyncpg.connect(settings.DB_URL)

# ==================== CONNECTION ORDERS ====================

async def fetch_warehouse_connection_orders(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Omborda turgan ulanish arizalari (connection_orders) - status: 'in_warehouse'
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                co.id,
                co.address,
                co.region,
                co.status,
                co.created_at,
                co.updated_at,
                co.jm_notes,
                u.full_name AS client_name,
                u.phone AS client_phone,
                u.telegram_id AS client_telegram_id,
                t.name AS tariff_name
            FROM connection_orders co
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE co.status = 'in_warehouse'
              AND co.is_active = TRUE
            ORDER BY co.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def fetch_warehouse_connection_orders_with_materials(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Ombordan material so'ralgan ulanish arizalari
    YANGI: Status tekshirmaydi, faqat material_requests mavjudligini tekshiradi
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT
                co.id,
                co.application_number,
                co.address,
                co.region,
                co.status,
                co.created_at,
                co.updated_at,
                co.jm_notes,
                u.full_name AS client_name,
                u.phone AS client_phone,
                u.telegram_id AS client_telegram_id,
                t.name AS tariff_name,
                COUNT(mr.id) as material_count
            FROM material_requests mr
            JOIN connection_orders co ON co.id = mr.applications_id
            LEFT JOIN users u ON u.id = co.user_id
            LEFT JOIN tarif t ON t.id = co.tarif_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND co.is_active = TRUE
            GROUP BY co.id, co.application_number, co.address, co.region, co.status, co.created_at, co.updated_at, 
                     co.jm_notes, u.full_name, u.phone, u.telegram_id, t.name
            ORDER BY co.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def count_warehouse_connection_orders_with_materials() -> int:
    """
    Ombordan material so'ralgan ulanish arizalari soni
    YANGI: Status tekshirmaydi, faqat tasdiqlash kutayotgan materiallar
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT co.id)
            FROM material_requests mr
            JOIN connection_orders co ON co.id = mr.applications_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND co.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

async def count_warehouse_technician_orders() -> int:
    """
    Ombordan material so'ralgan texnik arizalari soni
    YANGI: Status tekshirmaydi, faqat tasdiqlash kutayotgan materiallar
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT t_orders.id)
            FROM material_requests mr
            JOIN technician_orders t_orders ON t_orders.id = mr.applications_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND t_orders.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

async def count_warehouse_staff_orders() -> int:
    """
    Ombordan material so'ralgan xodim arizalari soni
    YANGI: Status tekshirmaydi, faqat tasdiqlash kutayotgan materiallar
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT so.id)
            FROM material_requests mr
            JOIN staff_orders so ON so.id = mr.applications_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND so.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

async def fetch_materials_for_connection_order(connection_order_id: int) -> List[Dict[str, Any]]:
    """
    Ulanish arizasi uchun materiallar ro'yxati
    YANGI: Faqat source_type='warehouse' bo'lgan materiallarni ko'rsatadi
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.material_id,
                m.name as material_name,
                mr.quantity,
                COALESCE(m.price, 0) as price,
                mr.total_price,
                mr.source_type,
                COALESCE(mr.warehouse_approved, false) as warehouse_approved
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            WHERE mr.applications_id = $1
              AND mr.source_type = 'warehouse'
            ORDER BY m.name
            """,
            connection_order_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# ==================== TECHNICIAN ORDERS ====================

async def fetch_warehouse_technician_orders(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Ombordan material so'ralgan texnik arizalari
    YANGI: Status tekshirmaydi, faqat material_requests mavjudligini tekshiradi
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT
                t_orders.id,
                t_orders.application_number,
                t_orders.address,
                t_orders.region,
                t_orders.status,
                t_orders.created_at,
                t_orders.updated_at,
                t_orders.description,
                t_orders.media,
                u.full_name AS client_name,
                u.phone AS client_phone,
                u.telegram_id AS client_telegram_id
            FROM material_requests mr
            JOIN technician_orders t_orders ON t_orders.id = mr.applications_id
            LEFT JOIN users u ON u.id = t_orders.user_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND t_orders.is_active = TRUE
            GROUP BY t_orders.id, t_orders.application_number, t_orders.address, t_orders.region, t_orders.status,
                     t_orders.created_at, t_orders.updated_at, t_orders.description, t_orders.media,
                     u.full_name, u.phone, u.telegram_id
            ORDER BY t_orders.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def fetch_warehouse_technician_orders_with_materials(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Omborda turgan texnik arizalari materiallar bilan
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT
                t_orders.id,
                t_orders.address,
                t_orders.region,
                t_orders.status,
                t_orders.created_at,
                t_orders.updated_at,
                t_orders.description,
                t_orders.media,
                u.full_name AS client_name,
                u.phone AS client_phone,
                u.telegram_id AS client_telegram_id,
                COUNT(mr.id) as material_count
            FROM technician_orders t_orders
            LEFT JOIN users u ON u.id = t_orders.user_id
            LEFT JOIN material_requests mr ON mr.applications_id = t_orders.id
            WHERE t_orders.status = 'in_warehouse'
              AND t_orders.is_active = TRUE
            GROUP BY t_orders.id, t_orders.address, t_orders.region, t_orders.status, t_orders.created_at, t_orders.updated_at, 
                     t_orders.description, t_orders.media, u.full_name, u.phone, u.telegram_id
            ORDER BY t_orders.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def count_warehouse_technician_orders_with_materials() -> int:
    """
    Ombordan material so'ralgan texnik arizalari soni
    YANGI: Status tekshirmaydi, faqat tasdiqlash kutayotgan materiallar
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT t_orders.id)
            FROM material_requests mr
            JOIN technician_orders t_orders ON t_orders.id = mr.applications_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND t_orders.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

async def fetch_materials_for_technician_order(technician_order_id: int) -> List[Dict[str, Any]]:
    """
    Texnik arizasi uchun materiallar ro'yxati
    YANGI: Faqat source_type='warehouse' bo'lgan materiallarni ko'rsatadi
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.material_id,
                m.name as material_name,
                mr.quantity,
                COALESCE(m.price, 0) as price,
                mr.total_price,
                mr.source_type,
                COALESCE(mr.warehouse_approved, false) as warehouse_approved
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            WHERE mr.applications_id = $1
              AND mr.source_type = 'warehouse'
            ORDER BY m.name
            """,
            technician_order_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# ==================== STAFF ORDERS ====================

async def fetch_warehouse_staff_orders(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Ombordan material so'ralgan xodim arizalari
    YANGI: Status tekshirmaydi, faqat material_requests mavjudligini tekshiradi
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT
                so.id,
                so.application_number,
                so.address,
                so.region,
                so.status,
                so.created_at,
                so.updated_at,
                so.description,
                so.type_of_zayavka,
                u.full_name AS client_name,
                u.phone AS client_phone,
                u.telegram_id AS client_telegram_id
            FROM material_requests mr
            JOIN staff_orders so ON so.id = mr.applications_id
            LEFT JOIN users u ON u.id = so.user_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND so.is_active = TRUE
            GROUP BY so.id, so.application_number, so.address, so.region, so.status,
                     so.created_at, so.updated_at, so.description, so.type_of_zayavka,
                     u.full_name, u.phone, u.telegram_id
            ORDER BY so.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def fetch_warehouse_staff_orders_with_materials(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Omborda turgan xodim arizalari materiallar bilan
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT
                so.id,
                so.application_number,
                so.address,
                so.region,
                so.status,
                so.created_at,
                so.updated_at,
                so.description,
                so.phone,
                so.abonent_id,
                u.full_name AS client_name,
                u.phone AS client_phone,
                u.telegram_id AS client_telegram_id,
                COUNT(mr.id) as material_count
            FROM staff_orders so
            LEFT JOIN users u ON u.id = so.user_id
            LEFT JOIN material_requests mr ON mr.applications_id = so.id
            WHERE so.status = 'in_warehouse'
              AND so.is_active = TRUE
            GROUP BY so.id, so.application_number, so.address, so.region, so.status, so.created_at, so.updated_at, 
                     so.description, so.phone, so.abonent_id, u.full_name, u.phone, u.telegram_id
            ORDER BY so.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def count_warehouse_staff_orders_with_materials() -> int:
    """
    Ombordan material so'ralgan xodim arizalari soni
    YANGI: Status tekshirmaydi, faqat tasdiqlash kutayotgan materiallar
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT so.id)
            FROM material_requests mr
            JOIN staff_orders so ON so.id = mr.applications_id
            WHERE mr.source_type = 'warehouse'
              AND COALESCE(mr.warehouse_approved, false) = false
              AND so.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

async def fetch_materials_for_staff_order(staff_order_id: int) -> List[Dict[str, Any]]:
    """
    Xodim arizasi uchun materiallar ro'yxati
    YANGI: Faqat source_type='warehouse' bo'lgan materiallarni ko'rsatadi
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.material_id,
                m.name as material_name,
                mr.quantity,
                COALESCE(m.price, 0) as price,
                mr.total_price,
                mr.source_type,
                COALESCE(mr.warehouse_approved, false) as warehouse_approved
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            WHERE mr.applications_id = $1
              AND mr.source_type = 'warehouse'
            ORDER BY m.name
            """,
            staff_order_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

# ==================== MATERIAL REQUESTS ====================

async def fetch_material_requests_by_connection_orders(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Ulanish arizalari uchun material so'rovlari
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.id,
                mr.applications_id,
                mr.material_id,
                mr.quantity,
                mr.price,
                mr.total_price,
                mr.created_at,
                m.name as material_name,
                co.address,
                co.region,
                u.full_name as client_name
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            JOIN connection_orders co ON co.id = mr.applications_id
            LEFT JOIN users u ON u.id = co.user_id
            WHERE co.status = 'in_warehouse'
              AND co.is_active = TRUE
            ORDER BY co.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def fetch_material_requests_by_technician_orders(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Texnik arizalari uchun material so'rovlari
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.id,
                mr.applications_id,
                mr.material_id,
                mr.quantity,
                mr.price,
                mr.total_price,
                mr.created_at,
                m.name as material_name,
                t_orders.address,
                t_orders.region,
                u.full_name as client_name
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            JOIN technician_orders t_orders ON t_orders.id = mr.applications_id
            LEFT JOIN users u ON u.id = t_orders.user_id
            WHERE t_orders.status = 'in_warehouse'
              AND t_orders.is_active = TRUE
            ORDER BY t_orders.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def fetch_material_requests_by_staff_orders(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Xodim arizalari uchun material so'rovlari
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.id,
                mr.applications_id,
                mr.material_id,
                mr.quantity,
                mr.price,
                mr.total_price,
                mr.created_at,
                m.name as material_name,
                so.address,
                so.region,
                u.full_name as client_name
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            JOIN staff_orders so ON so.id = mr.applications_id
            LEFT JOIN users u ON u.id = so.user_id
            WHERE so.status = 'in_warehouse'
              AND so.is_active = TRUE
            ORDER BY so.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def count_material_requests_by_connection_orders() -> int:
    """
    Ulanish arizalari uchun material so'rovlari soni
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM material_requests mr
            JOIN connection_orders co ON co.id = mr.applications_id
            WHERE co.status = 'in_warehouse'
              AND co.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

async def count_material_requests_by_technician_orders() -> int:
    """
    Texnik arizalari uchun material so'rovlari soni
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM material_requests mr
            JOIN technician_orders t_orders ON t_orders.id = mr.applications_id
            WHERE t_orders.status = 'in_warehouse'
              AND t_orders.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

async def count_material_requests_by_staff_orders() -> int:
    """
    Xodim arizalari uchun material so'rovlari soni
    """
    conn = await _conn()
    try:
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM material_requests mr
            JOIN staff_orders so ON so.id = mr.applications_id
            WHERE so.status = 'in_warehouse'
              AND so.is_active = TRUE
            """
        )
        return int(count or 0)
    finally:
        await conn.close()

# ---------- AGGREGATE COUNT FUNCTIONS ----------

async def get_all_material_requests_count() -> Dict[str, int]:
    """Get counts for all material request types"""
    conn = await _conn()
    try:
        connection_count = await count_material_requests_by_connection_orders()
        technician_count = await count_material_requests_by_technician_orders()
        staff_count = await count_material_requests_by_staff_orders()
        
        return {
            'connection_orders': connection_count,
            'technician_orders': technician_count,
            'staff_orders': staff_count,
            'total': connection_count + technician_count + staff_count
        }
    finally:
        await conn.close()

async def get_all_warehouse_orders_count() -> Dict[str, int]:
    """Get counts for all warehouse order types"""
    conn = await _conn()
    try:
        connection_count = await count_warehouse_connection_orders_with_materials()
        technician_count = await count_warehouse_technician_orders_with_materials()
        staff_count = await count_warehouse_staff_orders_with_materials()
        
        return {
            'connection_orders': connection_count,
            'technician_orders': technician_count,
            'staff_orders': staff_count,
            'total': connection_count + technician_count + staff_count
        }
    finally:
        await conn.close()

# ==================== HELPER FUNCTIONS ====================

async def create_material_and_technician_entry(order_id: int, order_type: str) -> bool:
    """
    Ariza tasdiqlangandan so'ng material_and_technician jadvaliga yozish
    """
    conn = await _conn()
    try:
        # Order type ga qarab material_requests dan materiallarni olish
        if order_type == "connection":
            table_name = "connection_orders"
        elif order_type == "technician":
            table_name = "technician_orders"
        elif order_type == "staff":
            table_name = "staff_orders"
        else:
            return False
        
        # Texnik ID ni olish
        technician_id = await conn.fetchval(
            f"""
            SELECT user_id 
            FROM {table_name} 
            WHERE id = $1
            """,
            order_id
        )
        
        if not technician_id:
            print(f"No technician_id found for {order_type} order {order_id}")
            return False
        
        # Material requests dan materiallarni olish
        material_requests = await conn.fetch(
            """
            SELECT mr.material_id, mr.quantity, mr.applications_id, mr.source_type
            FROM material_requests mr
            WHERE mr.applications_id = $1
            """,
            order_id
        )
        
        if not material_requests:
            print(f"No material requests found for {order_type} order {order_id}")
            return True  # Material yo'q bo'lsa ham tasdiqlash muvaffaqiyatli
        
        # Har bir material uchun material_and_technician ga yozish
        for mr in material_requests:
            material_id = mr['material_id']
            quantity = mr['quantity']
            source_type = mr.get('source_type', 'warehouse')
            
            # Faqat ombordan so'ralgan materiallarni texnikka qo'shish va ombor zaxirasini kamaytirish
            if source_type == 'warehouse':
                # UPSERT - agar mavjud bo'lsa quantity ni qo'shish, yo'q bo'lsa yangi yaratish
                await conn.execute(
                    """
                    INSERT INTO material_and_technician (user_id, material_id, quantity)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, material_id) 
                    DO UPDATE SET quantity = material_and_technician.quantity + $3
                    """,
                    technician_id, material_id, quantity
                )
                
                # Ombor zaxirasini kamaytirish
                await conn.execute(
                    """
                    UPDATE materials 
                    SET quantity = GREATEST(0, quantity - $1)
                    WHERE id = $2
                    """,
                    quantity, material_id
                )
            
            # warehouse_approved ni TRUE qilish
            await conn.execute(
                """
                UPDATE material_requests 
                SET warehouse_approved = TRUE
                WHERE applications_id = $1 AND material_id = $2
                """,
                order_id, material_id
            )
        
        return True
    except Exception as e:
        print(f"Error creating material_and_technician entries: {e}")
        return False
    finally:
        await conn.close()

# ==================== CONFIRMATION FUNCTIONS ====================

async def confirm_materials_and_update_status_for_connection(order_id: int, warehouse_user_id: int) -> bool:
    """
    Ulanish arizasi uchun materiallarni tasdiqlash
    YANGI: Status O'ZGARMAYDI! Faqat materiallarni texnikka berish va ombor zaxirasini kamaytirish
    """
    conn = await _conn()
    try:
        # STATUS O'ZGARMAYDI! Texnik allaqachon in_technician_work da davom etmoqda
        # Faqat materiallarni texnikka beramiz
        
        # Material_and_technician jadvaliga yozish va ombor zaxirasini kamaytirish
        success = await create_material_and_technician_entry(order_id, "connection")
        if not success:
            print(f"Failed to create material_and_technician entries for connection order {order_id}")
        
        return True
    except Exception as e:
        print(f"Error confirming connection order materials: {e}")
        return False
    finally:
        await conn.close()

async def confirm_materials_and_update_status_for_technician(order_id: int, warehouse_user_id: int) -> bool:
    """
    Texnik arizasi uchun materiallarni tasdiqlash
    YANGI: Status O'ZGARMAYDI! Faqat materiallarni texnikka berish va ombor zaxirasini kamaytirish
    """
    conn = await _conn()
    try:
        # STATUS O'ZGARMAYDI! Texnik allaqachon in_technician_work da davom etmoqda
        # Faqat materiallarni texnikka beramiz
        
        # Material_and_technician jadvaliga yozish va ombor zaxirasini kamaytirish
        success = await create_material_and_technician_entry(order_id, "technician")
        if not success:
            print(f"Failed to create material_and_technician entries for technician order {order_id}")
        
        return True
    except Exception as e:
        print(f"Error confirming technician order materials: {e}")
        return False
    finally:
        await conn.close()

async def confirm_materials_and_update_status_for_staff(order_id: int, warehouse_user_id: int) -> bool:
    """
    Xodim arizasi uchun materiallarni tasdiqlash
    YANGI: Status O'ZGARMAYDI! Faqat materiallarni texnikka berish va ombor zaxirasini kamaytirish
    """
    conn = await _conn()
    try:
        # STATUS O'ZGARMAYDI! Texnik allaqachon in_technician_work da davom etmoqda
        # Faqat materiallarni texnikka beramiz
        
        # Material_and_technician jadvaliga yozish va ombor zaxirasini kamaytirish
        success = await create_material_and_technician_entry(order_id, "staff")
        if not success:
            print(f"Failed to create material_and_technician entries for staff order {order_id}")
        
        return True
    except Exception as e:
        print(f"Error confirming staff order materials: {e}")
        return False
    finally:
        await conn.close()