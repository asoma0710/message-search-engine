"""
Simple test script for the Message Search Engine API
Run this after starting the server with: python main.py
"""

import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_endpoint(name, url, params=None):
    """Test an API endpoint and display results"""
    try:
        print(f"\nTesting {name}...")
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✓ Success! Status: {response.status_code}")
            print(f"Response:")
            print(json.dumps(data, indent=2))
            return data
    except httpx.TimeoutException:
        print(f"⚠ Timeout - This is normal for the first search request")
        print("  (It's fetching all messages from the external API)")
        return None
    except httpx.HTTPError as e:
        print(f"✗ Error: {e}")
        return None

def main():
    print_section("Message Search Engine API - Test Suite")
    print(f"Testing API at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Health endpoint
    print_section("1. Health Check")
    test_endpoint("Health", f"{BASE_URL}/health")
    
    # Test 2: Root endpoint
    print_section("2. Root Endpoint")
    test_endpoint("Root", f"{BASE_URL}/")
    
    # Test 3: Search endpoint - Paris
    print_section("3. Search Endpoint - Query: 'paris'")
    print("⚠ Note: First request may take 10-30 seconds (fetching data)")
    search_data = test_endpoint(
        "Search (paris)", 
        f"{BASE_URL}/search",
        params={"q": "paris", "page": 1, "page_size": 5}
    )
    
    if search_data:
        print(f"\n📊 Search Summary:")
        print(f"   Total matches: {search_data.get('total', 0)}")
        print(f"   Response time: {search_data.get('response_time_ms', 0)} ms")
        print(f"   Items returned: {len(search_data.get('items', []))}")
        if search_data.get('items'):
            print(f"\n   First result:")
            first = search_data['items'][0]
            print(f"   - User: {first.get('user_name')}")
            print(f"   - Message: {first.get('message')[:80]}...")
    
    # Test 4: Search endpoint - Dinner (should be fast if cache is warm)
    print_section("4. Search Endpoint - Query: 'dinner' (Cached)")
    search_data2 = test_endpoint(
        "Search (dinner)", 
        f"{BASE_URL}/search",
        params={"q": "dinner", "page": 1, "page_size": 3}
    )
    
    if search_data2:
        print(f"\n📊 Search Summary:")
        print(f"   Total matches: {search_data2.get('total', 0)}")
        print(f"   Response time: {search_data2.get('response_time_ms', 0)} ms")
        if search_data2.get('response_time_ms', 0) < 100:
            print("   ✓ Response time is under 100ms!")
    
    print_section("Test Complete")
    print("\n💡 Tip: Use http://localhost:8000/docs for interactive API testing")
    print("💡 Tip: Use http://localhost:8000/redoc for alternative documentation")

if __name__ == "__main__":
    main()

