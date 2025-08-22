#!/usr/bin/env python3
"""
Test Ambassador Role Sync Functionality
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection"""
    try:
        from supabase import create_client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials")
            return False
        
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase connection successful")
        
        # Test ambassadors table
        try:
            result = supabase.table('ambassadors').select('*').limit(1).execute()
            print("✅ Ambassadors table accessible")
            
            # Count records
            all_records = supabase.table('ambassadors').select('*').execute()
            print(f"📊 Current ambassadors: {len(all_records.data)}")
            
            # Show existing ambassadors
            if all_records.data:
                print("Current ambassadors:")
                for amb in all_records.data:
                    print(f"  - {amb.get('username', 'Unknown')} (ID: {amb.get('discord_id', 'Unknown')}) - Status: {amb.get('status', 'Unknown')}")
            else:
                print("⚠️ No ambassadors in database yet")
                
            return True
            
        except Exception as e:
            if 'does not exist' in str(e):
                print("❌ Ambassadors table does not exist")
                print("\n🔧 To fix this, run these SQL commands in your Supabase dashboard:")
                print("""
-- Create ambassadors table
CREATE TABLE ambassadors (
    id SERIAL PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    social_handles TEXT DEFAULT '',
    platforms TEXT DEFAULT 'all',
    current_month_points INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    consecutive_months INTEGER DEFAULT 0,
    reward_tier TEXT DEFAULT 'none',
    status TEXT DEFAULT 'active',
    weekly_posts TEXT DEFAULT '0000',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create submissions table
CREATE TABLE submissions (
    id SERIAL PRIMARY KEY,
    ambassador_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    post_type TEXT,
    url TEXT,
    screenshot_hash TEXT,
    engagement_data TEXT,
    content_preview TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    points_awarded INTEGER DEFAULT 0,
    is_duplicate BOOLEAN DEFAULT FALSE,
    validity_status TEXT DEFAULT 'pending',
    gemini_analysis TEXT
);
                """)
            else:
                print(f"❌ Table access error: {e}")
            return False
            
    except ImportError:
        print("❌ Supabase library not installed")
        print("Run: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_add_sample_ambassador():
    """Test adding a sample ambassador"""
    try:
        from supabase import create_client
        
        supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
        
        # Try to add a test ambassador
        test_ambassador = {
            'discord_id': '123456789012345678',  # Sample Discord ID
            'username': 'test_ambassador',
            'social_handles': 'test_handle',
            'platforms': 'all',
            'current_month_points': 0,
            'total_points': 0,
            'consecutive_months': 0,
            'reward_tier': 'none',
            'status': 'active',
            'weekly_posts': '0000'
        }
        
        # Check if test ambassador already exists
        existing = supabase.table('ambassadors').select('*').eq('discord_id', '123456789012345678').execute()
        
        if existing.data:
            print("✅ Test ambassador already exists")
        else:
            result = supabase.table('ambassadors').insert(test_ambassador).execute()
            print("✅ Successfully added test ambassador")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to add test ambassador: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Ambassador Sync Functionality\n")
    
    # Test 1: Supabase connection
    print("1️⃣ Testing Supabase connection...")
    if test_supabase_connection():
        print("✅ Connection test passed\n")
        
        # Test 2: Add sample ambassador
        print("2️⃣ Testing ambassador insertion...")
        if test_add_sample_ambassador():
            print("✅ Ambassador insertion test passed")
        else:
            print("❌ Ambassador insertion test failed")
    else:
        print("❌ Connection test failed")
        print("\n🔧 Fix the Supabase tables first, then Jim can sync ambassadors from Discord roles")
