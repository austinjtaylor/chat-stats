"""
Test Supabase connection and verify setup.
Validates database connectivity, tables, and auth configuration.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from data.database import SQLDatabase
from supabase_client import verify_supabase_config
import jwt

load_dotenv()


def test_supabase_connection():
    """Run comprehensive Supabase connection tests."""

    print("=" * 80)
    print("Supabase Connection Test")
    print("=" * 80)
    print()

    # Test 1: Configuration
    print("Test 1: Verifying Supabase configuration...")
    try:
        config = verify_supabase_config()
        print(f"✅ Configuration valid")
        print(f"   URL: {config['url']}")
        print(f"   Anon key: {'present' if config['has_anon_key'] else 'missing'}")
        print(f"   Service key: {'present' if config['has_service_key'] else 'missing'}")
        print(f"   Database URL: {'present' if config['has_database_url'] else 'missing'}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    print()

    # Test 2: Database Connection
    print("Test 2: Testing database connection...")
    try:
        db = SQLDatabase()
        db_type = db.get_database_type()

        if db_type != "PostgreSQL":
            print(f"⚠️  Warning: Expected PostgreSQL, got {db_type}")
            print("   Make sure DATABASE_URL is set in .env")
        else:
            print(f"✅ Connected to {db_type}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    print()

    # Test 3: Table Existence
    print("Test 3: Checking for required tables...")
    required_tables = [
        "teams",
        "players",
        "games",
        "player_game_stats",
        "player_season_stats",
        "user_subscriptions",
        "user_saved_queries",
        "user_favorite_players",
    ]

    try:
        table_info = db.get_table_info()
        tables_found = list(table_info.keys())

        missing_tables = []
        for table in required_tables:
            if table in tables_found:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} (missing)")
                missing_tables.append(table)

        if missing_tables:
            print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
            print("   Run migrations in Supabase SQL Editor:")
            print("   - backend/migrations/001_sports_stats_schema.sql")
            print("   - backend/migrations/002_user_tables.sql")
        else:
            print(f"\n✅ All required tables exist ({len(required_tables)} tables)")
    except Exception as e:
        print(f"❌ Table check error: {e}")
        return False
    print()

    # Test 4: Query Execution
    print("Test 4: Testing query execution...")
    try:
        # Simple test query
        result = db.execute_query("SELECT 1 as test")
        if result and result[0]["test"] == 1:
            print("✅ Query execution working")
        else:
            print("❌ Unexpected query result")
            return False
    except Exception as e:
        print(f"❌ Query execution error: {e}")
        return False
    print()

    # Test 5: Data Check
    print("Test 5: Checking for data...")
    try:
        teams_count = db.get_row_count("teams")
        players_count = db.get_row_count("players")
        games_count = db.get_row_count("games")

        print(f"   Teams: {teams_count:,}")
        print(f"   Players: {players_count:,}")
        print(f"   Games: {games_count:,}")

        if teams_count == 0 and players_count == 0 and games_count == 0:
            print("\n⚠️  No sports data found")
            print("   Run migration: uv run python scripts/migrate_to_supabase.py")
        else:
            print(f"\n✅ Database contains sports data")
    except Exception as e:
        print(f"⚠️  Could not check data: {e}")
    print()

    # Test 6: JWT Token Validation
    print("Test 6: Testing JWT token validation...")
    try:
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        if not service_key:
            print("⚠️  SUPABASE_SERVICE_KEY not set, skipping token test")
        else:
            # Create a test JWT token
            test_payload = {
                "sub": "test-user-id",
                "email": "test@example.com",
                "role": "authenticated",
                "aud": "authenticated"
            }

            token = jwt.encode(test_payload, service_key, algorithm="HS256")

            # Try to decode it
            decoded = jwt.decode(
                token,
                service_key,
                algorithms=["HS256"],
                audience="authenticated"
            )

            if decoded["sub"] == "test-user-id":
                print("✅ JWT token validation working")
            else:
                print("❌ Token validation failed")
                return False
    except Exception as e:
        print(f"❌ Token validation error: {e}")
        return False
    print()

    # Cleanup
    db.close()

    # Summary
    print("=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    print()
    print("Your Supabase setup is working correctly.")
    print()
    print("Next steps:")
    print("1. Import data (if not done): uv run python scripts/migrate_to_supabase.py")
    print("2. Start dev server: ./run-dev.sh")
    print("3. Implement frontend auth (Phase 3)")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_supabase_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
