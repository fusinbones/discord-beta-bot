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
        self.headers = [
            "Discord ID", "Username", "Current Month Points", "Total Points", 
            "Submissions Count", "Last Updated", "Status", "Manual Adjustments", "Notes"
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
    
    async def sync_ambassadors_to_sheet(self):
        """Sync all ambassador data from Supabase to Google Sheets"""
        try:
            # Get all active ambassadors from Supabase
            result = self.supabase.table('ambassadors').select('*').eq('status', 'active').execute()
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
                    "Active",
                    "",  # Manual Adjustments - empty initially
                    ""   # Notes - empty initially
                ]
                
                sheet_data.append(row_data)
            
            # Clear existing data and add headers + new data
            await self.clear_sheet_data()
            await self.add_headers()
            
            # Add all ambassador data
            success = await self.batch_update_sheet(sheet_data)
            
            if success:
                logging.info(f"✅ Successfully synced {len(ambassadors)} ambassadors to Google Sheets")
                return True
            else:
                logging.error("❌ Failed to sync ambassadors to Google Sheets")
                return False
            
        except Exception as e:
            logging.error(f"Error syncing ambassadors to sheet: {e}")
            return False
    
    async def sync_from_sheet_to_supabase(self):
        """Sync manual adjustments from Google Sheets back to Supabase"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Get all data from the sheet
            range_name = "Ambassadors!A2:I"  # Skip header row
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logging.error(f"Failed to read sheet data: {response.status}")
                        return False
                    
                    data = await response.json()
                    values = data.get('values', [])
                    
                    updates_made = 0
                    
                    for row in values:
                        if len(row) >= 8:  # Ensure we have enough columns
                            discord_id = row[0]
                            manual_adjustment = row[7] if len(row) > 7 else ""
                            notes = row[8] if len(row) > 8 else ""
                            
                            # If there's a manual adjustment, apply it
                            if manual_adjustment and manual_adjustment.strip():
                                try:
                                    adjustment_value = int(manual_adjustment.strip())
                                    
                                    # Update ambassador points in Supabase
                                    current_result = self.supabase.table('ambassadors').select('current_month_points, total_points').eq('discord_id', discord_id).execute()
                                    
                                    if current_result.data:
                                        current_data = current_result.data[0]
                                        new_month_points = current_data.get('current_month_points', 0) + adjustment_value
                                        new_total_points = current_data.get('total_points', 0) + adjustment_value
                                        
                                        # Update in database
                                        self.supabase.table('ambassadors').update({
                                            'current_month_points': max(0, new_month_points),  # Don't go negative
                                            'total_points': max(0, new_total_points),
                                            'notes': notes
                                        }).eq('discord_id', discord_id).execute()
                                        
                                        # Clear the manual adjustment in the sheet
                                        await self.clear_manual_adjustment(discord_id)
                                        
                                        updates_made += 1
                                        logging.info(f"Applied manual adjustment of {adjustment_value} points to {discord_id}")
                                
                                except ValueError:
                                    logging.warning(f"Invalid manual adjustment value: {manual_adjustment}")
                    
                    if updates_made > 0:
                        logging.info(f"✅ Applied {updates_made} manual adjustments from Google Sheets")
                        # Re-sync to update the sheet with new totals
                        await self.sync_ambassadors_to_sheet()
                    
                    return True
            
        except Exception as e:
            logging.error(f"Error syncing from sheet to Supabase: {e}")
            return False
    
    async def clear_manual_adjustment(self, discord_id: str):
        """Clear manual adjustment field for a specific ambassador"""
        try:
            # Find the row for this ambassador and clear column H (Manual Adjustments)
            token = await self.get_access_token()
            if not token:
                return
            
            # This is a simplified approach - in production you'd want to find the exact row
            # For now, we'll just re-sync the entire sheet which will clear adjustments
            pass
            
        except Exception as e:
            logging.error(f"Error clearing manual adjustment: {e}")
    
    async def batch_update_sheet(self, data: List[List]):
        """Batch update sheet with ambassador data"""
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
                        logging.error(f"Failed to batch update sheet: {response.status} - {error_text}")
                        return False
            
        except Exception as e:
            logging.error(f"Error in batch update: {e}")
            return False
    
    async def clear_sheet_data(self):
        """Clear existing data from the sheet"""
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
            logging.error(f"Error clearing sheet: {e}")
            return False
    
    async def add_headers(self):
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
                "values": [self.headers]
            }
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}"
            params = {
                "valueInputOption": "USER_ENTERED"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params, json=body) as response:
                    return response.status == 200
            
        except Exception as e:
            logging.error(f"Error adding headers: {e}")
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


class AmbassadorSheetsConfig:
    """Configuration for ambassador sheets integration"""
    
    SPREADSHEET_ID = os.getenv('AMBASSADOR_SPREADSHEET_ID')  # Set in environment
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
