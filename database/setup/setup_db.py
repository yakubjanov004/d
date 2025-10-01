#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALFABOT Database Setup Script
Ushbu skript ma'lumotlar bazasini 0dan ko'taradi va barcha kerakli jadvallarni yaratadi.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'ulugbek202', 
    'database': 'alfa_db_uz_100',
    'client_encoding': 'UTF8'
}

def create_database():
    """Ma'lumotlar bazasini yaratish"""
    try:
        # PostgreSQL serverga ulanish (database nomisiz)
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            client_encoding='UTF8'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Database mavjudligini tekshirish
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_CONFIG['database']}'")
        exists = cursor.fetchone()
        
        if not exists:
            # UTF-8 encoding bilan database yaratish (kirill va lotin harflari uchun)
            cursor.execute(f"""
                CREATE DATABASE {DB_CONFIG['database']} 
                WITH ENCODING 'UTF8'
                LC_COLLATE = 'en_US.UTF-8'
                LC_CTYPE = 'en_US.UTF-8'
                TEMPLATE = template0
            """)
            print(f"Database '{DB_CONFIG['database']}' UTF-8 encoding va to'g'ri locale bilan yaratildi")
        else:
            print(f"Database '{DB_CONFIG['database']}' allaqachon mavjud")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Database yaratishda xatolik: {e}")
        return False
    
    return True

