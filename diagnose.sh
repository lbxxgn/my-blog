#!/bin/bash

echo "=============================================="
echo "诊断脚本 - Simple Blog"
echo "=============================================="

echo ""
echo "1. 检查 Flask 进程:"
ps aux | grep -i "python.*app.py" | grep -v grep || echo "   ✓ 没有 Flask 进程运行"

echo ""
echo "2. 检查数据库触发器:"
python3 << 'PYTHON'
import sqlite3
conn = sqlite3.connect('/Users/gn/simple-blog/db/posts.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
triggers = cursor.fetchall()
if triggers:
    print(f"   ⚠ 发现 {len(triggers)} 个触发器:")
    for t in triggers:
        print(f"     - {t[0]}")
    print("")
    print("   解决方案: python3 /Users/gn/simple-blog/fix_db.py")
else:
    print("   ✓ 无触发器")
conn.close()
PYTHON

echo ""
echo "3. 检查代码更新:"
grep -n "Manually update FTS" /Users/gn/simple-blog/backend/models.py && echo "   ✓ models.py 已更新" || echo "   ✗ models.py 未更新"

echo ""
echo "=============================================="
