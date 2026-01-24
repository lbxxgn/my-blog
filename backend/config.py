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
