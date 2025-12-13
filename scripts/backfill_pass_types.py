#!/usr/bin/env python3
"""
Backfill pass_type for existing game_events that have coordinate data.

This script uses efficient batch UPDATE statements with CASE expressions
to classify all passes at once in the database.

Usage:
    uv run python scripts/backfill_pass_types.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.data.database import SQLDatabase


def backfill_pass_types() -> None:
    """
    Reclassify pass_type for all game_events using SQL CASE expressions.
    This is much faster than individual updates.
    """
    db = SQLDatabase()

    # Count events that will be updated
    count_result = db.execute_query(
        """
        SELECT COUNT(*) as count
        FROM game_events
        WHERE event_type IN (18, 19)
        AND thrower_x IS NOT NULL
        AND thrower_y IS NOT NULL
        AND receiver_x IS NOT NULL
        AND receiver_y IS NOT NULL
        """
    )
    total_to_update = count_result[0]["count"] if count_result else 0
    print(f"Found {total_to_update} events to reclassify")

    print("Running batch UPDATE with classification logic...")

    # Use SQL CASE expressions to classify all passes at once
    # Classification rules (priority order):
    # 1. huck: vertical >= 40 (long forward)
    # 2. swing: horiz >= 10 AND primarily lateral (horiz > 2 * |vert|)
    # 3. gainer: vertical >= 4 (forward pass)
    # 4. dump: vertical < -4 (backward pass)
    # 5. dish: everything else
    db.execute_query(
        """
        UPDATE game_events
        SET pass_type = CASE
            WHEN (receiver_y - thrower_y) >= 40 THEN 'huck'
            WHEN ABS(receiver_x - thrower_x) >= 10
                 AND ABS(receiver_x - thrower_x) > 2 * ABS(receiver_y - thrower_y) THEN 'swing'
            WHEN (receiver_y - thrower_y) >= 4 THEN 'gainer'
            WHEN (receiver_y - thrower_y) < -4 THEN 'dump'
            ELSE 'dish'
        END
        WHERE event_type IN (18, 19)
        AND thrower_x IS NOT NULL
        AND thrower_y IS NOT NULL
        AND receiver_x IS NOT NULL
        AND receiver_y IS NOT NULL
        """
    )

    print("Batch UPDATE complete!")

    # Show distribution of pass types
    distribution = db.execute_query(
        """
        SELECT pass_type, COUNT(*) as count
        FROM game_events
        WHERE pass_type IS NOT NULL
        GROUP BY pass_type
        ORDER BY count DESC
        """
    )
    print("\nPass type distribution:")
    for row in distribution:
        print(f"  {row['pass_type']}: {row['count']}")


if __name__ == "__main__":
    backfill_pass_types()
