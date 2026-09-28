"""
AI Base URL 安全校验

用户可在后台填写自定义 OpenAI 兼容服务的 Base URL，或测试请求中携带
任意 URL。若不做校验，攻击者可借此让服务器向内网/云元数据地址发起请求
（SSRF）。这里统一校验 scheme、主机名与解析后的 IP。

默认禁止私网/回环/链路本地/保留地址；如需接入自建内网模型服务，可设置
环境变量 AI_ALLOW_PRIVATE_BASE_URLS=true 放开私网与回环（链路本地与云元
数据地址始终禁止）。
"""

import ipaddress
import os
import socket
from urllib.parse import urlsplit


class UnsafeBaseUrlError(ValueError):
    """Base URL 不安全（SSRF 防护命中）"""


def _allow_private():
    return os.environ.get('AI_ALLOW_PRIVATE_BASE_URLS', '').lower() in ('true', '1', 'yes')


def _is_blocked_ip(ip, allow_private):
    # 链路本地（含云元数据 169.254.169.254）与未指定地址始终禁止
    if ip.is_link_local or ip.is_unspecified:
        return True
    if allow_private:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_reserved
        or ip.is_multicast
    )


def validate_ai_base_url(base_url, allow_private=None):
    """校验 Base URL；不安全时抛出 UnsafeBaseUrlError，合法则原样返回。"""
    if not base_url:
        return base_url

    if allow_private is None:
        allow_private = _allow_private()

    parts = urlsplit(str(base_url).strip())
    if parts.scheme not in ('http', 'https'):
        raise UnsafeBaseUrlError('Base URL 必须使用 http 或 https')
    if not parts.hostname:
        raise UnsafeBaseUrlError('Base URL 缺少主机名')

    host = parts.hostname

    # 字面量 IP
    try:
        ip = ipaddress.ip_address(host)
        if _is_blocked_ip(ip, allow_private):
            raise UnsafeBaseUrlError('Base URL 指向内网/保留地址，已拒绝')
        return base_url
    except ValueError:
        pass

    # 域名：解析后逐个校验，防止 DNS 指向内网
    try:
        infos = socket.getaddrinfo(
            host,
            parts.port or (443 if parts.scheme == 'https' else 80),
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        raise UnsafeBaseUrlError(f'无法解析 Base URL 主机名: {host}') from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _is_blocked_ip(ip, allow_private):
            raise UnsafeBaseUrlError('Base URL 解析到内网/保留地址，已拒绝')

    return base_url
