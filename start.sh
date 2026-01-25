#!/bin/bash
#
# Simple Blog 启动脚本
# 版本: 2.0
# 更新日期: 2026-01-25
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 加载 .env 文件（如果存在）
if [ -f .env ]; then
    echo -e "${BLUE}加载环境变量配置...${NC}"
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    echo -e "  ${GREEN}✓${NC} 已加载 .env 文件"
fi

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Simple Blog 启动脚本${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检查Python版本
echo -e "${YELLOW}[1/6] 检查Python版本...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "  当前版本: ${GREEN}Python $PYTHON_VERSION${NC}"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo -e "  ${RED}错误: 需要Python 3.8或更高版本${NC}"
    exit 1
fi

# 检查依赖
echo -e "${YELLOW}[2/6] 检查依赖...${NC}"
MISSING_DEPS=0

check_dep() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $1"
    else
        echo -e "  ${RED}✗${NC} $1 (未安装)"
        MISSING_DEPS=1
    fi
}

check_dep "flask"
check_dep "flask_wtf"
check_dep "flask_limiter"
check_dep "bleach"
check_dep "markdown2"
check_dep "PIL"  # Pillow
check_dep "pytz"

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo -e "${RED}错误: 缺少依赖，请运行: pip3 install -r requirements.txt${NC}"
    exit 1
fi

# 检查环境变量
echo -e "${YELLOW}[3/6] 检查环境变量...${NC}"

if [ -z "$ADMIN_USERNAME" ]; then
    echo -e "  ${YELLOW}未设置 ADMIN_USERNAME，使用默认值: admin${NC}"
    export ADMIN_USERNAME="admin"
else
    echo -e "  ${GREEN}✓${NC} ADMIN_USERNAME=$ADMIN_USERNAME"
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "  ${RED}错误: 必须设置 ADMIN_PASSWORD 环境变量${NC}"
    echo ""
    echo "示例用法:"
    echo "  export ADMIN_PASSWORD=\"YourSecurePassword123!\""
    echo "  ./start.sh"
    echo ""
    exit 1
else
    echo -e "  ${GREEN}✓${NC} ADMIN_PASSWORD=********"
fi

# 设置默认值
export DEBUG="${DEBUG:-False}"
export PORT="${PORT:-5001}"
echo -e "  DEBUG=$DEBUG"
echo -e "  PORT=$PORT"

# 检查数据库
echo -e "${YELLOW}[4/6] 检查数据库...${NC}"

if [ ! -f "db/posts.db" ]; then
    echo -e "  ${YELLOW}数据库不存在，首次启动将自动创建${NC}"
else
    DB_SIZE=$(du -h "db/posts.db" | cut -f1)
    echo -e "  ${GREEN}✓${NC} 数据库存在 (大小: $DB_SIZE)"
fi

# 创建必要的目录
echo -e "${YELLOW}[5/6] 创建必要目录...${NC}"

mkdir -p logs
mkdir -p static/uploads
mkdir -p db
mkdir -p backups

echo -e "  ${GREEN}✓${NC} logs/"
echo -e "  ${GREEN}✓${NC} static/uploads/"
echo -e "  ${GREEN}✓${NC} db/"
echo -e "  ${GREEN}✓${NC} backups/"

# 停止已存在的进程
echo -e "${YELLOW}[6/6] 启动应用...${NC}"

EXISTING_PID=$(ps aux | grep -v grep | grep "python.*backend/app.py" | awk '{print $2}' | head -1)
if [ -n "$EXISTING_PID" ]; then
    echo -e "  ${YELLOW}发现已运行的进程 (PID: $EXISTING_PID)，正在停止...${NC}"
    kill $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

# 启动应用
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  启动中...${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "访问地址:"
echo -e "  ${BLUE}主页${NC}:      http://localhost:$PORT/"
echo -e "  ${BLUE}登录${NC}:      http://localhost:$PORT/login"
echo -e "  ${BLUE}管理后台${NC}:  http://localhost:$PORT/admin"
echo ""
echo -e "按 Ctrl+C 停止应用"
echo ""

# 启动应用（前台运行）
python3 backend/app.py
