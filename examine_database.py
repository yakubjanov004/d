import psycopg2
import os
from datetime import datetime
from config import settings

def connect_to_db():
    """Connect to PostgreSQL database using project config"""
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database="alfa_db" 
        )
        return conn
    except Exception as e:
        return f"Database connection error: {e}"

def get_table_structure():
    """Get structure of all tables and return as string"""
    conn = connect_to_db()
    if isinstance(conn, str):  # Error message
        return conn
    
    cursor = conn.cursor()
    output = []
    
    # Get all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    
    output.append("=" * 80)
    output.append("DATABASE STRUCTURE ANALYSIS")
    output.append("=" * 80)
    output.append(f"Total tables found: {len(tables)}")
    output.append("")
    
    for table in tables:
        table_name = table[0]
        output.append(f"📋 TABLE: {table_name}")
        output.append("-" * 50)
        
        # Get columns for this table
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = cursor.fetchall()
        
        if columns:
            output.append(f"{'Column Name':<25} {'Type':<20} {'Nullable':<10} {'Default':<15}")
            output.append("-" * 70)
            
            for col in columns:
                col_name, data_type, nullable, default, max_length = col
                
                # Format data type with length if applicable
                if max_length and data_type in ['character varying', 'character']:
                    data_type = f"{data_type}({max_length})"
                
                # Format nullable
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                
                # Format default
                default_str = str(default) if default else ""
                if len(default_str) > 12:
                    default_str = default_str[:12] + "..."
                
                output.append(f"{col_name:<25} {data_type:<20} {nullable_str:<10} {default_str:<15}")
        else:
            output.append("No columns found")
        
        output.append("")
        
        # Get indexes for this table
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes 
            WHERE tablename = %s
            AND schemaname = 'public'
        """, (table_name,))
        
        indexes = cursor.fetchall()
        if indexes:
            output.append("🔍 INDEXES:")
            for idx in indexes:
                output.append(f"  - {idx[0]}: {idx[1]}")
            output.append("")
        
        # Get foreign keys for this table
        cursor.execute("""
            SELECT 
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
        """, (table_name,))
        
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            output.append("🔗 FOREIGN KEYS:")
            for fk in foreign_keys:
                output.append(f"  - {fk[2]} -> {fk[3]}.{fk[4]}")
            output.append("")
        
        output.append("=" * 80)
        output.append("")
    
    cursor.close()
    conn.close()
    return "\n".join(output)

def get_all_tables(conn):
    """Get all table names from the database"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    except Exception as e:
        return []

def analyze_project_requirements(conn=None):
    """Analyze if database matches project requirements and return as string"""
    output = []
    output.append("🔍 ALFABOT PROJECT REQUIREMENTS ANALYSIS")
    output.append("=" * 80)
    
    # Get actual tables from database if connection provided
    if conn:
        actual_tables = get_all_tables(conn)
        output.append("Actual tables found in database:")
        for table in actual_tables:
            output.append(f"  ✓ {table}")
    else:
        # Fallback to expected tables based on migrations
        expected_tables = [
            "users", "tarif", "connection_orders", "technician_orders",
            "saff_orders", "materials", "material_requests",
            "regions", "user_sessions", "audit_logs"
        ]
        output.append("Expected tables based on alfabot project structure:")
        for table in expected_tables:
            output.append(f"  ✓ {table}")
    
    output.append("")
    output.append("Key features that should be supported:")
    output.append("  - Multi-role user system (admin, client, manager, technician, etc.)")
    output.append("  - Connection order management workflow")
    output.append("  - Technical service order workflow")
    output.append("  - Materials and inventory management")
    output.append("  - Regional service management")
    output.append("  - Status tracking and transitions")
    output.append("  - Telegram bot integration")
    output.append("  - Multi-language support (uz/ru)")
    
    return "\n".join(output)

def save_database_analysis_to_file():
    """Save complete alfabot database analysis to a text file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"alfabot_database_analysis_{timestamp}.txt"
    
    # Get database structure
    structure_analysis = get_table_structure()
    
    # Get project requirements analysis
    conn = connect_to_db()
    requirements_analysis = analyze_project_requirements(conn)
    if isinstance(conn, str) == False:  # Close connection if it's valid
        conn.close()
    
    # Combine all analysis
    full_analysis = f"""
ALFABOT DATABASE ANALYSIS REPORT
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{'='*80}

{structure_analysis}

{requirements_analysis}

{'='*80}
END OF ALFABOT REPORT
"""
    
    # Write to file
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(full_analysis)
        print(f"✅ Alfabot database analysis saved to: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving alfabot analysis file: {e}")
        return None

if __name__ == "__main__":
    print("🔍 Alfabot Database Analysis Tool")
    print("=" * 50)
    
    saved_file = save_database_analysis_to_file()
    if saved_file:
        print(f"📄 Alfabot analysis completed and saved to: {saved_file}")
    else:
        print("❌ Failed to save alfabot analysis to file")