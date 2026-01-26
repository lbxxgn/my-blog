"""Article import functionality for backup restore"""
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import get_db_connection


def import_from_json(json_file_path: str, user_id: int = None) -> Tuple[int, int, List[str]]:
    """
    Import posts from JSON export file

    Args:
        json_file_path: Path to JSON export file
        user_id: User ID to assign as author (default: None, uses first admin user)

    Returns:
        Tuple of (imported_count, skipped_count, messages)
    """
    messages = []

    # Read JSON file
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return 0, 0, [f"❌ 读取JSON文件失败: {str(e)}"]

    posts = data.get('posts', [])
    if not posts:
        return 0, 0, ["❌ JSON文件中没有找到文章数据"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get user_id if not provided
    if user_id is None:
        cursor.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1')
        user = cursor.fetchone()
        if user:
            user_id = user['id']
        else:
            conn.close()
            return 0, 0, ["❌ 系统中没有管理员用户，无法导入"]

    imported_count = 0
    skipped_count = 0

    for post_data in posts:
        try:
            title = post_data.get('title', '').strip()
            content = post_data.get('content', '')
            is_published = post_data.get('is_published', 0)
            created_at = post_data.get('created_at')
            updated_at = post_data.get('updated_at')
            category_name = post_data.get('category_name')
            tags_str = post_data.get('tags', '')

            if not title or not content:
                skipped_count += 1
                messages.append(f"⚠️ 跳过：文章缺少标题或内容")
                continue

            # Check if post already exists (by title and creation date)
            cursor.execute('''
                SELECT id FROM posts
                WHERE title = ? AND created_at = ?
            ''', (title, created_at))
            existing = cursor.fetchone()

            if existing:
                skipped_count += 1
                messages.append(f"⚠️ 跳过：文章已存在 - {title}")
                continue

            # Handle category
            category_id = None
            if category_name:
                cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                category = cursor.fetchone()
                if category:
                    category_id = category['id']
                else:
                    # Create new category
                    try:
                        cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
                        conn.commit()
                        category_id = cursor.lastrowid
                    except:
                        # Category might have been created by another post
                        cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                        category = cursor.fetchone()
                        if category:
                            category_id = category['id']

            # Insert post
            cursor.execute('''
                INSERT INTO posts (title, content, is_published, category_id, author_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, content, is_published, category_id, user_id, created_at, updated_at))

            post_id = cursor.lastrowid
            conn.commit()

            # Handle tags
            if tags_str:
                tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]

                for tag_name in tag_names:
                    # Get or create tag
                    cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                    tag = cursor.fetchone()

                    if not tag:
                        cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag_name,))
                        conn.commit()
                        tag_id = cursor.lastrowid
                    else:
                        tag_id = tag['id']

                    # Link tag to post
                    try:
                        cursor.execute('INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                                     (post_id, tag_id))
                        conn.commit()
                    except:
                        # Tag might already be linked
                        pass

            imported_count += 1
            messages.append(f"✅ 导入成功：{title}")

        except Exception as e:
            skipped_count += 1
            messages.append(f"❌ 导入失败：{post_data.get('title', 'Unknown')} - {str(e)}")

    conn.close()

    messages.insert(0, f"📊 导入完成：成功 {imported_count} 篇，跳过 {skipped_count} 篇")

    return imported_count, skipped_count, messages


def import_from_markdown_directory(markdown_dir: str, user_id: int = None) -> Tuple[int, int, List[str]]:
    """
    Import posts from markdown files with YAML frontmatter

    Args:
        markdown_dir: Path to directory containing markdown files
        user_id: User ID to assign as author

    Returns:
        Tuple of (imported_count, skipped_count, messages)
    """
    messages = []
    markdown_path = Path(markdown_dir)

    if not markdown_path.exists():
        return 0, 0, [f"❌ 目录不存在: {markdown_dir}"]

    # Find all .md files
    md_files = list(markdown_path.glob('**/*.md'))
    if not md_files:
        return 0, 0, [f"❌ 在目录中未找到Markdown文件: {markdown_dir}"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get user_id if not provided
    if user_id is None:
        cursor.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1')
        user = cursor.fetchone()
        if user:
            user_id = user['id']
        else:
            conn.close()
            return 0, 0, ["❌ 系统中没有管理员用户，无法导入"]

    imported_count = 0
    skipped_count = 0

    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse YAML frontmatter
            metadata, body_content = parse_frontmatter(content)

            if not metadata or not metadata.get('title'):
                skipped_count += 1
                messages.append(f"⚠️ 跳过：{md_file.name} - 缺少标题元数据")
                continue

            title = metadata.get('title', '').strip()
            is_published = metadata.get('published', True)
            created_at = metadata.get('date')
            updated_at = metadata.get('updated', created_at)
            category_name = metadata.get('category')
            tags = metadata.get('tags', [])

            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]

            # Check if post already exists
            if created_at:
                cursor.execute('''
                    SELECT id FROM posts
                    WHERE title = ? AND created_at = ?
                ''', (title, created_at))
                existing = cursor.fetchone()

                if existing:
                    skipped_count += 1
                    messages.append(f"⚠️ 跳过：文章已存在 - {title}")
                    continue

            # Handle category
            category_id = None
            if category_name:
                cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                category = cursor.fetchone()
                if category:
                    category_id = category['id']
                else:
                    cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
                    conn.commit()
                    category_id = cursor.lastrowid

            # Insert post
            cursor.execute('''
                INSERT INTO posts (title, content, is_published, category_id, author_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, body_content, 1 if is_published else 0, category_id, user_id, created_at, updated_at))

            post_id = cursor.lastrowid
            conn.commit()

            # Handle tags
            for tag_name in tags:
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                tag = cursor.fetchone()

                if not tag:
                    cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag_name,))
                    conn.commit()
                    tag_id = cursor.lastrowid
                else:
                    tag_id = tag['id']

                try:
                    cursor.execute('INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                                 (post_id, tag_id))
                    conn.commit()
                except:
                    pass

            imported_count += 1
            messages.append(f"✅ 导入成功：{title}")

        except Exception as e:
            skipped_count += 1
            messages.append(f"❌ 导入失败：{md_file.name} - {str(e)}")

    conn.close()

    messages.insert(0, f"📊 导入完成：成功 {imported_count} 篇，跳过 {skipped_count} 篇")

    return imported_count, skipped_count, messages


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """
    Parse YAML frontmatter from markdown content

    Args:
        content: Markdown content with possible frontmatter

    Returns:
        Tuple of (metadata_dict, content_without_frontmatter)
    """
    # Match frontmatter pattern
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        frontmatter_text = match.group(1)
        body_content = match.group(2)

        # Parse simple YAML-like key-value pairs
        metadata = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Handle different value types
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.startswith('[') and value.endswith(']'):
                    # List format
                    value = [item.strip() for item in value[1:-1].split(',') if item.strip()]

                metadata[key] = value

        return metadata, body_content

    return {}, content


if __name__ == '__main__':
    # Test import
    import sys

    if len(sys.argv) < 2:
        print("Usage: python import_posts.py <json_file_or_markdown_dir>")
        sys.exit(1)

    input_path = sys.argv[1]

    if input_path.endswith('.json'):
        print(f"从JSON文件导入: {input_path}")
        count, skipped, messages = import_from_json(input_path)
    elif Path(input_path).is_dir():
        print(f"从Markdown目录导入: {input_path}")
        count, skipped, messages = import_from_markdown_directory(input_path)
    else:
        print("❌ 不支持的输入格式，请提供JSON文件或Markdown目录")
        sys.exit(1)

    print("\n".join(messages))
