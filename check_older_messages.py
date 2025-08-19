import sqlite3
from datetime import datetime, timedelta

with sqlite3.connect('beta_testing.db') as conn:
    cursor = conn.cursor()
    
    # Check messages from different time periods
    now = datetime.now()
    
    periods = [
        ("Last 1 hour", now - timedelta(hours=1)),
        ("Last 6 hours", now - timedelta(hours=6)),
        ("Last 24 hours", now - timedelta(days=1)),
        ("Last 2 days", now - timedelta(days=2)),
        ("Last 3 days", now - timedelta(days=3)),
        ("Last 7 days", now - timedelta(days=7))
    ]
    
    for period_name, cutoff in periods:
        cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp > ?', (cutoff.isoformat(),))
        count = cursor.fetchone()[0]
        print(f"{period_name}: {count} messages")
    
    print("\n" + "="*50)
    print("Sample messages from 2-3 days ago:")
    
    # Get messages from 2-3 days ago specifically
    three_days_ago = (now - timedelta(days=3)).isoformat()
    two_days_ago = (now - timedelta(days=2)).isoformat()
    
    cursor.execute('''
        SELECT username, message_content, timestamp, channel_name 
        FROM messages 
        WHERE timestamp BETWEEN ? AND ? 
        AND message_content NOT LIKE '!%'
        ORDER BY timestamp DESC 
        LIMIT 10
    ''', (three_days_ago, two_days_ago))
    
    older_messages = cursor.fetchall()
    
    if older_messages:
        for user, content, timestamp, channel in older_messages:
            print(f"[{channel}] {user}: {content[:80]}... ({timestamp})")
    else:
        print("No messages found from 2-3 days ago")
        
        # Check what the oldest message is
        cursor.execute('SELECT timestamp FROM messages ORDER BY timestamp ASC LIMIT 1')
        oldest = cursor.fetchone()
        if oldest:
            print(f"Oldest message in database: {oldest[0]}")
        else:
            print("No messages in database at all")
