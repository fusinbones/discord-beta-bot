#!/usr/bin/env python3
"""
Fix Existing Duplicates in Ambassador Submissions
This script identifies and marks duplicate submissions that were created before the fix
"""

import os
import asyncio
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

async def mark_existing_duplicates():
    """Find and mark duplicate submissions in the database"""
    
    print("🔍 Scanning for duplicate submissions...")
    
    # Connect to Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Get all submissions
    result = supabase.table('submissions').select('*').order('timestamp').execute()
    all_submissions = result.data
    
    print(f"📊 Total submissions found: {len(all_submissions)}")
    
    # Track seen content by ambassador
    seen_content = {}  # {ambassador_id: {hash: submission_id}}
    duplicates_found = 0
    
    for submission in all_submissions:
        ambassador_id = submission.get('ambassador_id')
        url = submission.get('url', '')
        original_discord_url = submission.get('original_discord_url', '')
        submission_id = submission.get('id')
        
        # Generate proper hash (without message.id)
        if url and not url.startswith('http'):
            # This is a stored image URL, use original if available
            url_to_hash = original_discord_url if original_discord_url else url
        else:
            url_to_hash = url
        
        # Create hash based on ambassador + URL only (proper way)
        content_hash = hashlib.md5(f"{ambassador_id}_{url_to_hash}".encode()).hexdigest()
        
        if ambassador_id not in seen_content:
            seen_content[ambassador_id] = {}
        
        # Check if we've seen this content before for this ambassador
        if content_hash in seen_content[ambassador_id]:
            # This is a duplicate!
            first_submission_id = seen_content[ambassador_id][content_hash]
            
            # Only mark as duplicate if it's not already marked
            if not submission.get('is_duplicate', False):
                print(f"🔍 Found duplicate:")
                print(f"   Ambassador: {ambassador_id}")
                print(f"   URL: {url_to_hash[:60]}...")
                print(f"   Original submission ID: {first_submission_id}")
                print(f"   Duplicate submission ID: {submission_id}")
                
                # Mark as duplicate and set points to 0
                supabase.table('submissions').update({
                    'is_duplicate': True,
                    'points_awarded': 0,
                    'validity_status': 'rejected'
                }).eq('id', submission_id).execute()
                
                duplicates_found += 1
        else:
            # First time seeing this content for this ambassador
            seen_content[ambassador_id][content_hash] = submission_id
    
    print(f"\n✅ Cleanup complete!")
    print(f"📊 Marked {duplicates_found} duplicates")
    print(f"💡 Next step: Restart Jim so the points audit can recalculate correct totals")

if __name__ == "__main__":
    asyncio.run(mark_existing_duplicates())
