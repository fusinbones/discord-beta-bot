import sqlite3
from datetime import datetime, timedelta

# Check what's in the database
with sqlite3.connect('beta_testing.db') as conn:
    cursor = conn.cursor()
    
    # Check total messages
    cursor.execute('SELECT COUNT(*) FROM messages')
    total = cursor.fetchone()[0]
    print(f"Total messages in database: {total}")
    
    # Check recent messages (last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp > ?', (week_ago,))
    recent = cursor.fetchone()[0]
    print(f"Messages from last 7 days: {recent}")
    
    # Check message samples
    cursor.execute('SELECT username, message_content, timestamp, channel_name FROM messages ORDER BY timestamp DESC LIMIT 10')
    messages = cursor.fetchall()
    
    print("\nRecent messages:")
    for user, content, timestamp, channel in messages:
        print(f"[{channel}] {user}: {content[:50]}... ({timestamp})")
    
    # Check if there are any messages at all
    cursor.execute('SELECT * FROM messages LIMIT 5')
    all_messages = cursor.fetchall()
    print(f"\nSample messages structure: {all_messages}")
