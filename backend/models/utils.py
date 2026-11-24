"""
Utility Model Functions

纯文本工具的实现已统一到 ``backend.utils.text``，这里仅做 re-export，
保持 ``from backend.models import strip_html_tags, truncate_text`` 等历史导入路径可用。
"""

from backend.utils.text import strip_html_tags, truncate_text

__all__ = [
    'strip_html_tags',
    'truncate_text',
]
