#!/usr/bin/env python3
"""
Check the current data in the Google Sheet to see where bugs should be added
"""
import asyncio
import os
from dotenv import load_dotenv
from google_sheets_integration import GoogleSheetsManager

async def check_sheet_data():
    """Check the current data in the Google Sheet"""
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    
    print(f"🔍 Checking current data in Google Sheet...")
    
    # Initialize the Google Sheets manager
    sheets_manager = GoogleSheetsManager(spreadsheet_id, credentials_path)
    
    # Get access token
    token = await sheets_manager.get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return
    
    # Read the current data to see where it ends
    import aiohttp
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Read a range that should include all current data
    range_name = "Issue Log!A1:J100"  # Read first 100 rows
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                values = data.get('values', [])
                
                print(f"📊 Found {len(values)} rows of data")
                
                # Find the last row with actual data
                last_data_row = 0
                for i, row in enumerate(values):
                    # Check if row has any non-empty data
                    if any(cell.strip() for cell in row if cell):
                        last_data_row = i + 1
                
                print(f"📍 Last row with data: {last_data_row}")
                print(f"➡️  Next available row should be: {last_data_row + 1}")
                
                # Show the last few rows with data
                print(f"\n📋 Last 5 rows with data:")
                start_idx = max(0, last_data_row - 5)
                for i in range(start_idx, min(last_data_row, len(values))):
                    row = values[i]
                    row_num = i + 1
                    # Show first few columns
                    preview = [cell[:20] + "..." if len(cell) > 20 else cell for cell in row[:4]]
                    print(f"Row {row_num}: {preview}")
                
                # Check if there are any rows way down at the bottom (like row 1010)
                print(f"\n🔍 Checking for data at the bottom of sheet...")
                range_name_bottom = "Issue Log!A1000:J1020"
                url_bottom = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name_bottom}"
                
                async with session.get(url_bottom, headers=headers) as response_bottom:
                    if response_bottom.status == 200:
                        data_bottom = await response_bottom.json()
                        values_bottom = data_bottom.get('values', [])
                        if values_bottom:
                            print(f"⚠️  Found {len(values_bottom)} rows of data at the bottom (rows 1000+)!")
                            for i, row in enumerate(values_bottom):
                                if any(cell.strip() for cell in row if cell):
                                    row_num = 1000 + i + 1
                                    preview = [cell[:20] + "..." if len(cell) > 20 else cell for cell in row[:4]]
                                    print(f"Row {row_num}: {preview}")
                        else:
                            print("✅ No data found at the bottom of the sheet")
            else:
                print(f"❌ Failed to read sheet data: {response.status}")

if __name__ == "__main__":
    asyncio.run(check_sheet_data())
