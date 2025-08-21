#!/usr/bin/env python3
"""
Fix Ambassador Persistence - Ensure data syncs between Supabase and local DB
"""

import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("❌ Supabase library not installed")
    SUPABASE_AVAILABLE = False

def sync_ambassador_data():
    """Sync ambassador data from Supabase to local database"""
    
    if not SUPABASE_AVAILABLE:
        print("❌ Cannot sync - Supabase not available")
        return False
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found")
        return False
    
    try:
        # Connect to Supabase
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get all ambassadors from Supabase
        result = supabase.table('ambassadors').select('*').execute()
        supabase_ambassadors = result.data
        
        print(f"📥 Found {len(supabase_ambassadors)} ambassadors in Supabase")
        
        # Connect to local database
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()

            # Clear local ambassadors table and repopulate from Supabase
            cursor.execute('DELETE FROM ambassadors')

            # Detect local schema
            cursor.execute('PRAGMA table_info(ambassadors)')
            cols = [row[1] for row in cursor.fetchall()]
            has_platforms = 'platforms' in cols and 'joined_date' not in cols
            has_target_platforms = 'target_platforms' in cols and 'joined_date' in cols

            for ambassador in supabase_ambassadors:
                if has_platforms:
                    cursor.execute('''
                        INSERT INTO ambassadors (
                            discord_id, username, social_handles, platforms,
                            current_month_points, total_points, consecutive_months,
                            reward_tier, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ambassador.get('discord_id'),
                        ambassador.get('username'),
                        ambassador.get('social_handles'),
                        ambassador.get('platforms') or ambassador.get('target_platforms') or 'all',
                        ambassador.get('current_month_points', 0),
                        ambassador.get('total_points', 0),
                        ambassador.get('consecutive_months', 0),
                        ambassador.get('reward_tier', 'none'),
                        ambassador.get('status', 'active')
                    ))
                elif has_target_platforms:
                    cursor.execute('''
                        INSERT INTO ambassadors (
                            discord_id, username, social_handles, target_platforms,
                            joined_date, total_points, current_month_points,
                            consecutive_months, reward_tier, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ambassador.get('discord_id'),
                        ambassador.get('username'),
                        ambassador.get('social_handles'),
                        ambassador.get('target_platforms') or ambassador.get('platforms') or 'all',
                        ambassador.get('joined_date') or datetime.now().isoformat(),
                        ambassador.get('total_points', 0),
                        ambassador.get('current_month_points', 0),
                        ambassador.get('consecutive_months', 0),
                        ambassador.get('reward_tier', 'none'),
                        ambassador.get('status', 'active')
                    ))

                print(f"  ✅ Synced: {ambassador.get('username')} (ID: {ambassador.get('discord_id')})")

            conn.commit()
            
        print(f"✅ Successfully synced {len(supabase_ambassadors)} ambassadors to local database")
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False

def add_darktiding_to_both_databases():
    """Add darktiding to both Supabase and local database"""
    
    # You need to replace this with your actual Discord ID
    discord_id = input("Enter your Discord ID (right-click your name in Discord with Developer Mode enabled): ").strip()
    
    if not discord_id or not discord_id.isdigit():
        print("❌ Invalid Discord ID")
        return False
    
    ambassador_data = {
        'discord_id': discord_id,
        'username': 'darktiding',
        'social_handles': 'darktiding',
        'platforms': 'instagram,tiktok,youtube',
        'total_points': 0,
        'current_month_points': 0,
        'consecutive_months': 0,
        'reward_tier': 'none',
        'status': 'active'
    }
    
    # Add to Supabase
    if SUPABASE_AVAILABLE:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            try:
                supabase: Client = create_client(supabase_url, supabase_key)
                result = supabase.table('ambassadors').upsert(ambassador_data).execute()
                print("✅ Added darktiding to Supabase")
            except Exception as e:
                print(f"❌ Failed to add to Supabase: {e}")
    
    # Add to local database
    try:
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            # Detect schema
            cursor.execute('PRAGMA table_info(ambassadors)')
            cols = [row[1] for row in cursor.fetchall()]
            has_platforms = 'platforms' in cols and 'joined_date' not in cols
            if has_platforms:
                cursor.execute('''
                    INSERT OR REPLACE INTO ambassadors (
                        discord_id, username, social_handles, platforms,
                        current_month_points, total_points, consecutive_months,
                        reward_tier, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ambassador_data['discord_id'],
                    ambassador_data['username'],
                    ambassador_data['social_handles'],
                    ambassador_data['platforms'],
                    ambassador_data['current_month_points'],
                    ambassador_data['total_points'],
                    ambassador_data['consecutive_months'],
                    ambassador_data['reward_tier'],
                    ambassador_data['status']
                ))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO ambassadors (
                        discord_id, username, social_handles, target_platforms, 
                        joined_date, total_points, current_month_points, 
                        consecutive_months, reward_tier, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ambassador_data['discord_id'],
                    ambassador_data['username'],
                    ambassador_data['social_handles'],
                    ambassador_data.get('platforms', 'all'),
                    datetime.now().isoformat(),
                    ambassador_data['total_points'],
                    ambassador_data['current_month_points'],
                    ambassador_data['consecutive_months'],
                    ambassador_data['reward_tier'],
                    ambassador_data['status']
                ))
            conn.commit()
            print("✅ Added darktiding to local database")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to add to local database: {e}")
        return False

def verify_ambassador_data():
    """Verify ambassador data in both databases"""
    
    print("\n🔍 Verifying ambassador data...")
    
    # Check Supabase
    if SUPABASE_AVAILABLE:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            try:
                supabase: Client = create_client(supabase_url, supabase_key)
                result = supabase.table('ambassadors').select('*').execute()
                print(f"📊 Supabase: {len(result.data)} ambassadors")
                for amb in result.data:
                    print(f"  - {amb.get('username')} (ID: {amb.get('discord_id')})")
            except Exception as e:
                print(f"❌ Supabase check failed: {e}")
    
    # Check local database
    try:
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT discord_id, username, status FROM ambassadors')
            ambassadors = cursor.fetchall()
            print(f"📊 Local DB: {len(ambassadors)} ambassadors")
            for amb in ambassadors:
                print(f"  - {amb[1]} (ID: {amb[0]}, Status: {amb[2]})")
    except Exception as e:
        print(f"❌ Local DB check failed: {e}")

if __name__ == "__main__":
    print("🚀 Fixing Ambassador Persistence...")
    
    print("\n1. Syncing data from Supabase to local database...")
    sync_ambassador_data()
    
    print("\n2. Adding darktiding as ambassador...")
    add_darktiding_to_both_databases()
    
    print("\n3. Verifying data...")
    verify_ambassador_data()
    
    print("\n✅ Ambassador persistence fix complete!")
    print("\n💡 The bot should now remember ambassadors across restarts.")
    print("   If issues persist, the problem might be in the bot's startup sequence.")
