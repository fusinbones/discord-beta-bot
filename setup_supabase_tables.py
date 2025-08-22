#!/usr/bin/env python3
"""
Setup Supabase tables for Ambassador Program
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in .env")
        exit(1)
    
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Connected to Supabase")
    
    # Create ambassadors table
    print("🔧 Creating ambassadors table...")
    try:
        # First check if table exists
        result = supabase.table('ambassadors').select('*').limit(1).execute()
        print("✅ Ambassadors table already exists")
        current_count = len(supabase.table('ambassadors').select('*').execute().data)
        print(f"   Current records: {current_count}")
    except Exception as e:
        if 'does not exist' in str(e):
            print("❌ Ambassadors table does not exist")
            print("⚠️  You need to create the table in Supabase dashboard with this SQL:")
            print("""
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
            """)
        else:
            print(f"❌ Error: {e}")
    
    # Create submissions table
    print("\n🔧 Checking submissions table...")
    try:
        result = supabase.table('submissions').select('*').limit(1).execute()
        print("✅ Submissions table already exists")
    except Exception as e:
        if 'does not exist' in str(e):
            print("❌ Submissions table does not exist")
            print("⚠️  You need to create the table in Supabase dashboard with this SQL:")
            print("""
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
    gemini_analysis TEXT,
    FOREIGN KEY (ambassador_id) REFERENCES ambassadors(discord_id)
);
            """)
        else:
            print(f"❌ Error: {e}")
            
except ImportError:
    print("❌ Supabase library not installed. Install with: pip install supabase")
except Exception as e:
    print(f"❌ Connection error: {e}")
