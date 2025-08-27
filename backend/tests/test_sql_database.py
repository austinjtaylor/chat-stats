"""
Test SQL Database module functionality.
Tests database operations, connection handling, and query execution.
"""

import pytest
import tempfile
import os
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sql_database import SQLDatabase, get_db


class TestSQLDatabase:
    """Test SQLDatabase class functionality"""
    
    def test_init_default_path(self):
        """Test database initialization with default path"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            with patch('sql_database.config.DATABASE_PATH', temp_path):
                db = SQLDatabase()
                assert db.db_path == temp_path
                assert db.connection is not None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_init_custom_path(self):
        """Test database initialization with custom path"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            assert db.db_path == temp_path
            assert db.connection is not None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_init_creates_directory(self):
        """Test that database initialization creates directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'subdir', 'test.db')
            
            db = SQLDatabase(db_path)
            assert os.path.exists(os.path.dirname(db_path))
            assert db.connection is not None
    
    def test_execute_query_simple_select(self):
        """Test executing a simple SELECT query"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            # Create a test table
            db.execute_query("CREATE TABLE test_table (id INTEGER, name TEXT)")
            db.execute_query("INSERT INTO test_table VALUES (1, 'test')")
            
            # Test SELECT query
            result = db.execute_query("SELECT * FROM test_table")
            assert len(result) == 1
            assert result[0]['id'] == 1
            assert result[0]['name'] == 'test'
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_execute_query_with_parameters(self):
        """Test executing query with parameters"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            # Create test table
            db.execute_query("CREATE TABLE test_params (id INTEGER, name TEXT)")
            
            # Test parameterized insert
            db.execute_query(
                "INSERT INTO test_params VALUES (:id, :name)",
                {"id": 1, "name": "test_param"}
            )
            
            # Test parameterized select
            result = db.execute_query(
                "SELECT * FROM test_params WHERE id = :id",
                {"id": 1}
            )
            assert len(result) == 1
            assert result[0]['name'] == 'test_param'
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_execute_query_no_results(self):
        """Test executing query that returns no results"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            db.execute_query("CREATE TABLE empty_table (id INTEGER)")
            
            result = db.execute_query("SELECT * FROM empty_table")
            assert result == []
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_execute_query_invalid_sql(self):
        """Test executing invalid SQL query"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            with pytest.raises(Exception):
                db.execute_query("INVALID SQL STATEMENT")
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_insert_data_basic(self):
        """Test basic insert_data functionality"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            # Create test table
            db.execute_query("CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT, city TEXT)")
            
            # Test insert
            data = {"name": "Lakers", "city": "Los Angeles"}
            result_id = db.insert_data("teams", data)
            
            assert result_id == 1
            
            # Verify insertion
            result = db.execute_query("SELECT * FROM teams WHERE id = 1")
            assert len(result) == 1
            assert result[0]['name'] == 'Lakers'
            assert result[0]['city'] == 'Los Angeles'
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_insert_data_multiple_rows(self):
        """Test inserting multiple rows"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            # Create test table
            db.execute_query("CREATE TABLE players (id INTEGER PRIMARY KEY, name TEXT, team TEXT)")
            
            # Insert multiple rows
            players = [
                {"name": "Player 1", "team": "Team A"},
                {"name": "Player 2", "team": "Team B"},
                {"name": "Player 3", "team": "Team A"}
            ]
            
            ids = []
            for player in players:
                result_id = db.insert_data("players", player)
                ids.append(result_id)
            
            assert len(ids) == 3
            assert ids == [1, 2, 3]
            
            # Verify all insertions
            result = db.execute_query("SELECT COUNT(*) as count FROM players")
            assert result[0]['count'] == 3
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_insert_data_with_null_values(self):
        """Test inserting data with null values"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            # Create test table with nullable columns
            db.execute_query("CREATE TABLE test_nulls (id INTEGER PRIMARY KEY, name TEXT, optional_field TEXT)")
            
            # Insert with null value
            data = {"name": "Test Name", "optional_field": None}
            result_id = db.insert_data("test_nulls", data)
            
            assert result_id == 1
            
            # Verify insertion
            result = db.execute_query("SELECT * FROM test_nulls WHERE id = 1")
            assert result[0]['name'] == 'Test Name'
            assert result[0]['optional_field'] is None
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_insert_data_invalid_table(self):
        """Test insert_data with invalid table name"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            data = {"name": "Test"}
            with pytest.raises(Exception):
                db.insert_data("nonexistent_table", data)
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_connection_persistence(self):
        """Test that connection persists across queries"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            initial_connection = db.connection
            
            # Execute several queries
            db.execute_query("CREATE TABLE persistence_test (id INTEGER)")
            db.execute_query("INSERT INTO persistence_test VALUES (1)")
            result = db.execute_query("SELECT * FROM persistence_test")
            
            # Connection should remain the same
            assert db.connection is initial_connection
            assert len(result) == 1
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_database_schema_creation(self):
        """Test that database schema is created properly"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            with patch('sql_database.os.path.exists') as mock_exists:
                # Mock that schema file exists
                mock_exists.return_value = True
                
                with patch('builtins.open', create=True) as mock_open:
                    # Mock schema file content
                    mock_schema = "CREATE TABLE test_schema (id INTEGER PRIMARY KEY);"
                    mock_open.return_value.__enter__.return_value.read.return_value = mock_schema
                    
                    db = SQLDatabase(temp_path)
                    
                    # Verify schema was executed
                    tables = db.execute_query(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='test_schema'"
                    )
                    assert len(tables) == 1
                    
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGetDBFunction:
    """Test get_db function"""
    
    @patch('sql_database._db', None)  # Reset singleton
    def test_get_db_creates_instance(self):
        """Test that get_db creates a singleton instance"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            with patch('sql_database.config.DATABASE_PATH', temp_path):
                db1 = get_db()
                db2 = get_db()
                
                # Should return the same instance
                assert db1 is db2
                assert isinstance(db1, SQLDatabase)
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('sql_database._db', None)  # Reset singleton
    def test_get_db_handles_missing_config(self):
        """Test get_db handles missing database configuration"""
        with patch('sql_database.config.DATABASE_PATH', ''):
            with pytest.raises((AttributeError, ValueError)):
                get_db()


