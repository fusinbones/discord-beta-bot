"""
Google Sheets Integration for Bug Tracking
Integrates with Jim's bug tracking system to sync bugs to a Google Spreadsheet
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
import aiohttp
import asyncio
import jwt
import time

class GoogleSheetsManager:
    def __init__(self, spreadsheet_id: str, credentials_path: str):
        """
        Initialize Google Sheets Manager
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            credentials_path: Path to Google service account credentials JSON
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self.base_url = "https://sheets.googleapis.com/v4/spreadsheets"
        self.access_token = None
        self.token_expires = 0
        
        # Spreadsheet headers - match the SDK Issue Log format exactly
        self.headers = [
            "Issue Type", "Area", "Description", "Solution", 
            "Responsible", "Reported by", "Date Created", "Status", "Comments"
        ]
        
    async def get_access_token(self):
        """Get OAuth2 access token using service account credentials"""
        try:
            # Load service account credentials
            with open(self.credentials_path, 'r') as f:
                credentials = json.load(f)
            
            # Create JWT token for service account authentication
            now = int(time.time())
            payload = {
                'iss': credentials['client_email'],
                'scope': 'https://www.googleapis.com/auth/spreadsheets',
                'aud': 'https://oauth2.googleapis.com/token',
                'iat': now,
                'exp': now + 3600  # Token expires in 1 hour
            }
            
            # Sign the JWT with the private key
            private_key = credentials['private_key']
            jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
            
            # Exchange JWT for access token
            token_data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': jwt_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://oauth2.googleapis.com/token', data=token_data) as response:
                    if response.status == 200:
                        token_response = await response.json()
                        self.access_token = token_response['access_token']
                        self.token_expires = now + token_response.get('expires_in', 3600)
                        logging.info("✅ Successfully obtained Google Sheets access token")
                        return self.access_token
                    else:
                        error_text = await response.text()
                        logging.error(f"Failed to get access token: {response.status} - {error_text}")
                        return None
            
        except Exception as e:
            logging.error(f"Failed to get Google Sheets access token: {e}")
            return None
    
    async def add_bug_to_sheet(self, bug_data: Dict):
        """Add a new bug to the Google Sheet"""
        try:
            # Map the bug data to match spreadsheet columns
            values = [
                bug_data.get('bug_id', ''),  # Bug # (column A)  
                "Issue",  # Issue Type (column B) - defaulting to "Issue" for Discord bugs
                bug_data.get('area', 'Other'),  # Area (column C) - default to Other if not detected
                bug_data.get('description', ''),  # Description (column D)
                "",  # Solution (column E) - empty initially
                "",  # Responsible (column F) - empty initially  
                f"{bug_data.get('username', '')} (Added by: {bug_data.get('added_by', bug_data.get('username', ''))})",  # Reported by (column G)
                bug_data.get('timestamp', ''),  # Date entered (column H)
                bug_data.get('status', 'Open'),  # Status (column I)
                f"Discord Bug #{bug_data.get('bug_id', '')} - Channel: <#{bug_data.get('channel_id', '')}>"  # Comments (column J)
            ]
            
            # Use a targeted range that will append after existing data in the used range
            range_name = "Issue Log!A1:J"  # This will append to the used range, not the entire sheet
            body = {
                "values": [values]
            }
            
            # Add the row to the sheet
            token = await self.get_access_token()
            if not token:
                raise Exception("Failed to get access token")
                
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}:append"
            params = {
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS"
            }
            
            async with aiohttp.ClientSession() as session:
                print(f"🔄 Attempting to add bug to Google Sheets...")
                print(f"📊 Bug data: {bug_data}")
                print(f"📝 Values to insert: {values}")
                print(f"🎯 Range: {range_name}")
                print(f"🔗 URL: {url}")
                
                async with session.post(url, headers=headers, params=params, json=body) as response:
                    response_text = await response.text()
                    print(f"📡 Response status: {response.status}")
                    print(f"📄 Response: {response_text}")
                    
                    if response.status == 200:
                        print(f"✅ Bug #{bug_data.get('bug_id', '')} added to spreadsheet successfully")
                        return True
                    else:
                        print(f"❌ Failed to add bug to spreadsheet: {response.status}")
                        print(f"💬 Error details: {response_text}")
                        return False
                        
        except Exception as e:
            return False
    
    async def update_bug_status(self, bug_id: int, new_status: str) -> bool:
        """Update the status of a bug in the spreadsheet"""
        try:
            print(f"🔍 Searching for bug #{bug_id} in spreadsheet...")
            
            # Find the bug in the spreadsheet
            bug_row = await self.find_bug_row(bug_id)
            if not bug_row:
                print(f"⚠️ Bug #{bug_id} not found in spreadsheet")
                print(f"💡 Make sure the bug was synced to Google Sheets")
                return False
            
            print(f"✅ Found bug #{bug_id} at row {bug_row}")
            
            token = await self.get_access_token()
            if not token:
                print(f"❌ Failed to get access token for Google Sheets")
                raise Exception("Failed to get access token")
                
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Update the Status column (column I) for the found row
            range_name = f"Issue Log!I{bug_row}"  # Status column with sheet name
            body = {
                "values": [[new_status]]
            }
            
            print(f"📝 Updating range: {range_name} with status: {new_status}")
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            params = {
                "valueInputOption": "USER_ENTERED"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=body) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        print(f"✅ Updated bug #{bug_id} status to '{new_status}' in Google Sheets")
                        print(f"📊 Response: {response_text}")
                        return True
                    else:
                        print(f"❌ Failed to update bug status: {response.status}")
                        print(f"💬 Error details: {response_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Error updating bug status: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def resolve_bug(self, bug_id: int) -> bool:
        """Mark a bug as resolved by updating its status instead of deleting it"""
        return await self.update_bug_status(bug_id, "Resolved")
    
    async def remove_closed_bug(self, bug_id: int) -> bool:
        """
        Remove a closed bug from the spreadsheet
        
        Args:
            bug_id: Bug ID to remove
        """
        try:
            if not await self.get_access_token():
                return False
            
            # Find the row with this bug ID
            bug_row = await self.find_bug_row(bug_id)
            if bug_row is None:
                logging.warning(f"Bug #{bug_id} not found in spreadsheet")
                return False
            
            # Delete the row
            url = f"{self.base_url}/{self.spreadsheet_id}:batchUpdate"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'requests': [{
                    'deleteDimension': {
                        'range': {
                            'sheetId': 0,  # Assuming first sheet
                            'dimension': 'ROWS',
                            'startIndex': bug_row - 1,  # 0-indexed
                            'endIndex': bug_row
                        }
                    }
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        logging.info(f"✅ Removed bug #{bug_id} from spreadsheet")
                        return True
                    else:
                        logging.error(f"❌ Failed to remove bug from spreadsheet: {response.status}")
                        return False
                        
        except Exception as e:
            logging.error(f"Error removing bug from spreadsheet: {e}")
            return False
    
    async def find_bug_row(self, bug_id: int) -> int:
        """Find the row number of a bug by searching in the Bug # column (column A)"""
        try:
            print(f"🔎 Looking for bug #{bug_id} in Bug # column...")
            
            token = await self.get_access_token()
            if not token:
                print(f"❌ No access token available")
                return None
                
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Get all data from Bug # column (column A) starting from row 30
            range_name = "Issue Log!A30:A"
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            
            print(f"📊 Fetching range: {range_name}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        values = data.get('values', [])
                        
                        print(f"📋 Found {len(values)} rows to search")
                        
                        # Search for the bug ID in column A
                        print(f"🔍 Searching for bug ID: {bug_id}")
                        
                        for row_idx, row_data in enumerate(values):
                            if row_data and len(row_data) > 0:
                                cell_content = str(row_data[0]).strip()
                                # Match exact bug ID (convert to int for comparison)
                                try:
                                    if int(cell_content) == bug_id:
                                        actual_row = row_idx + 30
                                        print(f"✅ Found bug #{bug_id} at row {actual_row}")
                                        return actual_row  # Return actual row number (30-based)
                                except (ValueError, TypeError):
                                    # Skip non-numeric values
                                    continue
                        
                        print(f"⚠️ Bug #{bug_id} not found in {len(values)} rows")
                        return None  # Bug not found
                    else:
                        error_text = await response.text()
                        print(f"❌ Failed to search for bug: {response.status}")
                        print(f"💬 Error: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error searching for bug: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def initialize_spreadsheet(self) -> bool:
        """Initialize the spreadsheet with proper headers if needed"""
        try:
            # Ensure we have a valid access token
            if not self.access_token:
                if not await self.get_access_token():
                    return False
            
            # Try to read the first row to check if headers exist
            url = f"{self.base_url}/{self.spreadsheet_id}/values/Issue Log!1:1"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        values = data.get('values', [])
                        
                        # If no headers, add them
                        if not values or not values[0]:
                            return await self.add_headers()
                        
                        logging.info("✅ Spreadsheet already initialized")
                        return True
                    else:
                        error_text = await response.text()
                        logging.error(f"Failed to check spreadsheet: {response.status}")
                        logging.error(f"Error details: {error_text}")
                        print(f"❌ Detailed error: {error_text}")
                        return False
                        
        except Exception as e:
            logging.error(f"Error initializing spreadsheet: {e}")
            return False
    
    async def add_headers(self) -> bool:
        """Add headers to the spreadsheet"""
        try:
            url = f"{self.base_url}/{self.spreadsheet_id}/values/Issue Log!1:1"
            params = {'valueInputOption': 'RAW'}
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'values': [self.headers]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=payload) as response:
                    if response.status == 200:
                        logging.info("✅ Added headers to spreadsheet")
                        return True
                    else:
                        logging.error(f"❌ Failed to add headers: {response.status}")
                        return False
                        
        except Exception as e:
            logging.error(f"Error adding headers to spreadsheet: {e}")
            return False
    
    async def get_next_row_number(self) -> int:
        """Get the next available row number for the data section"""
        try:
            token = await self.get_access_token()
            if not token:
                return 1  # Default to 1 if can't get token
                
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Get data from rows 30 onwards (first column A)
            range_name = "A30:A"
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        values = data.get('values', [])
                        
                        # Find the highest existing row number
                        max_number = 0
                        for row in values:
                            if row and len(row) > 0:
                                try:
                                    row_num = int(row[0])
                                    max_number = max(max_number, row_num)
                                except (ValueError, TypeError):
                                    continue
                        
                        # Return the next number in sequence
                        return max_number + 1
                    else:
                        print(f"❌ Failed to get next row number: {response.status}")
                        return 1  # Default to 1 if request fails
                        
        except Exception as e:
            print(f"❌ Error getting next row number: {str(e)}")
            return 1  # Default to 1 if error
    
    async def get_sheet_metadata(self):
        """Get spreadsheet metadata to see available sheets"""
        try:
            if not self.access_token:
                if not await self.get_access_token():
                    return None
            
            url = f"{self.base_url}/{self.spreadsheet_id}"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logging.error(f"Failed to get metadata: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logging.error(f"Error getting sheet metadata: {e}")
            return None


# Example configuration
class BugTrackingConfig:
    """Configuration for bug tracking integration"""
    
    SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')  # Set in environment
    CREDENTIALS_PATH = 'config/google_service_account.json'  # Path to credentials
    REMOVE_CLOSED_BUGS = True  # Whether to remove closed bugs from spreadsheet
    UPDATE_STATUS_ONLY = False  # If True, just update status; if False, remove closed bugs


async def test_integration():
    """Test the Google Sheets integration"""
    config = BugTrackingConfig()
    
    if not config.SPREADSHEET_ID:
        print("❌ GOOGLE_SPREADSHEET_ID not set in environment")
        return
    
    print(f"📊 Testing with Spreadsheet ID: {config.SPREADSHEET_ID}")
    print(f"🔑 Using credentials path: {config.CREDENTIALS_PATH}")
    
    sheets_manager = GoogleSheetsManager(
        spreadsheet_id=config.SPREADSHEET_ID,
        credentials_path=config.CREDENTIALS_PATH
    )
    
    # Test getting access token first
    print("🔐 Getting access token...")
    token = await sheets_manager.get_access_token()
    if token:
        print(f"✅ Access token obtained: {token[:50]}...")
    else:
        print("❌ Failed to get access token")
        return
    
    # Test initialization
    print("📋 Testing spreadsheet access...")
    success = await sheets_manager.initialize_spreadsheet()
    if success:
        print("✅ Spreadsheet integration test passed!")
    else:
        print("❌ Spreadsheet integration test failed!")
    
    # Test getting sheet metadata
    print("📊 Getting sheet metadata...")
    metadata = await sheets_manager.get_sheet_metadata()
    if metadata:
        print("✅ Sheet metadata obtained:")
        print(metadata)
        sheets = metadata.get('sheets', [])
        sheet_names = [sheet.get('properties', {}).get('title', '') for sheet in sheets]
        print(f"Available sheets: {sheet_names}")
    else:
        print("❌ Failed to get sheet metadata")


if __name__ == "__main__":
    asyncio.run(test_integration())
