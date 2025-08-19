import sqlite3

with sqlite3.connect('beta_testing.db') as conn:
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute("PRAGMA table_info(messages)")
    schema = cursor.fetchall()
    
    print("Messages table schema:")
    for col in schema:
        print(f"  {col[1]} ({col[2]})")
    
    # Test the exact query from whatsnew
    from datetime import datetime, timedelta
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    
    cursor.execute('''
        SELECT message_content, username, timestamp, channel_name 
        FROM messages 
        WHERE timestamp > ? AND message_content NOT LIKE '!%'
        ORDER BY timestamp DESC 
        LIMIT 5
    ''', (week_ago,))
    
    results = cursor.fetchall()
    print(f"\nQuery results (should have {len(results)} rows):")
    for row in results:
        print(f"  Content: {row[0][:50]}...")
        print(f"  User: {row[1]}")
        print(f"  Time: {row[2]}")
        print(f"  Channel: {row[3]}")
        print("  ---")
