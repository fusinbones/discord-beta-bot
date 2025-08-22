#!/usr/bin/env python3
"""
Check Supabase database status and existing tables
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
    print(f"🔗 URL: {supabase_url}")
    
    # Check if ambassadors table exists and has data
    print("\n🔍 Checking ambassadors table...")
    try:
        result = supabase.table('ambassadors').select('*').execute()
        ambassadors = result.data
        
        print(f"📋 Found {len(ambassadors)} ambassadors in Supabase:")
        
        if ambassadors:
            for ambassador in ambassadors:
                print(f"   - {ambassador['username']} (ID: {ambassador['discord_id']}) - Status: {ambassador['status']}")
                print(f"     Points: {ambassador['current_month_points']} this month, {ambassador['total_points']} total")
        else:
            print("⚠️ Ambassadors table exists but is empty")
            
    except Exception as e:
        print(f"❌ Error accessing ambassadors table: {e}")
        if "relation \"public.ambassadors\" does not exist" in str(e):
            print("❌ Ambassadors table does not exist")
        elif "permission denied" in str(e).lower():
            print("❌ Permission denied - check your Supabase key permissions")
    
    # Check submissions table
    print("\n🔍 Checking submissions table...")
    try:
        result = supabase.table('submissions').select('*').execute()
        submissions = result.data
        print(f"📋 Found {len(submissions)} submissions in Supabase")
        
        if submissions:
            print("Recent submissions:")
            for submission in submissions[-5:]:  # Show last 5
                print(f"   - {submission['ambassador_id']}: {submission['platform']} ({submission['points_awarded']} pts)")
        else:
            print("⚠️ Submissions table exists but is empty")
                
    except Exception as e:
        print(f"❌ Error accessing submissions table: {e}")
        if "relation \"public.submissions\" does not exist" in str(e):
            print("❌ Submissions table does not exist")
        
except ImportError:
    print("❌ Supabase library not installed. Install with: pip install supabase")
except Exception as e:
    print(f"❌ Connection error: {e}")
