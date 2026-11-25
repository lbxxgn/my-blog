"""
迁移脚本：添加文章访问控制功能
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing


def migrate():
    """添加文章访问控制字段"""
    with transaction() as conn:
        added = add_columns_if_missing(conn, 'posts', [
            ('access_level', "TEXT DEFAULT 'public'"),
            ('access_password', 'TEXT'),
        ])
        for name in added:
            print(f"✓ {name} 字段已添加")
        if not added:
            print("⏭️  access_level / access_password 字段已存在")

    print("\n✅ 文章访问控制功能迁移完成！")
    print("\n支持的访问级别：")
    print("  - public: 公开（所有人可见）")
    print("  - login: 登录用户（仅登录用户可见）")
    print("  - password: 密码保护（需输入密码）")
    print("  - private: 私密（仅作者和管理员可见）")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '文章访问控制 - 数据库迁移'))
