# -*- coding: utf-8 -*-
"""版本化迁移运行器测试（backend/migrations/__init__.py）"""
import importlib
import os
import sqlite3
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import backend.config as config


@pytest.fixture()
def migration_db():
    """提供一个带完整初始 schema 的临时数据库，并让 config 指向它"""
    os.environ['TESTING'] = '1'
    db_path = tempfile.gettempdir() + f'/test_migrations_{uuid.uuid4().hex}.db'
    original_env = os.environ.get('DATABASE_URL')

    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    importlib.reload(config)

    import models
    models.init_db()

    yield db_path

    # 恢复原配置
    if original_env is not None:
        os.environ['DATABASE_URL'] = original_env
    else:
        os.environ.pop('DATABASE_URL', None)
    importlib.reload(config)
    if os.path.exists(db_path):
        os.remove(db_path)


def _applied_versions(db_path):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute('SELECT version FROM schema_migrations ORDER BY version').fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def test_schema_migrations_table_created_by_init_db(migration_db):
    """init_db 应创建迁移版本表"""
    conn = sqlite3.connect(migration_db)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_apply_migrations_marks_all_applied(migration_db):
    """首次运行应用全部迁移并记录版本"""
    from backend.migrations import MIGRATIONS, apply_migrations

    done, skipped, failed = apply_migrations(verbose=False)

    assert failed == []
    assert done == len(MIGRATIONS)
    assert skipped == 0
    assert _applied_versions(migration_db) == sorted(v for v, *_ in MIGRATIONS)


def test_apply_migrations_is_idempotent(migration_db):
    """重复运行不再应用任何迁移（版本表生效）"""
    from backend.migrations import MIGRATIONS, apply_migrations

    apply_migrations(verbose=False)
    done, skipped, failed = apply_migrations(verbose=False)

    assert failed == []
    assert done == 0
    assert skipped == len(MIGRATIONS)
