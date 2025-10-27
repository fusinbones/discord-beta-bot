"""
Add a 'synced_to_sheets' flag to the bugs table to track which bugs have been synced
"""

import sqlite3

def add_synced_flag():
    """Add synced_to_sheets column to bugs table"""
    try:
        with sqlite3.connect('beta_testing.db') as conn:
            cursor = conn.cursor()
            
            # Check if column already exists
            cursor.execute("PRAGMA table_info(bugs)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'synced_to_sheets' in columns:
                print("✅ Column 'synced_to_sheets' already exists")
                return
            
            print("🔧 Adding 'synced_to_sheets' column to bugs table...")
            
            # Add the new column (default 0 = not synced)
            cursor.execute('''
                ALTER TABLE bugs ADD COLUMN synced_to_sheets INTEGER DEFAULT 0
            ''')
            
            conn.commit()
            print("✅ Successfully added 'synced_to_sheets' column")
            
            # Show table structure
            cursor.execute("PRAGMA table_info(bugs)")
            print("\n📋 Updated table structure:")
            for column in cursor.fetchall():
                print(f"   {column[1]} ({column[2]})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_synced_flag()
