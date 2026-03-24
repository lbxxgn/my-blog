"""
认证相关路由

包括登录、登出、修改密码等认证功能。
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from urllib.parse import urlparse, urljoin
import ipaddress
import re
import base64
import json

from models import (
    get_user_by_username, get_user_by_id, get_user_passkeys,
    get_passkey_by_credential_id, create_user_passkey,
    update_user_passkey_usage, delete_user_passkey, update_user_password
)
from auth_decorators import login_required
from logger import log_login
from backend.config import PASSKEY_RP_NAME, PASSKEY_RP_ID, PASSKEY_ALLOWED_ORIGINS
from webauthn import (
    generate_registration_options,
    generate_authentication_options,
    options_to_json,
    verify_registration_response,
    verify_authentication_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)


def is_safe_url(target):
    """验证URL是否安全，防止开放式重定向攻击"""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
        test_url.scheme in ('http', 'https') and
        ref_url.netloc == test_url.netloc
    )


def validate_password_strength(password):
    """
    验证密码强度

    要求:
        - 至少10位长度
        - 包含至少一个大写字母
        - 包含至少一个小写字母
        - 包含至少一个数字

    Args:
        password (str): 待验证的密码

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 10:
        return False, '密码长度至少为10位'

    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'

    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'

    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'

    return True, None


def _b64url_encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def _b64url_decode(value):
    padding = '=' * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _get_rp_id():
    if PASSKEY_RP_ID:
        return PASSKEY_RP_ID
    host = request.host.split(':', 1)[0]
    if host in ('127.0.0.1', '::1'):
        return 'localhost'
    return host


def _get_allowed_origins():
    if PASSKEY_ALLOWED_ORIGINS:
        return PASSKEY_ALLOWED_ORIGINS
    host = request.host.split(':', 1)[0]
    port = request.host.split(':', 1)[1] if ':' in request.host else ''
    origins = {request.host_url.rstrip('/')}

    if host in ('localhost', '127.0.0.1', '::1'):
        suffix = f':{port}' if port else ''
        origins.add(f'http://localhost{suffix}')
        origins.add(f'http://127.0.0.1{suffix}')

    return sorted(origins)


def _passkey_hostname_is_valid():
    host = request.host.split(':', 1)[0]
    if host in ('localhost',):
        return True

    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return '.' in host


def _passkey_context():
    host = request.host.split(':', 1)[0]
    port = request.host.split(':', 1)[1] if ':' in request.host else ''
    recommended_url = ''

    if host in ('127.0.0.1', '::1'):
        suffix = f':{port}' if port else ''
        recommended_url = f'http://localhost{suffix}{request.path}'

    return {
        'supported_host': _passkey_hostname_is_valid(),
        'host': host,
        'rp_id': _get_rp_id(),
        'allowed_origins': _get_allowed_origins(),
        'recommended_url': recommended_url,
        'reason': 'Passkey 在本地开发时建议使用 localhost，不建议直接用 IP 地址访问。' if not _passkey_hostname_is_valid() else '',
    }


def _serialize_passkey(passkey):
    transports = passkey.get('transports') or []
    transport_labels = {
        'internal': '本机设备',
        'hybrid': '跨设备',
        'usb': 'USB',
        'nfc': 'NFC',
        'ble': '蓝牙',
    }
    device_type = passkey.get('credential_device_type') or 'single_device'
    device_type_label = '可同步设备' if device_type == 'multi_device' else '单设备'
    return {
        'id': passkey['id'],
        'device_name': passkey.get('device_name') or '未命名设备',
        'credential_device_type': device_type,
        'credential_device_type_label': device_type_label,
        'backup_state': bool(passkey.get('backup_state')),
        'backup_eligible': bool(passkey.get('backup_eligible')),
        'created_at': passkey.get('created_at'),
        'last_used_at': passkey.get('last_used_at'),
        'transports': transports,
        'transport_labels': [transport_labels.get(item, item) for item in transports],
    }


def _parse_remember_device(value):
    return str(value).lower() in ('1', 'true', 'on', 'yes')


def _complete_login(user, remember_device=False):
    try:
        session.regenerate()
    except AttributeError:
        session.clear()

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user.get('role', 'author')
    session['remember_device'] = bool(remember_device)
    session.permanent = bool(remember_device)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    # Note: limiter will be applied from the main app
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_device = _parse_remember_device(request.form.get('remember_device'))

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            log_login(username or 'Unknown', success=False, error_msg='字段为空')
            return render_template('login.html', passkey_context=_passkey_context())

        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            _complete_login(user, remember_device=remember_device)
            flash(f'欢迎回来，{user["username"]}！', 'success')

            # 记录成功登录
            log_login(username, success=True)

            # 安全地处理重定向
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('用户名或密码错误', 'error')
            # 记录失败登录
            log_login(username, success=False, error_msg='密码错误或用户不存在')

    return render_template('login.html', passkey_context=_passkey_context())


