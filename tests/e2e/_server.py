#!/usr/bin/env python3
"""Start an isolated Flask server with a seeded temporary database for E2E tests.

The process is launched by ``tests/e2e/conftest.py``. It is intentionally a
separate process so the browser tests cannot interfere with the regular pytest
fixtures or the developer's local database.
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ADMIN_USERNAME = 'e2e_admin'
ADMIN_PASSWORD = 'E2ePassword123!'


def seed_database() -> dict:
    """Create deterministic data used by the browser tests."""
    from werkzeug.security import generate_password_hash

    from backend.models import (
        create_category,
        create_comment,
        create_kb_category,
        create_knowledge_doc,
        create_post,
        create_user,
        get_post_tags,
        set_post_tags,
    )

    admin_id = create_user(
        ADMIN_USERNAME,
        generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256'),
        role='admin',
        display_name='E2E 管理员',
        bio='端到端测试管理员',
    )
    if not admin_id:
        raise RuntimeError('failed to create E2E admin user')

    category_id = create_category('E2E 分类')
    if not category_id:
        raise RuntimeError('failed to create E2E category')

    published_id = create_post(
        title='E2E 已发布文章',
        content='<p>这是用于端到端测试的已发布文章。</p><p>关键词：e2e-marker</p>',
        is_published=True,
        category_id=category_id,
        author_id=admin_id,
    )
    second_post_id = create_post(
        title='E2E 已发布文章二',
        content='<p>用于首页列表和归档页验证的第二篇文章。</p>',
        is_published=True,
        category_id=category_id,
        author_id=admin_id,
    )
    draft_id = create_post(
        title='E2E 草稿文章',
        content='<p>这是草稿内容 e2e-draft-marker。</p>',
        is_published=False,
        category_id=category_id,
        author_id=admin_id,
    )
    set_post_tags(published_id, ['E2E标签', '自动化'])

    published_tags = get_post_tags(published_id)
    tag_id = published_tags[0]['id'] if published_tags else None

    comment_id = create_comment(
        published_id,
        author_name='E2E 种子访客',
        author_email='seed@example.com',
        content='这是一条 E2E 种子评论。',
    )

    kb_category_id = create_kb_category('E2E 知识库目录')
    kb_doc_id = create_knowledge_doc(
        title='E2E 知识库文档',
        content='# E2E 知识库文档\n\n这是知识库内容 e2e-kb-marker。',
        category_id=kb_category_id,
        tag_names=['知识库'],
        is_published=True,
        author_id=admin_id,
    )

    return {
        'admin_username': ADMIN_USERNAME,
        'admin_password': ADMIN_PASSWORD,
        'admin_id': admin_id,
        'category_id': category_id,
        'tag_id': tag_id,
        'post_id': published_id,
        'second_post_id': second_post_id,
        'draft_id': draft_id,
        'comment_id': comment_id,
        'kb_category_id': kb_category_id,
        'kb_doc_id': kb_doc_id,
        'post_title': 'E2E 已发布文章',
        'draft_title': 'E2E 草稿文章',
        'kb_doc_title': 'E2E 知识库文档',
        'seed_comment': '这是一条 E2E 种子评论。',
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--seed-out', required=True)
    parser.add_argument('--port', required=True, type=int)
    args = parser.parse_args()

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    os.environ['TESTING'] = '1'
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ.setdefault('SECRET_KEY', 'e2e-secret-key-not-for-production')
    os.environ.setdefault('SITE_NAME', 'E2E 博客')
    os.environ.setdefault('SITE_DESCRIPTION', '端到端测试站点')
    os.environ.setdefault('SITE_AUTHOR', 'E2E')
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FORCE_HTTPS', 'False')
    os.environ['BACKUP_SCHEDULE_ENABLED'] = 'False'

    from backend.migrations import apply_migrations
    from backend.models import init_db

    init_db()
    _, _, failed = apply_migrations(verbose=False)
    if failed:
        raise SystemExit(f'E2E schema migrations failed: {failed}')

    seed = seed_database()
    Path(args.seed_out).write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding='utf-8')

    from backend.app import create_app

    app = create_app({
        'TESTING': True,
        'DEBUG': False,
        'WTF_CSRF_ENABLED': True,
        'RATELIMIT_ENABLED': False,
        'SETUP_LOGGING': False,
        'REGENERATE_ASSETS': False,
        'CACHE_TYPE': 'NullCache',
    })
    app.config['RATELIMIT_ENABLED'] = False
    try:
        app.limiter.enabled = False
    except Exception:
        pass

    app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False, threaded=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
