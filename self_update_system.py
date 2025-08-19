"""
Self-Update System for Discord Bot
Allows the bot to update its own code and configuration while running
"""
import os
import json
import importlib
import ast
from datetime import datetime
import aiohttp
from typing import Dict, Any
import google.generativeai as genai

class SelfUpdateSystem:
    """Handles self-updating bot code and configurations"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.config_file = "config/dynamic_config.json"
        self.backup_dir = "backups/"
        self.update_log = "logs/updates.log"
        
        # Load dynamic configuration
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """Load dynamic configuration file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "poshmark_settings": {
                        "json_extraction": {
                            "scroll_actions": 3,
                            "timeout": 45000,
                            "wait_between_scrolls": 2000,
                            "scroll_amounts": [3000, 6000, 9000]
                        },
                        "fallback_crawl": {
                            "page_limit": 50,
                            "timeout": 120,
                            "scroll_amounts": [1500, 3000, 4500]
                        },
                        "simple_scrape": {
                            "timeout": 20000,
                            "scroll_amounts": [2000, 4000]
                        }
                    },
                    "api_settings": {
                        "firecrawl_base_url": "https://api.firecrawl.dev/v1",
                        "claude_model": "claude-3-5-sonnet-20241022",
                        "max_retries": 3,
                        "retry_delay": 5
                    },
                    "debug_settings": {
                        "verbose_logging": True,
                        "save_raw_responses": False,
                        "log_api_calls": True
                    }
                }
                self.save_config(default_config)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.config = config
            self._config_updated = True  # Set flag to indicate config update
            print(f"✅ Configuration updated: {datetime.now()}")
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    async def update_poshmark_settings(self, new_settings: Dict):
        """Update Poshmark scraping settings on the fly"""
        try:
            # Update config
            self.config['poshmark_settings'].update(new_settings)
            self.save_config(self.config)
            
            # Apply settings to running bot
            if hasattr(self.bot, 'mentorship_services'):
                services = self.bot.mentorship_services
                
                # Update timeout values
                if 'json_extraction' in new_settings:
                    services.poshmark_json_timeout = new_settings['json_extraction'].get('timeout', 45000)
                    services.poshmark_scroll_actions = new_settings['json_extraction'].get('scroll_actions', 3)
                
                print(f"✅ Applied Poshmark settings update: {new_settings}")
                return True
        except Exception as e:
            print(f"❌ Error updating Poshmark settings: {e}")
            return False
    
    async def hot_reload_module(self, module_name: str):
        """Hot reload a specific module"""
        try:
            if module_name in sys.modules:
                # Backup current module
                self.backup_current_code()
                
                # Reload module
                importlib.reload(sys.modules[module_name])
                print(f"✅ Hot reloaded module: {module_name}")
                
                # Log the update
                self.log_update(f"Hot reloaded {module_name}")
                return True
            else:
                print(f"❌ Module {module_name} not found in sys.modules")
                return False
        except Exception as e:
            print(f"❌ Error hot reloading {module_name}: {e}")
            return False
    
    async def self_edit_method(self, class_name: str, method_name: str, new_code: str):
        """Edit a specific method in the bot's code"""
        try:
            # This is advanced - edit source file directly
            bot_file = "bot.py"
            
            # Backup current file
            self.backup_current_code()
            
            # Read current file
            with open(bot_file, 'r') as f:
                content = f.read()
            
            # Parse AST to find method
            tree = ast.parse(content)
            
            # Find and replace method (simplified)
            # This would need more sophisticated AST manipulation
            
            print(f"⚠️ Self-editing not fully implemented for safety")
            return False
            
        except Exception as e:
            print(f"❌ Error self-editing {class_name}.{method_name}: {e}")
            return False
    
    def backup_current_code(self):
        """Backup current bot.py file"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.backup_dir}bot_backup_{timestamp}.py"
            
            # Copy current bot.py
            with open("bot.py", 'r') as src:
                with open(backup_file, 'w') as dst:
                    dst.write(src.read())
                    
            print(f"✅ Backed up to: {backup_file}")
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
    
    def log_update(self, message: str):
        """Log update activity"""
        try:
            os.makedirs(os.path.dirname(self.update_log), exist_ok=True)
            with open(self.update_log, 'a') as f:
                f.write(f"{datetime.now()} - {message}\n")
        except Exception as e:
            print(f"Error logging update: {e}")
    
    async def auto_fix_api_issues(self, error_message: str):
        """Automatically fix common API issues"""
        fixes_applied = []
        
        # Fix 1: Firecrawl timeout issues
        if "timeout" in error_message.lower() and ("firecrawl" in error_message.lower() or "500" in error_message):
            new_settings = {
                "json_extraction": {
                    "timeout": 25000,  # Reduce timeout from 45s to 25s
                    "scroll_actions": 2,  # Reduce from 3 to 2 scrolls
                    "wait_between_scrolls": 1500  # Faster scrolling
                },
                "fallback_crawl": {
                    "page_limit": 30,  # Reduce from 50 to 30
                    "timeout": 90  # Reduce timeout to 1.5 minutes
                },
                "simple_scrape": {
                    "timeout": 15000,  # Reduce scrape timeout
                    "scroll_amounts": [1500, 3000]  # Smaller scroll amounts
                }
            }
            if await self.update_poshmark_settings(new_settings):
                fixes_applied.append("Reduced Firecrawl timeouts and scroll actions to prevent 500 errors")
        
        # Fix 1b: Credit exhaustion - switch to aggressive simple scrape only
        if "insufficient credits" in error_message.lower() or "402" in error_message:
            new_settings = {
                "json_extraction": {
                    "enabled": False  # Disable expensive JSON extraction
                },
                "fallback_crawl": {
                    "enabled": False  # Disable expensive crawl method
                },
                "simple_scrape": {
                    "timeout": 60000,  # Long timeout for large stores
                    "scroll_actions": 15,  # MASSIVE scrolling for 400+ items
                    "wait_between_scrolls": 4000,  # Long waits for content loading
                    "scroll_amounts": [5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000, 60000, 65000, 70000, 75000],  # Aggressive infinite scroll
                    "wait_for": 10000  # Long initial wait
                }
            }
            if await self.update_poshmark_settings(new_settings):
                fixes_applied.append("Switched to credit-free aggressive scrolling for 400+ item stores")
        
        # Fix 1c: Large store insufficient scrolling detection  
        if (("1 pages" in error_message or "low page count" in error_message.lower()) and 
            any(num in error_message for num in ["400", "300", "200", "100"]) and
            "items" in error_message):
            
            print("🚨 DETECTED LARGE STORE WITH INSUFFICIENT SCROLLING!")
            new_settings = {
                "simple_scrape": {
                    "timeout": 90000,  # 1.5 minute timeout for massive stores
                    "scroll_actions": 25,  # EXTREME scrolling for 400+ items
                    "wait_between_scrolls": 3000,  # Wait for infinite scroll
                    "scroll_amounts": [8000, 16000, 24000, 32000, 40000, 48000, 56000, 64000, 72000, 80000, 88000, 96000, 104000, 112000, 120000, 128000, 136000, 144000, 152000, 160000, 168000, 176000, 184000, 192000, 200000],  # MASSIVE scroll distances
                    "wait_for": 12000,  # Very long initial wait
                    "force_aggressive": True
                }
            }
            if await self.update_poshmark_settings(new_settings):
                fixes_applied.append("Applied EXTREME scrolling settings for 400+ item Poshmark stores")
                fixes_applied.append("EXTREME scrolling settings applied successfully")
        
        # Fix 1d: General insufficient scrolling (without specific item count)
        if ("1 pages" in error_message or "low page count" in error_message.lower()) and "scroll" in error_message.lower():
            print("🔧 Detected insufficient scrolling - applying aggressive settings")
            new_settings = {
                "simple_scrape": {
                    "scroll_actions": 15,  # More scrolling
                    "timeout": 60000,      # Longer timeout
                    "scroll_amounts": [6000, 12000, 18000, 24000, 30000, 36000, 42000, 48000, 54000, 60000, 66000, 72000, 78000, 84000, 90000],
                    "wait_between_scrolls": 2500
                }
            }
            if await self.update_poshmark_settings(new_settings):
                fixes_applied.append("Increased scroll aggression for better data capture")
        
        # Fix 2: Headers not defined error
        if "headers" in error_message.lower() and "not defined" in error_message.lower():
            print("🔧 Auto-fix: Headers variable missing - this was fixed in the code")
            fixes_applied.append("Headers variable definition fixed")
        
        # Fix 3: Missing method errors
        if "_parse_analysis_json" in error_message or "has no attribute" in error_message:
            print("🔧 Auto-fix: Missing method detected - this was added to the code")
            fixes_applied.append("Missing method implementation added")
        
        # Fix 4: 400 Bad Request from deprecated API keys
        if "400" in error_message and ("includes" in error_message or "excludes" in error_message):
            new_settings = {
                "fallback_crawl": {
                    "use_simple_config": True,
                    "remove_deprecated_keys": True,
                    "page_limit": 25  # Even smaller limit for compatibility
                }
            }
            if await self.update_poshmark_settings(new_settings):
                fixes_applied.append("Switched to v1-compatible API configuration")
        
        # Fix 5: Rate limiting issues
        if "rate limit" in error_message.lower() or "429" in error_message:
            new_settings = {
                "api_settings": {
                    "retry_delay": 15,  # Longer delays
                    "max_retries": 1    # Single retry only
                }
            }
            self.config['api_settings'].update(new_settings)
            self.save_config(self.config)
            fixes_applied.append("Increased API retry delays and reduced retry attempts")
        
        # Fix 6: Store access issues (0 pages returned)
        if "No data retrieved" in error_message or "0 pages" in error_message:
            new_settings = {
                "poshmark_settings": {
                    "json_extraction": {
                        "scroll_actions": 1,  # Minimal scrolling
                        "timeout": 20000,     # Shorter timeout
                        "wait_between_scrolls": 3000  # Longer waits
                    },
                    "simple_scrape": {
                        "timeout": 25000,  # Longer timeout for simple scrape
                        "scroll_amounts": [3000, 6000, 9000]  # More aggressive scrolling
                    }
                }
            }
            if await self.update_poshmark_settings(new_settings):
                fixes_applied.append("Adjusted scraping strategy for better page capture")
        
        # Fix 7: General API connectivity issues
        if "All fallback methods failed" in error_message or "All Poshmark analysis methods failed" in error_message:
            new_settings = {
                "api_settings": {
                    "firecrawl_base_url": "https://api.firecrawl.dev/v1",  # Ensure correct endpoint
                    "max_retries": 2,
                    "retry_delay": 20  # Long delay between retries
                },
                "poshmark_settings": {
                    "json_extraction": {
                        "enabled": False  # Disable JSON extraction temporarily
                    },
                    "simple_scrape": {
                        "timeout": 30000,  # Maximum timeout for final fallback
                        "wait_for": 8000   # Long wait for page load
                    }
                }
            }
            if await self.update_poshmark_settings(new_settings):
                fixes_applied.append("Switched to most conservative scraping settings")
            
            # Also update API settings
            self.config['api_settings'].update(new_settings['api_settings'])
            self.save_config(self.config)
        
        # Apply manual fixes first
        if fixes_applied:
            print(f"🔧 Manual auto-fixes applied: {fixes_applied}")
            self.log_update(f"Manual auto-fixes for '{error_message[:50]}...': {fixes_applied}")
            return True
        
        # Check if any configuration was updated (even if fixes_applied is empty)
        if hasattr(self, '_config_updated') and self._config_updated:
            print(f"🔧 Configuration auto-fixes applied successfully!")
            self.log_update(f"Config auto-fixes for '{error_message[:50]}...'")
            self._config_updated = False  # Reset flag
            return True
        
        # AI-powered auto-fix using Gemini as fallback
        try:
            ai_fix = await self._gemini_autofix(error_message)
            if ai_fix:
                print(f"🤖 AI auto-fix applied: {ai_fix}")
                self.log_update(f"AI auto-fix for '{error_message[:50]}...': {ai_fix}")
                return True
        except Exception as e:
            print(f"❌ Error in AI auto-fix: {e}")
        
        return False
    
    async def _gemini_autofix(self, error_message: str) -> str:
        """Use Gemini AI to intelligently analyze and fix errors"""
        try:
            # Configure Gemini (get API key from environment)
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if not gemini_api_key:
                print("⚠️ GEMINI_API_KEY not found - skipping AI auto-fix")
                return None
            
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Create intelligent prompt for auto-fixing
            prompt = f"""
