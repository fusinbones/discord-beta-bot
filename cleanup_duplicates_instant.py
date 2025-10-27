"""
INSTANT duplicate cleanup using Google Sheets' built-in Remove Duplicates feature
This is by far the fastest method - completes in seconds regardless of row count
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def cleanup_duplicates_instant():
    """Remove duplicates using Google Sheets' native RemoveDuplicates feature"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = 'config/google_service_account.json'
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID not set in environment")
        return
    
    print(f"⚡ Starting INSTANT duplicate cleanup using Google Sheets' native feature")
    print(f"📊 Spreadsheet: {spreadsheet_id}")
    
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
    
    # Get sheet metadata to find the row count
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"❌ Failed to get spreadsheet info: {response.status}")
                return
            
            sheet_data = await response.json()
            sheets = sheet_data.get('sheets', [])
            
            if not sheets:
                print("❌ No sheets found")
                return
            
            # Get first sheet info
            sheet = sheets[0]
            sheet_id = sheet['properties']['sheetId']
            grid_properties = sheet['properties'].get('gridProperties', {})
            row_count = grid_properties.get('rowCount', 0)
            
            print(f"📋 Sheet ID: {sheet_id}")
            print(f"📊 Total rows: {row_count}")
    
    print(f"\n⚡ Using Google Sheets' RemoveDuplicates feature...")
    print(f"💡 This will keep the FIRST occurrence of each duplicate bug ID")
    print(f"⏱️ Operation completes in seconds!")
    
    confirmation = input("\n🔴 Type 'DELETE' to proceed with instant cleanup: ")
    
    if confirmation != "DELETE":
        print("❌ Cleanup cancelled")
        return
    
    # Use the DeleteDuplicatesRequest to remove duplicates based on column A (Bug #)
    remove_duplicates_request = {
        "requests": [
            {
                "deleteDuplicates": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 29,  # Row 30 (0-indexed)
                        "endRowIndex": row_count,
                        "startColumnIndex": 0,  # Column A
                        "endColumnIndex": 10  # Through column J
                    },
                    "comparisonColumns": [
                        {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,  # Column A (Bug #)
                            "endIndex": 1
                        }
                    ]
                }
            }
        ]
    }
    
    print(f"\n🗑️ Removing duplicates based on Bug # column (Column A)...")
    
    async with aiohttp.ClientSession() as session:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
        
        async with session.post(url, headers=headers, json=remove_duplicates_request) as response:
            response_text = await response.text()
            
            if response.status == 200:
                result = await response.json()
                
                # The response tells us how many duplicates were removed
                if 'replies' in result and len(result['replies']) > 0:
                    reply = result['replies'][0]
                    if 'deleteDuplicates' in reply:
                        duplicates_removed = reply['deleteDuplicates'].get('duplicatesRemovedCount', 0)
                        print(f"\n🎉 SUCCESS!")
                        print(f"✅ Removed {duplicates_removed} duplicate rows")
                        print(f"⚡ Completed in seconds!")
                    else:
                        print(f"\n✅ Operation completed successfully!")
                        print(f"📄 Response: {response_text}")
                else:
                    print(f"\n✅ Duplicates removed successfully!")
            else:
                print(f"❌ Error: {response.status}")
                print(f"💬 Details: {response_text}")
    
    print(f"\n💡 Next step: Restart Jim to prevent future duplicates")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates_instant())
