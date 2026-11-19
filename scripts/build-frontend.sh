#!/bin/bash
# 构建知识库编辑器前端（构建产物 static/frontend/ 不入库）
#
# 用法:
#   ./scripts/build-frontend.sh
#
# 依赖变化（package-lock.json 比 node_modules 新）时才执行 npm ci，其余情况只 build。
# 可在 systemd 的 ExecStartPre 中调用，让 restart 前自动重建前端。

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "frontend/ 不存在，跳过前端构建" >&2
    exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "错误: npm 未安装或不在 PATH 中（需要 Node.js 22+）" >&2
    exit 1
fi

cd "$FRONTEND_DIR"

# npm 缓存放到项目内，避免服务用户没有 HOME 或缓存目录不可写
export npm_config_cache="$FRONTEND_DIR/.npm-cache"

if [ ! -d node_modules ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
    echo "安装前端依赖..."
    npm ci --silent
fi

echo "构建前端..."
npm run build

if [ ! -f "$PROJECT_DIR/static/frontend/.vite/manifest.json" ]; then
    echo "错误: 构建完成但未找到 static/frontend/.vite/manifest.json" >&2
    exit 1
fi

echo "前端构建完成: static/frontend/"
