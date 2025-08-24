"""
Google Sheets Integration for Ambassador Tracking
Integrates with Jim's ambassador system to sync ambassador data to a Google Spreadsheet
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

class AmbassadorSheetsManager:
    def __init__(self, spreadsheet_id: str, credentials_path: str, supabase_client):
        """
        Initialize Ambassador Sheets Manager
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            credentials_path: Path to Google service account credentials JSON
            supabase_client: Supabase client for database operations
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self.supabase = supabase_client
        self.base_url = "https://sheets.googleapis.com/v4/spreadsheets"
        self.access_token = None
        self.token_expires = 0
        
        # Ambassador sheet headers
        self.ambassador_headers = [
            "Discord ID", "Username", "Current Month Points", "Total Points", 
            "Submissions Count", "Last Updated", "Status", "Manual Adjustments", "Notes"
        ]
        
        # Submissions sheet headers
        self.submissions_headers = [
            "ID", "Ambassador ID", "Username", "Platform", "Post Type", "URL", 
            "Points Awarded", "Timestamp", "Status", "Screenshot Hash", "Message ID", "Notes"
        ]
        
    async def get_access_token(self):
        """Get OAuth2 access token using service account credentials"""
        try:
            # Check if token is still valid
            if self.access_token and time.time() < self.token_expires - 300:  # 5 min buffer
                return self.access_token
            
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
    
    async def full_backup_to_sheets(self):
        """Complete backup of all ambassador data and submissions to Google Sheets"""
        try:
            # Create both sheets if they don't exist
            await self.create_ambassador_sheet()
            await self.create_submissions_sheet()
            
            # Sync ambassadors
            ambassador_success = await self.sync_ambassadors_to_sheet()
            
            # Sync all submissions
            submissions_success = await self.sync_submissions_to_sheet()
            
            if ambassador_success and submissions_success:
                logging.info("✅ Complete backup to Google Sheets successful")
                return True
            else:
                logging.error("❌ Partial backup failure")
                return False
            
        except Exception as e:
            logging.error(f"Error in full backup: {e}")
            return False
    
    async def sync_ambassadors_to_sheet(self):
        """Sync all ambassador data from Supabase to Google Sheets"""
        try:
            # Get all ambassadors from Supabase (including inactive)
            result = self.supabase.table('ambassadors').select('*').execute()
            ambassadors = result.data
            
            if not ambassadors:
                logging.info("No ambassadors found to sync")
                return False
            
            # Get access token
            token = await self.get_access_token()
            if not token:
                raise Exception("Failed to get access token")
            
            # Prepare data for sheet
            sheet_data = []
            
            for ambassador in ambassadors:
                discord_id = ambassador['discord_id']
                username = ambassador['username']
                current_points = ambassador.get('current_month_points', 0)
                total_points = ambassador.get('total_points', 0)
                status = ambassador.get('status', 'active')
                
                # Get submissions count
                submissions_result = self.supabase.table('submissions').select('id').eq('ambassador_id', discord_id).execute()
                submissions_count = len(submissions_result.data)
                
                # Prepare row data
                row_data = [
                    str(discord_id),
                    username,
                    current_points,
                    total_points,
                    submissions_count,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    status.title(),
                    "",  # Manual Adjustments - empty initially
                    ambassador.get('notes', '')  # Notes from database
                ]
                
                sheet_data.append(row_data)
            
            # Clear existing data and add headers + new data
            await self.clear_ambassador_sheet_data()
            await self.add_ambassador_headers()
            
            # Add all ambassador data
            success = await self.batch_update_ambassador_sheet(sheet_data)
            
            if success:
                logging.info(f"✅ Successfully synced {len(ambassadors)} ambassadors to Google Sheets")
                return True
            else:
                logging.error("❌ Failed to sync ambassadors to Google Sheets")
                return False
            
        except Exception as e:
            logging.error(f"Error syncing ambassadors to sheet: {e}")
            return False
    
    async def sync_submissions_to_sheet(self):
        """Sync all submissions from Supabase to Google Sheets"""
        try:
            # Get all submissions from Supabase
            result = self.supabase.table('submissions').select('*').order('timestamp', desc=True).execute()
            submissions = result.data
            
            if not submissions:
                logging.info("No submissions found to sync")
                return True  # Not an error if no submissions
            
            # Get access token
            token = await self.get_access_token()
            if not token:
                raise Exception("Failed to get access token")
            
            # Prepare data for sheet
            sheet_data = []
            
            for submission in submissions:
                # Get ambassador username
                ambassador_result = self.supabase.table('ambassadors').select('username').eq('discord_id', submission['ambassador_id']).execute()
                username = ambassador_result.data[0]['username'] if ambassador_result.data else 'Unknown'
                
                # Prepare row data
                row_data = [
                    str(submission.get('id', '')),
                    str(submission.get('ambassador_id', '')),
                    username,
                    submission.get('platform', ''),
                    submission.get('post_type', ''),
                    submission.get('url', ''),
                    submission.get('points_awarded', 0),
                    submission.get('timestamp', ''),
                    submission.get('validity_status', 'pending'),
                    submission.get('screenshot_hash', ''),
                    str(submission.get('message_id', '')),
                    submission.get('notes', '')
                ]
                
                sheet_data.append(row_data)
            
            # Clear existing data and add headers + new data
            await self.clear_submissions_sheet_data()
            await self.add_submissions_headers()
            
            # Add all submission data
            success = await self.batch_update_submissions_sheet(sheet_data)
            
            if success:
                logging.info(f"✅ Successfully synced {len(submissions)} submissions to Google Sheets")
                return True
            else:
                logging.error("❌ Failed to sync submissions to Google Sheets")
                return False
            
        except Exception as e:
            logging.error(f"Error syncing submissions to sheet: {e}")
            return False
    
    async def sync_from_sheets_to_supabase(self):
        """Comprehensive sync from Google Sheets back to Supabase - sheets control everything"""
        try:
            # Sync ambassador changes
            ambassador_success = await self.sync_ambassador_changes_from_sheet()
            
            # Sync submission changes
            submission_success = await self.sync_submission_changes_from_sheet()
            
            return ambassador_success and submission_success
            
        except Exception as e:
            logging.error(f"Error in comprehensive sync from sheets: {e}")
            return False
    
    async def sync_ambassador_changes_from_sheet(self):
        """Sync ambassador data changes from Google Sheets to Supabase"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Get all ambassador data from the sheet
            range_name = "Ambassadors!A2:I"  # Skip header row
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logging.error(f"Failed to read ambassador sheet data: {response.status}")
                        return False
                    
                    data = await response.json()
                    values = data.get('values', [])
                    
                    updates_made = 0
                    
                    for row in values:
                        if len(row) >= 7:  # Minimum required columns
                            discord_id = row[0]
                            username = row[1] if len(row) > 1 else ""
                            current_points = int(row[2]) if len(row) > 2 and str(row[2]).isdigit() else 0
                            total_points = int(row[3]) if len(row) > 3 and str(row[3]).isdigit() else 0
                            status = row[6].lower() if len(row) > 6 else "active"
                            manual_adjustment = row[7] if len(row) > 7 else ""
                            notes = row[8] if len(row) > 8 else ""
                            
                            # Apply manual adjustment if present
                            if manual_adjustment and manual_adjustment.strip():
                                try:
                                    adjustment_value = int(manual_adjustment.strip())
                                    current_points += adjustment_value
                                    total_points += adjustment_value
                                    # Clear adjustment after applying
                                    await self.clear_cell(f"Ambassadors!H{values.index(row) + 2}")
                                except ValueError:
                                    logging.warning(f"Invalid manual adjustment: {manual_adjustment}")
                            
                            # Update ambassador in Supabase with sheet data
                            try:
                                self.supabase.table('ambassadors').upsert({
                                    'discord_id': discord_id,
                                    'username': username,
                                    'current_month_points': max(0, current_points),
                                    'total_points': max(0, total_points),
                                    'status': status,
                                    'notes': notes,
                                    'last_updated': datetime.now().isoformat()
                                }).execute()
                                
                                updates_made += 1
                                
                            except Exception as e:
                                logging.error(f"Failed to update ambassador {discord_id}: {e}")
                    
                    if updates_made > 0:
                        logging.info(f"✅ Updated {updates_made} ambassadors from Google Sheets")
                    
                    return True
            
        except Exception as e:
            logging.error(f"Error syncing ambassador changes from sheet: {e}")
            return False
    
    async def sync_submission_changes_from_sheet(self):
        """Sync submission data changes from Google Sheets to Supabase"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Get all submission data from the sheet
            range_name = "Submissions!A2:L"  # Skip header row
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logging.error(f"Failed to read submissions sheet data: {response.status}")
                        return False
                    
                    data = await response.json()
                    values = data.get('values', [])
                    
                    updates_made = 0
                    
                    for row in values:
                        if len(row) >= 9:  # Minimum required columns
                            submission_id = row[0] if row[0] else None
                            ambassador_id = row[1]
                            platform = row[3] if len(row) > 3 else ""
                            post_type = row[4] if len(row) > 4 else ""
                            url = row[5] if len(row) > 5 else ""
                            points_awarded = int(row[6]) if len(row) > 6 and str(row[6]).isdigit() else 0
                            timestamp = row[7] if len(row) > 7 else ""
                            status = row[8] if len(row) > 8 else "pending"
                            screenshot_hash = row[9] if len(row) > 9 else ""
                            message_id = row[10] if len(row) > 10 else ""
                            notes = row[11] if len(row) > 11 else ""
                            
                            # Update or insert submission in Supabase
                            try:
                                submission_data = {
                                    'ambassador_id': ambassador_id,
                                    'platform': platform,
                                    'post_type': post_type,
                                    'url': url,
                                    'points_awarded': points_awarded,
                                    'timestamp': timestamp,
                                    'validity_status': status,
                                    'screenshot_hash': screenshot_hash,
                                    'message_id': message_id,
                                    'notes': notes
                                }
                                
                                if submission_id and submission_id.isdigit():
                                    # Update existing submission
                                    submission_data['id'] = int(submission_id)
                                    self.supabase.table('submissions').upsert(submission_data).execute()
                                else:
                                    # Insert new submission
                                    result = self.supabase.table('submissions').insert(submission_data).execute()
                                    # Update sheet with new ID
                                    if result.data:
                                        new_id = result.data[0]['id']
                                        await self.update_cell(f"Submissions!A{values.index(row) + 2}", str(new_id))
                                
                                updates_made += 1
                                
                            except Exception as e:
                                logging.error(f"Failed to update submission {submission_id}: {e}")
                    
                    if updates_made > 0:
                        logging.info(f"✅ Updated {updates_made} submissions from Google Sheets")
                    
                    return True
            
        except Exception as e:
            logging.error(f"Error syncing submission changes from sheet: {e}")
            return False
    
    async def clear_cell(self, cell_range: str):
        """Clear a specific cell in the sheet"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{cell_range}:clear"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as response:
                    return response.status == 200
            
        except Exception as e:
            logging.error(f"Error clearing cell {cell_range}: {e}")
            return False
    
    async def update_cell(self, cell_range: str, value: str):
        """Update a specific cell in the sheet"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            body = {
                "values": [[value]]
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{cell_range}"
            params = {
                "valueInputOption": "USER_ENTERED"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=body) as response:
                    return response.status == 200
            
        except Exception as e:
            logging.error(f"Error updating cell {cell_range}: {e}")
            return False
    
    async def batch_update_ambassador_sheet(self, data: List[List]):
        """Batch update ambassador sheet with data"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Start from row 2 (after headers)
            range_name = f"Ambassadors!A2:I{len(data) + 1}"
            body = {
                "values": data
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            params = {
                "valueInputOption": "USER_ENTERED"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=body) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        logging.error(f"Failed to batch update ambassador sheet: {response.status} - {error_text}")
                        return False
            
        except Exception as e:
            logging.error(f"Error in ambassador batch update: {e}")
            return False
    
    async def batch_update_submissions_sheet(self, data: List[List]):
        """Batch update submissions sheet with data"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Start from row 2 (after headers)
            range_name = f"Submissions!A2:L{len(data) + 1}"
            body = {
                "values": data
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            params = {
                "valueInputOption": "USER_ENTERED"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=body) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        logging.error(f"Failed to batch update submissions sheet: {response.status} - {error_text}")
                        return False
            
        except Exception as e:
            logging.error(f"Error in submissions batch update: {e}")
            return False
    
    async def clear_ambassador_sheet_data(self):
        """Clear existing data from the ambassador sheet"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Clear data range (keep some buffer)
            range_name = "Ambassadors!A1:I1000"
            body = {
                "values": []
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}:clear"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as response:
                    return response.status == 200
            
        except Exception as e:
            logging.error(f"Error clearing ambassador sheet: {e}")
            return False
    
    async def clear_submissions_sheet_data(self):
        """Clear existing data from the submissions sheet"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Clear data range (keep some buffer)
            range_name = "Submissions!A1:L1000"
            body = {
                "values": []
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}:clear"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as response:
                    return response.status == 200
            
        except Exception as e:
            logging.error(f"Error clearing submissions sheet: {e}")
            return False
    
    async def add_ambassador_headers(self):
        """Add headers to the ambassador sheet"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            range_name = "Ambassadors!A1:I1"
            body = {
                "values": [self.ambassador_headers]
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            params = {
                "valueInputOption": "USER_ENTERED"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=body) as response:
                    return response.status == 200
            
        except Exception as e:
            logging.error(f"Error adding ambassador headers: {e}")
            return False
    
    async def add_submissions_headers(self):
        """Add headers to the submissions sheet"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            range_name = "Submissions!A1:L1"
            body = {
                "values": [self.submissions_headers]
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            params = {
                "valueInputOption": "USER_ENTERED"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=body) as response:
                    return response.status == 200
            
        except Exception as e:
            logging.error(f"Error adding submissions headers: {e}")
            return False
    
    async def create_ambassador_sheet(self):
        """Create the Ambassadors sheet if it doesn't exist"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Add a new sheet named "Ambassadors"
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}:batchUpdate"
            
            body = {
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": "Ambassadors",
                                "gridProperties": {
                                    "rowCount": 1000,
                                    "columnCount": 10
                                }
                            }
                        }
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as response:
                    if response.status == 200:
                        logging.info("✅ Created Ambassadors sheet")
                        return True
                    else:
                        error_text = await response.text()
                        # Sheet might already exist
                        if "already exists" in error_text.lower():
                            logging.info("Ambassadors sheet already exists")
                            return True
                        logging.error(f"Failed to create sheet: {error_text}")
                        return False
            
        except Exception as e:
            logging.error(f"Error creating ambassador sheet: {e}")
            return False
    
    async def create_submissions_sheet(self):
        """Create the Submissions sheet if it doesn't exist"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Add a new sheet named "Submissions"
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}:batchUpdate"
            
            body = {
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": "Submissions",
                                "gridProperties": {
                                    "rowCount": 5000,
                                    "columnCount": 12
                                }
                            }
                        }
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as response:
                    if response.status == 200:
                        logging.info("✅ Created Submissions sheet")
                        return True
                    else:
                        error_text = await response.text()
                        # Sheet might already exist
                        if "already exists" in error_text.lower():
                            logging.info("Submissions sheet already exists")
                            return True
                        logging.error(f"Failed to create submissions sheet: {error_text}")
                        return False
            
        except Exception as e:
            logging.error(f"Error creating submissions sheet: {e}")
            return False