def execute_sql_script():
    """SQL skriptni bajarish"""
    
    sql_script = """
-- =========================
-- ALFABOT DATABASE SETUP
-- Ma'lumotlar bazasini 0dan ko'tarish
-- =========================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set database encoding for multilingual support (Windows compatible)
SET client_encoding = 'UTF8';

-- =========================
-- ENUM TYPES
-- =========================

-- Connection order statuses
CREATE TYPE connection_order_status AS ENUM (
    'new', 'in_manager', 'in_junior_manager', 'in_controller', 'in_technician',
    'in_diagnostics', 'in_repairs', 'in_warehouse', 'in_technician_work', 
    'completed', 'in_call_center'
);

-- Technician order statuses  
CREATE TYPE technician_order_status AS ENUM (
    'new', 'in_controller', 'in_technician', 'in_diagnostics', 'in_repairs',
    'in_warehouse', 'in_technician_work', 'completed'
);

-- Saff order statuses
CREATE TYPE saff_order_status AS ENUM (
    'in_call_center', 'in_manager', 'in_controller', 'in_technician', 'in_warehouse',
    'completed', 'cancelled'
);

-- Smart service categories
CREATE TYPE smart_service_category AS ENUM (
    'internet', 'tv', 'phone', 'other'
);

-- User roles
CREATE TYPE user_role AS ENUM (
    'admin', 'client', 'manager', 'junior_manager', 'controller',
    'technician', 'warehouse', 'callcenter_supervisor', 'callcenter_operator'
);

-- Type of applications
CREATE TYPE type_of_zayavka AS ENUM ('connection', 'technician');

-- =========================
-- DOMAIN TYPES
-- =========================

-- Smart service type domain
CREATE DOMAIN smart_service_type AS TEXT
CHECK (VALUE IN ('internet', 'tv', 'phone', 'other'));

-- =========================
-- SEQUENCES
-- =========================

-- User sequential ID sequence
CREATE SEQUENCE user_sequential_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

COMMENT ON SEQUENCE user_sequential_id_seq IS 'Sequential ID generator for users table';

-- =========================
-- TRIGGER FUNCTIONS
-- =========================

-- Drop existing functions if they exist
DROP FUNCTION IF EXISTS create_user_sequential(BIGINT, TEXT, TEXT, TEXT, user_role);
DROP FUNCTION IF EXISTS create_user_sequential();

-- Function to create user with sequential ID (for manual use)
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

-- Trigger function for automatic sequential ID assignment
CREATE OR REPLACE FUNCTION create_user_sequential()
RETURNS TRIGGER AS $$
BEGIN
    -- Only set ID if it's not already provided
    IF NEW.id IS NULL THEN
        NEW.id := get_next_sequential_user_id();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-- Function to reset user sequential sequence
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

-- Function to set updated_at timestamp
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- MAIN TABLES
-- =========================

-- AKT Documents table
CREATE TABLE akt_documents (
    id BIGSERIAL PRIMARY KEY,
    document_name TEXT NOT NULL,
    document_path TEXT NOT NULL,
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    file_size BIGINT,
    mime_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE akt_documents IS 'Table for storing AKT document information';
COMMENT ON COLUMN akt_documents.document_name IS 'Name of the document';
COMMENT ON COLUMN akt_documents.document_path IS 'File path where document is stored';
COMMENT ON COLUMN akt_documents.upload_date IS 'Date when document was uploaded';
COMMENT ON COLUMN akt_documents.file_size IS 'Size of the file in bytes';
COMMENT ON COLUMN akt_documents.mime_type IS 'MIME type of the document';

-- AKT Ratings table
CREATE TABLE akt_ratings (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    order_type TEXT NOT NULL CHECK (order_type IN ('connection', 'technician', 'saff')),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    rated_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE akt_ratings IS 'Table for storing order ratings and feedback';
COMMENT ON COLUMN akt_ratings.order_id IS 'ID of the rated order';
COMMENT ON COLUMN akt_ratings.order_type IS 'Type of order being rated';
COMMENT ON COLUMN akt_ratings.rating IS 'Rating value from 1 to 5';
COMMENT ON COLUMN akt_ratings.comment IS 'Optional comment with the rating';
COMMENT ON COLUMN akt_ratings.rated_by IS 'ID of user who gave the rating';

-- Users table
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    sequential_id INTEGER UNIQUE,
    telegram_id BIGINT UNIQUE,
    full_name TEXT,
    username TEXT,
    phone TEXT,
    language VARCHAR(5) NOT NULL DEFAULT 'uz',
    region INTEGER,
    address TEXT,
    role user_role,
    abonent_id TEXT,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Main users table with sequential ID support';
COMMENT ON COLUMN users.sequential_id IS 'Sequential ID for users, auto-generated';
COMMENT ON COLUMN users.telegram_id IS 'Telegram user ID';
COMMENT ON COLUMN users.full_name IS 'Full name of the user';
COMMENT ON COLUMN users.username IS 'Telegram username';
COMMENT ON COLUMN users.phone IS 'Phone number';
COMMENT ON COLUMN users.language IS 'Preferred language (uz, ru, en)';
COMMENT ON COLUMN users.region IS 'Region code';
COMMENT ON COLUMN users.address IS 'User address';
COMMENT ON COLUMN users.role IS 'User role in the system';
COMMENT ON COLUMN users.abonent_id IS 'Abonent identifier';
COMMENT ON COLUMN users.is_blocked IS 'Whether user is blocked';

-- Tarif table
CREATE TABLE tarif (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    picture TEXT,
    price DECIMAL(10,2),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tarif IS 'Tariff plans table';
COMMENT ON COLUMN tarif.name IS 'Tariff plan name';
COMMENT ON COLUMN tarif.picture IS 'Path to tariff picture';
COMMENT ON COLUMN tarif.price IS 'Tariff price';
COMMENT ON COLUMN tarif.description IS 'Tariff description';
COMMENT ON COLUMN tarif.is_active IS 'Whether tariff is active';

-- Connection orders table
CREATE TABLE connection_orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    region TEXT,
    address TEXT,
    tarif_id BIGINT REFERENCES tarif(id) ON DELETE SET NULL,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    rating INTEGER,
    notes TEXT,
    jm_notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    status connection_order_status NOT NULL DEFAULT 'in_manager',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE connection_orders IS 'Connection orders table';
COMMENT ON COLUMN connection_orders.user_id IS 'Reference to user who made the order';
COMMENT ON COLUMN connection_orders.region IS 'Region where connection is needed';
COMMENT ON COLUMN connection_orders.address IS 'Address for connection';
COMMENT ON COLUMN connection_orders.tarif_id IS 'Selected tariff plan';
COMMENT ON COLUMN connection_orders.longitude IS 'Longitude coordinate';
COMMENT ON COLUMN connection_orders.latitude IS 'Latitude coordinate';
COMMENT ON COLUMN connection_orders.rating IS 'Service rating';
COMMENT ON COLUMN connection_orders.notes IS 'General notes';
COMMENT ON COLUMN connection_orders.jm_notes IS 'Junior manager notes';
COMMENT ON COLUMN connection_orders.is_active IS 'Whether order is active';
COMMENT ON COLUMN connection_orders.status IS 'Current order status';

-- Materials table
CREATE TABLE materials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    price DECIMAL(10, 2),
    description TEXT,
    quantity INTEGER DEFAULT 0,
    serial_number VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE materials IS 'Materials inventory table';
COMMENT ON COLUMN materials.name IS 'Material name';
COMMENT ON COLUMN materials.price IS 'Material price';
COMMENT ON COLUMN materials.description IS 'Material description';
COMMENT ON COLUMN materials.quantity IS 'Available quantity';
COMMENT ON COLUMN materials.serial_number IS 'Unique serial number';

-- Connection orders (existing connections table)
CREATE TABLE connections (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    region TEXT,
    address TEXT,
    tarif_id BIGINT REFERENCES tarif(id) ON DELETE SET NULL,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    notes TEXT,
    jm_notes TEXT,
    controller_notes TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    status connection_order_status NOT NULL DEFAULT 'in_manager',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE connections IS 'Connection orders table';
COMMENT ON COLUMN connections.user_id IS 'Reference to user who made the order';
COMMENT ON COLUMN connections.region IS 'Region where connection is needed';
COMMENT ON COLUMN connections.address IS 'Address for connection';
COMMENT ON COLUMN connections.tarif_id IS 'Selected tariff plan';
COMMENT ON COLUMN connections.longitude IS 'Longitude coordinate';
COMMENT ON COLUMN connections.latitude IS 'Latitude coordinate';
COMMENT ON COLUMN connections.rating IS 'Service rating (1-5)';
COMMENT ON COLUMN connections.notes IS 'General notes';
COMMENT ON COLUMN connections.jm_notes IS 'Junior manager notes';
COMMENT ON COLUMN connections.controller_notes IS 'Controller notes';
COMMENT ON COLUMN connections.is_active IS 'Whether order is active';
COMMENT ON COLUMN connections.status IS 'Current order status';

-- Material requests table
CREATE TABLE material_requests (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT,
    order_type TEXT NOT NULL CHECK (order_type IN ('connection', 'technician')),
    material_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    requested_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    approved_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'delivered')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE material_requests IS 'Material requests for orders';
COMMENT ON COLUMN material_requests.order_id IS 'ID of related order';
COMMENT ON COLUMN material_requests.order_type IS 'Type of order (connection/technician)';
COMMENT ON COLUMN material_requests.material_name IS 'Name of requested material';
COMMENT ON COLUMN material_requests.quantity IS 'Requested quantity';
COMMENT ON COLUMN material_requests.requested_by IS 'User who requested material';
COMMENT ON COLUMN material_requests.approved_by IS 'User who approved request';
COMMENT ON COLUMN material_requests.status IS 'Request status';
COMMENT ON COLUMN material_requests.notes IS 'Additional notes';

-- Material and technician assignments
CREATE TABLE material_and_technician (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT,
    order_type TEXT NOT NULL CHECK (order_type IN ('connection', 'technician')),
    technician_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    materials JSONB,
    assigned_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE material_and_technician IS 'Material and technician assignments for orders';
COMMENT ON COLUMN material_and_technician.order_id IS 'ID of related order';
COMMENT ON COLUMN material_and_technician.order_type IS 'Type of order';
COMMENT ON COLUMN material_and_technician.technician_id IS 'Assigned technician';
COMMENT ON COLUMN material_and_technician.materials IS 'JSON data of assigned materials';
COMMENT ON COLUMN material_and_technician.assigned_by IS 'User who made assignment';
COMMENT ON COLUMN material_and_technician.assigned_at IS 'Assignment timestamp';
COMMENT ON COLUMN material_and_technician.notes IS 'Assignment notes';

-- Reports table
CREATE TABLE reports (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT,
    order_type TEXT NOT NULL CHECK (order_type IN ('connection', 'technician', 'saff')),
    report_type TEXT NOT NULL,
    content TEXT,
    media_files JSONB,
    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE reports IS 'Reports for various order types';
COMMENT ON COLUMN reports.order_id IS 'ID of related order';
COMMENT ON COLUMN reports.order_type IS 'Type of order';
COMMENT ON COLUMN reports.report_type IS 'Type of report';
COMMENT ON COLUMN reports.content IS 'Report content';
COMMENT ON COLUMN reports.media_files IS 'JSON array of media file paths';
COMMENT ON COLUMN reports.created_by IS 'User who created report';

-- Saff orders
CREATE TABLE saff_orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    phone TEXT,
    abonent_id TEXT,
    address TEXT,
    tarif_id BIGINT REFERENCES tarif(id) ON DELETE SET NULL,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    description TEXT,
    media TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    notes TEXT,
    status saff_order_status NOT NULL DEFAULT 'in_call_center',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE saff_orders IS 'Saff (quality) orders table';
COMMENT ON COLUMN saff_orders.user_id IS 'Reference to user';
COMMENT ON COLUMN saff_orders.phone IS 'Contact phone number';
COMMENT ON COLUMN saff_orders.abonent_id IS 'Abonent identifier';
COMMENT ON COLUMN saff_orders.address IS 'Service address';
COMMENT ON COLUMN saff_orders.tarif_id IS 'Related tariff';
COMMENT ON COLUMN saff_orders.longitude IS 'Longitude coordinate';
COMMENT ON COLUMN saff_orders.latitude IS 'Latitude coordinate';
COMMENT ON COLUMN saff_orders.description IS 'Order description';
COMMENT ON COLUMN saff_orders.media IS 'Media files';
COMMENT ON COLUMN saff_orders.rating IS 'Service rating';
COMMENT ON COLUMN saff_orders.notes IS 'Additional notes';
COMMENT ON COLUMN saff_orders.status IS 'Order status';
COMMENT ON COLUMN saff_orders.is_active IS 'Whether order is active';

-- Smart service orders
CREATE TABLE smart_service_orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    service_type smart_service_type NOT NULL,
    category smart_service_category NOT NULL,
    description TEXT,
    address TEXT,
    phone TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    media_files JSONB,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'cancelled')),
    assigned_to BIGINT REFERENCES users(id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE smart_service_orders IS 'Smart service orders table';
COMMENT ON COLUMN smart_service_orders.user_id IS 'User who created the order';
COMMENT ON COLUMN smart_service_orders.service_type IS 'Type of smart service';
COMMENT ON COLUMN smart_service_orders.category IS 'Service category';
COMMENT ON COLUMN smart_service_orders.description IS 'Order description';
COMMENT ON COLUMN smart_service_orders.address IS 'Service address';
COMMENT ON COLUMN smart_service_orders.phone IS 'Contact phone';
COMMENT ON COLUMN smart_service_orders.longitude IS 'Longitude coordinate';
COMMENT ON COLUMN smart_service_orders.latitude IS 'Latitude coordinate';
COMMENT ON COLUMN smart_service_orders.media_files IS 'JSON array of media files';
COMMENT ON COLUMN smart_service_orders.status IS 'Order status';
COMMENT ON COLUMN smart_service_orders.assigned_to IS 'Assigned technician';
COMMENT ON COLUMN smart_service_orders.rating IS 'Service rating';
COMMENT ON COLUMN smart_service_orders.notes IS 'Additional notes';
COMMENT ON COLUMN smart_service_orders.is_active IS 'Whether order is active';

-- Technician orders
CREATE TABLE technician_orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    region INTEGER,
    abonent_id TEXT,
    address TEXT,
    media TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    description TEXT,
    description_ish TEXT,
    status technician_order_status NOT NULL DEFAULT 'in_technician',
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE technician_orders IS 'Technician service orders';
COMMENT ON COLUMN technician_orders.user_id IS 'User who created the order';
COMMENT ON COLUMN technician_orders.region IS 'Region code';
COMMENT ON COLUMN technician_orders.abonent_id IS 'Abonent identifier';
COMMENT ON COLUMN technician_orders.address IS 'Service address';
COMMENT ON COLUMN technician_orders.media IS 'Media files';
COMMENT ON COLUMN technician_orders.longitude IS 'Longitude coordinate';
COMMENT ON COLUMN technician_orders.latitude IS 'Latitude coordinate';
COMMENT ON COLUMN technician_orders.description IS 'Problem description';
COMMENT ON COLUMN technician_orders.description_ish IS 'Work description';
COMMENT ON COLUMN technician_orders.status IS 'Order status';
COMMENT ON COLUMN technician_orders.rating IS 'Service rating';
COMMENT ON COLUMN technician_orders.notes IS 'Additional notes';
COMMENT ON COLUMN technician_orders.is_active IS 'Whether order is active';

-- =========================
-- TRIGGERS
-- =========================

-- Trigger for users sequential ID
CREATE TRIGGER trigger_users_sequential_id
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_user_sequential();

-- Triggers for updated_at columns
CREATE TRIGGER trigger_akt_documents_updated_at
    BEFORE UPDATE ON akt_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_akt_ratings_updated_at
    BEFORE UPDATE ON akt_ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_tarif_updated_at
    BEFORE UPDATE ON tarif
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_connection_orders_updated_at
    BEFORE UPDATE ON connection_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_materials_updated_at
    BEFORE UPDATE ON materials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_connections_updated_at
    BEFORE UPDATE ON connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_material_requests_updated_at
    BEFORE UPDATE ON material_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_material_and_technician_updated_at
    BEFORE UPDATE ON material_and_technician
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_saff_orders_updated_at
    BEFORE UPDATE ON saff_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_smart_service_orders_updated_at
    BEFORE UPDATE ON smart_service_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_technician_orders_updated_at
    BEFORE UPDATE ON technician_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================
-- INDEXES
-- =========================

-- Users indexes
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_sequential_id ON users(sequential_id);
CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_abonent_id ON users(abonent_id);

-- Connection orders indexes
CREATE INDEX idx_connection_orders_user_id ON connection_orders(user_id);
CREATE INDEX idx_connection_orders_status ON connection_orders(status);
CREATE INDEX idx_connection_orders_tarif_id ON connection_orders(tarif_id);
CREATE INDEX idx_connection_orders_created_at ON connection_orders(created_at);
CREATE INDEX idx_connection_orders_is_active ON connection_orders(is_active);

-- Materials indexes
CREATE INDEX idx_materials_name ON materials(name);
CREATE INDEX idx_materials_serial_number ON materials(serial_number);
CREATE INDEX idx_materials_created_at ON materials(created_at);

-- Connection orders indexes (existing connections table)
CREATE INDEX idx_connections_user_id ON connections(user_id);
CREATE INDEX idx_connections_status ON connections(status);
CREATE INDEX idx_connections_tarif_id ON connections(tarif_id);
CREATE INDEX idx_connections_created_at ON connections(created_at);
CREATE INDEX idx_connections_is_active ON connections(is_active);

-- Technician orders indexes
CREATE INDEX idx_technician_orders_user_id ON technician_orders(user_id);
CREATE INDEX idx_technician_orders_status ON technician_orders(status);
CREATE INDEX idx_technician_orders_abonent_id ON technician_orders(abonent_id);
CREATE INDEX idx_technician_orders_created_at ON technician_orders(created_at);
CREATE INDEX idx_technician_orders_is_active ON technician_orders(is_active);

-- Saff orders indexes
CREATE INDEX idx_saff_orders_user_id ON saff_orders(user_id);
CREATE INDEX idx_saff_orders_status ON saff_orders(status);
CREATE INDEX idx_saff_orders_tarif_id ON saff_orders(tarif_id);
CREATE INDEX idx_saff_orders_abonent_id ON saff_orders(abonent_id);
CREATE INDEX idx_saff_orders_created_at ON saff_orders(created_at);
CREATE INDEX idx_saff_orders_is_active ON saff_orders(is_active);

-- Smart service orders indexes
CREATE INDEX idx_smart_service_orders_user_id ON smart_service_orders(user_id);
CREATE INDEX idx_smart_service_orders_status ON smart_service_orders(status);
CREATE INDEX idx_smart_service_orders_service_type ON smart_service_orders(service_type);
CREATE INDEX idx_smart_service_orders_category ON smart_service_orders(category);
CREATE INDEX idx_smart_service_orders_assigned_to ON smart_service_orders(assigned_to);
CREATE INDEX idx_smart_service_orders_created_at ON smart_service_orders(created_at);

-- Material requests indexes
CREATE INDEX idx_material_requests_order_id ON material_requests(order_id);
CREATE INDEX idx_material_requests_order_type ON material_requests(order_type);
CREATE INDEX idx_material_requests_status ON material_requests(status);
CREATE INDEX idx_material_requests_requested_by ON material_requests(requested_by);

-- Reports indexes
CREATE INDEX idx_reports_order_id ON reports(order_id);
CREATE INDEX idx_reports_order_type ON reports(order_type);
CREATE INDEX idx_reports_created_by ON reports(created_by);
CREATE INDEX idx_reports_created_at ON reports(created_at);

-- AKT tables indexes
CREATE INDEX idx_akt_documents_upload_date ON akt_documents(upload_date);
CREATE INDEX idx_akt_ratings_order_id ON akt_ratings(order_id);
CREATE INDEX idx_akt_ratings_order_type ON akt_ratings(order_type);
CREATE INDEX idx_akt_ratings_rated_by ON akt_ratings(rated_by);

-- =========================
-- SAMPLE DATA
-- =========================

-- Insert sample tariff plans (only 4 plans as requested)
INSERT INTO tarif (name, picture) VALUES
('Hammasi birga 4', ''),
('Hammasi birga 3+', ''),
('Hammasi birga 3', ''),
('Hammasi birga 2', '');

-- Insert sample users (both Uzbek and Russian users)
INSERT INTO users (id, telegram_id, full_name, username, phone, language, region, address, role, abonent_id, is_blocked) VALUES
(1, 1978574076, 'Ulugbek Администратор', 'ulugbekbb', '998900042544', 'uz', 1, 'Toshkent shahri', 'admin', 'ADM001', false),
(2, 123456789, 'Aziz Karimov', 'aziz_k', '998901234567', 'uz', 1, 'Chilonzor tumani', 'client', '1001', false),
(3, 234567890, 'Nodira Toshmatova', 'nodira_t', '998912345678', 'uz', 2, 'Registon ko''chasi', 'manager', 'MGR001', false),
(4, 345678901, 'Bobur Alimov', 'bobur_a', '998923456789', 'uz', 3, 'Alpomish mahallasi', 'technician', 'TECH001', false),
(5, 456789012, 'Malika Rahimova', 'malika_r', '998934567890', 'uz', 4, 'Yuksalish ko''chasi', 'controller', 'CTRL001', false),
(6, 567890123, 'Jasur Nazarov', 'jasur_n', '998945678901', 'uz', 5, 'Navoiy prospekti', 'junior_manager', 'JM001', false),
(7, 678901234, 'Dilnoza Yusupova', 'dilnoza_y', '998956789012', 'uz', 1, 'Mirzo Ulug''bek tumani', 'warehouse', 'WH001', false),
(8, 789012345, 'Otabek Saidov', 'otabek_s', '998967890123', 'uz', 2, 'Shayxontohur tumani', 'callcenter_supervisor', 'CCS001', false),
(9, 890123456, 'Zarina Abdullayeva', 'zarina_a', '998978901234', 'uz', 3, 'Bektemir tumani', 'callcenter_operator', 'CCO001', false),
(10, 901234567, 'Rustam Tursunov', 'rustam_t', '998989012345', 'uz', 4, 'Sergeli tumani', 'technician', 'TECH002', false),
(11, 112233445, 'Gulnora Ismoilova', 'gulnora_i', '998901112233', 'uz', 5, 'Yunusobod tumani', 'client', '1010', false),
(12, 223344556, 'Sardor Mirzayev', 'sardor_m', '998902223344', 'uz', 1, 'Olmazor tumani', 'manager', 'MGR002', false),
(13, 334455667, 'Feruza Qodirova', 'feruza_q', '998903334455', 'uz', 2, 'Yashnobod tumani', 'controller', 'CTRL002', false),
(14, 445566778, 'Anvar Xolmatov', 'anvar_x', '998904445566', 'uz', 3, 'Uchtepa tumani', 'technician', 'TECH003', false),
(15, 555666777, 'Александр Петров', 'alex_petrov', '998911223344', 'ru', 1, 'ул. Пушкина, д. 15', 'client', '2001', false),
(16, 666777888, 'Елена Смирнова', 'elena_smirnova', '998922334455', 'ru', 2, 'пр. Ленина, д. 42', 'manager', 'MGR003', false),
(17, 777888999, 'Дмитрий Козлов', 'dmitry_kozlov', '998933445566', 'ru', 3, 'ул. Гагарина, д. 28', 'technician', 'TECH004', false),
(18, 888999000, 'Ольга Васильева', 'olga_vasileva', '998944556677', 'ru', 4, 'ул. Советская, д. 67', 'controller', 'CTRL003', false),
(19, 999000111, 'Сергей Николаев', 'sergey_nikolaev', '998955667788', 'ru', 5, 'пр. Мира, д. 89', 'junior_manager', 'JM002', false),
(20, 111222333, 'Анна Федорова', 'anna_fedorova', '998966778899', 'ru', 1, 'ул. Кирова, д. 34', 'warehouse', 'WH002', false),
(21, 222333444, 'Михаил Волков', 'mikhail_volkov', '998977889900', 'ru', 2, 'ул. Жукова, д. 56', 'callcenter_supervisor', 'CCS002', false),
(22, 333444555, 'Татьяна Морозова', 'tatyana_morozova', '998988990011', 'ru', 3, 'пр. Победы, д. 78', 'callcenter_operator', 'CCO002', false),
(23, 444555666, 'Владимир Соколов', 'vladimir_sokolov', '998999001122', 'ru', 4, 'ул. Маяковского, д. 91', 'technician', 'TECH005', false);

-- Insert sample connection orders (with both Uzbek and Russian users)
INSERT INTO connections (user_id, region, address, tarif_id, longitude, latitude, status, notes) VALUES
(2, 'Toshkent', 'Chilonzor tumani, 1-mavze', 2, 69.240562, 41.311158, 'new', 'Yangi ulanish so''rovi'),
(11, 'Toshkent', 'Yunusobod tumani, 5-uy', 3, 69.289398, 41.327142, 'in_manager', 'Manager ko''rib chiqmoqda'),
(15, 'Toshkent', 'ул. Пушкина, д. 15', 1, 69.240562, 41.311158, 'completed', 'Подключение завершено'),
(16, 'Samarqand', 'пр. Ленина, д. 42', 4, 66.975590, 39.627012, 'in_controller', 'На проверке у контроллера');

-- Insert sample connection_orders (new connection requests with both Uzbek and Russian users)
INSERT INTO connection_orders (user_id, region, address, tarif_id, longitude, latitude, status, notes, jm_notes) VALUES
(2, 'Toshkent', 'Chilonzor tumani, 12-uy, 45-xonadon', 1, 69.240562, 41.311158, 'new', 'Yangi ulanish uchun ariza', ''),
(11, 'Toshkent', 'Yunusobod tumani, 8-mavze, 23-uy', 2, 69.289398, 41.327142, 'in_manager', 'Manager tekshirmoqda', 'Hujjatlar to''liq'),
(12, 'Toshkent', 'Olmazor tumani, Navoiy ko''chasi 15', 3, 69.224326, 41.338797, 'in_junior_manager', 'Junior manager ko''rib chiqmoqda', 'Texnik imkoniyat bor'),
(15, 'Toshkent', 'ул. Пушкина, д. 25, кв. 12', 4, 69.240562, 41.311158, 'in_controller', 'На проверке у контроллера', 'Документы в порядке'),
(16, 'Samarqand', 'пр. Ленина, д. 58, кв. 7', 2, 66.975590, 39.627012, 'in_technician', 'Техник назначен', 'Готов к подключению'),
(20, 'Buxoro', 'ул. Кирова, д. 89, кв. 34', 1, 64.585262, 39.767477, 'completed', 'Подключение завершено', 'Успешно подключен'),
(13, 'Andijon', 'Yashnobod mahallasi, 7-uy', 3, 72.344415, 40.782370, 'new', 'Yangi tarif uchun ariza', ''),
(18, 'Namangan', 'ул. Советская, д. 45, кв. 18', 4, 71.672558, 40.998486, 'in_call_center', 'В обработке call-центра', 'Требует уточнения адреса');

-- Insert sample technician orders (with both Uzbek and Russian users)
INSERT INTO technician_orders (user_id, region, abonent_id, address, description, status) VALUES
(2, 1, '1001', 'Chilonzor tumani, 1-mavze', 'Internet aloqasi uzilmoqda', 'new'),
(11, 5, '1010', 'Yunusobod tumani, 5-uy', 'Router ishlamayapti', 'in_controller'),
(15, 1, '2001', 'ул. Пушкина, д. 15', 'Низкая скорость интернета', 'in_technician'),
(17, 3, 'TECH004', 'ул. Гагарина, д. 28', 'Проблемы с подключением', 'completed');

-- Insert sample materials (inventory items with both Uzbek and Russian descriptions)
INSERT INTO materials (name, price, description, quantity, serial_number) VALUES
('Optik kabel', 15000.00, 'Tashqi muhit uchun optik tolali kabel, 1km', 500, 'OPT-001'),
('Router TP-Link', 450000.00, 'Wi-Fi router, 4 port, 300Mbps', 25, 'RTR-001'),
('Splitter 1x8', 35000.00, 'Optik splitter, 1 kirish 8 chiqish', 100, 'SPL-001'),
('ONT Huawei', 320000.00, 'Optical Network Terminal, GPON', 50, 'ONT-001'),
('Patch cord', 8000.00, 'Optik patch cord, SC/UPC-SC/UPC, 3m', 200, 'PC-001'),
('Кабель оптический', 18000.00, 'Оптоволоконный кабель для внешней прокладки, 1км', 300, 'OPT-002'),
('Роутер D-Link', 380000.00, 'Wi-Fi роутер, 4 порта, 300Mbps', 30, 'RTR-002'),
('Сплиттер 1x16', 65000.00, 'Оптический сплиттер, 1 вход 16 выходов', 75, 'SPL-002'),
('ONT ZTE', 290000.00, 'Оптический сетевой терминал, GPON', 40, 'ONT-002'),
('Патч-корд', 9500.00, 'Оптический патч-корд, SC/UPC-SC/UPC, 5м', 150, 'PC-002'),
('Kabel UTP Cat6', 2500.00, 'UTP kabel, kategoriya 6, 1 metr', 1000, 'UTP-001'),
('Connector RJ45', 500.00, 'RJ45 ulagich, Cat6 uchun', 500, 'RJ45-001'),
('Switch 8 port', 180000.00, 'Ethernet switch, 8 port, gigabit', 20, 'SW-001'),
('Кабель UTP Cat6', 2800.00, 'UTP кабель, категория 6, 1 метр', 800, 'UTP-002'),
('Коннектор RJ45', 600.00, 'RJ45 разъем, для Cat6', 400, 'RJ45-002');

-- Insert sample saff orders (with both Uzbek and Russian users)
INSERT INTO saff_orders (user_id, phone, abonent_id, address, tarif_id, description, status) VALUES
(2, '998901234567', '1001', 'Chilonzor tumani, 1-mavze', 2, 'Sifat nazorati kerak', 'in_call_center'),
(11, '998901112233', '1010', 'Yunusobod tumani, 5-uy', 3, 'Xizmat sifatini tekshirish', 'in_manager'),
(15, '998911223344', '2001', 'ул. Пушкина, д. 15', 1, 'Проверка качества услуг', 'in_controller'),
(20, '998966778899', 'WH002', 'ул. Кирова, д. 34', 4, 'Контроль качества подключения', 'completed');

-- Insert sample smart service orders (with both Uzbek and Russian users)
INSERT INTO smart_service_orders (user_id, service_type, category, description, address, phone, status) VALUES
(2, 'internet', 'internet', 'Internet ulanishini sozlash', 'Chilonzor tumani, 1-mavze', '998901234567', 'new'),
(11, 'tv', 'tv', 'Televizor kanallarini sozlash', 'Yunusobod tumani, 5-uy', '998901112233', 'in_progress'),
(15, 'internet', 'internet', 'Настройка интернет-подключения', 'ул. Пушкина, д. 15', '998911223344', 'completed'),
(22, 'phone', 'phone', 'Настройка телефонной связи', 'пр. Победы, д. 78', '998988990011', 'new');

-- Insert sample material requests (updated with correct user IDs)
INSERT INTO material_requests (order_id, order_type, material_name, quantity, requested_by, status) VALUES
(1, 'connection', 'Optik kabel', 100, 4, 'pending'),
(2, 'connection', 'Router', 1, 4, 'approved'),
(1, 'technician', 'Splitter', 2, 17, 'delivered'),
(3, 'connection', 'Оптический кабель', 50, 17, 'pending');

-- Insert sample reports (updated with correct user IDs)
INSERT INTO reports (order_id, order_type, report_type, content, created_by) VALUES
(1, 'connection', 'installation', 'Ulanish muvaffaqiyatli o''rnatildi', 4),
(1, 'technician', 'repair', 'Muammo hal qilindi', 17),
(1, 'saff', 'quality_check', 'Sifat nazorati o''tkazildi', 5),
(3, 'connection', 'installation', 'Подключение успешно завершено', 17);

-- Insert sample AKT documents (with both languages)
INSERT INTO akt_documents (document_name, document_path, file_size, mime_type) VALUES
('Ulanish akti #001', '/documents/akt_001.pdf', 245760, 'application/pdf'),
('Ta''mirlash akti #002', '/documents/akt_002.pdf', 189440, 'application/pdf'),
('Sifat nazorati akti #003', '/documents/akt_003.pdf', 167890, 'application/pdf'),
('Акт подключения #004', '/documents/akt_004.pdf', 198765, 'application/pdf'),
('Акт ремонта #005', '/documents/akt_005.pdf', 156432, 'application/pdf');

-- Insert sample AKT ratings (updated with correct user IDs)
INSERT INTO akt_ratings (order_id, order_type, rating, comment, rated_by) VALUES
(1, 'connection', 5, 'Juda yaxshi xizmat', 2),
(2, 'technician', 4, 'Tez va sifatli', 11),
(3, 'saff', 5, 'Mukammal sifat', 15),
(4, 'connection', 5, 'Отличное обслуживание', 15),
(1, 'technician', 4, 'Быстро и качественно', 20);

-- =========================
-- FINAL SETUP
-- =========================

-- Reset the sequence to match existing data
SELECT reset_user_sequential_sequence();

-- Set sequence values based on existing data
SELECT setval('user_sequential_id_seq', (SELECT COALESCE(MAX(sequential_id), 0) + 1 FROM users), false);

-- =========================
-- COMMENTS
-- =========================

COMMENT ON SEQUENCE user_sequential_id_seq IS 'Sequential ID generator for users table';
COMMENT ON FUNCTION get_next_sequential_user_id() IS 'Returns next available sequential user ID';
COMMENT ON FUNCTION create_user_sequential(BIGINT, TEXT, TEXT, TEXT, user_role) IS 'Creates user with sequential ID';
COMMENT ON FUNCTION reset_user_sequential_sequence() IS 'Resets sequence to match existing data';

COMMIT;
"""
    
    try:
        # Ma'lumotlar bazasiga ulanish
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("SQL skript bajarilmoqda...")
        
        # SQL skriptni bajarish
        cursor.execute(sql_script)
        
        # O'zgarishlarni saqlash
        conn.commit()
        
        print("✅ Database muvaffaqiyatli yaratildi va ma'lumotlar kiritildi!")
        print("📊 Yaratilgan jadvallar:")
        print("   - users (foydalanuvchilar)")
        print("   - tarif (tarif rejalar)")
        print("   - connections (ulanish buyurtmalari)")
        print("   - technician_orders (texnik buyurtmalar)")
        print("   - saff_orders (sifat buyurtmalari)")
        print("   - smart_service_orders (aqlli xizmat buyurtmalari)")
        print("   - material_requests (material so'rovlari)")
        print("   - material_and_technician (material va texnik tayinlash)")
        print("   - reports (hisobotlar)")
        print("   - akt_documents (akt hujjatlari)")
        print("   - akt_ratings (akt baholari)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"SQL skript bajarishda xatolik: {e}")
        return False

def verify_setup():
    """Database setup ni tekshirish"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔍 Database setup tekshirilmoqda...")
        
        # Jadvallar sonini tekshirish
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]
        print(f"📋 Jadvallar soni: {table_count}")
        
        # ENUM turlarini tekshirish
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pg_type 
            WHERE typtype = 'e'
        """)
        enum_count = cursor.fetchone()[0]
        print(f"🏷️  ENUM turlari soni: {enum_count}")
        
        # Funksiyalarni tekshirish
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pg_proc 
            WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        """)
        function_count = cursor.fetchone()[0]
        print(f"⚙️  Funksiyalar soni: {function_count}")
        
        # Triggerlarni tekshirish
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.triggers 
            WHERE trigger_schema = 'public'
        """)
        trigger_count = cursor.fetchone()[0]
        print(f"🔄 Triggerlar soni: {trigger_count}")
        
        # Indexlarni tekshirish
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        index_count = cursor.fetchone()[0]
        print(f"📇 Indexlar soni: {index_count}")
        
        # Ma'lumotlar sonini tekshirish
        tables_to_check = ['users', 'tarif', 'connections', 'technician_orders', 'saff_orders']
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"📊 {table} jadvalidagi ma'lumotlar: {count}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database setup muvaffaqiyatli tekshirildi!")
        return True
        
    except Exception as e:
        print(f"❌ Tekshirishda xatolik: {e}")
        return False

def main():
    """Asosiy funksiya"""
    print("🚀 ALFABOT Database Setup boshlandi...")
    print("=" * 50)
    
    # 1. Database yaratish
    if not create_database():
        print("❌ Database yaratib bo'lmadi!")
        sys.exit(1)
    
    # 2. SQL skriptni bajarish
    if not execute_sql_script():
        print("❌ SQL skript bajarib bo'lmadi!")
        sys.exit(1)
    
    # 3. Setup ni tekshirish
    if not verify_setup():
        print("❌ Setup tekshirib bo'lmadi!")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 ALFABOT Database muvaffaqiyatli o'rnatildi!")
    print("💡 Endi botni ishga tushirishingiz mumkin.")

if __name__ == "__main__":
    main()