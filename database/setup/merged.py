#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALFABOT — Consolidated Database Setup (Merged Schema)
----------------------------------------------------
• Merged from 3 analysis reports (2025-09-22)
• Safe on Windows/Linux (UTF-8, no LC_* forcing)
• Idempotent: re-runnable (IF NOT EXISTS / DO $$ ... $$)
• Legacy-compat layer: connections.connecion_id <-> connection_order_id sync
• Rich bilingual (UZ/RU) seed data
How to run:
  1) (optional) set env: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
  2) python3 alfa_setup_merged.py
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_CONFIG = {
    'host': os.getenv('PGHOST', 'localhost'),
    'port': int(os.getenv('PGPORT', '5432')),
    'user': os.getenv('PGUSER', 'postgres'),
    'password': os.getenv('PGPASSWORD', 'ulugbek202'),
    'database': os.getenv('PGDATABASE', 'alfa_db_merged'),
}

def create_database():
    """Create DB (UTF8) if missing. Avoid Windows locale issues."""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG['database'],))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {DB_CONFIG['database']} WITH TEMPLATE template0 ENCODING 'UTF8'")
            print(f"[+] Database '{DB_CONFIG['database']}' created (UTF-8)")
        else:
            print(f"[=] Database '{DB_CONFIG['database']}' already exists")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[!] create_database error: {e}")
        return False

