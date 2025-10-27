"""
Script to clean up duplicate bugs in Google Sheets
Keeps only the first occurrence of each bug ID
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def cleanup_duplicates():
    """Remove duplicate bugs from the spreadsheet"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = 'config/google_service_account.json'
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID not set in environment")
        return
    
    print(f"🧹 Starting duplicate cleanup for spreadsheet: {spreadsheet_id}")
    
    sheets_manager = GoogleSheetsManager(
        spreadsheet_id=spreadsheet_id,
        credentials_path=credentials_path
    )
    
    # Get access token
    token = await sheets_manager.get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get all bug IDs from column A starting at row 30
    range_name = "Issue Log!A30:A"
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
    
    print(f"📊 Fetching all bug IDs from {range_name}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"❌ Failed to fetch data: {response.status}")
                return
            
            data = await response.json()
            values = data.get('values', [])
    
    print(f"📋 Found {len(values)} rows to check")
    
    # Track which bug IDs we've seen and which rows to delete
    seen_bugs = {}  # bug_id -> first row number
    duplicate_rows = []  # list of row numbers to delete
    
    for idx, row_data in enumerate(values):
        if not row_data or len(row_data) == 0:
            continue
        
        try:
            bug_id = int(str(row_data[0]).strip())
            actual_row = idx + 30
            
            if bug_id in seen_bugs:
                # This is a duplicate
                first_row = seen_bugs[bug_id]
                print(f"🔍 Found duplicate: Bug #{bug_id} at row {actual_row} (first seen at row {first_row})")
                duplicate_rows.append(actual_row)
            else:
                # First time seeing this bug
                seen_bugs[bug_id] = actual_row
        except (ValueError, TypeError):
            # Skip non-numeric values
            continue
    
    print(f"\n📊 Summary:")
    print(f"   Unique bugs: {len(seen_bugs)}")
    print(f"   Duplicates found: {len(duplicate_rows)}")
    
    if not duplicate_rows:
        print("✅ No duplicates to clean up!")
        return
    
    print(f"\n⚠️ WARNING: About to delete {len(duplicate_rows)} duplicate rows:")
    for row in duplicate_rows[:10]:  # Show first 10
        print(f"   - Row {row}")
    if len(duplicate_rows) > 10:
        print(f"   ... and {len(duplicate_rows) - 10} more")
    
    confirmation = input("\n🔴 Type 'DELETE' to proceed with cleanup: ")
    
    if confirmation != "DELETE":
        print("❌ Cleanup cancelled")
        return
    
    print(f"\n🗑️ Deleting {len(duplicate_rows)} duplicate rows...")
    
    # Delete rows in reverse order to avoid shifting issues
    duplicate_rows.sort(reverse=True)
    
    async with aiohttp.ClientSession() as session:
        deleted_count = 0
        for row_number in duplicate_rows:
            # Delete the row using the batchUpdate API
            delete_request = {
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": 0,  # Assuming first sheet
                                "dimension": "ROWS",
                                "startIndex": row_number - 1,  # 0-indexed
                                "endIndex": row_number  # exclusive
                            }
                        }
                    }
                ]
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
            
            async with session.post(url, headers=headers, json=delete_request) as response:
                if response.status == 200:
                    deleted_count += 1
                    print(f"✅ Deleted row {row_number} ({deleted_count}/{len(duplicate_rows)})")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to delete row {row_number}: {response.status} - {error_text}")
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)
    
    print(f"\n🎉 Cleanup complete! Deleted {deleted_count} duplicate rows")
    print(f"✅ Remaining unique bugs: {len(seen_bugs)}")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
