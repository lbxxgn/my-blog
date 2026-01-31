"""
路由模块

将应用路由拆分为多个蓝图模块：
- auth: 认证相关路由（登录、登出、修改密码）
- blog: 公开博客路由（首页、文章详情、搜索、分类、标签等）
- admin: 管理后台路由（仪表板、文章管理、用户管理等）
- api: API路由（RESTful API、二维码生成等）
- ai: AI功能路由（标签生成、摘要、推荐等）
- knowledge_base: 知识库路由（浏览器插件API、快速记事、时间线、卡片管理）
"""

from .auth import auth_bp
from .blog import blog_bp
from .admin import admin_bp
from .api import api_bp
from .ai import ai_bp
from .knowledge_base import knowledge_base_bp

__all__ = ['auth_bp', 'blog_bp', 'admin_bp', 'api_bp', 'ai_bp', 'knowledge_base_bp']
