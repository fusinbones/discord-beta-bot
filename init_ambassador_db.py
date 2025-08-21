import sqlite3
import os
from datetime import datetime

# Remove empty database file
if os.path.exists('ambassador_program.db'):
    os.remove('ambassador_program.db')
    print("Removed empty database file")

# Create new database
conn = sqlite3.connect('ambassador_program.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
    CREATE TABLE ambassadors (
        discord_id TEXT PRIMARY KEY,
        username TEXT,
        social_handles TEXT,
        target_platforms TEXT,
        joined_date TEXT,
        total_points INTEGER DEFAULT 0,
        current_month_points INTEGER DEFAULT 0,
        consecutive_months INTEGER DEFAULT 0,
        reward_tier TEXT DEFAULT 'none',
        status TEXT DEFAULT 'active'
    )
''')

cursor.execute('''
    CREATE TABLE submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ambassador_id TEXT,
        platform TEXT,
        post_type TEXT,
        url TEXT,
        screenshot_hash TEXT,
        engagement_data TEXT,
        content_preview TEXT,
        timestamp TEXT,
        points_awarded INTEGER,
        is_duplicate BOOLEAN,
        validity_status TEXT,
        gemini_analysis TEXT,
        FOREIGN KEY (ambassador_id) REFERENCES ambassadors (discord_id)
    )
''')

cursor.execute('''
    CREATE TABLE monthly_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_year TEXT,
        ambassador_id TEXT,
        total_points INTEGER,
        posts_count INTEGER,
        reward_earned TEXT,
        compliance_status TEXT,
        created_at TEXT
    )
''')

conn.commit()
print("Database tables created")

# Check tables were created
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables created: {[t[0] for t in tables]}")

conn.close()
print("Database initialization complete")
