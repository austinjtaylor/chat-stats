"""
SQL Database connection and query execution module for Sports Stats Chatbot.
Supports both SQLite (local dev) and PostgreSQL (Supabase production).
"""

import os
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, NullPool


class SQLDatabase:
    """Manages SQL database connections and query execution for sports statistics."""

    def __init__(self, database_path: str = None, database_url: str = None):
        """
        Initialize SQL database connection.
        Supports both SQLite (local) and PostgreSQL (Supabase).

        Args:
            database_path: Path to SQLite database file (for local dev)
            database_url: PostgreSQL connection URL (for Supabase/production)

        Environment Variables:
            DATABASE_URL: PostgreSQL URL (takes precedence)
            DATABASE_PATH: SQLite file path (fallback)
        """
        # Check for Supabase/PostgreSQL first
        self.database_url = database_url or os.getenv("DATABASE_URL")

        if self.database_url:
            # Use PostgreSQL (Supabase)
            self._use_postgresql = True
            print(f"🐘 Using PostgreSQL database (Supabase)")

            # Create PostgreSQL engine
            self.engine = create_engine(
                self.database_url,
                poolclass=NullPool,  # Let Supabase handle connection pooling
                echo=False,  # Set to True for SQL query debugging
            )
        else:
            # Use SQLite (local development)
            self._use_postgresql = False

            if database_path is None:
                database_path = os.getenv("DATABASE_PATH") or os.path.join(
                    os.path.dirname(__file__), "..", "..", "db", "sports_stats.db"
                )

            print(f"📁 Using SQLite database: {database_path}")

            # Ensure database directory exists
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

            # Create SQLite engine
            self.engine = create_engine(
                f"sqlite:///{database_path}",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Store metadata
        self.metadata = MetaData()

        # Initialize database schema if needed (SQLite only)
        if not self._use_postgresql:
            self._initialize_database()

    def _initialize_database(self):
        """Initialize database with schema if tables don't exist."""
        schema_file = os.path.join(os.path.dirname(__file__), "database_schema.sql")

        if os.path.exists(schema_file):
            with open(schema_file) as f:
                schema_sql = f.read()

            # Execute schema creation
            with self.engine.connect() as conn:
                # Split by semicolon and execute each statement
                for statement in schema_sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        try:
                            conn.execute(text(statement))
                            conn.commit()
                        except Exception as e:
                            # Table might already exist, continue
                            print(f"Note: {str(e)[:50]}...")

    def execute_query(
        self, query: str, params: dict[str, Any] = None
    ) -> list[dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dictionaries.

        Args:
            query: SQL query string
            params: Parameters for parameterized queries

        Returns:
            List of dictionaries representing query results
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})

                # Convert to list of dictionaries
                if result.returns_rows:
                    columns = result.keys()
                    return [
                        dict(zip(columns, row, strict=False))
                        for row in result.fetchall()
                    ]
                else:
                    conn.commit()
                    return []
        except Exception as e:
            print(f"Database query error: {e}")
            raise

    def get_dataframe(self, query: str, params: dict[str, Any] = None) -> pd.DataFrame:
        """
        Execute a SQL query and return results as pandas DataFrame.

        Args:
            query: SQL query string
            params: Parameters for parameterized queries

        Returns:
            pandas DataFrame with query results
        """
        try:
            return pd.read_sql_query(text(query), self.engine, params=params)
        except Exception as e:
            print(f"Database query error: {e}")
            raise

    def insert_data(self, table_name: str, data: dict[str, Any]) -> int:
        """
        Insert a single row into a table.

        Args:
            table_name: Name of the table
            data: Dictionary of column names and values

        Returns:
            ID of inserted row
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{k}" for k in data.keys()])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        with self.engine.connect() as conn:
            result = conn.execute(text(query), data)
            conn.commit()
            return result.lastrowid

    def bulk_insert_dataframe(
        self, table_name: str, df: pd.DataFrame, if_exists: str = "append"
    ):
        """
        Bulk insert pandas DataFrame into table.

        Args:
            table_name: Name of the table
            df: pandas DataFrame to insert
            if_exists: How to behave if table exists ('append', 'replace', 'fail')
        """
        df.to_sql(table_name, self.engine, if_exists=if_exists, index=False)

    def get_table_info(self) -> dict[str, list[str]]:
        """
        Get information about all tables and their columns.
        Works with both SQLite and PostgreSQL.

        Returns:
            Dictionary mapping table names to list of column names
        """
        if self._use_postgresql:
            # PostgreSQL query
            query = """
            SELECT
                table_name,
                column_name
            FROM
                information_schema.columns
            WHERE
                table_schema = 'public'
            ORDER BY
                table_name, ordinal_position
            """
        else:
            # SQLite query
            query = """
            SELECT
                m.name as table_name,
                p.name as column_name
            FROM
                sqlite_master m
            LEFT OUTER JOIN
                pragma_table_info((m.name)) p ON m.name <> p.name
            WHERE
                m.type = 'table'
                AND m.name NOT LIKE 'sqlite_%'
            ORDER BY
                table_name, p.cid
            """

        results = self.execute_query(query)

        # Group by table
        tables = {}
        for row in results:
            table = row["table_name"]
            column = row["column_name"]

            if table not in tables:
                tables[table] = []
            if column:  # Column can be None for tables with no columns
                tables[table].append(column)

        return tables

    def get_sample_data(self, table_name: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get sample rows from a table.

        Args:
            table_name: Name of the table
            limit: Number of rows to return

        Returns:
            List of sample rows as dictionaries
        """
        query = f"SELECT * FROM {table_name} LIMIT :limit"
        return self.execute_query(query, {"limit": limit})

    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_query(query)
        return result[0]["count"] if result else 0

    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL (Supabase)."""
        return self._use_postgresql

    def is_sqlite(self) -> bool:
        """Check if using SQLite (local dev)."""
        return not self._use_postgresql

    def get_database_type(self) -> str:
        """Get the database type being used."""
        return "PostgreSQL" if self._use_postgresql else "SQLite"

    def close(self):
        """Close database connection."""
        self.engine.dispose()


# Singleton instance for the application
_db_instance = None


def get_db() -> SQLDatabase:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLDatabase()
    return _db_instance
