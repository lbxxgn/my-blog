"""
AI功能路由

包括AI标签生成、摘要生成、相关文章推荐、内容续写等功能。
"""

import json
import re

from flask import Blueprint
import logging

from ai_services import TagGenerator

logger = logging.getLogger(__name__)

# 创建 AI 蓝图
ai_bp = Blueprint('ai', __name__, url_prefix='/admin/ai')


def _heuristic_title(content: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', content or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return '未命名记录'
    sentence = re.split(r'[。！？.!?\n]', text)[0].strip()
    return sentence[:24] if sentence else text[:24]


def _heuristic_summary(content: str, max_length: int = 120) -> str:
    text = re.sub(r'<[^>]+>', ' ', content or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + '...'


def _heuristic_type(title: str, content: str) -> str:
    combined = f"{title} {content}".lower()
    daily_keywords = ['今天', '昨天', '周末', '日常', '生活', '旅行', '见闻', '心情']
    knowledge_keywords = ['原理', '教程', '知识', '总结', '学习', '方法', 'flask', 'python', 'sql', 'api']
    idea_keywords = ['想法', '点子', '构想', '计划', '灵感', '尝试']

    if any(keyword in combined for keyword in daily_keywords):
        return 'daily'
    if any(keyword in combined for keyword in knowledge_keywords):
        return 'knowledge'
    if any(keyword in combined for keyword in idea_keywords):
        return 'idea'
    return 'knowledge' if len(combined) > 180 else 'idea'


def _heuristic_tags(title: str, content: str, max_tags: int = 4):
    combined = f"{title} {content}"
    candidates = re.findall(r'[\u4e00-\u9fffA-Za-z0-9#+.-]{2,12}', combined)
    stop_words = {
        '然后', '这个', '那个', '我们', '你们', '他们', '就是', '因为',
        '所以', '如果', '但是', '关于', '可以', '进行', '需要', '一个',
        '自己', '已经', '一下', '还是', '没有', '文章', '内容', '记录'
    }
    tags = []
    for candidate in candidates:
        lowered = candidate.lower()
        if lowered in stop_words or candidate.isdigit():
            continue
        if candidate not in tags:
            tags.append(candidate)
        if len(tags) >= max_tags:
            break
    return tags or ['随记']


def _pick_category(categories, title: str, content: str, tags):
    combined = f"{title} {content} {' '.join(tags or [])}".lower()
    best_match = None
    best_score = 0
    for category in categories or []:
        name = (category.get('name') or '').strip()
        if not name:
            continue
        score = 0
        lowered = name.lower()
        if lowered in combined:
            score += 3
        for fragment in re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', lowered):
            if fragment and fragment in combined:
                score += 1
        if score > best_score:
            best_match = category
            best_score = score
    return best_match


def _run_structured_prompt(user_config, system_prompt: str, user_prompt: str, max_tokens: int = 500, temperature: float = 0.3):
    if not user_config or not user_config.get('ai_tag_generation_enabled'):
        return None

    provider = TagGenerator.create_provider(
        user_config.get('ai_provider', 'dashscope'),
        user_config.get('ai_api_key'),
        user_config.get('ai_model'),
        base_url=user_config.get('ai_base_url')
    )

    if not getattr(provider, 'client', None) and hasattr(provider, '_init_client'):
        provider._init_client()

    response = provider.client.chat.completions.create(
        model=provider.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )

    content = response.choices[0].message.content.strip()
    usage = response.usage
    return {
        'content': content,
        'model': provider.model,
        'tokens_used': usage.total_tokens,
        'input_tokens': usage.prompt_tokens,
        'output_tokens': usage.completion_tokens
    }


def _parse_json_block(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise

# 各功能子模块（在 __init__ 定义共享助手/蓝图之后导入，注册路由）
from . import config, generation, organize, mentor  # noqa: E402,F401
