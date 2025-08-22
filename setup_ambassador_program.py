#!/usr/bin/env python3
"""
Setup Ambassador Program in Supabase
Creates the required tables and adds initial ambassador data
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("❌ Supabase library not installed. Install with: pip install supabase")
    exit(1)

def create_ambassador_tables():
    """Create ambassador tables in Supabase"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
        return False
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
        
        # Create ambassadors table
        print("🔄 Creating ambassadors table...")
        ambassadors_sql = """
        CREATE TABLE IF NOT EXISTS public.ambassadors (
            id BIGSERIAL PRIMARY KEY,
            discord_id TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            social_handles TEXT,
            platforms TEXT DEFAULT 'all',
            current_month_points INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0,
            consecutive_months INTEGER DEFAULT 0,
            reward_tier TEXT DEFAULT 'none',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Create submissions table
        print("🔄 Creating submissions table...")
        submissions_sql = """
        CREATE TABLE IF NOT EXISTS public.submissions (
            id BIGSERIAL PRIMARY KEY,
            ambassador_id TEXT NOT NULL,
            platform TEXT,
            post_type TEXT,
            url TEXT,
            screenshot_hash TEXT,
            engagement_data JSONB,
            content_preview TEXT,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            points_awarded INTEGER DEFAULT 0,
            is_duplicate BOOLEAN DEFAULT FALSE,
            validity_status TEXT DEFAULT 'accepted',
            gemini_analysis JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Execute SQL via RPC (if available) or direct table operations
        try:
            # Try to create tables using SQL
            result = supabase.rpc('exec_sql', {'sql': ambassadors_sql}).execute()
            print("✅ Ambassadors table created")
            
            result = supabase.rpc('exec_sql', {'sql': submissions_sql}).execute()
            print("✅ Submissions table created")
            
        except Exception as e:
            print(f"⚠️ Could not create tables via SQL: {e}")
            print("📋 Please run the following SQL in your Supabase SQL Editor:")
            print("\n" + "="*60)
            print(ambassadors_sql)
            print(submissions_sql)
            print("="*60 + "\n")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Supabase: {e}")
        return False

def add_sample_ambassador():
    """Add a sample ambassador for testing"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        return False
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Get Discord ID from user input
        discord_id = input("Enter your Discord ID to add as an ambassador (or press Enter to skip): ").strip()
        
        if discord_id:
            username = input("Enter your Discord username: ").strip() or "TestAmbassador"
            
            ambassador_data = {
                'discord_id': discord_id,
                'username': username,
                'social_handles': 'Discord: ' + username,
                'platforms': 'all',
                'current_month_points': 0,
                'total_points': 0,
                'consecutive_months': 0,
                'reward_tier': 'none',
                'status': 'active'
            }
            
            result = supabase.table('ambassadors').insert(ambassador_data).execute()
            print(f"✅ Added {username} as ambassador with Discord ID {discord_id}")
            return True
        else:
            print("⏭️ Skipping ambassador creation")
            return True
            
    except Exception as e:
        print(f"❌ Error adding ambassador: {e}")
        return False

def verify_setup():
    """Verify the ambassador program setup"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        return False
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Test ambassadors table
        result = supabase.table('ambassadors').select('*').execute()
        print(f"✅ Ambassadors table working - {len(result.data)} ambassadors found")
        
        # Test submissions table
        result = supabase.table('submissions').select('*').execute()
        print(f"✅ Submissions table working - {len(result.data)} submissions found")
        
        # Show ambassadors
        if result.data:
            print("\n📋 Current ambassadors:")
            for ambassador in result.data:
                print(f"   - {ambassador['username']} (ID: {ambassador['discord_id']}) - Status: {ambassador['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Ambassador Program Setup")
    print("=" * 40)
    
    # Create tables
    if create_ambassador_tables():
        print("✅ Tables created successfully")
        
        # Add sample ambassador
        if add_sample_ambassador():
            print("✅ Ambassador setup complete")
            
            # Verify setup
            if verify_setup():
                print("\n🎉 Ambassador program is ready!")
                print("You can now restart Jim and the ambassador program will work.")
            else:
                print("⚠️ Setup verification failed")
        else:
            print("⚠️ Ambassador creation failed")
    else:
        print("❌ Table creation failed")
        print("\n📋 Manual Setup Required:")
        print("1. Go to your Supabase project dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Run the SQL from create_supabase_tables.sql")
        print("4. Re-run this script")

if __name__ == "__main__":
    main()
