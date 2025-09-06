#!/usr/bin/env python3
"""
Backward compatibility test suite for the stats chat system.
Run this before and after changes to ensure queries still work correctly.
"""

import json
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Tuple

API_URL = "http://localhost:8000/api/query"

# Test cases: (query, expected_keywords_in_response)
TEST_CASES = [
    # Basic queries that should always work
    ("What teams are in the UFA?", ["Carolina", "Atlanta", "teams"]),
    ("Who are the top scorers this season?", ["goals", "assists"]),
    ("Who has the most blocks this season?", ["blocks"]),
    ("Who has the most assists in 2025?", ["assists", "2025"]),
    
    # Player-specific queries
    ("How many total yards does Austin Taylor have in 2025?", ["Austin Taylor", "yards"]),
    ("What are the top goal scorers all-time?", ["goals"]),
    
    # Team queries
    ("What is Atlanta Hustle's record in 2025?", ["Atlanta", "Hustle", "wins", "losses"]),
    ("Show me the standings for 2025", ["standing", "wins", "losses"]),
    
    # Complex queries
    ("Who has the best plus/minus in 2024?", ["plus", "minus", "2024"]),
    ("Which players have the most hucks completed this season?", ["hucks", "completed"]),
    
    # Critical semantic tests - ensure correct interpretation
    ("Who are the top goal scorers in the UFA?", ["375", "goals"]),  # Matt Smith has 375 goals
    ("Who are the top scorers in the UFA?", ["goals", "assists"]),  # Should include both
]

def test_query(query: str, expected_keywords: List[str], delay: float = 2.0) -> Tuple[bool, str]:
    """Test a single query and check if response contains expected keywords."""
    try:
        # Add delay to avoid rate limits
        time.sleep(delay)
        
        # Prepare request
        data = json.dumps({"query": query}).encode('utf-8')
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        # Make request
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 200:
                return False, f"HTTP {response.status}"
            
            response_data = json.loads(response.read().decode('utf-8'))
        
        answer = response_data.get("answer", "").lower()
        
        # Check for rate limit error
        if "429" in answer or "rate limit" in answer.lower():
            return False, "RATE_LIMITED"
        
        # Check for generic error
        if answer.startswith("i'm sorry, i encountered an error"):
            return False, "ERROR"
        
        # Check for expected keywords
        missing_keywords = []
        for keyword in expected_keywords:
            if keyword.lower() not in answer:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            return False, f"Missing: {', '.join(missing_keywords)}"
        
        return True, "OK"
        
    except Exception as e:
        return False, str(e)

def run_tests():
    """Run all test cases and report results."""
    print("=" * 80)
    print("BACKWARD COMPATIBILITY TEST SUITE")
    print("=" * 80)
    
    results = []
    rate_limited_count = 0
    
    for i, (query, expected) in enumerate(TEST_CASES, 1):
        print(f"\nTest {i}/{len(TEST_CASES)}: {query[:50]}...")
        
        # Increase delay if we've seen rate limits
        delay = 3.0 if rate_limited_count > 0 else 2.0
        
        success, message = test_query(query, expected, delay)
        
        if message == "RATE_LIMITED":
            rate_limited_count += 1
            print(f"  ⚠️  RATE LIMITED (waiting longer...)")
            # Wait longer and retry once
            time.sleep(10)
            success, message = test_query(query, expected, 0)
        
        if success:
            print(f"  ✅ PASS")
        else:
            print(f"  ❌ FAIL: {message}")
        
        results.append((query, success, message))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")
    
    if failed > 0:
        print("\nFailed Tests:")
        for query, success, message in results:
            if not success:
                print(f"  - {query[:60]}... ({message})")
    
    # Save results for comparison
    with open("test_results.json", "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "passed": passed,
            "failed": failed,
            "total": len(results),
            "results": [(q, s, m) for q, s, m in results]
        }, f, indent=2)
    
    print(f"\nResults saved to test_results.json")
    
    return passed == len(results)

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)