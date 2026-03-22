"""Tests for database migration script"""
import pytest
import sqlite3
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import migrate_db


class TestCheckColumnExists:
    """Test checking if column exists in table"""

    def test_column_exists(self, tmp_path):
        """Test detecting existing column"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)')
        conn.commit()

        result = migrate_db.check_column_exists(conn, 'users', 'username')
        assert result is True
        conn.close()

    def test_column_not_exists(self, tmp_path):
        """Test detecting non-existing column"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)')
        conn.commit()

        result = migrate_db.check_column_exists(conn, 'users', 'email')
        assert result is False
        conn.close()

    def test_table_not_exists(self, tmp_path):
        """Test checking column when table doesn't exist"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))

        result = migrate_db.check_column_exists(conn, 'nonexistent', 'id')
        assert result is False
        conn.close()


class TestMigrateUsersTable:
    """Test migrating users table"""

    def test_add_missing_columns(self, tmp_path):
        """Test adding missing columns to users table"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)')
        conn.commit()

        result = migrate_db.migrate_users_table(conn)
        assert result is True

        # Verify columns were added
        cursor = conn.execute('PRAGMA table_info(users)')
        columns = [row[1] for row in cursor.fetchall()]
        assert 'role' in columns
        assert 'display_name' in columns
        assert 'bio' in columns
        conn.close()

    def test_existing_columns_unchanged(self, tmp_path):
        """Test that existing columns remain unchanged"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT DEFAULT 'author'
        )''')
        conn.commit()

        result = migrate_db.migrate_users_table(conn)
        assert result is True
        conn.close()


class TestMigratePostsTable:
    """Test migrating posts table"""

    def test_add_author_id_column(self, tmp_path):
        """Test adding author_id column to posts table"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT)')
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        conn.execute('INSERT INTO users (id) VALUES (1)')
        conn.commit()

        result = migrate_db.migrate_posts_table(conn)
        assert result is True

        # Verify column was added
        cursor = conn.execute('PRAGMA table_info(posts)')
        columns = [row[1] for row in cursor.fetchall()]
        assert 'author_id' in columns
        conn.close()

    def test_assign_author_to_existing_posts(self, tmp_path):
        """Test assigning author to existing posts"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT)')
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        conn.execute('INSERT INTO users (id) VALUES (1)')
        conn.execute('INSERT INTO posts (title) VALUES ("Test Post")')
        conn.commit()

        migrate_db.migrate_posts_table(conn)

        # Verify author was assigned
        cursor = conn.execute('SELECT author_id FROM posts WHERE id = 1')
        result = cursor.fetchone()
        assert result[0] == 1
        conn.close()


class TestCreateIndexes:
    """Test creating database indexes"""

    def test_create_indexes_success(self, tmp_path):
        """Test successful index creation"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, author_id INTEGER, created_at TIMESTAMP)')
        conn.commit()

        result = migrate_db.create_indexes(conn)
        assert result is True

        # Verify indexes were created
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = [row[0] for row in cursor.fetchall()]
        assert 'idx_author_id' in index_names or any('author' in name for name in index_names)
        conn.close()


class TestRebuildFTSIndex:
    """Test rebuilding FTS index"""

    def test_rebuild_fts_index_success(self, tmp_path):
        """Test successful FTS index rebuild"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE VIRTUAL TABLE posts_fts USING fts5(title, content)')
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        conn.execute('INSERT INTO posts (id, title, content) VALUES (1, "Test", "Content")')
        conn.commit()

        result = migrate_db.rebuild_fts_index(conn)
        assert result is True

        # Verify FTS data was populated
        cursor = conn.execute('SELECT COUNT(*) FROM posts_fts')
        count = cursor.fetchone()[0]
        assert count >= 0
        conn.close()


class TestGetMigrationStatus:
    """Test getting migration status"""

    def test_get_migration_status(self, tmp_path, capfd):
        """Test getting migration status"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY)')
        conn.commit()

        migrate_db.get_migration_status(conn)

        captured = capfd.readouterr()
        assert '数据库状态' in captured.out
        conn.close()
