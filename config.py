import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
DATABASE_URL = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/posts.db'

UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
