#!/bin/bash
#
# 生成 iPhone 用的 .mobileconfig 配置描述文件（内嵌自签 CA）
# ============================================================
# 用法：
#   sudo ./scripts/make-apple-cert-profile.sh
#   sudo CERT_DIR=/etc/ssl/my-blog OUT=/tmp/my-blog-ca.mobileconfig ./scripts/make-apple-cert-profile.sh
#
# 生成后：把 <OUT> 放进站点可访问目录，用 iPhone Safari 打开安装，再到
#   「设置 → 通用 → 关于本机 → 证书信任设置」里打开完全信任。
# ============================================================

set -euo pipefail

CERT_DIR="${CERT_DIR:-/etc/ssl/my-blog}"
OUT="${OUT:-$CERT_DIR/my-blog-ca.mobileconfig}"
CA_PEM="$CERT_DIR/ca.pem"

if [ ! -f "$CA_PEM" ]; then
    echo "找不到 CA：$CA_PEM（先运行 scripts/setup-https-selfsigned.sh，或用 CERT_DIR= 指定）" >&2
    exit 1
fi

# 生成 UUID（兼容无 uuidgen 的系统）
gen_uuid() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr 'A-Z' 'a-z'
    else
        cat /proc/sys/kernel/random/uuid
    fi
}
UUID_CERT="$(gen_uuid)"
UUID_PROFILE="$(gen_uuid)"

# 内嵌 DER 格式证书的 base64（plist <data> 接受换行）
CA_B64="$(openssl x509 -in "$CA_PEM" -outform der | base64)"

cat > "$OUT" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>PayloadCertificateFileName</key>
            <string>ca.pem</string>
            <key>PayloadContent</key>
            <data>
$CA_B64
            </data>
            <key>PayloadDescription</key>
            <string>安装 my-blog 本地 CA 证书</string>
            <key>PayloadDisplayName</key>
            <string>my-blog Local CA</string>
            <key>PayloadIdentifier</key>
            <string>com.myblog.ca.$UUID_CERT</string>
            <key>PayloadType</key>
            <string>com.apple.security.root</string>
            <key>PayloadUUID</key>
            <string>$UUID_CERT</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>my-blog CA</string>
    <key>PayloadIdentifier</key>
    <string>com.myblog.profile.$UUID_PROFILE</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>$UUID_PROFILE</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>
EOF

chmod 644 "$OUT"
echo "已生成: $OUT"
echo
echo "下一步（在服务器上）："
echo "  cp $OUT /path/to/my-blog/static/my-blog-ca.mobileconfig"
echo "然后用 iPhone 的 Safari 打开："
echo "  https://你的服务器IP/static/my-blog-ca.mobileconfig"
echo "（证书尚未信任时 Safari 会先警告，点“继续访问”即可）"
echo
echo "安装后务必再到：设置 → 通用 → 关于本机 → 证书信任设置，打开“完全信任”。"
