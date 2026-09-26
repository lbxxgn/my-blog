"""
Site Settings Model Functions

站点级键值配置（目前用于自定义站点图标版本等）。
"""

import sqlite3

from .db import get_db_connection

__all__ = [
    'ensure_site_settings_table',
    'get_site_setting',
    'set_site_setting',
    'delete_site_setting',
    'get_site_icon_version',
]


def ensure_site_settings_table():
    """确保站点配置表存在（幂等）。"""
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    finally:
        conn.close()


def get_site_setting(key, default=None):
    """读取站点配置；表不存在时安全降级为默认值。"""
    conn = get_db_connection()
    try:
        try:
            row = conn.execute(
                'SELECT value FROM site_settings WHERE key = ?', (key,)
            ).fetchone()
        except sqlite3.OperationalError:
            return default
        return row['value'] if row else default
    finally:
        conn.close()


def set_site_setting(key, value):
    """写入（或覆盖）站点配置。"""
    ensure_site_settings_table()
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO site_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        ''', (key, str(value)))
        conn.commit()
    finally:
        conn.close()


def delete_site_setting(key):
    """删除一条站点配置。"""
    conn = get_db_connection()
    try:
        try:
            conn.execute('DELETE FROM site_settings WHERE key = ?', (key,))
            conn.commit()
        except sqlite3.OperationalError:
            pass
    finally:
        conn.close()


def get_site_icon_version():
    """返回自定义图标的版本号（用于缓存失效），无自定义图标时为 '0'。"""
    return get_site_setting('icon_version') or '0'
