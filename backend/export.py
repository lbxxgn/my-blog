"""Article export functionality for backup."""
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import get_db_connection
from backend.config import BASE_DIR

POST_SELECT = '''
    SELECT
        p.id, p.title, p.content, p.created_at, p.updated_at, p.is_published,
        p.post_type, p.type, p.content_format, p.access_level, p.access_password,
        p.publish_at, p.source_post_id,
        c.name as category_name, c.space as category_space, c.parent_id as category_parent_id,
        GROUP_CONCAT(t.name, ',') as tags
    FROM posts p
    LEFT JOIN categories c ON p.category_id = c.id
    LEFT JOIN post_tags pt ON p.id = pt.post_id
    LEFT JOIN tags t ON pt.tag_id = t.id
    WHERE p.deleted_at IS NULL
    GROUP BY p.id
    ORDER BY p.created_at DESC
'''


def _load_posts(post_type=None):
    conn = get_db_connection()
    try:
        sql = POST_SELECT
        params = []
        if post_type:
            sql = sql.replace('WHERE p.deleted_at IS NULL', 'WHERE p.deleted_at IS NULL AND p.post_type = ?')
            params.append(post_type)
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _copy_upload_images(destination):
    source = BASE_DIR / 'static' / 'uploads' / 'images'
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    if source.exists():
        for file_path in source.iterdir():
            if file_path.is_file():
                shutil.copy2(file_path, destination / file_path.name)
                copied += 1
    return copied


def export_all_posts_to_markdown(output_dir='exports', post_type=None):
    """Export all posts to individual markdown files, including uploaded images."""
    export_path = Path(output_dir)
    export_path.mkdir(exist_ok=True)
    posts_dir = export_path / 'posts'
    posts_dir.mkdir(exist_ok=True)
    images_dir = export_path / 'images'

    posts = _load_posts(post_type)
    exported_count = 0
    for post in posts:
        markdown = f"""---
title: {post['title']}
date: {post['created_at']}
updated: {post.get('updated_at', post['created_at'])}
published: {bool(post['is_published'])}
post_type: {post.get('post_type') or 'blog'}
type: {post.get('type') or 'post'}
content_format: {post.get('content_format') or 'html'}
access_level: {post.get('access_level') or 'public'}
category: {post['category_name'] or 'Uncategorized'}
tags: [{post['tags'] or ''}]
---

{post['content']}
"""
        safe_title = "".join(c for c in post['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{post['id']}_{safe_title[:50]}.md"
        (posts_dir / filename).write_text(markdown, encoding='utf-8')
        exported_count += 1

    image_count = _copy_upload_images(images_dir)
    readme = f"""# Blog Export

Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Total Posts: {exported_count}
Images: {image_count}

- posts/: Markdown files
- images/: uploaded images
"""
    (export_path / 'README.md').write_text(readme, encoding='utf-8')
    return exported_count, str(export_path.absolute())


def export_to_json(output_dir='exports', post_type=None):
    """Export all posts (full fields) to a single JSON file."""
    export_path = Path(output_dir)
    export_path.mkdir(exist_ok=True)
    posts = _load_posts(post_type)
    export_data = {
        'export_date': datetime.now().isoformat(),
        'total_posts': len(posts),
        'posts': posts,
    }
    output_file = export_path / f'blog_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    output_file.write_text(json.dumps(export_data, ensure_ascii=False, indent=2), encoding='utf-8')
    return len(posts), str(output_file.absolute())


def export_full_archive(output_dir='exports', post_type=None):
    """Create a ZIP containing full JSON metadata and uploaded images."""
    export_path = Path(output_dir)
    export_path.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='blog_export_') as tmp:
        tmp_path = Path(tmp)
        count, json_path = export_to_json(str(tmp_path), post_type=post_type)
        _copy_upload_images(tmp_path / 'images')
        archive = export_path / f'blog_full_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_path, 'blog_export.json')
            for image in (tmp_path / 'images').glob('*'):
                if image.is_file():
                    zf.write(image, f'images/{image.name}')
            zf.writestr('README.txt', f'Full export generated at {datetime.now().isoformat()}\nPosts: {count}\n')
    return count, str(archive.absolute())


if __name__ == '__main__':
    print("Starting blog export...")
    count, path = export_all_posts_to_markdown()
    print(f"Exported {count} posts to {path}/posts/")
    count, path = export_to_json()
    print(f"Exported {count} posts to {path}")
