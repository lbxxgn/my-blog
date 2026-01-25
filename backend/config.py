import os
from pathlib import Path

# Backend directory
BACKEND_DIR = Path(__file__).parent
# Project root directory (one level up from backend)
BASE_DIR = BACKEND_DIR.parent

SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
DATABASE_URL = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/db/posts.db'

# Site settings
SITE_NAME = os.environ.get('SITE_NAME') or '我的博客'
SITE_DESCRIPTION = os.environ.get('SITE_DESCRIPTION') or '一个简单的博客系统'
SITE_AUTHOR = os.environ.get('SITE_AUTHOR') or '管理员'

UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Debug mode (set via environment variable)
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Environment detection
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production' or not DEBUG

# Session security settings
# Note: SESSION_COOKIE_SECURE should only be True if using HTTPS
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
