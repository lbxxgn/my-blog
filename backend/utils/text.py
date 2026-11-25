"""纯文本处理工具（无数据库依赖）。

``strip_html_tags`` / ``truncate_text`` 原先寄居在 ``backend.models.utils``，
现在由本模块持有，模型层只做 re-export，保持 ``backend.models`` 的导入路径不变。
"""

import re

__all__ = [
    'strip_html_tags',
    'truncate_text',
    'auto_title',
    'heuristic_summary',
]


def strip_html_tags(html_content):
    """移除 HTML 标签与常见实体，返回压缩空白后的纯文本。"""
    if not html_content:
        return ""

    # 移除 script/style 标签及其内容
    html_content = re.sub(r'<script[^>]*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*?>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # 替换 HTML 标签
    html_content = re.sub(r'<[^>]+>', '', html_content)

    # 替换 HTML 实体
    html_entities = {
        '&nbsp;': ' ',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'",
        '&copy;': '©',
        '&reg;': '®',
        '&mdash;': '—',
        '&ndash;': '–',
        '&hellip;': '…',
        '&#39;': "'",
        '&#34;': '"',
    }
    for entity, char in html_entities.items():
        html_content = html_content.replace(entity, char)

    # 清理多余的空白
    html_content = re.sub(r'\s+', ' ', html_content)
    return html_content.strip()


def truncate_text(text, max_length=200, suffix='...'):
    """截断文本到指定长度，尽量不在单词中间截断。"""
    if not text:
        return ""

    text = strip_html_tags(text)

    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # 空格出现在末尾 20% 时才回退，避免截得过短
        truncated = truncated[:last_space]

    return truncated + suffix


def auto_title(content, max_length=24, fallback='未命名记录'):
    """从正文中取首句作为标题（无标题时的兜底）。

    后台新建文章、AI 标题生成失败时的启发式回退都使用同一实现。
    """
    text = strip_html_tags(content)
    if not text:
        return fallback
    sentence = re.split(r'[。！？.!?\n]', text)[0].strip()
    return sentence[:max_length] if sentence else text[:max_length]


def heuristic_summary(content, max_length=120):
    """无 AI 时按正文截断生成摘要。"""
    text = strip_html_tags(content)
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + '...'
