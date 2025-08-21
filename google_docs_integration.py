"""
Google Docs Integration for Ambassador Program Reporting
Syncs ambassador data to a Google Doc for staff-friendly viewing
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import sqlite3
from google_sheets_integration import GoogleSheetsManager

class GoogleDocsManager:
    def __init__(self, document_id: str, credentials_path: str):
        """
        Initialize Google Docs Manager for Ambassador Program reporting
        
        Args:
            document_id: The ID of the Google Document
            credentials_path: Path to Google service account credentials JSON
        """
        self.document_id = document_id
        self.credentials_path = credentials_path
        self.base_url = "https://docs.googleapis.com/v1/documents"
        self.access_token = None
        self.token_expires = 0
        
        # Use the same auth system as GoogleSheetsManager
        self.sheets_manager = GoogleSheetsManager("dummy", credentials_path)
    
    async def get_access_token(self):
        """Get OAuth2 access token using service account credentials"""
        return await self.sheets_manager.get_access_token()
    
    async def update_ambassador_report(self, ambassadors_data: List[Dict], monthly_stats: Dict):
        """Update the Google Doc with current ambassador program status"""
        try:
            token = await self.get_access_token()
            if not token:
                print("❌ Failed to get access token for Google Docs")
                return False
            
            # Clear existing content and add new report
            await self._clear_document(token)
            await self._add_report_content(token, ambassadors_data, monthly_stats)
            
            print("✅ Successfully updated Google Docs ambassador report")
            return True
            
        except Exception as e:
            print(f"❌ Error updating Google Docs report: {e}")
            return False
    
    async def _clear_document(self, token: str):
        """Clear the document content"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get document to find content length
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/{self.document_id}", headers=headers) as response:
                if response.status == 200:
                    doc_data = await response.json()
                    content_length = doc_data['body']['content'][-1]['endIndex'] - 1
                    
                    # Delete all content except the first character
                    if content_length > 1:
                        delete_request = {
                            "requests": [{
                                "deleteContentRange": {
                                    "range": {
                                        "startIndex": 1,
                                        "endIndex": content_length
                                    }
                                }
                            }]
                        }
                        
                        async with session.post(
                            f"{self.base_url}/{self.document_id}:batchUpdate",
                            headers=headers,
                            json=delete_request
                        ) as delete_response:
                            if delete_response.status != 200:
                                print(f"⚠️ Warning: Failed to clear document: {delete_response.status}")
    
    async def _add_report_content(self, token: str, ambassadors_data: List[Dict], monthly_stats: Dict):
        """Add the ambassador report content to the document"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Generate report content
        current_date = datetime.now().strftime("%B %Y")
        
        content_requests = []
        
        # Title
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": f"Sidekick Tools Ambassador Program Report - {current_date}\n\n"
            }
        })
        
        # Summary Statistics
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": "📊 PROGRAM SUMMARY\n"
            }
        })
        
        summary_text = f"""
Total Active Ambassadors: {monthly_stats.get('total_ambassadors', 0)}
On Track (75+ points): {monthly_stats.get('compliant_count', 0)}
Behind Pace: {monthly_stats.get('behind_count', 0)}
Average Points This Month: {monthly_stats.get('avg_points', 0):.1f}
Total Points Awarded: {monthly_stats.get('total_points_awarded', 0)}

"""
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": summary_text
            }
        })
        
        # Leaderboard
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": "🏆 CURRENT MONTH LEADERBOARD\n\n"
            }
        })
        
        # Sort ambassadors by current month points
        sorted_ambassadors = sorted(ambassadors_data, key=lambda x: x.get('current_month_points', 0), reverse=True)
        
        for i, ambassador in enumerate(sorted_ambassadors[:15], 1):
            status_emoji = "✅" if ambassador.get('current_month_points', 0) >= 75 else "⚠️"
            tier_info = ambassador.get('reward_tier', 'none').replace('_', ' ').title()
            if tier_info == 'None':
                tier_info = ""
            else:
                tier_info = f" ({tier_info})"
            
            leaderboard_line = f"{i}. {status_emoji} {ambassador.get('username', 'Unknown')} - {ambassador.get('current_month_points', 0)} pts{tier_info}\n"
            content_requests.append({
                "insertText": {
                    "location": {"index": 1},
                    "text": leaderboard_line
                }
            })
        
        # Detailed Ambassador Breakdown
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": "\n\n📋 DETAILED AMBASSADOR STATUS\n\n"
            }
        })
        
        for ambassador in sorted_ambassadors:
            username = ambassador.get('username', 'Unknown')
            month_points = ambassador.get('current_month_points', 0)
            total_points = ambassador.get('total_points', 0)
            consecutive = ambassador.get('consecutive_months', 0)
            platforms = ambassador.get('platforms', 'Not specified')
            
            compliance_status = "✅ Compliant" if month_points >= 75 else f"⚠️ Behind ({75 - month_points} pts needed)"
            
            ambassador_detail = f"""
{username}
  Current Month: {month_points} points
  Total Points: {total_points}
  Consecutive Months: {consecutive}
  Platforms: {platforms}
  Status: {compliance_status}
  
