#!/usr/bin/env python3
"""
Debug Ambassador Program Initialization
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_ambassador_program_init():
    """Test if AmbassadorProgram can be initialized"""
    print("🔧 Testing Ambassador Program initialization...")
    
    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    print(f"SUPABASE_ANON_KEY: {'✅ Set' if supabase_key else '❌ Missing'}")
    
    if supabase_url:
        print(f"URL: {supabase_url}")
    
    # Check if Supabase library is available
    try:
        from supabase import create_client
        print("✅ Supabase library installed")
    except ImportError:
        print("❌ Supabase library not installed")
        print("Run: pip install supabase")
        return False
    
    # Try to create Supabase client
    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
            print("✅ Supabase client created successfully")
            
            # Test connection
            result = supabase.table('ambassadors').select('*').limit(1).execute()
            print("✅ Supabase connection working")
            print(f"Ambassadors table accessible with {len(supabase.table('ambassadors').select('*').execute().data)} records")
            
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            return False
    else:
        print("❌ Missing Supabase credentials")
        return False
    
    # Try to initialize AmbassadorProgram
    try:
        from ambassador_program import AmbassadorProgram
        
        # Create a mock bot object
        class MockBot:
            pass
        
        mock_bot = MockBot()
        ambassador_program = AmbassadorProgram(mock_bot)
        print("✅ AmbassadorProgram initialized successfully")
        print(f"Supabase client: {'✅ Available' if ambassador_program.supabase else '❌ Not available'}")
        
        return True
        
    except Exception as e:
        print(f"❌ AmbassadorProgram initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ambassador_program_init()
    
    if success:
        print("\n✅ Ambassador Program should work correctly")
        print("If Jim still isn't syncing roles, restart the bot")
    else:
        print("\n❌ Ambassador Program initialization failed")
        print("Fix the issues above before expecting role sync to work")
