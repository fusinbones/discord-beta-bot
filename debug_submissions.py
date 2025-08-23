#!/usr/bin/env python3
"""
Debug Ambassador Submissions - Check if sync is working
"""

import os
from dotenv import load_dotenv

load_dotenv()

def check_submissions_table():
    """Check submissions table in Supabase"""
    try:
        from supabase import create_client
        
        supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
        print("✅ Connected to Supabase")
        
        # Check submissions table
        try:
            result = supabase.table('submissions').select('*').execute()
            submissions = result.data
            
            print(f"📊 Submissions table: {len(submissions)} total records")
            
            if submissions:
                print("\nRecent submissions:")
                for i, sub in enumerate(submissions[-10:]):  # Show last 10
                    print(f"{i+1}. Ambassador: {sub.get('ambassador_id', 'Unknown')}")
                    print(f"   Platform: {sub.get('platform', 'Unknown')}")
                    print(f"   URL: {sub.get('url', 'No URL')[:50]}...")
                    print(f"   Points: {sub.get('points_awarded', 0)}")
                    print(f"   Status: {sub.get('validity_status', 'Unknown')}")
                    print(f"   Timestamp: {sub.get('timestamp', 'Unknown')}")
                    print()
            else:
                print("⚠️ No submissions found in table")
                
            # Check by ambassador
            print("\n📋 Submissions by ambassador:")
            ambassadors_result = supabase.table('ambassadors').select('discord_id', 'username').eq('status', 'active').execute()
            
            for amb in ambassadors_result.data[:5]:  # Check first 5 ambassadors
                discord_id = amb['discord_id']
                username = amb['username']
                
                amb_submissions = supabase.table('submissions').select('*').eq('ambassador_id', discord_id).execute()
                print(f"  {username}: {len(amb_submissions.data)} submissions")
                
        except Exception as e:
            print(f"❌ Error accessing submissions table: {e}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

def check_ambassador_channels():
    """Check what channels would be scanned"""
    print("\n🔍 Ambassador channel detection logic:")
    print("Looking for channels with keywords: 'ambassador', 'content-creator', 'influencer'")
    print("This would need to be run from within Discord bot context")

if __name__ == "__main__":
    print("🔧 Debugging Ambassador Submissions\n")
    check_submissions_table()
    check_ambassador_channels()
