#!/usr/bin/env python3
"""
Fix the database schema by adding the missing bug_id column
"""
import sqlite3
import os

def fix_database_schema():
    """Add missing bug_id column to bugs table"""
    db_path = 'beta_testing.db'
    
    print(f"🔧 Fixing database schema...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check current schema
            cursor.execute("PRAGMA table_info(bugs)")
            columns = cursor.fetchall()
            print(f"📋 Current columns in bugs table:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Check if bug_id column exists
            column_names = [col[1] for col in columns]
            if 'bug_id' not in column_names:
                print(f"➕ Adding missing bug_id column...")
                
                # Add the bug_id column
                cursor.execute("ALTER TABLE bugs ADD COLUMN bug_id INTEGER")
                
                # Update existing rows to have bug_id = id (for backward compatibility)
                cursor.execute("UPDATE bugs SET bug_id = id WHERE bug_id IS NULL")
                
                conn.commit()
                print(f"✅ Added bug_id column and populated with existing id values")
            else:
                print(f"✅ bug_id column already exists")
            
            # Verify the fix
            cursor.execute("PRAGMA table_info(bugs)")
            columns_after = cursor.fetchall()
            print(f"📋 Updated columns in bugs table:")
            for col in columns_after:
                print(f"  - {col[1]} ({col[2]})")
                
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")

if __name__ == "__main__":
    fix_database_schema()
