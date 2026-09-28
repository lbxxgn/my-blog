#!/bin/bash
#
# IP + 自签证书 一键 HTTPS（无需域名 / 无备案问题）
# ============================================================
# 适用：大陆云服务器（阿里云等）用域名会被 ICP 备案拦截，但纯 IP 访问不受影响。
# 本脚本用服务器公网 IP 生成自签 CA + 服务器证书，Nginx 在 443 上以 IP 提供服务。
#
# 用法：
#   sudo ./scripts/setup-https-selfsigned.sh
#   sudo PUBLIC_IP=1.2.3.4   ./scripts/setup-https-selfsigned.sh
#   sudo CERT_DIR=/etc/ssl/my-blog DAYS=3650 ./scripts/setup-https-selfsigned.sh
#   sudo FORCE_CA=1          ./scripts/setup-https-selfsigned.sh   # 强制重新生成 CA
#
# 说明：
#   - CA 和服务器证书在同一次执行内生成，避免 issuer 对不上导致 verify 失败。
#   - 默认复用已存在的 CA（只重签服务器证书），避免每次跑都更换 CA 让所有客户端重装。
#   - 服务器证书有效期默认 397 天（Apple 对 TLS 服务器证书上限 825 天，过长会被 iOS 拒绝）。
#
# 注意：
#   - 客户端首次访问会提示证书不受信任，需在你自己的电脑/手机上信任 ca.crt（脚本会给出文件与步骤）。
#   - 客户端只装 CA（ca.crt/ca.pem），不要装 server.pem（叶子证书不能作为信任根）。
#   - Passkey / WebAuthn 不能用 IP（RP ID 必须是域名），此方案下 Passkey 不可用。
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}$*${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}!${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; }

CERT_DIR="${CERT_DIR:-/etc/ssl/my-blog}"
DAYS="${DAYS:-3650}"                 # CA 有效期
SERVER_DAYS="${SERVER_DAYS:-397}"    # 服务器证书有效期（Apple 对 TLS 服务器证书上限 825 天）
FORCE_CA="${FORCE_CA:-0}"            # 置 1 强制重新生成 CA（会导致所有客户端需重装 CA）

if [ "$(id -u)" -ne 0 ]; then
    fail "需要 root 权限运行：sudo $0"
    exit 1
fi

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
    info "[1/3] 探测公网 IP..."
    if ! PUBLIC_IP="$(detect_ip)"; then
        fail "无法自动探测公网 IP，请用 PUBLIC_IP=你的IP 重跑"
        exit 1
    fi
else
    info "[1/3] 使用指定公网 IP..."
