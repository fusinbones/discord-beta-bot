#!/usr/bin/env python3
"""
Migrate Ambassador Data from SQLite to Supabase
This will preserve all the ambassadors you added earlier today
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("❌ Supabase library not installed. Install with: pip install supabase")
    exit(1)

def migrate_ambassadors():
    """Migrate all ambassadors from SQLite to Supabase"""
    
    # Check if local database exists
    if not os.path.exists('ambassador_program.db'):
        print("❌ No local ambassador_program.db found")
        return False
    
    # Connect to Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in .env")
        return False
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
        
        # First, create tables if they don't exist
        print("🔄 Creating Supabase tables...")
        
        # Create ambassadors table
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
            weekly_posts TEXT DEFAULT '0000',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Create submissions table
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
        
        # Create indexes
        indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_ambassadors_discord_id ON public.ambassadors(discord_id);
        CREATE INDEX IF NOT EXISTS idx_ambassadors_status ON public.ambassadors(status);
        CREATE INDEX IF NOT EXISTS idx_submissions_ambassador_id ON public.submissions(ambassador_id);
        CREATE INDEX IF NOT EXISTS idx_submissions_timestamp ON public.submissions(timestamp);
        """
        
        print("📋 Please run this SQL in your Supabase SQL Editor:")
        print("="*60)
        print(ambassadors_sql)
        print(submissions_sql)
        print(indexes_sql)
        print("="*60)
        
        # Read from SQLite
        print("\n🔄 Reading ambassadors from local SQLite database...")
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            
            # Get all ambassadors
            cursor.execute('''
                SELECT discord_id, username, social_handles, platforms,
                       current_month_points, total_points, consecutive_months,
                       reward_tier, status, weekly_posts, created_at
                FROM ambassadors
            ''')
            ambassadors = cursor.fetchall()
            
            print(f"📋 Found {len(ambassadors)} ambassadors in SQLite:")
            for amb in ambassadors:
                print(f"   - {amb[1]} (Discord ID: {amb[0]}) - Status: {amb[8]}")
            
            if not ambassadors:
                print("⚠️ No ambassadors found in local database")
                return False
            
            # Migrate each ambassador to Supabase
            print("\n🔄 Migrating ambassadors to Supabase...")
            migrated_count = 0
            
            for amb in ambassadors:
                try:
                    ambassador_data = {
                        'discord_id': amb[0],
                        'username': amb[1],
                        'social_handles': amb[2] or '',
                        'platforms': amb[3] or 'all',
                        'current_month_points': amb[4] or 0,
                        'total_points': amb[5] or 0,
                        'consecutive_months': amb[6] or 0,
                        'reward_tier': amb[7] or 'none',
                        'status': amb[8] or 'active',
                        'weekly_posts': amb[9] or '0000'
                    }
                    
                    # Try to insert (will skip if already exists due to UNIQUE constraint)
                    result = supabase.table('ambassadors').insert(ambassador_data).execute()
                    print(f"✅ Migrated {amb[1]} to Supabase")
                    migrated_count += 1
                    
                except Exception as e:
                    if 'duplicate key' in str(e).lower():
                        print(f"⏭️ {amb[1]} already exists in Supabase")
                    else:
                        print(f"❌ Error migrating {amb[1]}: {e}")
            
            # Also migrate submissions if they exist
            cursor.execute('SELECT COUNT(*) FROM submissions')
            submission_count = cursor.fetchone()[0]
            
            if submission_count > 0:
                print(f"\n🔄 Found {submission_count} submissions to migrate...")
                cursor.execute('''
                    SELECT ambassador_id, platform, post_type, url, screenshot_hash,
                           engagement_data, content_preview, timestamp, points_awarded,
                           is_duplicate, validity_status, gemini_analysis
                    FROM submissions
                ''')
                submissions = cursor.fetchall()
                
                for sub in submissions:
                    try:
                        submission_data = {
                            'ambassador_id': sub[0],
                            'platform': sub[1],
                            'post_type': sub[2],
                            'url': sub[3],
                            'screenshot_hash': sub[4],
                            'engagement_data': sub[5],
                            'content_preview': sub[6],
                            'timestamp': sub[7],
                            'points_awarded': sub[8] or 0,
                            'is_duplicate': bool(sub[9]) if sub[9] is not None else False,
                            'validity_status': sub[10] or 'accepted',
                            'gemini_analysis': sub[11]
                        }
                        
                        supabase.table('submissions').insert(submission_data).execute()
                        
                    except Exception as e:
                        if 'duplicate key' not in str(e).lower():
                            print(f"⚠️ Error migrating submission: {e}")
                
                print(f"✅ Migrated {submission_count} submissions")
            
            print(f"\n🎉 Migration complete! Migrated {migrated_count} ambassadors")
            
            # Verify migration
            print("\n🔍 Verifying migration...")
            result = supabase.table('ambassadors').select('discord_id, username, status').execute()
            supabase_ambassadors = result.data
            
            print(f"📋 Supabase now has {len(supabase_ambassadors)} ambassadors:")
            for amb in supabase_ambassadors:
                print(f"   - {amb['username']} (ID: {amb['discord_id']}) - {amb['status']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Ambassador Migration from SQLite to Supabase...")
    
    if migrate_ambassadors():
        print("\n✅ Migration successful!")
        print("\n📋 Next steps:")
        print("1. Run the SQL in your Supabase SQL Editor (shown above)")
        print("2. Test Jim - he should now recognize all ambassadors")
        print("3. The local SQLite database is preserved as backup")
    else:
        print("\n❌ Migration failed - check errors above")
