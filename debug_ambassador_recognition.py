#!/usr/bin/env python3
"""
Debug Ambassador Recognition Issues
Checks local database, Supabase sync, and provides diagnostic information
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("⚠️ Supabase not installed - checking local database only")
    SUPABASE_AVAILABLE = False

def check_local_database():
    """Check local SQLite database for ambassadors"""
    print("🔍 Checking local ambassador database...")
    
    try:
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            
            # Check if ambassadors table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ambassadors'")
            if not cursor.fetchone():
                print("❌ Ambassadors table does not exist in local database!")
                return False
            
            # Get table schema
            cursor.execute("PRAGMA table_info(ambassadors)")
            columns = cursor.fetchall()
            print(f"📋 Table schema: {[col[1] for col in columns]}")
            
            # Count total ambassadors
            cursor.execute("SELECT COUNT(*) FROM ambassadors")
            total_count = cursor.fetchone()[0]
            print(f"👥 Total ambassadors in local DB: {total_count}")
            
            # Count active ambassadors
            cursor.execute("SELECT COUNT(*) FROM ambassadors WHERE status = 'active'")
            active_count = cursor.fetchone()[0]
            print(f"✅ Active ambassadors: {active_count}")
            
            # Show all ambassadors
            cursor.execute("SELECT discord_id, username, status FROM ambassadors ORDER BY username")
            ambassadors = cursor.fetchall()
            
            print("\n📋 All ambassadors in local database:")
            for discord_id, username, status in ambassadors:
                status_emoji = "✅" if status == "active" else "❌"
                print(f"  {status_emoji} {username} (ID: {discord_id}) - Status: {status}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error checking local database: {e}")
        return False

def check_supabase_database():
    """Check Supabase database for ambassadors"""
    if not SUPABASE_AVAILABLE:
        print("⚠️ Supabase not available - skipping cloud database check")
        return False
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("⚠️ Supabase credentials not found - skipping cloud database check")
        return False
    
    print("\n🌐 Checking Supabase database...")
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Get all ambassadors from Supabase
        result = supabase.table('ambassadors').select('*').execute()
        ambassadors = result.data
        
        print(f"👥 Total ambassadors in Supabase: {len(ambassadors)}")
        
        active_ambassadors = [amb for amb in ambassadors if amb.get('status') == 'active']
        print(f"✅ Active ambassadors in Supabase: {len(active_ambassadors)}")
        
        print("\n📋 All ambassadors in Supabase:")
        for ambassador in ambassadors:
            discord_id = ambassador.get('discord_id')
            username = ambassador.get('username')
            status = ambassador.get('status', 'unknown')
            status_emoji = "✅" if status == "active" else "❌"
            print(f"  {status_emoji} {username} (ID: {discord_id}) - Status: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Supabase database: {e}")
        return False

def check_specific_user(discord_id):
    """Check if a specific Discord ID is in the ambassador database"""
    print(f"\n🔍 Checking specific user ID: {discord_id}")
    
    # Check local database
    try:
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT discord_id, username, status, current_month_points, total_points FROM ambassadors WHERE discord_id = ?', 
                (str(discord_id),)
            )
            result = cursor.fetchone()
            
            if result:
                discord_id_db, username, status, month_pts, total_pts = result
                print(f"✅ Found in local DB: {username} (Status: {status}, Month: {month_pts} pts, Total: {total_pts} pts)")
            else:
                print("❌ NOT found in local database")
    
    except Exception as e:
        print(f"❌ Error checking local database for user: {e}")
    
    # Check Supabase
    if SUPABASE_AVAILABLE:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            try:
                supabase = create_client(supabase_url, supabase_key)
                result = supabase.table('ambassadors').select('*').eq('discord_id', str(discord_id)).execute()
                
                if result.data:
                    ambassador = result.data[0]
                    username = ambassador.get('username')
                    status = ambassador.get('status')
                    month_pts = ambassador.get('current_month_points', 0)
                    total_pts = ambassador.get('total_points', 0)
                    print(f"✅ Found in Supabase: {username} (Status: {status}, Month: {month_pts} pts, Total: {total_pts} pts)")
                else:
                    print("❌ NOT found in Supabase database")
                    
            except Exception as e:
                print(f"❌ Error checking Supabase for user: {e}")

def sync_from_supabase_to_local():
    """Sync ambassadors from Supabase to local database"""
    if not SUPABASE_AVAILABLE:
        print("⚠️ Cannot sync - Supabase not available")
        return False
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("⚠️ Cannot sync - Supabase credentials not found")
        return False
    
    print("\n🔄 Syncing ambassadors from Supabase to local database...")
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        result = supabase.table('ambassadors').select('*').execute()
        supabase_ambassadors = result.data
        
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            
            # Detect local schema
            cursor.execute("PRAGMA table_info(ambassadors)")
            cols = [row[1] for row in cursor.fetchall()]
            has_platforms = 'platforms' in cols
            has_target_platforms = 'target_platforms' in cols
            has_joined_date = 'joined_date' in cols
            
            print(f"📋 Local schema detected: platforms={has_platforms}, target_platforms={has_target_platforms}, joined_date={has_joined_date}")
            
            synced_count = 0
            for ambassador in supabase_ambassadors:
                try:
                    if has_platforms and not has_joined_date:
                        # Current schema
                        cursor.execute('''
                            INSERT OR REPLACE INTO ambassadors (
                                discord_id, username, social_handles, platforms, 
                                current_month_points, total_points, 
                                consecutive_months, reward_tier, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            ambassador.get('discord_id'),
                            ambassador.get('username'),
                            ambassador.get('social_handles'),
                            ambassador.get('target_platforms') or ambassador.get('platforms') or 'all',
                            ambassador.get('current_month_points', 0),
                            ambassador.get('total_points', 0),
                            ambassador.get('consecutive_months', 0),
                            ambassador.get('reward_tier', 'none'),
                            ambassador.get('status', 'active')
                        ))
                    elif has_target_platforms and has_joined_date:
                        # Legacy schema
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
                            ambassador.get('joined_date', '2024-01-01'),
                            ambassador.get('total_points', 0),
                            ambassador.get('current_month_points', 0),
                            ambassador.get('consecutive_months', 0),
                            ambassador.get('reward_tier', 'none'),
                            ambassador.get('status', 'active')
                        ))
                    
                    synced_count += 1
                    
                except Exception as e:
                    print(f"⚠️ Failed to sync ambassador {ambassador.get('username', 'unknown')}: {e}")
                    continue
            
            conn.commit()
            print(f"✅ Synced {synced_count} ambassadors from Supabase to local database")
            return True
            
    except Exception as e:
        print(f"❌ Error syncing from Supabase: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🔧 Ambassador Recognition Diagnostic Tool")
    print("=" * 50)
    
    # Check local database
    local_ok = check_local_database()
    
    # Check Supabase database
    supabase_ok = check_supabase_database()
    
    # Get user input for specific Discord ID to check
    print("\n" + "=" * 50)
    discord_id = input("Enter Discord ID to check (or press Enter to skip): ").strip()
    
    if discord_id:
        try:
            discord_id = int(discord_id)
            check_specific_user(discord_id)
        except ValueError:
            print("❌ Invalid Discord ID format")
    
    # Offer to sync if Supabase is available
    if supabase_ok and not local_ok:
        print("\n" + "=" * 50)
        sync_choice = input("Local database seems empty but Supabase has data. Sync now? (y/n): ").strip().lower()
        if sync_choice == 'y':
            sync_from_supabase_to_local()
    
    print("\n🔧 Diagnostic complete!")
    print("\nIf you're still not recognized as an ambassador:")
    print("1. Make sure you're added to both local and Supabase databases")
    print("2. Check that your status is 'active'")
    print("3. Restart the bot after making database changes")
    print("4. Use !ambassador-recover command to scan chat history")

if __name__ == "__main__":
    main()
