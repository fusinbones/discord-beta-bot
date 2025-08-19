#!/usr/bin/env python3
"""
Test the new Poshmark API implementation
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot import PoshmarkAnalyzer

async def test_new_poshmark():
    """Test the updated Poshmark scraping method"""
    
    # Create a minimal analyzer instance
    analyzer = PoshmarkAnalyzer()
    
    # Test with jle4518
    store_url = "https://poshmark.com/closet/jle4518"
    
    print("🔥 Testing NEW Poshmark API implementation")
    print(f"🎯 Target: {store_url}")
    print("-" * 50)
    
    result = await analyzer._poshmark_direct_api_scrape(store_url)
    
    print("-" * 50)
    print("📊 FINAL RESULT:")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Success!")
        print(f"   Username: {result.get('username', 'N/A')}")
        print(f"   Total Products: {result.get('total_products', 0)}")
        print(f"   API Requests: {result.get('requests_made', 0)}")
        print(f"   Method: {result.get('scrape_method', 'N/A')}")
        
        if result.get('products'):
            print(f"\n📦 Sample Product:")
            first_product = result['products'][0]
            print(f"   Title: {first_product.get('title', 'N/A')}")
            print(f"   Price: {first_product.get('price', 'N/A')}")
            print(f"   Brand: {first_product.get('brand', 'N/A')}")
            print(f"   Size: {first_product.get('size', 'N/A')}")
            print(f"   Category: {first_product.get('category', 'N/A')}")
    
    return result

if __name__ == "__main__":
    result = asyncio.run(test_new_poshmark())
    if "error" not in result:
        print("\n🎉 NEW POSHMARK API TEST PASSED! 🎉")
    else:
        print("\n💥 Test failed - need more debugging")
