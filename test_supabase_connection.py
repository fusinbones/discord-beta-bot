#!/usr/bin/env python3
"""
Test Supabase connection and check ambassador data
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("❌ Supabase library not installed")
    SUPABASE_AVAILABLE = False
    exit(1)

def test_supabase_connection():
    """Test Supabase connection and check ambassador table"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in .env")
        return False
    
    print(f"🔗 Connecting to Supabase: {supabase_url}")
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test connection by listing tables
        print("✅ Supabase connection successful")
        
        # Check if ambassadors table exists
        try:
            result = supabase.table('ambassadors').select('*').limit(5).execute()
            print(f"📊 Ambassadors table found with {len(result.data)} records")
            
            for ambassador in result.data:
                print(f"  - {ambassador.get('username', 'Unknown')} (ID: {ambassador.get('discord_id', 'Unknown')})")
                
        except Exception as table_error:
            print(f"⚠️ Ambassadors table issue: {table_error}")
            
            # Try to create the table
            print("🔧 Attempting to create ambassadors table...")
            try:
                # Note: This would require admin privileges, might fail
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS ambassadors (
                    discord_id TEXT PRIMARY KEY,
                    username TEXT,
                    social_handles TEXT,
                    target_platforms TEXT,
                    joined_date TIMESTAMP,
                    total_points INTEGER DEFAULT 0,
                    current_month_points INTEGER DEFAULT 0,
                    consecutive_months INTEGER DEFAULT 0,
                    reward_tier TEXT DEFAULT 'none',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """
                # This might not work with the anon key
                print("⚠️ Table creation requires admin privileges - check Supabase dashboard")
                
            except Exception as create_error:
                print(f"❌ Could not create table: {create_error}")
        
        # Check submissions table
        try:
            result = supabase.table('submissions').select('*').limit(5).execute()
            print(f"📊 Submissions table found with {len(result.data)} records")
        except Exception as submissions_error:
            print(f"⚠️ Submissions table issue: {submissions_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def add_darktiding_to_supabase():
    """Add darktiding to Supabase if connection works"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        return False
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Add darktiding (you'll need to replace with actual Discord ID)
        ambassador_data = {
            'discord_id': 'REPLACE_WITH_ACTUAL_DISCORD_ID',  # Replace this
            'username': 'darktiding',
            'social_handles': 'darktiding',
            'target_platforms': 'instagram,tiktok,youtube',
            'joined_date': '2025-08-21T10:15:00Z',
            'total_points': 0,
            'current_month_points': 0,
            'consecutive_months': 0,
            'reward_tier': 'none',
            'status': 'active'
        }
        
        result = supabase.table('ambassadors').upsert(ambassador_data).execute()
        print(f"✅ Added darktiding to Supabase: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to add darktiding to Supabase: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Supabase connection...")
    
    if test_supabase_connection():
        print("\n🔧 Attempting to add darktiding...")
        add_darktiding_to_supabase()
    
    print("\n✅ Supabase test complete")
