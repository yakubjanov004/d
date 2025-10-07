# database/technician/materials.py
import asyncpg
from typing import List, Dict, Any, Optional
from config import settings


# ----------------- YORDAMCHI -----------------
async def _conn():
    return await asyncpg.connect(settings.DB_URL)

def _as_dicts(rows):
    return [dict(r) for r in rows]


# ======================= MATERIALLAR (SELECTION) =======================
async def fetch_technician_materials(user_id: int = None, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    conn = await _conn()
    try:
        if user_id is not None:
            rows = await conn.fetch(
                """
                SELECT
                  m.id          AS material_id,
                  m.name,
                  m.price,
                  m.serial_number,
                  t.quantity    AS stock_quantity
                FROM material_and_technician t
                JOIN materials m ON m.id = t.material_id
                WHERE t.user_id = $1
                  AND t.quantity > 0
                ORDER BY m.name
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                  m.id          AS material_id,
                  m.name,
                  m.price,
                  m.serial_number,
                  t.quantity    AS stock_quantity
                FROM material_and_technician t
                JOIN materials m ON m.id = t.material_id
                WHERE t.quantity > 0
                ORDER BY m.name
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
        return _as_dicts(rows)
    finally:
        await conn.close()


async def fetch_all_materials(limit: int = 200, offset: int = 0) -> list[dict]:
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                m.id   AS material_id,
                m.name,
                COALESCE(m.price, 0) AS price
            FROM materials m
            ORDER BY m.name
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def fetch_materials_not_assigned_to_technician(user_id: int, limit: int = 200, offset: int = 0) -> list[dict]:
    """
    Materials jadvalida bor lekin material_technician jadvalida yo'q bo'lgan materiallarni olish.
    Ya'ni texnikka biriktirilmagan materiallar.
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                m.id AS material_id,
                m.name,
                COALESCE(m.price, 0) AS price,
                COALESCE(m.quantity, 0) AS stock_quantity
            FROM materials m
            LEFT JOIN material_and_technician mt ON m.id = mt.material_id AND mt.user_id = $1
            WHERE mt.material_id IS NULL
            ORDER BY m.name
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def fetch_material_by_id(material_id: int) -> Optional[Dict[str, Any]]:
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            "SELECT id, name, price, serial_number FROM materials WHERE id=$1",
            material_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def fetch_assigned_qty(user_id: int, material_id: int) -> int:
    """Texnikka biriktirilgan joriy qoldiq."""
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            """
            SELECT COALESCE(quantity, 0) AS qty
            FROM material_and_technician
            WHERE user_id = $1 AND material_id = $2
            """,
            user_id, material_id
        )
        return int(row["qty"]) if row else 0
    finally:
        await conn.close()


# --- MUHIM: Tanlovni jamlamay, aynan o'rnatuvchi upsert (OVERWRITE) ---

async def _has_column(conn, table: str, column: str) -> bool:
    """
    Checks if a column exists in a given table.
    """
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = $1 AND column_name = $2
        )
    """
    return await conn.fetchval(sql, table, column)

async def upsert_material_selection(
    user_id: int,
    applications_id: int,
    material_id: int,
    qty: int,
) -> None:
    """
    Tanlangan miqdorni to'g'ridan-to'g'ri o'rnatadi (jamlamaydi).
    material_requests da UNIQUE (user_id, applications_id, material_id) tavsiya etiladi.
    """
    if qty <= 0:
        raise ValueError("Miqdor 0 dan katta bo'lishi kerak")

    conn = await _conn()
    try:
        async with conn.transaction():
            price = await conn.fetchval(
                "SELECT COALESCE(price, 0) FROM materials WHERE id=$1",
                material_id
            ) or 0
            total = price * qty

            has_updated_at = await _has_column(conn, "material_requests", "updated_at")

            # Check if record exists first
            existing_record = await conn.fetchrow(
                "SELECT id FROM material_requests WHERE user_id = $1 AND applications_id = $2 AND material_id = $3",
                user_id, applications_id, material_id
            )

            if existing_record:
                # Update existing record
                if has_updated_at:
                    await conn.execute(
                        """
                        UPDATE material_requests 
                        SET quantity = $1, price = $2, total_price = $3, updated_at = NOW()
                        WHERE id = $4
                        """,
                        qty, price, total, existing_record['id']
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE material_requests 
                        SET quantity = $1, price = $2, total_price = $3
                        WHERE id = $4
                        """,
                        qty, price, total, existing_record['id']
                    )
            else:
                # Insert new record
                if has_updated_at:
                    await conn.execute(
                        """
                        INSERT INTO material_requests (user_id, applications_id, material_id, quantity, price, total_price, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        """,
                        user_id, applications_id, material_id, qty, price, total
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO material_requests (user_id, applications_id, material_id, quantity, price, total_price)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        user_id, applications_id, material_id, qty, price, total
                    )
    except Exception as e:
        # Re-raise with more context
        raise Exception(f"Material selection upsert failed: {str(e)}")
    finally:
        await conn.close()