class TestDatabaseErrorHandling:
    """Test database error handling scenarios"""
    
    def test_database_file_permissions(self):
        """Test handling of database file permission errors"""
        # Create a directory where we can't write
        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_path = os.path.join(temp_dir, 'restricted')
            os.makedirs(restricted_path)
            os.chmod(restricted_path, 0o444)  # Read-only
            
            db_path = os.path.join(restricted_path, 'test.db')
            
            try:
                with pytest.raises(Exception):
                    SQLDatabase(db_path)
            finally:
                # Restore permissions for cleanup
                os.chmod(restricted_path, 0o755)
    
    def test_concurrent_access(self):
        """Test handling of concurrent database access"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db1 = SQLDatabase(temp_path)
            db2 = SQLDatabase(temp_path)
            
            # Create table with first connection
            db1.execute_query("CREATE TABLE IF NOT EXISTS concurrent_test (id INTEGER)")
            
            # Use second connection
            db2.execute_query("INSERT INTO concurrent_test VALUES (1)")
            
            # Read from first connection
            result = db1.execute_query("SELECT * FROM concurrent_test")
            assert len(result) == 1
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_sql_injection_prevention(self):
        """Test that parameterized queries prevent SQL injection"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            db = SQLDatabase(temp_path)
            
            # Create test table
            db.execute_query("CREATE TABLE injection_test (id INTEGER, name TEXT)")
            db.execute_query("INSERT INTO injection_test VALUES (1, 'safe_value')")
            
            # Attempt SQL injection through parameters
            malicious_input = "'; DROP TABLE injection_test; --"
            
            # This should not drop the table
            result = db.execute_query(
                "SELECT * FROM injection_test WHERE name = :name",
                {"name": malicious_input}
            )
            
            # Table should still exist and be empty for this query
            assert result == []
            
            # Verify table still exists
            tables = db.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='injection_test'"
            )
            assert len(tables) == 1
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)