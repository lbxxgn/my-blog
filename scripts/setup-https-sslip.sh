#!/bin/bash
#
# 无域名 HTTPS 一键配置：sslip.io + Let's Encrypt
# ============================================================
# 用「你的公网IP.sslip.io」作为主机名申请免费的 Let's Encrypt 证书。
# sslip.io 会把 *.<ip>.sslip.io 自动解析到该 IP，因此无需购买域名、无需备案。
#
# 用法：
#   sudo ./scripts/setup-https-sslip.sh
#   sudo PUBLIC_IP=1.2.3.4   ./scripts/setup-https-sslip.sh
#   sudo EMAIL=me@example.com ./scripts/setup-https-sslip.sh
#   sudo STAGING=1           ./scripts/setup-https-sslip.sh   # 先用测试环境验证
#
# 前置条件：
#   1) 80 端口已对外放通（阿里云安全组入方向 + 系统防火墙）
#   2) nginx 已按 nginx.conf.example 配置，并在 80 端口包含：
#        location /.well-known/acme-challenge/ { root /var/www/letsencrypt; }
#
# 完成后把提示的 server_name / 证书路径填进 nginx，并 reload。
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}$*${NC}"; }
ok()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()  { echo -e "  ${YELLOW}!${NC} $*"; }
fail()  { echo -e "  ${RED}✗${NC} $*"; }

# webroot 可通过环境变量覆盖；Alinux/CentOS 若 SELinux 折腾，可用
#   sudo WEBROOT=/usr/share/nginx/html ./scripts/setup-https-sslip.sh
WEBROOT="${WEBROOT:-/var/www/letsencrypt}"
EMAIL="${EMAIL:-}"
STAGING="${STAGING:-}"

if [ "$(id -u)" -ne 0 ]; then
    fail "需要 root 权限运行：sudo $0"
    exit 1
fi

# ---------------------------------------------------------------
# 1. 探测公网 IPv4
# ---------------------------------------------------------------
detect_ip() {
    local url ip
    for url in "https://api.ipify.org" "https://ifconfig.me/ip" "https://ipinfo.io/ip"; do
        ip="$(curl -4 -fsS --max-time 5 "$url" 2>/dev/null || true)"
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "$ip"
            return 0
        fi
    done
    return 1
}

PUBLIC_IP="${PUBLIC_IP:-}"
if [ -z "$PUBLIC_IP" ]; then
    info "[1/5] 探测公网 IP..."
    if ! PUBLIC_IP="$(detect_ip)"; then
        fail "无法自动探测公网 IP，请用 PUBLIC_IP=你的IP 重跑"
        exit 1
    fi
else
    info "[1/5] 使用指定公网 IP..."
fi

