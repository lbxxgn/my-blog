"""Tests for image cleanup tool"""
import pytest
import sqlite3
import re
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import image_cleanup_tool


class TestCleanLocalImages:
    """Test local image cleaning functionality"""

    def test_clean_local_images_no_posts(self, tmp_path, capfd):
        """Test cleaning with no posts"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        conn.commit()
        conn.close()

        with patch.object(image_cleanup_tool, 'get_db_connection') as mock_get_conn:
            mock_get_conn.return_value = sqlite3.connect(str(db_path))
            mock_get_conn.return_value.row_factory = sqlite3.Row
            result = image_cleanup_tool.clean_local_images(dry_run=True)

        assert result['total_posts'] == 0
        captured = capfd.readouterr()
        assert '开始扫描' in captured.out

    def test_clean_local_images_with_images(self, tmp_path):
        """Test cleaning posts with local images"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        # 使用安全的SQL参数化插入
        content = '<img src="/uploads/test.jpg">'
        conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)', ("Test", content))
        conn.commit()
        conn.close()

        # Mock CleanupLogger to avoid print issues
        with patch.object(image_cleanup_tool, 'get_db_connection') as mock_get_conn:
            mock_conn = sqlite3.connect(str(db_path))
            mock_conn.row_factory = sqlite3.Row
            mock_get_conn.return_value = mock_conn

            with patch('image_cleanup_tool.CleanupLogger'):
                result = image_cleanup_tool.clean_local_images(dry_run=True)

        assert result['total_posts'] == 1
        assert result['posts_with_images'] == 1
        assert result['total_images'] == 1


class TestCleanAllImages:
    """Test cleaning all images including external"""

    def test_clean_all_images_with_external(self, tmp_path):
        """Test cleaning with external images"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        content = '<img src="https://example.com/test.jpg">'
        conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)', ("Test", content))
        conn.commit()
        conn.close()

        with patch.object(image_cleanup_tool, 'get_db_connection') as mock_get_conn:
            mock_get_conn.return_value = sqlite3.connect(str(db_path))
            mock_get_conn.return_value.row_factory = sqlite3.Row
            result = image_cleanup_tool.clean_all_images(dry_run=True, check_external=False)

        assert result['total_posts'] == 1
        assert result['external_skipped'] == 1


class TestFastCleanInvalidDomains:
    """Test fast cleaning of known invalid domains"""

    def test_fast_clean_126_net(self, tmp_path):
        """Test cleaning 126.net images"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        content = '<img src="http://img.126.net/test.jpg"> content'
        conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)', ("Test", content))
        conn.commit()
        conn.close()

        with patch.object(image_cleanup_tool, 'get_db_connection') as mock_get_conn:
            mock_conn = sqlite3.connect(str(db_path))
            mock_conn.row_factory = sqlite3.Row
            mock_get_conn.return_value = mock_conn
            result = image_cleanup_tool.fast_clean_invalid_domains()

        assert result['total_posts'] == 1

    def test_fast_clean_163_com(self, tmp_path):
        """Test cleaning blog.163.com images"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        content = '<img src="http://blog.163.com/test.jpg"> content'
        conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)', ("Test", content))
        conn.commit()
        conn.close()

        with patch.object(image_cleanup_tool, 'get_db_connection') as mock_get_conn:
            mock_conn = sqlite3.connect(str(db_path))
            mock_conn.row_factory = sqlite3.Row
            mock_get_conn.return_value = mock_conn
            result = image_cleanup_tool.fast_clean_invalid_domains()

        assert result['total_posts'] == 1


class TestCheckExternalImages:
    """Test checking external images"""

    @patch('image_cleanup_tool.get_db_connection')
    @patch('image_cleanup_tool.extract_images_from_content')
    @patch('image_cleanup_tool.check_image_urls_with_progress')
    def test_check_external_images_no_posts(self, mock_check_urls, mock_extract, mock_get_conn, tmp_path):
        """Test checking with no posts"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        conn.commit()
        conn.close()

        def mock_get_conn_func():
            c = sqlite3.connect(str(db_path))
            c.row_factory = sqlite3.Row
            return c

        mock_get_conn.side_effect = mock_get_conn_func

        with patch('builtins.print') as mock_print:
            image_cleanup_tool.check_external_images(show_progress=False)

        mock_print.assert_any_call('✅ 没有找到外部图片URL')

    @patch('image_cleanup_tool.get_db_connection')
    @patch('image_cleanup_tool.extract_images_from_content')
    @patch('image_cleanup_tool.check_image_urls_with_progress')
    def test_check_external_images_with_urls(self, mock_check_urls, mock_extract, mock_get_conn, tmp_path):
        """Test checking with external URLs"""
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
        conn.execute('INSERT INTO posts VALUES (1, "Test", "content")')
        conn.commit()
        conn.close()

        # Mock the connection to return row factory enabled connection
        def mock_get_conn_func():
            c = sqlite3.connect(str(db_path))
            c.row_factory = sqlite3.Row
            return c

        mock_get_conn.side_effect = mock_get_conn_func
        mock_extract.return_value = [('<img src="https://example.com/test.jpg">', 'https://example.com/test.jpg')]
        mock_check_urls.return_value = {'https://example.com/test.jpg': (True, None)}

        with patch('builtins.print') as mock_print:
            image_cleanup_tool.check_external_images(show_progress=False)


class TestMainFunction:
    """Test main function argument parsing"""

    @patch('image_cleanup_tool.clean_local_images')
    def test_main_local_mode(self, mock_clean):
        """Test local mode"""
        mock_clean.return_value = {'invalid_images': 5}

        with patch('sys.argv', ['image_cleanup_tool', 'local', '--dry-run']):
            with patch('builtins.print') as mock_print:
                image_cleanup_tool.main()

        mock_clean.assert_called_once()

    @patch('image_cleanup_tool.clean_all_images')
    def test_main_all_mode(self, mock_clean):
        """Test all mode"""
        mock_clean.return_value = {'invalid_images': 0}

        with patch('sys.argv', ['image_cleanup_tool', 'all', '--dry-run', '--check-external']):
            with patch('builtins.print') as mock_print:
                image_cleanup_tool.main()

        mock_clean.assert_called_once()

    @patch('image_cleanup_tool.fast_clean_invalid_domains')
    def test_main_fast_clean_mode(self, mock_clean):
        """Test fast-clean mode"""
        mock_clean.return_value = {'total_posts': 10}

        with patch('sys.argv', ['image_cleanup_tool', 'fast-clean']):
            with patch('builtins.print') as mock_print:
                image_cleanup_tool.main()

        mock_clean.assert_called_once()

    @patch('image_cleanup_tool.check_external_images')
    def test_main_check_external_mode(self, mock_check):
        """Test check-external mode"""
        with patch('sys.argv', ['image_cleanup_tool', 'check-external']):
            with patch('builtins.print') as mock_print:
                image_cleanup_tool.main()

        mock_check.assert_called_once()
