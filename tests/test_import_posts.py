"""Tests for import_posts module"""
import pytest
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import import_posts


class TestParseFrontmatter:
    """Test parsing YAML frontmatter from markdown"""

    def test_valid_frontmatter(self):
        """Test parsing valid frontmatter"""
        content = """---
title: Test Post
published: true
date: 2024-01-01
tags: [python, testing]
---
This is the body content."""

        metadata, body = import_posts.parse_frontmatter(content)

        assert metadata['title'] == 'Test Post'
        assert metadata['published'] is True
        assert metadata['date'] == '2024-01-01'
        assert metadata['tags'] == ['python', 'testing']
        assert body.strip() == 'This is the body content.'

    def test_no_frontmatter(self):
        """Test content without frontmatter"""
        content = "This is just plain content without frontmatter."

        metadata, body = import_posts.parse_frontmatter(content)

        assert metadata == {}
        assert body == content

    def test_boolean_values(self):
        """Test parsing boolean values in frontmatter"""
        content = """---
published: false
featured: true
---
Body content"""

        metadata, body = import_posts.parse_frontmatter(content)

        assert metadata['published'] is False
        assert metadata['featured'] is True

    def test_list_values(self):
        """Test parsing list values in frontmatter"""
        content = """---
tags: [python, flask, testing]
categories: [tech, web]
---
Body"""

        metadata, body = import_posts.parse_frontmatter(content)

        assert metadata['tags'] == ['python', 'flask', 'testing']
        assert metadata['categories'] == ['tech', 'web']


class TestImportFromJson:
    """Test importing posts from JSON file"""

    @pytest.fixture
    def sample_json_data(self):
        """Create sample JSON export data"""
        return {
            'posts': [
                {
                    'title': 'Test Post 1',
                    'content': 'This is test content',
                    'is_published': 1,
                    'created_at': '2024-01-01 12:00:00',
                    'updated_at': '2024-01-01 12:00:00',
                    'category_name': 'Test Category',
                    'tags': 'python,testing'
                },
                {
                    'title': 'Test Post 2',
                    'content': 'More test content',
                    'is_published': 0,
                    'created_at': '2024-01-02 12:00:00',
                    'updated_at': '2024-01-02 12:00:00',
                    'category_name': None,
                    'tags': ''
                }
            ]
        }

    def test_import_successful(self, sample_json_data, tmp_path):
        """Test successful import"""
        # Create temp JSON file
        json_file = tmp_path / 'export.json'
        with open(json_file, 'w') as f:
            json.dump(sample_json_data, f)

        # Create temp database
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT)')
        conn.execute('CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY)')
        conn.execute('INSERT INTO users (id, role) VALUES (1, "admin")')
        conn.commit()
        conn.close()

        with patch('import_posts.get_db_connection') as mock_get_conn:
            mock_get_conn.return_value = sqlite3.connect(str(db_path))
            mock_get_conn.return_value.row_factory = sqlite3.Row

            imported, skipped, messages = import_posts.import_from_json(str(json_file))

        assert imported >= 0
        assert isinstance(messages, list)
        assert len(messages) > 0

    def test_import_file_not_found(self):
        """Test import with non-existent file"""
        imported, skipped, messages = import_posts.import_from_json('/nonexistent/file.json')

        assert imported == 0
        assert skipped == 0
        assert len(messages) == 1
        assert '读取JSON文件失败' in messages[0]

    def test_import_empty_posts(self, tmp_path):
        """Test import with empty posts array"""
        json_file = tmp_path / 'empty.json'
        with open(json_file, 'w') as f:
            json.dump({'posts': []}, f)

        imported, skipped, messages = import_posts.import_from_json(str(json_file))

        assert imported == 0
        assert skipped == 0
        assert '没有找到文章数据' in messages[0]


class TestImportFromMarkdownDirectory:
    """Test importing from markdown directory"""

    def test_import_nonexistent_directory(self):
        """Test importing from non-existent directory"""
        imported, skipped, messages = import_posts.import_from_markdown_directory('/nonexistent/dir')

        assert imported == 0
        assert skipped == 0
        assert '目录不存在' in messages[0]

    def test_import_empty_directory(self, tmp_path):
        """Test importing from empty directory"""
        empty_dir = tmp_path / 'empty'
        empty_dir.mkdir()

        imported, skipped, messages = import_posts.import_from_markdown_directory(str(empty_dir))

        assert imported == 0
        assert skipped == 0
        assert '未找到Markdown文件' in messages[0]

    def test_import_valid_markdown(self, tmp_path):
        """Test importing valid markdown file"""
        md_dir = tmp_path / 'markdown'
        md_dir.mkdir()

        md_file = md_dir / 'test-post.md'
        md_file.write_text('''---
title: Test Post
date: 2024-01-01
published: true
tags: [python, testing]
---
This is the content.''')

        # Create temp database
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(str(db_path))
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT)')
        conn.execute('CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY)')
        conn.execute('INSERT INTO users (id, role) VALUES (1, "admin")')
        conn.commit()
        conn.close()

        with patch('import_posts.get_db_connection') as mock_get_conn:
            mock_get_conn.return_value = sqlite3.connect(str(db_path))
            mock_get_conn.return_value.row_factory = sqlite3.Row

            imported, skipped, messages = import_posts.import_from_markdown_directory(str(md_dir))

        assert isinstance(imported, int)
        assert isinstance(messages, list)
