"""Tests for blog import functionality"""
import pytest
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import import_blog


class TestTimestampToDatetime:
    """Test timestamp to datetime conversion"""

    def test_valid_timestamp(self):
        """Test converting valid timestamp"""
        timestamp_ms = "1609459200000"  # 2021-01-01 00:00:00 UTC
        result = import_blog.timestamp_to_datetime(timestamp_ms)
        assert isinstance(result, datetime)
        assert result.year == 2021
        assert result.month == 1
        assert result.day == 1

    def test_invalid_timestamp(self):
        """Test converting invalid timestamp"""
        result = import_blog.timestamp_to_datetime("invalid")
        assert isinstance(result, datetime)

    def test_none_timestamp(self):
        """Test converting None timestamp"""
        result = import_blog.timestamp_to_datetime(None)
        assert isinstance(result, datetime)


class TestCleanHtmlContent:
    """Test HTML content cleaning"""

    def test_remove_wbr_tags(self):
        """Test removing wbr tags"""
        html = '<p>Hello<wbr></wbr>World</p>'
        result = import_blog.clean_html_content(html)
        assert '<wbr>' not in result
        assert '</wbr>' not in result

    def test_remove_white_space_style(self):
        """Test removing white-space style spans"""
        html = '<p><span style="white-space:pre;">  text  </span></p>'
        result = import_blog.clean_html_content(html)
        assert 'white-space:pre' not in result

    def test_empty_content(self):
        """Test handling empty content"""
        result = import_blog.clean_html_content('')
        assert result == ''

    def test_none_content(self):
        """Test handling None content"""
        result = import_blog.clean_html_content(None)
        assert result == ''


class TestImportBlogsFromXml:
    """Test importing blogs from XML"""

    def create_test_xml(self, tmp_path, entries):
        """Helper to create test XML file"""
        xml_file = tmp_path / 'test_blog.xml'
        root = ET.Element('blogs')

        for entry in entries:
            blog = ET.SubElement(root, 'blog')
            for key, value in entry.items():
                elem = ET.SubElement(blog, key)
                elem.text = value

        tree = ET.ElementTree(root)
        tree.write(str(xml_file), encoding='utf-8', xml_declaration=True)
        return xml_file

    @patch('import_blog.create_post')
    @patch('import_blog.get_db_connection')
    @patch('import_blog.init_db')
    def test_import_single_blog(self, mock_init, mock_get_conn, mock_create_post, tmp_path):
        """Test importing a single blog entry - the post doesn't exist so it should be created"""
        # Setup
        mock_create_post.return_value = 1
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First fetchone for user check, second for checking if post exists (return None = not exists)
        mock_cursor.fetchone.side_effect = [
            {'id': 1, 'username': 'test', 'display_name': 'Test'},  # User exists
            None  # Post doesn't exist yet
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        xml_file = self.create_test_xml(tmp_path, [{
            'title': 'Test Post',
            'content': 'Test content',
            'ispublished': '1',
            'publishTime': '1609459200000'
        }])

        # Execute
        import_blog.import_blogs_from_xml(str(xml_file), author_id=1)

        # Verify create_post was called
        mock_create_post.assert_called_once()

    @patch('import_blog.get_db_connection')
    @patch('import_blog.init_db')
    def test_import_no_entries(self, mock_init, mock_get_conn, tmp_path):
        """Test importing with no entries"""
        xml_file = self.create_test_xml(tmp_path, [])

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        with patch('import_blog.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.parent.parent = tmp_path
            import_blog.import_blogs_from_xml(str(xml_file), author_id=1)


class TestCleanHtmlContentEdgeCases:
    """Test edge cases for HTML content cleaning"""

    def test_cdata_in_title(self):
        """Test handling CDATA in title"""
        html = '<![CDATA[Test Title]]'
        # The function should handle this gracefully
        result = import_blog.clean_html_content(html)
        assert isinstance(result, str)

    def test_malformed_html(self):
        """Test handling malformed HTML"""
        html = '<p>Unclosed tag <span>text'
        result = import_blog.clean_html_content(html)
        assert isinstance(result, str)

    def test_special_characters(self):
        """Test handling special characters"""
        html = '<p>Special chars: ñ 中文 🎉</p'
        result = import_blog.clean_html_content(html)
        assert isinstance(result, str)
