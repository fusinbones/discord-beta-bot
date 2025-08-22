#!/usr/bin/env python3
"""
Railway Environment Debug - Check ambassador program status
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def debug_railway_environment():
    """Debug Railway environment for ambassador program"""
    print("🚂 Railway Environment Debug")
    print(f"Python version: {sys.version}")
    
    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"\n🔧 Environment Variables:")
    print(f"SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    print(f"SUPABASE_ANON_KEY: {'✅ Set' if supabase_key else '❌ Missing'}")
    
    # Check required libraries
    print(f"\n📦 Required Libraries:")
    
    try:
        import discord
        print(f"discord.py: ✅ {discord.__version__}")
    except ImportError as e:
        print(f"discord.py: ❌ {e}")
    
    try:
        from supabase import create_client
        print("supabase: ✅ Installed")
        
        if supabase_url and supabase_key:
            try:
                supabase = create_client(supabase_url, supabase_key)
                result = supabase.table('ambassadors').select('*').limit(1).execute()
                print("supabase connection: ✅ Working")
                
                total_ambassadors = len(supabase.table('ambassadors').select('*').execute().data)
                print(f"ambassadors table: ✅ {total_ambassadors} records")
                
            except Exception as e:
                print(f"supabase connection: ❌ {e}")
        else:
            print("supabase connection: ⚠️ Missing credentials")
            
    except ImportError as e:
        print(f"supabase: ❌ {e}")
    
    try:
        import google.generativeai as genai
        print("google-generativeai: ✅ Installed")
    except ImportError as e:
        print(f"google-generativeai: ❌ {e}")
    
    # Test ambassador program initialization
    print(f"\n🤖 Ambassador Program Test:")
    try:
        from ambassador_program import AmbassadorProgram
        
        class MockBot:
            pass
        
        mock_bot = MockBot()
        ambassador_program = AmbassadorProgram(mock_bot)
        print("AmbassadorProgram: ✅ Initialized successfully")
        print(f"Supabase client: {'✅' if ambassador_program.supabase else '❌'}")
        
    except Exception as e:
        print(f"AmbassadorProgram: ❌ {e}")
        print("This is why role sync isn't working!")

if __name__ == "__main__":
    debug_railway_environment()
