#!/bin/bash
# Flask 博客系统启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到 backend 目录
cd "$SCRIPT_DIR/backend"

# 设置环境变量
export FLASK_APP=app.py
export FLASK_ENV=production
export PYTHONPATH="$SCRIPT_DIR/backend:$PYTHONPATH"

# 启动应用
echo "正在启动 Flask 博客系统..."
python3 app.py