# Orqa-ward compat: eski nomli funksiya ham shu mantiqqa yo'naltiriladi
async def upsert_material_request_and_decrease_stock(
    user_id: int,
    applications_id: int,
    material_id: int,
    add_qty: int,
) -> None:
    await upsert_material_selection(user_id, applications_id, material_id, add_qty)


async def fetch_selected_materials_for_request(
    user_id: int,
    applications_id: int
) -> list[dict]:
    """
    Tanlangan materiallar ro'yxati.
    Eski testlarda dublikat yozuvlar bo'lishi mumkinligi uchun SUM(...) qilib jamlaymiz.
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                mr.material_id,
                m.name,
                COALESCE(m.price, 0) AS price,
                SUM(
                    COALESCE(mr.quantity, 0)
                    + COALESCE(NULLIF(mr.description, '')::int, 0)
                ) AS qty
            FROM material_requests mr
            JOIN materials m ON m.id = mr.material_id
            WHERE mr.user_id = $1
              AND mr.applications_id = $2
            GROUP BY mr.material_id, m.name, m.price
            ORDER BY m.name
            """,
            user_id, applications_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# --- Omborga jo'natish: material_requests'ga QAYTA yozmaydi! ---
async def pick_warehouse_user_rr(seed: int) -> int | None:
    """
    Omborchilar orasidan bitta foydalanuvchini round-robin usulida tanlaydi.
    seed odatda applications_id bo'ladi.
    """
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT id
            FROM users
            WHERE role = 'warehouse'
            ORDER BY id
            """
        )
        if not rows:
            return None
        ids = [r["id"] for r in rows]
        return ids[seed % len(ids)]
    finally:
        await conn.close()


async def send_selection_to_warehouse(
    applications_id: int,
    technician_user_id: Optional[int] = None, *,
    technician_id: Optional[int] = None,
    request_type: str = "connection",  # 'connection' | 'technician' | 'staff'
) -> bool:
    """
    Tanlangan materiallarni omborga jo'natish.
    - material_requests ga QAYTA insert qilinmaydi (dublikatning ildizi shu edi).
    - faqat statusni 'in_warehouse' ga o'tkazamiz va connections ga tarix yozamiz (to'g'ri id-ustun bilan).
    """
    uid = technician_user_id if technician_user_id is not None else technician_id
    if uid is None:
        raise TypeError("send_selection_to_warehouse(): technician_user_id yoki technician_id bering")

    conn = await _conn()
    try:
        async with conn.transaction():
            # 1) status -> in_warehouse
            if request_type == "technician":
                await conn.execute(
                    "UPDATE technician_orders SET status='in_warehouse', updated_at=NOW() WHERE id=$1",
                    applications_id
                )
            elif request_type == "staff":
                await conn.execute(
                    "UPDATE staff_orders SET status='in_warehouse', updated_at=NOW() WHERE id=$1",
                    applications_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE connection_orders
                       SET status='in_warehouse'::connection_order_status,
                           updated_at=NOW()
                     WHERE id=$1
                    """,
                    applications_id
                )

            # 2) connections ga tarix yozish: recipient — omborchi
            warehouse_id = await pick_warehouse_user_rr(applications_id)
            if warehouse_id is not None:
                conn_id  = applications_id if request_type == "connection"  else None
                tech_oid = applications_id if request_type == "technician" else None
                staff_oid = applications_id if request_type == "staff"       else None

                await conn.execute(
                    """
                    INSERT INTO connections(
                        sender_id, recipient_id,
                        connection_id, technician_id, staff_id,
                        sender_status, recipient_status,
                        created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5,
                            'in_technician_work', 'in_warehouse',
                            NOW(), NOW())
                    """,
                    uid, warehouse_id, conn_id, tech_oid, staff_oid
                )

            return True
    finally:
        await conn.close()


