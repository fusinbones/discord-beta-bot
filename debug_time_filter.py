import sqlite3
from datetime import datetime, timedelta

with sqlite3.connect('beta_testing.db') as conn:
    cursor = conn.cursor()
    
    # Check what week_ago would be
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    print(f"Week ago cutoff: {week_ago}")
    print(f"Current time: {datetime.now().isoformat()}")
    
    # Check messages with the current filter
    cursor.execute('''
        SELECT message_content, username, timestamp, channel_name 
        FROM messages 
        WHERE timestamp > ? 
        AND message_content NOT LIKE '!%'
        AND (
            message_content LIKE '%bug%' OR
            message_content LIKE '%issue%' OR
            message_content LIKE '%error%' OR
            message_content LIKE '%problem%' OR
            message_content LIKE '%crash%' OR
            message_content LIKE '%broken%' OR
            message_content LIKE '%fix%' OR
            message_content LIKE '%test%' OR
            message_content LIKE '%feature%' OR
            message_content LIKE '%sidekick%' OR
            message_content LIKE '%tool%' OR
            message_content LIKE '%auction%' OR
            message_content LIKE '%automation%' OR
            message_content LIKE '%update%' OR
            message_content LIKE '%version%' OR
            message_content LIKE '%beta%' OR
            message_content LIKE '%feedback%' OR
            message_content LIKE '%suggestion%' OR
            message_content LIKE '%improvement%' OR
            LENGTH(message_content) > 50
        )
        ORDER BY timestamp DESC 
        LIMIT 20
    ''', (week_ago,))
    
    results = cursor.fetchall()
    
    print(f"\nFiltered messages ({len(results)} found):")
    for msg, user, timestamp, channel in results:
        print(f"[{timestamp}] {user}: {msg[:100]}...")
    
    # Check if there are older testing-related messages
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    cursor.execute('''
        SELECT message_content, username, timestamp 
        FROM messages 
        WHERE timestamp BETWEEN ? AND ?
        AND (
            message_content LIKE '%auction%' OR
            message_content LIKE '%tool%' OR
            message_content LIKE '%bug%' OR
            message_content LIKE '%test%'
        )
        ORDER BY timestamp DESC 
        LIMIT 10
    ''', (week_ago, three_days_ago))
    
    older_results = cursor.fetchall()
    print(f"\nOlder testing messages from 3-7 days ago ({len(older_results)} found):")
    for msg, user, timestamp in older_results:
        print(f"[{timestamp}] {user}: {msg[:100]}...")
