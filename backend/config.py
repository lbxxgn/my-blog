import os
from pathlib import Path

# Backend directory
BACKEND_DIR = Path(__file__).parent
# Project root directory (one level up from backend)
BASE_DIR = BACKEND_DIR.parent

SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
DATABASE_URL = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/db/posts.db'

UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

# Debug mode (set via environment variable)
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Environment detection
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production' or not DEBUG

# Session security settings (only enabled in production)
if IS_PRODUCTION:
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection for cookies
else:
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
