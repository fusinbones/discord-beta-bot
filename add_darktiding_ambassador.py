import sqlite3
from datetime import datetime

# Connect to the ambassador database
conn = sqlite3.connect('ambassador_program.db')
cursor = conn.cursor()

# Add darktiding as ambassador
# Note: Using a placeholder Discord ID - you'll need to get your actual Discord ID
discord_id = "REPLACE_WITH_YOUR_DISCORD_ID"  # Replace this with your actual Discord user ID
username = "darktiding"
social_handles = "darktiding"
target_platforms = "instagram,tiktok,youtube"
joined_date = datetime.now().isoformat()

# Insert ambassador record
cursor.execute('''
    INSERT OR REPLACE INTO ambassadors (
        discord_id, username, social_handles, target_platforms, 
        joined_date, total_points, current_month_points, 
        consecutive_months, reward_tier, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    discord_id, username, social_handles, target_platforms,
    joined_date, 0, 0, 0, 'none', 'active'
))

conn.commit()

# Verify the record was added
cursor.execute('SELECT * FROM ambassadors WHERE username = ?', (username,))
ambassador = cursor.fetchone()

if ambassador:
    print(f"✅ Ambassador {username} added successfully!")
    print(f"   Discord ID: {ambassador[0]}")
    print(f"   Username: {ambassador[1]}")
    print(f"   Status: {ambassador[9]}")
else:
    print("❌ Failed to add ambassador")

conn.close()
print("\n⚠️  IMPORTANT: Replace 'REPLACE_WITH_YOUR_DISCORD_ID' with your actual Discord user ID")
