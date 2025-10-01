# database/controller_orders.py
# Controller roli uchun statistika. Uslub: asyncpg.connect(settings.DB_URL)

import asyncpg
from config import settings

# 1) Jami: faqat technician_ordersdagi barcha arizalar
async def ctrl_total_tech_orders_count() -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        return await conn.fetchval("SELECT COUNT(*) FROM technician_orders;")
    finally:
        await conn.close()

# 2) Yangi: technician_orders.status='in_controller' + connection_orders.status='in_controller'
#    (ikkalasi ham is_active = TRUE)
async def ctrl_new_in_controller_count() -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        t_cnt = await conn.fetchval("""
            SELECT COUNT(*) FROM technician_orders
             WHERE is_active = TRUE AND status = 'in_controller';
        """)
        c_cnt = await conn.fetchval("""
            SELECT COUNT(*) FROM connection_orders
             WHERE is_active = TRUE AND status = 'in_controller';
        """)
        return int(t_cnt) + int(c_cnt)
    finally:
        await conn.close()

# 3) Jarayonda: (technician_orders + connection_orders)
#    is_active = TRUE va status <> 'completed'
async def ctrl_in_progress_count() -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        t_cnt = await conn.fetchval("""
            SELECT COUNT(*) FROM technician_orders
             WHERE is_active = TRUE AND status <> 'completed';
        """)
        c_cnt = await conn.fetchval("""
            SELECT COUNT(*) FROM connection_orders
             WHERE is_active = TRUE AND status <> 'completed';
        """)
        return int(t_cnt) + int(c_cnt)
    finally:
        await conn.close()

# 4) Bugun bajarilgan: (technician_orders + connection_orders)
#    status = 'completed', DATE(updated_at) = CURRENT_DATE, is_active = TRUE
async def ctrl_completed_today_count() -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        t_cnt = await conn.fetchval("""
            SELECT COUNT(*) FROM technician_orders
             WHERE is_active = TRUE
               AND status = 'completed'
               AND DATE(updated_at) = CURRENT_DATE;
        """)
        c_cnt = await conn.fetchval("""
            SELECT COUNT(*) FROM connection_orders
             WHERE is_active = TRUE
               AND status = 'completed'
               AND DATE(updated_at) = CURRENT_DATE;
        """)
        return int(t_cnt) + int(c_cnt)
    finally:
        await conn.close()

# 5) Bekor qilingan: (technician_orders + connection_orders) is_active = FALSE
async def ctrl_cancelled_count() -> int:
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        t_cnt = await conn.fetchval(
            "SELECT COUNT(*) FROM technician_orders WHERE is_active = FALSE;"
        )
        c_cnt = await conn.fetchval(
            "SELECT COUNT(*) FROM connection_orders WHERE is_active = FALSE;"
        )
        return int(t_cnt) + int(c_cnt)
    finally:
        await conn.close()
