"""
Utility Model Functions

HTML 清理与文本截断工具函数（无数据库依赖）。
"""

__all__ = [
    'strip_html_tags',
    'truncate_text',
]


def strip_html_tags(html_content):
    """
    移除HTML标签，保留纯文本

    Args:
        html_content: 包含HTML的文本

    Returns:
        str: 纯文本内容
    """
    import re

    if not html_content:
        return ""

    # 移除script和style标签及其内容
    html_content = re.sub(r'<script[^>]*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*?>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # 替换HTML标签
    html_content = re.sub(r'<[^>]+>', '', html_content)

    # 替换HTML实体
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
    html_content = html_content.strip()

    return html_content


def truncate_text(text, max_length=200, suffix='...'):
    """
    截断文本到指定长度，避免在单词中间截断

    Args:
        text: 要截断的文本
        max_length: 最大长度
        suffix: 截断后添加的后缀

    Returns:
        str: 截断后的文本
    """
    if not text:
        return ""

    # 先移除HTML标签
    text = strip_html_tags(text)

    # 如果文本已经足够短，直接返回
    if len(text) <= max_length:
        return text

    # 截断到最大长度
    truncated = text[:max_length]

    # 尝试在最后一个空格处截断，避免截断单词
    last_space = truncated.rfind(' ')

    if last_space > max_length * 0.8:  # 如果最后一个空格在80%位置之后
        truncated = truncated[:last_space]

    return truncated + suffix
