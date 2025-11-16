# Archived Scripts

This directory contains legacy scripts that were used for one-time setup, migrations, or development testing. These are kept for historical reference but are no longer actively used.

## Archived Scripts

### One-Time Migration/Setup
- **migrate_sqlite_to_supabase.py** - One-time migration from SQLite to Supabase PostgreSQL (completed)
- **database_setup.py** - Legacy database setup script (now using `backend/migrations/` for schema management)
- **add_composite_indexes.py** - One-time script to add composite indexes (completed)

### Development Utilities
- **test_supabase_connection.py** - Connection testing utility (dev use only)
- **test_ufa_queries.py** - UFA API query testing utility (dev use only)

## Note

These scripts are archived because:
1. They were one-time operations that have been completed
2. The functionality has been replaced by better tooling (e.g., migrations)
3. They are development/testing utilities no longer actively used

If you need to reference historical setup procedures, these scripts provide insight into past operations.
