#!/usr/bin/env python3
"""
Test the fixed bug insertion to ensure it goes to the correct row
"""
import asyncio
import os
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def test_bug_insertion():
    """Test inserting a bug at the correct row"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    
    print(f"🧪 Testing bug insertion at correct row...")
    
    # Initialize the Google Sheets manager
    sheets_manager = GoogleSheetsManager(spreadsheet_id, credentials_path)
    
    # Test bug data
    bug_data = {
        'bug_id': 999,
        'area': 'Discord Bot',
        'description': 'TEST BUG - Row placement fix test',
        'username': 'TestUser',
        'added_by': 'Cascade',
        'timestamp': '2025-06-27',
        'status': 'Open',
        'channel_id': '123456789'
    }
    
    # First, check what row it should go to
    next_row = await sheets_manager.get_next_available_row()
    print(f"🎯 Next available row should be: {next_row}")
    
    # Add the bug
    result = await sheets_manager.add_bug_to_sheet(bug_data)
    
    if result:
        print(f"✅ Test bug added successfully! Should be at row {next_row}")
        print(f"🔗 Check the sheet to verify it's in the right place")
    else:
        print(f"❌ Test bug insertion failed")

if __name__ == "__main__":
    asyncio.run(test_bug_insertion())
