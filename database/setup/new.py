#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALFABOT — Complete Real Database Setup with Realistic Data
----------------------------------------------------------
• Real working database with proper user roles and order flows
• 1 Admin (Ulugbek), 1 Manager, 1 Controller, 1 CCS, 2 of each other role
• Realistic orders with proper status progression
• All indexes, triggers, and foreign keys included
• Bilingual support (UZ/RU)

How to run:
  1) (optional) set env: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
  2) python3 database/setup/new.py
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
    'database': os.getenv('PGDATABASE', 'alfa_db_real'),
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

# Schema will be added in parts due to size limitations
SCHEMA_PART_1 = r"""
-- ===============================================
-- ALFABOT REAL SCHEMA - PART 1 (ENUMS & BASIC TABLES)
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
                 WHERE t.typname = 'staff_order_status' AND n.nspname = 'public') THEN
    CREATE TYPE public.staff_order_status AS ENUM (
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
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON public.users(telegram_id);
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
CREATE INDEX IF NOT EXISTS idx_connection_orders_active ON public.connection_orders(is_active);
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
CREATE INDEX IF NOT EXISTS idx_technician_orders_active ON public.technician_orders(is_active);
DROP TRIGGER IF EXISTS trg_technician_orders_updated_at ON public.technician_orders;
CREATE TRIGGER trg_technician_orders_updated_at BEFORE UPDATE ON public.technician_orders
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.staff_orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  phone TEXT,
  region INTEGER,
  abonent_id TEXT,
  tarif_id BIGINT REFERENCES public.tarif(id) ON DELETE SET NULL,
  address TEXT,
  description TEXT,
  status public.staff_order_status NOT NULL DEFAULT 'in_call_center',
  type_of_zayavka public.type_of_zayavka NOT NULL DEFAULT 'connection',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_staff_orders_user ON public.staff_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_staff_orders_status ON public.staff_orders(status);
CREATE INDEX IF NOT EXISTS idx_staff_status_active ON public.staff_orders(status, is_active);
CREATE INDEX IF NOT EXISTS idx_staff_ccs_active_created
  ON public.staff_orders(created_at, id)
  WHERE (status = 'in_call_center'::public.staff_order_status AND is_active = TRUE);
DROP TRIGGER IF EXISTS trg_staff_orders_updated_at ON public.staff_orders;
CREATE TRIGGER trg_staff_orders_updated_at BEFORE UPDATE ON public.staff_orders
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
  staff_order_id INTEGER REFERENCES public.staff_orders(id) ON DELETE SET NULL,
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
  staff_id BIGINT REFERENCES public.staff_orders(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sender_status TEXT,
  recipient_status TEXT
);
-- Legacy column sync
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name='connections' AND column_name='connection_id') THEN
    ALTER TABLE public.connections ADD COLUMN connection_id INTEGER;
  END IF;
END $$;
CREATE OR REPLACE FUNCTION public.trg_sync_connections_ids()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.connection_order_id IS NOT NULL AND NEW.connection_id IS NULL THEN
    NEW.connection_id := NEW.connection_order_id::INTEGER;
  ELSIF NEW.connection_id IS NOT NULL AND NEW.connection_order_id IS NULL THEN
    NEW.connection_order_id := NEW.connection_id::BIGINT;
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
-- SEQUENTIAL USER ID SYSTEM
-- =========================
CREATE SEQUENCE IF NOT EXISTS user_sequential_id_seq START 1;

CREATE OR REPLACE FUNCTION get_next_sequential_user_id()
RETURNS INTEGER AS $$
DECLARE
    next_id INTEGER;
BEGIN
    SELECT nextval('user_sequential_id_seq') INTO next_id;
    WHILE EXISTS (SELECT 1 FROM users WHERE id = next_id) LOOP
        SELECT nextval('user_sequential_id_seq') INTO next_id;
    END LOOP;
    RETURN next_id;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS create_user_sequential(BIGINT, TEXT, TEXT, TEXT, user_role);
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
    SELECT get_next_sequential_user_id() INTO new_user_id;
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

CREATE OR REPLACE FUNCTION reset_user_sequential_sequence()
RETURNS VOID AS $$
DECLARE
    max_id INTEGER;
BEGIN
    SELECT COALESCE(MAX(id), 0) + 1 INTO max_id FROM users;
    PERFORM setval('user_sequential_id_seq', max_id, false);
END;
$$ LANGUAGE plpgsql;

SELECT reset_user_sequential_sequence();
CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);
"""

