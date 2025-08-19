#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from self_update_system import SelfUpdateSystem

class MockBot:
    pass

async def test_emergency_autofix():
    print("🚨 TESTING EMERGENCY AUTO-FIX for krafty10 (400+ items)")
    
    mock_bot = MockBot()
    updater = SelfUpdateSystem(mock_bot)
    
    # Test the specific error scenarios
    test_cases = [
        "Insufficient credits to perform this request. 402 error",
        "crawled 1 pages - closet has over 400 items", 
        "Low page count for Poshmark infinite scroll - may need more scroll actions"
    ]
    
    for i, error_msg in enumerate(test_cases, 1):
        print(f"\n🔧 Test {i}: {error_msg}")
        
        try:
            result = await updater.auto_fix_api_issues(error_msg)
            print(f"   Result: {'✅ FIXED' if result else '❌ No fix applied'}")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n🚀 Emergency auto-fix test complete!")

if __name__ == "__main__":
    asyncio.run(test_emergency_autofix())
