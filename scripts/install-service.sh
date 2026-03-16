#!/bin/bash
#
# Simple Blog systemd 服务安装脚本
# 用途：自动配置和安装 systemd 服务
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Simple Blog 服务安装脚本${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 获取项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${GREEN}项目目录: ${PROJECT_DIR}${NC}"

# 检测 Python 路径
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo -e "${RED}错误: 未找到 python3${NC}"
    exit 1
fi
echo -e "${GREEN}Python 路径: ${PYTHON_PATH}${NC}"

# 读取配置
echo ""
echo -e "${YELLOW}请输入部署配置（按 Enter 使用默认值）:${NC}"

read -p "部署路径 [$PROJECT_DIR]: " DEPLOY_PATH
DEPLOY_PATH=${DEPLOY_PATH:-$PROJECT_DIR}

read -p "运行用户 [root]: " SERVICE_USER
SERVICE_USER=${SERVICE_USER:-root}

read -p "监听端口 [5001]: " SERVICE_PORT
SERVICE_PORT=${SERVICE_PORT:-5001}

echo ""
echo -e "${BLUE}配置摘要:${NC}"
echo -e "  部署路径: ${GREEN}${DEPLOY_PATH}${NC}"
echo -e "  运行用户: ${GREEN}${SERVICE_USER}${NC}"
echo -e "  监听端口: ${GREEN}${SERVICE_PORT}${NC}"
echo -e "  Python:   ${GREEN}${PYTHON_PATH}${NC}"
echo ""

read -p "确认安装? (y/n) [y]: " CONFIRM
CONFIRM=${CONFIRM:-y}
if [ "$CONFIRM" != "y" ]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

# 创建必要的目录
echo -e "${YELLOW}创建目录...${NC}"
mkdir -p "$DEPLOY_PATH/logs"
mkdir -p "$DEPLOY_PATH/db"
mkdir -p "$DEPLOY_PATH/static/uploads"
mkdir -p "$DEPLOY_PATH/backups"
echo -e "${GREEN}✓ 目录创建完成${NC}"

# 生成 systemd 服务文件
echo -e "${YELLOW}生成服务文件...${NC}"

cat > /tmp/simple-blog.service <<EOF
[Unit]
Description=Simple Blog Flask Application
Documentation=https://github.com/lbxxgn/my-blog
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$DEPLOY_PATH

Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"
Environment="PYTHONPATH=$DEPLOY_PATH"
Environment="PORT=$SERVICE_PORT"

# 从 .env 文件加载环境变量（不存在不报错）
EnvironmentFile=-$DEPLOY_PATH/.env

# 启动命令
ExecStart=$PYTHON_PATH $DEPLOY_PATH/backend/app.py

# 重启策略
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# 日志配置
StandardOutput=append:$DEPLOY_PATH/logs/app.log
StandardError=append:$DEPLOY_PATH/logs/error.log

# 资源限制
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# 安装服务文件
echo -e "${YELLOW}安装 systemd 服务...${NC}"
sudo cp /tmp/simple-blog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable simple-blog.service
echo -e "${GREEN}✓ 服务安装完成${NC}"

# 清理临时文件
rm -f /tmp/simple-blog.service

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  安装完成！${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "常用命令:"
echo -e "  ${BLUE}启动服务${NC}:    sudo systemctl start simple-blog"
echo -e "  ${BLUE}停止服务${NC}:    sudo systemctl stop simple-blog"
echo -e "  ${BLUE}重启服务${NC}:    sudo systemctl restart simple-blog"
echo -e "  ${BLUE}查看状态${NC}:    sudo systemctl status simple-blog"
echo -e "  ${BLUE}查看日志${NC}:    sudo journalctl -u simple-blog -f"
echo -e "  ${BLUE}开机自启${NC}:    sudo systemctl enable simple-blog"
echo ""
echo -e "日志文件:"
echo -e "  应用日志: ${YELLOW}${DEPLOY_PATH}/logs/app.log${NC}"
echo -e "  错误日志: ${YELLOW}${DEPLOY_PATH}/logs/error.log${NC}"
echo ""

read -p "是否现在启动服务? (y/n) [y]: " START_NOW
START_NOW=${START_NOW:-y}
if [ "$START_NOW" = "y" ]; then
    sudo systemctl start simple-blog
    sleep 2
    sudo systemctl status simple-blog --no-pager
fi

echo ""
echo -e "${GREEN}完成！${NC}"
