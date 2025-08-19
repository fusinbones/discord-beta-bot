import asyncio
import aiohttp
import json
import discord
from discord.ext import commands, tasks
import os
from datetime import datetime, timedelta
import sqlite3
from collections import deque
import re
from typing import Dict, List, Optional, Tuple
import urllib.parse
import google.generativeai as genai
from anthropic import AsyncAnthropic
import openai
import pytz
from self_update_system import SelfUpdateSystem, SelfUpdateCommands
from dotenv import load_dotenv
import random

# === JIM THE MENTOR - Enhanced Imports ===
import anthropic  # Claude AI
from openai import AsyncOpenAI  # OpenAI API
import httpx  # HTTP client
from PIL import Image, ImageEnhance, ImageFilter  # Image processing
import io
import base64
# from elevenlabs import Client  # Voice synthesis - temporarily disabled

# === GOOGLE SHEETS INTEGRATION ===
from google_sheets_integration import GoogleSheetsManager, BugTrackingConfig

# === AMBASSADOR PROGRAM ===
from ambassador_program import AmbassadorProgram, PostType, Platform, EngagementMetrics, AmbassadorSubmission

# Load environment variables
load_dotenv()

# === JIM THE MENTOR - API Client Initialization ===
# Claude AI Client
claude_client = None
if os.getenv('CLAUDE_API_KEY'):
    claude_client = AsyncAnthropic(api_key=os.getenv('CLAUDE_API_KEY'))

# OpenAI Client  
openai_client = None
if os.getenv('OPENAI_API_KEY'):
    openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Replicate Client
# if os.getenv('REPLICATE_API_KEY'):
#     replicate.api_token = os.getenv('REPLICATE_API_KEY')

# ElevenLabs API Key
elevenlabs_api_key = None  # os.getenv('ELEVENLABS_API_KEY') - temporarily disabled

# Firecrawl Configuration
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')
FIRECRAWL_MCP_URL = os.getenv('FIRECRAWL_MCP_URL', 'https://mcp.firecrawl.com/sse')

# === NATURAL CONVERSATION SYSTEM ===
class NaturalConversationSystem:
    def __init__(self, bot):
        self.bot = bot
        self.conversation_chance = 0.05  # 5% chance to jump into conversation
        self.last_message_time = {}
        self.conversation_context = {}
        
    async def should_participate(self, message):
        """Determine if Jim should randomly jump into the conversation"""
        # Don't participate in commands
        if message.content.startswith('!'):
            return False
            
        # Don't respond to bots
        if message.author.bot:
            return False
            
        # Random chance to participate
        if random.random() < self.conversation_chance:
            return True
            
        # Always participate if mentioned or replied to
        if self.bot.user in message.mentions:
            return True
            
        # Check if replying to Jim
        if message.reference and message.reference.message_id:
            try:
                referenced_msg = await message.channel.fetch_message(message.reference.message_id)
                if referenced_msg.author == self.bot.user:
                    return True
            except:
                pass
                
        return False
        
    def is_bug_or_sidekick_related(self, content):
        """Check if the message is about bugs or Sidekick Tools"""
        bug_keywords = [
            'bug', 'error', 'issue', 'problem', 'crash', 'glitch', 'broken', 'not working',
            'sidekick', 'sidekick tools', 'app', 'application', 'feature', 'functionality'
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in bug_keywords)
        
    async def generate_human_response(self, message, context=""):
        """Generate a natural, human-like response"""
        
        # Check if it's bug/Sidekick related for knowledge base
        is_relevant = self.is_bug_or_sidekick_related(message.content)
        
        if is_relevant:
            # Store in knowledge base
            await self.store_knowledge(message)
            
        # Create a very human-like prompt
        prompt = f"""
        You are Jim, a friendly and extremely human Discord community member who helps with Sidekick Tools app testing. 
        
        IMPORTANT: Respond as if you're a real human, not an AI. Use casual language, contractions, and natural speech patterns.
        
        Recent message from {message.author.display_name}: "{message.content}"
        
        Context about the conversation: {context}
        
        Guidelines:
        - Be conversational and friendly
        - Use casual language like "lol", "yeah", "totally", etc.
        - Keep responses relatively short (1-2 sentences usually)
        - Don't be overly helpful or formal
        - If they mention a bug or issue with Sidekick Tools, casually suggest they might want to report it
        - Never mention you're an AI or bot
        - Sometimes use emojis but don't overdo it
        - Be genuinely interested in what they're saying
        
        If this is about a bug or Sidekick Tools issue, you can casually suggest: "Sounds like that might be worth reporting - I can help you add it to our bug tracker if you want!"
        
        Respond naturally as Jim would:
        """
        
        try:
            response = await self.bot.get_ai_response(prompt, context)
            return response
        except Exception as e:
            # Fallback human responses
            casual_responses = [
                "Yeah, I hear you on that one!",
                "Oh interesting, tell me more about that",
                "Haha, that's pretty typical honestly",
                "I feel you on that - been there myself",
                "That's wild, never seen that before",
                "Gotcha, makes sense to me"
            ]
            return random.choice(casual_responses)
            
    async def store_knowledge(self, message):
        """Store bug/Sidekick Tools related conversations in knowledge base"""
        try:
            with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
                cursor = conn.cursor()
                
                # Create knowledge base table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge_base (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        username TEXT,
                        message_content TEXT,
                        timestamp TEXT,
                        channel_id TEXT,
                        is_bug_related BOOLEAN,
                        context TEXT
                    )
                ''')
                
                cursor.execute('''
                    INSERT INTO knowledge_base (user_id, username, message_content, timestamp, channel_id, is_bug_related, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(message.author.id),
                    message.author.display_name,
                    message.content,
                    datetime.now().isoformat(),
                    str(message.channel.id),
                    True,
                    "Natural conversation about bugs/Sidekick Tools"
                ))
                
                conn.commit()
                
        except Exception as e:
            print(f"Error storing knowledge: {e}")
            
    async def suggest_bug_report(self, message):
        """Suggest adding a bug to the tracker"""
        suggestions = [
            "That definitely sounds like something worth tracking! Want me to help you add it to our bug sheet? 📊",
            "Oh that's a good catch - we should probably log that one. I can help you report it if you'd like!",
            "Hmm, that might be worth documenting. I can add it to our tracker for you - just let me know!",
            "That sounds like the kind of thing the team would want to know about. Want to make it official and report it?",
            "Good find! That's definitely bug-worthy. I can help you get it into our system if you want 🐛"
        ]
        
        return random.choice(suggestions)

class BugTrackingConfig:
    def __init__(self):
        self.SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')
        self.CREDENTIALS_PATH = 'config/google_service_account.json'

# Initialize database
def init_database():
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                channel_id TEXT,
                channel_name TEXT,
                message_content TEXT,
                timestamp TEXT,
                message_id TEXT,
                has_attachments BOOLEAN DEFAULT FALSE,
                attachment_urls TEXT,
                is_staff_message BOOLEAN DEFAULT FALSE,
                screenshot_info TEXT
            )
        ''')
        
        # Add new columns if they don't exist (database migration)
        try:
            cursor.execute('ALTER TABLE messages ADD COLUMN has_attachments BOOLEAN DEFAULT FALSE')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE messages ADD COLUMN attachment_urls TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute('ALTER TABLE messages ADD COLUMN is_staff_message BOOLEAN DEFAULT FALSE')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute('ALTER TABLE messages ADD COLUMN screenshot_info TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                bug_description TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'potential',
                staff_notified BOOLEAN DEFAULT FALSE,
                channel_id TEXT,
                added_by TEXT
            )
        ''')
        
        # Add new columns if they don't exist (database migration)
        try:
            cursor.execute('ALTER TABLE bugs ADD COLUMN channel_id TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute('ALTER TABLE bugs ADD COLUMN added_by TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS testing_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT,
                status TEXT,
                last_updated TEXT,
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whats_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                timestamp TEXT,
                created_by TEXT
            )
        ''')
        
        # === JIM THE MENTOR - Extended Database Schema ===
        
        # Core mentorship tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mentorship_users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                onboarding_completed BOOLEAN DEFAULT FALSE,
                primary_platform TEXT,
                store_url TEXT,
                experience_level TEXT,
                monthly_goal REAL DEFAULT 0,
                preferred_categories TEXT,
                biggest_challenge TEXT,
                created_at TEXT,
                last_active TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS store_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                store_url TEXT,
                platform TEXT,
                overall_score INTEGER,
                product_quality_score INTEGER,
                pricing_strategy_score INTEGER,
                listing_optimization_score INTEGER,
                branding_score INTEGER,
                inventory_diversity_score INTEGER DEFAULT 5,
                analysis_summary TEXT,
                recommendations TEXT,
                jim_response TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        # Add inventory_diversity_score column if it doesn't exist (migration)
        try:
            cursor.execute('ALTER TABLE store_analysis ADD COLUMN inventory_diversity_score INTEGER DEFAULT 5')
            print("Added inventory_diversity_score column to store_analysis table")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Mentorship sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mentorship_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_type TEXT,
                user_input TEXT,
                jim_response TEXT,
                timestamp TEXT,
                channel_type TEXT,
                advice_category TEXT,
                effectiveness_score INTEGER,
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        # User progress
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                date TEXT,
                sales_count INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0.0,
                listings_created INTEGER DEFAULT 0,
                mood_score INTEGER,
                daily_challenges TEXT,
                wins_today TEXT,
                jim_encouragement TEXT,
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        # Mentorship goals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mentorship_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                goal_title TEXT,
                goal_description TEXT,
                target_value REAL,
                current_progress REAL DEFAULT 0,
                goal_type TEXT,
                deadline TEXT,
                created_at TEXT,
                completed_at TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                milestone_rewards TEXT,
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        # Photo edits
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photo_edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                original_filename TEXT,
                edit_type TEXT,
                edit_parameters TEXT,
                processing_cost REAL,
                processing_time_seconds REAL,
                result_quality_score INTEGER,
                created_at TEXT,
                api_used TEXT,
                user_satisfaction INTEGER,
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        # Daily check-ins
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                checkin_date TEXT,
                mood TEXT,
                challenges_faced TEXT,
                wins_achieved TEXT,
                goals_progress TEXT,
                jim_advice TEXT,
                next_checkin_scheduled TEXT,
                response_received BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        # Mentorship insights
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mentorship_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                insight_type TEXT,
                insight_title TEXT,
                insight_description TEXT,
                confidence_score REAL,
                actionable_steps TEXT,
                created_at TEXT,
                acted_upon BOOLEAN DEFAULT FALSE,
                effectiveness_rating INTEGER,
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        # User preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                notification_frequency TEXT DEFAULT 'daily',
                preferred_checkin_time TEXT,
                voice_messages_enabled BOOLEAN DEFAULT TRUE,
                coaching_style TEXT DEFAULT 'balanced',
                goal_reminder_frequency TEXT DEFAULT 'weekly',
                privacy_level TEXT DEFAULT 'standard',
                communication_channels TEXT DEFAULT 'dm_only',
                FOREIGN KEY (user_id) REFERENCES mentorship_users (user_id)
            )
        ''')
        
        conn.commit()

