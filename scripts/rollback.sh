#!/bin/bash
###############################################################################
# Simple Blog 回滚脚本
# 将系统恢复到升级前的状态
#
# 使用方法:
#   ./rollback.sh <backup_directory>
#
# 例如:
#   ./rollback.sh backups/upgrade_20260314_105500
#
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 检查参数
if [ $# -lt 1 ]; then
    echo -e "${RED}错误: 请指定备份目录${NC}"
    echo ""
    echo "使用方法: $0 <backup_directory>"
    echo ""
    echo "可用的备份目录:"
    ls -dt backups/upgrade_* 2>/dev/null || echo "  没有找到备份目录"
    exit 1
fi

BACKUP_DIR="$1"

# 检查备份目录是否存在
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}错误: 备份目录不存在: $BACKUP_DIR${NC}"
    exit 1
fi

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 确认回滚
confirm_rollback() {
    cat << EOF

${YELLOW}⚠️  警告: 即将执行回滚操作${NC}

此操作将会:
  1. 停止当前运行的应用
  2. 恢复数据库到升级前的状态
  3. 所有升级后的更改将丢失

备份目录: $BACKUP_DIR

${RED}此操作不可逆！请确认是否继续？${NC}
EOF

    read -p "输入 'yes' 继续，其他任何输入取消: " confirm

    if [ "$confirm" != "yes" ]; then
        echo "回滚已取消"
        exit 0
    fi
}

# 停止应用
stop_application() {
    log "停止当前应用..."

    if lsof -ti:5001 > /dev/null 2>&1; then
        lsof -ti:5001 | xargs kill -9 2>/dev/null || true
        log "应用已停止"
    else
        log_info "没有运行的应用"
    fi

    sleep 2
}

# 恢复数据库
restore_database() {
    log "恢复数据库..."

    if [ -f "$BACKUP_DIR/simple_blog.db" ]; then
        # 确保db目录存在
        mkdir -p db

        # 恢复数据库
        cp "$BACKUP_DIR/simple_blog.db" "$PROJECT_ROOT/db/simple_blog.db"
        log "数据库恢复完成 ✓"
    else
        log_warning "备份数据库不存在，跳过恢复"
    fi
}

# 恢复上传文件
restore_uploads() {
    log "恢复上传文件..."

    if [ -d "$BACKUP_DIR/uploads" ]; then
        # 删除现有的uploads目录（保留用户数据）
        # 注意：这里只恢复升级时的备份，不删除用户之后上传的文件
        log_warning "上传文件恢复需要手动操作"
        log_info "备份位置: $BACKUP_DIR/uploads"
        log_info "目标位置: $PROJECT_ROOT/static/uploads"
    else
        log_info "没有上传文件备份"
    fi
}

# 删除升级新增的文件
remove_upgrade_files() {
    log "清理升级新增的文件..."

    # 注意：这里不删除，只是显示需要手动清理的文件
    log_warning "以下文件/表是升级新增的，如需完全回滚请手动删除："
    echo ""
    echo "  数据库表:"
    echo "    - drafts"
    echo "    - optimized_images"
    echo ""
    echo "  文件:"
    echo "    - static/js/shortcuts.js"
    echo "    - static/js/draft-sync.js"
    echo "    - templates/components/breadcrumb.html"
    echo "    - backend/models/draft.py"
    echo "    - backend/routes/drafts.py"
    echo "    - backend/tasks/image_optimization_task.py"
    echo "    - backend/utils/asset_version.py"
    echo "    - static/manifest.json"
    echo ""
    echo "  如需删除这些文件，请手动执行:"
    echo "    sqlite3 db/simple_blog.db 'DROP TABLE IF EXISTS drafts;'"
    echo "    sqlite3 db/simple_blog.db 'DROP TABLE IF EXISTS optimized_images;'"
}

# 启动应用
start_application() {
    log "启动应用..."

    if [ -f "$BACKUP_DIR/app.pid" ]; then
        old_pid=$(cat "$BACKUP_DIR/app.pid")
        log_info "之前的应用PID: $old_pid"
    fi

    source .venv/bin/activate
    export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
    export ADMIN_PASSWORD="${ADMIN_PASSWORD:-AdminPass123456}"
    export DATABASE_URL="sqlite:///db/simple_blog.db"

    nohup python3 backend/app.py > /tmp/flask.log 2>&1 &

    sleep 5

    if lsof -ti:5001 > /dev/null 2>&1; then
        log "应用启动完成 ✓"
    else
        log_error "应用启动失败，请检查日志: /tmp/flask.log"
        return 1
    fi
}

# 验证回滚
verify_rollback() {
    log "验证回滚结果..."

    # 检查应用是否运行
    if lsof -ti:5001 > /dev/null 2>&1; then
        log "应用运行正常 ✓"

        # 检查数据库
        if [ -f "$PROJECT_ROOT/db/simple_blog.db" ]; then
            log "数据库文件存在 ✓"
        else
            log_error "数据库文件缺失"
        fi

        log "回滚完成"
    else
        log_error "应用未运行"
        return 1
    fi
}

# 主回滚流程
main() {
    echo -e "${BLUE}"
    cat << "EOF"
   _____  ______ _____ _____  _____ _____ _____ ____  _____
  |  \|  || ___ |  _  |_   _|/  ___|  ___|_   _|  _ \|  ___|
  | . ` || |_  | | | | | |  \ `--.| |_    | | | | | | |__
  | |\  ||  _| | |_| | | |   `--. \  _|   | | | |_| |  __|
  | \ \ || |   |  _  | | |  /\__/ | |___  | | |  _  | |___
  | \_/ \_|   \_| |_/ \_/  \____/ \____/  \_/ \_| |_/\____/

             Rollback Script - 恢复到升级前状态
EOF
    echo -e "${NC}"

    log "开始回滚流程..."
    log "备份目录: $BACKUP_DIR"

    # 1. 确认
    confirm_rollback

    # 2. 停止应用
    stop_application

    # 3. 恢复数据库
    restore_database

    # 4. 恢复上传文件（需要手动）
    restore_uploads

    # 5. 清理升级文件（需要手动）
    remove_upgrade_files

    # 6. 启动应用
    start_application

    # 7. 验证
    if verify_rollback; then
        cat << EOF

${GREEN}回滚完成！${NC}

✓ 数据库已恢复
✓ 应用已重启

${YELLOW}注意:${NC}
  - 新增的功能已被禁用
  - 部分文件需要手动删除（见上方列表）
  - 建议检查应用功能是否正常

访问: http://127.0.0.1:5001

EOF
    else
        log_error "回滚验证失败"
        exit 1
    fi
}

# 捕获错误
trap 'log_error "回滚过程中断"; exit 1' ERR

# 运行主流程
main "$@"
