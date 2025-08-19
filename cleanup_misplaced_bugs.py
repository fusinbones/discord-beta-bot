#!/usr/bin/env python3
"""
Clean up the misplaced bugs that were added at the bottom of the sheet
"""
import asyncio
import os
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager
import aiohttp

async def cleanup_misplaced_bugs():
    """Move misplaced bugs from bottom of sheet to correct location"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    
    print(f"🧹 Cleaning up misplaced bugs...")
    
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
    
    # Read the misplaced bugs from the bottom
    range_name_bottom = "Issue Log!A1000:J1020"
    url_bottom = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name_bottom}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url_bottom, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                values_bottom = data.get('values', [])
                
                # Find actual bug data (not just row numbers)
                misplaced_bugs = []
                for i, row in enumerate(values_bottom):
                    if len(row) > 3 and row[1] == "Issue" and row[2] == "Discord Bot":
                        row_num = 1000 + i + 1
                        misplaced_bugs.append((row_num, row))
                        print(f"🐛 Found misplaced bug at row {row_num}: {row[3][:50]}...")
                
                if misplaced_bugs:
                    print(f"📋 Found {len(misplaced_bugs)} misplaced bugs to move")
                    
                    # Get the next available row for proper placement
                    next_row = await sheets_manager.get_next_available_row()
                    
                    # Move each bug to the correct location
                    for i, (old_row, bug_data) in enumerate(misplaced_bugs):
                        new_row = next_row + i
                        
                        # Insert bug at correct location
                        range_name_new = f"Issue Log!A{new_row}:J{new_row}"
                        body = {"values": [bug_data]}
                        url_new = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name_new}"
                        params = {"valueInputOption": "USER_ENTERED"}
                        
                        async with session.put(url_new, headers=headers, params=params, json=body) as response_new:
                            if response_new.status == 200:
                                print(f"✅ Moved bug from row {old_row} to row {new_row}")
                                
                                # Clear the old location
                                range_name_old = f"Issue Log!A{old_row}:J{old_row}"
                                clear_body = {"values": [[""] * 10]}  # Clear with empty values
                                url_old = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name_old}"
                                
                                async with session.put(url_old, headers=headers, params=params, json=clear_body) as response_clear:
                                    if response_clear.status == 200:
                                        print(f"🧹 Cleared old location at row {old_row}")
                                    else:
                                        print(f"⚠️ Failed to clear row {old_row}")
                            else:
                                print(f"❌ Failed to move bug from row {old_row}")
                    
                    print(f"✅ Cleanup complete! Moved {len(misplaced_bugs)} bugs to correct locations")
                else:
                    print("✅ No misplaced bugs found")
            else:
                print(f"❌ Failed to read bottom of sheet: {response.status}")

if __name__ == "__main__":
    asyncio.run(cleanup_misplaced_bugs())