# === JIM THE MENTOR - MentorshipServices Class ===
class MentorshipServices:
    """
    Comprehensive AI-powered mentorship services for Jim the Mentor
    Integrates Claude, Firecrawl, ElevenLabs, OpenAI, and Replicate APIs
    """
    
    def __init__(self, bot):
        self.claude_client = claude_client
        self.openai_client = openai_client
        self.firecrawl_api_key = FIRECRAWL_API_KEY
        # self.elevenlabs_api_key = elevenlabs_api_key - temporarily disabled
        self.bot = bot
        
        # Analysis queue
        self.analysis_queue = deque()
        
    async def is_staff_member(self, user_id: str) -> bool:
        """Check if a user is a staff member who should bypass rate limits"""
        # Staff member user IDs who bypass rate limits
        staff_members = [
            "547170700004163587",  # Darktiding
            # Add more staff member IDs here as needed
        ]
        
        # Also check for Discord administrator permissions if user is in a guild
        try:
            for guild in self.bot.guilds:
                member = guild.get_member(int(user_id))
                if member and member.guild_permissions.administrator:
                    return True
        except:
            pass
            
        return user_id in staff_members
    
    async def analyze_store_with_firecrawl(self, store_url: str, user_id: str) -> Dict:
        """Analyze a reseller store using Firecrawl + Claude AI with full store crawling"""
        try:
            # Check rate limiting - 1 analysis per hour per user (bypass for staff)
            current_time = datetime.now()
            
            # Staff members bypass all rate limits and queue
            if self.is_staff_member(user_id):
                print(f"🔧 Staff member {user_id} bypassing rate limit and queue")
                return await self.crawl_and_analyze_store(store_url, user_id)
            
            # Add to queue
            queue_item = {
                "user_id": user_id,
                "store_url": store_url,
                "timestamp": current_time,
                "status": "queued"
            }
            
            self.analysis_queue.append(queue_item)
            queue_position = len(self.analysis_queue)
            
            # Start processing if not already running
            if not hasattr(self, 'processing_analysis') or not self.processing_analysis:
                asyncio.create_task(self.process_analysis_queue())
            
            # Return queue information
            return {
                "queued": True,
                "queue_position": queue_position,
                "estimated_wait": queue_position * 3  # Estimate 3 minutes per analysis
            }
            
        except Exception as e:
            return {"error": f"Failed to queue analysis: {e}"}
    
    async def process_analysis_queue(self):
        """Process analysis requests from the queue"""
        if hasattr(self, 'processing_analysis') and self.processing_analysis:
            return
            
        self.processing_analysis = True
        
        try:
            while self.analysis_queue:
                queue_item = self.analysis_queue.popleft()
                user_id = queue_item["user_id"]
                store_url = queue_item["store_url"]
                
                print(f"Processing analysis for user {user_id}: {store_url}")
                
                # Perform the actual analysis
                result = await self.crawl_and_analyze_store(store_url, user_id)
                
                # Save result and notify user
                await self.save_analysis_result(user_id, store_url, result)
                
                # Wait between analyses to avoid overloading APIs
                await asyncio.sleep(30)  # 30 second delay between analyses
                
        except Exception as e:
            print(f"Error processing analysis queue: {e}")
        finally:
            self.processing_analysis = False
    
    async def crawl_and_analyze_store(self, store_url: str, user_id: str) -> Dict:
        """Crawl and analyze a reseller store using Firecrawl + Claude AI"""
        try:
            platform = self._detect_platform(store_url)
            print(f"Starting analysis for {platform} store: {store_url}")
            
            # For Poshmark, try scrape with infinite scroll instead of crawl
            if platform.lower() == 'poshmark':
                return await self._analyze_poshmark_with_scrape(store_url, user_id)
            
            # Step 1: Crawl the store with platform-specific config (for other platforms)
            crawl_config = self._get_platform_crawl_config(platform, store_url)
            print(f"DEBUG: Using crawl config with {crawl_config.get('limit', 100)} page limit")
            
            headers = {
                'Authorization': f'Bearer {self.firecrawl_api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Start crawl
                async with session.post(
                    'https://api.firecrawl.dev/v1/crawl',
                    headers=headers,
                    json=crawl_config
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Crawl start failed: {response.status} - {error_text}")
                        return {"error": f"Failed to start crawl: {response.status}"}
                    
                    response_data = await response.json()
                    crawl_id = response_data.get('id')
                    
                    if not crawl_id:
                        return {"error": "No crawl ID received"}
                
                # Poll for completion with better timeout handling
                max_wait = 300  # 5 minutes
                wait_time = 0
                crawl_data = []
                
                print("Crawling store... This may take a few minutes for large inventories")
                
                while wait_time < max_wait:
                    await asyncio.sleep(10)
                    wait_time += 10
                    
                    try:
                        async with session.get(
                            f'https://api.firecrawl.dev/v1/crawl/{crawl_id}',
                            headers=headers
                        ) as status_response:
                            if status_response.status != 200:
                                print(f"Status check failed: {status_response.status}")
                                continue
                                
                            status_data = await status_response.json()
                            status = status_data.get('status')
                            
                            print(f"Crawl status: {status} (waited {wait_time}s)")
                            
                            if status == 'completed':
                                crawl_data = status_data.get('data', [])
                                print(f"Crawl completed! Found {len(crawl_data)} pages")
                                break
                            elif status == 'failed':
                                error_reason = status_data.get('error', 'Unknown error')
                                print(f"Crawl failed: {error_reason}")
                                return {"error": f"Store crawl failed: {error_reason}"}
                    except Exception as e:
                        print(f"Error checking crawl status: {e}")
                        continue
                
                if wait_time >= max_wait:
                    print("Crawl timed out after 5 minutes")
                    return {"error": "Store crawl timed out - the store may be too large or unavailable"}
            
            # Process crawl results
            return await self._process_crawl_results(crawl_data, store_url, platform)
                
        except Exception as e:
            print(f"Critical error in store analysis: {e}")
            return {"error": f"Analysis system error: {str(e)}"}
    
    async def _analyze_poshmark_with_scrape(self, store_url: str, user_id: str) -> Dict:
        """🔥 NEW: Poshmark analysis using direct API first, Firecrawl as fallback"""
        try:
            print("🔥 ATTEMPTING DIRECT POSHMARK API (bypassing Firecrawl)")
            
            # Try direct API first - faster and more reliable
            api_result = await self._poshmark_direct_api_scrape(store_url)
            
            if "error" not in api_result and api_result.get("products"):
                print(f"✅ Direct API Success: {len(api_result['products'])} products")
                return api_result
            else:
                print(f"❌ Direct API failed: {api_result.get('error', 'Unknown error')}")
                print("🔧 Falling back to Firecrawl scraping...")
            
            # Fallback to original Firecrawl method if API fails
            return await self._analyze_poshmark_with_firecrawl_fallback(store_url, user_id)
            
        except Exception as e:
            print(f"❌ Critical error in Poshmark analysis: {e}")
            print("🔧 Falling back to Firecrawl scraping...")
            return await self._analyze_poshmark_with_firecrawl_fallback(store_url, user_id)
    
    async def _analyze_poshmark_with_firecrawl_fallback(self, store_url: str, user_id: str) -> Dict:
        """Original Firecrawl-based Poshmark scraping - now used as fallback only"""
        try:
            # Load dynamic configuration from self-update system
            config = getattr(self.bot, 'self_update_system', None)
            if config and hasattr(config, 'config'):
                poshmark_settings = config.config.get('poshmark_settings', {})
                json_extraction_settings = poshmark_settings.get('json_extraction', {})
                
                # Skip JSON extraction if disabled by auto-fix
                if not json_extraction_settings.get('enabled', True):
                    print("🔧 JSON extraction disabled by auto-fix - skipping to simple scrape")
                    return await self._simple_poshmark_scrape(store_url, user_id)
            
            print("Using Firecrawl JSON schema extraction with infinite scroll")
            
            headers = {
                'Authorization': f'Bearer {self.firecrawl_api_key}',
                'Content-Type': 'application/json'
            }
            
            scrape_config = {
                'url': store_url,
                'formats': ['json'],  # Request JSON format for structured extraction
                'timeout': 45000,     # 45 seconds to stay under limit
                'maxAge': 0,          # No caching, always fresh data
                'actions': [
                    {'type': 'wait', 'milliseconds': 3000},
                    {'type': 'scroll', 'direction': 'down', 'amount': 1500},
                    {'type': 'wait', 'milliseconds': 2000},
                    {'type': 'scroll', 'direction': 'down', 'amount': 2500},
                    {'type': 'wait', 'milliseconds': 2000},
                    {'type': 'scroll', 'direction': 'down', 'amount': 3500},
                    {'type': 'wait', 'milliseconds': 2000},
                    {'type': 'scroll', 'direction': 'down', 'amount': 4000},
                    {'type': 'wait', 'milliseconds': 2000},
                    {'type': 'scroll', 'direction': 'down', 'amount': 5000},
                    {'type': 'wait', 'milliseconds': 3000}  # Final wait
                ],
                'jsonOptions': {
                    'schema': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'title': {'type': 'string'},
                                'price': {'type': 'string'},
                                'brand': {'type': 'string'},
                                'size': {'type': 'string'},
                                'listingUrl': {'type': 'string'},
                                'imageUrl': {'type': 'string'}
                            },
                            'required': ['title', 'price', 'brand', 'size', 'listingUrl', 'imageUrl']
                        }
                    },
                    'prompt': 'Extract all listings from this Poshmark closet page. For each listing, include the title, price, brand, size, listing URL, and image URL.'
                },
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': f"https://poshmark.com/closet/{store_url.split('/')[-1]}",
                    'Origin': 'https://poshmark.com'
                }
            }
            
            print(f"DEBUG: Using minimal fallback crawl config with {scrape_config.get('limit', 50)} page limit")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.firecrawl.dev/v1/scrape',
                    headers=headers,
                    json=scrape_config
                ) as response:
                    if response.status == 500:
                        print("Firecrawl JSON extraction timed out, falling back to regular crawl method")
                        return await self._fallback_poshmark_crawl(store_url, user_id)
                    
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Poshmark JSON scrape failed: {response.status} - {error_text}")
                        print("Falling back to regular crawl method")
                        return await self._fallback_poshmark_crawl(store_url, user_id)
                    
                    scrape_data = await response.json()
                    
                    if not scrape_data.get('success'):
                        error_msg = scrape_data.get('error', 'Unknown error')
                        print(f"Poshmark scrape unsuccessful: {error_msg}")
                        if 'timeout' in error_msg.lower():
                            print("Timeout detected, falling back to regular crawl method")
                            return await self._fallback_poshmark_crawl(store_url, user_id)
                        return {"error": f"Poshmark scrape failed: {error_msg}"}
                    
                    # Extract the structured JSON data
                    listings_data = scrape_data.get('data', {}).get('json', [])
                    
                    if not listings_data or not isinstance(listings_data, list):
                        print("No structured listings data found, falling back to regular crawl method")
                        return await self._fallback_poshmark_crawl(store_url, user_id)
                    
                    product_count = len(listings_data)
                    print(f"DEBUG: Poshmark JSON extraction found {product_count} structured listings")
                    
                    # Convert structured listings to markdown-like format for Claude analysis
                    formatted_content = self._format_poshmark_listings_for_analysis(listings_data)
                    
                    # Create fake crawl_data structure for compatibility with existing analysis
                    fake_crawl_data = [{
                        'url': store_url,
                        'markdown': formatted_content
                    }]
                    
                    return await self._process_crawl_results(fake_crawl_data, store_url, 'poshmark', product_count)
            
        except Exception as e:
            print(f"Error in Poshmark JSON schema extraction: {e}")
            print("Falling back to regular crawl method")
            return await self._fallback_poshmark_crawl(store_url, user_id)
    
    async def _fallback_poshmark_crawl(self, store_url: str, user_id: str) -> Dict:
        """Fallback to regular crawl method when JSON extraction fails"""
        try:
            # Check if fallback crawl is disabled by auto-fix
            config = getattr(self.bot, 'self_update_system', None)
            if config and hasattr(config, 'config'):
                poshmark_settings = config.config.get('poshmark_settings', {})
                fallback_settings = poshmark_settings.get('fallback_crawl', {})
                
                # Skip fallback crawl if disabled by auto-fix
                if not fallback_settings.get('enabled', True):
                    print("🔧 Fallback crawl disabled by auto-fix - skipping to simple scrape")
                    return await self._simple_poshmark_scrape(store_url, user_id)
            
            print("Using fallback crawl method for Poshmark")
            
            # Even simpler crawl configuration - minimal options
            crawl_config = {
                'url': store_url,
                'limit': 50,  # Smaller limit for fallback
                'scrapeOptions': {
                    'formats': ['markdown'],
                    'waitFor': 5000,
                    'timeout': 25000,
                    'actions': [
                        {'type': 'wait', 'milliseconds': 3000},
                        {'type': 'scroll', 'direction': 'down', 'amount': 1500},
                        {'type': 'wait', 'milliseconds': 2000},
                        {'type': 'scroll', 'direction': 'down', 'amount': 3000},
                        {'type': 'wait', 'milliseconds': 2000},
                        {'type': 'scroll', 'direction': 'down', 'amount': 4500},
                        {'type': 'wait', 'milliseconds': 3000}
                    ]
                }
            }
            
            print(f"DEBUG: Using minimal fallback crawl config with {crawl_config.get('limit', 50)} page limit")
            
            headers = {
                'Authorization': f'Bearer {self.firecrawl_api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Start crawl
                async with session.post(
                    'https://api.firecrawl.dev/v1/crawl',
                    headers=headers,
                    json=crawl_config
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Fallback crawl start failed: {response.status} - {error_text}")
                        # Try a simple scrape instead of crawl as final fallback
                        return await self._simple_poshmark_scrape(store_url, user_id)
                    
                    response_data = await response.json()
                    crawl_id = response_data.get('id')
                    
                    if not crawl_id:
                        print("No crawl ID received, trying simple scrape fallback")
                        return await self._simple_poshmark_scrape(store_url, user_id)
                
                # Poll for completion with shorter timeout for fallback
                max_wait = 120  # 2 minutes for fallback
                wait_time = 0
                crawl_data = []
                
                print("Fallback crawling Poshmark store...")
                
                while wait_time < max_wait:
                    await asyncio.sleep(10)
                    wait_time += 10
                    
                    try:
                        async with session.get(
                            f'https://api.firecrawl.dev/v1/crawl/{crawl_id}',
                            headers=headers
                        ) as status_response:
                            if status_response.status != 200:
                                print(f"Fallback status check failed: {status_response.status}")
                                continue
                                
                            status_data = await status_response.json()
                            status = status_data.get('status')
                            
                            print(f"Fallback crawl status: {status} (waited {wait_time}s)")
                            
                            if status == 'completed':
                                crawl_data = status_data.get('data', [])
                                print(f"Fallback crawl completed! Found {len(crawl_data)} pages")
                                
                                # If we got 0 pages, try simple scrape
                                if len(crawl_data) == 0:
                                    print("0 pages from crawl, trying simple scrape fallback")
                                    return await self._simple_poshmark_scrape(store_url, user_id)
                                break
                            elif status == 'failed':
                                error_reason = status_data.get('error', 'Unknown error')
                                print(f"Fallback crawl failed: {error_reason}")
                                print("Crawl failed, trying simple scrape fallback")
                                return await self._simple_poshmark_scrape(store_url, user_id)
                    except Exception as e:
                        print(f"Error checking fallback crawl status: {e}")
                        continue
                
                if wait_time >= max_wait:
                    print("Fallback crawl timed out, trying simple scrape fallback")
                    return await self._simple_poshmark_scrape(store_url, user_id)
            
            # Process fallback crawl results
            return await self._process_crawl_results(crawl_data, store_url, 'poshmark')
                
        except Exception as e:
            print(f"Critical error in fallback crawl: {e}")
            print("Fallback crawl exception, trying simple scrape fallback")
            return await self._simple_poshmark_scrape(store_url, user_id)

    async def _simple_poshmark_scrape(self, store_url: str, user_id: str) -> Dict:
        """Final fallback using simple scrape endpoint"""
        try:
            print("Using simple scrape as final fallback for Poshmark")
            
            # Load dynamic configuration for aggressive scrolling
            config = getattr(self.bot, 'self_update_system', None)
            scroll_settings = {
                'timeout': 30000,
                'scroll_actions': 5,
                'wait_between_scrolls': 2000,
                'scroll_amounts': [3000, 6000, 9000, 12000, 15000],
                'wait_for': 5000
            }
            
            if config and hasattr(config, 'config'):
                poshmark_settings = config.config.get('poshmark_settings', {})
                simple_scrape_settings = poshmark_settings.get('simple_scrape', {})
                if simple_scrape_settings:
                    scroll_settings.update(simple_scrape_settings)
                    print(f"🔧 Using dynamic scroll settings: {len(scroll_settings.get('scroll_amounts', []))} scroll actions")
            
            headers = {
                'Authorization': f'Bearer {self.firecrawl_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Build dynamic scroll actions based on configuration
            actions = [{'type': 'wait', 'milliseconds': scroll_settings['wait_for']}]
            
            scroll_amounts = scroll_settings.get('scroll_amounts', [3000, 6000, 9000])
            wait_time = scroll_settings.get('wait_between_scrolls', 2000)
            
            for amount in scroll_amounts:
                actions.append({'type': 'scroll', 'direction': 'down', 'amount': amount})
                actions.append({'type': 'wait', 'milliseconds': wait_time})
            
            scrape_config = {
                'url': store_url,
                'formats': ['markdown'],
                'timeout': scroll_settings['timeout'],
                'maxAge': 0,
                'actions': actions
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.firecrawl.dev/v1/scrape',
                    headers=headers,
                    json=scrape_config
                ) as response:
                    if response.status != 200:
                        print(f"Simple scrape failed: {response.status}")
                        return {"error": f"All fallback methods failed: {response.status}"}
                    
                    scrape_data = await response.json()
                    
                    if not scrape_data.get('success'):
                        error_msg = scrape_data.get('error', 'Unknown error')
                        print(f"Simple scrape unsuccessful: {error_msg}")
                        return {"error": f"Simple scrape failed: {error_msg}"}
                    
                    # Extract markdown content
                    content = scrape_data.get('data', {}).get('markdown', '')
                    
                    if not content or len(content.strip()) < 100:
                        print("Simple scrape returned insufficient content")
                        return {"error": "Store appears to be empty or inaccessible - all scraping methods failed"}
                    
                    print(f"Simple scrape got {len(content)} characters of content")
                    
                    # Create fake crawl_data structure for compatibility
                    fake_crawl_data = [{
                        'url': store_url,
                        'markdown': content
                    }]
                    
                    return await self._process_crawl_results(fake_crawl_data, store_url, 'poshmark')
            
        except Exception as e:
            print(f"Critical error in simple scrape fallback: {e}")
            return {"error": f"All Poshmark analysis methods failed: {str(e)}"}
    
    async def _process_crawl_results(self, crawl_data: list, store_url: str, platform: str, estimated_products: int = None) -> Dict:
        """Process crawled data and generate analysis"""
        # Step 2: Process crawled data with better validation
        if not crawl_data:
            return {"error": "No data retrieved from store - the store may be private or empty"}
        
        # Enhanced debug logging
        print(f"DEBUG: Successfully crawled {len(crawl_data)} pages for {store_url}")
        
        # Check pagination effectiveness
        page_urls = [page.get('url', '') for page in crawl_data]
        pagination_keywords = ['page=', 'offset=', 'start=', 'p=', 'after=', 'cursor=']
        paginated_urls = [url for url in page_urls if any(keyword in url for keyword in pagination_keywords)]
        print(f"DEBUG: Found {len(paginated_urls)} potentially paginated URLs")
        
        # Sample of URLs found for debugging
        sample_urls = page_urls[:5]
        print(f"DEBUG: Sample URLs crawled: {sample_urls}")
        
        # Platform-specific warnings and analysis
        product_count_note = ""
        if platform.lower() == 'poshmark':
            if estimated_products:
                print(f"DEBUG: Poshmark scrape analysis - estimated {estimated_products} products")
                product_count_note = f" (Note: Estimated {estimated_products} products from single page scrape with infinite scroll)"
            else:
                # For Poshmark, check if we got enough content from infinite scroll
                print(f"DEBUG: Poshmark infinite scroll analysis - crawled {len(crawl_data)} pages")
                if len(crawl_data) < 30:
                    print(f"DEBUG: Low page count for Poshmark infinite scroll - may need more scroll actions")
                    product_count_note = f" (Note: {len(crawl_data)} pages captured via infinite scroll - may be incomplete)"
                elif len(crawl_data) >= 100:
                    product_count_note = f" (Note: Captured {len(crawl_data)} pages via infinite scroll)"
                else:
                    product_count_note = f" (Note: {len(crawl_data)} pages captured via infinite scroll)"
        elif len(crawl_data) == 200:  # Hit our limit
            product_count_note = f" (Note: Crawl stopped at 200 pages - store may have more products)"
        
        # Combine page content with better content validation
        all_content = ""
        valid_pages = 0
        
        for page in crawl_data[:50]:  # Process up to 50 pages for analysis
            page_content = page.get('markdown', '')
            if page_content and len(page_content.strip()) > 50:  # Must have substantial content
                all_content += page_content + "\n\n"
                valid_pages += 1
        
        print(f"DEBUG: Using content from {valid_pages} valid pages for analysis")
        
        if not all_content.strip():
            return {"error": "No valid content found in store pages - the store may be empty or inaccessible"}
        
        # Step 3: Analyze with Claude AI with improved prompt
        analysis_prompt = f"""
        As Jim, analyze this store data. Respond with ONLY clean JSON - no markdown, no backticks, no extra text.

        Store: {store_url}
        Platform: {platform}
        Pages Analyzed: {valid_pages}{product_count_note}

        {all_content[:8000]}

        Return exactly this JSON structure with all fields:
        {{
            "overall_score": 7,
            "product_quality_score": 8,
            "pricing_strategy_score": 6,
            "listing_optimization_score": 7,
            "branding_score": 5,
            "inventory_diversity_score": 6,
            "product_count": {estimated_products or len(crawl_data)},
            "analysis_summary": "One sentence summary of store performance based on {valid_pages} pages analyzed{product_count_note}",
            "specific_recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"],
            "jim_personality_response": "Hey! I analyzed {valid_pages} pages of your store{product_count_note}. Here's what I found..."
        }}
        """
        
        if self.claude_client:
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            analysis_text = response.content[0].text.strip()
            
            # Improved JSON parsing with multiple fallback attempts
            return self._parse_analysis_json(analysis_text, estimated_products or len(crawl_data), valid_pages, product_count_note)
        else:
            return {"error": "Claude AI not configured - please check API key"}
    
    async def save_analysis_result(self, user_id: str, store_url: str, analysis_result: Dict):
        """Save analysis result and notify user"""
        try:
            if "error" not in analysis_result:
                await self.save_store_analysis(user_id, store_url, analysis_result)
                print(f"Analysis completed for user {user_id}")
                
                # Notify user via DM
                await self.notify_user_analysis_complete(user_id, store_url, analysis_result)
            else:
                print(f"Analysis failed for user {user_id}: {analysis_result['error']}")
                await self.notify_user_analysis_failed(user_id, store_url, analysis_result["error"])
        except Exception as e:
            print(f"Error saving analysis result: {e}")
    
    async def notify_user_analysis_complete(self, user_id: str, store_url: str, analysis_result: Dict):
        """Send DM to user when analysis is complete"""
        try:
            # Get the bot instance to send DMs
            bot = self.bot if hasattr(self, 'bot') else None
            if not bot:
                print("Bot instance not available for notifications")
                return
            
            user = bot.get_user(int(user_id))
            if not user:
                print(f"Could not find user {user_id} for notification")
                return
            
            # Create results embed
            results_embed = discord.Embed(
                title="✅ Your Complete Store Analysis is Ready!",
                description=f"**Store**: {store_url}\n**Products Analyzed**: {analysis_result.get('product_count', 'Unknown')}",
                color=0x00ff00
            )
            
            # Add Jim's personality response
            jim_response = analysis_result.get('jim_personality_response', '')
            if jim_response:
                results_embed.add_field(
                    name="💬 Jim's Take",
                    value=jim_response[:1024],
                    inline=False
                )
            
            # Add all scores
            results_embed.add_field(
                name="🎯 Overall Score",
                value=f"**{analysis_result.get('overall_score', 0)}/10**",
                inline=True
            )
            results_embed.add_field(
                name="📦 Product Quality",
                value=f"{analysis_result.get('product_quality_score', 0)}/10",
                inline=True
            )
            results_embed.add_field(
                name="💰 Pricing Strategy",
                value=f"{analysis_result.get('pricing_strategy_score', 0)}/10",
                inline=True
            )
            results_embed.add_field(
                name="✨ Listing Optimization",
                value=f"{analysis_result.get('listing_optimization_score', 0)}/10",
                inline=True
            )
            results_embed.add_field(
                name="🎨 Branding",
                value=f"{analysis_result.get('branding_score', 0)}/10",
                inline=True
            )
            results_embed.add_field(
                name="🔄 Inventory Diversity",
                value=f"{analysis_result.get('inventory_diversity_score', 0)}/10",
                inline=True
            )
            results_embed.add_field(
                name="📝 Summary",
                value=analysis_result.get('analysis_summary', 'No summary available'),
                inline=False
            )
            
            # Add recommendations
            recommendations = analysis_result.get('specific_recommendations', [])
            if recommendations:
                rec_text = '\n'.join([f"• {rec}" for rec in recommendations[:3]])
                results_embed.add_field(
                    name="💡 Top Recommendations",
                    value=rec_text,
                    inline=False
                )
            
            results_embed.add_field(
                name="📊 Next Steps",
                value="Use `!progress` to see all your analyses\nUse `!ask` for personalized follow-up advice!",
                inline=False
            )
            
            await user.send(embed=results_embed)
            print(f"Sent analysis results to user {user_id}")
            
        except Exception as e:
            print(f"Error sending analysis notification to user {user_id}: {e}")
    
    async def notify_user_analysis_failed(self, user_id: str, store_url: str, error_message: str):
        """Notify user that their store analysis failed"""
        try:
            user = self.bot.get_user(int(user_id))
            if user:
                # Create a more helpful error message based on the error type
                if "timeout" in error_message.lower():
                    title = "⏰ Store Analysis Timed Out"
                    description = "The store analysis took longer than expected."
                    help_text = "This can happen with very large stores. Try again or use a smaller store section."
                elif "private" in error_message.lower() or "empty" in error_message.lower():
                    title = "🔒 Store Access Issue"
                    description = "I couldn't access the store content."
                    help_text = "Make sure the store is public and the URL is correct."
                elif "parsing" in error_message.lower():
                    title = "🔧 Analysis Processing Issue"
                    description = "I analyzed your store but had trouble formatting the results."
                    help_text = "The basic analysis was completed - try again to get the full report."
                else:
                    title = "❌ Store Analysis Issue"
                    description = "I encountered an issue while analyzing your store."
                    help_text = "Please try again in a few minutes or contact support if the issue persists."
                
                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=0xff9500  # Orange for warnings
                )
                embed.add_field(
                    name="Store URL",
                    value=store_url,
                    inline=False
                )
                embed.add_field(
                    name="💡 What to try",
                    value=help_text,
                    inline=False
                )
                embed.add_field(
                    name="🔄 Try Again",
                    value="You can retry analysis in 1 hour or try a different store URL",
                    inline=False
                )
                embed.set_footer(text="Jim the Mentor • Store Analysis")
                
                await user.send(embed=embed)
        except Exception as e:
            print(f"Failed to notify user of analysis failure: {e}")
    
    async def generate_personalized_advice(self, user_id: str, user_input: str, context: str = "") -> str:
        """
        Generate personalized mentorship advice using Claude AI
        """
        try:
            # Get user data for context
            user_data = await self.get_user_mentorship_data(user_id)
            
            advice_prompt = f"""
            You are Jim, a knowledgeable and supportive reselling mentor with years of experience. Respond to this user's question with accurate, current reselling advice:

            User Question: {user_input}
            Context: {context}

            User Background:
            - Experience Level: {user_data.get('experience_level', 'Unknown')}
            - Primary Platform: {user_data.get('primary_platform', 'Unknown')}
            - Goals: {user_data.get('initial_goals', 'Not specified')}
            - Total Sessions: {user_data.get('total_sessions', 0)}

            IMPORTANT RESELLING GUIDELINES:
            - Bundling: Only recommend bundling when buyers request it or for slow-moving inventory. Most successful resellers sell items individually for higher profit margins.
            - Platform-specific advice: Tailor recommendations to their primary platform (Poshmark, Mercari, eBay, etc.)
            - Current market trends: Consider 2024/2025 reselling landscape
            - Accurate strategies: Base advice on proven methods, not outdated practices

            Respond as Jim with:
            - Casual, encouraging tone with emojis (but keep it professional)
            - Specific, actionable advice based on current reselling best practices
            - Personal touches referencing their goals/progress
            - 2-3 paragraphs max
            - End with a motivating question or challenge
            
            If you're unsure about current trends or platform-specific details, say "I'm thinking about this" and provide general guidance while noting they should verify current platform policies.
            """
            
            if self.claude_client:
                response = self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    messages=[{"role": "user", "content": advice_prompt}]
                )
                
                jim_response = response.content[0].text
                
                # Log the session
                await self.log_mentorship_session(
                    user_id, "advice", user_input, jim_response, "advice"
                )
                
                return jim_response
            else:
                return "Hey! My advanced AI brain isn't connected right now, but I'm still here to help! 🧠✨"
                
        except Exception as e:
            return f"Oops! Something went sideways on my end. Let's try that again! 😅 ({str(e)})"
    
    # async def create_voice_message(self, user_id: str, message_text: str, message_type: str = "motivation") -> Optional[bytes]:
    #     """
    #     Generate voice message using ElevenLabs
    #     """
    #     try:
    #         if not self.elevenlabs_api_key:
    #             return None
                
    #         # Generate audio using ElevenLabs client
    #         client = elevenlabs.Client(api_key=self.elevenlabs_api_key)
            
    #         audio = client.generate(
    #             text=message_text,
    #             voice="Rachel",  # You can customize this
    #             model="eleven_monolingual_v1"
    #         )
            
    #         # Convert generator to bytes
    #         audio_bytes = b"".join(audio)
            
    #         # Save to database
    #         await self.save_voice_message(
    #             user_id, message_type, message_text, audio_bytes
    #         )
            
    #         return audio_bytes
            
    #     except Exception as e:
    #         print(f"Voice generation failed: {e}")
    #         return None
    
    # === Database Utility Functions ===
    
    async def get_user_mentorship_data(self, user_id: str) -> Dict:
        """Get comprehensive user mentorship data"""
        try:
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                
                # Get user profile
                cursor.execute('''
                    SELECT * FROM mentorship_users WHERE user_id = ?
                ''', (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    return {}
                
                # Convert to dict
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, user_data))
                
                # Get recent goals
                cursor.execute('''
                    SELECT * FROM mentorship_goals 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC LIMIT 3
                ''', (user_id,))
                goals = cursor.fetchall()
                user_dict['active_goals'] = goals
                
                # Get recent progress
                cursor.execute('''
                    SELECT * FROM user_progress 
                    WHERE user_id = ? 
                    ORDER BY date DESC LIMIT 7
                ''', (user_id,))
                progress = cursor.fetchall()
                user_dict['recent_progress'] = progress
                
                return user_dict
                
        except Exception as e:
            print(f"Error getting user data: {e}")
            return {}
    
    async def save_store_analysis(self, user_id: str, store_url: str, analysis: Dict):
        """Save store analysis results to database"""
        try:
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO store_analysis (
                        user_id, store_url, platform, overall_score,
                        product_quality_score, pricing_strategy_score,
                        listing_optimization_score, branding_score,
                        inventory_diversity_score, analysis_summary, recommendations, jim_response, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, store_url, self._detect_platform(store_url),
                    analysis.get('overall_score', 0),
                    analysis.get('product_quality_score', 0),
                    analysis.get('pricing_strategy_score', 0),
                    analysis.get('listing_optimization_score', 0),
                    analysis.get('branding_score', 0),
                    analysis.get('inventory_diversity_score', 0),
                    analysis.get('analysis_summary', ''),
                    json.dumps(analysis.get('specific_recommendations', [])),
                    analysis.get('jim_personality_response', ''),
                    datetime.now().isoformat()
                ))
                
        except Exception as e:
            print(f"Error saving store analysis: {e}")
    
    async def log_mentorship_session(self, user_id: str, session_type: str, 
                                   user_input: str, jim_response: str, advice_category: str):
        """Log mentorship session to database"""
        try:
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO mentorship_sessions (
                        user_id, session_type, user_input, jim_response,
                        timestamp, channel_type, advice_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, session_type, user_input, jim_response,
                    datetime.now().isoformat(), 'dm', advice_category
                ))
                
        except Exception as e:
            print(f"Error logging session: {e}")
    
    # async def save_voice_message(self, user_id: str, message_type: str, 
    #                            transcript: str, audio_data: bytes):
    #     """Save voice message to database"""
    #     try:
    #         with sqlite3.connect('beta_testing.db') as conn:
    #             cursor = conn.cursor()
                
    #             cursor.execute('''
    #                 INSERT INTO voice_messages (
    #                     user_id, message_type, transcript, audio_data,
    #                     voice_model, created_at
    #                 ) VALUES (?, ?, ?, ?, ?, ?)
    #             ''', (
    #                 user_id, message_type, transcript, audio_data,
    #                 'Rachel', datetime.now().isoformat()
    #             ))
                
    #     except Exception as e:
    #         print(f"Error saving voice message: {e}")
    
    async def create_user_goal(self, user_id: str, goal_title: str, 
                             goal_description: str, target_value: float = 0, 
                             goal_type: str = "general", deadline: str = None):
        """Create a new user goal"""
        try:
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO mentorship_goals (
                        user_id, goal_title, goal_description, target_value,
                        goal_type, deadline, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, goal_title, goal_description, target_value,
                    goal_type, deadline, datetime.now().isoformat()
                ))
                
        except Exception as e:
            print(f"Error creating goal: {e}")
    
    async def update_user_progress(self, user_id: str, sales_count: int = 0, 
                                 revenue: float = 0.0, listings_created: int = 0,
                                 mood_score: int = 5, daily_challenges: str = "",
                                 wins_today: str = ""):
        """Update daily user progress"""
        try:
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                
                today = datetime.now().date().isoformat()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO user_progress (
                        user_id, date, sales_count, revenue, listings_created,
                        mood_score, daily_challenges, wins_today
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, today, sales_count, revenue, listings_created,
                    mood_score, daily_challenges, wins_today
                ))
                
        except Exception as e:
            print(f"Error updating progress: {e}")
    
    def _detect_platform(self, url: str) -> str:
        """Detect reselling platform from URL"""
        url_lower = url.lower()
        if 'poshmark' in url_lower:
            return 'Poshmark'
        elif 'ebay' in url_lower:
            return 'eBay'
        elif 'mercari' in url_lower:
            return 'Mercari'
        elif 'depop' in url_lower:
            return 'Depop'
        elif 'facebook' in url_lower or 'marketplace' in url_lower:
            return 'Facebook Marketplace'
        else:
            return 'Other'
    
    def _get_platform_crawl_config(self, platform: str, store_url: str) -> Dict:
        """Get platform-specific crawl configuration"""
        base_config = {
            'url': store_url,
            'limit': 200,  # Increased to get more products
            'scrapeOptions': {
                'formats': ['markdown'],  # Request markdown format for structured extraction
                'includeTags': ['title', 'meta', 'img', 'a', 'price', 'span', 'div'],
                'excludeTags': ['nav', 'footer', 'header', 'script', 'style'],
                'waitFor': 5000
            }
        }
        
        # Platform-specific configurations
        if platform == 'poshmark':
            # For Poshmark, focus on infinite scroll rather than pagination
            base_config.update({
                'includes': [
                    '*/closet/*',  # Main closet pages
                    '*/listing/*', # Individual product listings
                    '*poshmark.com/closet/*',
                    '*poshmark.com/listing/*'
                ],
                'excludes': [
                    '*/following*', 
                    '*/followers*', 
                    '*/likes*',
                    '*/notifications*',
                    '*/bundles*',
                    '*/feed*',
                    '*/news*',
                    '*/help*',
                    '*/search*',
                    '*/brand/*'
                ],
                'crawlerOptions': {
                    'includes': ['**/closet/**', '**/listing/**'],
                    'maxDepth': 2,  # Don't go too deep, focus on main pages
                    'followLinks': True,
                    'allowBackwardCrawling': False,  # Not needed for infinite scroll
                    'ignoreSitemap': True,  # Sitemap won't help with dynamic content
                    'respectRobotsTxt': False
                },
                # Enhanced infinite scroll handling
                'pageOptions': {
                    'includeHtml': False,
                    'includeRawHtml': False,
                    'waitFor': 10000,  # Wait longer for initial content
                    'screenshot': False,
                    'fullPageScreenshot': False,
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    },
                    # Multiple scroll actions to trigger infinite scroll
                    'actions': [
                        {
                            'type': 'wait',
                            'milliseconds': 3000
                        },
                        {
                            'type': 'scroll',
                            'coordinate': [0, 1000]
                        },
                        {
                            'type': 'wait',
                            'milliseconds': 2000
                        },
                        {
                            'type': 'scroll',
                            'coordinate': [0, 2000]
                        },
                        {
                            'type': 'wait',
                            'milliseconds': 2000
                        },
                        {
                            'type': 'scroll',
                            'coordinate': [0, 3000]
                        },
                        {
                            'type': 'wait',
                            'milliseconds': 2000
                        },
                        {
                            'type': 'scroll',
                            'coordinate': [0, 4000]
                        },
                        {
                            'type': 'wait',
                            'milliseconds': 2000
                        },
                        {
                            'type': 'scroll',
                            'coordinate': [0, 5000]
                        },
                        {
                            'type': 'wait',
                            'milliseconds': 3000
                        }
                    ]
                }
            })
        elif platform == 'mercari':
            base_config.update({
                'includes': ['*/item/*', '*/profile/*'],
                'excludes': ['*/reviews*', '*/following*']
            })
        elif platform == 'ebay':
            base_config.update({
                'includes': ['*/itm/*', '*/usr/*'],
                'excludes': ['*/feedback*', '*/allitem*']
            })
        elif platform == 'depop':
            base_config.update({
                'includes': ['*/products/*', '*/users/*'],
                'excludes': ['*/reviews*', '*/following*']
            })
        
        return base_config
    
    def _format_poshmark_listings_for_analysis(self, listings: list) -> str:
        """Format structured Poshmark listings data for Claude analysis"""
        formatted_lines = [
            "=== POSHMARK STORE ANALYSIS ===",
            f"Total Products Found: {len(listings)}",
            "",
            "PRODUCT LISTINGS:",
            ""
        ]
        
        for i, listing in enumerate(listings[:100], 1):  # Limit to first 100 for analysis
            title = listing.get('title', 'No title')
            price = listing.get('price', 'No price')
            brand = listing.get('brand', {}).get('display_name', "") if listing.get('brand') else ""
            size = listing.get('size_obj', {}).get('display', "") if listing.get('size_obj') else ""
            
            formatted_lines.extend([
                f"LISTING #{i}:",
                f"Title: {title}",
                f"Price: {price}",
                f"Brand: {brand}",
                f"Size: {size}",
                f"URL: {listing.get('listingUrl', 'No URL')}",
                f"Image URL: {listing.get('imageUrl', 'No image URL')}",
                ""
            ])
        
        if len(listings) > 100:
            formatted_lines.append(f"... and {len(listings) - 100} more listings")
        
        return "\n".join(formatted_lines)

    def _parse_analysis_json(self, analysis_text: str, product_count: int, valid_pages: int, product_count_note: str) -> Dict:
        """Parse Claude's analysis response into structured JSON"""
        try:
            # Remove any markdown formatting
            cleaned_text = analysis_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Try to parse JSON
            analysis_result = json.loads(cleaned_text)
            
            # Validate required fields and add defaults if missing
            required_fields = {
                'overall_score': 5,
                'product_quality_score': 5,
                'pricing_strategy_score': 5,
                'listing_optimization_score': 5,
                'branding_score': 5,
                'inventory_diversity_score': 5,
                'product_count': product_count,
                'analysis_summary': f'Store analysis based on {valid_pages} pages{product_count_note}',
                'specific_recommendations': ['Improve product photos', 'Optimize pricing strategy', 'Enhance product descriptions'],
                'jim_personality_response': f'Hey! I analyzed {valid_pages} pages of your store{product_count_note}. Here\'s what I found...'
            }
            
            # Fill in missing fields
            for field, default_value in required_fields.items():
                if field not in analysis_result:
                    analysis_result[field] = default_value
            
            # Ensure numeric fields are valid
            numeric_fields = ['overall_score', 'product_quality_score', 'pricing_strategy_score', 
                            'listing_optimization_score', 'branding_score', 'inventory_diversity_score']
            
            for field in numeric_fields:
                try:
                    score = int(analysis_result.get(field, 5))
                    analysis_result[field] = max(1, min(10, score))  # Clamp between 1-10
                except (ValueError, TypeError):
                    analysis_result[field] = 5
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Raw analysis text: {analysis_text[:200]}...")
            
            # Return fallback analysis
            return {
                'overall_score': 6,
                'product_quality_score': 6,
                'pricing_strategy_score': 6,
                'listing_optimization_score': 6,
                'branding_score': 5,
                'inventory_diversity_score': 6,
                'product_count': product_count,
                'analysis_summary': f'Store analysis completed on {valid_pages} pages{product_count_note} (JSON parsing error occurred)',
                'specific_recommendations': [
                    'Continue building inventory with quality items',
                    'Focus on competitive pricing research',
                    'Improve listing photos and descriptions'
                ],
                'jim_personality_response': f'Hey! I analyzed your store but had some technical issues with the detailed breakdown. Based on {valid_pages} pages{product_count_note}, your store looks decent overall!',
                'json_error': str(e),
                'raw_response': analysis_text[:500]
            }
        except Exception as e:
            print(f"Critical error in JSON parsing: {e}")
            return {
                'error': f'Analysis parsing failed: {str(e)}',
                'json_error': str(e),
                'raw_response': analysis_text[:500]
            }

    async def _poshmark_direct_api_scrape(self, store_url: str) -> Dict:
        """
        🔥 UPDATED: Proper Poshmark API scraping using correct endpoints and authentication
        Based on comprehensive Poshmark scraping guide
        """
        try:
            import re
            
            # Extract username from Poshmark URL
            username_match = re.search(r'poshmark\.com/closet/([^/?]+)', store_url)
            if not username_match:
                return {"error": "Could not extract username from Poshmark URL"}
            
            username = username_match.group(1)
            print(f"🔥 Using proper Poshmark API for user: {username}")
            
            # Step 1: Get initial page to extract CSRF token and initial data
            closet_url = f"https://poshmark.com/closet/{username}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin"
            }
            
            async with aiohttp.ClientSession() as session:
                # Get initial page
                print(f"📡 Getting initial page: {closet_url}")
                async with session.get(closet_url, headers=headers) as response:
                    if response.status != 200:
                        return {"error": f"Failed to load closet page: {response.status}"}
                    
                    html_content = await response.text()
                    print(f"📄 Got HTML page ({len(html_content)} chars)")
                
                # Extract CSRF token from HTML
                csrf_token = None
                csrf_match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html_content)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                    print(f"🔐 Found CSRF token: {csrf_token[:20]}...")
                
                # Update headers for API calls
                api_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer": closet_url,
                    "Origin": "https://poshmark.com",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin"
                }
                
                if csrf_token:
                    api_headers["X-CSRF-Token"] = csrf_token
                
                # Step 2: Get user info first
                user_api_url = "https://poshmark.com/vm-rest/users/info"
                user_params = {"username": username}
                
                print(f"👤 Getting user info: {user_api_url}?username={username}")
                async with session.get(user_api_url, headers=api_headers, params=user_params) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        print(f"✅ User info response: {list(user_data.keys())}")
                    else:
                        print(f"❌ User info failed: {response.status}")
                
                # Step 3: Get closet listings with proper parameters
                api_url = "https://poshmark.com/vm-rest/users/closet"
                all_products = []
                offset = 0
                limit = 48
                max_requests = 50  # Safety limit
                requests_made = 0
                
                while requests_made < max_requests:
                    params = {
                        "username": username,
                        "offset": offset,
                        "limit": limit,
                        "sort_by": "added_desc"
                    }
                    
                    print(f"📦 Request {requests_made + 1}: offset={offset}, limit={limit}")
                    
                    async with session.get(api_url, headers=api_headers, params=params) as response:
                        if response.status != 200:
                            print(f"❌ API request failed: {response.status}")
                            break
                        
                        data = await response.json()
                        print(f"📋 Response keys: {list(data.keys())}")
                        
                        if "error" in data:
                            print(f"❌ API Error: {data['error']}")
                            break
                        
                        if "data" not in data or "listings" not in data["data"]:
                            print(f"❌ Unexpected response format: {data}")
                            break
                        
                        listings = data["data"]["listings"]
                        if not listings:
                            print("✅ No more listings found - pagination complete")
                            break
                        
                        print(f"📦 Found {len(listings)} listings at offset {offset}")
                        
                        # Process listings
                        for listing in listings:
                            product = {
                                "title": listing.get("title", ""),
                                "price": listing.get("price", ""),
                                "original_price": listing.get("original_price", ""),
                                "brand": listing.get("brand", {}).get("display_name", "") if listing.get("brand") else "",
                                "size": listing.get("size_obj", {}).get("display", "") if listing.get("size_obj") else "",
                                "category": listing.get("category", {}).get("display_name", "") if listing.get("category") else "",
                                "subcategory": listing.get("subcategory", {}).get("display_name", "") if listing.get("subcategory") else "",
                                "listing_url": f"https://poshmark.com/listing/{listing.get('id', '')}",
                                "image_url": listing.get("cover_shot", {}).get("url", "") if listing.get("cover_shot") else "",
                                "status": listing.get("status", ""),
                                "condition": listing.get("condition", ""),
                                "created_at": listing.get("created_at", ""),
                                "inventory_status": listing.get("inventory_status", "available"),
                                "listing_id": listing.get("id", "")
                            }
                            all_products.append(product)
                        
                        # Update for next request
                        offset += len(listings)
                        requests_made += 1
                        
                        # Rate limiting
                        await asyncio.sleep(0.5)
                
                print(f"🎉 Successfully collected {len(all_products)} products from {username}")
                
                return {
                    "platform": "poshmark",
                    "store_url": store_url,
                    "username": username,
                    "total_products": len(all_products),
                    "products": all_products,
                    "scrape_method": "direct_api_v2",
                    "requests_made": requests_made
                }
                
        except Exception as e:
            print(f"❌ Error in Poshmark direct API scrape: {e}")
            return {"error": f"Poshmark API scraping failed: {str(e)}"}
        
        return {"error": "Unknown error in Poshmark scraping"}

class BetaTestingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.messages = True
        intents.guild_messages = True
        intents.dm_messages = True
        intents.message_content = True
        print("\nInitializing bot with intents:")
        print(f"- messages: {intents.messages}")
        print(f"- guild_messages: {intents.guild_messages}")
        print(f"- dm_messages: {intents.dm_messages}")
        print(f"- message_content: {intents.message_content}")
        super().__init__(command_prefix='!', intents=intents)
        
        # Initialize Gemini AI
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Beta testing channels (configure these)
        self.beta_channels = []  # Will be populated from config
        self.beta_tester_role_name = "beta tester"
        self.beta_staff_role_name = "staff"
        self.guild_id = None
        self.scanning_mode = False
        
        # Staff and developer usernames to prioritize
        self.staff_developers = ['Jin', 'treblig', 'JM', 'Hailin']
        
        # Initialize database
        init_database()
        
        # === JIM THE MENTOR - Initialize Mentorship Services ===
        self.mentorship_services = MentorshipServices(self)
        
        # === JIM THE MENTOR - Queue System ===
        self.queue = deque()
        
        # === JIM THE MENTOR - Self-Update System Integration ===
        self.self_update_system = SelfUpdateSystem(self)
        self.self_update_commands = SelfUpdateCommands(self)
        
        # === GOOGLE SHEETS INTEGRATION - Bug Tracking ===
        self.sheets_config = BugTrackingConfig()
        self.sheets_config.SPREADSHEET_ID = '1lTOj3r-LVMnp-oVu7dDnGWjBzKxWeZJJGZSxUMaMwB4'
        self.sheets_manager = GoogleSheetsManager(
            spreadsheet_id=self.sheets_config.SPREADSHEET_ID,
            credentials_path=self.sheets_config.CREDENTIALS_PATH
        ) if self.sheets_config.SPREADSHEET_ID else None

        # === AMBASSADOR PROGRAM ===
        self.ambassador_program = AmbassadorProgram(self)
        
        # === JIM THE MENTOR - Natural Conversation System ===
        self.natural_conversation_system = NaturalConversationSystem(self)
        
    async def on_ready(self):
        print(f'Jim (Beta Testing Assistant) is now online!')
        print(f'Connected to {len(self.guilds)} Discord servers')
        print(f'Ready to assist with beta testing coordination!')
        print(f'Bot User ID: {self.user.id}')
        print(f'Bot Username: {self.user.name}')
        
        # Start Ambassador Program monthly check task
        if hasattr(self, 'ambassador_program') and not self.ambassador_program.monthly_check.is_running():
            self.ambassador_program.monthly_check.start()
            print('✅ Ambassador Program monthly check task started')
            
        # Initialize Ambassador Program database
        if hasattr(self, 'ambassador_program'):
            self.ambassador_program.init_local_database()
            print('✅ Ambassador Program database initialized')
            
        # Load configuration first
        await self.load_config()
        
        # Send startup notification to beta channels
        await self.send_startup_notification()
        
        # Scan recent history silently (no announcements)
        await self.scan_recent_history_silent()
        
        # Start 30-minute update task
        if not self.scheduled_update_task.is_running():
            self.scheduled_update_task.start()
    
    async def on_message(self, message):
        try:
            # Simple test to verify this method is being called
            print(f"\n🔔 MESSAGE RECEIVED: {message.content[:50]}... from {message.author}")
            
            # Don't respond to ourselves or other bots
            if message.author == self.user or message.author.bot:
                return
            
            # Handle DMs for ambassador submissions
            if isinstance(message.channel, discord.DMChannel):
                try:
                    ambassador = None
                    
                    # Check Supabase first (persistent storage)
                    if self.ambassador_program.supabase:
                        try:
                            result = self.ambassador_program.supabase.table('ambassadors').select('*').eq('discord_id', str(message.author.id)).eq('status', 'active').execute()
                            if result.data:
                                ambassador = result.data[0]
                                # Convert to tuple format for compatibility
                                ambassador = (
                                    ambassador['discord_id'], ambassador['username'], ambassador['social_handles'],
                                    ambassador['target_platforms'], ambassador['joined_date'], ambassador['total_points'],
                                    ambassador['current_month_points'], ambassador['consecutive_months'],
                                    ambassador['reward_tier'], ambassador['status']
                                )
                        except Exception as e:
                            print(f"⚠️ Supabase lookup failed: {e}")
                    
                    # Fallback to local SQLite if Supabase failed or no data
                    if not ambassador:
                        with sqlite3.connect('ambassador_program.db') as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT * FROM ambassadors WHERE discord_id = ? AND status = "active"', (str(message.author.id),))
                            ambassador = cursor.fetchone()
                    
                    if ambassador:
                        await handle_ambassador_submission(message, ambassador)
                        return  # Don't process further if it's an ambassador submission
                    else:
                        # Not an ambassador, check if it's a command before sending help
                        if not message.content.startswith('!'):
                            # Not a command, send help message for DMs
                            embed = discord.Embed(
                                title="👋 Hello!",
                                description="I'm Jim, the beta testing assistant. To submit content as an ambassador, you need to be registered first.",
                                color=0x3498db
                            )
                            embed.add_field(
                                name="📝 How to become an ambassador",
                                value="Ask a Staff member to add you with: `!ambassador add @yourname platforms`",
                                inline=False
                            )
                            await message.channel.send(embed=embed)
                            return
                        # If it's a command, let it fall through to command processing
                except Exception as e:
                    print(f"❌ Error checking ambassador status: {e}")
            
            # Handle Ambassador Program category channels
            elif message.guild and message.channel.category and "ambassador program" in message.channel.category.name.lower():
                try:
                    with sqlite3.connect('ambassador_program.db') as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM ambassadors WHERE discord_id = ? AND status = "active"', (str(message.author.id),))
                        ambassador = cursor.fetchone()
                    
                    if ambassador:
                        await handle_ambassador_submission(message, ambassador)
                        return  # Don't process further if it's an ambassador submission
                except Exception as e:
                    print(f"❌ Error processing ambassador channel submission: {e}")
                
            # Check if Jim is mentioned in the message
            if self.user in message.mentions:
                print(f"🎯 JIM WAS MENTIONED! Processing question...")
                
                # Extract the question (remove the mention)
                question = message.content
                for mention in message.mentions:
                    question = question.replace(f'<@{mention.id}>', '').strip()
                
                if question:
                    print(f"📝 Question extracted: {question}")
                    
                    # Use Gemini to generate a response
                    try:
                        response = self.model.generate_content(f"""
                        You are Jim, a helpful Discord bot assistant for beta testing. A user asked: "{question}"
                        
                        Provide a helpful, concise response. If it's about bugs, suggest they report it properly.
                        If it's about the app, provide general guidance. Keep responses under 200 words.
                        """)
                        
                        if response and response.text:
                            await message.reply(response.text)
                            print(f"✅ Responded to mention with: {response.text[:100]}...")
                        else:
                            await message.reply("I'm here to help! Could you rephrase your question?")
                            
                    except Exception as e:
                        print(f"❌ Error generating response: {e}")
                        await message.reply("I'm having trouble processing that right now. Please try again later!")
                        
                return  # Don't process further if it was a mention
            
            # Track messages in beta channels for bug detection
            if str(message.channel.id) in self.beta_channels:
                await self.track_message(message)
                
        except Exception as e:
            print(f"❌ Error in on_message: {e}")
            
        # Always process commands at the end
        await self.process_commands(message)
    
    async def handle_question(self, message, question):
        """Handle a question asked to Jim by searching chat history"""
        try:
            # Show typing indicator while processing
            async with message.channel.typing():
                print(f"🔍 Searching for answers to: {question}")
                
                # Search for relevant messages in this channel first
                search_results = await self.search_chat_history(
                    query=question,
                    channel_id=str(message.channel.id),
                    days_back=30
                )
                
                if not search_results:
                    # If no results found in this channel, try searching all channels
                    print(f"🔍 No results in current channel, searching all channels...")
                    search_results = await self.search_chat_history(
                        query=question,
                        days_back=30
                    )
                
                if search_results:
                    print(f"✅ Found {len(search_results)} relevant messages")
                    # Format the search results
                    formatted_results = []
                    for i, result in enumerate(search_results[:5], 1):  # Limit to top 5 results
                        # Truncate long messages
                        content = result['content']
                        if len(content) > 200:
                            content = content[:197] + '...'
                            
                        formatted_results.append(
                            f"**{i}.** *{result['username']}* in #{result['channel']}:"
                            f"\n> {content}"
                            f"\n*({result['timestamp'].split('T')[0]})*\n"
                        )
                    
                    # If we have multiple results, ask if any are helpful
                    if len(search_results) > 1:
                        response = (
                            f"Hey {message.author.mention}, I may have found multiple answers for your question, are these helpful?\n\n"
                            + "\n".join(formatted_results) +
                            "\nLet me know if you'd like more details on any of them!"
                        )
                    else:
                        # If only one result, present it as the answer
                        response = (
                            f"{message.author.mention}, I found this information that might help:\n\n"
                            + formatted_results[0] +
                            "\nLet me know if you need more details!"
                        )
                    
                    # Send the response
                    await message.reply(response, mention_author=True)
                else:
                    print(f"❌ No relevant information found")
                    # No results found
                    await message.reply(
                        f"{message.author.mention} I couldn't find any relevant information in the chat history. "
                        "Would you like me to help you search for something more specific?"
                    )
                    
        except Exception as e:
            print(f"❌ Error handling question: {e}")
            await message.reply(f"{message.author.mention} Sorry, I encountered an error while searching for answers. Please try again!")
                
            # Show typing indicator while processing
            async with message.channel.typing():
                # Search for relevant messages in this channel
                search_results = await self.search_chat_history(
                    query=question,
                    channel_id=str(message.channel.id),
                    days_back=30
                )
                
                if not search_results:
                    # If no results found in this channel, try searching all channels
                    search_results = await self.search_chat_history(
                        query=question,
                        days_back=30
                    )
                
                if search_results:
                    # Format the search results
                    formatted_results = []
                    for i, result in enumerate(search_results[:5], 1):  # Limit to top 5 results
                        # Truncate long messages
                        content = result['content']
                        if len(content) > 200:
                            content = content[:197] + '...'
                            
                        formatted_results.append(
                            f"**{i}.** *{result['username']}* in #{result['channel']}:"
                            f"\n> {content}"
                            f"\n*({result['timestamp'].split('T')[0]})*\n"
                        )
                    
                    # If we have multiple results, ask if any are helpful
                    if len(search_results) > 1:
                        response = (
                            f"Hey {message.author.mention}, I found some information that might help with your question:\n\n"
                            + "\n".join(formatted_results) +
                            "\nAre any of these helpful? Let me know if you'd like more details on any of them!"
                        )
                    else:
                        # If only one result, present it as the answer
                        response = (
                            f"{message.author.mention}, I found this information that might help:\n\n"
                            + formatted_results[0] +
                            "\nLet me know if you need more details!"
                        )
                    
                    # Send the response
                    await message.reply(response, mention_author=True)
                else:
                    # No results found
                    await message.reply(
                        f"{message.author.mention} I couldn't find any relevant information in the chat history. "
                        "Would you like me to help you search for something specific?"
                    )
        
        # Process commands
        await self.process_commands(message)
        
        # Track the message in the database
        await self.track_message(message)
    
    @tasks.loop(minutes=30)  # Check every 30 minutes
    async def scheduled_update_task(self):
        """Send proactive updates 3 times per day: 9am, 5pm, 10pm EST"""
        
        # Get current time in EST
        import pytz
        est = pytz.timezone('US/Eastern')
        current_time = datetime.now(est)
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # Target times: 9am, 5pm (17), 10pm (22) EST
        target_hours = [9, 17, 22]
        
        # Only send updates at the target hours and within first 30 minutes
        if current_hour in target_hours and current_minute < 30:
            # Check if we already sent an update this hour
            if not hasattr(self, '_last_update_hour') or self._last_update_hour != current_hour:
                self._last_update_hour = current_hour
                
                try:
                    await self.send_scheduled_update(current_hour)
                except Exception as e:
                    print(f"Error in scheduled update: {e}")
    
    async def send_scheduled_update(self, hour):
        """Send automated update to beta channels with Google Sheets integration status"""
        
        # Determine time period and lookback based on hour
        if hour == 9:
            period_name = "Morning"
            hours_back = 12  # Since last evening update
            greeting = "🌅 Good morning, beta testers!"
        elif hour == 17:
            period_name = "Afternoon" 
            hours_back = 8   # Since morning update
            greeting = "🌆 Good afternoon, time for an update!"
        else:  # hour == 22
            period_name = "Evening"
            hours_back = 5   # Since afternoon update
            greeting = "🌙 Good evening, wrapping up the day!"
        
        # Get recent activity from the specified lookback period
        lookback_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        with sqlite3.connect('beta_testing.db') as conn:
            cursor = conn.cursor()
            
            # Get new messages, bugs, and activity from lookback period
            cursor.execute('''
                SELECT COUNT(*) FROM messages WHERE timestamp > ?
            ''', (lookback_time,))
            new_messages = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM bugs WHERE timestamp > ? AND status != 'potential'
            ''', (lookback_time,))
            new_bugs = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM bugs WHERE status = 'potential' AND timestamp > ?
            ''', (lookback_time,))
            potential_bugs = cursor.fetchone()[0]
            
            # Get Google Sheets sync status information
            cursor.execute('''
                SELECT COUNT(*) FROM bugs WHERE timestamp > ?
            ''', (lookback_time,))
            total_new_bugs = cursor.fetchone()[0]
        
        # Check Google Sheets integration status
        sheets_status = "🟢 Active" if self.sheets_manager else "🔴 Offline"
        
        # Only send update if there's activity OR it's a scheduled check-in
        if new_messages > 2 or new_bugs > 0 or potential_bugs > 0 or hour in [9, 17, 22]:
            # Get AI summary of recent activity
            context = await self.get_recent_activity_context(hours_back)
            
            ai_prompt = f"""Create a brief {period_name.lower()} update of beta testing activity. Focus on:
        1. Key discussions or issues mentioned
        2. Any new bugs or problems reported  
        3. Testing progress or feedback
        4. Encouragement for continued testing
        5. Note that bug reports are automatically synced to Google Sheets
        
        IMPORTANT FORMATTING RULES:
        - Always refer to users by their display names/usernames, NEVER by user IDs or numbers
        - When mentioning what someone said, include a clickable link to their message using this format:
          "[Username said xyz](message_link)" or "Username mentioned [this issue](message_link)"
        - Be creative with link text: "[see what they said](link)", "[check it out](link)", "[view discussion](link)"
        - Make links intuitive and natural, like: "Linda reported [a login issue](link)" or "Mike shared [great feedback](link)"
        - Use the message links provided in the context data (format: https://discord.com/channels/guild/channel/message)
        
        Example good formats:
        - "Sarah mentioned [an interesting bug](https://discord.com/channels/123/456/789) with the new feature"
        - "Check out [Tom's feedback](https://discord.com/channels/123/456/790) on the latest update"
        - "Linda said [the app crashed](https://discord.com/channels/123/456/791) during testing"
        
        Keep it factual, actionable, and make the links feel natural and helpful for beta testers."""
            
            ai_summary = await self.get_ai_response(ai_prompt, context)
            
            embed = discord.Embed(
                title=f"⏰ {period_name} Beta Testing Update", 
                description=f"{greeting}\n\n{ai_summary}",
                color=0x0099ff,
                timestamp=datetime.now()
            )
            
            # Add activity fields
            if new_bugs > 0:
                embed.add_field(name="🐛 New Bugs", value=str(new_bugs), inline=True)
            if potential_bugs > 0:
                embed.add_field(name="👀 Potential Issues Detected", value=str(potential_bugs), inline=True)
            
            # Add Google Sheets integration status
            embed.add_field(name="📊 Sheets Integration", value=sheets_status, inline=True)
            
            if total_new_bugs > 0:
                embed.add_field(name="📋 Synced to Spreadsheet", value=f"{total_new_bugs} bug entries", inline=True)
            
            embed.set_footer(text="Jim the Mentor • Store Analysis • Google Sheets Integration")
            
            # Send to all beta channels
            for guild in self.guilds:
                for channel_id in self.beta_channels:
                    try:
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            await channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error sending {period_name.lower()} update to {channel_id}: {e}")
        else:
            print(f"⏰ {period_name} check: No significant activity, skipping update (Sheets: {sheets_status})")
    
    async def get_recent_activity_context(self, hours_back: int) -> str:
        """Get context of recent activity for AI analysis with message links"""
        time_ago = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        with sqlite3.connect('beta_testing.db') as conn:
            cursor = conn.cursor()
            
            # Get recent messages with message IDs and channel IDs for linking
            cursor.execute('''
                SELECT message_content, username, message_id, channel_id, guild_id
                FROM messages 
                WHERE timestamp > ? AND message_content NOT LIKE '!%'
                ORDER BY timestamp DESC 
                LIMIT 15
            ''', (time_ago,))
            recent_messages = cursor.fetchall()
            
            # Get recent bugs
            cursor.execute('''
                SELECT bug_description, username, status, timestamp, channel_id
                FROM bugs 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (time_ago,))
            recent_bugs = cursor.fetchall()
        
        context = f"{hours_back} hour(s) of activity:\n\n"
        
        if recent_bugs:
            context += "Bug Reports:\n"
            for bug, user, status, timestamp, channel_id in recent_bugs:
                context += f"- {bug} (by {user}, {status})\n"
            context += "\n"
        
        if recent_messages:
            context += "Recent Messages (with source links):\n"
            for msg, user, msg_id, channel_id, guild_id in recent_messages:
                if len(msg) > 80:
                    msg = msg[:80] + "..."
                # Create Discord message link
                message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                context += f"- {user}: {msg} [LINK: {message_link}]\n"
        
        return context
    
    async def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.beta_channels = config.get('beta_channels', [])
                self.beta_tester_role_name = config.get('beta_tester_role_name', 'beta tester')
                self.beta_staff_role_name = config.get('staff_role_name', 'staff')
        except FileNotFoundError:
            print("⚠️ config.json not found. Using default settings.")
            self.beta_channels = []
    
    async def send_startup_notification(self):
        """Send startup notification to all beta channels"""
        if not self.beta_channels:
            print("⚠️ No beta channels configured for startup notifications")
            return
            
        embed = discord.Embed(
            title="🤖 Jim is Online!",
            description="Beta Testing Assistant is ready to help with bug reports and testing coordination.",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🏛️ Ambassador Program",
            value="Ready to process submissions and track ambassador activities",
            inline=False
        )
        
        embed.add_field(
            name="📊 Features Active",
            value="• Bug report analysis\n• Store monitoring\n• Ambassador tracking\n• Natural conversation support",
            inline=False
        )
        
        embed.set_footer(text="Jim the Mentor • Ready for Beta Testing")
        
        notifications_sent = 0
        for guild in self.guilds:
            for channel_id in self.beta_channels:
                try:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        await channel.send(embed=embed)
                        notifications_sent += 1
                        print(f"✅ Startup notification sent to #{channel.name} in {guild.name}")
                except Exception as e:
                    print(f"❌ Failed to send startup notification to channel {channel_id}: {e}")
        
        print(f"📢 Startup notifications sent to {notifications_sent} beta channels")
    
    # Removed duplicate on_message handler - consolidated into main handler below
    
    async def track_message(self, message):
        """Track message in database with optimized async processing"""
        try:
            # Skip tracking for bot messages or DMs
            if message.author.bot or not message.guild:
                return
                
            # Skip if in scanning mode to avoid conflicts
            if hasattr(self, 'scanning_mode') and self.scanning_mode:
                return
            
            # Quick database operation with minimal lock time
            message_data = await self._prepare_message_data(message)
            success = await self._insert_message_fast(message_data)
            
            if success:
                # Auto bug detection disabled - only record bugs via !bug command
                # asyncio.create_task(self._async_bug_detection(message))
                pass
                    
        except Exception as e:
            print(f"Error tracking message: {e}")
    
    async def _prepare_message_data(self, message):
        """Prepare message data without database operations"""
        # Determine if this is a staff message
        is_staff_message = any(role.name in ['Staff', 'Admin', 'Moderator', 'Developer'] for role in message.author.roles)
        
        # Check for attachments
        has_attachments = len(message.attachments) > 0
        attachment_urls = ', '.join([att.url for att in message.attachments]) if has_attachments else None
        
        # Get screenshot info if available
        screenshot_info = None
        if has_attachments:
            for attachment in message.attachments:
                if attachment.filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                    screenshot_info = f"{attachment.filename} ({attachment.size} bytes)"
                    break
        
        return {
            'message_id': str(message.id),
            'user_id': str(message.author.id),
            'username': message.author.display_name,
            'message_content': message.content,
            'timestamp': message.created_at.isoformat(),
            'channel_id': str(message.channel.id),
            'channel_name': message.channel.name,
            'has_attachments': has_attachments,
            'attachment_urls': attachment_urls,
            'is_staff_message': is_staff_message,
            'screenshot_info': screenshot_info,
            'guild_id': str(message.guild.id) if message.guild else None
        }
    
    async def _insert_message_fast(self, message_data):
        """Fast message insertion with minimal lock time"""
        try:
            # Use shorter timeout and immediate commit
            with sqlite3.connect('beta_testing.db', timeout=5.0) as conn:
                cursor = conn.cursor()
                
                # Quick duplicate check
                cursor.execute('SELECT 1 FROM messages WHERE message_id = ? LIMIT 1', (message_data['message_id'],))
                if cursor.fetchone():
                    return False  # Already exists
                
                # Fast insert
                cursor.execute('''
                    INSERT INTO messages (
                        message_id, user_id, username, message_content, 
                        timestamp, channel_id, channel_name, has_attachments, 
                        attachment_urls, is_staff_message, screenshot_info, guild_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_data['message_id'], message_data['user_id'], message_data['username'],
                    message_data['message_content'], message_data['timestamp'], message_data['channel_id'],
                    message_data['channel_name'], message_data['has_attachments'], message_data['attachment_urls'],
                    message_data['is_staff_message'], message_data['screenshot_info'], message_data['guild_id']
                ))
                
                conn.commit()
                return True
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print(f"Database locked, skipping message {message_data['message_id']}")
                return False
            else:
                print(f"Database error: {e}")
                return False
    
    async def _async_bug_detection(self, message):
        """Asynchronous bug detection to prevent blocking main thread"""
        try:
            # Add small delay to prevent overwhelming the system
            await asyncio.sleep(0.1)
            
            # Only process if not in scanning mode
            if not hasattr(self, 'scanning_mode') or not self.scanning_mode:
                await self.auto_detect_bugs(message)
                
        except Exception as e:
            print(f"Error in async bug detection: {e}")
    
    async def auto_detect_bugs(self, message):
        """Automatically detect potential bug reports in messages
        
        NOTE: This function is currently DISABLED to reduce noise in the bug sheet.
        Only bugs reported via !bug command will be recorded.
        """
        try:
            bug_keywords = [
                'crash', 'bug', 'error', 'broken', 'not working', 'issue', 'problem',
                'glitch', 'freeze', 'stuck', 'fail', 'wrong', 'weird', 'strange'
            ]
            
            message_lower = message.content.lower()
            
            # Check if message contains bug keywords and is substantial
            if (any(keyword in message_lower for keyword in bug_keywords) and 
                len(message.content) > 20 and 
                not message.content.startswith('!')):
                
                # Use AI to determine if this is actually a bug report
                ai_prompt = f"""Is this message describing a bug or technical issue that should be tracked?
                
                Message: "{message.content}"
                
                Respond with only "YES" if it's a bug report, or "NO" if it's not."""
                
                ai_response = await self.get_ai_response(ai_prompt)
                
                if ai_response and "YES" in ai_response.upper():
                    # Auto-log as potential bug with retry logic for database locks
                    max_retries = 2  # Reduce retries to prevent long waits
                    for attempt in range(max_retries):
                        try:
                            # Use much shorter timeout for bug detection
                            with sqlite3.connect('beta_testing.db', timeout=3.0) as conn:
                                cursor = conn.cursor()
                                
                                cursor.execute('''
                                    INSERT INTO bugs (user_id, username, bug_description, timestamp, status, staff_notified, channel_id, added_by)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    str(message.author.id),
                                    message.author.display_name,
                                    f"[AUTO-DETECTED] {message.content}",
                                    datetime.now().isoformat(),
                                    'potential',
                                    False,
                                    str(message.channel.id),
                                    message.author.display_name
                                ))
                                
                                bug_id = cursor.lastrowid
                                conn.commit()
                                
                                # Add to Google Sheets if enabled
                                if self.sheets_manager:
                                    try:
                                        bug_data = {
                                            'bug_id': bug_id,
                                            'username': message.author.display_name,
                                            'description': f"[AUTO-DETECTED] {message.content}",
                                            'timestamp': datetime.now().isoformat(),
                                            'status': 'potential',
                                            'channel_id': str(message.channel.id),
                                            'guild_id': str(message.guild.id) if message.guild else '',
                                            'added_by': message.author.display_name
                                        }
                                        await self.sheets_manager.add_bug_to_sheet(bug_data)
                                    except Exception as e:
                                        print(f"⚠️ Failed to add bug to spreadsheet: {e}")
                                
                                # React to the message to show it was detected
                                try:
                                    await message.add_reaction('🐛')
                                    await message.add_reaction('👀')
                                except:
                                    pass
                                break  # Success, exit retry loop
                                
                        except sqlite3.OperationalError as e:
                            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                                print(f"Database locked, retry {attempt + 1}/{max_retries} in 1 second...")
                                await asyncio.sleep(1)
                                continue
                            else:
                                raise  # Re-raise if not a lock error or max retries reached
        except Exception as e:
            print(f"Error in auto_detect_bugs: {e}")
    
    async def get_ai_response(self, prompt: str, context: str = "") -> str:
        """Get response from Gemini AI"""
        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            
            # Generate response with retry logic
            for attempt in range(3):
                try:
                    response = self.model.generate_content(full_prompt)
                    if response and response.text:
                        return response.text
                    else:
                        print(f"Empty AI response on attempt {attempt + 1}")
                except Exception as e:
                    print(f"AI attempt {attempt + 1} failed: {e}")
                    if attempt < 2:  # Don't wait on last attempt
                        await asyncio.sleep(1)
                        
            return "AI service temporarily unavailable. Please try again later."
            
        except Exception as e:
            print(f"AI Error: {e}")
            return "AI service error. Please try again later."
    
    def has_beta_tester_role(self, member) -> bool:
        """Check if user has beta tester role"""
        # If it's a DM or user doesn't have roles, allow access
        if not hasattr(member, 'roles') or not member.roles:
            return True
            
        return any(role.name.lower() == self.beta_tester_role_name.lower() for role in member.roles)
    
    def get_staff_role(self, guild):
        """Get staff role from guild"""
        return discord.utils.get(guild.roles, name=self.beta_staff_role_name)

    async def scan_recent_history_silent(self, days_back: int = 7):
        """Silently scan recent messages without channel announcements"""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        self.scanning_mode = True
        
        for guild in self.guilds:
            for channel_id in self.beta_channels:
                try:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        print(f"Silently scanning #{channel.name} for messages from last {days_back} days...")
                        
                        message_count = 0
                        async for message in channel.history(limit=1000, after=cutoff_date):
                            if not message.author.bot:
                                await self.track_message(message)
                                message_count += 1
                        
                        print(f"Catalogued {message_count} messages from #{channel.name}")
                        
                except Exception as e:
                    print(f"Error scanning channel {channel_id}: {e}")
        
        print("📚 Silent history scan complete!")
        
        self.scanning_mode = False

    async def search_chat_history(self, query: str, channel_id: str = None, days_back: int = 30) -> List[Dict]:
        """Search chat history for specific terms"""
        with sqlite3.connect('beta_testing.db') as conn:
            cursor = conn.cursor()
            
            # Build search query - include user_id for filtering
            sql = '''
                SELECT username, message_content, timestamp, channel_name, user_id 
                FROM messages 
                WHERE message_content LIKE ? 
            '''
            params = [f'%{query}%']
            
            if channel_id:
                sql += ' AND channel_id = ?'
                params.append(channel_id)
            
            # Add date filter
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            sql += ' AND timestamp > ? ORDER BY timestamp DESC LIMIT 50'  # Get more results for better filtering
            params.append(cutoff_date)
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
        
        return [
            {
                'username': row[0],
                'content': row[1],
                'timestamp': row[2],
                'channel': row[3],
                'user_id': row[4]
            }
            for row in results
        ]

    async def handle_reselling_dm(self, message):
        """Handle natural conversation about reselling in DMs"""
        try:
            # Check if message is about reselling
            reselling_keywords = [
                'resell', 'selling', 'poshmark', 'mercari', 'ebay', 'depop', 'facebook marketplace',
                'thrift', 'flip', 'profit', 'price', 'pricing', 'bundle', 'inventory', 'listing',
                'buyer', 'seller', 'vintage', 'brand', 'authenticate', 'condition', 'photos',
                'shipping', 'returns', 'closet', 'store', 'sales', 'income', 'business',
                'sourcing', 'goodwill', 'garage sale', 'estate sale', 'wholesale', 'retail arbitrage'
            ]
            
            message_lower = message.content.lower()
            
            # Check if message contains reselling keywords or is a follow-up to recent reselling conversation
            is_reselling_related = any(keyword in message_lower for keyword in reselling_keywords)
            
            # Also check if this is a follow-up to recent mentorship activity
            user_id = str(message.author.id)
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM mentorship_sessions 
                    WHERE user_id = ? AND timestamp > datetime('now', '-1 hour')
                ''', (user_id,))
                recent_mentorship = cursor.fetchone()[0] > 0
            
            if is_reselling_related or recent_mentorship:
                # Show typing indicator
                async with message.channel.typing():
                    # Determine if we need to research
                    needs_research = any(word in message_lower for word in [
                        'how to', 'what is', 'explain', 'why', 'when', 'where', 'best way',
                        'should i', 'can i', 'is it', 'do i', 'help me'
                    ])
                    
                    if needs_research:
                        # Show thinking message
                        thinking_msg = await message.channel.send("🤔 *Jim is thinking...*")
                        
                        # Research the topic
                        research_context = await self.research_reselling_topic(message.content)
                        context = f"DM conversation. Research context: {research_context}"
                        
                        # Delete thinking message
                        await thinking_msg.delete()
                    else:
                        context = "DM conversation"
                    
                    # Generate response
                    response = await self.mentorship_services.generate_personalized_advice(
                        user_id, message.content, context
                    )
                    
                    # Send response
                    await message.channel.send(response)
                    
                    # Log the session
                    await self.mentorship_services.log_mentorship_session(
                        user_id, "dm_conversation", message.content, response, "general_advice"
                    )
        except Exception as e:
            print(f"Error in handle_reselling_dm: {e}")
            await message.channel.send("Sorry, I had trouble processing that. Try using `!ask` followed by your question!")
    
    async def get_ai_analysis(self, prompt: str) -> str:
        """Get AI analysis using available AI clients"""
        try:
            print(f"🔧 AI Analysis Debug:")
            print(f"   Claude client available: {claude_client is not None}")
            print(f"   OpenAI client available: {openai_client is not None}")
            
            # Try Claude first if available
            if claude_client:
                print(f"   Trying Claude...")
                try:
                    response = await claude_client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=100,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text.strip()
                except Exception as e:
                    print(f"Claude AI error: {e}")
            
            # Try OpenAI if Claude fails or unavailable
            if openai_client:
                try:
                    response = await openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        max_tokens=100,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    print(f"OpenAI error: {e}")
            
            print("No AI clients available for bug area detection")
            return None
            
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return None
    
    async def detect_bug_area(self, bug_description: str) -> str:
        """Detect which app area the bug belongs to using AI analysis"""
        try:
            print(f"🔍 Starting bug area detection for: {bug_description[:100]}...")
            
            # Define the available areas from the data validation list
            areas = [
                "SmartFill", "Stock Photo", "Crosslisting", "Auction Tools", 
                "Bulk Actions", "Analytics", "Settings", "Authentication",
                "UI/UX", "Performance", "Integration", "Discord Bot", "Other"
            ]
            
            ai_prompt = f"""Analyze this bug report and determine which app area it belongs to.
            
Bug Description: "{bug_description}"

Available Areas:
- SmartFill: Auto-filling product details, descriptions, titles
- Stock Photo: Photo editing, filters, backgrounds, image processing
- Crosslisting: Listing items across multiple platforms (Poshmark, Depop, etc.)
- Auction Tools: Bidding, sniping, auction management
- Bulk Actions: Mass operations, batch processing
- Analytics: Reports, statistics, performance tracking
- Settings: App configuration, preferences, account settings
- Authentication: Login, signup, account access issues
- UI/UX: Interface problems, navigation, layout issues
- Performance: Speed, crashes, freezing, loading issues
- Integration: API connections, third-party services
- Discord Bot: Issues with this Discord bot itself
- Other: Anything that doesn't fit the above categories

Respond with ONLY the area name from the list above that best matches the bug description."""
            
            print(f"🤖 Sending AI prompt for area detection...")
            ai_response = await self.get_ai_analysis(ai_prompt)
            print(f"🤖 AI Response: '{ai_response}'")
            
            # Clean and validate the response
            if ai_response:
                detected_area = ai_response.strip()
                print(f"🧹 Cleaned response: '{detected_area}'")
                
                # Check if the detected area is in our valid list
                for area in areas:
                    if area.lower() in detected_area.lower():
                        print(f"✅ Matched area: {area}")
                        return area
                
                print(f"❌ No match found for '{detected_area}', defaulting to 'Other'")
            else:
                print(f"❌ No AI response received, defaulting to 'Other'")
            
            # Default fallback
            return "Other"
            
        except Exception as e:
            print(f"❌ Error detecting bug area: {e}")
            return "Other"