if [[ ! "$PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    fail "PUBLIC_IP 不是合法的 IPv4 地址：$PUBLIC_IP"
    exit 1
fi
ok "公网 IP: $PUBLIC_IP"

# 主机名（横线形式，certbot 更稳妥；点形式同样可用）
SSLIP_HOST="${PUBLIC_IP//./-}.sslip.io"
ok "使用主机名: $SSLIP_HOST"

# ---------------------------------------------------------------
# 2. 安装 certbot
# ---------------------------------------------------------------
info "[2/5] 检查 certbot..."
if command -v certbot >/dev/null 2>&1; then
    ok "certbot 已安装"
else
    warn "未安装 certbot，尝试通过包管理器安装..."
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y && apt-get install -y certbot
    elif command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1; then
        # RHEL/CentOS/Alibaba Cloud Linux 系：base 源可能没有 certbot，需要 EPEL
        PKG="$(command -v dnf || command -v yum)"
        if ! $PKG install -y certbot; then
            warn "base 源未提供 certbot，尝试安装 EPEL 后重试..."
            if ! rpm -q epel-release >/dev/null 2>&1; then
                $PKG install -y epel-release \
                    || $PKG install -y "https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm" \
                    || true
            fi
            if ! $PKG install -y certbot; then
                fail "certbot 安装失败，请参考 https://certbot.eff.org 手动安装后重跑"
                exit 1
            fi
        fi
    else
        fail "未知的包管理器，请手动安装 certbot 后重跑"
        exit 1
    fi
    ok "certbot 安装完成"
fi

# ---------------------------------------------------------------
# 3. 准备 webroot
# ---------------------------------------------------------------
info "[3/5] 准备 ACME 校验目录..."
mkdir -p "$WEBROOT"
ok "已就绪: $WEBROOT"

# SELinux（Alibaba Cloud Linux / CentOS / RHEL 默认开启）：让 nginx 能读取校验文件。
# 用 semanage 写持久规则，保证 certbot 之后新建的挑战文件也带正确上下文。
if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce 2>/dev/null || echo Disabled)" != "Disabled" ]; then
    if ! command -v semanage >/dev/null 2>&1; then
        if command -v dnf >/dev/null 2>&1; then
            dnf install -y policycoreutils-python-utils >/dev/null 2>&1 || true
        elif command -v yum >/dev/null 2>&1; then
            yum install -y policycoreutils-python-utils >/dev/null 2>&1 || true
        fi
    fi
    if command -v semanage >/dev/null 2>&1; then
        semanage fcontext -a -t httpd_sys_content_t "$WEBROOT(/.*)?" 2>/dev/null \
            || semanage fcontext -m -t httpd_sys_content_t "$WEBROOT(/.*)?" 2>/dev/null \
            || true
        restorecon -R "$WEBROOT" >/dev/null 2>&1 || true
        ok "已设置 SELinux 上下文 httpd_sys_content_t（$WEBROOT）"
    else
        chcon -R -t httpd_sys_content_t "$WEBROOT" 2>/dev/null \
            && ok "已设置 SELinux 上下文（临时，重启 relabel 后可能失效）" \
            || warn "SELinux 上下文设置失败；若校验返回 403，请手动执行：semanage fcontext -a -t httpd_sys_content_t \"$WEBROOT(/.*)?\" && restorecon -Rv $WEBROOT"
    fi
fi

# ---------------------------------------------------------------
# 4. 申请证书
# ---------------------------------------------------------------
info "[4/5] 申请证书（HTTP-01 校验，需要 80 端口公网可达）..."
certbot_args=(
    certonly --webroot -w "$WEBROOT"
    -d "$SSLIP_HOST"
    --agree-tos --non-interactive
    --deploy-hook "systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null || true"
)
if [ -n "$EMAIL" ]; then
    certbot_args+=(-m "$EMAIL")
else
    certbot_args+=(--register-unsafely-without-email)
fi
if [ -n "$STAGING" ]; then
    certbot_args+=(--staging)
    warn "使用 Let's Encrypt 测试环境（证书不被浏览器信任，仅用于验证流程）"
fi

if ! certbot "${certbot_args[@]}"; then
    echo ""
    fail "证书申请失败，常见原因："
    echo "    - 安全组/防火墙未放通 80 端口"
    echo "    - nginx 未运行，或 80 端口未包含 ACME 校验 location（root 必须是 $WEBROOT）"
    echo "    - server_name 与本次主机名不一致（横线/点形式不同），请求落到默认 server："
    echo "      确认 sudo nginx -T | grep server_name 里包含 $SSLIP_HOST"
    echo "    - SELinux 返回 403（Alinux/CentOS 默认 Enforcing）：先看 sudo getenforce，"
    echo "      再执行 sudo semanage fcontext -a -t httpd_sys_content_t \"$WEBROOT(/.*)?\" && sudo restorecon -Rv $WEBROOT"
    echo "    - 域名解析异常：试运行 nslookup $SSLIP_HOST"
    echo "    - 本地自测：mkdir -p $WEBROOT/.well-known/acme-challenge && echo ok > $WEBROOT/.well-known/acme-challenge/test"
    echo "      curl -i http://127.0.0.1/.well-known/acme-challenge/test   # 期望 200"
    exit 1
fi
ok "证书申请成功"

# ---------------------------------------------------------------
# 5. 输出后续配置
# ---------------------------------------------------------------
CERT_DIR="/etc/letsencrypt/live/$SSLIP_HOST"
info "[5/5] 完成。请将以下内容填入配置："

echo ""
echo -e "${BLUE}--- nginx.conf（443 server 块）---${NC}"
echo "    server_name $SSLIP_HOST;"
echo "    ssl_certificate     $CERT_DIR/fullchain.pem;"
echo "    ssl_certificate_key $CERT_DIR/privkey.pem;"
echo ""
echo -e "${BLUE}--- nginx.conf（80 块 ACME 段，root 必须与本次 webroot 一致）---${NC}"
echo "    location /.well-known/acme-challenge/ { root $WEBROOT; }"
echo ""
echo -e "${BLUE}--- .env ---${NC}"
echo "    FORCE_HTTPS=True"
echo "    PASSKEY_RP_NAME=我的博客"
echo "    PASSKEY_RP_ID=$SSLIP_HOST"
echo "    PASSKEY_ALLOWED_ORIGINS=https://$SSLIP_HOST"
echo ""
echo -e "${BLUE}--- 访问地址 ---${NC}"
echo "    https://$SSLIP_HOST"
echo ""
echo "修改后执行：nginx -t && systemctl reload nginx"
echo "证书会自动续期（certbot 定时任务），无需手动维护。"

# firewalld（Alibaba Cloud Linux / CentOS / RHEL 默认使用）
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    echo ""
    echo -e "${YELLOW}检测到 firewalld，请确保已放通 80/443：${NC}"
    echo "    sudo firewall-cmd --permanent --add-service=http --add-service=https && sudo firewall-cmd --reload"
fi

# SELinux 代理放行提示（Alibaba Cloud Linux 默认 enforcing）
if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce 2>/dev/null || echo Disabled)" = "Enforcing" ]; then
    echo ""
    echo -e "${YELLOW}SELinux 处于 Enforcing：若 nginx 反向代理报 502/权限错误，执行${NC}"
    echo "    sudo setsebool -P httpd_can_network_connect 1"
    echo "  若静态文件 403，执行："
    echo "    sudo chcon -R -t httpd_sys_content_t /path/to/my-blog/static"
fi
