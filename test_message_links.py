#!/usr/bin/env python3
"""
Test the message linking feature for beta testing updates
"""
import sqlite3
from datetime import datetime, timedelta

def test_message_links():
    """Test if we can generate proper Discord message links from database data"""
    db_path = 'beta_testing.db'
    
    print(f"🔗 Testing message link generation...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get recent messages with all required fields
            time_ago = (datetime.now() - timedelta(hours=24)).isoformat()
            cursor.execute('''
                SELECT message_content, username, message_id, channel_id, guild_id, timestamp
                FROM messages 
                WHERE timestamp > ? AND message_content NOT LIKE '!%'
                AND message_id IS NOT NULL AND guild_id IS NOT NULL
                ORDER BY timestamp DESC 
                LIMIT 5
            ''', (time_ago,))
            
            recent_messages = cursor.fetchall()
            
            if recent_messages:
                print(f"✅ Found {len(recent_messages)} recent messages with link data:")
                print(f"")
                
                for i, (msg, user, msg_id, channel_id, guild_id, timestamp) in enumerate(recent_messages, 1):
                    # Truncate long messages
                    if len(msg) > 60:
                        msg = msg[:60] + "..."
                    
                    # Generate Discord message link
                    message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                    
                    print(f"  {i}. {user}: {msg}")
                    print(f"     🔗 Link: {message_link}")
                    print(f"     📅 Time: {timestamp}")
                    print(f"")
                
                # Show how this would look in a beta update
                print(f"📋 Example beta update format:")
                msg, user, msg_id, channel_id, guild_id, timestamp = recent_messages[0]
                if len(msg) > 40:
                    msg = msg[:40] + "..."
                message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                
                print(f"   • {user} mentioned [{msg}]({message_link}) during testing")
                print(f"   • Check out [{user}'s feedback]({message_link}) on the latest build")
                print(f"   • {user} reported [an issue]({message_link}) that needs attention")
                
            else:
                print(f"❌ No recent messages found with complete link data")
                print(f"💡 This might mean:")
                print(f"   - No recent messages in the last 24 hours")
                print(f"   - Messages were tracked before guild_id field was added")
                print(f"   - Bot needs to track new messages to populate link data")
                
            # Check total message count
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM messages WHERE message_id IS NOT NULL AND guild_id IS NOT NULL")
            linkable_messages = cursor.fetchone()[0]
            
            print(f"📊 Database stats:")
            print(f"   - Total messages: {total_messages}")
            print(f"   - Messages with link data: {linkable_messages}")
            print(f"   - Coverage: {(linkable_messages/total_messages*100):.1f}%" if total_messages > 0 else "   - Coverage: 0%")
                
    except Exception as e:
        print(f"❌ Error testing message links: {e}")

if __name__ == "__main__":
    test_message_links()
