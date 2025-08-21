#!/usr/bin/env python3
"""
Comprehensive Ambassador Persistence Fix
This script ensures ambassador data persists across bot restarts by:
1. Fixing database initialization
2. Adding data synchronization between Supabase and local DB
3. Adding darktiding as ambassador
4. Implementing startup data sync in the bot
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
    print("❌ Supabase library not installed - run: pip install supabase")
    SUPABASE_AVAILABLE = False

class AmbassadorPersistenceFix:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase = None
        
        if SUPABASE_AVAILABLE and self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                print("✅ Supabase connection established")
            except Exception as e:
                print(f"❌ Supabase connection failed: {e}")
        else:
            print("⚠️ Supabase not available - using local database only")
    
    def initialize_local_database(self):
        """Initialize local SQLite database with proper schema"""
        try:
            # Remove empty database file if it exists
            if os.path.exists('ambassador_program.db') and os.path.getsize('ambassador_program.db') == 0:
                os.remove('ambassador_program.db')
                print("🗑️ Removed empty database file")
            
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
                print("✅ Local database initialized")
                return True
                
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    def sync_from_supabase_to_local(self):
        """Sync ambassador data from Supabase to local database"""
        if not self.supabase:
            print("⚠️ Supabase not available - skipping sync")
            return False
        
        try:
            # Get all ambassadors from Supabase
            result = self.supabase.table('ambassadors').select('*').execute()
            supabase_ambassadors = result.data
            
            print(f"📥 Found {len(supabase_ambassadors)} ambassadors in Supabase")
            
            # Sync to local database
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                
                # Detect local schema columns
                cursor.execute("PRAGMA table_info(ambassadors)")
                cols = [row[1] for row in cursor.fetchall()]
                has_platforms = 'platforms' in cols and 'joined_date' not in cols
                has_target_platforms = 'target_platforms' in cols and 'joined_date' in cols

                for ambassador in supabase_ambassadors:
                    if has_platforms:
                        cursor.execute('''
                            INSERT OR REPLACE INTO ambassadors (
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
                            INSERT OR REPLACE INTO ambassadors (
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
            print(f"❌ Sync from Supabase failed: {e}")
            return False
    
    def add_darktiding_ambassador(self, discord_id):
        """Add darktiding as ambassador to both databases"""
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
        
        success = True
        
        # Add to Supabase
        if self.supabase:
            try:
                result = self.supabase.table('ambassadors').upsert(ambassador_data).execute()
                print("✅ Added darktiding to Supabase")
            except Exception as e:
                print(f"❌ Failed to add to Supabase: {e}")
                success = False
        
        # Add to local database
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                # Detect schema
                cursor.execute("PRAGMA table_info(ambassadors)")
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
                
        except Exception as e:
            print(f"❌ Failed to add to local database: {e}")
            success = False
        
        return success
    
    def verify_ambassador_data(self):
        """Verify ambassador data in both databases"""
        print("\n🔍 Verifying ambassador data...")
        
        # Check Supabase
        if self.supabase:
            try:
                result = self.supabase.table('ambassadors').select('*').execute()
                print(f"📊 Supabase: {len(result.data)} ambassadors")
                for amb in result.data:
                    print(f"  - {amb.get('username')} (ID: {amb.get('discord_id')}, Status: {amb.get('status')})")
            except Exception as e:
                print(f"❌ Supabase check failed: {e}")
        
        # Check local database
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT discord_id, username, status FROM ambassadors WHERE status = "active"')
                ambassadors = cursor.fetchall()
                print(f"📊 Local DB: {len(ambassadors)} active ambassadors")
                for discord_id, username, status in ambassadors:
                    print(f"  - {username} (ID: {discord_id}, Status: {status})")
        except Exception as e:
            print(f"❌ Local DB check failed: {e}")
    
    def create_startup_sync_patch(self):
        """Create a patch for the bot to sync data on startup"""
        patch_code = """
# Add this to the bot's on_ready event to ensure data persistence
async def sync_ambassador_data_on_startup(self):
    '''Sync ambassador data from Supabase to local DB on bot startup'''
    if not hasattr(self, 'ambassador_program') or not self.ambassador_program.supabase:
        return
    
    try:
        print("🔄 Syncing ambassador data from Supabase...")
        result = self.ambassador_program.supabase.table('ambassadors').select('*').execute()
        supabase_ambassadors = result.data
        
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            # Detect schema
            cursor.execute("PRAGMA table_info(ambassadors)")
            cols = [row[1] for row in cursor.fetchall()]
            has_platforms = 'platforms' in cols and 'joined_date' not in cols
            
            # Sync each ambassador
            for ambassador in supabase_ambassadors:
                if has_platforms:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ambassadors (
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
                else:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ambassadors (
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
            
            conn.commit()
            print(f"✅ Synced {len(supabase_ambassadors)} ambassadors from Supabase")
            
    except Exception as e:
        print(f"⚠️ Startup sync failed: {e}")
"""
        
        with open('startup_sync_patch.py', 'w') as f:
            f.write(patch_code)
        
        print("📝 Created startup_sync_patch.py - add this to bot's on_ready event")

def main():
    print("🚀 Starting comprehensive ambassador persistence fix...")
    
    fixer = AmbassadorPersistenceFix()
    
    # Step 1: Initialize local database
    print("\n1. Initializing local database...")
    fixer.initialize_local_database()
    
    # Step 2: Sync from Supabase
    print("\n2. Syncing data from Supabase...")
    fixer.sync_from_supabase_to_local()
    
    # Step 3: Add darktiding
    print("\n3. Adding darktiding as ambassador...")
    discord_id = input("Enter darktiding's Discord ID (get it from Discord with Developer Mode): ").strip()
    
    if discord_id and discord_id.isdigit():
        fixer.add_darktiding_ambassador(discord_id)
    else:
        print("⚠️ Invalid Discord ID - skipping darktiding addition")
    
    # Step 4: Verify data
    print("\n4. Verifying ambassador data...")
    fixer.verify_ambassador_data()
    
    # Step 5: Create startup sync patch
    print("\n5. Creating startup sync patch...")
    fixer.create_startup_sync_patch()
    
    print("\n✅ Ambassador persistence fix complete!")
    print("\n📋 Next steps:")
    print("   1. Restart your bot to test persistence")
    print("   2. Use '!ambassador add @darktiding instagram,tiktok,youtube' command")
    print("   3. Add the startup sync code to your bot's on_ready event")
    print("   4. Your ambassador status should now persist across restarts")

if __name__ == "__main__":
    main()