# ======================= MATERIAL CHECKING AND WAREHOUSE INTEGRATION =======================

async def check_technician_material_availability(user_id: int, material_id: int, required_quantity: int) -> Dict[str, Any]:
    """
    Texnikning materialiga ega ekanligini tekshirish
    Agar yetarli bo'lmasa, ombordan qo'shimcha olish imkoniyatini ko'rsatish
    """
    conn = await _conn()
    try:
        # Texnikning joriy material miqdorini olish
        current_qty = await fetch_assigned_qty(user_id, material_id)
        
        # Ombor material miqdorini olish
        warehouse_qty = await conn.fetchval(
            """
            SELECT COALESCE(quantity, 0) 
            FROM materials 
            WHERE id = $1
            """,
            material_id
        )
        
        # Material ma'lumotlarini olish
        material_info = await fetch_material_by_id(material_id)
        
        result = {
            'material_id': material_id,
            'material_name': material_info['name'] if material_info else 'Unknown',
            'required_quantity': required_quantity,
            'current_quantity': current_qty,
            'warehouse_quantity': warehouse_qty,
            'has_enough': current_qty >= required_quantity,
            'can_get_from_warehouse': warehouse_qty >= (required_quantity - current_qty) if current_qty < required_quantity else True,
            'shortage': max(0, required_quantity - current_qty)
        }
        
        return result
    finally:
        await conn.close()

async def transfer_material_from_warehouse_to_technician(user_id: int, material_id: int, quantity: int) -> bool:
    """
    Ombordan texnikka material o'tkazish
    """
    conn = await _conn()
    try:
        # Transaction boshlash
        async with conn.transaction():
            # Ombordagi material miqdorini tekshirish
            warehouse_qty = await conn.fetchval(
                """
                SELECT COALESCE(quantity, 0) 
                FROM materials 
                WHERE id = $1
                """,
                material_id
            )
            
            if warehouse_qty < quantity:
                print(f"Insufficient warehouse quantity for material {material_id}. Available: {warehouse_qty}, Required: {quantity}")
                return False
            
            # Ombordagi material miqdorini kamaytirish
            await conn.execute(
                """
                UPDATE materials 
                SET quantity = quantity - $2, updated_at = now()
                WHERE id = $1
                """,
                material_id, quantity
            )
            
            # Texnikka material qo'shish (UPSERT)
            await conn.execute(
                """
                INSERT INTO material_and_technician (user_id, material_id, quantity)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, material_id) 
                DO UPDATE SET quantity = material_and_technician.quantity + $3
                """,
                user_id, material_id, quantity
            )
            
            return True
    except Exception as e:
        print(f"Error transferring material from warehouse to technician: {e}")
        return False
    finally:
        await conn.close()

async def get_technician_material_shortage_list(user_id: int, order_materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Texnikning biror ariza uchun yetishmayotgan materiallar ro'yxatini olish
    """
    shortage_list = []
    
    for material in order_materials:
        material_id = material['material_id']
        required_qty = material['quantity']
        
        availability = await check_technician_material_availability(user_id, material_id, required_qty)
        
        if not availability['has_enough']:
            shortage_list.append(availability)
    
    return shortage_list

# Eski nom bilan chaqirilsa ham yangi mantiqqa yo'naltirish
async def create_material_request_and_mark_in_warehouse(
    applications_id: int,
    technician_user_id: Optional[int] = None, *,
    technician_id: Optional[int] = None,
    material_id: int = 0,
    qty: int = 0,
    request_type: str = "connection",
) -> bool:
    # material_requests ga QAYTA yozmaymiz; tanlov bosqichida upsert_material_selection ishlatiladi.
    uid = technician_user_id if technician_user_id is not None else technician_id
    return await send_selection_to_warehouse(applications_id, technician_user_id=uid, request_type=request_type)
