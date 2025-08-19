#!/usr/bin/env python3
"""
Final check and cleanup of the bottom section
"""
import asyncio
import os
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager
import aiohttp

async def final_cleanup():
    """Final cleanup check"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    
    print(f"🔍 Final cleanup check...")
    
    # Initialize the Google Sheets manager
    sheets_manager = GoogleSheetsManager(spreadsheet_id, credentials_path)
    
    # Get access token
    token = await sheets_manager.get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Clear the entire bottom section to be sure
    range_name_clear = "Issue Log!A1000:J1020"
    clear_body = {
        "values": [[""] * 10 for _ in range(21)]  # Clear 21 rows with empty values
    }
    
    url_clear = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name_clear}"
    params = {"valueInputOption": "USER_ENTERED"}
    
    async with aiohttp.ClientSession() as session:
        async with session.put(url_clear, headers=headers, params=params, json=clear_body) as response:
            if response.status == 200:
                print("✅ Cleared entire bottom section (rows 1000-1020)")
            else:
                print(f"❌ Failed to clear bottom section: {response.status}")
        
        # Now check if it's actually clean
        async with session.get(f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name_clear}", headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                values = data.get('values', [])
                if values:
                    print(f"⚠️ Still found {len(values)} rows at bottom")
                else:
                    print("✅ Bottom section is now completely clean!")
            else:
                print(f"❌ Failed to check bottom section")

if __name__ == "__main__":
    asyncio.run(final_cleanup())
