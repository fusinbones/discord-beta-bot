#!/usr/bin/env python3
"""
Test the fixed append method to ensure it goes to the correct next row
"""
import asyncio
import os
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def test_fixed_append():
    """Test the fixed append method"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    
    print(f"🧪 Testing fixed append method...")
    
    # Initialize the Google Sheets manager
    sheets_manager = GoogleSheetsManager(spreadsheet_id, credentials_path)
    
    # Test bug data
    bug_data = {
        'bug_id': 888,
        'area': 'Discord Bot',
        'description': 'TEST - Fixed append method',
        'username': 'TestUser',
        'added_by': 'Cascade',
        'timestamp': '2025-06-27',
        'status': 'Open',
        'channel_id': '123456789'
    }
    
    # Add the bug using the fixed method
    result = await sheets_manager.add_bug_to_sheet(bug_data)
    
    if result:
        print(f"✅ Test bug added successfully with fixed append method!")
        print(f"🔗 Check the sheet to verify it's in the correct location (should be right after existing data)")
    else:
        print(f"❌ Test bug insertion failed")

if __name__ == "__main__":
    asyncio.run(test_fixed_append())
