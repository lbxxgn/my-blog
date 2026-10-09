"""
内容格式标注纠偏迁移

背景：渲染管道按 content_format 分流后（markdown 走 markdown2，html 只清洗不解析），
历史数据中大量纯文本/Markdown 文章被默认标注为 'html'（老迁移把所有 NULL 一律标成 html），
若不排除纠偏，这些文章将停止 Markdown 渲染，显示原始符号。

策略：只处理 content_format 为 NULL 或 'html' 的行；内容含块级 HTML 标签的保持 'html'，
其余一律改为 'markdown'。已是 'markdown' 的行不动。幂等。
"""
import re
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config

# 块级/富文本特征标签：Quill 等富文本编辑器产出的 HTML 必然命中其一；
# Markdown 正文里偶尔出现的行内标签（<em>/<a>/<strong>/<img> 等）不触发，避免误伤。
_BLOCK_TAG_RE = re.compile(
    r'</?(?:p|div|h[1-6]|ul|ol|li|blockquote|pre|table|thead|tbody|tr|td|th|'
    r'figure|figcaption|iframe|section|article|br|hr|font|center|dl|dt|dd|'
    r'details|summary|video|audio|caption|colgroup)\b',
    re.IGNORECASE,
)


def _detect_format(content):
    content = content or ''
    if _BLOCK_TAG_RE.search(content):
        return 'html'
    return 'markdown'


def migrate():
    db_path = Path(config.DATABASE_URL.replace('sqlite:///', ''))

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 兼容旧库：posts 表可能还没有 content_format 列
        columns = {row[1] for row in cursor.execute('PRAGMA table_info(posts)')}
        if 'content_format' not in columns:
            print("   ⏭️  posts 表无 content_format 列，跳过")
            return True

        rows = cursor.execute('''
            SELECT id, content FROM posts
            WHERE content_format IS NULL OR content_format = 'html'
        ''').fetchall()

        to_markdown = 0
        kept_html = 0
        for post_id, content in rows:
            if _detect_format(content) == 'markdown':
                cursor.execute(
                    "UPDATE posts SET content_format = 'markdown' WHERE id = ?",
                    (post_id,),
                )
                to_markdown += 1
            else:
                kept_html += 1

        conn.commit()
        print(f"   ✅ 纠偏为 markdown: {to_markdown} 篇，保持 html: {kept_html} 篇")
        print("✅ 内容格式标注纠偏完成")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