# Realistic data insertion
REALISTIC_DATA = r"""
-- ===== REALISTIC SEED DATA =====

-- Tariflar
INSERT INTO public.tarif (name, picture) VALUES
  ('Hammasi birga 4', ''),
  ('Hammasi birga 3+', ''),
  ('Hammasi birga 3', ''),
  ('Hammasi birga 2', '')
ON CONFLICT DO NOTHING;

-- Realistic Users (1 Admin, 1 Manager, 1 Controller, 1 CCS, 2 of each other role)
INSERT INTO public.users (telegram_id, full_name, username, phone, language, region, address, role, abonent_id, is_blocked) VALUES
  -- Admin (Ulugbek)
  (1978574076, 'Ulug''bek Administrator', 'ulugbekbb', '998900042544', 'uz', 1, 'Toshkent shahar', 'admin', 'ADM001', FALSE),
  
  -- Manager (1 ta)
  (210000001, 'Aziz Karimov', 'aziz_manager', '998901234567', 'uz', 1, 'Chilonzor tumani', 'manager', 'MGR001', FALSE),
  
  -- Controller (1 ta)
  (220000001, 'Bobur Nazarov', 'bobur_controller', '998902345678', 'uz', 1, 'Yunusobod tumani', 'controller', 'CTRL001', FALSE),
  
  -- Call Center Supervisor (1 ta)
  (230000001, 'Malika Toshmatova', 'malika_ccs', '998903456789', 'uz', 1, 'Mirzo Ulug''bek tumani', 'callcenter_supervisor', 'CCS001', FALSE),
  
  -- Junior Managers (2 ta)
  (310000001, 'Javohir Saidov', 'javohir_jm', '998911223344', 'uz', 1, 'Shayxontohur tumani', 'junior_manager', 'JM001', FALSE),
  (310000002, 'Александр Петров', 'alex_jm', '998911223345', 'ru', 1, 'ул. Пушкина', 'junior_manager', 'JM002', FALSE),
  
  -- Technicians (2 ta)
  (410000001, 'Umid Toshmatov', 'umid_tech', '998921334455', 'uz', 1, 'Sergeli tumani', 'technician', 'TECH001', FALSE),
  (410000002, 'Владимир Смирнов', 'vladimir_tech', '998921334456', 'ru', 1, 'ул. Ленина', 'technician', 'TECH002', FALSE),
  
  -- Warehouse (2 ta)
  (510000001, 'Kamola Qodirova', 'kamola_wh', '998931445566', 'uz', 1, 'Yakkasaroy tumani', 'warehouse', 'WH001', FALSE),
  (510000002, 'Елена Козлова', 'elena_wh', '998931445567', 'ru', 1, 'ул. Гагарина', 'warehouse', 'WH002', FALSE),
  
  -- Call Center Operators (2 ta)
  (610000001, 'Zarina Abdullayeva', 'zarina_cco', '998941556677', 'uz', 1, 'Bektemir tumani', 'callcenter_operator', 'CCO001', FALSE),
  (610000002, 'Дмитрий Волков', 'dmitry_cco', '998941556678', 'ru', 1, 'ул. Мира', 'callcenter_operator', 'CCO002', FALSE),
  
  -- Clients (10 ta - real foydalanuvchilar)
  (710000001, 'Akmal Rajabov', 'akmal_client', '998951667788', 'uz', 1, 'Olmazor tumani', 'client', 'CL001', FALSE),
  (710000002, 'Мария Иванова', 'maria_client', '998951667789', 'ru', 1, 'ул. Советская', 'client', 'CL002', FALSE),
  (710000003, 'Sardor Umarov', 'sardor_client', '998961778899', 'uz', 1, 'Yangihayot tumani', 'client', 'CL003', FALSE),
  (710000004, 'Анна Сидорова', 'anna_client', '998961778900', 'ru', 1, 'ул. Центральная', 'client', 'CL004', FALSE),
  (710000005, 'Farida Nematova', 'farida_client', '998971889900', 'uz', 1, 'Uchtepa tumani', 'client', 'CL005', FALSE),
  (710000006, 'Игорь Петров', 'igor_client', '998971889901', 'ru', 1, 'ул. Красная', 'client', 'CL006', FALSE),
  (710000007, 'Bakhtiyor Karimov', 'bakhtiyor_client', '998981990011', 'uz', 1, 'Mirobod tumani', 'client', 'CL007', FALSE),
  (710000008, 'Ольга Николаева', 'olga_client', '998981990012', 'ru', 1, 'ул. Зеленая', 'client', 'CL008', FALSE),
  (710000009, 'Dilnoza Toshmatova', 'dilnoza_client', '998992001122', 'uz', 1, 'Hamza tumani', 'client', 'CL009', FALSE),
  (710000010, 'Сергей Кузнецов', 'sergey_client', '998992001123', 'ru', 1, 'ул. Новая', 'client', 'CL010', FALSE)
ON CONFLICT (telegram_id) DO NOTHING;

-- Materials (realistic materials)
INSERT INTO public.materials (name, price, description, quantity, serial_number) VALUES
  ('Optik kabel OM3 50m', 150000, 'Optik kabel 50 metr', 25, 'OPT-OM3-50'),
  ('Optik kabel OM4 100m', 280000, 'Optik kabel 100 metr', 15, 'OPT-OM4-100'),
  ('Кабель оптический OM3 50м', 180000, 'Оптический кабель 50 метров', 20, 'OPT-OM3-50-RU'),
  ('Router TP-Link Archer', 450000, 'Wi-Fi router', 30, 'RT-TP-AC1200'),
  ('Switch 24 port', 650000, '24 portli switch', 12, 'SW-24-PORT'),
  ('Коммутатор 24 порта', 700000, 'Коммутатор на 24 порта', 10, 'SW-24-PORT-RU'),
  ('Modem Huawei', 320000, '4G modem', 18, 'MD-HW-4G'),
  ('Кabel UTP Cat6', 25000, 'UTP kabel metr', 500, 'UTP-CAT6-1M'),
  ('Кабель UTP Cat6', 30000, 'UTP кабель метр', 400, 'UTP-CAT6-1M-RU'),
  ('Wi-Fi adapter', 85000, 'USB Wi-Fi adapter', 35, 'WIFI-USB-AC'),
  ('Адаптер Wi-Fi', 95000, 'USB адаптер Wi-Fi', 25, 'WIFI-USB-AC-RU'),
  ('Antenna 2.4GHz', 120000, 'Wi-Fi antenna', 20, 'ANT-2.4G'),
  ('Антенна 2.4ГГц', 135000, 'Wi-Fi антенна', 15, 'ANT-2.4G-RU')
ON CONFLICT (serial_number) DO NOTHING;

-- Realistic Connection Orders (har xil statuslarda)
INSERT INTO public.connection_orders (user_id, region, address, tarif_id, status, notes, created_at) VALUES
  -- Menejerda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000001), 'Toshkent', 'Olmazor tumani, Navoiy ko''chasi 12-uy', 1, 'in_manager', 'Yangi mijoz, internet ulanish kerak', NOW() - INTERVAL '2 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000002), 'Toshkent', 'ул. Советская 45', 2, 'in_manager', 'Новый клиент, нужен интернет', NOW() - INTERVAL '1 day'),
  
  -- Junior Managerda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000003), 'Toshkent', 'Yangihayot tumani, Mustaqillik ko''chasi 78', 1, 'in_junior_manager', 'Menejer tomonidan yuborilgan', NOW() - INTERVAL '3 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000004), 'Toshkent', 'ул. Центральная 23', 3, 'in_junior_manager', 'Отправлено менеджером', NOW() - INTERVAL '2 days'),
  
  -- Controllerda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000005), 'Toshkent', 'Uchtepa tumani, Bunyodkor ko''chasi 34', 2, 'in_controller', 'Junior manager tomonidan yuborilgan', NOW() - INTERVAL '4 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000006), 'Toshkent', 'ул. Красная 67', 1, 'in_controller', 'Отправлено младшим менеджером', NOW() - INTERVAL '3 days'),
  
  -- Texnikda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000007), 'Toshkent', 'Mirobod tumani, Amir Temur ko''chasi 89', 4, 'in_technician', 'Controller tomonidan texnikka yuborilgan', NOW() - INTERVAL '5 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000008), 'Toshkent', 'ул. Зеленая 12', 2, 'in_technician', 'Отправлено контроллером технику', NOW() - INTERVAL '4 days'),
  
  -- Texnik ishlayapti (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000009), 'Toshkent', 'Hamza tumani, Alisher Navoiy ko''chasi 56', 3, 'in_technician_work', 'Texnik ishni boshlagan', NOW() - INTERVAL '6 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000010), 'Toshkent', 'ул. Новая 34', 1, 'in_technician_work', 'Техник начал работу', NOW() - INTERVAL '5 days'),
  
  -- Tugallangan (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000001), 'Toshkent', 'Olmazor tumani, Navoiy ko''chasi 12-uy', 1, 'completed', 'Muvaffaqiyatli tugallangan', NOW() - INTERVAL '7 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000002), 'Toshkent', 'ул. Советская 45', 2, 'completed', 'Успешно завершен', NOW() - INTERVAL '6 days')
ON CONFLICT DO NOTHING;

-- Realistic Technician Orders (har xil statuslarda)
INSERT INTO public.technician_orders (user_id, region, abonent_id, address, description, status, created_at) VALUES
  -- Controllerda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000003), 1, 'CL003', 'Yangihayot tumani, Mustaqillik ko''chasi 78', 'Internet tezligi sekin', 'in_controller', NOW() - INTERVAL '2 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000004), 1, 'CL004', 'ул. Центральная 23', 'Медленная скорость интернета', 'in_controller', NOW() - INTERVAL '1 day'),
  
  -- Texnikda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000005), 1, 'CL005', 'Uchtepa tumani, Bunyodkor ko''chasi 34', 'Router ishlamayapti', 'in_technician', NOW() - INTERVAL '3 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000006), 1, 'CL006', 'ул. Красная 67', 'Роутер не работает', 'in_technician', NOW() - INTERVAL '2 days'),
  
  -- Texnik ishlayapti (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000007), 1, 'CL007', 'Mirobod tumani, Amir Temur ko''chasi 89', 'Kabel almashtirish kerak', 'in_technician_work', NOW() - INTERVAL '4 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000008), 1, 'CL008', 'ул. Зеленая 12', 'Нужна замена кабеля', 'in_technician_work', NOW() - INTERVAL '3 days'),
  
  -- Tugallangan (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000009), 1, 'CL009', 'Hamza tumani, Alisher Navoiy ko''chasi 56', 'Wi-Fi signal kuchsiz', 'completed', NOW() - INTERVAL '5 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000010), 1, 'CL010', 'ул. Новая 34', 'Слабый сигнал Wi-Fi', 'completed', NOW() - INTERVAL '4 days')
ON CONFLICT DO NOTHING;

-- Realistic staff Orders (Call Center uchun)
INSERT INTO public.staff_orders (user_id, phone, region, abonent_id, tarif_id, address, description, status, type_of_zayavka, created_at) VALUES
  -- Call Centerda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000001), '998951667788', 1, 'CL001', 1, 'Olmazor tumani', 'Internet ulanish kerak', 'in_call_center', 'connection', NOW() - INTERVAL '1 day'),
  ((SELECT id FROM users WHERE telegram_id = 710000002), '998951667789', 1, 'CL002', 2, 'ул. Советская', 'Нужно подключение интернета', 'in_call_center', 'connection', NOW()),
  
  -- Managerda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000003), '998961778899', 1, 'CL003', 3, 'Yangihayot tumani', 'Tarifni o''zgartirish kerak', 'in_manager', 'connection', NOW() - INTERVAL '2 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000004), '998961778900', 1, 'CL004', 1, 'ул. Центральная', 'Нужно изменить тариф', 'in_manager', 'connection', NOW() - INTERVAL '1 day'),
  
  -- Controllerda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000005), '998971889900', 1, 'CL005', 2, 'Uchtepa tumani', 'Texnik xizmat kerak', 'in_controller', 'technician', NOW() - INTERVAL '3 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000006), '998971889901', 1, 'CL006', 4, 'ул. Красная', 'Нужен технический сервис', 'in_controller', 'technician', NOW() - INTERVAL '2 days'),
  
  -- Texnikda (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000007), '998981990011', 1, 'CL007', 1, 'Mirobod tumani', 'Qurilma ta''mirlash', 'in_technician', 'technician', NOW() - INTERVAL '4 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000008), '998981990012', 1, 'CL008', 3, 'ул. Зеленая', 'Ремонт оборудования', 'in_technician', 'technician', NOW() - INTERVAL '3 days'),
  
  -- Tugallangan (2 ta)
  ((SELECT id FROM users WHERE telegram_id = 710000009), '998992001122', 1, 'CL009', 2, 'Hamza tumani', 'Internet ulanish', 'completed', 'connection', NOW() - INTERVAL '5 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000010), '998992001123', 1, 'CL010', 1, 'ул. Новая', 'Подключение интернета', 'completed', 'connection', NOW() - INTERVAL '4 days')
ON CONFLICT DO NOTHING;

-- Smart Service Orders
INSERT INTO public.smart_service_orders (user_id, category, service_type, address, is_active, created_at) VALUES
  ((SELECT id FROM users WHERE telegram_id = 710000001), 'aqlli_avtomatlashtirilgan_xizmatlar', 'aqlli_uy_tizimlarini_ornatish_sozlash', 'Olmazor tumani, Navoiy ko''chasi 12-uy', TRUE, NOW() - INTERVAL '1 day'),
  ((SELECT id FROM users WHERE telegram_id = 710000002), 'umnye_avtomatizirovannye_uslugi', 'ustanovka_nastroyka_sistem_umnogo_doma', 'ул. Советская 45', TRUE, NOW()),
  ((SELECT id FROM users WHERE telegram_id = 710000003), 'xavfsizlik_kuzatuv_tizimlari', 'videokuzatuv_kameralarini_ornatish_ip_va_analog', 'Yangihayot tumani, Mustaqillik ko''chasi 78', TRUE, NOW() - INTERVAL '2 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000004), 'sistemy_bezopasnosti_nablyudeniya', 'ustanovka_kamer_videonablyudeniya_ip_analog', 'ул. Центральная 23', TRUE, NOW() - INTERVAL '1 day'),
  ((SELECT id FROM users WHERE telegram_id = 710000005), 'internet_tarmoq_xizmatlari', 'wi_fi_tarmoqlarini_ornatish_sozlash', 'Uchtepa tumani, Bunyodkor ko''chasi 34', TRUE, NOW() - INTERVAL '3 days'),
  ((SELECT id FROM users WHERE telegram_id = 710000006), 'internet_setevye_uslugi', 'ustanovka_nastroyka_wi_fi_setey', 'ул. Красная 67', TRUE, NOW() - INTERVAL '2 days')
ON CONFLICT DO NOTHING;

-- Material Requests (realistic material requests)
INSERT INTO public.material_requests (description, user_id, applications_id, material_id, connection_order_id, quantity, price, total_price) VALUES
  ('Optik kabel kerak', (SELECT id FROM users WHERE telegram_id = 410000001), 1, 1, 1, 2, 150000, 300000),
  ('Router kerak', (SELECT id FROM users WHERE telegram_id = 410000001), 1, 4, 1, 1, 450000, 450000),
  ('UTP kabel kerak', (SELECT id FROM users WHERE telegram_id = 410000002), 2, 8, 2, 10, 25000, 250000),
  ('Wi-Fi adapter kerak', (SELECT id FROM users WHERE telegram_id = 410000002), 2, 10, 2, 2, 85000, 170000)
ON CONFLICT DO NOTHING;

-- Reports
INSERT INTO public.reports (title, description, created_by, created_at) VALUES
  ('Oylik hisobot', 'Yanvar oyi uchun umumiy hisobot', (SELECT id FROM users WHERE telegram_id = 210000001), NOW() - INTERVAL '5 days'),
  ('Texnik xizmat hisoboti', 'Texnik ishlar bo''yicha hisobot', (SELECT id FROM users WHERE telegram_id = 220000001), NOW() - INTERVAL '3 days'),
  ('Call Center hisoboti', 'Call center ishlari bo''yicha hisobot', (SELECT id FROM users WHERE telegram_id = 230000001), NOW() - INTERVAL '2 days'),
  ('Ombor hisoboti', 'Materiallar bo''yicha hisobot', (SELECT id FROM users WHERE telegram_id = 510000001), NOW() - INTERVAL '1 day')
ON CONFLICT DO NOTHING;

-- AKT Documents
INSERT INTO public.akt_documents (request_id, request_type, akt_number, file_path, file_hash, created_at) VALUES
  (1, 'connection', 'AKT-CONN-001', '/documents/AKT-CONN-001.pdf', 'abc123def456', NOW() - INTERVAL '7 days'),
  (2, 'connection', 'AKT-CONN-002', '/documents/AKT-CONN-002.pdf', 'def456ghi789', NOW() - INTERVAL '6 days'),
  (1, 'technician', 'AKT-TECH-001', '/documents/AKT-TECH-001.pdf', 'ghi789jkl012', NOW() - INTERVAL '5 days'),
  (2, 'technician', 'AKT-TECH-002', '/documents/AKT-TECH-002.pdf', 'jkl012mno345', NOW() - INTERVAL '4 days')
ON CONFLICT (request_id, request_type) DO NOTHING;

-- AKT Ratings
INSERT INTO public.akt_ratings (request_id, request_type, rating, comment, created_at) VALUES
  (1, 'connection', 5, 'Juda yaxshi xizmat, tavsiya qilaman!', NOW() - INTERVAL '6 days'),
  (2, 'connection', 4, 'Хороший сервис, рекомендую!', NOW() - INTERVAL '5 days'),
  (1, 'technician', 5, 'Texnik juda tez va sifatli ishladi', NOW() - INTERVAL '4 days'),
  (2, 'technician', 4, 'Техник работал быстро и качественно', NOW() - INTERVAL '3 days')
ON CONFLICT (request_id, request_type) DO NOTHING;

-- Connections (realistic connections between users)
INSERT INTO public.connections (sender_id, recipient_id, connection_order_id, created_at, sender_status, recipient_status) VALUES
  ((SELECT id FROM users WHERE telegram_id = 210000001), (SELECT id FROM users WHERE telegram_id = 310000001), 1, NOW() - INTERVAL '2 days', 'sent', 'received'),
  ((SELECT id FROM users WHERE telegram_id = 210000001), (SELECT id FROM users WHERE telegram_id = 310000002), 2, NOW() - INTERVAL '1 day', 'sent', 'received'),
  ((SELECT id FROM users WHERE telegram_id = 310000001), (SELECT id FROM users WHERE telegram_id = 220000001), 3, NOW() - INTERVAL '3 days', 'sent', 'received'),
  ((SELECT id FROM users WHERE telegram_id = 310000002), (SELECT id FROM users WHERE telegram_id = 220000001), 4, NOW() - INTERVAL '2 days', 'sent', 'received'),
  ((SELECT id FROM users WHERE telegram_id = 220000001), (SELECT id FROM users WHERE telegram_id = 410000001), 5, NOW() - INTERVAL '4 days', 'sent', 'received'),
  ((SELECT id FROM users WHERE telegram_id = 220000001), (SELECT id FROM users WHERE telegram_id = 410000002), 6, NOW() - INTERVAL '3 days', 'sent', 'received')
ON CONFLICT DO NOTHING;

-- Material and Technician assignments
INSERT INTO public.material_and_technician (user_id, material_id, quantity) VALUES
  ((SELECT id FROM users WHERE telegram_id = 410000001), 1, 5),
  ((SELECT id FROM users WHERE telegram_id = 410000001), 4, 2),
  ((SELECT id FROM users WHERE telegram_id = 410000001), 8, 20),
  ((SELECT id FROM users WHERE telegram_id = 410000002), 2, 3),
  ((SELECT id FROM users WHERE telegram_id = 410000002), 5, 1),
  ((SELECT id FROM users WHERE telegram_id = 410000002), 10, 4)
ON CONFLICT (user_id, material_id) DO NOTHING;
"""

