#!/usr/bin/env python3
"""
Check the messages table schema to see if we have message_id and guild_id fields
"""
import sqlite3

def check_messages_schema():
    """Check the current schema of the messages table"""
    db_path = 'beta_testing.db'
    
    print(f"🔍 Checking messages table schema...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check current schema
            cursor.execute("PRAGMA table_info(messages)")
            columns = cursor.fetchall()
            print(f"📋 Current columns in messages table:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Check if we have the required fields
            column_names = [col[1] for col in columns]
            required_fields = ['message_id', 'guild_id']
            
            missing_fields = []
            for field in required_fields:
                if field not in column_names:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                print(f"💡 These fields are needed to create Discord message links")
            else:
                print(f"✅ All required fields are present for message linking")
                
            # Show a sample of recent messages to see what data we have
            cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 3")
            sample_messages = cursor.fetchall()
            
            if sample_messages:
                print(f"\\n📝 Sample messages:")
                for i, msg in enumerate(sample_messages, 1):
                    print(f"  {i}. {msg}")
            else:
                print(f"\\n📝 No messages found in database")
                
    except Exception as e:
        print(f"❌ Error checking database schema: {e}")

if __name__ == "__main__":
    check_messages_schema()
