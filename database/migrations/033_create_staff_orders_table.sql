-- Migration: Add missing media column to staff_orders table
-- Date: 2025-10-21
-- Description: Adds the missing media column to the existing staff_orders table

BEGIN;

-- Add missing media column if it doesn't exist
ALTER TABLE public.staff_orders 
ADD COLUMN IF NOT EXISTS media TEXT;

-- Add foreign key constraints if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_staff_orders_user_id') THEN
        ALTER TABLE public.staff_orders 
        ADD CONSTRAINT fk_staff_orders_user_id 
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_staff_orders_tarif_id') THEN
        ALTER TABLE public.staff_orders 
        ADD CONSTRAINT fk_staff_orders_tarif_id 
        FOREIGN KEY (tarif_id) REFERENCES public.tarif(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_staff_orders_user_id ON public.staff_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_staff_orders_status ON public.staff_orders(status);
CREATE INDEX IF NOT EXISTS idx_staff_orders_application_number ON public.staff_orders(application_number);
CREATE INDEX IF NOT EXISTS idx_staff_orders_created_at ON public.staff_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_staff_orders_is_active ON public.staff_orders(is_active);

-- Add comments
COMMENT ON TABLE public.staff_orders IS 'Staff orders table for call center and internal orders';
COMMENT ON COLUMN public.staff_orders.application_number IS 'Unique application number (e.g., STAFF-CONN-B2C-0001)';
COMMENT ON COLUMN public.staff_orders.user_id IS 'User who created the order';
COMMENT ON COLUMN public.staff_orders.phone IS 'Contact phone number';
COMMENT ON COLUMN public.staff_orders.abonent_id IS 'Subscriber ID';
COMMENT ON COLUMN public.staff_orders.region IS 'Region name';
COMMENT ON COLUMN public.staff_orders.address IS 'Full address';
COMMENT ON COLUMN public.staff_orders.tarif_id IS 'Selected tariff ID';
COMMENT ON COLUMN public.staff_orders.description IS 'Order description';
COMMENT ON COLUMN public.staff_orders.problem_description IS 'Detailed problem description for technician orders';
COMMENT ON COLUMN public.staff_orders.diagnostics IS 'Diagnostics results';
COMMENT ON COLUMN public.staff_orders.media IS 'Media files (photos, videos, documents)';
COMMENT ON COLUMN public.staff_orders.business_type IS 'Business type (B2B/B2C)';
COMMENT ON COLUMN public.staff_orders.type_of_zayavka IS 'Type of application (connection/technician)';
COMMENT ON COLUMN public.staff_orders.status IS 'Order status';
COMMENT ON COLUMN public.staff_orders.jm_notes IS 'Junior Manager notes';
COMMENT ON COLUMN public.staff_orders.cancellation_note IS 'Cancellation reason';
COMMENT ON COLUMN public.staff_orders.is_active IS 'Is order active';
COMMENT ON COLUMN public.staff_orders.created_by_role IS 'Role of user who created the order';

COMMIT;
