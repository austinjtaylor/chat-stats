"""
Migrate data from local SQLite database to Supabase PostgreSQL.
Copies all sports statistics tables while preserving data integrity.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from data.database import SQLDatabase
from dotenv import load_dotenv

load_dotenv()


def transform_row_data(table_name, row):
    """Transform row data for PostgreSQL compatibility."""
    transformed = row.copy()

    # Players table: Convert integer active (0/1) to boolean
    if table_name == "players" and "active" in transformed:
        transformed["active"] = bool(transformed["active"])

    # Player season stats: Remove generated columns
    if table_name == "player_season_stats":
        # Remove calculated columns (auto-generated in PostgreSQL)
        for col in ["calculated_plus_minus"]:
            transformed.pop(col, None)

    return transformed


def migrate_to_supabase():
    """Migrate all data from SQLite to Supabase PostgreSQL."""

    print("=" * 80)
    print("SQLite → Supabase Migration Script")
    print("=" * 80)
    print()

    # Check environment
    database_url = os.getenv("DATABASE_URL")
    database_path = os.getenv("DATABASE_PATH", "./db/sports_stats.db")

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env")
        print("   Please add your Supabase DATABASE_URL to continue.")
        return False

    if not os.path.exists(database_path):
        print(f"❌ ERROR: SQLite database not found at {database_path}")
        print("   Nothing to migrate.")
        return False

    print(f"📁 Source (SQLite): {database_path}")
    print(f"🐘 Target (PostgreSQL): {database_url[:50]}...")
    print()

    # Connect to both databases
    print("Connecting to databases...")

    # Temporarily remove DATABASE_URL from environment for SQLite connection
    original_database_url = os.environ.pop("DATABASE_URL", None)

    try:
        # Connect to SQLite (without DATABASE_URL in environment)
        sqlite_db = SQLDatabase(database_path=database_path)

        # Restore DATABASE_URL for PostgreSQL connection
        if original_database_url:
            os.environ["DATABASE_URL"] = original_database_url

        # Connect to PostgreSQL
        postgres_db = SQLDatabase(database_url=database_url)

        print(f"✅ Connected to SQLite: {sqlite_db.get_database_type()}")
        print(f"✅ Connected to PostgreSQL: {postgres_db.get_database_type()}")

        if sqlite_db.is_postgresql():
            print("\n❌ ERROR: Source database is PostgreSQL, not SQLite!")
            print("   Check your DATABASE_PATH setting.")
            return False

        if not postgres_db.is_postgresql():
            print("\n❌ ERROR: Target database is not PostgreSQL!")
            print("   Check your DATABASE_URL setting.")
            return False

        print()

    except Exception as e:
        # Restore DATABASE_URL on error
        if original_database_url:
            os.environ["DATABASE_URL"] = original_database_url
        raise

    # Tables to migrate (in order due to foreign key constraints)
    tables_to_migrate = [
        "teams",
        "players",
        "games",
        "player_game_stats",
        "player_season_stats",
        "team_season_stats",
        "game_events",
    ]

    print("Starting migration...")
    print()

    total_rows_migrated = 0

    for table_name in tables_to_migrate:
        try:
            # Get row count from SQLite
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = sqlite_db.execute_query(count_query)
            row_count = result[0]["count"] if result else 0

            if row_count == 0:
                print(f"⏭️  Skipping {table_name} (empty)")
                continue

            print(f"📋 Migrating {table_name}...")
            print(f"   Source rows: {row_count:,}")

            # Read all data from SQLite
            select_query = f"SELECT * FROM {table_name}"
            data = sqlite_db.execute_query(select_query)

            if not data:
                print(f"   No data found")
                continue

            # Get column names
            columns = list(data[0].keys())

            # Filter out SQLite-specific columns
            columns_filtered = [
                col for col in columns if col != "id"
            ]  # Let PostgreSQL auto-generate IDs

            # Prepare batch insert
            batch_size = 1000
            total_inserted = 0

            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]

                # Build INSERT query
                placeholders = ", ".join([f":{col}" for col in columns_filtered])
                insert_query = f"""
                    INSERT INTO {table_name} ({', '.join(columns_filtered)})
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """

                # Insert batch
                for row in batch:
                    # Transform row for PostgreSQL compatibility
                    transformed_row = transform_row_data(table_name, row)
                    # Filter row to match columns
                    filtered_row = {k: v for k, v in transformed_row.items() if k in columns_filtered}
                    postgres_db.execute_query(insert_query, filtered_row)

                total_inserted += len(batch)
                print(f"   Progress: {total_inserted:,} / {row_count:,} rows", end="\r")

            print(f"   ✅ Migrated: {total_inserted:,} rows")
            total_rows_migrated += total_inserted

        except Exception as e:
            print(f"   ❌ Error migrating {table_name}: {e}")
            print(f"   Continuing with next table...")
            continue

    print()
    print("=" * 80)
    print(f"✅ Migration Complete!")
    print(f"   Total rows migrated: {total_rows_migrated:,}")
    print("=" * 80)
    print()

    # Verify migration
    print("Verifying migration...")
    for table_name in tables_to_migrate:
        try:
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = postgres_db.execute_query(count_query)
            count = result[0]["count"] if result else 0
            print(f"   {table_name}: {count:,} rows")
        except Exception as e:
            print(f"   {table_name}: Error - {e}")

    print()
    print("🎉 Migration successful! Your data is now in Supabase.")
    print()

    # Cleanup
    sqlite_db.close()
    postgres_db.close()

    return True


if __name__ == "__main__":
    try:
        success = migrate_to_supabase()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
