#!/bin/bash
# 同步浏览器扩展共享代码
#
# browser-extension/ 是共享代码的权威来源（popup/content/background 全部 JS/CSS/HTML），
# safari-extension/ 仅保留自己的 manifest.json、icons 与 README。
# 修改共享文件后运行本脚本，避免两处拷贝漂移：
#
#   ./scripts/sync-extensions.sh
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$PROJECT_ROOT/browser-extension"
DST="$PROJECT_ROOT/safari-extension"

SHARED_FILES=(
    background/api-client.js
    background/auth-manager.js
    background/service-worker.js
    content/content-bundle.js
    content/content.css
    content/content.js
    content/selector.js
    content/toolbar.js
    popup/popup.css
    popup/popup.html
    popup/popup.js
)

for f in "${SHARED_FILES[@]}"; do
    if [ ! -f "$SRC/$f" ]; then
        echo "❌ 源文件不存在: $SRC/$f"
        exit 1
    fi
    cp "$SRC/$f" "$DST/$f"
    echo "✓ $f"
done

echo ""
echo "✅ 已同步 ${#SHARED_FILES[@]} 个共享文件到 safari-extension/"