class AmbassadorSheetsConfig:
    """Configuration for ambassador sheets integration"""
    
    # Use the provided ambassador sheet ID
    SPREADSHEET_ID = os.getenv('AMBASSADOR_SPREADSHEET_ID', '1zyGJupeR086ytKMQxtqHtP7UwlQ0redE-aze2RH-RdA')
    CREDENTIALS_PATH = 'config/google_service_account.json'  # Path to credentials
    SYNC_INTERVAL_HOURS = 6  # How often to sync (hours)


async def test_ambassador_sheets():
    """Test the Ambassador Sheets integration"""
    config = AmbassadorSheetsConfig()
    
    if not config.SPREADSHEET_ID:
        print("❌ AMBASSADOR_SPREADSHEET_ID not set in environment")
        print("📋 Please create a Google Sheet and set the AMBASSADOR_SPREADSHEET_ID environment variable")
        return
    
    print(f"📊 Testing Ambassador Sheets with ID: {config.SPREADSHEET_ID}")
    
    # This would need a real supabase client in practice
    sheets_manager = AmbassadorSheetsManager(
        spreadsheet_id=config.SPREADSHEET_ID,
        credentials_path=config.CREDENTIALS_PATH,
        supabase_client=None  # Would be real client
    )
    
    # Test getting access token
    print("🔐 Getting access token...")
    token = await sheets_manager.get_access_token()
    if token:
        print(f"✅ Access token obtained")
        print("✅ Ambassador Sheets integration ready!")
    else:
        print("❌ Failed to get access token")


if __name__ == "__main__":
    asyncio.run(test_ambassador_sheets())
