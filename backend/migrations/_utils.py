"""迁移脚本共用的连接与入口助手。

历史脚本各自复制了「建连接 → try/except → commit/rollback → close」样板，
错误处理方式也不一致（有的打印后 ``return False``，运行器却仍把它记为已应用）。
这里收敛为上下文管理器：成功提交、异常回滚并继续抛出，由运行器统一标记失败。
"""

import sqlite3
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

__all__ = ['db_path', 'transaction', 'run_cli']


def db_path():
    """当前 ``DATABASE_URL`` 指向的 SQLite 文件路径。"""
    import backend.config as config

    return Path(config.DATABASE_URL.replace('sqlite:///', ''))


@contextmanager
def transaction(path=None):
    """打开一个迁移事务：正常结束时 commit，出错时 rollback 并重新抛出。"""
    conn = sqlite3.connect(str(path or db_path()))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_cli(migrate, title=None):
    """脚本直接运行时的统一入口，返回进程退出码。"""
    if title:
        print('=' * 50)
        print(title)
        print('=' * 50)

    try:
        migrate()
    except Exception as e:
        print(f'❌ 迁移失败: {e}')
        traceback.print_exc()
        return 1
    return 0