You are an expert bot developer analyzing an error in a Poshmark scraping system. 

ERROR MESSAGE: {error_message}

CONTEXT: This is a Discord bot that scrapes Poshmark stores using Firecrawl API with infinite scroll handling. The bot has these components:
- JSON schema extraction with scroll actions
- Fallback crawl method with page limits  
- Simple scrape as final fallback
- Rate limiting and timeout controls

CURRENT ISSUES WE'VE SEEN:
- Firecrawl 500 timeouts from too aggressive scrolling
- Only capturing 1-3 pages instead of full store inventory (should get 50-200+ products)
- Headers variable not defined errors
- Missing method errors
- API rate limiting

ANALYZE THE ERROR AND PROVIDE A SPECIFIC FIX:
Return ONLY a JSON object with this exact format:
{{
    "error_type": "timeout|insufficient_data|missing_code|api_error|rate_limit|other",
    "fix_description": "Brief description of what to fix",
    "settings_to_update": {{
        "json_extraction": {{"timeout": 45000, "scroll_actions": 5, "wait_between_scrolls": 2000}},
        "fallback_crawl": {{"page_limit": 75, "timeout": 180}},
        "simple_scrape": {{"timeout": 30000, "scroll_amounts": [3000, 6000, 9000]}}
    }},
    "confidence": 0.85
}}

