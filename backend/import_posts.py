"""Article import functionality for backup restore"""
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import get_db_connection


def _get_or_create_category(cursor, name, space='blog', parent_id=None):
    if not name:
        return None
    cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
    row = cursor.fetchone()
    if row:
        return row['id']
    try:
        cursor.execute(
            'INSERT INTO categories (name, space, parent_id) VALUES (?, ?, ?)',
            (name, space, parent_id),
        )
    except Exception:
        cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
    return cursor.lastrowid


def _set_tags(cursor, post_id, tag_names):
    for tag_name in tag_names or []:
        tag_name = str(tag_name).strip()
        if not tag_name:
            continue
        cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
        row = cursor.fetchone()
        if row:
            tag_id = row['id']
        else:
            cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag_name,))
            tag_id = cursor.lastrowid
        try:
            cursor.execute('INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)', (post_id, tag_id))
        except Exception:
            pass


def _insert_post(cursor, post_data, user_id, content_format, post_type, access_password):
    cursor.execute("""
        INSERT INTO posts (
            title, content, is_published, category_id, author_id, created_at, updated_at,
            content_format, post_type, type, access_level, access_password, publish_at, source_post_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_data.get('title'), post_data.get('content'), post_data.get('is_published', 0),
        post_data.get('category_id'), user_id, post_data.get('created_at'),
        post_data.get('updated_at'), content_format, post_type,
        post_data.get('type') or 'post', post_data.get('access_level') or 'public',
        access_password, post_data.get('publish_at'), post_data.get('source_post_id'),
    ))
    return cursor.lastrowid


def import_from_json(json_file_path: str, user_id: int = None, dry_run: bool = False) -> Tuple[int, int, List[str]]:
    """Import posts from a full JSON export. Returns (imported, skipped, messages)."""
    messages = []
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
    if user_id is None:
        cursor.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1')
        user = cursor.fetchone()
        if not user:
            conn.close()
            return 0, 0, ["❌ 系统中没有管理员用户，无法导入"]
        user_id = user['id']

    imported_count = 0
    skipped_count = 0
    try:
        conn.execute('BEGIN')
        for post_data in posts:
            try:
                title = (post_data.get('title') or '').strip()
                content = post_data.get('content') or ''
                if not title or not content:
                    skipped_count += 1
                    messages.append("⚠️ 跳过：文章缺少标题或内容")
                    continue

                cursor.execute('SELECT id FROM posts WHERE title = ? AND created_at = ?',
                               (title, post_data.get('created_at')))
                if cursor.fetchone():
                    skipped_count += 1
                    messages.append(f"⚠️ 跳过：文章已存在 - {title}")
                    continue

                category_id = _get_or_create_category(
                    cursor, post_data.get('category_name'),
                    space=post_data.get('category_space') or 'blog',
                    parent_id=post_data.get('category_parent_id'),
                )
                content_format = (post_data.get('content_format') or 'html').lower()
                if content_format not in ('html', 'markdown'):
                    content_format = 'html'
                post_type = post_data.get('post_type') or 'blog'
                access_password = post_data.get('access_password')
                if access_password and post_data.get('access_level') == 'password':
                    try:
                        from models import hash_access_password
                        access_password = hash_access_password(access_password)
                    except Exception:
                        pass
                payload = dict(post_data)
                payload['category_id'] = category_id
                if dry_run:
                    imported_count += 1
                    messages.append(f"🔎 预检通过：{title}")
                    continue
                post_id = _insert_post(cursor, payload, user_id, content_format, post_type, access_password)
                tags = post_data.get('tags') or ''
                if isinstance(tags, str):
                    tags = [t.strip() for t in re.split(r'[,，]', tags) if t.strip()]
                _set_tags(cursor, post_id, tags)
                try:
                    from models.db import _safe_replace_post_fts
                    _safe_replace_post_fts(cursor, post_id, title, content)
                except Exception:
                    pass
                imported_count += 1
                messages.append(f"✅ 导入成功：{title}")
            except Exception as e:
                skipped_count += 1
                messages.append(f"❌ 导入失败：{post_data.get('title', 'Unknown')} - {str(e)}")
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception as e:
        conn.rollback()
        messages.append(f"❌ 导入事务失败，已回滚：{str(e)}")
    finally:
        conn.close()

    prefix = '预检' if dry_run else '导入'
    messages.insert(0, f"📊 {prefix}完成：通过 {imported_count} 篇，跳过 {skipped_count} 篇")
    return imported_count, skipped_count, messages


def import_from_markdown_directory(markdown_dir: str, user_id: int = None, dry_run: bool = False) -> Tuple[int, int, List[str]]:
    """Import Markdown files with YAML frontmatter."""
    messages = []
    markdown_path = Path(markdown_dir)
    if not markdown_path.exists():
        return 0, 0, [f"❌ 目录不存在: {markdown_dir}"]
    md_files = list(markdown_path.glob('**/*.md'))
    if not md_files:
        return 0, 0, [f"❌ 在目录中未找到Markdown文件: {markdown_dir}"]

    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id is None:
        cursor.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1')
        user = cursor.fetchone()
        if not user:
            conn.close()
            return 0, 0, ["❌ 系统中没有管理员用户，无法导入"]
        user_id = user['id']

    imported_count = 0
    skipped_count = 0
    try:
        conn.execute('BEGIN')
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                metadata, body_content = parse_frontmatter(content)
                if not metadata or not metadata.get('title'):
                    skipped_count += 1
                    messages.append(f"⚠️ 跳过：{md_file.name} - 缺少标题元数据")
                    continue
                title = str(metadata.get('title', '')).strip()
                created_at = metadata.get('date')
                if created_at:
                    cursor.execute('SELECT id FROM posts WHERE title = ? AND created_at = ?', (title, created_at))
                    if cursor.fetchone():
                        skipped_count += 1
                        messages.append(f"⚠️ 跳过：文章已存在 - {title}")
                        continue
                post_type = metadata.get('post_type') or 'blog'
                category_id = _get_or_create_category(
                    cursor, metadata.get('category'),
                    space='knowledge' if post_type == 'knowledge' else 'blog',
                )
                tags = metadata.get('tags', [])
                if isinstance(tags, str):
                    tags = [t.strip() for t in re.split(r'[,，]', tags) if t.strip()]
                content_format = str(metadata.get('content_format') or 'markdown').lower()
                if content_format not in ('html', 'markdown'):
                    content_format = 'markdown'
                payload = {
                    'title': title,
                    'content': body_content,
                    'is_published': 1 if metadata.get('published', True) else 0,
                    'category_id': category_id,
                    'created_at': created_at,
                    'updated_at': metadata.get('updated', created_at),
                    'type': metadata.get('type') or 'post',
                    'access_level': metadata.get('access_level') or 'public',
                    'publish_at': metadata.get('publish_at'),
                    'source_post_id': metadata.get('source_post_id'),
                }
                if dry_run:
                    imported_count += 1
                    messages.append(f"🔎 预检通过：{title}")
                    continue
                post_id = _insert_post(cursor, payload, user_id, content_format, post_type, None)
                _set_tags(cursor, post_id, tags)
                try:
                    from models.db import _safe_replace_post_fts
                    _safe_replace_post_fts(cursor, post_id, title, body_content)
                except Exception:
                    pass
                imported_count += 1
                messages.append(f"✅ 导入成功：{title}")
            except Exception as e:
                skipped_count += 1
                messages.append(f"❌ 导入失败：{md_file.name} - {str(e)}")
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception as e:
        conn.rollback()
        messages.append(f"❌ 导入事务失败，已回滚：{str(e)}")
    finally:
        conn.close()

    prefix = '预检' if dry_run else '导入'
    messages.insert(0, f"📊 {prefix}完成：通过 {imported_count} 篇，跳过 {skipped_count} 篇")
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
