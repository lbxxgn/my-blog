"""敏感配置的最小加密工具。

使用 SECRET_KEY 派生 Fernet 密钥，对 API Key 等可逆读取的敏感值做静态加密。
历史明文数据仍可读取（decrypt_secret 会原样返回未加密内容），后续保存时自动加密。
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

import backend.config as config

_PREFIX = 'enc:v1:'


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(_PREFIX)


def _fernet():
    digest = hashlib.sha256(
        f'simple-blog-secret-box:{config.SECRET_KEY}'.encode('utf-8')
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value):
    """加密非空密钥；已加密值保持幂等。"""
    if not value:
        return value
    if is_encrypted(value):
        return value
    token = _fernet().encrypt(str(value).encode('utf-8')).decode('ascii')
    return f'{_PREFIX}{token}'


def decrypt_secret(value):
    """解密密钥；未加密的旧数据原样返回，无法解密时返回空字符串。"""
    if not value:
        return value
    if not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX):].encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError):
        return ''


def mask_secret(value):
    """用于界面展示的掩码，绝不返回明文。"""
    plain = decrypt_secret(value)
    if not plain:
        return ''
    if len(plain) <= 4:
        return '****'
    return f'****{plain[-4:]}'
