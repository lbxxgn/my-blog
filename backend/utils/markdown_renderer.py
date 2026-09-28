"""Markdown -> 安全 HTML 的统一渲染（博客正文与知识库文档共用）。

历史实现分别在 routes/blog.py 与 routes/knowledge.py 各写了一份 markdown2 + bleach
的清洗逻辑（含逐字复制的 CSS 兜底清洗器）。此处合并，仅用 ``with_header_ids``
区分两处差异（知识库保留标题锚点 id）。
"""

import re

import bleach
import markdown2

# Quill 2.x 会为代码块插入语言选择 <select class="ql-ui">，它是编辑器内部控件，
# 阅读端应整体删除（连内容），否则 bleach 会留下 option 文本污染代码块。
_QUILL_SELECT_RE = re.compile(r'<select\b[^>]*>.*?</select>', re.IGNORECASE | re.DOTALL)


def _strip_editor_widgets(html):
    return _QUILL_SELECT_RE.sub('', html or '')

# 允许的 HTML 标签。
# 说明：博客正文由 Quill 产出 HTML，历史导入内容还包含 font/align 等旧式标签。
# 这份白名单需覆盖富文本编辑器实际会产生的语义标签，否则 bleach 会把内容“洗没了”。
ALLOWED_TAGS = [
    # 文本语义
    'p', 'a', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del', 'ins',
    'mark', 'small', 'big', 'sub', 'sup', 'abbr', 'code', 'pre', 'blockquote',
    'span', 'div', 'font', 'br', 'hr', 'wbr', 'center',
    # 标题
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    # 列表
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    # 表格
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'col', 'colgroup',
    # 媒体
    'img', 'figure', 'figcaption', 'iframe', 'video', 'audio', 'source',
    # 折叠
    'details', 'summary',
]

# 允许的行内样式。
# 覆盖颜色/字号/对齐/缩进等常见富文本格式；刻意排除 position/top/left/z-index
# 等可用于点击劫持或覆盖 UI 的属性，避免 CSS 注入影响页面结构。
ALLOWED_CSS = {
    'color', 'background-color', 'text-align', 'text-indent', 'text-decoration',
    'font-size', 'font-family', 'font-weight', 'font-style', 'line-height',
    'letter-spacing', 'white-space', 'word-wrap', 'word-break', 'overflow-wrap',
    'vertical-align',
    'padding', 'padding-left', 'padding-right', 'padding-top', 'padding-bottom',
    'margin', 'margin-left', 'margin-right', 'margin-top', 'margin-bottom',
    'border', 'border-radius', 'width', 'max-width', 'min-width',
    'height', 'max-height',
}

# 允许的属性。on* 事件属性由 bleach 统一剥离，javascript: 协议也会被过滤。
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'srcset', 'sizes', 'loading'],
    'font': ['color', 'face', 'size'],
    'iframe': ['src', 'width', 'height', 'title', 'allow', 'allowfullscreen',
               'frameborder', 'loading'],
    'video': ['src', 'poster', 'width', 'height', 'controls', 'preload', 'playsinline'],
    'audio': ['src', 'controls', 'preload'],
    'source': ['src', 'type', 'srcset', 'media'],
    'td': ['colspan', 'rowspan', 'align', 'valign', 'width', 'height'],
    'th': ['colspan', 'rowspan', 'align', 'valign', 'width', 'height', 'scope'],
    'table': ['width', 'border', 'cellpadding', 'cellspacing'],
    'ol': ['type', 'start', 'reversed'],
    # Quill 2.x 用 <li data-list="bullet|ordered|checked|unchecked"> 表达列表类型
    'li': ['value', 'data-list'],
    'details': ['open'],
    '*': ['class', 'id', 'style', 'align', 'title'],
}


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
    if with_header_ids:
        extras.append('header-ids')

    html = markdown2.markdown(content or '', extras=extras)
    html = _strip_editor_widgets(html)
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=_CSS_SANITIZER,
        strip_comments=False,
    )
