#!/usr/bin/env python3
"""
Quick test to verify Poshmark direct API functionality
"""
import asyncio
import aiohttp
import json

async def test_poshmark_api():
    """Test direct Poshmark API access with different endpoint formats"""
    username = "jle4518"  # Known to exist
    
    # Try different endpoint variations
    api_variations = [
        f"https://poshmark.com/vm-rest/users/{username}/closet?limit=48&offset=0",
        f"https://poshmark.com/api/v1/users/{username}/closet?limit=48&offset=0", 
        f"https://poshmark.com/vm-rest/users/{username}/listings?limit=48&offset=0",
        f"https://poshmark.com/closet/{username}?format=json",
        f"https://poshmark.com/vm-rest/closets/{username}?limit=48&offset=0"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": f"https://poshmark.com/closet/{username}",
        "Origin": "https://poshmark.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors", 
        "Sec-Fetch-Site": "same-origin"
    }
    
    async with aiohttp.ClientSession() as session:
        for i, api_url in enumerate(api_variations, 1):
            try:
                print(f"\n🔥 Test {i}: {api_url}")
                
                async with session.get(api_url, headers=headers) as response:
                    print(f"📊 Status: {response.status}")
                    print(f"📊 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print(f"📋 Response keys: {list(data.keys()) if data else 'None'}")
                            
                            if 'error' in data:
                                error = data['error']
                                print(f"❌ API Error: {error}")
                                if isinstance(error, dict):
                                    print(f"   Status Code: {error.get('statusCode')}")
                                    print(f"   Error Type: {error.get('errorType')}")
                            
                            if 'data' in data and data['data']:
                                print(f"✅ SUCCESS! Found data structure")
                                products = data['data'].get('products', [])
                                if products:
                                    print(f"🎉 Found {len(products)} products!")
                                    return True
                                    
                        except json.JSONDecodeError:
                            text = await response.text()
                            print(f"📄 HTML Response (first 200 chars): {text[:200]}")
                    else:
                        print(f"❌ Failed: {response.status}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # If all API endpoints fail, try to scrape the HTML page directly
        print(f"\n🌐 Testing HTML page access:")
        page_url = f"https://poshmark.com/closet/{username}"
        async with session.get(page_url, headers=headers) as response:
            print(f"📊 HTML Status: {response.status}")
            if response.status == 200:
                html = await response.text()
                print(f"✅ HTML page loads successfully ({len(html)} chars)")
                # Look for JSON data in the HTML
                if '"products"' in html:
                    print("🔍 Found 'products' in HTML - data is embedded!")
                return False
    
    return False

if __name__ == "__main__":
    result = asyncio.run(test_poshmark_api())
    if result:
        print("\n🎉 Poshmark API test PASSED!")
    else:
        print("\n💥 Poshmark API test FAILED!")
