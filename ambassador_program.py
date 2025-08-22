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
        
        # Initialize Supabase - REQUIRED for ambassador program
        if not SUPABASE_AVAILABLE:
            raise Exception("Supabase library not installed - ambassador program requires cloud database")
        
        if not self.supabase_url or not self.supabase_key:
            raise Exception("Supabase credentials not found - set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
        
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        print("✅ Ambassador program initialized with Supabase-only storage")
        
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
        
        # Weekly streak bonus
        self.weekly_streak_bonus = 10
        
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
        
        # Verify Supabase tables exist (non-blocking)
        self.verify_supabase_tables()
        
        # Don't start task here - will be started in on_ready event
    
    def init_local_database(self):
        """Initialize local SQLite database for ambassador data"""
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            
            # Ambassadors table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ambassadors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                social_handles TEXT,
                platforms TEXT,
                current_month_points INTEGER DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                consecutive_months INTEGER DEFAULT 0,
                reward_tier TEXT DEFAULT 'none',
                status TEXT DEFAULT 'active',
                weekly_posts TEXT DEFAULT '0000',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    def init_local_database(self):
        """Legacy method - no longer used with Supabase-only architecture"""
        pass
    
    def verify_supabase_tables(self):
        """Verify that required Supabase tables exist"""
        try:
            # Test ambassadors table
            result = self.supabase.table('ambassadors').select('discord_id').limit(1).execute()
            print("✅ Ambassadors table verified in Supabase")
            
            # Test submissions table
            result = self.supabase.table('submissions').select('id').limit(1).execute()
            print("✅ Submissions table verified in Supabase")
            
        except Exception as e:
            print(f"⚠️ Supabase table verification failed: {e}")
            print("⚠️ Ambassador program will be disabled until tables are created")
            print("⚠️ Make sure your Supabase project has the required tables:")
            print("   - ambassadors (discord_id, username, social_handles, platforms, current_month_points, total_points, consecutive_months, reward_tier, status)")
            print("   - submissions (ambassador_id, platform, post_type, url, screenshot_hash, engagement_data, content_preview, timestamp, points_awarded, is_duplicate, validity_status, gemini_analysis)")
            # Don't raise - let bot continue without ambassador program
            self.supabase = None  # Disable Supabase functionality
    
    async def analyze_screenshot_with_gemini(self, image_data: bytes, submission_context: str = "") -> Dict:
        """Analyze screenshot using Google Gemini Vision"""
        try:
            if not self.gemini_model:
                return {"error": "Gemini Vision not configured"}
            
            # Prepare the prompt for Gemini
            prompt = f"""
            Analyze this social media post screenshot and extract the following information in JSON format.
            IMPORTANT: Only detect these valid platforms that earn points: youtube, tiktok, instagram, facebook, twitter, reddit, quora, linkedin.
            If the screenshot shows Pinterest, Snapchat, Discord, Telegram, WhatsApp, Tumblr, Twitch, Vimeo, or any other platform, return "invalid_platform".
            
            {{
                "platform": "detected platform (youtube, tiktok, instagram, facebook, twitter, reddit, quora, linkedin, or invalid_platform)",
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
        
        # Engagement multipliers (handle None values)
        engagement_bonus = 0
        engagement_bonus += (engagement.likes or 0) // 25  # +1 per 25 likes
        engagement_bonus += ((engagement.comments or 0) // 5) * 2  # +2 per 5 comments
        engagement_bonus += (engagement.shares or 0)  # +1 per share
        engagement_bonus += (engagement.retweets or 0)  # +1 per retweet
        engagement_bonus += (engagement.saves or 0)  # +1 per save
        
        return base + engagement_bonus
    
    def generate_content_hash(self, content: str, url: str = None, image_data: bytes = None) -> str:
        """Generate unique hash for content to detect duplicates"""
        hash_input = content.lower().strip()
        if url:
            hash_input += url
        if image_data:
            hash_input += hashlib.md5(image_data).hexdigest()
        
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def get_ambassador_by_discord_id(self, discord_id: int) -> Optional[str]:
        """Get ambassador ID by Discord ID - returns ambassador_id if found, None if not"""
        if not self.supabase:
            return None  # Ambassador program disabled
            
        try:
            result = self.supabase.table('ambassadors').select('discord_id').eq('discord_id', str(discord_id)).eq('status', 'active').execute()
            if result.data:
                return result.data[0]['discord_id']
            return None
                
        except Exception as e:
            print(f"❌ Error looking up ambassador {discord_id}: {e}")
            return None
    
    async def check_duplicate_submission(self, content_hash: str, ambassador_id: str) -> bool:
        """Check if submission is a duplicate"""
        if not self.supabase:
            return False  # Ambassador program disabled
            
        try:
            result = self.supabase.table('submissions').select('id').or_(f'screenshot_hash.eq.{content_hash},url.eq.{content_hash}').eq('ambassador_id', ambassador_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"❌ Error checking for duplicates: {e}")
            return False
    
    async def store_submission(self, submission: AmbassadorSubmission) -> bool:
        """Store submission in Supabase"""
        if not self.supabase:
            print("⚠️ Ambassador program disabled - submission not stored")
            return False
            
        try:
            supabase_data = {
                'ambassador_id': submission.ambassador_id,
                'platform': submission.platform.value if hasattr(submission.platform, 'value') else str(submission.platform),
                'post_type': submission.post_type.value if hasattr(submission.post_type, 'value') else str(submission.post_type),
                'url': submission.url,
                'screenshot_hash': submission.screenshot_hash,
                'engagement_data': json.dumps(submission.engagement.__dict__) if submission.engagement else None,
                'content_preview': submission.content_preview,
                'points_awarded': submission.points_awarded,
                'timestamp': submission.timestamp.isoformat(),
                'is_duplicate': submission.is_duplicate,
                'validity_status': submission.validity_status,
                'gemini_analysis': json.dumps(submission.gemini_analysis) if submission.gemini_analysis else None
            }
            
            result = self.supabase.table('submissions').insert(supabase_data).execute()
            print(f"✅ Stored in Supabase: {submission.url or 'Screenshot'}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing submission: {e}")
            return False
    
    async def update_ambassador_points(self, ambassador_id: str, points: int):
        """Update ambassador's point totals in Supabase"""
        if not self.supabase:
            print("⚠️ Ambassador program disabled - points not updated")
            return
            
        try:
            # Get current points from Supabase
            result = self.supabase.table('ambassadors').select('total_points', 'current_month_points').eq('discord_id', ambassador_id).execute()
            if result.data:
                current = result.data[0]
                self.supabase.table('ambassadors').update({
                    'total_points': current['total_points'] + points,
                    'current_month_points': current['current_month_points'] + points
                }).eq('discord_id', ambassador_id).execute()
                print(f"✅ Updated points for {ambassador_id}: +{points} points")
            else:
                print(f"⚠️ Ambassador {ambassador_id} not found in Supabase")
                    
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
        """Send encouraging reminders to ambassadors behind pace"""
        if not self.supabase:
            print("⚠️ Ambassador program disabled - skipping reminders")
            return
            
        try:
            result = self.supabase.table('ambassadors').select('discord_id', 'username', 'current_month_points').eq('status', 'active').lt('current_month_points', 50).execute()
            behind_pace = result.data
                
            for ambassador in behind_pace:
                try:
                    discord_id = ambassador['discord_id']
                    username = ambassador['username']
                    points = ambassador['current_month_points']
                    
                    user = await self.bot.fetch_user(int(discord_id))
                    needed = 75 - points
                    
                    embed = discord.Embed(
                        title="🚀 Let's Keep the Momentum Going!",
                        description=f"Hey {username}! I'm Jim, and I wanted to check in on your ambassador journey.",
                        color=0x3498db
                    )
                    embed.add_field(
                        name="🎯 Monthly Goal",
                        value=f"You need **{needed} more points** to reach your 75-point goal!",
                        inline=False
                    )
                    embed.add_field(
                        name="💡 Easy Ways to Earn Points",
                        value="""• 🎥 Share a YouTube/TikTok video about Sidekick Tools (15 pts)
• 📸 Post an Instagram story or reel (8 pts)
• 🐦 Tweet about your experience (6 pts)
• ❓ Answer a question on Reddit/Quora (12 pts)
• 📊 Share a LinkedIn post about Sidekick Tools (10 pts)
• 📄 Share a Facebook post about Sidekick Tools (8 pts)
• 📸 Share a TikTok video about Sidekick Tools (12 pts)
• 📊 Share a Twitter thread about Sidekick Tools (15 pts)""",
                        inline=False
                    )
                    embed.add_field(
                        name="🏆 What You're Working Toward",
                        value="Consistent ambassadors unlock recurring commissions and exclusive rewards. You've got this!",
                        inline=False
                    )
                    embed.set_footer(text="💬 Just DM me your content - I'll handle the rest!")
                        
                    await user.send(embed=embed)
                    print(f"📨 Sent encouragement to {username} ({points} points)")
                        
                except Exception as e:
                    print(f"❌ Failed to send reminder to {username}: {e}")
                        
        except Exception as e:
            print(f"❌ Error sending mid-month reminders: {e}")
    
    async def send_progress_celebration(self, discord_id, username, milestone):
        """Send celebration message when ambassador hits milestones"""
        try:
            user = await self.bot.fetch_user(int(discord_id))
            
            if milestone == "monthly_goal":
                embed = discord.Embed(
                    title="🎉 Monthly Goal Achieved!",
                    description=f"Congratulations {username}! You've hit your 75-point monthly goal!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="🏆 Achievement Unlocked",
                    value="You've maintained your ambassador status for another month!",
                    inline=False
                )
                embed.add_field(
                    name="🚀 Keep Going",
                    value="Every additional point counts toward your all-time total and reward tiers!",
                    inline=False
                )
            elif milestone == "first_submission":
                embed = discord.Embed(
                    title="🎊 Welcome to Action!",
                    description=f"Great job {username}! You've made your first submission as a Sidekick Tools ambassador!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="🎯 You're On Track",
                    value="Keep posting consistently to reach your 75-point monthly goal!",
                    inline=False
                )
                embed.add_field(
                    name="💡 Pro Tip",
                    value="Mix different types of content across platforms for maximum points!",
                    inline=False
                )
            
            embed.set_footer(text="🌟 Thanks for spreading the word about Sidekick Tools!")
            await user.send(embed=embed)
            print(f"🎉 Sent {milestone} celebration to {username}")
            
        except Exception as e:
            print(f"❌ Failed to send celebration to {username}: {e}")
    
    async def send_weekly_progress_update(self):
        """Send weekly progress updates to all ambassadors"""
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT discord_id, username, current_month_points 
                    FROM ambassadors 
                    WHERE status = 'active'
                ''')
                
                ambassadors = cursor.fetchall()
                
                for discord_id, username, points in ambassadors:
                    try:
                        user = await self.bot.fetch_user(int(discord_id))
                        progress_percentage = min(100, (points / 75) * 100)
                        
                        # Create progress bar
                        filled_blocks = int(progress_percentage / 10)
                        empty_blocks = 10 - filled_blocks
                        progress_bar = "█" * filled_blocks + "░" * empty_blocks
                        
                        embed = discord.Embed(
                            title="📈 Weekly Progress Update",
                            description=f"Hi {username}! Here's how you're doing this month:",
                            color=0x3498db
                        )
                        embed.add_field(
                            name="📊 Current Progress",
                            value=f"`{progress_bar}` {progress_percentage:.1f}%\n**{points}/75 points**",
                            inline=False
                        )
                        
                        if points >= 75:
                            embed.add_field(
                                name="🎉 Status",
                                value="**Goal achieved!** Keep going for bonus points!",
                                inline=False
                            )
                        elif points >= 55:
                            embed.add_field(
                                name="🔥 Status",
                                value="You're almost there! Just a few more posts to reach your goal!",
                                inline=False
                            )
                        elif points >= 30:
                            embed.add_field(
                                name="💪 Status",
                                value="Great progress! You're on track to hit your monthly target!",
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name="🚀 Status",
                                value="Let's ramp up! Share some content about Sidekick Tools this week!",
                                inline=False
                            )
                        
                        embed.set_footer(text="💡 Remember: I automatically detect platforms and award points!")
                        await user.send(embed=embed)
                        
                    except Exception as e:
                        print(f"❌ Failed to send weekly update to {username}: {e}")
                        
        except Exception as e:
            print(f"❌ Error sending weekly updates: {e}")
    
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
                    compliance = "✅ Compliant" if month_points >= 75 else "⚠️ Below Minimum"
                    
                    # Update consecutive months
                    if month_points >= 75:
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
                        current_month, discord_id, total_points,
                        self.get_monthly_post_count(discord_id),
                        new_tier, compliance, datetime.now().isoformat()
                    ))
                    
                    # Update ambassador record
                    cursor.execute('''
                    UPDATE ambassadors 
                    SET current_month_points = 0, 
                        weekly_posts = '0000',
                        consecutive_months = CASE 
                            WHEN current_month_points + ? >= 75 THEN consecutive_months + 1 
                            ELSE 0 
                        END
                    WHERE status = 'active'
                ''', (self.calculate_monthly_streak_bonus(discord_id),))
                    conn.commit()
                    
                    # Generate Google Docs report
                    if self.reporting_system:
                        await self.reporting_system.generate_monthly_report()
                
        except Exception as e:
            print(f"❌ Error generating monthly reports: {e}")
    
    def calculate_reward_tier(self, consecutive_months: int, high_performer_months: int = 0) -> str:
        """Calculate reward tier based on consecutive months and performance"""
        # Loyal Ambassador: Consistent high performance (100+ pts for multiple months)
        if high_performer_months >= 6:  # 6+ months of 100+ points
            return "loyal_ambassador"
        elif consecutive_months >= 12:
            return "lifetime_commissions"
        elif consecutive_months >= 9:
            return "commission_bump_5pct"
        elif consecutive_months >= 6:
            return "6month_recurring"
        elif consecutive_months >= 3 and high_performer_months >= 3:  # 100+ pts for 3 months
            return "commission_bump_5pct"
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
                            
                            # New function call
                            await self.handle_submission(message, ambassador)
                            recovered_submissions += 1
                
                except Exception as e:
                    print(f"❌ Error recovering from channel {channel.name}: {e}")
            
            print(f"✅ Recovered {recovered_submissions} submissions from logs")
        
            
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
        elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
            return Platform.FACEBOOK, PostType.FB_GROUP_POST
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return Platform.TWITTER, PostType.TWEET
        elif 'reddit.com' in url_lower:
            return Platform.REDDIT, PostType.REDDIT_ANSWER
        elif 'quora.com' in url_lower:
            return Platform.QUORA, PostType.QUORA_ANSWER
        elif 'linkedin.com' in url_lower:
            return Platform.LINKEDIN, PostType.INSTAGRAM_POST
        elif 'pinterest.com' in url_lower or 'pin.it' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'snapchat.com' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'discord.com' in url_lower or 'discord.gg' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'telegram.org' in url_lower or 't.me' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'whatsapp.com' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'tumblr.com' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'twitch.tv' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'vimeo.com' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'medium.com' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'substack.com' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        elif 'github.com' in url_lower or 'gitlab.com' in url_lower:
            return Platform.INSTAGRAM, PostType.INSTAGRAM_POST
        else:
            # Unknown platform - accept but will be flagged for review
            return None, None
