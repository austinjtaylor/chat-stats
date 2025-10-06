#!/usr/bin/env python3
"""
Migrate all data from local SQLite database to Supabase PostgreSQL.
Run this via Railway: railway run uv run python scripts/migrate_sqlite_to_supabase.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate_table(sqlite_conn, postgres_conn, table_name, batch_size=10000):
    """Migrate a single table from SQLite to PostgreSQL."""
    print(f"\n📊 Migrating {table_name}...")
    print("=" * 60)

    # Get count from SQLite
    sqlite_count = sqlite_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
    print(f"  SQLite records: {sqlite_count:,}")

    if sqlite_count == 0:
        print(f"  ⏭️  Skipping {table_name} (no data)")
        return

    # Check if table is already fully migrated
    postgres_count = postgres_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
    if postgres_count == sqlite_count:
        print(f"  ✅ Already migrated: {postgres_count:,} records")
        return postgres_count
    elif postgres_count > 0:
        print(f"  ⚠️  Partial migration detected: {postgres_count:,}/{sqlite_count:,} - continuing from where we left off")

    # Get column names (excluding auto-increment ids and generated columns)
    columns_result = sqlite_conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()

    # Exclude id column and known generated columns
    excluded_columns = {'id', 'calculated_plus_minus', 'completion_percentage'}
    columns = [col[1] for col in columns_result if col[1] not in excluded_columns]

    columns_str = ', '.join(columns)
    placeholders = ', '.join([f':{col}' for col in columns])

    # Build INSERT query with ON CONFLICT handling
    if table_name in ['teams', 'players', 'games']:
        # These tables have composite primary keys
        if table_name == 'teams':
            conflict_cols = 'team_id, year'
        elif table_name == 'players':
            conflict_cols = 'player_id, team_id, year'  # PostgreSQL uses 3-column unique constraint
        elif table_name == 'games':
            conflict_cols = 'game_id'
        else:
            conflict_cols = columns[0]  # fallback

        insert_query = f"""
        INSERT INTO {table_name} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_cols}) DO NOTHING
        """
    else:
        # Other tables - just ignore conflicts
        insert_query = f"""
        INSERT INTO {table_name} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
        """

    # Fetch and insert in batches
    offset = 0
    total_inserted = 0

    while offset < sqlite_count:
        # Fetch batch from SQLite
        select_query = f"SELECT {columns_str} FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
        rows = sqlite_conn.execute(text(select_query)).fetchall()

        if not rows:
            break

        # Convert rows to list of dicts
        batch_data = []
        # Get column info for type checking
        col_info = {col[1]: col[2] for col in columns_result}

        # Columns that should be boolean in PostgreSQL
        boolean_columns = {'active'}

        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                # Convert empty strings to None for INTEGER columns
                if value == '' and col_info.get(col) == 'INTEGER':
                    value = None
                # Convert INTEGER (0/1) to BOOLEAN for boolean columns
                elif col in boolean_columns and isinstance(value, int):
                    value = bool(value)
                row_dict[col] = value
            batch_data.append(row_dict)

        # Insert batch into PostgreSQL
        try:
            postgres_conn.execute(text(insert_query), batch_data)
            total_inserted += len(batch_data)

            # Commit every 50,000 records or at the end
            if (offset + len(batch_data)) % 50000 < batch_size or offset + len(batch_data) >= sqlite_count:
                postgres_conn.commit()
                print(f"  ✅ Committed batch {offset:,} - {offset+len(batch_data):,} ({total_inserted:,}/{sqlite_count:,})")
            else:
                print(f"  📝 Inserted batch {offset:,} - {offset+len(batch_data):,} ({total_inserted:,}/{sqlite_count:,})")
        except Exception as e:
            print(f"  ⚠️  Error inserting batch at offset {offset}: {str(e)[:200]}")
            postgres_conn.rollback()

        offset += batch_size

    # Verify count
    postgres_count = postgres_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
    print(f"  ✅ PostgreSQL records: {postgres_count:,}")

    return postgres_count

def main():
    """Main migration function."""
    print("🚀 Starting SQLite to Supabase Migration")
    print("=" * 60)

    # Connect to SQLite (local file - will be uploaded with script)
    sqlite_db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'sports_stats.db')
    print(f"📁 SQLite database: {sqlite_db_path}")

    if not os.path.exists(sqlite_db_path):
        print(f"❌ SQLite database not found at {sqlite_db_path}")
        print("   Make sure to run this script from the project root")
        sys.exit(1)

    sqlite_engine = create_engine(f'sqlite:///{sqlite_db_path}')

    # Connect to PostgreSQL (Supabase)
    postgres_url = os.getenv('DATABASE_URL')
    if not postgres_url:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)

    print(f"🐘 PostgreSQL database: {postgres_url.split('@')[1].split('/')[0]}")
    postgres_engine = create_engine(postgres_url)

    # Tables to migrate (in order due to foreign key constraints)
    tables = [
        'teams',
        'players',
        'games',
        'player_season_stats',
        'player_game_stats',
        'game_events'
    ]

    with sqlite_engine.connect() as sqlite_conn, postgres_engine.connect() as postgres_conn:
        total_stats = {}
        for table in tables:
            count = migrate_table(sqlite_conn, postgres_conn, table)
            total_stats[table] = count

    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
    for table, count in total_stats.items():
        print(f"  {table:25} {count:,}" if count else f"  {table:25} skipped")

    print("\n📝 Next steps:")
    print("  1. Run scripts/composite_indexes.sql in Supabase SQL Editor")
    print("  2. Run scripts/create_career_stats_view.sql in Supabase SQL Editor")
    print("  3. Refresh the materialized view:")
    print("     REFRESH MATERIALIZED VIEW player_career_stats;")

if __name__ == "__main__":
    main()
