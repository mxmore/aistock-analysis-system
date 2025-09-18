#!/usr/bin/env python3
"""
SearXNG Integration Test
Tests SearXNG connectivity with different approaches
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, backend_root)

from dotenv import load_dotenv
load_dotenv()

import httpx

class SearXNGTester:
    def __init__(self):
        self.searxng_url = os.getenv("SEARXNG_URL", "http://localhost:10000")

    async def test_basic_connectivity(self):
        """Test basic connectivity to SearXNG"""
        print("🔍 Testing basic SearXNG connectivity...")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.searxng_url}/")
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✅ SearXNG homepage is accessible")
                    return True
                else:
                    print(f"❌ SearXNG homepage returned: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False

    async def test_search_get(self):
        """Test search with GET request"""
        print("\n🔍 Testing search with GET request...")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.searxng_url}/search",
                    params={"q": "test", "format": "json"}
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✅ GET search successful")
                    return True
                else:
                    print(f"❌ GET search failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ GET search error: {str(e)}")
            return False

    async def test_search_post(self):
        """Test search with POST request"""
        print("\n🔍 Testing search with POST request...")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.searxng_url}/search",
                    data={"q": "test", "format": "json"}
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✅ POST search successful")
                    return True
                else:
                    print(f"❌ POST search failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ POST search error: {str(e)}")
            return False

    async def test_search_post_with_headers(self):
        """Test search with POST request and additional headers"""
        print("\n🔍 Testing search with POST request and headers...")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.searxng_url}/search",
                    data={"q": "test", "format": "json"},
                    headers={
                        "X-Forwarded-For": "127.0.0.1",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json"
                    }
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✅ POST search with headers successful")
                    print(f"Response preview: {response.text[:200]}...")
                    return True
                else:
                    print(f"❌ POST search with headers failed: {response.status_code}")
                    print(f"Response: {response.text[:200]}...")
                    return False
        except Exception as e:
            print(f"❌ POST search with headers error: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting SearXNG Comprehensive Test")
        print(f"URL: {self.searxng_url}")
        print("=" * 50)

        results = []

        results.append(await self.test_basic_connectivity())
        results.append(await self.test_search_get())
        results.append(await self.test_search_post())
        results.append(await self.test_search_post_with_headers())

        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)

        test_names = [
            "Basic Connectivity",
            "GET Search",
            "POST Search",
            "POST Search with Headers"
        ]

        for i, (name, result) in enumerate(zip(test_names, results)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{i+1}. {name}: {status}")

        successful_tests = sum(results)
        print(f"\nTotal: {successful_tests}/{len(results)} tests passed")

        if successful_tests > 0:
            print("🎉 SearXNG is working for some operations!")
        else:
            print("❌ All tests failed - SearXNG may not be running")

async def main():
    tester = SearXNGTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())