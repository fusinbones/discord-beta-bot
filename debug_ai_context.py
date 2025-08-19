#!/usr/bin/env python3
"""
Debug the AI context being sent for whatsnew command
"""
import sqlite3
from datetime import datetime, timedelta

def debug_ai_context():
    """Debug the exact context being sent to AI for whatsnew"""
    
    print("🔍 Debugging AI context for !whatsnew command...")
    print("=" * 60)
    
    crosslisting_channel_id = "1002197177562574909"  # From debug output
    channel_name = "crosslisting_beta"
    
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Get recent bug reports for this channel
        cursor.execute('''
            SELECT bug_description, username, status, timestamp, channel_id
            FROM bugs 
            WHERE timestamp > ? 
            AND channel_id = ?
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', ((datetime.now() - timedelta(days=7)).isoformat(), crosslisting_channel_id))
        recent_bugs = cursor.fetchall()
        
        # Get staff guidance
        cursor.execute('''
            SELECT DISTINCT message_content, username 
            FROM messages 
            WHERE timestamp > ? 
            AND is_staff_message = TRUE
            AND LENGTH(message_content) > 20
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        staff_guidance = cursor.fetchall()
        
        # Get recent messages with links (exact same query as whatsnew)
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
        ''', ((datetime.now() - timedelta(days=7)).isoformat(), crosslisting_channel_id))
        recent_messages = cursor.fetchall()
        
        # Get statistics
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
        ''', ((datetime.now() - timedelta(days=7)).isoformat(), crosslisting_channel_id))
        stats = cursor.fetchone()
    
    # Create AI summary context (exact same as in whatsnew)
    context = f"{channel_name} Beta Testing Activity (Last 7 Days):\n\n"
    
    if recent_bugs:
        context += "Bug Reports:\n"
        for bug, user, status, timestamp, channel_id in recent_bugs:
            context += f"- {bug} (by {user}, {status})\n"
        context += "\n"
    
    if staff_guidance:
        context += "Staff Guidance:\n"
        for msg, user in staff_guidance:
            context += f"- {user}: {msg[:100]}{'...' if len(msg) > 100 else ''}\n"
        context += "\n"
    
    if recent_messages:
        context += "Recent Messages (with source links):\n"
        for msg, user, timestamp, channel, screenshot_info, msg_id, guild_id in recent_messages:
            if len(msg) > 80:
                msg = msg[:80] + "..."
            # Create Discord message link if we have the required IDs
            if msg_id and guild_id and crosslisting_channel_id:
                message_link = f"https://discord.com/channels/{guild_id}/{crosslisting_channel_id}/{msg_id}"
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
    
    print("📋 FULL AI CONTEXT:")
    print("=" * 60)
    print(context)
    print("=" * 60)
    
    print(f"\n📊 Data Summary:")
    print(f"   • Recent bugs: {len(recent_bugs)}")
    print(f"   • Staff guidance: {len(staff_guidance)}")
    print(f"   • Recent messages: {len(recent_messages)}")
    print(f"   • Statistics: {stats}")
    
    if recent_messages:
        print(f"\n🔗 Sample Links Generated:")
        for i, (msg, user, timestamp, channel, screenshot_info, msg_id, guild_id) in enumerate(recent_messages[:3], 1):
            if msg_id and guild_id:
                link = f"https://discord.com/channels/{guild_id}/{crosslisting_channel_id}/{msg_id}"
                print(f"   {i}. {user}: {msg[:50]}... -> {link}")

if __name__ == "__main__":
    debug_ai_context()
