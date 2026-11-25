"""``flask`` CLI 命令。"""

__all__ = ['register_cli_commands']


def register_cli_commands(app):
    from backend.bootstrap.admin_user import create_admin_user
    from backend.models import init_db

    @app.cli.command()
    def init():
        """Initialize the database and create admin user"""
        init_db()
        create_admin_user()
        print("Database initialized successfully")

    @app.cli.command('weekly-review')
    def weekly_review_command():
        """为「所有开启了 AI 的用户」生成每周回顾（无则退为第一个 admin 用户）

        适合 crontab 定时调用，例如每周一早上：
            0 9 * * 1 cd /path/to/my-blog && .venv/bin/flask --app backend/app.py weekly-review
        """
        from backend.models import get_db_context
        from backend.services.weekly_review import generate_weekly_review

        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username FROM users
                WHERE ai_tag_generation_enabled = 1
                  AND ai_api_key IS NOT NULL AND ai_api_key != ''
                ORDER BY id
            ''')
            users = [dict(r) for r in cursor.fetchall()]
            if not users:
                # 没有启用 AI 的用户时，退而为第一个 admin 生成（会自动降级为纯统计版）
                cursor.execute("SELECT id, username FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
                users = [dict(r) for r in cursor.fetchall()]

            if not users:
                print('没有可生成回顾的用户')
                return

            for user in users:
                try:
                    result = generate_weekly_review(user['id'])
                    if result.get('exists'):
                        print(f"[{user['username']}] 本周回顾已存在: {result['title']} ({result['url']})")
                    elif result.get('success'):
                        mode = 'AI' if result.get('ai_used') else '统计'
                        print(f"[{user['username']}] 已生成（{mode}版）: {result['title']} ({result['url']})")
                    else:
                        print(f"[{user['username']}] 生成失败: {result.get('error')}")
                except Exception as e:
                    print(f"[{user['username']}] 生成异常: {e}")
