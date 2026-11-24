"""首次部署时创建管理员账号。

凭据只能来自环境变量；密码策略比用户自助改密更严（至少 12 位）。
"""

import os
import re

from werkzeug.security import generate_password_hash

from backend.models import create_user, get_user_by_username

__all__ = ['create_admin_user']

MIN_ADMIN_PASSWORD_LENGTH = 12

# 常见弱密码（含 .env.example 历史示例值）
WEAK_ADMIN_PASSWORDS = frozenset({
    'password',
    'admin123',
    '123456789012',
    'password123',
    'yoursecretpassword123!',
})

_MISSING_ENV_MESSAGE = (
    '\n' + '=' * 70 +
    '\n SECURITY ERROR: ADMIN_USERNAME and ADMIN_PASSWORD must be set!' +
    '\n' +
    '\n To set up the admin user, export these environment variables:' +
    "\n   export ADMIN_USERNAME='your_username'" +
    "\n   export ADMIN_PASSWORD='your_secure_password'" +
    '\n' +
    '\n Password requirements:' +
    '\n - At least 12 characters long' +
    '\n - Must contain uppercase and lowercase letters' +
    '\n - Must contain at least one digit' +
    '\n' +
    '=' * 70
)


def _validate_admin_password(password):
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise ValueError('ADMIN_PASSWORD must be at least 12 characters long')
    if not re.search(r'[A-Z]', password):
        raise ValueError('ADMIN_PASSWORD must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise ValueError('ADMIN_PASSWORD must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        raise ValueError('ADMIN_PASSWORD must contain at least one digit')
    if password.lower() in WEAK_ADMIN_PASSWORDS:
        raise ValueError('ADMIN_PASSWORD is too common. Please use a stronger password.')


def create_admin_user():
    """按环境变量创建管理员；已存在时仅提示，不修改密码。"""
    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')

    if not username or not password:
        raise ValueError(_MISSING_ENV_MESSAGE)

    _validate_admin_password(password)

    if get_user_by_username(username):
        print(f'ℹ Admin user already exists: {username}')
        return

    user_id = create_user(username, generate_password_hash(password), role='admin')
    if user_id:
        print(f'✓ Created admin user: {username}')
    else:
        print('✗ Failed to create admin user')
