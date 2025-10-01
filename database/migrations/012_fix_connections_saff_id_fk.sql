-- ==========================================================
-- Migration: Fix connections.saff_id foreign key
-- Author: ChatGPT
-- Date: 2025-09-17
-- Purpose: Point saff_id to saff_orders.id instead of users.id
-- ==========================================================

BEGIN;

-- 1️⃣ Eski constraintni olib tashlaymiz
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'connections_saff_id_fkey'
          AND table_name = 'connections'
    ) THEN
        ALTER TABLE connections
        DROP CONSTRAINT connections_saff_id_fkey;
    END IF;
END$$;

-- 2️⃣ Yangi constraint qo‘shamiz (saff_orders.id ga bog‘lash)
ALTER TABLE connections
ADD CONSTRAINT connections_saff_id_fkey
    FOREIGN KEY (saff_id)
    REFERENCES saff_orders(id)
    ON DELETE CASCADE;

COMMIT;
