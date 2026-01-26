"""
AI Services Module for Simple Blog

This module provides AI-powered features for the blog, including:
- Automatic tag generation
- Content analysis
- Multiple LLM provider support (OpenAI, Claude, Qwen)
"""

from .tag_generator import TagGenerator

__all__ = ['TagGenerator']
