"""
SQL Database connection and query execution module for Sports Stats Chatbot.
PostgreSQL (Supabase) only.
"""

import os
from typing import Any

import pandas as pd
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


class SQLDatabase:
    """Manages PostgreSQL database connections and query execution for sports statistics."""

    def __init__(self, database_url: str = None):
        """
        Initialize PostgreSQL database connection.

        Args:
            database_url: PostgreSQL connection URL (for Supabase)

        Environment Variables:
            DATABASE_URL: PostgreSQL URL (required)
        """
        # Get database URL from parameter or environment
        self.database_url = database_url or os.getenv("DATABASE_URL")

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is required. Please set it in your .env file."
            )

        print("🐘 Using PostgreSQL database (Supabase)")

        # Create PostgreSQL engine
        self.engine = create_engine(
            self.database_url,
            poolclass=NullPool,  # Let Supabase handle connection pooling
            echo=False,  # Set to True for SQL query debugging
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Store metadata
        self.metadata = MetaData()

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
        Get information about all tables and their columns (PostgreSQL).

        Returns:
            Dictionary mapping table names to list of column names
        """
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
        """Check if using PostgreSQL (always True now)."""
        return True

    def get_database_type(self) -> str:
        """Get the database type being used."""
        return "PostgreSQL"

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
