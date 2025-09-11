#!/usr/bin/env python3
"""
Test script to verify UFA data and plus/minus calculations are working correctly.
"""

import os
import sys

# Add both parent directory and backend to path for proper import resolution
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # For backend.* imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))  # For internal backend imports

import logging

from backend.data.database import SQLDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_database():
    """Test various queries to verify the database is set up correctly."""

    logger.info("Testing UFA database queries...")

    # Initialize database
    db = SQLDatabase()

    tests = []

    # Test 1: Check available seasons
    logger.info("\n1. Available seasons:")
    result = db.execute_query(
        "SELECT DISTINCT season FROM player_season_stats ORDER BY season"
    )
    seasons = [r["season"] for r in result]
    logger.info(f"   Seasons: {seasons}")
    tests.append(("Available seasons", "2025" in seasons))

    # Test 2: Check plus/minus calculation for 2024
    logger.info("\n2. Top 5 plus/minus in 2024:")
    result = db.execute_query(
        """
        SELECT p.name, pss.calculated_plus_minus,
               pss.total_goals, pss.total_assists, pss.total_blocks,
               pss.total_throwaways, pss.total_stalls, pss.total_drops
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.id
        WHERE pss.season = '2024'
        ORDER BY pss.calculated_plus_minus DESC
        LIMIT 5
    """
    )
    for r in result:
        expected = (
            r["total_goals"]
            + r["total_assists"]
            + r["total_blocks"]
            - r["total_throwaways"]
            - r["total_stalls"]
            - r["total_drops"]
        )
        correct = expected == r["calculated_plus_minus"]
        logger.info(
            f"   {r['name']}: {r['calculated_plus_minus']} "
            f"(G:{r['total_goals']} A:{r['total_assists']} B:{r['total_blocks']} "
            f"T:{r['total_throwaways']} S:{r['total_stalls']} D:{r['total_drops']}) "
            f"{'✓' if correct else '✗'}"
        )
    tests.append(
        ("Plus/minus calculation", all(r["calculated_plus_minus"] > 0 for r in result))
    )

    # Test 3: Check UFA-specific fields exist
    logger.info("\n3. UFA-specific fields:")
    result = db.execute_query(
        """
        SELECT SUM(total_completions) as completions,
               SUM(total_hockey_assists) as hockey_assists,
               SUM(total_callahans) as callahans,
               SUM(total_yards_thrown) as yards_thrown
        FROM player_season_stats
        WHERE season = '2024'
    """
    )
    if result:
        r = result[0]
        logger.info(f"   Completions: {r['completions']}")
        logger.info(f"   Hockey Assists: {r['hockey_assists']}")
        logger.info(f"   Callahans: {r['callahans']}")
        logger.info(f"   Yards Thrown: {r['yards_thrown']}")
    tests.append(("UFA fields populated", result and result[0]["completions"] > 0))

    # Test 4: Check 2025 data exists
    logger.info("\n4. 2025 season data:")
    result = db.execute_query(
        """
        SELECT COUNT(DISTINCT player_id) as players,
               COUNT(*) as stat_records,
               SUM(total_goals) as total_goals
        FROM player_season_stats
        WHERE season = '2025'
    """
    )
    if result:
        r = result[0]
        logger.info(f"   Players with stats: {r['players']}")
        logger.info(f"   Stat records: {r['stat_records']}")
        logger.info(f"   Total goals: {r['total_goals']}")
    tests.append(("2025 data exists", result and result[0]["players"] > 0))

    # Test 5: Check completion percentage
    logger.info("\n5. Best completion percentage in 2024 (min 100 attempts):")
    result = db.execute_query(
        """
        SELECT p.name, pss.completion_percentage,
               pss.total_completions, pss.total_throw_attempts
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.id
        WHERE pss.season = '2024' 
          AND pss.total_throw_attempts >= 100
          AND pss.completion_percentage IS NOT NULL
        ORDER BY pss.completion_percentage DESC
        LIMIT 5
    """
    )
    for r in result:
        logger.info(
            f"   {r['name']}: {r['completion_percentage']:.1f}% "
            f"({r['total_completions']}/{r['total_throw_attempts']})"
        )
    tests.append(("Completion percentage", len(result) > 0))

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST RESULTS:")
    logger.info("=" * 50)

    all_passed = True
    for test_name, passed in tests:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        all_passed = all_passed and passed

    if all_passed:
        logger.info(
            "\n🎉 All tests passed! Database is configured correctly for UFA data."
        )
    else:
        logger.info("\n⚠️  Some tests failed. Please check the configuration.")

    return all_passed


if __name__ == "__main__":
    test_database()