@auth_bp.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('blog.index'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            flash('请填写所有字段', 'error')
            return render_template('change_password.html', passkeys=[_serialize_passkey(item) for item in get_user_passkeys(session['user_id'])], passkey_context=_passkey_context())

        if new_password != confirm_password:
            flash('新密码和确认密码不匹配', 'error')
            return render_template('change_password.html', passkeys=[_serialize_passkey(item) for item in get_user_passkeys(session['user_id'])], passkey_context=_passkey_context())

        # 验证密码强度
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('change_password.html', passkeys=[_serialize_passkey(item) for item in get_user_passkeys(session['user_id'])], passkey_context=_passkey_context())

        # 验证当前密码
        user = get_user_by_username(session['username'])
        if not check_password_hash(user['password_hash'], current_password):
            flash('当前密码错误', 'error')
            return render_template('change_password.html')

        # 更新密码
        new_password_hash = generate_password_hash(new_password)
        update_user_password(user['id'], new_password_hash)
        flash('密码修改成功', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    passkeys = [_serialize_passkey(item) for item in get_user_passkeys(session['user_id'])]
    return render_template('change_password.html', passkeys=passkeys, passkey_context=_passkey_context())


@auth_bp.route('/passkeys/register/begin', methods=['POST'])
@login_required
def passkey_register_begin():
    """开始绑定 Passkey"""
    if not _passkey_hostname_is_valid():
        context = _passkey_context()
        return jsonify({
            'success': False,
            'error': context['reason'],
            'recommended_url': context['recommended_url'],
        }), 400

    user = get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    existing_passkeys = get_user_passkeys(user['id'])
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=item['credential_id'])
        for item in existing_passkeys
    ]

    options = generate_registration_options(
        rp_id=_get_rp_id(),
        rp_name=PASSKEY_RP_NAME,
        user_name=user['username'],
        user_id=str(user['id']).encode('utf-8'),
        user_display_name=user.get('display_name') or user['username'],
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    session['passkey_registration_challenge'] = _b64url_encode(options.challenge)
    return jsonify({'success': True, 'options': json.loads(options_to_json(options))})


@auth_bp.route('/passkeys/register/finish', methods=['POST'])
@login_required
def passkey_register_finish():
    """完成 Passkey 绑定"""
    payload = request.get_json() or {}
    credential = payload.get('credential')
    challenge = session.get('passkey_registration_challenge')

    if not credential or not challenge:
        return jsonify({'success': False, 'error': '缺少注册上下文，请重试'}), 400

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=_b64url_decode(challenge),
            expected_rp_id=_get_rp_id(),
            expected_origin=_get_allowed_origins(),
            require_user_verification=True,
        )
    except Exception as exc:
        return jsonify({'success': False, 'error': f'Passkey 验证失败：{exc}'}), 400
    finally:
        session.pop('passkey_registration_challenge', None)

    passkey_id = create_user_passkey(
        user_id=session['user_id'],
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        device_name=(payload.get('device_name') or '').strip() or '当前设备',
        transports=credential.get('transports') or [],
        credential_device_type=verification.credential_device_type.value,
        backup_eligible=verification.credential_backed_up,
        backup_state=verification.credential_backed_up,
    )

    if not passkey_id:
        return jsonify({'success': False, 'error': '这把 Passkey 已经绑定过了'}), 409

    return jsonify({'success': True, 'message': '快捷登录已启用'})


@auth_bp.route('/passkeys/authenticate/begin', methods=['POST'])
def passkey_authenticate_begin():
    """开始 Passkey 登录"""
    if not _passkey_hostname_is_valid():
        context = _passkey_context()
        return jsonify({
            'success': False,
            'error': context['reason'],
            'recommended_url': context['recommended_url'],
        }), 400

    options = generate_authentication_options(
        rp_id=_get_rp_id(),
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    session['passkey_authentication_challenge'] = _b64url_encode(options.challenge)
    return jsonify({'success': True, 'options': json.loads(options_to_json(options))})


@auth_bp.route('/passkeys/authenticate/finish', methods=['POST'])
def passkey_authenticate_finish():
    """完成 Passkey 登录"""
    payload = request.get_json() or {}
    credential = payload.get('credential')
    challenge = session.get('passkey_authentication_challenge')
    remember_device = _parse_remember_device(payload.get('remember_device'))

    if not credential or not challenge:
        return jsonify({'success': False, 'error': '缺少登录上下文，请重试'}), 400

    credential_id = credential.get('id')
    if not credential_id:
        return jsonify({'success': False, 'error': '缺少 credential id'}), 400

    passkey = get_passkey_by_credential_id(_b64url_decode(credential_id))
    if not passkey:
        return jsonify({'success': False, 'error': '未找到匹配的 Passkey'}), 404

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=_b64url_decode(challenge),
            expected_rp_id=_get_rp_id(),
            expected_origin=_get_allowed_origins(),
            credential_public_key=passkey['public_key'],
            credential_current_sign_count=passkey['sign_count'],
            require_user_verification=True,
        )
    except Exception as exc:
        return jsonify({'success': False, 'error': f'Passkey 验证失败：{exc}'}), 400
    finally:
        session.pop('passkey_authentication_challenge', None)

    user = get_user_by_id(passkey['user_id'])
    if not user or not user.get('is_active', 1):
        return jsonify({'success': False, 'error': '用户不可用'}), 403

    _complete_login(user, remember_device=remember_device)
    update_user_passkey_usage(
        passkey['id'],
        verification.new_sign_count,
        credential_device_type=verification.credential_device_type.value,
        backup_state=verification.credential_backed_up,
    )
    log_login(user['username'], success=True)

    next_page = payload.get('next')
    redirect_to = next_page if next_page and is_safe_url(next_page) else url_for('admin.admin_dashboard')
    return jsonify({'success': True, 'redirect': redirect_to})


@auth_bp.route('/passkeys', methods=['GET'])
@login_required
def passkey_list():
    """获取当前用户的 Passkey 列表"""
    passkeys = [_serialize_passkey(item) for item in get_user_passkeys(session['user_id'])]
    return jsonify({'success': True, 'passkeys': passkeys})


@auth_bp.route('/passkeys/<int:passkey_id>', methods=['DELETE'])
@login_required
def passkey_delete(passkey_id):
    """删除当前用户的一把 Passkey"""
    deleted = delete_user_passkey(passkey_id, session['user_id'])
    if not deleted:
        return jsonify({'success': False, 'error': 'Passkey 不存在'}), 404
    return jsonify({'success': True, 'message': '快捷登录设备已移除'})
