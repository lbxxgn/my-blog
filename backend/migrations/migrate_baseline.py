"""基线 schema：空库首次安装时创建基础表结构。

迁移 001-015 只负责增量变更，因此必须在最前面执行基线。
实现复用 models.init_db()，保证基线定义只有一份。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.models import init_db


def migrate():
    init_db()
    print('✅ 基线 schema 已创建/校验')
    return True


if __name__ == '__main__':
    migrate()
