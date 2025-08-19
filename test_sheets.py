#!/usr/bin/env python3
"""
Test script to verify Google Sheets integration
"""
import asyncio
import os
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def test_sheets_connection():
    """Test the Google Sheets connection and permissions"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    
    print(f"🔧 Testing Google Sheets connection...")
    print(f"📊 Spreadsheet ID: {spreadsheet_id}")
    print(f"🔑 Credentials path: {credentials_path}")
    print(f"📁 Credentials file exists: {os.path.exists(credentials_path) if credentials_path else 'No path set'}")
    
    if not spreadsheet_id or not credentials_path:
        print("❌ Missing environment variables!")
        print("Required: GOOGLE_SPREADSHEET_ID, GOOGLE_SERVICE_ACCOUNT_PATH")
        return
    
    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found at: {credentials_path}")
        return
    
    # Initialize the Google Sheets manager
    try:
        sheets_manager = GoogleSheetsManager(spreadsheet_id, credentials_path)
        print("✅ GoogleSheetsManager initialized")
    except Exception as e:
        print(f"❌ Failed to initialize GoogleSheetsManager: {e}")
        return
    
    # Test getting access token
    try:
        print("🔄 Testing access token...")
        token = await sheets_manager.get_access_token()
        if token:
            print("✅ Access token obtained successfully")
            print(f"🔑 Token preview: {token[:20]}...")
        else:
            print("❌ Failed to get access token")
            return
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test adding a bug to the sheet
    try:
        print("🔄 Testing bug insertion...")
        test_bug_data = {
            'bug_id': 999,
            'username': 'TestUser',
            'description': 'TEST BUG - Please ignore this entry',
            'timestamp': '2024-01-01T12:00:00',
            'status': 'test',
            'channel_id': '123456789',
            'guild_id': '987654321',
            'added_by': 'TestScript'
        }
        
        result = await sheets_manager.add_bug_to_sheet(test_bug_data)
        if result:
            print("✅ Test bug added successfully!")
            print("🎉 Google Sheets integration is working!")
        else:
            print("❌ Failed to add test bug")
    except Exception as e:
        print(f"❌ Error adding test bug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sheets_connection())
