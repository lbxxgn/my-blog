"""密码强度校验。

用户自助改密、管理员重置密码、后台建用户共用同一套规则，避免三处实现漂移。
"""

import re

__all__ = ['MIN_PASSWORD_LENGTH', 'validate_password_strength']

MIN_PASSWORD_LENGTH = 10


def validate_password_strength(password):
    """校验密码强度。

    要求：至少 ``MIN_PASSWORD_LENGTH`` 位、包含大写字母、小写字母与数字。

    Args:
        password (str): 待验证的密码

    Returns:
        tuple: (is_valid, error_message)；通过时 error_message 为 None
    """
    password = password or ''

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f'密码长度至少为{MIN_PASSWORD_LENGTH}位'

    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'

    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'

    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'

    return True, None
