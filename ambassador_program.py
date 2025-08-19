"""
Ambassador Program + Compliance Module for Jim
Comprehensive system for managing Sidekick Tools ambassadors with Gemini Vision analysis
"""

import os
import json
import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import discord
from discord.ext import commands, tasks
import aiohttp
import sqlite3
from dataclasses import dataclass
from enum import Enum
import google.generativeai as genai
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("⚠️ Supabase not installed - using local database only")
    SUPABASE_AVAILABLE = False
    Client = None
from dotenv import load_dotenv

load_dotenv()

# Import Google Docs integration
from google_docs_integration import GoogleDocsManager, AmbassadorReportingSystem, AmbassadorDocsConfig

class PostType(Enum):
    YOUTUBE_VIDEO = "youtube_tiktok_video"
    TIKTOK_VIDEO = "youtube_tiktok_video"
    QUORA_ANSWER = "quora_reddit_answer"
    REDDIT_ANSWER = "quora_reddit_answer"
    FB_GROUP_POST = "fb_group_post"
    INSTAGRAM_REEL = "instagram_reel_post"
    INSTAGRAM_POST = "instagram_reel_post"
    TWEET = "tweet_threads_post"
    THREAD = "tweet_threads_post"
    STORY = "story"

class Platform(Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    QUORA = "quora"
    REDDIT = "reddit"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"

@dataclass
class EngagementMetrics:
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    saves: int = 0
    retweets: int = 0

@dataclass
class AmbassadorSubmission:
    ambassador_id: str
    platform: Platform
    post_type: PostType
    url: Optional[str]
    screenshot_hash: Optional[str]
    engagement: EngagementMetrics
    content_preview: str
    timestamp: datetime
    points_awarded: int
    is_duplicate: bool
    validity_status: str  # accepted/flagged/rejected
    gemini_analysis: Optional[Dict]

class AmbassadorProgram:
    def __init__(self, bot):
        self.bot = bot
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase: Client = None
        
        # Initialize Supabase if credentials available and library installed
        if SUPABASE_AVAILABLE and self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
        else:
            self.supabase = None
        
        # Initialize Gemini Vision
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Scoring system configuration
        self.base_points = {
            PostType.YOUTUBE_VIDEO: 15,
            PostType.TIKTOK_VIDEO: 15,
            PostType.QUORA_ANSWER: 12,
            PostType.REDDIT_ANSWER: 12,
            PostType.FB_GROUP_POST: 10,
            PostType.INSTAGRAM_REEL: 8,
            PostType.INSTAGRAM_POST: 8,
            PostType.TWEET: 6,
            PostType.THREAD: 6,
            PostType.STORY: 3
        }
        
        # Initialize Google Docs integration
        self.docs_config = AmbassadorDocsConfig()
        if self.docs_config.DOCUMENT_ID:
            self.docs_manager = GoogleDocsManager(
                document_id=self.docs_config.DOCUMENT_ID,
                credentials_path=self.docs_config.CREDENTIALS_PATH
            )
            self.reporting_system = AmbassadorReportingSystem(self.docs_manager)
        else:
            self.docs_manager = None
            self.reporting_system = None
        
        # Initialize local database for fallback
        self.init_local_database()
        
        # Don't start task here - will be started in on_ready event
    
    def init_local_database(self):
        """Initialize local SQLite database for ambassador data"""
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            
            # Ambassadors table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ambassadors (
                    discord_id TEXT PRIMARY KEY,
                    username TEXT,
                    social_handles TEXT,
                    target_platforms TEXT,
                    joined_date TEXT,
                    total_points INTEGER DEFAULT 0,
                    current_month_points INTEGER DEFAULT 0,
                    consecutive_months INTEGER DEFAULT 0,
                    reward_tier TEXT DEFAULT 'none',
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Submissions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ambassador_id TEXT,
                    platform TEXT,
                    post_type TEXT,
                    url TEXT,
                    screenshot_hash TEXT,
                    engagement_data TEXT,
                    content_preview TEXT,
                    timestamp TEXT,
                    points_awarded INTEGER,
                    is_duplicate BOOLEAN,
                    validity_status TEXT,
                    gemini_analysis TEXT,
                    FOREIGN KEY (ambassador_id) REFERENCES ambassadors (discord_id)
                )
            ''')
            
            # Monthly reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monthly_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month_year TEXT,
                    ambassador_id TEXT,
                    total_points INTEGER,
                    posts_count INTEGER,
                    reward_earned TEXT,
                    compliance_status TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.commit()
    
    async def analyze_screenshot_with_gemini(self, image_data: bytes, submission_context: str = "") -> Dict:
        """Analyze screenshot using Google Gemini Vision"""
        try:
            if not self.gemini_model:
                return {"error": "Gemini Vision not configured"}
            
            # Prepare the prompt for Gemini
            prompt = f"""
            Analyze this social media post screenshot and extract the following information in JSON format:
            
            {{
                "platform": "detected platform (youtube, tiktok, instagram, facebook, twitter, reddit, quora, linkedin)",
                "post_type": "type of content (video, post, story, answer, thread)",
                "author_handle": "username/handle visible in the screenshot",
                "engagement_metrics": {{
                    "likes": number_of_likes_or_upvotes,
                    "comments": number_of_comments,
                    "shares": number_of_shares_or_retweets,
                    "views": number_of_views_if_visible,
                    "saves": number_of_saves_if_visible
                }},
                "content_preview": "brief description of the post content (max 100 chars)",
                "authenticity_check": {{
                    "is_likely_authentic": true_or_false,
                    "suspicious_indicators": ["list of any red flags"],
                    "quality_score": 1_to_10_rating
                }},
                "duplicate_risk": {{
                    "appears_cropped": true_or_false,
                    "timestamp_visible": true_or_false,
                    "unique_identifiers": ["list of unique elements that could prevent duplicates"]
                }}
            }}
            
            Context: {submission_context}
            
            Be thorough in detecting fake metrics, cropped screenshots, or other attempts to game the system.
            """
            
            # Convert bytes to PIL Image for Gemini
            import io
            from PIL import Image
            image = Image.open(io.BytesIO(image_data))
            
            # Generate analysis
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                [prompt, image]
            )
            
            # Parse JSON response
            analysis_text = response.text.strip()
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text[7:-3]
            elif analysis_text.startswith('```'):
                analysis_text = analysis_text[3:-3]
            
            analysis = json.loads(analysis_text)
            return analysis
            
        except Exception as e:
            print(f"❌ Gemini Vision analysis failed: {e}")
            return {
                "error": str(e),
                "platform": "unknown",
                "post_type": "unknown",
                "engagement_metrics": {"likes": 0, "comments": 0, "shares": 0, "views": 0},
                "authenticity_check": {"is_likely_authentic": False, "quality_score": 0}
            }
    
    def calculate_points(self, post_type: PostType, engagement: EngagementMetrics, is_reply: bool = False) -> int:
        """Calculate points based on post type and engagement"""
        if is_reply:
            return 1  # Reply bonus
        
        # Base points
        base = self.base_points.get(post_type, 3)
        
        # Engagement multipliers
        engagement_bonus = 0
        engagement_bonus += engagement.likes // 25  # +1 per 25 likes
        engagement_bonus += (engagement.comments // 5) * 2  # +2 per 5 comments
        engagement_bonus += engagement.shares  # +1 per share
        engagement_bonus += engagement.retweets  # +1 per retweet
        engagement_bonus += engagement.saves  # +1 per save
        
        return base + engagement_bonus
    
    def generate_content_hash(self, content: str, url: str = None, image_data: bytes = None) -> str:
        """Generate unique hash for content to detect duplicates"""
        hash_input = content.lower().strip()
        if url:
            hash_input += url
        if image_data:
            hash_input += hashlib.md5(image_data).hexdigest()
        
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def check_duplicate_submission(self, content_hash: str, ambassador_id: str) -> bool:
        """Check if submission is a duplicate"""
        try:
            # Check local database first
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM submissions 
                    WHERE (screenshot_hash = ? OR url = ?) 
                    AND ambassador_id = ?
                ''', (content_hash, content_hash, ambassador_id))
                
                if cursor.fetchone():
                    return True
            
            # Check Supabase if available
            if self.supabase:
                try:
                    result = self.supabase.table('submissions').select('id').eq('ambassador_id', ambassador_id).or_(
                        f'screenshot_hash.eq.{content_hash},url.eq.{content_hash}'
                    ).execute()
                    
                    if result.data:
                        return True
                except Exception as supabase_error:
                    print(f"⚠️ Supabase check failed, using local database only: {supabase_error}")
                    # Continue with local database only
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking duplicates: {e}")
            return False
    
    async def store_submission(self, submission: AmbassadorSubmission) -> bool:
        """Store submission in both local DB and Supabase"""
        try:
            # Store in local database
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO submissions (
                        ambassador_id, platform, post_type, url, screenshot_hash,
                        engagement_data, content_preview, timestamp, points_awarded,
                        is_duplicate, validity_status, gemini_analysis
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    submission.ambassador_id,
                    submission.platform.value,
                    submission.post_type.value,
                    submission.url,
                    submission.screenshot_hash,
                    json.dumps(submission.engagement.__dict__),
                    submission.content_preview,
                    submission.timestamp.isoformat(),
                    submission.points_awarded,
                    submission.is_duplicate,
                    submission.validity_status,
                    json.dumps(submission.gemini_analysis) if submission.gemini_analysis else None
                ))
                conn.commit()
            
            # Store in Supabase if available
            if self.supabase:
                try:
                    supabase_data = {
                        'ambassador_id': submission.ambassador_id,
                        'platform': submission.platform,
                        'post_type': submission.post_type,
                        'url': submission.url,
                        'screenshot_hash': submission.screenshot_hash,
                        'points_awarded': submission.points_awarded,
                        'timestamp': submission.timestamp.isoformat(),
                        'validity_status': submission.validity_status,
                        'fraud_score': submission.fraud_score,
                        'engagement_bonus': submission.engagement_bonus
                    }
                    
                    result = self.supabase.table('submissions').insert(supabase_data).execute()
                    print(f"✅ Stored in Supabase: {submission.url or 'Screenshot'}")
                except Exception as supabase_error:
                    print(f"⚠️ Supabase storage failed, using local database only: {supabase_error}")
                    # Continue with local database only
            
            return True
            
            # Update ambassador points
            await self.update_ambassador_points(submission.ambassador_id, submission.points_awarded)
            
            return True
            
        except Exception as e:
            print(f"❌ Error storing submission: {e}")
            return False
    
    async def update_ambassador_points(self, ambassador_id: str, points: int):
        """Update ambassador's point totals"""
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ambassadors 
                    SET total_points = total_points + ?, 
                        current_month_points = current_month_points + ?
                    WHERE discord_id = ?
                ''', (points, points, ambassador_id))
                conn.commit()
            
            if self.supabase:
                # Get current points
                result = self.supabase.table('ambassadors').select('total_points', 'current_month_points').eq('discord_id', ambassador_id).execute()
                if result.data:
                    current = result.data[0]
                    self.supabase.table('ambassadors').update({
                        'total_points': current['total_points'] + points,
                        'current_month_points': current['current_month_points'] + points
                    }).eq('discord_id', ambassador_id).execute()
                    
        except Exception as e:
            print(f"❌ Error updating points: {e}")
    
    @tasks.loop(hours=24)
    async def monthly_check(self):
        """Daily check for monthly reports and reminders"""
        now = datetime.now()
        
        # Check if it's mid-month (15th)
        if now.day == 15:
            await self.send_midmonth_reminders()
        
        # Check if it's end of month (last day)
        if now.day == (now.replace(month=now.month + 1, day=1) - timedelta(days=1)).day:
            await self.generate_monthly_reports()
    
    async def send_midmonth_reminders(self):
        """Send reminders to ambassadors behind pace"""
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT discord_id, username, current_month_points 
                    FROM ambassadors 
                    WHERE status = 'active' AND current_month_points < 25
                ''')
                
                behind_pace = cursor.fetchall()
                
                for discord_id, username, points in behind_pace:
                    try:
                        user = await self.bot.fetch_user(int(discord_id))
                        needed = 50 - points
                        
                        embed = discord.Embed(
                            title="📊 Ambassador Program - Mid-Month Check",
                            description=f"Hi {username}! You currently have **{points} points** this month.",
                            color=0xffa500
                        )
                        embed.add_field(
                            name="🎯 Goal Reminder",
                            value=f"You need **{needed} more points** to reach the 50-point monthly minimum.",
                            inline=False
                        )
                        embed.add_field(
                            name="💡 Quick Tips",
                            value="• YouTube/TikTok videos = 15 base points\n• Engage with your posts for bonus points\n• Spread posts throughout the month",
                            inline=False
                        )
                        
                        await user.send(embed=embed)
                        
                    except Exception as e:
                        print(f"❌ Failed to send reminder to {username}: {e}")
                        
        except Exception as e:
            print(f"❌ Error sending mid-month reminders: {e}")
    
    async def generate_monthly_reports(self):
        """Generate end-of-month reports and reset monthly points"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                
                # Get all active ambassadors
                cursor.execute('SELECT * FROM ambassadors WHERE status = "active"')
                ambassadors = cursor.fetchall()
                
                for ambassador in ambassadors:
                    discord_id, username, _, _, _, total_points, month_points, consecutive, reward_tier, _ = ambassador
                    
                    # Determine compliance
                    compliance = "✅ Compliant" if month_points >= 50 else "⚠️ Below Minimum"
                    
                    # Update consecutive months
                    if month_points >= 50:
                        consecutive += 1
                    else:
                        consecutive = 0
                    
                    # Determine reward tier
                    new_tier = self.calculate_reward_tier(consecutive)
                    
                    # Store monthly report
                    cursor.execute('''
                        INSERT INTO monthly_reports (
                            month_year, ambassador_id, total_points, posts_count,
                            reward_earned, compliance_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        current_month, discord_id, month_points,
                        self.get_monthly_post_count(discord_id),
                        new_tier, compliance, datetime.now().isoformat()
                    ))
                    
                    # Update ambassador record
                    cursor.execute('''
                        UPDATE ambassadors 
                        SET current_month_points = 0, 
                            consecutive_months = ?, 
                            reward_tier = ?
                        WHERE discord_id = ?
                    ''', (consecutive, new_tier, discord_id))
                
                conn.commit()
                
                # Generate Google Docs report
                if self.reporting_system:
                    await self.reporting_system.generate_monthly_report()
                
        except Exception as e:
            print(f"❌ Error generating monthly reports: {e}")
    
    def calculate_reward_tier(self, consecutive_months: int) -> str:
        """Calculate reward tier based on consecutive months"""
        if consecutive_months >= 12:
            return "lifetime_commissions"
        elif consecutive_months >= 9:
            return "commission_bump_5pct"
        elif consecutive_months >= 6:
            return "6month_recurring"
        elif consecutive_months >= 3:
            return "3month_recurring"
        else:
            return "none"
    
    def get_monthly_post_count(self, ambassador_id: str) -> int:
        """Get number of posts this month for an ambassador"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM submissions 
                    WHERE ambassador_id = ? 
                    AND strftime('%Y-%m', timestamp) = ?
                    AND validity_status = 'accepted'
                ''', (ambassador_id, current_month))
                
                return cursor.fetchone()[0]
        except:
            return 0
    
    async def recover_from_logs(self):
        """Fallback recovery system - rebuild ambassador data from Discord logs"""
        try:
            print("🔄 Starting ambassador program recovery from logs...")
            
            # Get all channels in "Ambassador Program" category
            ambassador_channels = []
            for guild in self.bot.guilds:
                for category in guild.categories:
                    if "ambassador program" in category.name.lower():
                        ambassador_channels.extend(category.channels)
            
            if not ambassador_channels:
                print("⚠️ No Ambassador Program channels found for recovery")
                return
            
            recovered_submissions = 0
            
            # Scan recent messages in ambassador channels
            for channel in ambassador_channels:
                try:
                    # Look back 30 days
                    after_date = datetime.now() - timedelta(days=30)
                    
                    async for message in channel.history(limit=1000, after=after_date):
                        # Skip bot messages
                        if message.author.bot:
                            continue
                        
                        # Check if user is an ambassador
                        with sqlite3.connect('ambassador_program.db') as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT * FROM ambassadors WHERE discord_id = ? AND status = "active"', 
                                         (str(message.author.id),))
                            ambassador = cursor.fetchone()
                        
                        if not ambassador:
                            continue
                        
                        # Check for URLs or attachments
                        import re
                        url_pattern = r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?'
                        urls = re.findall(url_pattern, message.content)
                        screenshots = [att for att in message.attachments if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
                        
                        if urls or screenshots:
                            # Check if already processed
                            content_hash = self.generate_content_hash(message.content, urls[0] if urls else None)
                            
                            with sqlite3.connect('ambassador_program.db') as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT id FROM submissions WHERE screenshot_hash = ? OR url = ?', 
                                             (content_hash, content_hash))
                                if cursor.fetchone():
                                    continue  # Already processed
                            
                            # Process the submission
                            if urls:
                                await self._recover_url_submission(message, ambassador, urls[0])
                            elif screenshots:
                                await self._recover_screenshot_submission(message, ambassador, screenshots[0])
                            
                            recovered_submissions += 1
                            
                except discord.Forbidden:
                    print(f"⚠️ No access to channel: {channel.name}")
                    continue
                except Exception as e:
                    print(f"❌ Error processing channel {channel.name}: {e}")
                    continue
            
            print(f"✅ Recovery complete: {recovered_submissions} submissions recovered")
            
        except Exception as e:
            print(f"❌ Error during recovery: {e}")
    
    async def _recover_url_submission(self, message, ambassador_data, url):
        """Recover a URL submission from logs"""
        try:
            discord_id = ambassador_data[0]
            platform, post_type = self._detect_platform_from_url(url)
            
            # Basic engagement for recovery
            engagement = EngagementMetrics(likes=0, comments=0, shares=0, views=0)
            points = self.calculate_points(post_type, engagement)
            
            submission = AmbassadorSubmission(
                ambassador_id=discord_id,
                platform=platform,
                post_type=post_type,
                url=url,
                screenshot_hash=None,
                engagement=engagement,
                content_preview=message.content[:100],
                timestamp=message.created_at,
                points_awarded=points,
                is_duplicate=False,
                validity_status="accepted",
                gemini_analysis=None
            )
            
            await self.store_submission(submission)
            print(f"📝 Recovered URL submission from {ambassador_data[1]}")
            
        except Exception as e:
            print(f"❌ Error recovering URL submission: {e}")
    
    async def _recover_screenshot_submission(self, message, ambassador_data, screenshot):
        """Recover a screenshot submission from logs"""
        try:
            discord_id = ambassador_data[0]
            
            # Download screenshot for analysis
            screenshot_data = await screenshot.read()
            content_hash = self.generate_content_hash(message.content, image_data=screenshot_data)
            
            # Analyze with Gemini if available
            if self.gemini_model:
                analysis = await self.analyze_screenshot_with_gemini(screenshot_data, f"Recovery: {message.content}")
            else:
                analysis = {"platform": "instagram", "post_type": "post", "engagement_metrics": {"likes": 0, "comments": 0}}
            
            # Extract platform and post type
            try:
                platform = Platform(analysis.get('platform', 'instagram'))
            except ValueError:
                platform = Platform.INSTAGRAM
            
            try:
                post_type_str = analysis.get('post_type', 'post')
                if 'video' in post_type_str.lower():
                    post_type = PostType.INSTAGRAM_REEL
                else:
                    post_type = PostType.INSTAGRAM_POST
            except:
                post_type = PostType.INSTAGRAM_POST
            
            # Extract engagement
            engagement_data = analysis.get('engagement_metrics', {})
            engagement = EngagementMetrics(
                likes=engagement_data.get('likes', 0),
                comments=engagement_data.get('comments', 0),
                shares=engagement_data.get('shares', 0),
                views=engagement_data.get('views', 0)
            )
            
            points = self.calculate_points(post_type, engagement)
            
            submission = AmbassadorSubmission(
                ambassador_id=discord_id,
                platform=platform,
                post_type=post_type,
                url=None,
                screenshot_hash=content_hash,
                engagement=engagement,
                content_preview=analysis.get('content_preview', message.content[:100]),
                timestamp=message.created_at,
                points_awarded=points,
                is_duplicate=False,
                validity_status="accepted",
                gemini_analysis=analysis
            )
            
            await self.store_submission(submission)
            print(f"📸 Recovered screenshot submission from {ambassador_data[1]}")
            
        except Exception as e:
            print(f"❌ Error recovering screenshot submission: {e}")
    
    def _detect_platform_from_url(self, url):
        """Detect platform and post type from URL"""
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return Platform.YOUTUBE, PostType.YOUTUBE_VIDEO
        elif 'tiktok.com' in url_lower:
            return Platform.TIKTOK, PostType.TIKTOK_VIDEO
        elif 'instagram.com' in url_lower:
            if '/reel/' in url_lower:
                return Platform.INSTAGRAM, PostType.INSTAGRAM_REEL
            else:
                return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'facebook.com' in url_lower:
            return Platform.FACEBOOK, PostType.FB_GROUP_POST
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return Platform.TWITTER, PostType.TWEET
        elif 'reddit.com' in url_lower:
            return Platform.REDDIT, PostType.REDDIT_ANSWER
        elif 'quora.com' in url_lower:
            return Platform.QUORA, PostType.QUORA_ANSWER
        else:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