# === SCREENSHOT ANALYSIS FUNCTION ===
async def analyze_screenshot_with_ai(screenshot_url: str, bug_description: str) -> str:
    """Analyze a screenshot using AI and provide insights for bug reports"""
    try:
        # Use Claude AI for screenshot analysis if available
        if claude_client:
            prompt = f"""
Analyze this screenshot in the context of a bug report. The user described the issue as: "{bug_description}"

Please provide a concise analysis (2-3 sentences) covering:
1. What you can see in the screenshot
2. Any visible errors, issues, or anomalies
3. How it relates to the reported bug

Keep it technical but accessible.
"""
            
            try:
                response = await claude_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=200,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "url",
                                        "url": screenshot_url
                                    }
                                }
                            ]
                        }
                    ]
                )
                return response.content[0].text.strip()
            except Exception as claude_error:
                print(f"Claude analysis failed: {claude_error}")
        
        # Fallback to OpenAI if Claude fails or isn't available
        if openai_client:
            try:
                response = await openai_client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Analyze this screenshot for a bug report. User says: '{bug_description}'. Provide a brief technical analysis (2-3 sentences)."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": screenshot_url
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=200
                )
                return response.choices[0].message.content.strip()
            except Exception as openai_error:
                print(f"OpenAI analysis failed: {openai_error}")
        
        # If both AI services fail, return a basic analysis
        return f"Screenshot attached showing the issue described: '{bug_description}'. Manual review recommended."
        
    except Exception as e:
        print(f"Screenshot analysis error: {e}")
        return "Screenshot analysis failed, but image has been preserved for manual review."