fi
if [[ ! "$PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    fail "PUBLIC_IP 不是合法的 IPv4 地址：$PUBLIC_IP"
    exit 1
fi
ok "公网 IP: $PUBLIC_IP"

info "[2/3] 生成自签 CA 与服务器证书..."
mkdir -p "$CERT_DIR"
chmod 700 "$CERT_DIR"

# openssl 配置：用 [v3_ca] / [v3_server] 显式声明扩展，
# 比 openssl req -x509 -addext 在旧版本（如 1.1.1k FIPS）上更可靠。
cat > "$CERT_DIR/openssl.cnf" <<EOF
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[ dn ]
CN = my-blog Local CA

[ v3_ca ]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash

[ v3_server ]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[ alt_names ]
IP.1 = $PUBLIC_IP
IP.2 = 127.0.0.1
DNS.1 = localhost
EOF

# 1) 本地 CA（客户端只需信任这一个 ca.crt）
#    已存在且未指定 FORCE_CA=1 时复用，避免换 CA 导致所有设备需重装
if [ -f "$CERT_DIR/ca.pem" ] && [ -f "$CERT_DIR/ca.key" ] && [ "${FORCE_CA:-0}" != "1" ]; then
    ok "复用已有 CA：$CERT_DIR/ca.pem（如需更换请 FORCE_CA=1 重跑）"
else
    info "生成新的 CA（有效期 ${DAYS} 天）..."
    openssl genrsa -out "$CERT_DIR/ca.key" 4096 2>/dev/null
    openssl req -x509 -new -key "$CERT_DIR/ca.key" -sha256 -days "$DAYS" \
        -out "$CERT_DIR/ca.pem" -config "$CERT_DIR/openssl.cnf" -extensions v3_ca
fi

# 2) 服务器证书（SAN 含公网 IP 与 localhost；有效期 <= 825 天）
info "签发服务器证书（有效期 ${SERVER_DAYS} 天）..."
openssl genrsa -out "$CERT_DIR/server.key" 2048 2>/dev/null
openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" \
    -subj "/CN=$PUBLIC_IP" -config "$CERT_DIR/openssl.cnf"
openssl x509 -req -in "$CERT_DIR/server.csr" -CA "$CERT_DIR/ca.pem" -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial -out "$CERT_DIR/server.pem" -days "$SERVER_DAYS" -sha256 \
    -extfile "$CERT_DIR/openssl.cnf" -extensions v3_server

# 3) Nginx 用的链（服务器证书 + CA）；另生成 DER 版 ca.crt 便于客户端导入
cat "$CERT_DIR/server.pem" "$CERT_DIR/ca.pem" > "$CERT_DIR/server-fullchain.pem"
openssl x509 -in "$CERT_DIR/ca.pem" -outform der -out "$CERT_DIR/ca.crt"

chmod 600 "$CERT_DIR/ca.key" "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/ca.pem" "$CERT_DIR/server.pem" "$CERT_DIR/server-fullchain.pem" "$CERT_DIR/ca.crt" "$CERT_DIR/openssl.cnf"
rm -f "$CERT_DIR/server.csr" "$CERT_DIR/ca.srl"
ok "证书已生成到 $CERT_DIR"

# 4) 自检：链必须验证通过
if openssl verify -CAfile "$CERT_DIR/ca.pem" "$CERT_DIR/server.pem" >/dev/null 2>&1; then
    ok "证书链验证通过（client 只需信任 $CERT_DIR/ca.crt）"
else
    fail "证书链验证失败！请用 FORCE_CA=1 重新生成，或检查 openssl 版本"
fi
info "CA SHA-256 指纹（客户端核对用）："
openssl x509 -in "$CERT_DIR/ca.pem" -noout -fingerprint -sha256 2>/dev/null | sed 's/^/    /'

info "[3/3] 完成。后续配置："
echo ""
echo -e "${BLUE}--- nginx.conf（443 server 块）---${NC}"
echo "    listen 443 ssl;"
echo "    server_name _;"
echo "    ssl_certificate     $CERT_DIR/server-fullchain.pem;"
echo "    ssl_certificate_key $CERT_DIR/server.key;"
echo ""
echo -e "${BLUE}--- .env ---${NC}"
echo "    FORCE_HTTPS=True"
echo "    # 注意：Passkey 不能用 IP，无需配置 PASSKEY_*"
echo ""
echo -e "${BLUE}--- 访问地址 ---${NC}"
echo "    https://$PUBLIC_IP"
echo ""
echo "修改后执行：nginx -t && systemctl reload nginx"

# firewalld（Alinux/CentOS/RHEL 默认）
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    echo ""
    echo -e "${YELLOW}检测到 firewalld，请确保已放通 443（80 如需跳转也要放通）：${NC}"
    echo "    sudo firewall-cmd --permanent --add-service=https && sudo firewall-cmd --reload"
fi

echo ""
echo -e "${YELLOW}客户端信任（消除浏览器警告，各设备操作一次）：${NC}"
echo "  把文件 $CERT_DIR/ca.crt 下载到你自己的电脑/手机，然后："
echo "  - macOS: 双击导入钥匙串 -> 找到 'my-blog Local CA' -> 设为“始终信任”"
echo "  - iPhone: AirDrop/邮件发送 ca.crt -> 设置-通用-VPN与设备管理 安装 -> 设置-通用-关于本机-证书信任设置 打开完全信任"
echo "            （更推荐）用 scripts/make-apple-cert-profile.sh 生成 .mobileconfig，Safari 打开即可安装"
echo "  - Windows: 双击 ca.crt -> 安装到“受信任的根证书颁发机构”"
echo "  - Android: 设置-安全-加密与凭据-安装证书-CA 证书，选 ca.crt"
