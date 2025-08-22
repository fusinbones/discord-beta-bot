#!/usr/bin/env python3
"""
Quick script to add an ambassador to Supabase
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
    
    # Add your Discord ID here
    discord_id = input("Enter your Discord ID: ").strip()
    username = input("Enter your Discord username: ").strip()
    
    ambassador_data = {
        'discord_id': discord_id,
        'username': username,
        'social_handles': f'Discord: {username}',
        'platforms': 'all',
        'current_month_points': 0,
        'total_points': 0,
        'consecutive_months': 0,
        'reward_tier': 'none',
        'status': 'active'
    }
    
    result = supabase.table('ambassadors').insert(ambassador_data).execute()
    print(f"✅ Added {username} as ambassador!")
    
    # Verify
    result = supabase.table('ambassadors').select('*').execute()
    print(f"📋 Total ambassadors: {len(result.data)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
