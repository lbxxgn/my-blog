"""Tests for database check and repair tool"""
import pytest
import sqlite3
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import db_check


class TestCheckDatabase:
    """Test database integrity checking functions"""

    def test_check_database_integrity_check(self, tmp_path, capfd):
        """Test successful integrity check"""
        # Create a test database
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()

        with patch.object(db_check, 'DB_PATH', db_path):
            result = db_check.check_database()
            assert result is True

        captured = capfd.readouterr()
        assert '数据库结构完整' in captured.out

    def test_check_database_foreign_key_check(self, tmp_path, capfd):
        """Test foreign key constraint checking"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE parent (id INTEGER PRIMARY KEY)')
        conn.execute('CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))')
        conn.commit()
        conn.close()

        with patch.object(db_check, 'DB_PATH', db_path):
            db_check.check_database()

        captured = capfd.readouterr()
        assert '外键约束正常' in captured.out


class TestBackupDatabase:
    """Test database backup functionality"""

    def test_backup_database_creates_backup(self, tmp_path):
        """Test that backup creates a backup file"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()

        with patch.object(db_check, 'DB_PATH', db_path):
            db_check.backup_database()

        # Check that backup file was created
        backup_files = list(tmp_path.glob('*.backup.*'))
        assert len(backup_files) > 0


class TestVacuumDatabase:
    """Test database vacuum functionality"""

    def test_vacuum_database_success(self, tmp_path, capfd):
        """Test successful database vacuum"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()

        with patch.object(db_check, 'DB_PATH', db_path):
            db_check.vacuum_database()

        captured = capfd.readouterr()
        assert '数据库已优化' in captured.out

    def test_vacuum_database_error(self, tmp_path, capfd):
        """Test vacuum with invalid/corrupted database file"""
        # Create an empty/corrupted file that will cause VACUUM to fail
        db_path = tmp_path / 'corrupted.db'
        db_path.write_text('not a valid sqlite database')

        with patch.object(db_check, 'DB_PATH', db_path):
            db_check.vacuum_database()

        captured = capfd.readouterr()
        assert '优化失败' in captured.out or 'database' in captured.out.lower() or 'disk' in captured.out.lower()


class TestReindexDatabase:
    """Test database reindex functionality"""

    def test_reindex_database_success(self, tmp_path, capfd):
        """Test successful database reindex"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()

        with patch.object(db_check, 'DB_PATH', db_path):
            db_check.reindex_database()

        captured = capfd.readouterr()
        assert '索引已重建' in captured.out


class TestFixDatabase:
    """Test database repair functionality"""

    def test_fix_database_with_backup(self, tmp_path, capfd):
        """Test database repair with backup creation"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        conn.commit()
        conn.close()

        with patch.object(db_check, 'DB_PATH', db_path):
            result = db_check.fix_database()

        captured = capfd.readouterr()
        assert '创建备份' in captured.out

    def test_fix_database_export_data(self, tmp_path, capfd):
        """Test database repair exports data"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('INSERT INTO test (name) VALUES ("test")')
        conn.commit()
        conn.close()

        with patch.object(db_check, 'DB_PATH', db_path):
            db_check.fix_database()

        captured = capfd.readouterr()
        assert '导出数据' in captured.out