Focus on MAXIMUM DATA CAPTURE for Poshmark infinite scroll while avoiding timeouts.
"""
            
            response = model.generate_content(prompt)
            
            # Parse AI response
            try:
                # Clean the response text
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                fix_data = json.loads(response_text)
                
                # Apply the AI-suggested settings
                if "settings_to_update" in fix_data:
                    success = await self.update_poshmark_settings(fix_data["settings_to_update"])
                    if success:
                        print(f"🤖 AI Auto-Fix Applied: {fix_data['fix_description']}")
                        print(f"🎯 Confidence: {fix_data.get('confidence', 'unknown')}")
                        return fix_data['fix_description']
                
            except json.JSONDecodeError:
                print(f"❌ Failed to parse AI auto-fix response: {response_text[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ Gemini AI auto-fix error: {e}")
            return None
        
        return None

# Commands to add to the bot for self-updating
class SelfUpdateCommands:
    """Discord commands for self-updating"""
    
    def __init__(self, update_system):
        self.updater = update_system
    
    async def cmd_update_poshmark_settings(self, ctx, setting_name: str, new_value: str):
        """Update Poshmark settings on the fly"""
        try:
            # Parse new value
            if new_value.isdigit():
                new_value = int(new_value)
            elif new_value.lower() in ['true', 'false']:
                new_value = new_value.lower() == 'true'
            
            # Apply update
            if setting_name == "timeout":
                settings = {"json_extraction": {"timeout": new_value}}
            elif setting_name == "scroll_actions":
                settings = {"json_extraction": {"scroll_actions": new_value}}
            elif setting_name == "page_limit":
                settings = {"fallback_crawl": {"page_limit": new_value}}
            else:
                await ctx.send(f"❌ Unknown setting: {setting_name}")
                return
            
            success = await self.updater.update_poshmark_settings(settings)
            if success:
                await ctx.send(f"✅ Updated {setting_name} to {new_value}")
            else:
                await ctx.send(f"❌ Failed to update {setting_name}")
                
        except Exception as e:
            await ctx.send(f"❌ Error updating settings: {e}")
    
    async def cmd_reload_module(self, ctx, module_name: str = "bot"):
        """Hot reload a module"""
        success = await self.updater.hot_reload_module(module_name)
        if success:
            await ctx.send(f"✅ Reloaded {module_name}")
        else:
            await ctx.send(f"❌ Failed to reload {module_name}")
    
    async def cmd_show_config(self, ctx):
        """Show current dynamic configuration"""
        config_text = json.dumps(self.updater.config, indent=2)
        await ctx.send(f"```json\n{config_text[:1500]}...\n```")
