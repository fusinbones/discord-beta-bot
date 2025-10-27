"""
Fast cleanup of duplicate bugs in Google Sheets using batch deletion
Keeps only the first occurrence of each bug ID
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def cleanup_duplicates_fast():
    """Remove duplicate bugs from the spreadsheet using batch operations"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = 'config/google_service_account.json'
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID not set in environment")
        return
    
    print(f"🧹 Starting FAST duplicate cleanup for spreadsheet: {spreadsheet_id}")
    
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
    
    print(f"\n⚠️ WARNING: About to delete {len(duplicate_rows)} duplicate rows in BATCHES")
    print(f"   This will be much faster than one-by-one deletion")
    print(f"\n⏱️ Estimated time: ~30 seconds")
    
    confirmation = input("\n🔴 Type 'DELETE' to proceed with fast cleanup: ")
    
    if confirmation != "DELETE":
        print("❌ Cleanup cancelled")
        return
    
    print(f"\n🗑️ Deleting {len(duplicate_rows)} duplicate rows in batches...")
    
    # Sort rows in reverse order to avoid index shifting
    duplicate_rows.sort(reverse=True)
    
    # Create deletion requests in batches
    batch_size = 100  # Delete 100 rows per batch
    total_deleted = 0
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(duplicate_rows), batch_size):
            batch = duplicate_rows[i:i + batch_size]
            
            # Build batch delete request
            delete_requests = []
            for row_number in batch:
                delete_requests.append({
                    "deleteDimension": {
                        "range": {
                            "sheetId": 0,  # Assuming first sheet
                            "dimension": "ROWS",
                            "startIndex": row_number - 1,  # 0-indexed
                            "endIndex": row_number  # exclusive
                        }
                    }
                })
            
            batch_request = {
                "requests": delete_requests
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
            
            async with session.post(url, headers=headers, json=batch_request) as response:
                if response.status == 200:
                    total_deleted += len(batch)
                    percent = (total_deleted / len(duplicate_rows)) * 100
                    print(f"✅ Batch complete: {total_deleted}/{len(duplicate_rows)} rows deleted ({percent:.1f}%)")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to delete batch: {response.status} - {error_text}")
                    print(f"⚠️ Stopping at {total_deleted} deletions")
                    break
            
            # Small delay between batches
            await asyncio.sleep(0.5)
    
    print(f"\n🎉 Cleanup complete! Deleted {total_deleted} duplicate rows")
    print(f"✅ Remaining unique bugs: {len(seen_bugs)}")
    print(f"\n💡 Next step: Restart Jim to prevent future duplicates")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates_fast())
