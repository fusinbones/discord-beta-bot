"""
Smart cleanup of duplicate bugs respecting Google Sheets API rate limits
Uses range-based deletion to delete multiple consecutive rows at once
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def cleanup_duplicates_smart():
    """Remove duplicate bugs using optimized range-based deletion"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = 'config/google_service_account.json'
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID not set in environment")
        return
    
    print(f"🧹 Starting SMART duplicate cleanup for spreadsheet: {spreadsheet_id}")
    
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
                duplicate_rows.append(actual_row)
            else:
                seen_bugs[bug_id] = actual_row
        except (ValueError, TypeError):
            continue
    
    print(f"\n📊 Summary:")
    print(f"   Unique bugs: {len(seen_bugs)}")
    print(f"   Duplicates found: {len(duplicate_rows)}")
    
    if not duplicate_rows:
        print("✅ No duplicates to clean up!")
        return
    
    # Sort in reverse order
    duplicate_rows.sort(reverse=True)
    
    # Group consecutive rows into ranges for efficient deletion
    ranges_to_delete = []
    current_range_start = duplicate_rows[0]
    current_range_end = duplicate_rows[0]
    
    for row in duplicate_rows[1:]:
        if row == current_range_end - 1:  # Consecutive
            current_range_end = row
        else:  # New range
            ranges_to_delete.append((current_range_end, current_range_start + 1))
            current_range_start = row
            current_range_end = row
    
    # Don't forget the last range
    ranges_to_delete.append((current_range_end, current_range_start + 1))
    
    print(f"\n💡 Optimized: {len(duplicate_rows)} rows grouped into {len(ranges_to_delete)} deletion ranges")
    print(f"⏱️ Estimated time: {len(ranges_to_delete) // 2} minutes (respecting API limits)")
    
    confirmation = input("\n🔴 Type 'DELETE' to proceed: ")
    
    if confirmation != "DELETE":
        print("❌ Cleanup cancelled")
        return
    
    print(f"\n🗑️ Deleting duplicates in {len(ranges_to_delete)} efficient operations...")
    
    total_deleted = 0
    batch_requests = []
    
    async with aiohttp.ClientSession() as session:
        for i, (start_row, end_row) in enumerate(ranges_to_delete):
            # Add to current batch
            batch_requests.append({
                "deleteDimension": {
                    "range": {
                        "sheetId": 0,
                        "dimension": "ROWS",
                        "startIndex": start_row - 1,  # 0-indexed
                        "endIndex": end_row  # exclusive
                    }
                }
            })
            
            rows_in_range = end_row - start_row
            
            # Send batch every 50 ranges or at the end
            if len(batch_requests) >= 50 or i == len(ranges_to_delete) - 1:
                batch_request = {"requests": batch_requests}
                url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
                
                async with session.post(url, headers=headers, json=batch_request) as response:
                    if response.status == 200:
                        total_deleted += sum(r['deleteDimension']['range']['endIndex'] - 
                                           r['deleteDimension']['range']['startIndex'] 
                                           for r in batch_requests)
                        percent = (total_deleted / len(duplicate_rows)) * 100
                        print(f"✅ Progress: {total_deleted}/{len(duplicate_rows)} deleted ({percent:.1f}%)")
                    else:
                        error_text = await response.text()
                        print(f"❌ Error: {response.status} - {error_text[:200]}")
                        print(f"⏸️ Pausing and retrying in 60 seconds...")
                        await asyncio.sleep(60)
                        continue
                
                batch_requests = []
                
                # Respect rate limit: wait between batches
                if i < len(ranges_to_delete) - 1:
                    await asyncio.sleep(2)
    
    print(f"\n🎉 Cleanup complete! Deleted {total_deleted} duplicate rows")
    print(f"✅ Remaining unique bugs: {len(seen_bugs)}")
    print(f"\n💡 Next step: Restart Jim to prevent future duplicates")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates_smart())