# === CREATE BOT INSTANCE ===
bot = BetaTestingBot()

# Bug reporting command
@bot.command(name='bug')
async def report_bug(ctx, *, description=None):
    """Report a bug and notify staff (supports screenshots)"""
    if not description:
        embed = discord.Embed(
            title="🐛 Bug Report Command",
            description="Please provide a description of the bug you want to report.",
            color=0xff6b6b
        )
        embed.add_field(
            name="Usage", 
            value="`!bug Your bug description here`", 
            inline=False
        )
        embed.add_field(
            name="With Screenshot", 
            value="Attach a screenshot to your message for better analysis!", 
            inline=False
        )
        embed.add_field(
            name="Example", 
            value="`!bug The app crashes when I try to save a file`", 
            inline=False
        )
        embed.set_footer(text="📸 Screenshots are automatically analyzed by AI!")
        await ctx.send(embed=embed)
        return
    
    try:
        # Check for screenshot attachments
        screenshot_urls = []
        screenshot_analysis = ""
        
        if ctx.message.attachments:
            print(f"📸 Found {len(ctx.message.attachments)} attachments")
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    screenshot_urls.append(attachment.url)
                    print(f"📸 Screenshot detected: {attachment.filename} ({attachment.size} bytes)")
        
        # Generate AI analysis of screenshots if present
        if screenshot_urls:
            try:
                print(f"🤖 Analyzing {len(screenshot_urls)} screenshot(s) with AI...")
                screenshot_analysis = await analyze_screenshot_with_ai(screenshot_urls[0], description)
                print(f"✅ Screenshot analysis complete: {screenshot_analysis[:100]}...")
            except Exception as e:
                print(f"❌ Screenshot analysis failed: {e}")
                screenshot_analysis = "Screenshot analysis unavailable"
        
        # Combine description with screenshot analysis
        full_description = description
        if screenshot_analysis:
            full_description += f"\n\n🤖 AI Screenshot Analysis: {screenshot_analysis}"
        
        # Store bug in database with retry logic
        bug_id = None
        for attempt in range(3):
            try:
                with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO bugs (user_id, username, bug_description, timestamp, status, staff_notified, channel_id, added_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(ctx.author.id),
                        ctx.author.display_name,
                        full_description,
                        datetime.now().isoformat(),
                        'open',
                        True,
                        str(ctx.channel.id),
                        ctx.author.display_name
                    ))
                    
                    bug_id = cursor.lastrowid
                    conn.commit()
                    break
                    
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    print(f"Database locked, retrying in 1 second... (attempt {attempt + 1})")
                    await asyncio.sleep(1)
                    continue
                else:
                    print(f"Database error: {e}")
                    await ctx.send("❌ Failed to save bug report to database. Please try again.")
                    return
        
        if bug_id is None:
            await ctx.send("❌ Failed to save bug report. Please try again.")
            return
        
        # Add to Google Sheets if enabled
        sheets_success = False
        if bot.sheets_manager:
            try:
                print(f"🔄 Attempting to add bug #{bug_id} to Google Sheets...")
                
                # Detect the app area using AI analysis
                try:
                    print(f"🔍 Starting AI detection for manual !bug command: {description[:50]}...")
                    detected_area = await bot.detect_bug_area(description)
                    print(f"🎯 Detected area for !bug command: {detected_area}")
                except Exception as e:
                    print(f"❌ AI detection failed for !bug command: {e}")
                    detected_area = "Other"
                
                # Prepare screenshot info for Google Sheets
                screenshot_info = ""
                if screenshot_urls:
                    screenshot_info = f"Screenshots: {', '.join(screenshot_urls)}"
                    if screenshot_analysis:
                        screenshot_info += f" | Analysis: {screenshot_analysis}"
                
                bug_data = {
                    'bug_id': bug_id,
                    'username': ctx.author.display_name,
                    'description': description,
                    'area': detected_area,  # Add the detected area
                    'timestamp': datetime.now().isoformat(),
                    'status': 'open',
                    'channel_id': str(ctx.channel.id),
                    'guild_id': str(ctx.guild.id) if ctx.guild else '',
                    'added_by': ctx.author.display_name,
                    'screenshots': screenshot_info  # Add screenshot info
                }
                print(f"📊 Bug data prepared: {bug_data}")
                
                # Properly await the Google Sheets call
                sheets_result = await bot.sheets_manager.add_bug_to_sheet(bug_data)
                if sheets_result:
                    print(f"✅ Successfully added bug #{bug_id} to Google Sheets")
                    sheets_success = True
                else:
                    print(f"❌ Failed to add bug #{bug_id} to Google Sheets - API returned False")
                    sheets_success = False
                        
            except Exception as e:
                print(f"⚠️ Exception while adding bug to spreadsheet: {e}")
                import traceback
                traceback.print_exc()
                sheets_success = False
        else:
            print("⚠️ Google Sheets manager not initialized")
        
        # Send success message with Google Sheet link
        embed = discord.Embed(
            title="✅ Bug Report Submitted!",
            description=f"Your bug report has been logged as **Bug #{bug_id}**",
            color=0x00ff00
        )
        embed.add_field(
            name="🐛 Description",
            value=description[:1000] + ("..." if len(description) > 1000 else ""),
            inline=False
        )
        
        # Add screenshot info if present
        if screenshot_urls:
            embed.add_field(
                name="📸 Screenshots",
                value=f"{len(screenshot_urls)} screenshot(s) attached and analyzed",
                inline=True
            )
            if screenshot_analysis:
                embed.add_field(
                    name="🤖 AI Analysis",
                    value=screenshot_analysis[:200] + ("..." if len(screenshot_analysis) > 200 else ""),
                    inline=False
                )
        
        embed.add_field(
            name="👤 Reported by",
            value=f"{ctx.author.display_name} (Added by {ctx.author.display_name})",
            inline=True
        )
        embed.add_field(
            name="📊 Status",
            value="Open for review",
            inline=True
        )
        
        if sheets_success:
            embed.add_field(
                name="📈 Track Progress",
                value="[View in Google Sheets](https://docs.google.com/spreadsheets/d/1lTOj3r-LVMnp-oVu7dDnGWjBzKxWeZJJGZSxUMaMwB4/edit)",
                inline=False
            )
            embed.set_footer(text="Your bug has been added to our shared tracking sheet for transparency!")
        else:
            embed.set_footer(text="Bug saved locally. Google Sheets sync pending.")
        
        await ctx.send(embed=embed)
        
        # Add reaction to show it was processed
        try:
            await ctx.message.add_reaction('✅')
            await ctx.message.add_reaction('🐛')
        except:
            pass
            
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Error Submitting Bug Report",
            description=f"Sorry, there was an error saving your bug report: {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=error_embed)

