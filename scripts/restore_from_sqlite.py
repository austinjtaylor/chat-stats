#!/usr/bin/env python3
"""
Restore PostgreSQL database from SQLite backup.
"""

import os
import sqlite3
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch

load_dotenv()

SQLITE_PATH = "/Users/austintaylor/Documents/Projects/chat-stats/backups/sports_stats_20251002_221730.db"

# Tables to restore in order (respecting foreign keys)
TABLES = [
    "teams",
    "players",
    "games",
    "game_events",
    "player_game_stats",
    "player_season_stats",
    "team_season_stats",
]


def get_postgres_connection():
    """Get PostgreSQL connection."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url)


def get_sqlite_connection():
    """Get SQLite connection."""
    return sqlite3.connect(SQLITE_PATH)


def get_table_columns(sqlite_cursor, table_name):
    """Get column names for a table."""
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in sqlite_cursor.fetchall()]


def restore_table(sqlite_conn, pg_conn, table_name):
    """Restore a single table from SQLite to PostgreSQL."""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Get columns
    columns = get_table_columns(sqlite_cursor, table_name)

    # Skip columns that don't exist in PostgreSQL or are auto-generated
    skip_columns = {'id', 'created_at', 'updated_at'}
    columns = [c for c in columns if c not in skip_columns]

    if not columns:
        print(f"  Skipping {table_name} - no columns to restore")
        return 0

    # Fetch all data from SQLite
    col_list = ", ".join(columns)
    sqlite_cursor.execute(f"SELECT {col_list} FROM {table_name}")
    rows = sqlite_cursor.fetchall()

    if not rows:
        print(f"  {table_name}: 0 rows (empty)")
        return 0

    # Clear existing data in PostgreSQL
    pg_cursor.execute(f"DELETE FROM {table_name}")

    # Insert into PostgreSQL
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    # Convert rows to list of tuples (handle None values)
    data = [tuple(row) for row in rows]

    execute_batch(pg_cursor, insert_sql, data, page_size=1000)
    pg_conn.commit()

    print(f"  {table_name}: {len(rows)} rows restored")
    return len(rows)


def main():
    print("Restoring PostgreSQL database from SQLite backup...")
    print(f"Source: {SQLITE_PATH}\n")

    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()

    total_rows = 0

    for table in TABLES:
        try:
            rows = restore_table(sqlite_conn, pg_conn, table)
            total_rows += rows
        except Exception as e:
            print(f"  ERROR restoring {table}: {e}")
            pg_conn.rollback()

    sqlite_conn.close()
    pg_conn.close()

    print(f"\nTotal rows restored: {total_rows}")
    print("Done!")


if __name__ == "__main__":
    main()
