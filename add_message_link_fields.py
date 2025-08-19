#!/usr/bin/env python3
"""
Add message_id and guild_id fields to the messages table for Discord message linking
"""
import sqlite3

def add_message_link_fields():
    """Add missing message_id and guild_id fields to messages table"""
    db_path = 'beta_testing.db'
    
    print(f"🔧 Adding message link fields to messages table...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check current schema
            cursor.execute("PRAGMA table_info(messages)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Add message_id field if missing
            if 'message_id' not in column_names:
                print(f"➕ Adding message_id column...")
                cursor.execute("ALTER TABLE messages ADD COLUMN message_id TEXT")
                print(f"✅ Added message_id column")
            else:
                print(f"✅ message_id column already exists")
            
            # Add guild_id field if missing
            if 'guild_id' not in column_names:
                print(f"➕ Adding guild_id column...")
                cursor.execute("ALTER TABLE messages ADD COLUMN guild_id TEXT")
                print(f"✅ Added guild_id column")
            else:
                print(f"✅ guild_id column already exists")
            
            conn.commit()
            
            # Verify the changes
            cursor.execute("PRAGMA table_info(messages)")
            updated_columns = cursor.fetchall()
            print(f"\\n📋 Updated messages table schema:")
            for col in updated_columns:
                print(f"  - {col[1]} ({col[2]})")
                
    except Exception as e:
        print(f"❌ Error adding message link fields: {e}")

if __name__ == "__main__":
    add_message_link_fields()
