"""
Smart sync system for Discord bot to catch up on missed !bug commands
"""
import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import asyncio

@commands.command(name='sync')
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
                            processed = await process_missed_bug_command(ctx.bot, message)
                            if processed:
                                synced_bugs += 1
                                
                except discord.Forbidden:
                    continue  # Skip channels we can't access
                except Exception as e:
                    print(f"Error syncing channel {channel.name}: {e}")
                    continue
        
        # Check for deleted bug reports in database vs Discord
        removed_bugs = await check_for_deleted_bug_reports(ctx.bot)
        
        embed = discord.Embed(
            title="🔄 Smart Sync Complete",
            description=f"Processed last {hours} hours of chat history",
            color=0x00ff00
        )
        embed.add_field(name="📝 Bugs Synced", value=str(synced_bugs), inline=True)
        embed.add_field(name="🗑️ Removed Entries", value=str(removed_bugs), inline=True)
        embed.add_field(name="📊 Status", value="✅ Complete", inline=True)
        
        await ctx.send(embed=embed)
        print(f"✅ Sync complete: {synced_bugs} bugs processed, {removed_bugs} removed entries cleaned")
        
    except Exception as e:
        await ctx.send(f"❌ Error during sync: {e}")
        print(f"❌ Error in sync_missed_bug_reports: {e}")

async def process_missed_bug_command(bot, message):
    """Process a missed !bug command and add to sheets if not already there"""
    try:
        # Extract bug description from command
        bug_description = message.content[5:].strip()  # Remove "!bug "
        if not bug_description:
            return False
            
        # Check if this bug is already in our database
        with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bug_id FROM bugs 
                WHERE user_id = ? AND bug_description LIKE ? AND timestamp >= ?
            ''', (
                str(message.author.id),
                f"%{bug_description[:50]}%",  # Match first 50 chars
                (message.created_at - timedelta(minutes=5)).isoformat()  # 5 min window
            ))
            
            if cursor.fetchone():
                return False  # Already processed
        
        # Add to database
        def db_operation():
            with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
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
        
        # Add to Google Sheets
        bug_data = {
            'bug_id': bug_id,
            'username': message.author.display_name,
            'description': bug_description,
            'timestamp': message.created_at.isoformat(),
            'status': 'open',
            'channel_id': str(message.channel.id),
            'guild_id': str(message.guild.id) if message.guild else '',
            'added_by': message.author.display_name
        }
        
        asyncio.create_task(bot.sheets_manager.add_bug_to_sheet(bug_data))
        print(f"📝 Synced missed bug #{bug_id} from {message.author.display_name}")
        return True
        
    except Exception as e:
        print(f"Error processing missed bug command: {e}")
        return False

async def check_for_deleted_bug_reports(bot):
    """Check for bug reports that were deleted from Discord and mark them accordingly"""
    removed_count = 0
    
    try:
        # Get recent bug reports from database
        with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bug_id, channel_id, timestamp, bug_description 
                FROM bugs 
                WHERE timestamp >= ? AND status != 'deleted' AND status != 'potentially_deleted'
            ''', ((datetime.now() - timedelta(hours=48)).isoformat(),))
            
            bugs_to_check = cursor.fetchall()
        
        for bug_id, channel_id, timestamp, description in bugs_to_check:
            try:
                # Try to find the original message
                channel = bot.get_channel(int(channel_id))
                if not channel:
                    continue
                    
                # Search for the bug command in recent messages
                cutoff_time = datetime.fromisoformat(timestamp) - timedelta(minutes=5)
                message_found = False
                
                async for message in channel.history(after=cutoff_time, limit=100):
                    if (message.content.startswith('!bug ') and 
                        description.replace('[AUTO-DETECTED] ', '') in message.content):
                        message_found = True
                        break
                
                # If message not found, it might have been deleted
                if not message_found:
                    # Mark as potentially deleted (don't remove, just flag)
                    def update_db():
                        with sqlite3.connect('beta_testing.db', timeout=30.0) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE bugs SET status = 'potentially_deleted' 
                                WHERE bug_id = ?
                            ''', (bug_id,))
                            conn.commit()
                    
                    await asyncio.get_event_loop().run_in_executor(None, update_db)
                    removed_count += 1
                    print(f"🗑️ Marked bug #{bug_id} as potentially deleted")
                    
            except Exception as e:
                print(f"Error checking bug {bug_id}: {e}")
                continue
                
    except Exception as e:
        print(f"Error in check_for_deleted_bug_reports: {e}")
        
    return removed_count

def setup(bot):
    """Setup function for the cog"""
    bot.add_command(sync_missed_bugs)