# What's new command
@bot.command(name='whatsnew')
async def whats_new(ctx):
    """Send latest updates to beta testers via DM (channel-specific)"""
    if not ctx.bot.has_beta_tester_role(ctx.author):
        await ctx.send("❌ This command is only available to beta testers.")
        return
    
    # Get the current channel name for context
    channel_name = ctx.channel.name if ctx.guild else "DM"
    channel_id = str(ctx.channel.id) if ctx.guild else None
    
    # Get manual updates
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Get new messages, bugs, and activity from last hour
        cursor.execute('''
            SELECT content, timestamp, created_by 
            FROM whats_new 
            ORDER BY timestamp DESC 
            LIMIT 3
        ''')
        manual_updates = cursor.fetchall()
        
        # Get recent bug reports for this channel or all channels if from DM
        if channel_id:
            cursor.execute('''
                SELECT bug_description, username, status, timestamp, channel_id
                FROM bugs 
                WHERE timestamp > ? 
                AND channel_id = ?
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', ((datetime.now() - timedelta(days=7)).isoformat(), channel_id))
        else:
            cursor.execute('''
                SELECT bug_description, username, status, timestamp, channel_id
                FROM bugs 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        recent_bugs = cursor.fetchall()
        
        # Get staff/developer guidance (prioritize their messages) from CURRENT CHANNEL
        if channel_id:
            cursor.execute('''
                SELECT DISTINCT message_content, username, message_id, guild_id
                FROM messages 
                WHERE timestamp > ? 
                AND channel_id = ?
                AND is_staff_message = TRUE
                AND LENGTH(message_content) > 20
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', ((datetime.now() - timedelta(days=7)).isoformat(), channel_id))
        else:
            # If from DM, get staff guidance from all channels
            cursor.execute('''
                SELECT DISTINCT message_content, username, message_id, guild_id
                FROM messages 
                WHERE timestamp > ? 
                AND is_staff_message = TRUE
                AND LENGTH(message_content) > 20
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        staff_guidance = cursor.fetchall()
        
        # Get recent chat activity for context - filter for testing-related content from CURRENT CHANNEL
        if channel_id:
            cursor.execute('''
                SELECT DISTINCT message_content, username, timestamp, channel_name, screenshot_info, message_id, guild_id
                FROM messages 
                WHERE timestamp > ? 
                AND channel_id = ?
                AND message_content NOT LIKE '!%'
                AND message_content NOT LIKE '%jim%'
                AND message_content NOT LIKE '%bot%'
                AND message_content NOT LIKE '%Mike%'
                AND message_content NOT LIKE '%Darktiding%'
                AND message_content NOT LIKE '%need fixing%'
                AND message_content NOT LIKE '%fixing him%'
                AND (
                    message_content LIKE '%error%' OR
                    message_content LIKE '%issue%' OR
                    message_content LIKE '%problem%' OR
                    message_content LIKE '%broken%' OR
                    message_content LIKE '%not working%' OR
                    message_content LIKE '%bug%' OR
                    message_content LIKE '%crash%' OR
                    message_content LIKE '%feature%' OR
                    message_content LIKE '%tool%' OR
                    message_content LIKE '%automation%' OR
                    message_content LIKE '%sidekick%' OR
                    message_content LIKE '%crosslist%' OR
                    message_content LIKE '%depop%' OR
                    message_content LIKE '%ebay%' OR
                    message_content LIKE '%mercari%' OR
                    message_content LIKE '%poshmark%' OR
                    message_content LIKE '%facebook%' OR
                    message_content LIKE '%marketplace%' OR
                    message_content LIKE '%auction%'
                )
                ORDER BY timestamp DESC 
                LIMIT 50
            ''', ((datetime.now() - timedelta(days=7)).isoformat(), channel_id))
        else:
            # If from DM, get from all channels
            cursor.execute('''
                SELECT DISTINCT message_content, username, timestamp, channel_name, screenshot_info, message_id, guild_id
                FROM messages 
                WHERE timestamp > ? 
                AND message_content NOT LIKE '!%'
                AND message_content NOT LIKE '%jim%'
                AND message_content NOT LIKE '%bot%'
                AND (
                    message_content LIKE '%error%' OR
                    message_content LIKE '%issue%' OR
                    message_content LIKE '%problem%' OR
                    message_content LIKE '%broken%' OR
                    message_content LIKE '%not working%' OR
                    message_content LIKE '%bug%' OR
                    message_content LIKE '%crash%' OR
                    message_content LIKE '%feature%' OR
                    message_content LIKE '%tool%' OR
                    message_content LIKE '%automation%' OR
                    message_content LIKE '%sidekick%'
                )
                ORDER BY timestamp DESC 
                LIMIT 50
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        recent_messages = cursor.fetchall()
        
        # Get message statistics for testing-related content only from CURRENT CHANNEL
        if channel_id:
            cursor.execute('''
                SELECT COUNT(DISTINCT message_id) as total_messages,
                       COUNT(DISTINCT username) as active_users
                FROM messages 
                WHERE timestamp > ?
                AND channel_id = ?
                AND message_content NOT LIKE '%jim%'
                AND message_content NOT LIKE '%bot%'
                AND message_content NOT LIKE '%Mike%'
                AND message_content NOT LIKE '%Darktiding%'
                AND (
                    message_content LIKE '%depop%' OR
                    message_content LIKE '%auction%' OR
                    message_content LIKE '%sidekick%' OR
                    message_content LIKE '%tool%' OR
                    message_content LIKE '%feature%' OR
                    message_content LIKE '%bug%' OR
                    message_content LIKE '%issue%' OR
                    message_content LIKE '%error%' OR
                    message_content LIKE '%crosslist%' OR
                    message_content LIKE '%ebay%' OR
                    message_content LIKE '%mercari%' OR
                    message_content LIKE '%poshmark%' OR
                    message_content LIKE '%facebook%' OR
                    message_content LIKE '%marketplace%'
                )
            ''', ((datetime.now() - timedelta(days=7)).isoformat(), channel_id))
        else:
            # If from DM, get stats from all channels
            cursor.execute('''
                SELECT COUNT(DISTINCT message_id) as total_messages,
                       COUNT(DISTINCT username) as active_users
                FROM messages 
                WHERE timestamp > ?
                AND message_content NOT LIKE '%jim%'
                AND message_content NOT LIKE '%bot%'
                AND (
                    message_content LIKE '%sidekick%' OR
                    message_content LIKE '%tool%' OR
                    message_content LIKE '%feature%' OR
                    message_content LIKE '%bug%' OR
                    message_content LIKE '%issue%' OR
                    message_content LIKE '%error%'
                )
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        stats = cursor.fetchone()
    
    # Create AI summary of recent activity
    context = f"{channel_name} Beta Testing Activity (Last 7 Days):\n\n"
    
    if recent_bugs:
        context += "Bug Reports:\n"
        for bug, user, status, timestamp, channel_id in recent_bugs:
            context += f"- {bug} (by {user}, {status})\n"
        context += "\n"
    
    if staff_guidance:
        context += "Staff Guidance (with source links):\n"
        for msg, user, msg_id, guild_id in staff_guidance:
            if len(msg) > 100:
                msg = msg[:100] + "..."
            # Create Discord message link if we have the required IDs
            if msg_id and guild_id and channel_id:
                message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                context += f"- {user}: {msg} [LINK: {message_link}]\n"
            else:
                context += f"- {user}: {msg}\n"
        context += "\n"
    
    if recent_messages:
        context += "Recent Messages (with source links):\n"
        for msg, user, timestamp, channel, screenshot_info, msg_id, guild_id in recent_messages:
            if len(msg) > 80:
                msg = msg[:80] + "..."
            # Create Discord message link if we have the required IDs
            if msg_id and guild_id and channel_id:
                message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                context += f"- {user}: {msg} [LINK: {message_link}]\n"
            else:
                context += f"- {user}: {msg}\n"
            if screenshot_info:
                context += f"  - Screenshot: {screenshot_info}\n"
        context += "\n"
    
    if stats:
        context += f"📊 Testing Activity Stats:\n"
        context += f"- Testing-related messages: {stats[0]}\n"
        context += f"- Active beta testers: {stats[1]}\n\n"
    
    # Get AI summary
    ai_prompt = """Analyze the Sidekick Tools beta testing data above and create a summary.

    CRITICAL REQUIREMENT: You MUST include clickable Discord links whenever you mention what users said or reported. This is mandatory.

    ONLY use the information provided in these sections:
    - Bug Tracking Summary (statistics)
    - Recent Bug Reports (if any)
    - Staff Guidance (with source links)
    - Recent Messages (with source links)

    Create a brief summary with:
    1. **Bug Status This Week**: Use the exact numbers from Bug Tracking Summary
    2. **Staff Guidance**: Highlight what staff/developers want testers to focus on
    3. **Key Issues**: List the actual issues from "Recent Messages" section - YOU MUST INCLUDE LINKS HERE
    4. **Testing Priority**: What features need testing based on staff guidance and recent discussions
    5. **Action Items**: What testers should focus on this week

    MANDATORY LINK FORMATTING:
    - Every time you mention a user message, you MUST include the [LINK: ...] as a clickable link
    - Format: "A user reported [an activation issue](https://discord.com/channels/...)"
    - Format: "Someone mentioned [this problem](https://discord.com/channels/...)"
    - Format: "Testers discussed [feature concerns](https://discord.com/channels/...)"
    - Be creative: "[see the full report](link)", "[check the details](link)", "[view the discussion](link)"
    - NEVER mention a user message without including its source link
    - If a message has [LINK: url] in the context, you MUST use that URL in your response

    EXAMPLE OF CORRECT FORMAT:
    "A user reported [an issue with Poshmark item activation](https://discord.com/channels/906704950908821504/1002197177562574909/1388209745730474105) where cancelled items show incorrect status when reactivated."

    DO NOT:
    - Mention any user names except staff (Jin, treblig, JM, Hailin)
    - Treat people as features or bugs
    - Make up information not provided
    - Reference conversations about users
    - Expose raw user IDs; use display names/usernames only
    - Ever mention a user message without including its clickable source link

    Keep it factual and actionable for beta testers. REMEMBER: Links are mandatory for all user message references."""
    
    ai_summary = await ctx.bot.get_ai_response(ai_prompt, context)
    
    # Create comprehensive embed
    embed = discord.Embed(
        title=f"📋 {channel_name} Beta Testing Summary",
        description=f"Latest updates from **#{channel_name}** channel (last 7 days)",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    # Add manual updates if any
    if manual_updates:
        manual_content = ""
        for content, timestamp, created_by in manual_updates:
            manual_content += f"• {content}\n*Added by {created_by} on {timestamp[:10]}*\n\n"
        embed.add_field(name="📢 Official Updates", value=manual_content[:1024], inline=False)
    
    # Add AI summary
    if ai_summary:
        embed.add_field(name="🤖 Recent Activity Summary", value=ai_summary[:1024], inline=False)
    
    # Add recent bug count
    if recent_bugs:
        open_bugs = len([b for b in recent_bugs if b[2] == 'open'])
        fixed_bugs = len([b for b in recent_bugs if b[2] == 'fixed'])
        potential_bugs = len([b for b in recent_bugs if b[2] == 'potential'])
        embed.add_field(
            name="🐛 Bug Status (Last 7 Days)",
            value=f"🔴 {open_bugs} open bugs\n✅ {fixed_bugs} fixed bugs\n👀 {potential_bugs} potential issues",
            inline=True
        )
    
    # Add testing focus
    embed.add_field(
        name="🎯 Testing Focus",
        value="Use `!help-test <question>` for specific guidance\nUse `!bug <description>` to report issues",
        inline=True
    )
    
    try:
        # Always send via DM to keep channel clean
        await ctx.author.send(embed=embed)
        await ctx.send(f"✅ I've sent you the latest updates from **#{channel_name}** via DM!")
    except discord.Forbidden:
        await ctx.send("❌ I couldn't send you a DM. Please check your privacy settings and try again.")
        
    # If command was used in a channel, confirm it was sent to DM
    if ctx.guild:
        await ctx.send(f"✅ {ctx.author.mention}, I've sent the latest updates from **#{channel_name}** to your DMs!")

# Testing status command
@bot.command(name='status')
async def testing_status(ctx):
    """Get current testing status and progress"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Get testing progress
        cursor.execute('''
            SELECT feature_name, status, last_updated, notes 
            FROM testing_progress 
            ORDER BY last_updated DESC
        ''')
        
        progress = cursor.fetchall()
        
        # Get recent bugs
        cursor.execute('SELECT COUNT(*) FROM bugs WHERE status = "open"')
        open_bugs = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bugs WHERE status = "fixed"')
        fixed_bugs = cursor.fetchone()[0]
    
    embed = discord.Embed(
        title="📊 Beta Testing Status",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🐛 Open Bugs", value=str(open_bugs), inline=True)
    embed.add_field(name="✅ Fixed Bugs", value=str(fixed_bugs), inline=True)
    embed.add_field(name="📈 Features in Testing", value=str(len(progress)), inline=True)
    
    if progress:
        feature_status = "\n".join([f"• {name}: {status}" for name, status, _, _ in progress[:5]])
        embed.add_field(name="🔧 Current Features", value=feature_status, inline=False)
    
    await ctx.send(embed=embed)

# AI assistance command
@bot.command(name='help-test')
async def help_test(ctx, *, question: str = None):
    """Get testing guidance from Jim"""
    
    # Get recent staff guidance and current priorities
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Get recent staff messages for context
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT message_content, username 
            FROM messages 
            WHERE timestamp > ? 
            AND is_staff_message = TRUE
            AND LENGTH(message_content) > 20
            ORDER BY timestamp DESC 
            LIMIT 5
        ''', (week_ago,))
        staff_guidance = cursor.fetchall()
    
    guidance = "🧪 **Beta Testing Guidance**\n\n"
    
    if staff_guidance:
        guidance += "📝 **Recent Staff Direction:**\n"
        for msg, user in staff_guidance:
            guidance += f"• {user}: {msg[:100]}{'...' if len(msg) > 100 else ''}\n"
        guidance += "\n"
    
    guidance += "🎯 **General Testing Focus:**\n"
    guidance += "• **Depop Integration**: Test crosslisting, image handling, listing creation\n"
    guidance += "• **Auction Tools**: Test bidding, sniping, bulk operations\n"
    guidance += "• **Automation Features**: Test scheduled tasks, bulk actions\n"
    guidance += "• **UI/UX**: Report any interface issues, crashes, or confusing flows\n\n"
    
    guidance += "📸 **When Reporting Bugs:**\n"
    guidance += "• Include screenshots when possible\n"
    guidance += "• Use `!bug <description>` to report issues\n"
    guidance += "• Be specific about what you were doing when the issue occurred\n\n"
    
    if question:
        guidance += f"❓ **Your Question**: {question}\n\n"
        
        ai_context = f"Staff guidance: {staff_guidance}\n\nUser question: {question}"
        ai_prompt = f"""Based on the staff guidance and beta testing context, provide specific testing advice for this question: {question}
        
        Focus on:
        1. What specific features to test
        2. What to look for
        3. How to test effectively
        4. What to report
        
        Keep response concise and actionable. If there's minimal activity, just say 'Quiet hour - keep testing!'"""
        
        ai_response = await ctx.bot.get_ai_response(ai_prompt, ai_context)
        guidance += f"🤖 **Jim's Answer**: {ai_response}\n\n"
    
    guidance += "💡 **Need More Help?**\n"
    guidance += "• DM me with `!help-test <your question>`\n"
    guidance += "• Use `!whatsnew` for weekly testing updates\n"
    guidance += "• Use `!buginfo <id>` for detailed bug information"
    
    # Send via DM if possible, otherwise in channel
    try:
        await ctx.author.send(guidance)
        if ctx.guild:
            await ctx.send(f"✅ {ctx.author.mention}, I've sent testing guidance to your DMs!")
    except discord.Forbidden:
        await ctx.send(guidance)

# Search chat history command
@bot.command(name='search')
async def search_chat_history(ctx, query: str, channel_id: str = None, days_back: int = 30):
    """Search chat history for specific terms"""
    results = await bot.search_chat_history(query, channel_id, days_back)
    
    if results:
        embed = discord.Embed(title=f"Search Results for '{query}'", color=0x0099ff)
        for result in results[:5]:  # Limit to 5 results
            embed.add_field(
                name=f"{result['username']} in #{result['channel']}",
                value=result['content'][:100] + ("..." if len(result['content']) > 100 else ""),
                inline=False
            )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"No results found for '{query}'")

# Question answering command (search chat history for answers)
@bot.command(name='question')
async def ask_question(ctx, *, question: str = None):
    """Ask Jim a question and get answers from chat history"""
    if not question:
        await ctx.send("Please ask me a question! For example: `!question How do I use the stock photo feature?`")
        return
        
    try:
        # Show typing indicator while processing
        async with ctx.typing():
            print(f"🔍 Searching for answers to: {question}")
            
            # Search for relevant messages in ALL channels with longer timeframe
            print(f"🔍 Searching all channels for answers (up to 365 days back)...")
            
            # Extract key terms from the question for better searching
            key_terms = []
            question_lower = question.lower()
            
            # Remove common question words and extract meaningful terms
            stop_words = ['what', 'is', 'how', 'do', 'i', 'the', 'a', 'an', 'to', 'can', 'does', 'anyone', 'know']
            words = question_lower.replace('?', '').split()
            key_terms = [word for word in words if word not in stop_words and len(word) > 2]
            
            print(f"🔎 Key terms to search: {key_terms}")
            
            # Search for each key term to find relevant discussions
            all_results = []
            for term in key_terms[:3]:  # Use top 3 key terms to avoid too broad search
                term_results = await bot.search_chat_history(
                    query=term,
                    channel_id=None,  # Search all channels
                    days_back=365     # Search up to 1 year back
                )
                all_results.extend(term_results)
            
            # Also search the full question
            full_results = await bot.search_chat_history(
                query=question,
                channel_id=None,
                days_back=365
            )
            all_results.extend(full_results)
            
            # Remove duplicates and prioritize answers
            if all_results:
                seen_content = set()
                unique_results = []
                user_id = str(ctx.author.id)
                username = ctx.author.display_name
                
                print(f"🔍 Processing {len(all_results)} total results...")
                
                for result in all_results:
                    content = result['content']
                    content_key = content.lower().strip()
                    
                    # Skip duplicates
                    if content_key in seen_content:
                        continue
                    seen_content.add(content_key)
                    
                    result_user_id = result.get('user_id', '')
                    result_username = result.get('username', '')
                    
                    # Skip the user's own messages
                    if result_user_id == user_id or result_username == username:
                        continue
                    
                    # Skip command messages
                    if content.startswith('!'):
                        continue
                    
                    # Skip very short messages
                    if len(content.strip()) < 15:
                        continue
                    
                    # Prioritize messages that seem like answers (longer, informative)
                    is_likely_answer = (
                        len(content) > 30 and  # Substantial content
                        not content.strip().endswith('?') and  # Not ending with question
                        any(indicator in content.lower() for indicator in [
                            'you can', 'you need', 'try', 'use', 'go to', 'click', 'select', 
                            'it is', 'it\'s', 'that is', 'means', 'works', 'feature', 'option'
                        ])
                    )
                    
                    if is_likely_answer:
                        print(f"✅ High priority answer from {result_username}: {content[:50]}...")
                        unique_results.insert(0, result)  # Add to front
                    else:
                        print(f"📝 Including message from {result_username}: {content[:50]}...")
                        unique_results.append(result)
                
                search_results = unique_results[:5]  # Limit to top 5
                print(f"📊 Final results: {len(search_results)} messages found")
            
            if search_results:
                print(f"✅ Found {len(search_results)} relevant messages")
                # Format the search results
                formatted_results = []
                for i, result in enumerate(search_results[:5], 1):  # Limit to top 5 results
                    # Truncate long messages
                    content = result['content']
                    if len(content) > 200:
                        content = content[:197] + '...'
                        
                    formatted_results.append(
                        f"**{i}.** *{result['username']}* in #{result['channel']}:"
                        f"\n> {content}"
                        f"\n*({result['timestamp'].split('T')[0]})*\n"
                    )
                
                # If we have multiple results, ask if any are helpful
                if len(search_results) > 1:
                    response = (
                        f"Hey {ctx.author.mention}, I may have found multiple answers for your question, are these helpful?\n\n"
                        + "\n".join(formatted_results) +
                        "\nLet me know if you'd like more details on any of them!"
                    )
                else:
                    # If only one result, present it as the answer
                    response = (
                        f"{ctx.author.mention}, I found this information that might help:\n\n"
                        + formatted_results[0] +
                        "\nLet me know if you need more details!"
                    )
                
                # Send the response
                await ctx.send(response)
            else:
                print(f"❌ No relevant information found")
                # No results found
                await ctx.send(
                    f"{ctx.author.mention} I couldn't find any relevant information in the chat history. "
                    "Would you like me to help you search for something more specific?"
                )
                
    except Exception as e:
        print(f"❌ Error handling question: {e}")
        await ctx.send(f"{ctx.author.mention} Sorry, I encountered an error while searching for answers. Please try again!")

# === JIM THE MENTOR - Mentorship Commands ===

@bot.command(name='mentor')
async def mentor_command(ctx):
    """Jim's comprehensive mentorship onboarding and guidance"""
    user_id = str(ctx.author.id)
    
    # Check if user is already onboarded
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM mentorship_users WHERE user_id = ?', (user_id,))
        existing_user = cursor.fetchone()
    
    try:
        # Send onboarding flow in DMs
        if not existing_user:
            # New user onboarding
            onboarding_embed = discord.Embed(
                title="🎯 Welcome to Jim's Mentorship Program!",
                description="Hey there! I'm Jim, your personal reselling mentor. Let's get you set up for success! 🚀",
                color=0x00ff88
            )
            onboarding_embed.add_field(
                name="📚 What I Do",
                value="• Analyze your stores with AI\n• Track your progress and goals\n• Give personalized advice\n• Help with photo editing\n• Send motivational voice messages",
                inline=False
            )
            onboarding_embed.add_field(
                name="🤝 Let's Get Started!",
                value="I'll ask you a few questions to personalize your experience. Ready?",
                inline=False
            )
            
            dm_channel = await ctx.author.create_dm()
            await dm_channel.send(embed=onboarding_embed)
            
            # Start onboarding conversation
            await dm_channel.send("**First up:** What's your experience level with reselling?\n\n" +
                                "🌱 **Beginner** - Just starting out\n" +
                                "📈 **Intermediate** - Selling for a few months\n" +
                                "🏆 **Advanced** - Experienced seller\n\n" +
                                "Just type your level!")
            
            # Store onboarding state
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO mentorship_users (
                        user_id, username, display_name, onboarded_at
                    ) VALUES (?, ?, ?, ?)
                ''', (user_id, ctx.author.name, ctx.author.display_name, datetime.now().isoformat()))
            
            await ctx.send("✅ Check your DMs! Let's get your mentorship journey started! 🎯")
            
        else:
            # Returning user - show available commands
            welcome_back_embed = discord.Embed(
                title="👋 Hey there, welcome back!",
                description=f"Great to see you again! Here's what I can help you with today:",
                color=0x0099ff
            )
            welcome_back_embed.add_field(
                name="🔍 **!analyze** [store_url]",
                value="AI-powered store analysis with recommendations",
                inline=False
            )
            welcome_back_embed.add_field(
                name="📊 **!progress**",
                value="See your reselling progress and goals",
                inline=False
            )
            welcome_back_embed.add_field(
                name="🎨 **!photoedit** [attach image]",
                value="AI photo editing and enhancement",
                inline=False
            )
            welcome_back_embed.add_field(
                name="💬 **!ask** [question]",
                value="Get personalized mentorship advice",
                inline=False
            )
            
            await ctx.send(embed=welcome_back_embed)
            
    except discord.Forbidden:
        await ctx.send("❌ I couldn't send you DMs! Please enable DMs from server members in your privacy settings, then try `!mentor` again.")

@bot.command(name='analyze')
async def analyze_store(ctx, store_url: str = None):
    """Analyze a reselling store using Claude AI + Firecrawl with full store crawling"""
    if not store_url:
        await ctx.send("📊 **Store Analysis** - Give me your store URL and I'll analyze your ENTIRE store with AI!\n\n" +
                      "Usage: `!analyze https://poshmark.com/closet/yourstore`\n\n" +
                      "✅ Supported platforms: Poshmark, eBay, Mercari, Depop, Facebook Marketplace\n" +
                      "🔄 **Queue system**: Multiple requests are automatically queued")
        return
    
    user_id = str(ctx.author.id)
    
    # Send analysis starting message
    analysis_embed = discord.Embed(
        title="🔍 Analyzing Your ENTIRE Store...",
        description=f"I'm crawling through ALL pages of your store:\n{store_url}",
        color=0xffaa00
    )
    analysis_embed.add_field(
        name="🤖 Full Store Analysis Process",
        value="• **Step 1**: Crawling ALL product pages with Firecrawl\n• **Step 2**: Processing entire inventory data\n• **Step 3**: Claude AI comprehensive analysis\n• **Step 4**: Generating detailed recommendations",
        inline=False
    )
    analysis_embed.add_field(
        name="⏰ Processing Time",
        value="This may take 3-5 minutes depending on your store size and queue position",
        inline=False
    )
    
    analysis_msg = await ctx.send(embed=analysis_embed)
    
    # Perform analysis (which now handles queueing)
    try:
        analysis_result = await ctx.bot.mentorship_services.analyze_store_with_firecrawl(store_url, user_id)
        
        # Handle queue response
        if analysis_result.get("queued"):
            queue_embed = discord.Embed(
                title="⏳ Added to Analysis Queue",
                description=f"Your store analysis has been queued!\n\n**Store**: {store_url}",
                color=0x00aaff
            )
            queue_embed.add_field(
                name="🚀 Queue Position",
                value=f"#{analysis_result.get('queue_position', 1)}",
                inline=True
            )
            queue_embed.add_field(
                name="⏰ Estimated Wait",
                value=f"~{analysis_result.get('estimated_wait', 3)} minutes",
                inline=True
            )
            queue_embed.add_field(
                name="📋 What's Happening",
                value="• Your request is in the queue\n• I'll crawl your ENTIRE store\n• Complete analysis will be saved\n• You'll get results via DM when done",
                inline=False
            )
            queue_embed.add_field(
                name="💡 Pro Tip",
                value="You can continue using other commands while waiting!",
                inline=False
            )
            
            await analysis_msg.edit(embed=queue_embed)
            await ctx.send(f"🔔 {ctx.author.mention}, I'll DM you when your complete store analysis is ready!")
            return
        
        # Handle other errors
        if "error" in analysis_result:
            error_embed = discord.Embed(
                title="❌ Analysis Failed",
                description=f"Sorry, I couldn't analyze that store: {analysis_result['error']}",
                color=0xff0000
            )
            
            # Show debug info if available
            if "raw_response" in analysis_result:
                error_embed.add_field(
                    name="🐛 Debug Info",
                    value=f"Raw response: {analysis_result['raw_response'][:100]}...",
                    inline=False
                )
            if "json_error" in analysis_result:
                error_embed.add_field(
                    name="⚠️ JSON Error",
                    value=f"Parse error: {analysis_result['json_error']}",
                    inline=False
                )
                
            await analysis_msg.edit(embed=error_embed)
            return
        
        # Show successful analysis results
        results_embed = discord.Embed(
            title="✅ Complete Store Analysis Results",
            description=f"**Store**: {store_url}\n**Platform**: {analysis_result.get('platform', 'Unknown')}\n**Products Analyzed**: {analysis_result.get('product_count', 'Unknown')}",
            color=0x00ff00
        )
        
        # Add Jim's personality response
        jim_response = analysis_result.get('jim_personality_response', '')
        if jim_response:
            results_embed.add_field(
                name="💬 Jim's Take",
                value=jim_response[:1024],
                inline=False
            )
        
        # Add scoring with new inventory diversity score
        results_embed.add_field(
            name="🎯 Overall Score",
            value=f"**{analysis_result.get('overall_score', 0)}/10**",
            inline=True
        )
        results_embed.add_field(
            name="📦 Product Quality",
            value=f"{analysis_result.get('product_quality_score', 0)}/10",
            inline=True
        )
        results_embed.add_field(
            name="💰 Pricing Strategy",
            value=f"{analysis_result.get('pricing_strategy_score', 0)}/10",
            inline=True
        )
        results_embed.add_field(
            name="✨ Listing Optimization",
            value=f"{analysis_result.get('listing_optimization_score', 0)}/10",
            inline=True
        )
        results_embed.add_field(
            name="🎨 Branding",
            value=f"{analysis_result.get('branding_score', 0)}/10",
            inline=True
        )
        results_embed.add_field(
            name="🔄 Inventory Diversity",
            value=f"{analysis_result.get('inventory_diversity_score', 0)}/10",
            inline=True
        )
        results_embed.add_field(
            name="📝 Summary",
            value=analysis_result.get('analysis_summary', 'No summary available'),
            inline=False
        )
        
        # Add recommendations
        recommendations = analysis_result.get('specific_recommendations', [])
        if recommendations:
            rec_text = '\n'.join([f"• {rec}" for rec in recommendations[:3]])
            results_embed.add_field(
                name="💡 Top Recommendations",
                value=rec_text,
                inline=False
            )
        
        await analysis_msg.edit(embed=results_embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Something Went Wrong",
            description=f"Analysis failed: {str(e)}",
            color=0xff0000
        )
        await analysis_msg.edit(embed=error_embed)

@bot.command(name='queue')
async def queue_status(ctx):
    """Check the current analysis queue status"""
    user_id = str(ctx.author.id)
    
    queue_embed = discord.Embed(
        title="📋 Analysis Queue Status",
        color=0x00aaff
    )
    
    # Check if user has a request in queue
    user_in_queue = False
    user_position = 0
    
    for i, item in enumerate(ctx.bot.mentorship_services.analysis_queue):
        if item["user_id"] == user_id:
            user_in_queue = True
            user_position = i + 1
            break
    
    if user_in_queue:
        queue_embed.add_field(
            name="🚀 Your Position",
            value=f"#{user_position}",
            inline=True
        )
        queue_embed.add_field(
            name="⏰ Estimated Wait",
            value=f"~{user_position * 3} minutes",
            inline=True
        )
    else:
        queue_embed.add_field(
            name="📊 Your Status",
            value="No analysis in queue",
            inline=True
        )
    
    # Show total queue length
    total_queue = len(ctx.bot.mentorship_services.analysis_queue)
    queue_embed.add_field(
        name="📈 Total Queue",
        value=f"{total_queue} requests",
        inline=True
    )
    
    await ctx.send(embed=queue_embed)

@bot.command(name='progress')
async def show_progress(ctx):
    """Show user's reselling progress and goals"""
    user_id = str(ctx.author.id)
    
    try:
        user_data = await ctx.bot.mentorship_services.get_user_mentorship_data(user_id)
        
        if not user_data:
            await ctx.send("❌ You haven't started your mentorship journey yet! Use `!mentor` to get started.")
            return
        
        progress_embed = discord.Embed(
            title="📊 Your Reselling Progress",
            description=f"Here's how you're doing, {ctx.author.display_name}! 🎯",
            color=0x0099ff
        )
        
        # User info
        progress_embed.add_field(
            name="👤 Profile",
            value=f"Experience: {user_data.get('experience_level', 'Not set')}\n" +
                  f"Platform: {user_data.get('primary_platform', 'Not set')}\n" +
                  f"Total Sessions: {user_data.get('total_sessions', 0)}",
            inline=True
        )
        
        # Active goals
        goals = user_data.get('active_goals', [])
        if goals:
            goal_text = ""
            for goal in goals[:3]:  # Show up to 3 goals
                goal_text += f"🎯 {goal[2]}\n"  # goal_title
            progress_embed.add_field(
                name="🎯 Active Goals",
                value=goal_text,
                inline=True
            )
        
        # Recent progress
        recent_progress = user_data.get('recent_progress', [])
        if recent_progress:
            progress_text = "📈 Last 7 days:\n"
            total_sales = sum([p[3] for p in recent_progress if p[3]])  # sales_count
            total_revenue = sum([p[4] for p in recent_progress if p[4]])  # revenue
            progress_text += f"Sales: {total_sales}\n"
            progress_text += f"Revenue: ${total_revenue:.2f}"
            progress_embed.add_field(
                name="📈 Recent Activity",
                value=progress_text,
                inline=False
            )
        
        # Jim's encouragement
        encouragement = [
            "You're making great progress! Keep it up! 🚀",
            "Every step forward counts - proud of you! 💪",
            "Your consistency is paying off! 🌟",
            "Remember, success is a journey, not a destination! 🎯"
        ]
        import random
        progress_embed.add_field(
            name="💬 Jim Says",
            value=random.choice(encouragement),
            inline=False
        )
        
        await ctx.send(embed=progress_embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error getting your progress: {str(e)}")

@bot.command(name='photoedit')
async def photo_edit(ctx):
    """AI-powered photo editing for reselling images"""
    if not ctx.message.attachments:
        help_embed = discord.Embed(
            title="🎨 AI Photo Editing",
            description="Upload an image with this command and I'll enhance it for you!",
            color=0xff6b9d
        )
        help_embed.add_field(
            name="✨ What I Can Do",
            value="• Remove backgrounds\n• Enhance lighting and colors\n• Improve image quality\n• Generate product variations",
            inline=False
        )
        help_embed.add_field(
            name="📷 How to Use",
            value="1. Type `!photoedit`\n2. Attach your image\n3. Choose your edit type\n4. Get your enhanced photo!",
            inline=False
        )
        
        await ctx.send(embed=help_embed)
        return
    
    user_id = str(ctx.author.id)
    attachment = ctx.message.attachments[0]
    
    # Check if it's an image
    if not attachment.content_type or not attachment.content_type.startswith('image/'):
        await ctx.send("❌ Please upload an image file (PNG, JPG, JPEG)")
        return
    
    # Photo editing options
    edit_embed = discord.Embed(
        title="🎨 Choose Your Edit Type",
        description="What would you like me to do with your image?",
        color=0xff6b9d
    )
    edit_embed.add_field(
        name="🔄 Background Removal",
        value="Remove the background for clean product shots",
        inline=False
    )
    edit_embed.add_field(
        name="✨ Enhancement",
        value="Improve lighting, colors, and overall quality",
        inline=False
    )
    edit_embed.add_field(
        name="🎯 Coming Soon",
        value="• AI-generated variations\n• Style transfers\n• Batch processing",
        inline=False
    )
    
    await ctx.send(embed=edit_embed)
    await ctx.send("📝 **Reply with:** `background` or `enhance` to choose your edit type!")
    
    # Log the photo edit request
    try:
        with sqlite3.connect('beta_testing.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO photo_edits (
                    user_id, original_filename, edit_type, created_at
                ) VALUES (?, ?, ?, ?)
            ''', (user_id, attachment.filename, 'requested', datetime.now().isoformat()))
    except Exception as e:
        print(f"Error logging photo edit: {e}")

@bot.command(name='ask')
async def ask_jim(ctx, *, question: str = None):
    """Get personalized mentorship advice from Jim"""
    if not question:
        await ctx.send("💬 **Ask Jim Anything!**\n\nUsage: `!ask How do I price my items better?`\n\n" +
                      "I'll give you personalized advice based on your goals and progress! 🎯")
        return
    
    user_id = str(ctx.author.id)
    
    # Generate thinking message
    thinking_embed = discord.Embed(
        title="🤔 Jim is thinking...",
        description=f"Let me consider your question: *{question}*",
        color=0xffaa00
    )
    thinking_msg = await ctx.send(embed=thinking_embed)
    
    try:
        # Get personalized advice
        channel_context = "Asked in DM" if isinstance(ctx.channel, discord.DMChannel) else f"Asked in channel: {ctx.channel.name}"
        jim_response = await ctx.bot.mentorship_services.generate_personalized_advice(
            user_id, question, channel_context
        )
        
        # Create response embed
        response_embed = discord.Embed(
            title="💬 Jim's Advice",
            description=jim_response,
            color=0x00ff88
        )
        response_embed.set_footer(text="💡 Want more specific help? Try !analyze or !progress")
        
        await thinking_msg.edit(embed=response_embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Something Went Wrong",
            description=f"Sorry, I couldn't process your question: {str(e)}",
            color=0xff0000
        )
        await thinking_msg.edit(embed=error_embed)

@bot.command(name='goals')
async def set_goals(ctx, *, goal_description: str = None):
    """Set and manage your reselling goals"""
    user_id = str(ctx.author.id)
    
    if not goal_description:
        # Show existing goals
        try:
            with sqlite3.connect('beta_testing.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT goal_title, goal_description, target_value, current_progress, created_at
                    FROM mentorship_goals 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                goals = cursor.fetchall()
            
            if not goals:
                goals_embed = discord.Embed(
                    title="🎯 No Goals Set Yet",
                    description="Let's set some goals to track your progress!",
                    color=0x0099ff
                )
                goals_embed.add_field(
                    name="How to Set Goals",
                    value="`!goals Make $500 this month`\n`!goals List 50 new items`\n`!goals Get 100 followers`",
                    inline=False
                )
            else:
                goals_embed = discord.Embed(
                    title="🎯 Your Active Goals",
                    description=f"You have {len(goals)} active goals:",
                    color=0x00ff88
                )
                for goal in goals[:5]:  # Show up to 5 goals
                    progress_bar = "█" * int(goal[3]/10) if goal[3] else ""
                    goals_embed.add_field(
                        name=f"🎯 {goal[0]}",
                        value=f"{goal[1]}\nProgress: {progress_bar} {goal[3]:.1f}%",
                        inline=False
                    )
            
            await ctx.send(embed=goals_embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting your goals: {str(e)}")
    
    else:
        # Create new goal
        try:
            await ctx.bot.mentorship_services.create_user_goal(
                user_id, "New Goal", goal_description
            )
            
            success_embed = discord.Embed(
                title="✅ Goal Created!",
                description=f"Added to your goals: *{goal_description}*",
                color=0x00ff88
            )
            success_embed.add_field(
                name="🎯 What's Next?",
                value="I'll help you track progress towards this goal. Use `!progress` to see updates!",
                inline=False
            )
            
            await ctx.send(embed=success_embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error creating goal: {str(e)}")

# Admin commands for managing the bot
@bot.command(name='add-update')
@commands.has_permissions(administrator=True)
async def add_update(ctx, *, content):
    """Add a new update (Admin only)"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO whats_new (content, timestamp, created_by)
            VALUES (?, ?, ?)
        ''', (content, datetime.now().isoformat(), ctx.author.display_name))
    
    await ctx.send("✅ Update added successfully!")

@bot.command(name='rescan')
@commands.has_permissions(administrator=True)
async def manual_scan_history(ctx, hours: int = 24):
    """Manually scan chat history (Admin only)"""
    await ctx.send(f"🔍 Scanning last {hours} hours of chat history...")
    await ctx.bot.scan_recent_history_with_announcements(hours)
    await ctx.send("✅ History scan complete!")

@bot.command(name='chat-stats')
@commands.has_permissions(administrator=True)
async def chat_stats(ctx):
    """Get chat statistics (Admin only)"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Get message count by user
        cursor.execute('''
            SELECT username, COUNT(*) as message_count 
            FROM messages 
            GROUP BY username 
            ORDER BY message_count DESC 
            LIMIT 10
        ''')
        top_users = cursor.fetchall()
        
        # Get total message count
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        # Get messages from last 24 hours
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp > ?', (yesterday,))
        recent_messages = cursor.fetchone()[0]
    
    embed = discord.Embed(
        title="📊 Chat Statistics",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Total Messages Tracked", value=str(total_messages), inline=True)
    embed.add_field(name="Messages (Last 24h)", value=str(recent_messages), inline=True)
    embed.add_field(name="Top Contributors", value="\n".join([f"{user}: {count}" for user, count in top_users[:5]]), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='close-bug')
@commands.has_permissions(administrator=True)
async def close_bug(ctx, bug_id: int):
    """Close a bug report (Admin only)"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bugs SET status = 'fixed' WHERE id = ?
        ''', (bug_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
    
    if rows_affected > 0:
        # Update Google Sheets if enabled
        if ctx.bot.sheets_manager:
            try:
                await ctx.bot.sheets_manager.update_bug_status(bug_id, 'fixed')
            except Exception as e:
                print(f"⚠️ Failed to update bug status in spreadsheet: {e}")
        
        await ctx.send(f"✅ Bug #{bug_id} marked as fixed!")
    else:
        await ctx.send(f"❌ Bug #{bug_id} not found.")

@bot.command(name='resolve-bug')
async def resolve_bug(ctx, bug_id: int):
    """Mark your own bug as resolved (Testers can use this)"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Check if the bug exists and belongs to the user
        cursor.execute('''
            SELECT id, username, bug_description, status 
            FROM bugs 
            WHERE id = ?
        ''', (bug_id,))
        
        bug = cursor.fetchone()
        
        if not bug:
            await ctx.send(f"❌ Bug #{bug_id} not found.")
            return
        
        bug_id_db, bug_username, description, current_status = bug
        
        # Allow the original reporter or staff to resolve
        is_staff = any(role.name.lower() in ['staff', 'admin', 'moderator', 'developer'] 
                      for role in ctx.author.roles) if ctx.guild else False
        
        if bug_username.lower() != ctx.author.display_name.lower() and not is_staff:
            await ctx.send(f"❌ You can only resolve bugs that you reported. Bug #{bug_id} was reported by {bug_username}.")
            return
        
        if current_status == 'fixed':
            await ctx.send(f"✅ Bug #{bug_id} is already marked as resolved!")
            return
        
        # Update bug status to resolved
        cursor.execute('''
            UPDATE bugs SET status = 'fixed' WHERE id = ?
        ''', (bug_id,))
        
        conn.commit()
    
    # Update Google Sheets if enabled (use resolve_bug method for "Resolved" status)
    sheets_success = False
    if ctx.bot.sheets_manager:
        try:
            sheets_success = await ctx.bot.sheets_manager.resolve_bug(bug_id)
            if sheets_success:
                print(f"✅ Updated bug #{bug_id} status to 'Resolved' in Google Sheets")
            else:
                print(f"⚠️ Failed to update bug #{bug_id} in Google Sheets")
        except Exception as e:
            print(f"❌ Error updating Google Sheets: {e}")
    
    # Create success embed
    embed = discord.Embed(
        title="✅ Bug Resolved!",
        description=f"Bug #{bug_id} has been marked as resolved.",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📝 Description", 
        value=description[:100] + ('...' if len(description) > 100 else ''),
        inline=False
    )
    
    embed.add_field(name="👤 Resolved by", value=ctx.author.display_name, inline=True)
    embed.add_field(name="📅 Resolved at", value=datetime.now().strftime("%Y-%m-%d %H:%M"), inline=True)
    
    # Add Google Sheets status
    if sheets_success:
        embed.add_field(
            name="📊 Google Sheets", 
            value="✅ Status updated to 'Resolved'", 
            inline=True
        )
    else:
        embed.add_field(
            name="📊 Google Sheets", 
            value="⚠️ Manual update may be needed", 
            inline=True
        )
    
    embed.set_footer(text="Bug preserved in sheet for historical tracking • Thanks for testing! 🎉")
    
    await ctx.send(embed=embed)

@bot.command(name='reopen-bug')
@commands.has_permissions(administrator=True)
async def reopen_bug(ctx, bug_id: int):
    """Reopen a closed bug report (Admin only)"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bugs SET status = 'potential' WHERE id = ?
        ''', (bug_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
    
    if rows_affected > 0:
        # Update Google Sheets if enabled
        if ctx.bot.sheets_manager:
            try:
                await ctx.bot.sheets_manager.update_bug_status(bug_id, 'open')
            except Exception as e:
                print(f"⚠️ Failed to update bug status in spreadsheet: {e}")
        
        await ctx.send(f"🔄 Bug #{bug_id} reopened for investigation!")
    else:
        await ctx.send(f"❌ Bug #{bug_id} not found.")

@bot.command(name='update-feature')
@commands.has_permissions(administrator=True)
async def update_feature(ctx, feature_name, status, *, notes=""):
    """Update feature testing status (Admin only)"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO testing_progress (feature_name, status, last_updated, notes)
            VALUES (?, ?, ?, ?)
        ''', (feature_name, status, datetime.now().isoformat(), notes))
    
    await ctx.send(f"✅ Feature '{feature_name}' updated to '{status}'!")

@bot.command(name='review-bugs')
@commands.has_permissions(administrator=True)
async def review_bugs(ctx):
    """Review potential bugs (Admin only) - NOTE: Auto-detection is disabled"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, bug_description, timestamp, username 
            FROM bugs 
            WHERE status = 'potential'
        ''')
        potential_bugs = cursor.fetchall()
    
    if not potential_bugs:
        await ctx.send("No potential bugs to review.")
        return
    
    embed = discord.Embed(
        title="🐛 Potential Bugs to Review",
        color=0xff0000,
        timestamp=datetime.now()
    )
    
    for bug_id, description, timestamp, username in potential_bugs:
        embed.add_field(
            name=f"Bug #{bug_id} by {username}",
            value=f"{description}\n*{timestamp}*",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='jim')
async def jim(ctx):
    """Manual greeting"""
    await ctx.bot.announce_startup()

@bot.command(name='my-bugs')
async def my_bugs(ctx):
    """View all your reported bugs and their status"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Get all bugs reported by this user
        cursor.execute('''
            SELECT id, bug_description, status, timestamp 
            FROM bugs 
            WHERE username = ? 
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (ctx.author.display_name,))
        
        bugs = cursor.fetchall()
    
    if not bugs:
        embed = discord.Embed(
            title="🐛 Your Bug Reports",
            description="You haven't reported any bugs yet. Use `!bug <description>` to report issues!",
            color=0x0099ff
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"🐛 Your Bug Reports ({len(bugs)} total)",
        color=0x0099ff
    )
    
    open_count = sum(1 for bug in bugs if bug[2] in ['open', 'potential'])
    fixed_count = sum(1 for bug in bugs if bug[2] == 'fixed')
    
    embed.add_field(name="🔴 Open/Potential", value=str(open_count), inline=True)
    embed.add_field(name="✅ Resolved", value=str(fixed_count), inline=True)
    embed.add_field(name="📈 Total", value=str(len(bugs)), inline=True)
    
    bug_list = ""
    for bug_id, description, status, timestamp in bugs:
        status_emoji = "✅" if status == 'fixed' else ("🔴" if status == 'open' else "🟡")
        short_desc = description[:50] + ('...' if len(description) > 50 else '')
        bug_list += f"{status_emoji} **#{bug_id}**: {short_desc}\n"
    
    embed.add_field(name="📝 Recent Bugs", value=bug_list or "No bugs found", inline=False)
    
    embed.set_footer(text="Use !resolve-bug <id> to mark your bugs as resolved | Use !bug-info <id> for details")
    
    await ctx.send(embed=embed)

@bot.command(name='buginfo')
async def bug_info(ctx, bug_id: int):
    """Get detailed information about a bug"""
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT bug_description, timestamp, username, status, channel_id, added_by
            FROM bugs 
            WHERE id = ?
        ''', (bug_id,))
        bug_info = cursor.fetchone()
    
    if not bug_info:
        await ctx.send(f"❌ Bug #{bug_id} not found.")
        return
    
    bug_description, timestamp, username, status, channel_id, added_by = bug_info
    
    channel = ctx.bot.get_channel(int(channel_id))
    
    embed = discord.Embed(
        title=f"🐛 Bug #{bug_id} Information",
        color=0xff0000,
        timestamp=datetime.now()
    )
    embed.add_field(name="Description", value=bug_description, inline=False)
    embed.add_field(name="Reported by", value=f"{username} (Added by {added_by})", inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Reported on", value=timestamp, inline=True)
    embed.add_field(name="Channel", value=channel.mention, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='update-settings')
@commands.has_permissions(administrator=True)
async def update_settings(ctx, setting_name: str = None, new_value: str = None):
    """Update bot settings on the fly (Admin only)"""
    if not setting_name or not new_value:
        await ctx.send("📝 **Self-Update Settings**\n\n" +
                      "Usage: `!update-settings <setting> <value>`\n\n" +
                      "**Available settings:**\n" +
                      "• `timeout` - Firecrawl timeout (ms)\n" +
                      "• `scroll_actions` - Number of scroll actions\n" +
                      "• `page_limit` - Max pages to crawl\n\n" +
                      "Example: `!update-settings timeout 30000`")
        return

@bot.command(name='reload')
@commands.has_permissions(administrator=True)
async def reload_module(ctx, module_name: str = "self_update_system"):
    """Hot reload a module (Admin only)"""
    await bot.self_update_commands.cmd_reload_module(ctx, module_name)

@bot.command(name='show-config')
@commands.has_permissions(administrator=True)
async def show_config(ctx):
    """Show current bot configuration (Admin only)"""
    await bot.self_update_commands.cmd_show_config(ctx)

@bot.command(name='auto-fix')
@commands.has_permissions(administrator=True)
async def auto_fix(ctx, error_message: str = None):
    """Auto-fix common API issues (Admin only)"""
    if not error_message:
        await ctx.send("🔧 **Auto-Fix System**\n\n" +
                      "Usage: `!auto-fix \"error message\"`\n\n" +
                      "I'll analyze the error and apply automatic fixes!")
        return
    
    try:
        fixes_applied = await bot.self_update_system.auto_fix_api_issues(error_message)
        if fixes_applied:
            await ctx.send(f"✅ **Auto-fixes applied!** The bot should work better now.")
        else:
            await ctx.send(f"❌ No automatic fixes available for this error type.")
    except Exception as e:
        await ctx.send(f"❌ Error during auto-fix: {e}")

@bot.command(name='report-bug')
async def report_bug(ctx, *, bug_description: str = None):
    """Report a bug manually"""
    if not bug_description:
        embed = discord.Embed(
            title="🐛 Bug Report",
            description="Please provide a description of the bug you encountered.",
            color=0xff0000
        )
        embed.add_field(
            name="Usage", 
            value="`!report-bug Your bug description here`", 
            inline=False
        )
        embed.add_field(
            name="Example", 
            value="`!report-bug The app crashes when I try to upload images`", 
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    try:
        # Save to database with retry logic
        max_retries = 3
        bug_id = None
        
        for attempt in range(max_retries):
            try:
                with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO bugs (user_id, username, bug_description, timestamp, status, staff_notified, channel_id, added_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(ctx.author.id),
                        ctx.author.display_name,
                        f"[MANUAL REPORT] {description}",
                        datetime.now().isoformat(),
                        'open',
                        False,
                        str(ctx.channel.id),
                        ctx.author.display_name
                    ))
                    
                    bug_id = cursor.lastrowid
                    conn.commit()
                    break  # Success, exit retry loop
                    
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"Database locked, retry {attempt + 1}/{max_retries} in 1 second...")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise  # Re-raise if not a lock error or max retries reached
        
        # Add to Google Sheets if enabled
        if ctx.bot.sheets_manager and bug_id:
            try:
                print(f"🔄 Attempting to add bug #{bug_id} to Google Sheets...")
                
                # Detect the app area using AI analysis
                try:
                    print(f"🔍 Starting AI detection for manual report: {description[:50]}...")
                    detected_area = await ctx.bot.detect_bug_area(description)
                    print(f"🎯 Detected area: {detected_area}")
                except Exception as e:
                    print(f"❌ Manual AI detection failed: {e}")
                    detected_area = "Other"
                
                bug_data = {
                    'bug_id': bug_id,
                    'username': ctx.author.display_name,
                    'description': f"[MANUAL REPORT] {description}",
                    'area': detected_area,  # Add the detected area
                    'timestamp': datetime.now().isoformat(),
                    'status': 'open',
                    'channel_id': str(ctx.channel.id),
                    'guild_id': str(ctx.guild.id) if ctx.guild else '',
                    'added_by': ctx.author.display_name
                }
                print(f"📊 Bug data prepared: {bug_data}")
                
                # Properly await the Google Sheets call
                sheets_result = await ctx.bot.sheets_manager.add_bug_to_sheet(bug_data)
                if sheets_result:
                    print(f"✅ Successfully added bug #{bug_id} to Google Sheets")
                    sheets_success = True
                else:
                    print(f"❌ Failed to add bug #{bug_id} to Google Sheets - API returned False")
                    sheets_success = False
                    
            except Exception as e:
                print(f"⚠️ Exception while adding bug to spreadsheet: {e}")
                import traceback
                traceback.print_exc()
                sheets_success = False
        else:
            if not ctx.bot.sheets_manager:
                print("⚠️ Google Sheets manager not initialized")
            if not bug_id:
                print("⚠️ Bug ID is None or empty")
            sheets_success = False
        
        # Send success message with Google Sheet link
        embed = discord.Embed(
            title="✅ Bug Report Submitted!",
            description=f"Your bug report has been logged as **Bug #{bug_id}**",
            color=0x00ff00
        )
        embed.add_field(
            name="🐛 Description",
            value=bug_description[:1000] + ("..." if len(bug_description) > 1000 else ""),
            inline=False
        )
        embed.add_field(
            name="👤 Reported by",
            value=f"{ctx.author.display_name} (Added by {ctx.author.display_name})",
            inline=True
        )
        embed.add_field(
            name="📊 Status",
            value="Open for review",
            inline=True
        )
        
        if sheets_success:
            embed.add_field(
                name="📈 Track Progress",
                value="[View in Google Sheets](https://docs.google.com/spreadsheets/d/1lTOj3r-LVMnp-oVu7dDnGWjBzKxWeZJJGZSxUMaMwB4/edit)",
                inline=False
            )
            embed.set_footer(text="Your bug has been added to our shared tracking sheet for transparency!")
        else:
            embed.set_footer(text="Bug saved locally. Google Sheets sync pending.")
        
        await ctx.send(embed=embed)
        
        # Add reaction to show it was processed
        try:
            await ctx.message.add_reaction('✅')
            await ctx.message.add_reaction('🐛')
        except:
            pass
            
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Error Submitting Bug Report",
            description=f"Sorry, there was an error saving your bug report: {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=error_embed)

@bot.command(name='view-sheet')
@commands.has_any_role('Staff', 'Admin', 'Moderator')
async def view_sheet(ctx):
    """View link to the Google Sheets bug tracking sheet (Staff only)"""
    embed = discord.Embed(
        title="📊 Bug Tracking Sheet",
        description="Access the shared Google Sheets bug tracking system",
        color=0x4285f4  # Google blue
    )
    embed.add_field(
        name="🔗 Google Sheets Link",
        value="[Open Bug Tracking Sheet](https://docs.google.com/spreadsheets/d/1lTOj3r-LVMnp-oVu7dDnGWjBzKxWeZJJGZSxUMaMwB4/edit)",
        inline=False
    )
    embed.add_field(
        name="📋 What's Included",
        value="• All reported bugs from Discord\n• Manual bug reports\n• Bug status tracking\n• Assignment and resolution info",
        inline=False
    )
    embed.add_field(
        name="⚙️ Access Level",
        value="Staff members can view and edit\nService account syncs automatically",
        inline=False
    )
    embed.set_footer(text="💡 This sheet updates automatically when bugs are reported or status changes are made")
    
    await ctx.send(embed=embed)

@bot.command(name='sync')
@commands.has_permissions(administrator=True)
async def sync_missed_bugs(ctx, hours: int = 24):
    """
    Smart sync to catch up on missed !bug commands and handle deleted messages
    Usage: !sync [hours] (default: 24 hours)
    """
    if not ctx.bot.sheets_manager:
        await ctx.send("⚠️ Google Sheets not configured, skipping sync")
        return
        
    await ctx.send(f"🔄 Starting smart bug report sync for last {hours} hours...")
    
    try:
        synced_bugs = 0
        removed_bugs = 0
        
        # Process all guilds and channels
        for guild in ctx.bot.guilds:
            for channel in guild.text_channels:
                try:
                    # Check if bot has permission to read message history
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                        
                    # Get messages from the last X hours
                    cutoff_time = datetime.now() - timedelta(hours=hours)
                    
                    async for message in channel.history(after=cutoff_time, limit=1000):
                        # Look for !bug commands
                        if message.content.startswith('!bug ') and not message.author.bot:
                            # Extract bug description
                            bug_description = message.content[5:].strip()
                            if not bug_description:
                                continue
                                
                            # Check if already in database
                            with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    SELECT bug_id FROM bugs 
                                    WHERE user_id = ? AND bug_description LIKE ? AND timestamp >= ?
                                ''', (
                                    str(message.author.id),
                                    f"%{bug_description[:50]}%",
                                    (message.created_at - timedelta(minutes=5)).isoformat()
                                ))
                                
                                if cursor.fetchone():
                                    continue  # Already processed
                            
                            # Add to database
                            def db_operation():
                                with sqlite3.connect('beta_testing.db') as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('''
                                        INSERT INTO bugs (user_id, username, bug_description, timestamp, status, staff_notified, channel_id, added_by)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        str(message.author.id),
                                        message.author.display_name,
                                        bug_description,
                                        message.created_at.isoformat(),
                                        'open',
                                        True,
                                        str(message.channel.id),
                                        message.author.display_name
                                    ))
                                    bug_id = cursor.lastrowid
                                    conn.commit()
                                    return bug_id
                            
                            # Run database operation in thread pool
                            bug_id = await asyncio.get_event_loop().run_in_executor(None, db_operation)
                            
                            # Detect the app area using AI analysis
                            try:
                                print(f"🔍 Starting AI detection for: {bug_description[:50]}...")
                                detected_area = await ctx.bot.detect_bug_area(bug_description)
                                print(f"🎯 Auto-detected area for bug #{bug_id}: {detected_area}")
                            except Exception as e:
                                print(f"❌ AI detection failed: {e}")
                                detected_area = "Other"
                            
                            # Add to Google Sheets
                            bug_data = {
                                'bug_id': bug_id,
                                'username': message.author.display_name,
                                'description': bug_description,
                                'area': detected_area,  # Add the detected area
                                'timestamp': message.created_at.isoformat(),
                                'status': 'open',
                                'channel_id': str(message.channel.id),
                                'guild_id': str(message.guild.id) if message.guild else '',
                                'added_by': message.author.display_name
                            }
                            
                            await ctx.bot.sheets_manager.add_bug_to_sheet(bug_data)
                            synced_bugs += 1
                            print(f"📝 Synced missed bug #{bug_id} from {message.author.display_name}")
                                
                except discord.Forbidden:
                    continue  # Skip channels we can't access
                except Exception as e:
                    print(f"Error syncing channel {channel.name}: {e}")
                    continue
        
        embed = discord.Embed(
            title="🔄 Smart Sync Complete",
            description=f"Processed last {hours} hours of chat history",
            color=0x00ff00
        )
        embed.add_field(name="📝 Bugs Synced", value=str(synced_bugs), inline=True)
        embed.add_field(name="📊 Status", value="✅ Complete", inline=True)
        
        await ctx.send(embed=embed)
        print(f"✅ Sync complete: {synced_bugs} bugs processed")
        
    except Exception as e:
        await ctx.send(f"❌ Error during sync: {e}")
        print(f"❌ Error in sync: {e}")

# === AMBASSADOR PROGRAM COMMANDS ===

def has_staff_role(user, guild=None):
    """Check if user has Staff role or manage_guild permissions"""
    if guild:
        # Check in guild context
        member = guild.get_member(user.id)
        if member:
            return any(role.name.lower() == "staff" for role in member.roles) or member.guild_permissions.manage_guild
    else:
        # Check across all mutual guilds for DM context
        for guild in bot.guilds:
            member = guild.get_member(user.id)
            if member:
                if any(role.name.lower() == "staff" for role in member.roles) or member.guild_permissions.manage_guild:
                    return True
    return False

@bot.command(name='ambassador')
async def ambassador_command(ctx, action=None, user=None, *, platforms=None):
    """Ambassador Program management commands"""
    # Check Staff role permissions (works in DMs and guilds)
    if not has_staff_role(ctx.author, ctx.guild):
        await ctx.send("❌ You need the Staff role or Manage Server permissions to use ambassador commands.")
        return
    
    if action == "add" and user and platforms:
        # Convert user string to Member object if needed
        if isinstance(user, str):
            # Remove @ symbol if present
            user_str = user.replace('@', '').replace('<', '').replace('>', '')
            
            # Try to find member by username or ID
            member = None
            
            # Search across all guilds the bot is in
            for guild in bot.guilds:
                if user_str.isdigit():
                    # It's a user ID
                    member = guild.get_member(int(user_str))
                else:
                    # It's a username, search by display name or username
                    for m in guild.members:
                        if m.display_name.lower() == user_str.lower() or m.name.lower() == user_str.lower():
                            member = m
                            break
                
                if member:
                    break
            
            if not member:
                await ctx.send(f"❌ Could not find member: {user}")
                return
            user = member
        
        # Add new ambassador
        try:
            # Store in Supabase first (persistent)
            if bot.ambassador_program.supabase:
                try:
                    supabase_data = {
                        'discord_id': str(user.id),
                        'username': user.display_name,
                        'social_handles': platforms,
                        'target_platforms': platforms,
                        'joined_date': datetime.now().isoformat(),
                        'total_points': 0,
                        'current_month_points': 0,
                        'consecutive_months': 0,
                        'reward_tier': 'none',
                        'status': 'active'
                    }
                    bot.ambassador_program.supabase.table('ambassadors').upsert(supabase_data).execute()
                    print(f"✅ Ambassador stored in Supabase: {user.display_name}")
                except Exception as e:
                    print(f"⚠️ Supabase storage failed: {e}")
            
            # Also store in local SQLite as backup
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO ambassadors (
                        discord_id, username, social_handles, target_platforms, 
                        joined_date, total_points, current_month_points, 
                        consecutive_months, reward_tier, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(user.id), user.display_name, platforms, platforms,
                    datetime.now().isoformat(), 0, 0, 0, 'none', 'active'
                ))
                conn.commit()
            
            # Send DM with rules and scoring system
            embed = discord.Embed(
                title="🎉 Welcome to the Sidekick Tools Ambassador Program!",
                description=f"Hi {user.display_name}! You've been added as an ambassador.",
                color=0x00ff00
            )
            embed.add_field(
                name="📋 Your Platforms",
                value=platforms,
                inline=False
            )
            embed.add_field(
                name="🎯 Monthly Goal",
                value="Earn **50+ points** each month to maintain ambassador status",
                inline=False
            )
            embed.add_field(
                name="📊 Scoring System",
                value="""
                **Base Points:**
                • YouTube/TikTok Videos: 15 pts
                • Quora/Reddit Answers: 12 pts  
                • Facebook Group Posts: 10 pts
                • Instagram Posts/Reels: 8 pts
                • Tweets/Threads: 6 pts
                • Stories: 3 pts
                
                **Engagement Bonuses:**
                • +1 pt per 25 likes/upvotes
                • +2 pts per 5 comments
                • +1 pt per share/retweet
                """,
                inline=False
            )
            embed.add_field(
                name="🏆 Reward Tiers",
                value="""
                • 3 months: 3-month recurring commissions
                • 6 months: 6-month recurring commissions  
                • 9 months: +5% commission bump
                • 12 months: Lifetime commissions
                """,
                inline=False
            )
            embed.add_field(
                name="📤 How to Submit",
                value="DM me your post URLs or screenshots. I'll analyze and award points automatically!",
                inline=False
            )
            
            try:
                await user.send(embed=embed)
                await ctx.send(f"✅ {user.display_name} has been added as an ambassador and sent the program details!")
            except discord.Forbidden:
                await ctx.send(f"✅ {user.display_name} added as ambassador, but couldn't send DM (DMs disabled)")
                
        except Exception as e:
            await ctx.send(f"❌ Error adding ambassador: {e}")
    
    elif action == "remove" and user:
        # Remove ambassador
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE ambassadors SET status = "inactive" WHERE discord_id = ?', (str(user.id),))
                if cursor.rowcount == 0:
                    await ctx.send(f"❌ {user.display_name} is not currently an ambassador.")
                    return
                conn.commit()
            
            await ctx.send(f"✅ {user.display_name} has been removed from the ambassador program.")
        except Exception as e:
            await ctx.send(f"❌ Error removing ambassador: {e}")
    
    else:
        # Show usage
        embed = discord.Embed(
            title="🏛️ Ambassador Program Commands",
            color=0x3498db
        )
        embed.add_field(
            name="Add Ambassador",
            value="`!ambassador add @user platforms`\nExample: `!ambassador add @john YouTube, Instagram`",
            inline=False
        )
        embed.add_field(
            name="Remove Ambassador", 
            value="`!ambassador remove @user`",
            inline=False
        )
        await ctx.send(embed=embed)

@bot.command(name='ambassadors')
async def ambassadors_report(ctx, action=None):
    """Generate ambassador reports"""
    if not has_staff_role(ctx.author, ctx.guild):
        await ctx.send("❌ You need the Staff role or Manage Server permissions to view ambassador reports.")
        return
    
    if action == "report":
        try:
            with sqlite3.connect('ambassador_program.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT discord_id, username, current_month_points, total_points, 
                           consecutive_months, reward_tier, status
                    FROM ambassadors 
                    WHERE status = 'active'
                    ORDER BY current_month_points DESC
                ''')
                ambassadors = cursor.fetchall()
            
            if not ambassadors:
                await ctx.send("📊 No active ambassadors found.")
                return
            
            embed = discord.Embed(
                title="📊 Ambassador Program Leaderboard",
                description=f"Current month performance ({len(ambassadors)} active ambassadors)",
                color=0x00ff00
            )
            
            leaderboard = ""
            for i, (discord_id, username, month_points, total_points, consecutive, tier, status) in enumerate(ambassadors[:10]):
                status_emoji = "✅" if month_points >= 50 else "⚠️"
                tier_emoji = "👑" if tier != "none" else ""
                leaderboard += f"{i+1}. {status_emoji} **{username}** {tier_emoji}\n"
                leaderboard += f"   This month: {month_points} pts | Total: {total_points} pts | Streak: {consecutive}mo\n\n"
            
            embed.add_field(name="🏆 Top Performers", value=leaderboard or "No data", inline=False)
            
            # Summary stats
            compliant = sum(1 for a in ambassadors if a[2] >= 50)
            behind = len(ambassadors) - compliant
            
            embed.add_field(name="📈 Summary", value=f"✅ On track: {compliant}\n⚠️ Behind pace: {behind}", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error generating report: {e}")
    
    else:
        await ctx.send("Use `!ambassadors report` to see the current leaderboard.")

@bot.command(name='ambassador-detail')
async def ambassador_detail(ctx, user: discord.Member = None):
    """Get detailed ambassador information"""
    if not has_staff_role(ctx.author, ctx.guild):
        await ctx.send("❌ You need the Staff role or Manage Server permissions to view ambassador details.")
        return
    
    if not user:
        await ctx.send("❌ Please specify a user: `!ambassador-detail @user`")
        return
    
    try:
        with sqlite3.connect('ambassador_program.db') as conn:
            cursor = conn.cursor()
            
            # Get ambassador info
            cursor.execute('SELECT * FROM ambassadors WHERE discord_id = ?', (str(user.id),))
            ambassador = cursor.fetchone()
            
            if not ambassador:
                await ctx.send(f"❌ {user.display_name} is not an ambassador.")
                return
            
            # Get recent submissions
            cursor.execute('''
                SELECT platform, post_type, points_awarded, timestamp, validity_status
                FROM submissions 
                WHERE ambassador_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', (str(user.id),))
            submissions = cursor.fetchall()
        
        discord_id, username, social_handles, platforms, joined_date, total_points, month_points, consecutive, tier, status = ambassador
        
        embed = discord.Embed(
            title=f"👤 Ambassador Details: {username}",
            color=0x3498db
        )
        
        embed.add_field(name="📊 Points", value=f"This month: {month_points}\nTotal: {total_points}", inline=True)
        embed.add_field(name="🔥 Streak", value=f"{consecutive} months", inline=True)
        embed.add_field(name="🏆 Tier", value=tier.replace('_', ' ').title(), inline=True)
        embed.add_field(name="🎯 Platforms", value=platforms or "Not specified", inline=False)
        
        if submissions:
            recent_posts = ""
            for platform, post_type, points, timestamp, validity in submissions[:5]:
                date = datetime.fromisoformat(timestamp).strftime("%m/%d")
                status_emoji = "✅" if validity == "accepted" else "⚠️" if validity == "flagged" else "❌"
                recent_posts += f"{status_emoji} {date} - {platform.title()} {post_type.replace('_', ' ')} ({points} pts)\n"
            
            embed.add_field(name="📝 Recent Posts", value=recent_posts, inline=False)
        
        compliance = "✅ On Track" if month_points >= 50 else f"⚠️ Behind ({50 - month_points} pts needed)"
        embed.add_field(name="📈 Compliance", value=compliance, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error getting ambassador details: {e}")

# Add recovery command for Ambassador Program
@bot.command(name='ambassador-recover')
async def ambassador_recover(ctx):
    """Recover ambassador submissions from Discord logs"""
    if not has_staff_role(ctx.author, ctx.guild):
        await ctx.send("❌ You need the Staff role or Manage Server permissions to use recovery commands.")
        return
    
    try:
        embed = discord.Embed(
            title="🔄 Starting Ambassador Program Recovery",
            description="Scanning Discord logs for missed submissions...",
            color=0x3498db
        )
        status_msg = await ctx.send(embed=embed)
        
        # Run recovery
        await bot.ambassador_program.recover_from_logs()
        
        # Update status
        embed = discord.Embed(
            title="✅ Recovery Complete",
            description="Ambassador program data has been recovered from Discord logs.",
            color=0x00ff00
        )
        embed.add_field(name="📊 Next Steps", value="Use `!ambassadors report` to see updated data", inline=False)
        
        await status_msg.edit(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error during recovery: {e}")

@bot.command(name='ambassador-docs')
async def ambassador_docs_sync(ctx):
    """Manually sync ambassador report to Google Docs"""
    if not has_staff_role(ctx.author, ctx.guild):
        await ctx.send("❌ You need the Staff role or Manage Server permissions to sync reports.")
        return
    
    try:
        if not bot.ambassador_program.reporting_system:
            await ctx.send("❌ Google Docs integration not configured. Set AMBASSADOR_GOOGLE_DOC_ID environment variable.")
            return
        
        embed = discord.Embed(
            title="📄 Syncing to Google Docs",
            description="Generating ambassador report...",
            color=0x3498db
        )
        status_msg = await ctx.send(embed=embed)
        
        # Generate report
        success = await bot.ambassador_program.reporting_system.generate_monthly_report()
        
        if success:
            embed = discord.Embed(
                title="✅ Google Docs Sync Complete",
                description="Ambassador report has been updated in Google Docs.",
                color=0x00ff00
            )
            embed.add_field(name="📊 Report Includes", value="• Current leaderboard\n• Detailed ambassador status\n• Recent activity summary", inline=False)
        else:
            embed = discord.Embed(
                title="❌ Sync Failed",
                description="Could not update Google Docs report.",
                color=0xff0000
            )
        
        await status_msg.edit(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error syncing to Google Docs: {e}")

@bot.command(name='helpambassador')
async def help_ambassador_command(ctx):
    """Ambassador Program help for staff members"""
    # Check if user has staff permissions
    if not has_staff_role(ctx.author, ctx.guild):
        await ctx.send("❌ Ambassador help is only available to Staff members.")
        return
    
    embed = discord.Embed(
        title="🏛️ Ambassador Program - Staff Commands",
        description="All commands work in DMs or server channels",
        color=0x3498db
    )
    
    embed.add_field(
        name="👥 Ambassador Management",
        value="""
        `!ambassador add @user platforms` - Add new ambassador
        `!ambassador remove @user` - Remove ambassador
        
        **Example:** `!ambassador add @john YouTube, Instagram`
        """,
        inline=False
    )
    
    embed.add_field(
        name="📊 Reports & Analytics",
        value="""
        `!ambassadors report` - View current leaderboard
        `!ambassador-detail @user` - Detailed ambassador info
        `!ambassador-docs` - Sync report to Google Docs
        """,
        inline=False
    )
    
    embed.add_field(
        name="🔧 Administration",
        value="""
        `!ambassador-recover` - Recover data from Discord logs
        `!helpambassador` - Show this help (works in DM)
        """,
        inline=False
    )
    
    embed.add_field(
        name="💡 Tips",
        value="""
        • All commands work via DM to Jim
        • Ambassadors submit content by DMing Jim URLs or screenshots
        • Monthly goal: 50+ points to maintain status
        • Gemini Vision AI analyzes screenshots automatically
        """,
        inline=False
    )
    
    await ctx.send(embed=embed)

# Consolidated on_message handler - moved into BetaTestingBot class

async def handle_ambassador_submission(message, ambassador_data):
    """Handle ambassador post submissions"""
    try:
        discord_id, username, social_handles, platforms, joined_date, total_points, month_points, consecutive, tier, status = ambassador_data
        
        # Check for URLs in message
        url_pattern = r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?'
        urls = re.findall(url_pattern, message.content)
        
        # Check for attachments (screenshots)
        screenshots = [att for att in message.attachments if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        
        if not urls and not screenshots:
            embed = discord.Embed(
                title="📤 Ambassador Submission Help",
                description="To submit content for points, please include either:",
                color=0x3498db
            )
            embed.add_field(name="🔗 URL", value="Link to your post (preferred)", inline=False)
            embed.add_field(name="📸 Screenshot", value="Image of your post with visible engagement metrics", inline=False)
            await message.reply(embed=embed)
            return
        
        # Process URL submissions
        if urls:
            for url in urls:
                await process_url_submission(message, discord_id, url)
        
        # Process screenshot submissions  
        if screenshots:
            for screenshot in screenshots:
                await process_screenshot_submission(message, discord_id, screenshot)
                
    except Exception as e:
        print(f"❌ Error handling ambassador submission: {e}")
        await message.reply("❌ Error processing your submission. Please try again.")

async def process_url_submission(message, ambassador_id, url):
    """Process URL-based submission"""
    try:
        # Generate content hash for duplicate detection
        content_hash = bot.ambassador_program.generate_content_hash(message.content, url)
        
        # Check for duplicates
        is_duplicate = await bot.ambassador_program.check_duplicate_submission(content_hash, ambassador_id)
        
        if is_duplicate:
            await message.reply("⚠️ This post appears to be a duplicate. Each post can only be submitted once.")
            return
        
        # Determine platform and post type from URL
        platform, post_type = detect_platform_from_url(url)
        
        # For now, use basic engagement (would need API integration for real scraping)
        engagement = EngagementMetrics(likes=0, comments=0, shares=0, views=0)
        
        # Calculate points
        points = bot.ambassador_program.calculate_points(post_type, engagement)
        
        # Create submission
        submission = AmbassadorSubmission(
            ambassador_id=ambassador_id,
            platform=platform,
            post_type=post_type,
            url=url,
            screenshot_hash=None,
            engagement=engagement,
            content_preview=message.content[:100],
            timestamp=datetime.now(),
            points_awarded=points,
            is_duplicate=False,
            validity_status="accepted",
            gemini_analysis=None
        )
        
        # Store submission
        success = await bot.ambassador_program.store_submission(submission)
        
        if success:
            embed = discord.Embed(
                title="✅ Submission Accepted!",
                description=f"Your {platform.value.title()} {post_type.value.replace('_', ' ')} has been processed.",
                color=0x00ff00
            )
            embed.add_field(name="🎯 Points Awarded", value=f"{points} points", inline=True)
            embed.add_field(name="🔗 URL", value=url, inline=False)
            embed.add_field(name="💡 Note", value="Engagement metrics will be updated when available", inline=False)
            
            await message.reply(embed=embed)
        else:
            await message.reply("❌ Error storing your submission. Please try again.")
            
    except Exception as e:
        print(f"❌ Error processing URL submission: {e}")
        await message.reply("❌ Error processing your URL submission.")

async def process_screenshot_submission(message, ambassador_id, screenshot):
    """Process screenshot-based submission"""
    try:
        # Download screenshot
        screenshot_data = await screenshot.read()
        
        # Generate content hash
        content_hash = bot.ambassador_program.generate_content_hash(message.content, image_data=screenshot_data)
        
        # Check for duplicates
        is_duplicate = await bot.ambassador_program.check_duplicate_submission(content_hash, ambassador_id)
        
        if is_duplicate:
            await message.reply("⚠️ This screenshot appears to be a duplicate. Each post can only be submitted once.")
            return
        
        # Analyze with Gemini Vision
        analysis = await bot.ambassador_program.analyze_screenshot_with_gemini(
            screenshot_data, 
            f"Ambassador submission from {message.author.display_name}: {message.content}"
        )
        
        if "error" in analysis:
            await message.reply(f"❌ Error analyzing screenshot: {analysis['error']}")
            return
        
        # Extract data from analysis
        try:
            platform = Platform(analysis.get('platform', 'unknown'))
        except ValueError:
            platform = Platform.INSTAGRAM  # Default fallback
        
        try:
            post_type_str = analysis.get('post_type', 'post')
            if 'video' in post_type_str.lower():
                post_type = PostType.INSTAGRAM_REEL
            elif 'answer' in post_type_str.lower():
                post_type = PostType.QUORA_ANSWER
            else:
                post_type = PostType.INSTAGRAM_POST
        except:
            post_type = PostType.INSTAGRAM_POST
        
        # Extract engagement metrics
        engagement_data = analysis.get('engagement_metrics', {})
        engagement = EngagementMetrics(
            likes=engagement_data.get('likes', 0),
            comments=engagement_data.get('comments', 0),
            shares=engagement_data.get('shares', 0),
            views=engagement_data.get('views', 0),
            saves=engagement_data.get('saves', 0)
        )
        
        # Check authenticity
        authenticity = analysis.get('authenticity_check', {})
        is_authentic = authenticity.get('is_likely_authentic', True)
        quality_score = authenticity.get('quality_score', 5)
        
        validity_status = "accepted"
        if not is_authentic or quality_score < 3:
            validity_status = "flagged"
        
        # Calculate points
        points = bot.ambassador_program.calculate_points(post_type, engagement)
        if validity_status == "flagged":
            points = 0  # No points for flagged content
        
        # Create submission
        submission = AmbassadorSubmission(
            ambassador_id=ambassador_id,
            platform=platform,
            post_type=post_type,
            url=None,
            screenshot_hash=content_hash,
            engagement=engagement,
            content_preview=analysis.get('content_preview', message.content[:100]),
            timestamp=datetime.now(),
            points_awarded=points,
            is_duplicate=False,
            validity_status=validity_status,
            gemini_analysis=analysis
        )
        
        # Store submission
        success = await bot.ambassador_program.store_submission(submission)
        
        if success:
            if validity_status == "accepted":
                embed = discord.Embed(
                    title="✅ Screenshot Analyzed & Accepted!",
                    description=f"Your {platform.value.title()} {post_type.value.replace('_', ' ')} has been processed.",
                    color=0x00ff00
                )
                embed.add_field(name="🎯 Points Awarded", value=f"{points} points", inline=True)
                embed.add_field(name="📊 Engagement", value=f"👍 {engagement.likes} | 💬 {engagement.comments} | 🔄 {engagement.shares}", inline=True)
                embed.add_field(name="🤖 AI Analysis", value=analysis.get('content_preview', 'Content analyzed'), inline=False)
            else:
                embed = discord.Embed(
                    title="⚠️ Submission Flagged",
                    description="Your submission has been flagged for manual review.",
                    color=0xffa500
                )
                embed.add_field(name="🔍 Reason", value="Quality or authenticity concerns detected", inline=False)
                embed.add_field(name="📝 Next Steps", value="Staff will review and award points if valid", inline=False)
            
            await message.reply(embed=embed)
        else:
            await message.reply("❌ Error storing your submission. Please try again.")
            
    except Exception as e:
        print(f"❌ Error processing screenshot submission: {e}")
        await message.reply("❌ Error processing your screenshot submission.")

def detect_platform_from_url(url):
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
        return Platform.INSTAGRAM, PostType.INSTAGRAM_POST  # Default fallback

if __name__ == "__main__":
    # Load environment variables
    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not discord_token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    
    if not gemini_key:
        print("Error: GEMINI_API_KEY environment variable not set!")
        exit(1)
    
    bot.run(discord_token)