def run_sql(conn, sql_text):
    """Execute SQL script."""
    cur = conn.cursor()
    try:
        cur.execute(sql_text)
        conn.commit()
        print("[✓] SQL executed successfully")
    except Exception as e:
        print(f"[!] SQL execution error: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()

def verify_setup():
    """Verify database setup."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        cur = conn.cursor()
        
        # Check tables
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
        table_count = cur.fetchone()[0]
        print(f"[✓] Tables created: {table_count}")
        
        # Check enums
        cur.execute("SELECT typname FROM pg_type WHERE typtype='e' AND typnamespace=(SELECT oid FROM pg_namespace WHERE nspname='public')")
        enums = [r[0] for r in cur.fetchall()]
        print(f"[✓] Enums created: {', '.join(enums)}")
        
        # Check users
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        print(f"[✓] Users created: {user_count}")
        
        # Check orders by status
        cur.execute("SELECT status, COUNT(*) FROM connection_orders GROUP BY status")
        conn_orders = cur.fetchall()
        print(f"[✓] Connection orders by status:")
        for status, count in conn_orders:
            print(f"    {status}: {count}")
            
        cur.execute("SELECT status, COUNT(*) FROM technician_orders GROUP BY status")
        tech_orders = cur.fetchall()
        print(f"[✓] Technician orders by status:")
        for status, count in tech_orders:
            print(f"    {status}: {count}")
            
        cur.execute("SELECT status, COUNT(*) FROM staff_orders GROUP BY status")
        staff_orders = cur.fetchall()
        print(f"[✓] staff orders by status:")
        for status, count in staff_orders:
            print(f"    {status}: {count}")
        
        # Check materials
        cur.execute("SELECT COUNT(*) FROM materials")
        material_count = cur.fetchone()[0]
        print(f"[✓] Materials created: {material_count}")
        
        # Check user roles
        cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY role")
        roles = cur.fetchall()
        print(f"[✓] Users by role:")
        for role, count in roles:
            print(f"    {role}: {count}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[!] Verification error: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 ALFABOT Real Database Setup Starting...")
    print("=" * 50)
    
    # Create database
    if not create_database():
        print("[!] Failed to create database. Exiting.")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        print("[✓] Connected to database")
        
        # Apply schema
        print("\n[>] Applying database schema...")
        run_sql(conn, SCHEMA_PART_1)
        
        # Apply realistic data
        print("\n[>] Inserting realistic data...")
        run_sql(conn, REALISTIC_DATA)
        
        conn.close()
        print("\n[✓] Database setup completed!")
        
        # Verify setup
        print("\n[>] Verifying setup...")
        if verify_setup():
            print("\n✅ ALFABOT Real Database Setup Complete!")
            print("=" * 50)
            print("📊 Database Summary:")
            print("   • 1 Admin (Ulugbek)")
            print("   • 1 Manager")
            print("   • 1 Controller") 
            print("   • 1 Call Center Supervisor")
            print("   • 2 Junior Managers")
            print("   • 2 Technicians")
            print("   • 2 Warehouse staff")
            print("   • 2 Call Center Operators")
            print("   • 10 Clients")
            print("   • Realistic orders with proper status flow")
            print("   • All indexes, triggers, and foreign keys")
            print("   • Bilingual support (UZ/RU)")
            print("\n🎉 Ready for production testing!")
        else:
            print("\n⚠️  Setup completed but verification failed")
            
    except Exception as e:
        print(f"\n[!] Setup error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
