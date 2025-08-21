#!/usr/bin/env python3
"""
Fix Ambassador Database - Initialize and add darktiding as ambassador
"""

import sqlite3
import os
from datetime import datetime

def fix_ambassador_database():
    """Initialize ambassador database and add darktiding"""
    
    # Remove empty database file if it exists
    if os.path.exists('ambassador_program.db'):
        if os.path.getsize('ambassador_program.db') == 0:
            print("🗑️ Removing empty ambassador_program.db file")
            os.remove('ambassador_program.db')
    
    print("🔧 Initializing ambassador database...")
    
    with sqlite3.connect('ambassador_program.db') as conn:
        cursor = conn.cursor()
        
        # Create ambassadors table (current schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ambassadors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                social_handles TEXT,
                platforms TEXT,
                current_month_points INTEGER DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                consecutive_months INTEGER DEFAULT 0,
                reward_tier TEXT DEFAULT 'none',
                status TEXT DEFAULT 'active',
                weekly_posts TEXT DEFAULT '0000',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
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
        
        # Create monthly reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_reports (
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
        print("✅ Database tables created successfully")
        
        # Add darktiding as ambassador
        # Note: You'll need to replace 'YOUR_DISCORD_ID' with your actual Discord user ID
        # You can get this by enabling Developer Mode in Discord and right-clicking your name
        
        # For now, I'll use a placeholder - you'll need to update this
        discord_id = "DARKTIDING_DISCORD_ID"  # Replace with actual Discord ID
        username = "darktiding"
        social_handles = "darktiding"
        platforms = "instagram,tiktok,youtube"
        
        # Check if ambassador already exists
        cursor.execute('SELECT discord_id FROM ambassadors WHERE username = ?', (username,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"✅ Ambassador {username} already exists in database")
        else:
            cursor.execute('''
                INSERT INTO ambassadors (
                    discord_id, username, social_handles, platforms,
                    current_month_points, total_points, consecutive_months,
                    reward_tier, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                discord_id, username, social_handles, platforms,
                0, 0, 0, 'none', 'active'
            ))
            conn.commit()
            print(f"✅ Added {username} as ambassador")
        
        # Verify the data
        cursor.execute('SELECT discord_id, username, status FROM ambassadors')
        ambassadors = cursor.fetchall()
        print(f"\n📊 Current ambassadors in database: {len(ambassadors)}")
        for discord_id_row, username_row, status_row in ambassadors:
            print(f"  - {username_row} (Discord ID: {discord_id_row}, Status: {status_row})")

def get_discord_id_from_beta_db():
    """Try to find darktiding's Discord ID from the main beta database"""
    try:
        with sqlite3.connect('beta_testing.db') as conn:
            cursor = conn.cursor()
            
            # Check what tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"📋 Tables in beta_testing.db: {[t[0] for t in tables]}")
            
            # Try to find darktiding in various possible tables
            for table_name in [t[0] for t in tables]:
                try:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    # Look for username or discord_id columns
                    if 'username' in column_names or 'discord_id' in column_names:
                        print(f"🔍 Checking table {table_name} for darktiding...")
                        
                        if 'username' in column_names:
                            cursor.execute(f"SELECT * FROM {table_name} WHERE username LIKE '%darktiding%'")
                            results = cursor.fetchall()
                            if results:
                                print(f"  Found in {table_name}: {results}")
                                
                except Exception as e:
                    continue
                    
    except Exception as e:
        print(f"❌ Error checking beta database: {e}")

if __name__ == "__main__":
    print("🚀 Starting Ambassador Database Fix...")
    
    # First, try to find Discord ID from main database
    get_discord_id_from_beta_db()
    
    # Then fix the ambassador database
    fix_ambassador_database()
    
    print("\n✅ Ambassador database fix complete!")
    print("\n⚠️  IMPORTANT: You need to update the discord_id in this script with your actual Discord ID")
    print("   To get your Discord ID:")
    print("   1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)")
    print("   2. Right-click your username and select 'Copy User ID'")
    print("   3. Replace 'DARKTIDING_DISCORD_ID' in this script with your actual ID")
    print("   4. Run this script again")