"""
            content_requests.append({
                "insertText": {
                    "location": {"index": 1},
                    "text": ambassador_detail
                }
            })
        
        # Recent Activity Summary
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": "\n📈 RECENT ACTIVITY HIGHLIGHTS\n\n"
            }
        })
        
        # Get recent submissions for activity summary
        recent_activity = await self._get_recent_activity_summary()
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": recent_activity
            }
        })
        
        # Footer
        footer_text = f"\n\nReport generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Jim's Ambassador Program System\n"
        content_requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": footer_text
            }
        })
        
        # Apply all content in batch
        batch_request = {"requests": content_requests}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/{self.document_id}:batchUpdate",
                headers=headers,
                json=batch_request
            ) as response:
                if response.status == 200:
                    print("✅ Successfully added content to Google Doc")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to add content to Google Doc: {response.status} - {error_text}")
    
    async def _get_recent_activity_summary(self) -> str:
        """Get a summary of recent ambassador activity"""
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                
                # Get submissions from last 7 days
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute('''
                    SELECT platform, post_type, points_awarded, timestamp, 
                           (SELECT username FROM ambassadors WHERE discord_id = submissions.ambassador_id) as username
                    FROM submissions 
                    WHERE timestamp > ? AND validity_status = 'accepted'
                    ORDER BY timestamp DESC 
                    LIMIT 20
                ''', (week_ago,))
                
                recent_submissions = cursor.fetchall()
                
                if not recent_submissions:
                    return "No recent activity in the past 7 days.\n"
                
                activity_summary = f"Last 7 days - {len(recent_submissions)} submissions:\n\n"
                
                for platform, post_type, points, timestamp, username in recent_submissions:
                    date = datetime.fromisoformat(timestamp).strftime("%m/%d")
                    platform_name = platform.replace('_', ' ').title()
                    post_name = post_type.replace('_', ' ').title()
                    activity_summary += f"• {date} - {username}: {platform_name} {post_name} ({points} pts)\n"
                
                return activity_summary
                
        except Exception as e:
            print(f"❌ Error getting recent activity: {e}")
            return "Error retrieving recent activity data.\n"

class AmbassadorReportingSystem:
    def __init__(self, docs_manager: GoogleDocsManager):
        self.docs_manager = docs_manager
    
    async def generate_monthly_report(self):
        """Generate and sync monthly ambassador report to Google Docs"""
        try:
            # Get all ambassador data
            ambassadors_data = await self._get_ambassadors_data()
            monthly_stats = await self._calculate_monthly_stats(ambassadors_data)
            
            # Update Google Doc
            success = await self.docs_manager.update_ambassador_report(ambassadors_data, monthly_stats)
            
            if success:
                print("✅ Monthly ambassador report generated and synced to Google Docs")
            else:
                print("❌ Failed to sync monthly report to Google Docs")
            
            return success
            
        except Exception as e:
            print(f"❌ Error generating monthly report: {e}")
            return False
    
    async def _get_ambassadors_data(self) -> List[Dict]:
        """Get all ambassador data from database"""
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT discord_id, username, social_handles, platforms,
                           current_month_points, total_points,
                           consecutive_months, reward_tier, status, created_at
                    FROM ambassadors 
                    WHERE status = 'active'
                    ORDER BY current_month_points DESC
                ''')
                
                ambassadors = cursor.fetchall()
                
                return [
                    {
                        'discord_id': row[0],
                        'username': row[1],
                        'social_handles': row[2],
                        'platforms': row[3],
                        'current_month_points': row[4],
                        'total_points': row[5],
                        'consecutive_months': row[6],
                        'reward_tier': row[7],
                        'status': row[8],
                        'created_at': row[9]
                    }
                    for row in ambassadors
                ]
                
        except Exception as e:
            print(f"❌ Error getting ambassadors data: {e}")
            return []
    
    async def _calculate_monthly_stats(self, ambassadors_data: List[Dict]) -> Dict:
        """Calculate monthly statistics"""
        total_ambassadors = len(ambassadors_data)
        compliant_count = sum(1 for a in ambassadors_data if a['current_month_points'] >= 75)
        behind_count = total_ambassadors - compliant_count
        
        total_points = sum(a['current_month_points'] for a in ambassadors_data)
        avg_points = total_points / total_ambassadors if total_ambassadors > 0 else 0
        
        # Get total points awarded this month
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                current_month = datetime.now().strftime("%Y-%m")
                cursor.execute('''
                    SELECT SUM(points_awarded) FROM submissions 
                    WHERE strftime('%Y-%m', timestamp) = ? 
                    AND validity_status = 'accepted'
                ''', (current_month,))
                
                result = cursor.fetchone()
                total_points_awarded = result[0] if result[0] else 0
        except:
            total_points_awarded = 0
        
        return {
            'total_ambassadors': total_ambassadors,
            'compliant_count': compliant_count,
            'behind_count': behind_count,
            'avg_points': avg_points,
            'total_points_awarded': total_points_awarded
        }

# Configuration class for Google Docs integration
class AmbassadorDocsConfig:
    """Configuration for Ambassador Program Google Docs integration"""
    
    DOCUMENT_ID = os.getenv('AMBASSADOR_GOOGLE_DOC_ID')  # Set in environment
    CREDENTIALS_PATH = 'config/google_service_account.json'  # Path to credentials

async def test_docs_integration():
    """Test the Google Docs integration"""
    config = AmbassadorDocsConfig()
    
    if not config.DOCUMENT_ID:
        print("❌ AMBASSADOR_GOOGLE_DOC_ID not set in environment")
        return
    
    print(f"📄 Testing with Document ID: {config.DOCUMENT_ID}")
    print(f"🔑 Using credentials path: {config.CREDENTIALS_PATH}")
    
    docs_manager = GoogleDocsManager(
        document_id=config.DOCUMENT_ID,
        credentials_path=config.CREDENTIALS_PATH
    )
    
    reporting_system = AmbassadorReportingSystem(docs_manager)
    
    # Test generating a report
    print("📊 Generating test report...")
    success = await reporting_system.generate_monthly_report()
    
    if success:
        print("✅ Google Docs integration test passed!")
    else:
        print("❌ Google Docs integration test failed!")

if __name__ == "__main__":
    asyncio.run(test_docs_integration())
