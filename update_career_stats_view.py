#!/usr/bin/env python3
"""
Quick script to update the player_career_stats materialized view with new columns.
Run this after making changes to scripts/create_career_stats_view.sql
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_career_stats_view():
    """Drop and recreate the player_career_stats materialized view."""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        sys.exit(1)

    print("🔄 Connecting to database...")
    engine = create_engine(database_url)

    # Read the SQL script
    sql_file = Path(__file__).parent / "scripts" / "create_career_stats_view.sql"
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        sys.exit(1)

    with open(sql_file, 'r') as f:
        sql_script = f.read()

    try:
        with engine.connect() as conn:
            # Drop existing view
            print("🗑️  Dropping existing materialized view...")
            conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS player_career_stats CASCADE"))
            conn.commit()

            # Create new view with updated schema
            print("✨ Creating updated materialized view...")
            conn.execute(text(sql_script))
            conn.commit()

            print("✅ Successfully updated player_career_stats materialized view!")
            print("   The view now includes:")
            print("   - yards_per_completion (Y/C)")
            print("   - yards_per_reception (Y/R)")
            print("   - assists_per_turnover (AST/TO)")

    except Exception as e:
        print(f"❌ Error updating materialized view: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_career_stats_view()
