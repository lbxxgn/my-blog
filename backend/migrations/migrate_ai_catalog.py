"""
AI 提供商与模型目录迁移
- 新建 ai_providers / ai_models 表
- 首次迁移写入内置供应商、模型与价格（幂等）
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config
from ai_services.provider_defaults import DEFAULT_CATALOG


def _seed_default_catalog(conn):
    for provider in DEFAULT_CATALOG:
        conn.execute('''
            INSERT OR IGNORE INTO ai_providers
                (slug, name, description, driver, base_url, currency,
                 allow_custom_model, requires_base_url, enabled, is_builtin, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            provider['slug'],
            provider['name'],
            provider.get('description') or '',
            provider['driver'],
            provider.get('base_url'),
            provider.get('currency') or 'CNY',
            1 if provider.get('allow_custom_model') else 0,
            1 if provider.get('requires_base_url') else 0,
            1 if provider.get('enabled', True) else 0,
            1 if provider.get('is_builtin') else 0,
            provider.get('sort_order') or 0,
        ))
        row = conn.execute(
            'SELECT id FROM ai_providers WHERE slug = ?', (provider['slug'],)
        ).fetchone()
        if not row:
            continue
        for model in provider.get('models') or []:
            conn.execute('''
                INSERT OR IGNORE INTO ai_models
                    (provider_id, model_id, display_name, description,
                     input_price, output_price, enabled, is_default, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['id'],
                model['model_id'],
                model.get('display_name') or model['model_id'],
                model.get('description') or '',
                model.get('input_price'),
                model.get('output_price'),
                1 if model.get('enabled', True) else 0,
                1 if model.get('is_default') else 0,
                model.get('sort_order') or 0,
            ))


def migrate():
    db_path = Path(config.DATABASE_URL.replace('sqlite:///', ''))

    if not db_path.exists():
        raise RuntimeError(f'数据库文件不存在: {db_path}')

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ai_providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                driver TEXT NOT NULL,
                base_url TEXT,
                currency TEXT NOT NULL DEFAULT 'CNY',
                allow_custom_model BOOLEAN DEFAULT 0,
                requires_base_url BOOLEAN DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                is_builtin BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ai_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                display_name TEXT,
                description TEXT,
                input_price REAL,
                output_price REAL,
                enabled BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider_id, model_id),
                FOREIGN KEY(provider_id) REFERENCES ai_providers(id) ON DELETE CASCADE
            )
        ''')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_ai_models_provider '
            'ON ai_models(provider_id, sort_order, id)'
        )

        count = conn.execute('SELECT COUNT(*) FROM ai_providers').fetchone()[0]
        if count == 0:
            _seed_default_catalog(conn)

        conn.commit()
        print('   ✅ 创建表: ai_providers / ai_models，并写入内置目录')
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
