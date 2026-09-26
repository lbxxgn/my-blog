#!/bin/bash
#
# 清理 sslip.io + Let's Encrypt 方案残留
# ============================================================
# 适用：已改用「IP + 自签证书」或其它方案，想移除 certbot 相关文件/服务。
#
# 默认只清理文件与定时器（安全、可逆性高）；卸载软件包需显式开关：
#   sudo ./scripts/cleanup-https-sslip.sh
#   sudo REMOVE_CERTBOT=1 ./scripts/cleanup-https-sslip.sh   # 顺带卸载 certbot
#   sudo REMOVE_EPEL=1    ./scripts/cleanup-https-sslip.sh   # 顺带移除 EPEL 源（谨慎）
#   sudo DRY_RUN=1        ./scripts/cleanup-https-sslip.sh   # 只打印要做什么
#
# 不会动的东西：Nginx 配置（请自行替换/回退）、应用数据、你已有的其它 EPEL 软件。
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
run()  {
    if [ "${DRY_RUN:-}" = "1" ]; then
        echo "    [dry-run] $*"
    else
        eval "$@"
    fi
}

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}需要 root 权限运行：sudo $0${NC}"
    exit 1
fi

WEBROOT="${WEBROOT:-/var/www/letsencrypt}"

info "[1/4] 停止并禁用 certbot 定时器/服务..."
run "systemctl disable --now certbot-renew.timer 2>/dev/null || true"
run "systemctl disable --now certbot-renew.service 2>/dev/null || true"
run "systemctl reset-failed certbot-renew.timer certbot-renew.service 2>/dev/null || true"
ok "已处理 certbot 定时器"

info "[2/4] 删除 ACME 校验目录与 certbot 数据..."
for p in "$WEBROOT" /etc/letsencrypt /var/log/letsencrypt /var/lib/letsencrypt; do
    if [ -e "$p" ]; then
        run "rm -rf '$p'"
        ok "已删除 $p"
    fi
done

info "[3/4] 清理 Nginx 中残留的 ACME 段（提示）..."
if [ -d /etc/nginx ]; then
    if grep -Rqs "acme-challenge\|letsencrypt" /etc/nginx 2>/dev/null; then
        warn "检测到 /etc/nginx 下仍有 acme-challenge / letsencrypt 引用："
        grep -Rns "acme-challenge\|letsencrypt" /etc/nginx 2>/dev/null | sed 's/^/    /'
        warn "如已改用自签配置请手动删除这些 location；改完执行 nginx -t && systemctl reload nginx"
    else
        ok "未发现 Nginx 中的相关残留"
    fi
fi

info "[4/4] 可选：卸载软件包..."
if [ "${REMOVE_CERTBOT:-0}" = "1" ]; then
    if command -v dnf >/dev/null 2>&1; then
        run "dnf remove -y certbot python3-certbot python3-certbot-nginx 2>/dev/null || dnf remove -y certbot || true"
        run "dnf autoremove -y 2>/dev/null || true"
    elif command -v yum >/dev/null 2>&1; then
        run "yum remove -y certbot 2>/dev/null || true"
        run "yum autoremove -y 2>/dev/null || true"
    elif command -v apt-get >/dev/null 2>&1; then
        run "apt-get remove -y certbot 2>/dev/null || true"
        run "apt-get autoremove -y 2>/dev/null || true"
    fi
    ok "已卸载 certbot"
else
    warn "未卸载 certbot（如需：sudo REMOVE_CERTBOT=1 $0）"
fi

if [ "${REMOVE_EPEL:-0}" = "1" ]; then
    if rpm -q epel-release >/dev/null 2>&1; then
        warn "移除 EPEL 源（若你其它软件依赖 EPEL，请勿执行）"
        run "rm -f /etc/yum.repos.d/epel*.repo"
        run "dnf clean all 2>/dev/null || yum clean all 2>/dev/null || true"
        ok "已移除 EPEL 源配置"
    fi
else
    warn "保留 EPEL（如确认无用：sudo REMOVE_EPEL=1 $0）"
fi

echo ""
if [ "${DRY_RUN:-}" = "1" ]; then
    echo -e "${YELLOW}以上为 dry-run 预览，未实际执行。去掉 DRY_RUN=1 重跑。${NC}"
else
    echo -e "${GREEN}清理完成。${NC}"
fi
