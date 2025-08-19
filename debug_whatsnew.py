#!/usr/bin/env python3
"""
Debug the whatsnew command to see what data is being retrieved
"""
import sqlite3
from datetime import datetime, timedelta

def debug_whatsnew_data():
    """Debug what data the whatsnew command is actually getting"""
    
    print("🔍 Debugging !whatsnew command data retrieval...")
    print("=" * 60)
    
    # Get crosslisting-beta channel ID (you'll need to replace this with actual ID)
    # For now, let's see what channels we have
    with sqlite3.connect('beta_testing.db') as conn:
        cursor = conn.cursor()
        
        # Check what channels we have messages from
        print("📊 Available Channels:")
        cursor.execute('''
            SELECT DISTINCT channel_id, channel_name, COUNT(*) as message_count
            FROM messages 
            WHERE timestamp > ?
            GROUP BY channel_id, channel_name
            ORDER BY message_count DESC
        ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        
        channels = cursor.fetchall()
        for channel_id, channel_name, count in channels:
            print(f"   • {channel_name}: {count} messages (ID: {channel_id})")
        
        print("\n" + "=" * 60)
        
        # Find crosslisting-beta channel ID
        crosslisting_channel_id = None
        for channel_id, channel_name, count in channels:
            if 'crosslisting' in channel_name.lower():
                crosslisting_channel_id = channel_id
                print(f"🎯 Found crosslisting channel: {channel_name} (ID: {channel_id})")
                break
        
        if not crosslisting_channel_id:
            print("❌ Could not find crosslisting-beta channel ID")
            return
            
        print(f"\n🔍 Testing whatsnew query for channel: {crosslisting_channel_id}")
        print("=" * 60)
        
        # Test the exact query used in whatsnew
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
            LIMIT 10
        ''', ((datetime.now() - timedelta(days=7)).isoformat(), crosslisting_channel_id))
        
        recent_messages = cursor.fetchall()
        
        print(f"📋 Found {len(recent_messages)} matching messages:")
        print("-" * 40)
        
        for i, (msg, user, timestamp, channel, screenshot_info, msg_id, guild_id) in enumerate(recent_messages, 1):
            print(f"{i}. User: {user}")
            print(f"   Message: {msg[:100]}{'...' if len(msg) > 100 else ''}")
            print(f"   Channel: {channel}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Message ID: {msg_id}")
            print(f"   Guild ID: {guild_id}")
            print(f"   Screenshot: {screenshot_info}")
            
            # Test link generation
            if msg_id and guild_id and crosslisting_channel_id:
                link = f"https://discord.com/channels/{guild_id}/{crosslisting_channel_id}/{msg_id}"
                print(f"   🔗 Generated Link: {link}")
            else:
                print(f"   ❌ Cannot generate link - missing data")
            print("-" * 40)
        
        if not recent_messages:
            print("❌ No messages found matching the criteria!")
            print("\n🔍 Let's check what messages exist in this channel:")
            
            cursor.execute('''
                SELECT message_content, username, timestamp, message_id, guild_id
                FROM messages 
                WHERE timestamp > ? 
                AND channel_id = ?
                AND message_content NOT LIKE '!%'
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', ((datetime.now() - timedelta(days=7)).isoformat(), crosslisting_channel_id))
            
            all_messages = cursor.fetchall()
            print(f"📋 Found {len(all_messages)} total messages (without keyword filtering):")
            
            for i, (msg, user, timestamp, msg_id, guild_id) in enumerate(all_messages, 1):
                print(f"{i}. {user}: {msg[:80]}{'...' if len(msg) > 80 else ''}")
                print(f"   Link data: msg_id={msg_id}, guild_id={guild_id}")
        
        print("\n" + "=" * 60)
        print("🔍 Checking message statistics query...")
        
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
        print(f"📊 Statistics: {stats[0]} messages, {stats[1]} users")

if __name__ == "__main__":
    debug_whatsnew_data()