SCHEMA_SQL = r"""
-- ===============================================
-- ALFABOT MERGED SCHEMA (13 tables, 6 ENUMs, bilingual UZ/RU)
-- ===============================================
SET client_encoding = 'UTF8';

-- ===== ENUM TYPES =====
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE t.typname = 'user_role' AND n.nspname = 'public') THEN
    CREATE TYPE public.user_role AS ENUM (
      'admin','client','manager','junior_manager','controller','technician',
      'warehouse','callcenter_supervisor','callcenter_operator'
    );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE t.typname = 'connection_order_status' AND n.nspname = 'public') THEN
    CREATE TYPE public.connection_order_status AS ENUM (
      'in_manager','in_junior_manager','in_controller','in_technician',
      'in_diagnostics','in_repairs','in_warehouse','in_technician_work',
      'completed','in_call_center','in_call_center_operator','in_call_center_supervisor'
    );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE t.typname = 'technician_order_status' AND n.nspname = 'public') THEN
    CREATE TYPE public.technician_order_status AS ENUM (
      'in_controller','in_technician','in_diagnostics','in_repairs',
      'in_warehouse','in_technician_work','completed','cancelled'
    );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE t.typname = 'saff_order_status' AND n.nspname = 'public') THEN
    CREATE TYPE public.saff_order_status AS ENUM (
      'in_call_center','in_manager','in_controller','in_warehouse','in_technician','completed','cancelled'
    );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE t.typname = 'type_of_zayavka' AND n.nspname = 'public') THEN
    CREATE TYPE public.type_of_zayavka AS ENUM ('connection','technician');
  END IF;
END $$;

-- Smart Service: 6 bilingual categories (UZ + RU)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE t.typname = 'smart_service_category' AND n.nspname = 'public') THEN
    CREATE TYPE public.smart_service_category AS ENUM (
      'aqlli_avtomatlashtirilgan_xizmatlar', 'umnye_avtomatizirovannye_uslugi',
      'xavfsizlik_kuzatuv_tizimlari', 'sistemy_bezopasnosti_nablyudeniya',
      'internet_tarmoq_xizmatlari', 'internet_setevye_uslugi',
      'energiya_yashil_texnologiyalar', 'energiya_zelenye_texnologii',
      'multimediya_aloqa_tizimlari', 'multimedia_sistemy_svyazi',
      'maxsus_qoshimcha_xizmatlar', 'specialnye_dopolnitelnye_uslugi'
    );
  END IF;
END $$;

-- Smart Service: 42 bilingual service types (DOMAIN)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'smart_service_type') THEN
    CREATE DOMAIN public.smart_service_type AS TEXT CHECK (VALUE IN (
      -- UZ
      'aqlli_uy_tizimlarini_ornatish_sozlash','aqlli_yoritish_smart_lighting_tizimlari',
      'aqlli_termostat_iqlim_nazarati_tizimlari','smart_lock_internet_boshqariladigan_eshik_qulfi',
      'aqlli_rozetalar_energiya_monitoring_tizimlari','uyni_masofadan_boshqarish_qurilmalari_uzim',
      'aqlli_pardalari_jaluz_tizimlari','aqlli_malahiy_texnika_integratsiyasi',
      'videokuzatuv_kameralarini_ornatish_ip_va_analog','kamera_arxiv_tizimlari_bulutli_saqlash_xizmatlari',
      'domofon_tizimlari_ornatish','xavfsizlik_signalizatsiyasi_harakat_sensorlari',
      'yong_signalizatsiyasi_tizimlari','gaz_sizish_sav_toshqinliqqa_qarshi_tizimlar',
      'yuzni_tanish_face_recognition_tizimlari','avtomatik_eshik_darvoza_boshqaruv_tizimlari',
      'wi_fi_tarmoqlarini_ornatish_sozlash','wi_fi_qamrov_zonasini_kengaytirish_access_point',
      'mobil_aloqa_signalini_kuchaytirish_repeater','ofis_va_uy_uchun_lokal_tarmoq_lan_qurish',
      'internet_provayder_xizmatlarini_ulash','server_va_nas_qurilmalarini_ornatish',
      'bulutli_fayl_almashish_zaxira_tizimlari','vpn_va_xavfsiz_internet_ulanishlarini_tashkil',
      'quyosh_panellarini_ornatish_ulash','quyosh_batareyalari_orqali_energiya_saqlash',
      'shamol_generatorlarini_ornatish','elektr_energiyasini_tejovchi_yoritish_tizimlari',
      'avtomatik_suv_orish_tizimlari_smart_irrigation','smart_tv_ornatish_ulash',
      'uy_kinoteatri_tizimlari_ornatish','audio_tizimlar_multiroom',
      'ip_telefoniya_mini_ats_tizimlarini_tashkil','video_konferensiya_tizimlari',
      'interaktiv_taqdimot_tizimlari_proyektor_led','aqlli_ofis_tizimlarini_ornatish',
      'data_markaz_server_room_loyihalash_montaj','qurilma_tizimlar_uchun_texnik_xizmat_korsatish',
      'dasturiy_taminotni_ornatish_yangilash','iot_internet_of_things_qurilmalarini_integratsiya',
      'qurilmalarni_masofadan_boshqarish_tizimlarini_sozlash','suniy_intellekt_asosidagi_uy_ofis_boshqaruv',
      -- RU
      'ustanovka_nastroyka_sistem_umnogo_doma','umnoe_osveshchenie_smart_lighting_sistemy',
      'umnyy_termostat_sistemy_klimat_kontrolya','smart_lock_internet_upravlyaemyy_zamok_dveri',
      'umnye_rozetki_sistemy_monitoring_energii','distantsionnoe_upravlenie_domom_ustroystv',
      'umnye_shtory_zhalyuzi_sistemy','integratsiya_umnoy_bytovoy_texniki',
      'ustanovka_kamer_videonablyudeniya_ip_analog','sistemy_arxiva_kamer_oblachnoe_xranenie',
      'ustanovka_sistem_domofona','oxrannaya_signalizatsiya_datchiki_dvizheniya',
      'pozharnaya_signalizatsiya_sistemy','sistemy_protiv_utechki_gaza_vody_potopa',
      'sistemy_raspoznavaniya_lits_face_recognition','avtomaticheskie_sistemy_upravleniya_dver_vorot',
      'ustanovka_nastroyka_wi_fi_setey','rasshirenie_zony_pokrytiya_wi_fi_access_point',
      'usilenie_signala_mobilnoy_svyazi_repeater','postroenie_lokalnoy_seti_lan_dlya_ofisa_doma',
      'podklyuchenie_uslug_internet_provaydera','ustanovka_serverov_nas_ustroystv',
      'oblachnye_sistemy_obmena_rezervnogo_kopir','organizatsiya_vpn_bezopasnyx_internet_soedineniy',
      'ustanovka_podklyuchenie_solnechnyx_paneley','nakoplenie_energii_cherez_solnechnye_batarei',
      'ustanovka_vetryanyx_generatorov','energosberegayushchie_sistemy_osveshcheniya',
      'avtomaticheskie_sistemy_poliva_smart_irrigation','ustanovka_podklyuchenie_smart_tv',
      'ustanovka_sistem_domashnego_kinoteatr','audio_sistemy_multiroom',
      'organizatsiya_ip_telefonii_mini_ats_sistem','sistemy_videokonferentsiy',
      'interaktivnye_prezentatsionnye_sistemy_proyektor_led','ustanovka_sistem_umnogo_ofisa',
      'proektirovanie_montazh_data_tsentr_server_room','texnicheskoe_obsluzhivanie_ustroystv_sistem',
      'ustanovka_obnovlenie_programmnogo_obespecheniya','integratsiya_iot_internet_of_things_ustroystv',
      'nastroyka_sistem_distantsionnogo_upravleniya_ustroystv','upravlenie_domom_ofisom_na_osnove_ii'
    ));
  END IF;
END $$;

-- ===== COMMON FUNCTION: updated_at =====
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===== TABLES =====
CREATE TABLE IF NOT EXISTS public.users (
  id BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT UNIQUE,
  full_name TEXT,
  username TEXT,
  phone TEXT,
  language VARCHAR(5) NOT NULL DEFAULT 'uz',
  region INTEGER,
  address TEXT,
  role public.user_role,
  abonent_id TEXT,
  is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_abonent_id ON public.users(abonent_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
DROP TRIGGER IF EXISTS trg_users_updated_at ON public.users;
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.tarif (
  id BIGSERIAL PRIMARY KEY,
  name TEXT,
  picture TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
DROP TRIGGER IF EXISTS trg_tarif_updated_at ON public.tarif;
CREATE TRIGGER trg_tarif_updated_at BEFORE UPDATE ON public.tarif
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.connection_orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  region TEXT,
  address TEXT,
  tarif_id BIGINT REFERENCES public.tarif(id) ON DELETE SET NULL,
  longitude DOUBLE PRECISION,
  latitude DOUBLE PRECISION,
  rating INTEGER,
  notes TEXT,
  jm_notes TEXT,
  controller_notes TEXT NOT NULL DEFAULT '',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  status public.connection_order_status NOT NULL DEFAULT 'in_manager',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_connection_orders_user ON public.connection_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_connection_orders_status ON public.connection_orders(status);
CREATE INDEX IF NOT EXISTS idx_connection_orders_created ON public.connection_orders(created_at);
DROP TRIGGER IF EXISTS trg_connection_orders_updated_at ON public.connection_orders;
CREATE TRIGGER trg_connection_orders_updated_at BEFORE UPDATE ON public.connection_orders
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.technician_orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  region INTEGER,
  abonent_id TEXT,
  address TEXT,
  media TEXT,
  longitude DOUBLE PRECISION,
  latitude DOUBLE PRECISION,
  description TEXT,
  description_ish TEXT,
  description_operator TEXT,
  status public.technician_order_status NOT NULL DEFAULT 'in_controller',
  rating INTEGER,
  notes TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_technician_orders_user ON public.technician_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_technician_orders_status ON public.technician_orders(status);
CREATE INDEX IF NOT EXISTS idx_technician_orders_created ON public.technician_orders(created_at);
DROP TRIGGER IF EXISTS trg_technician_orders_updated_at ON public.technician_orders;
CREATE TRIGGER trg_technician_orders_updated_at BEFORE UPDATE ON public.technician_orders
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.saff_orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  phone TEXT,
  region INTEGER,
  abonent_id TEXT,
  tarif_id BIGINT REFERENCES public.tarif(id) ON DELETE SET NULL,
  address TEXT,
  description TEXT,
  status public.saff_order_status NOT NULL DEFAULT 'in_call_center',
  type_of_zayavka public.type_of_zayavka NOT NULL DEFAULT 'connection',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_saff_orders_user ON public.saff_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_saff_orders_status ON public.saff_orders(status);
CREATE INDEX IF NOT EXISTS idx_saff_status_active ON public.saff_orders(status, is_active);
CREATE INDEX IF NOT EXISTS idx_saff_ccs_active_created
  ON public.saff_orders(created_at, id)
  WHERE (status = 'in_call_center'::public.saff_order_status AND is_active = TRUE);
DROP TRIGGER IF EXISTS trg_saff_orders_updated_at ON public.saff_orders;
CREATE TRIGGER trg_saff_orders_updated_at BEFORE UPDATE ON public.saff_orders
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.smart_service_orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  category public.smart_service_category NOT NULL,
  service_type public.smart_service_type NOT NULL,
  address TEXT NOT NULL,
  longitude DOUBLE PRECISION,
  latitude DOUBLE PRECISION,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sso_user_id ON public.smart_service_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_sso_category ON public.smart_service_orders(category);
CREATE INDEX IF NOT EXISTS idx_sso_created ON public.smart_service_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_sso_created_desc ON public.smart_service_orders(created_at DESC);
DROP TRIGGER IF EXISTS trg_sso_updated_at ON public.smart_service_orders;
CREATE TRIGGER trg_sso_updated_at BEFORE UPDATE ON public.smart_service_orders
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Smart Service Category Normalization
DROP FUNCTION IF EXISTS public.normalize_sso_category(TEXT);
CREATE OR REPLACE FUNCTION public.normalize_sso_category(p_cat TEXT)
RETURNS public.smart_service_category AS $$
BEGIN
  CASE p_cat
    WHEN 'umnye_avtomatizirovannye_uslugi' THEN RETURN 'aqlli_avtomatlashtirilgan_xizmatlar'::public.smart_service_category;
    WHEN 'sistemy_bezopasnosti_nablyudeniya' THEN RETURN 'xavfsizlik_kuzatuv_tizimlari'::public.smart_service_category;
    WHEN 'internet_setevye_uslugi' THEN RETURN 'internet_tarmoq_xizmatlari'::public.smart_service_category;
    WHEN 'energiya_zelenye_texnologii' THEN RETURN 'energiya_yashil_texnologiyalar'::public.smart_service_category;
    WHEN 'multimedia_sistemy_svyazi' THEN RETURN 'multimediya_aloqa_tizimlari'::public.smart_service_category;
    WHEN 'specialnye_dopolnitelnye_uslugi' THEN RETURN 'maxsus_qoshimcha_xizmatlar'::public.smart_service_category;
    ELSE RETURN p_cat::public.smart_service_category;
  END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

DROP FUNCTION IF EXISTS public.trg_normalize_sso_category();
CREATE OR REPLACE FUNCTION public.trg_normalize_sso_category()
RETURNS TRIGGER AS $$
BEGIN
  NEW.category := public.normalize_sso_category(NEW.category::TEXT);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_normalize_sso_category_bi ON public.smart_service_orders;
CREATE TRIGGER trg_normalize_sso_category_bi
BEFORE INSERT ON public.smart_service_orders
FOR EACH ROW EXECUTE FUNCTION public.trg_normalize_sso_category();

CREATE TABLE IF NOT EXISTS public.materials (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255),
  price NUMERIC,
  description TEXT,
  quantity INTEGER DEFAULT 0,
  serial_number VARCHAR(100) UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_materials_name ON public.materials(name);
CREATE INDEX IF NOT EXISTS idx_materials_serial ON public.materials(serial_number);
DROP TRIGGER IF EXISTS trg_materials_updated_at ON public.materials;
CREATE TRIGGER trg_materials_updated_at BEFORE UPDATE ON public.materials
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.material_and_technician (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  material_id INTEGER NOT NULL REFERENCES public.materials(id) ON DELETE CASCADE,
  quantity INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_mat_tech_user_material
  ON public.material_and_technician(user_id, material_id);

CREATE TABLE IF NOT EXISTS public.material_requests (
  id SERIAL PRIMARY KEY,
  description TEXT,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  applications_id INTEGER NOT NULL,
  material_id INTEGER NOT NULL REFERENCES public.materials(id) ON DELETE CASCADE,
  connection_order_id INTEGER REFERENCES public.connection_orders(id) ON DELETE SET NULL,
  technician_order_id INTEGER REFERENCES public.technician_orders(id) ON DELETE SET NULL,
  saff_order_id INTEGER REFERENCES public.saff_orders(id) ON DELETE SET NULL,
  quantity INTEGER DEFAULT 1,
  price NUMERIC DEFAULT 0,
  total_price NUMERIC DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_material_requests_triplet
  ON public.material_requests(user_id, applications_id, material_id);
CREATE INDEX IF NOT EXISTS idx_material_requests_user ON public.material_requests(user_id);

CREATE TABLE IF NOT EXISTS public.reports (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  created_by BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Fix: FK to users.id (not telegram_id)
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.table_constraints
             WHERE table_name='reports' AND constraint_type='FOREIGN KEY') THEN
    ALTER TABLE public.reports DROP CONSTRAINT reports_created_by_fkey;
  END IF;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;
ALTER TABLE public.reports
  ADD CONSTRAINT reports_created_by_fkey
  FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_reports_created_by ON public.reports(created_by);
DROP TRIGGER IF EXISTS trg_reports_updated_at ON public.reports;
CREATE TRIGGER trg_reports_updated_at BEFORE UPDATE ON public.reports
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.akt_documents (
  id SERIAL PRIMARY KEY,
  request_id INTEGER NOT NULL,
  request_type VARCHAR(20) NOT NULL,
  akt_number VARCHAR(50) NOT NULL,
  file_path VARCHAR(255) NOT NULL,
  file_hash VARCHAR(64) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  sent_to_client_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS akt_documents_request_id_request_type_key
  ON public.akt_documents(request_id, request_type);
CREATE INDEX IF NOT EXISTS idx_akt_documents_request ON public.akt_documents(request_id, request_type);
CREATE INDEX IF NOT EXISTS idx_akt_documents_created ON public.akt_documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_akt_documents_sent ON public.akt_documents(sent_to_client_at);

CREATE TABLE IF NOT EXISTS public.akt_ratings (
  id SERIAL PRIMARY KEY,
  request_id INTEGER NOT NULL,
  request_type VARCHAR(20) NOT NULL,
  rating INTEGER NOT NULL,
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS akt_ratings_request_id_request_type_key
  ON public.akt_ratings(request_id, request_type);
CREATE INDEX IF NOT EXISTS idx_akt_ratings_request ON public.akt_ratings(request_id, request_type);
CREATE INDEX IF NOT EXISTS idx_akt_ratings_rating ON public.akt_ratings(rating);
CREATE INDEX IF NOT EXISTS idx_akt_ratings_created ON public.akt_ratings(created_at DESC);

CREATE TABLE IF NOT EXISTS public.connections (
  id BIGSERIAL PRIMARY KEY,
  sender_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  recipient_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  connection_order_id BIGINT REFERENCES public.connection_orders(id) ON DELETE SET NULL,
  technician_id BIGINT REFERENCES public.technician_orders(id) ON DELETE SET NULL,
  saff_id BIGINT REFERENCES public.saff_orders(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sender_status TEXT,
  recipient_status TEXT
);
-- Legacy column sync
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name='connections' AND column_name='connecion_id') THEN
    ALTER TABLE public.connections ADD COLUMN connecion_id INTEGER;
  END IF;
END $$;
CREATE OR REPLACE FUNCTION public.trg_sync_connections_ids()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.connection_order_id IS NOT NULL AND NEW.connecion_id IS NULL THEN
    NEW.connecion_id := NEW.connection_order_id::INTEGER;
  ELSIF NEW.connecion_id IS NOT NULL AND NEW.connection_order_id IS NULL THEN
    NEW.connection_order_id := NEW.connecion_id::BIGINT;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_sync_connections_ids_bi ON public.connections;
CREATE TRIGGER trg_sync_connections_ids_bi
BEFORE INSERT OR UPDATE ON public.connections
FOR EACH ROW EXECUTE FUNCTION public.trg_sync_connections_ids();
CREATE INDEX IF NOT EXISTS idx_connections_sender_id ON public.connections(sender_id);
CREATE INDEX IF NOT EXISTS idx_connections_recipient_id ON public.connections(recipient_id);
CREATE INDEX IF NOT EXISTS idx_connections_technician_id ON public.connections(technician_id);
DROP TRIGGER IF EXISTS trg_connections_updated_at ON public.connections;
CREATE TRIGGER trg_connections_updated_at BEFORE UPDATE ON public.connections
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =========================
-- SEQUENTIAL USER ID SYSTEM (005 Migration)
-- =========================

-- Create a custom sequence for sequential user IDs
CREATE SEQUENCE IF NOT EXISTS user_sequential_id_seq START 1;

-- Function to get next sequential user ID
CREATE OR REPLACE FUNCTION get_next_sequential_user_id()
RETURNS INTEGER AS $$
DECLARE
    next_id INTEGER;
BEGIN
    -- Get the next value from our custom sequence
    SELECT nextval('user_sequential_id_seq') INTO next_id;
    
    -- Check if this ID already exists in users table
    WHILE EXISTS (SELECT 1 FROM users WHERE id = next_id) LOOP
        SELECT nextval('user_sequential_id_seq') INTO next_id;
    END LOOP;
    
    RETURN next_id;
END;
$$ LANGUAGE plpgsql;

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS create_user_sequential(BIGINT, TEXT, TEXT, TEXT, user_role);

-- Function to create user with sequential ID
CREATE OR REPLACE FUNCTION create_user_sequential(
    p_telegram_id BIGINT,
    p_username TEXT DEFAULT NULL,
    p_full_name TEXT DEFAULT NULL,
    p_phone TEXT DEFAULT NULL,
    p_role user_role DEFAULT 'client'
)
RETURNS TABLE(
    user_id INTEGER,
    user_telegram_id BIGINT,
    user_username TEXT,
    user_full_name TEXT,
    user_phone TEXT,
    user_role user_role,
    user_created_at TIMESTAMPTZ
) AS $$
DECLARE
    new_user_id INTEGER;
    ret_user_id INTEGER;
    ret_telegram_id BIGINT;
    ret_username TEXT;
    ret_full_name TEXT;
    ret_phone TEXT;
    ret_role user_role;
    ret_created_at TIMESTAMPTZ;
BEGIN
    -- Get next sequential ID
    SELECT get_next_sequential_user_id() INTO new_user_id;
    
    -- Insert user with sequential ID
    INSERT INTO users (id, telegram_id, username, full_name, phone, role)
    VALUES (new_user_id, p_telegram_id, p_username, p_full_name, p_phone, p_role)
    ON CONFLICT (telegram_id) DO UPDATE SET
        username = EXCLUDED.username,
        full_name = EXCLUDED.full_name,
        phone = EXCLUDED.phone,
        updated_at = NOW()
    RETURNING users.id, users.telegram_id, users.username, users.full_name, users.phone, users.role, users.created_at
    INTO ret_user_id, ret_telegram_id, ret_username, ret_full_name, ret_phone, ret_role, ret_created_at;
    
    create_user_sequential.user_id := ret_user_id;
    create_user_sequential.user_telegram_id := ret_telegram_id;
    create_user_sequential.user_username := ret_username;
    create_user_sequential.user_full_name := ret_full_name;
    create_user_sequential.user_phone := ret_phone;
    create_user_sequential.user_role := ret_role;
    create_user_sequential.user_created_at := ret_created_at;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to reset sequence to match existing data
CREATE OR REPLACE FUNCTION reset_user_sequential_sequence()
RETURNS VOID AS $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Get the maximum existing user ID
    SELECT COALESCE(MAX(id), 0) + 1 INTO max_id FROM users;
    
    -- Reset the sequence to start from the next available ID
    PERFORM setval('user_sequential_id_seq', max_id, false);
END;
$$ LANGUAGE plpgsql;

-- Reset the sequence to match existing data
SELECT reset_user_sequential_sequence();

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);

COMMENT ON SEQUENCE user_sequential_id_seq IS 'Sequential ID generator for users table';
COMMENT ON FUNCTION get_next_sequential_user_id() IS 'Returns next available sequential user ID';
COMMENT ON FUNCTION create_user_sequential(BIGINT, TEXT, TEXT, TEXT, user_role) IS 'Creates user with sequential ID';
COMMENT ON FUNCTION reset_user_sequential_sequence() IS 'Resets sequence to match existing data';

-- ===== BILINGUAL SEED DATA =====
INSERT INTO public.tarif (name, picture) VALUES
  ('Hammasi birga 4', ''), ('Hammasi birga 3+', ''),
  ('Домашний Интернет+', ''), ('Супер ТВ пакет', '')
ON CONFLICT DO NOTHING;

INSERT INTO public.users (telegram_id, full_name, username, phone, language, region, address, role, abonent_id, is_blocked) VALUES
  (1978574076, 'Ulug‘bek Administrator', 'ulugbekbb', '998900042544', 'uz', 1, 'Toshkent', 'admin', 'ADM001', FALSE),
  (210000001, 'Aziz Karimov', 'aziz_k', '998901234567', 'uz', 1, 'Chilonzor', 'client', '1001', FALSE),
  (310000001, 'Александр Петров', 'alex_petrov', '998911223344', 'ru', 1, 'ул. Пушкина', 'client', '2001', FALSE)
ON CONFLICT DO NOTHING;

INSERT INTO public.materials (name, price, serial_number) VALUES
  ('Optik kabel', 15000, 'OPT-001'),
  ('Кабель оптический', 18000, 'OPT-002')
ON CONFLICT DO NOTHING;

INSERT INTO public.connection_orders (user_id, address, tarif_id, status)
SELECT id, 'Chilonzor 12-45', 1, 'in_manager' FROM public.users WHERE username = 'aziz_k'
ON CONFLICT DO NOTHING;

INSERT INTO public.smart_service_orders (user_id, category, service_type, address, is_active)
SELECT id, 'internet_tarmoq_xizmatlari', 'wi_fi_tarmoqlarini_ornatish_sozlash', 'Chilonzor', TRUE
FROM public.users WHERE username = 'aziz_k'
ON CONFLICT DO NOTHING;

INSERT INTO public.smart_service_orders (user_id, category, service_type, address, is_active)
SELECT id, 'internet_setevye_uslugi', 'ustanovka_nastroyka_wi_fi_setey', 'ул. Пушкина', TRUE
FROM public.users WHERE username = 'alex_petrov'
ON CONFLICT DO NOTHING;

INSERT INTO public.reports (title, created_by)
SELECT 'Hisobot', id FROM public.users WHERE username = 'aziz_k'
ON CONFLICT DO NOTHING;

INSERT INTO public.akt_documents (request_id, request_type, akt_number, file_path, file_hash)
VALUES (1, 'connection', 'AKT-001', '/docs/akt1.pdf', 'abc123')
ON CONFLICT DO NOTHING;

INSERT INTO public.akt_ratings (request_id, request_type, rating)
VALUES (1, 'connection', 5)
ON CONFLICT DO NOTHING;

-- Final comments
COMMENT ON TYPE public.smart_service_category IS 'Bilingual (UZ/RU)';
COMMENT ON DOMAIN public.smart_service_type IS '42 bilingual service types';
"""

def run_sql(conn, sql_text):
    cur = conn.cursor()
    # Execute the entire SQL script as a single block
    # PostgreSQL can handle multiple statements including DO blocks and CREATE FUNCTION
    cur.execute(sql_text)
    cur.close()

def verify_setup():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
        print(f"[✓] Tables: {cur.fetchone()[0]}")
        cur.execute("SELECT typname FROM pg_type WHERE typtype='e' AND typnamespace=(SELECT oid FROM pg_namespace WHERE nspname='public')")
        enums = [r[0] for r in cur.fetchall()]
        print(f"[✓] Enums: {', '.join(enums)}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[!] verify_setup error: {e}")
        return False

def main():
    print("🚀 ALFABOT merged setup start")
    if not create_database():
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        # Don't set autocommit mode for schema application
        
        print("[>] Applying schema & seeds...")
        run_sql(conn, SCHEMA_SQL)
        
        conn.commit()  # Commit the transaction
        conn.close()
        
        if verify_setup():
            print("✅ ALFABOT merged setup complete!")
        else:
            print("⚠️  Setup completed but verification failed")
    except Exception as e:
        print(f"[!] setup error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()