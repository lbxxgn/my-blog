import os
from pathlib import Path

# =============================================================================
# 路径配置
# =============================================================================

# Backend directory
BACKEND_DIR = Path(__file__).parent
# Project root directory (one level up from backend)
BASE_DIR = BACKEND_DIR.parent

# =============================================================================
# 安全配置
# =============================================================================

# Flask密钥（生产环境必须修改）
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

# =============================================================================
# 数据库配置
# =============================================================================

# SQLite数据库路径
DATABASE_URL = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/db/simple_blog.db'

# =============================================================================
# 网站设置
# =============================================================================

# 网站名称（显示在导航栏和浏览器标签）
SITE_NAME = os.environ.get('SITE_NAME') or '我的博客'

# 网站描述（用于SEO和meta标签）
SITE_DESCRIPTION = os.environ.get('SITE_DESCRIPTION') or '一个简单的博客系统'

# 网站作者
SITE_AUTHOR = os.environ.get('SITE_AUTHOR') or '管理员'

# =============================================================================
# 文件上传配置
# =============================================================================

# 上传文件存储目录
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# 允许的图片文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# 最大上传文件大小（16MB）
# 注意：这是全局限制，对单个请求生效
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# =============================================================================
# CSRF保护配置
# =============================================================================

# 是否启用CSRF保护（默认启用）
WTF_CSRF_ENABLED = True

# CSRF令牌有效期（None表示永久有效）
WTF_CSRF_TIME_LIMIT = None

# 是否在HTTPS下严格检查CSRF令牌（HTTPS环境应设置为True）
WTF_CSRF_SSL_STRICT = False  # Set to True if using HTTPS

# =============================================================================
# 环境和调试配置
# =============================================================================

# 调试模式（开发环境设置为true，生产环境设置为false）
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# 环境检测
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production' or not DEBUG

# =============================================================================
# 会话安全配置
# =============================================================================
# 注意：SESSION_COOKIE_SECURE should only be True if using HTTPS
# Set FORCE_HTTPS environment variable to True if you have HTTPS enabled
FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() in ('true', '1', 'yes')

if IS_PRODUCTION and FORCE_HTTPS:
    # Production with HTTPS
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection for cookies
else:
    # Development or Production without HTTPS
    SESSION_COOKIE_SECURE = False  # Allow cookies over HTTP
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection for cookies

# =============================================================================
# AI功能配置
# =============================================================================

# AI默认配置
AI_DEFAULT_PROVIDER = os.environ.get('AI_DEFAULT_PROVIDER') or 'openai'
AI_DEFAULT_MODEL = os.environ.get('AI_DEFAULT_MODEL') or 'gpt-3.5-turbo'

# AI功能限流（每小时最大请求次数）
AI_RATE_LIMIT_PER_HOUR = int(os.environ.get('AI_RATE_LIMIT_PER_HOUR', 10))

# AI内容截断长度（字符数）
AI_CONTENT_MAX_LENGTH = int(os.environ.get('AI_CONTENT_MAX_LENGTH', 500))

# 是否启用AI历史记录（默认启用）
AI_HISTORY_ENABLED = os.environ.get('AI_HISTORY_ENABLED', 'True').lower() in ('true', '1', 'yes')

# 支持的AI提供商和模型
AI_SUPPORTED_PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'models': ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4-turbo', 'gpt-4'],
        'default_model': 'gpt-3.5-turbo'
    },
    'volcengine': {
        'name': '火山引擎',
        'models': ['doubao-pro-32k', 'doubao-pro-4k', 'doubao-lite-4k'],
        'default_model': 'doubao-pro-4k'
    },
    'dashscope': {
        'name': '阿里百炼',
        'models': [
            'qwen-flash',
            'qwen-turbo',
            'qwen-plus',
            'qwen-max',
            'qwen-coder-plus',
            'qwen-coder-plus-1106',
            'qwen-coder-plus-latest',
            'qwen-long-latest',
            'qwen-long-2025-01-25',
            'qwen-vl-max',
            'qwen-vl-max-latest',
        ],
        'default_model': 'qwen-turbo'
    },
    # 未来可添加更多提供商
    # 'claude': {
    #     'name': 'Anthropic Claude',
    #     'models': ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229'],
    #     'default_model': 'claude-3-haiku-20240307'
    # },
}
