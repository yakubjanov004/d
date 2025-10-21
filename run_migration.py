#!/usr/bin/env python3
"""
Migration Runner Script
Executes specific database migrations in order
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import DB_CONFIG
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/migration.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def run_migration(connection, migration_file):
    """Run a single migration file"""
    try:
        migration_path = os.path.join('database', 'migrations', migration_file)
        
        if not os.path.exists(migration_path):
            logger.error(f"Migration file not found: {migration_path}")
            return False
            
        with open(migration_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        logger.info(f"Running migration: {migration_file}")
        
        with connection.cursor() as cursor:
            # Split SQL content by semicolons and execute each statement separately
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        error_msg = str(e).lower()
                        if any(phrase in error_msg for phrase in ["already exists", "уже существует", "duplicate", "duplicate constraint"]):
                            logger.info(f"[SKIP] Object already exists in {migration_file}: {e}")
                        else:
                            raise
            
        logger.info(f"[SUCCESS] Migration {migration_file} completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Migration {migration_file} failed: {e}")
        return False

def check_migration_status(connection, migration_file):
    """Check if migration has been applied"""
    try:
        with connection.cursor() as cursor:
            # Check if migrations table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'migrations'
                );
            """)
            
            if not cursor.fetchone()[0]:
                # Create migrations table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE migrations (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                logger.info("Created migrations tracking table")
            else:
                # Check if table has correct structure, fix if needed
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'migrations' AND column_name = 'name'
                """)
                
                if not cursor.fetchone():
                    # Table exists but has wrong structure, recreate it
                    cursor.execute("DROP TABLE IF EXISTS migrations")
                    cursor.execute("""
                        CREATE TABLE migrations (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) UNIQUE NOT NULL,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    logger.info("Recreated migrations tracking table with correct structure")
            
            # Check if migration is already applied
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM migrations 
                    WHERE name = %s
                );
            """, (migration_file,))
            
            return cursor.fetchone()[0]
            
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return False

def mark_migration_applied(connection, migration_file):
    """Mark migration as applied"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO migrations (name) 
                VALUES (%s) 
                ON CONFLICT (name) DO NOTHING;
            """, (migration_file,))
        logger.info(f"Marked {migration_file} as applied")
    except Exception as e:
        logger.error(f"Error marking migration as applied: {e}")

def check_and_create_material_requests_table(connection):
    """Check if material_requests table exists and create if needed"""
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'material_requests'
                );
            """)
            
            if not cursor.fetchone()[0]:
                logger.info("[INFO] material_requests table does not exist, creating...")
                
                # Create the table based on backup.sql structure
                cursor.execute("""
                    CREATE TABLE material_requests (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT,
                        applications_id BIGINT,
                        material_id BIGINT,
                        connection_order_id BIGINT,
                        technician_order_id BIGINT,
                        staff_order_id BIGINT,
                        quantity INTEGER DEFAULT 1,
                        price NUMERIC DEFAULT 0,
                        total_price NUMERIC DEFAULT 0,
                        source_type VARCHAR(20) DEFAULT 'warehouse',
                        warehouse_approved BOOLEAN DEFAULT false,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                        application_number VARCHAR(50)
                    );
                """)
                
                # Add check constraint
                cursor.execute("""
                    ALTER TABLE material_requests 
                    ADD CONSTRAINT chk_material_requests_source_type 
                    CHECK (source_type IN ('warehouse', 'technician_stock'));
                """)
                
                logger.info("[SUCCESS] material_requests table created successfully")
            else:
                logger.info("[INFO] material_requests table already exists")
                
    except Exception as e:
        logger.error(f"[ERROR] Failed to check/create material_requests table: {e}")
        raise

def main():
    """Main migration runner"""
    # Define migrations to run (in order)
    migrations_to_run = [
        '029_unique_material_requests.sql',
        '030_improve_material_requests_persistence.sql', 
        '031_add_application_number_to_material_requests.sql',
        '032_remove_unused_columns.sql',
        '033_create_staff_orders_table.sql'
    ]
    
    logger.info("[START] Starting migration process...")
    logger.info(f"Migrations to run: {', '.join(migrations_to_run)}")
    
    connection = None
    try:
        connection = get_db_connection()
        logger.info("[SUCCESS] Database connection established")
        
        # Check and create material_requests table if needed
        check_and_create_material_requests_table(connection)
        
        successful_migrations = 0
        failed_migrations = 0
        
        for migration_file in migrations_to_run:
            logger.info(f"\n[PROCESSING] {migration_file}")
            
            # Check if already applied
            if check_migration_status(connection, migration_file):
                logger.info(f"[SKIP] Migration {migration_file} already applied, skipping...")
                continue
            
            # Run migration
            if run_migration(connection, migration_file):
                mark_migration_applied(connection, migration_file)
                successful_migrations += 1
            else:
                failed_migrations += 1
                logger.error(f"Migration {migration_file} failed, stopping...")
                break
        
        # Summary
        logger.info(f"\n[SUMMARY] Migration Summary:")
        logger.info(f"[SUCCESS] Successful: {successful_migrations}")
        logger.info(f"[ERROR] Failed: {failed_migrations}")
        
        if failed_migrations == 0:
            logger.info("[COMPLETE] All migrations completed successfully!")
        else:
            logger.error("[FAILED] Some migrations failed. Check logs for details.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"[FAILED] Migration process failed: {e}")
        sys.exit(1)
    finally:
        if connection:
            connection.close()
            logger.info("[CLOSE] Database connection closed")

if __name__ == "__main__":
    main()
