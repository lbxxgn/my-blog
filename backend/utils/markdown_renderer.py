"""Markdown -> 安全 HTML 的统一渲染（博客正文与知识库文档共用）。

历史实现分别在 routes/blog.py 与 routes/knowledge.py 各写了一份 markdown2 + bleach
的清洗逻辑（含逐字复制的 CSS 兜底清洗器）。此处合并，仅用 ``with_header_ids``
区分两处差异（知识库保留标题锚点 id）。
"""

import bleach
import markdown2

# 允许的 HTML 标签（两处历史实现一致）
ALLOWED_TAGS = [
    'p', 'a', 'strong', 'em', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'table', 'thead', 'tbody',
    'tr', 'th', 'td', 'img', 'div', 'span',
]

# 允许的行内样式（编辑器首行缩进等）
ALLOWED_CSS = {'text-indent', 'padding-left', 'margin-left'}


class _SimpleCSSSanitizer:
    """tinycss2 不可用时的极简 CSS 清洗兜底。

    bleach 会调用通过 ``css_sanitizer`` 传入对象的 ``sanitize_css``，方法名必须一致。
    """

    def __init__(self, allowed_properties):
        self.allowed_properties = {p.lower() for p in allowed_properties}

    def sanitize_css(self, css):
        if not css:
            return ''
        cleaned = []
        for decl in css.split(';'):
            decl = decl.strip()
            if not decl or ':' not in decl:
                continue
            prop = decl.split(':', 1)[0].strip().lower()
            if prop in self.allowed_properties:
                cleaned.append(decl)
        return '; '.join(cleaned) + ';' if cleaned else ''

    # 旧版 bleach 使用 ``sanitize``；两者都保留以兼容。
    sanitize = sanitize_css


try:  # pragma: no cover - 取决于 bleach/tinycss2 版本
    from bleach.css_sanitizer import CSSSanitizer
    _CSS_SANITIZER = CSSSanitizer(allowed_css_properties=list(ALLOWED_CSS))
except Exception:  # pragma: no cover
    _CSS_SANITIZER = _SimpleCSSSanitizer(ALLOWED_CSS)


def render_markdown(content, with_header_ids=False):
    """把 Markdown 渲染为经过 bleach 清洗的安全 HTML。

    Args:
        content: Markdown 文本
        with_header_ids: 是否为标题生成 id 锚点（知识库目录需要）
    """
    extras = ['fenced-code-blocks', 'tables']
    star_attrs = ['class', 'style']
    if with_header_ids:
        extras.append('header-ids')
        star_attrs = ['class', 'id', 'style']

    html = markdown2.markdown(content or '', extras=extras)
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes={
            'a': ['href', 'title', 'rel'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            '*': star_attrs,
        },
        css_sanitizer=_CSS_SANITIZER,
        strip_comments=False,
    )
