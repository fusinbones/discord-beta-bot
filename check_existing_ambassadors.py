#!/usr/bin/env python3
"""
Check for existing ambassador data in Supabase
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found")
        exit(1)
    
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Connected to Supabase")
    
    # Check if ambassadors table exists and has data
    try:
        result = supabase.table('ambassadors').select('*').execute()
        ambassadors = result.data
        
        print(f"📋 Found {len(ambassadors)} ambassadors in Supabase:")
        
        if ambassadors:
            for ambassador in ambassadors:
                print(f"   - {ambassador['username']} (ID: {ambassador['discord_id']}) - Status: {ambassador['status']}")
                print(f"     Points: {ambassador['current_month_points']} this month, {ambassador['total_points']} total")
        else:
            print("⚠️ No ambassadors found in the table")
            
    except Exception as e:
        print(f"❌ Error accessing ambassadors table: {e}")
        
        # Check if table exists at all
        try:
            # Try to get table info
            result = supabase.rpc('get_table_info', {'table_name': 'ambassadors'}).execute()
            print("📋 Table exists but may be empty or have permission issues")
        except:
            print("❌ Ambassadors table does not exist")
    
    # Check submissions table too
    try:
        result = supabase.table('submissions').select('*').execute()
        submissions = result.data
        print(f"📋 Found {len(submissions)} submissions in Supabase")
        
        if submissions:
            print("Recent submissions:")
            for submission in submissions[-5:]:  # Show last 5
                print(f"   - {submission['ambassador_id']}: {submission['platform']} ({submission['points_awarded']} pts)")
                
    except Exception as e:
        print(f"❌ Error accessing submissions table: {e}")
        
except Exception as e:
    print(f"❌ Connection error: {e}")
