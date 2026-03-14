#!/bin/bash
###############################################################################
# Simple Blog UX增强功能升级脚本
# 从旧版本升级到包含5个UX增强功能的新版本
#
# 功能列表：
# 1. 键盘快捷键支持
# 2. 面包屑导航
# 3. 草稿服务器同步
# 4. 图片自动压缩优化
# 5. 静态资源自动版本化
#
# 使用方法:
#   chmod +x upgrade.sh
#   ./upgrade.sh
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

# 备份目录
BACKUP_DIR="$PROJECT_ROOT/backups/upgrade_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BACKUP_DIR/upgrade.log"

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

# 创建备份目录
create_backup_dir() {
    log "创建备份目录: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
}

# 检查环境
check_environment() {
    log "检查运行环境..."

    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi

    python_version=$(python3 --version | awk '{print $2}')
    log_info "Python版本: $python_version"

    # 检查虚拟环境
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        log_warning "虚拟环境不存在，将创建新的虚拟环境"
        python3 -m venv .venv
        log "虚拟环境创建完成"
    fi

    # 激活虚拟环境
    source .venv/bin/activate

    # 检查pip
    if ! command -v pip &> /dev/null; then
        log_error "pip 未安装"
        exit 1
    fi

    log "环境检查完成 ✓"
}

# 备份数据库
backup_database() {
    log "备份数据库..."

    if [ -f "$PROJECT_ROOT/db/simple_blog.db" ]; then
        cp "$PROJECT_ROOT/db/simple_blog.db" "$BACKUP_DIR/simple_blog.db"
        log "数据库已备份到: $BACKUP_DIR/simple_blog.db"
    else
        log_warning "数据库文件不存在，跳过备份"
    fi
}

# 备份静态资源
backup_static_assets() {
    log "备份静态资源..."

    if [ -d "$PROJECT_ROOT/static" ]; then
        # 只备份manifest和关键文件
        [ -f "$PROJECT_ROOT/static/manifest.json" ] && \
            cp "$PROJECT_ROOT/static/manifest.json" "$BACKUP_DIR/"

        log "静态资源已备份"
    else
        log_warning "static目录不存在，跳过备份"
    fi
}

# 备份上传的文件
backup_uploads() {
    log "备份上传文件..."

    if [ -d "$PROJECT_ROOT/static/uploads" ]; then
        mkdir -p "$BACKUP_DIR/uploads"
        cp -r "$PROJECT_ROOT/static/uploads/"* "$BACKUP_DIR/uploads/" 2>/dev/null || true
        log "上传文件已备份到: $BACKUP_DIR/uploads"
    else
        log_info "uploads目录不存在，跳过备份"
    fi
}

# 安装/更新依赖
install_dependencies() {
    log "检查并安装Python依赖..."

    source .venv/bin/activate

    # 检查requirements.txt是否存在
    if [ -f "$PROJECT_ROOT/backend/requirements.txt" ]; then
        pip install -r backend/requirements.txt --quiet >> "$LOG_FILE" 2>&1
        log "依赖安装完成 ✓"
    else
        log_warning "requirements.txt 不存在"
    fi
}

# 运行数据库迁移
run_migrations() {
    log "运行数据库迁移..."

    source .venv/bin/activate
    export DATABASE_URL="sqlite:///db/simple_blog.db"

    # 运行drafts表迁移
    if [ -f "$PROJECT_ROOT/backend/migrations/migrate_drafts.py" ]; then
        log "创建草稿同步表..."
        python3 backend/migrations/migrate_drafts.py >> "$LOG_FILE" 2>&1
        log "drafts表迁移完成 ✓"
    else
        log_warning "migrate_drafts.py 不存在，跳过"
    fi

    # 运行图片优化表迁移
    if [ -f "$PROJECT_ROOT/backend/migrations/migrate_image_optimization.py" ]; then
        log "创建图片优化表..."
        python3 backend/migrations/migrate_image_optimization.py >> "$LOG_FILE" 2>&1
        log "optimized_images表迁移完成 ✓"
    else
        log_warning "migrate_image_optimization.py 不存在，跳过"
    fi
}

# 生成静态资源manifest
generate_manifest() {
    log "生成静态资源manifest..."

    if [ -f "$PROJECT_ROOT/generate_manifest.py" ]; then
        source .venv/bin/activate
        python3 generate_manifest.py >> "$LOG_FILE" 2>&1
        log "manifest生成完成 ✓"
    else
        log_warning "generate_manifest.py 不存在，使用AssetVersionManager生成"

        # 使用Python代码生成
        source .venv/bin/activate
        python3 -c "
import sys
sys.path.insert(0, 'backend')
from utils.asset_version import AssetVersionManager
manager = AssetVersionManager('static')
manager.regenerate()
print('Manifest生成完成')
" >> "$LOG_FILE" 2>&1
    fi
}

# 创建必要的目录
create_directories() {
    log "创建必要的目录..."

    mkdir -p static/uploads/optimized
    mkdir -p db

    log "目录创建完成 ✓"
}

# 停止现有应用
stop_application() {
    log "停止现有应用..."

    # 查找并杀死Flask进程
    if lsof -ti:5001 > /dev/null 2>&1; then
        lsof -ti:5001 | xargs kill -9 2>/dev/null || true
        log "应用已停止 ✓"
    else
        log_info "没有运行在端口5001的应用"
    fi

    sleep 2
}

# 启动应用
start_application() {
    log "启动应用..."

    source .venv/bin/activate
    export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
    export ADMIN_PASSWORD="${ADMIN_PASSWORD:-AdminPass123456}"
    export DATABASE_URL="sqlite:///db/simple_blog.db"

    nohup python3 backend/app.py > /tmp/flask.log 2>&1 &
    APP_PID=$!

    # 等待应用启动
    sleep 5

    # 检查应用是否运行
    if ps -p $APP_PID > /dev/null 2>&1; then
        log "应用启动成功 (PID: $APP_PID) ✓"
        echo $APP_PID > "$BACKUP_DIR/app.pid"
    else
        log_error "应用启动失败，请检查日志: /tmp/flask.log"
        return 1
    fi
}

# 验证升级
verify_upgrade() {
    log "验证升级结果..."

    local errors=0

    # 1. 检查应用是否运行
    if ! lsof -ti:5001 > /dev/null 2>&1; then
        log_error "应用未在端口5001运行"
        ((errors++))
    else
        log_info "✓ 应用运行正常"
    fi

    # 2. 检查数据库表
    source .venv/bin/activate
    export DATABASE_URL="sqlite:///db/simple_blog.db"

    tables_exist=$(python3 -c "
import sys
sys.path.insert(0, 'backend')
from models import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute(\"\"\"
    SELECT COUNT(*) FROM sqlite_master
    WHERE type='table' AND name IN ('drafts', 'optimized_images')
\"\"\")
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null)

    if [ "$tables_exist" = "2" ]; then
        log_info "✓ 数据库表已创建"
    else
        log_error "数据库表未正确创建"
        ((errors++))
    fi

    # 3. 检查manifest文件
    if [ -f "$PROJECT_ROOT/static/manifest.json" ]; then
        manifest_count=$(python3 -c "import json; print(len(json.load(open('static/manifest.json'))))" 2>/dev/null || echo "0")
        if [ "$manifest_count" -gt 0 ]; then
            log_info "✓ Manifest已生成 ($manifest_count 个资源)"
        else
            log_error "Manifest文件为空或无效"
            ((errors++))
        fi
    else
        log_error "Manifest文件不存在"
        ((errors++))
    fi

    # 4. 检查静态资源可访问性
    css_response=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:5001/static/css/style.css" 2>/dev/null || echo "000")
    if [ "$css_response" = "200" ]; then
        log_info "✓ 静态资源可访问"
    else
        log_warning "静态资源访问异常 (HTTP $css_response)"
    fi

    # 5. 检查关键文件
    local key_files=(
        "static/js/shortcuts.js"
        "static/js/draft-sync.js"
        "templates/components/breadcrumb.html"
        "backend/models/draft.py"
        "backend/routes/drafts.py"
        "backend/tasks/image_optimization_task.py"
    )

    for file in "${key_files[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            log_info "✓ $file"
        else
            log_error "✗ $file 缺失"
            ((errors++))
        fi
    done

    # 总结
    echo ""
    log "验证完成"
    if [ $errors -eq 0 ]; then
        log "升级成功！所有检查通过 🎉"
        return 0
    else
        log_error "发现 $errors 个问题，请检查日志"
        return 1
    fi
}

# 显示升级后信息
show_post_upgrade_info() {
    cat << EOF

================================================================================
                    升级完成！新功能使用指南
================================================================================

✨ 新增功能：

1. ⌨️  键盘快捷键
   - Ctrl+N: 新建文章
   - Ctrl+B: 编辑器内加粗
   - ESC: 关闭编辑器（带确认）
   - 访问页面查看快捷键提示

2. 🍞 面包屑导航
   - 文章页面显示: 首页 > 分类 > 文章标题
   - 访问任意文章查看效果

3. 💾 草稿自动同步
   - 编辑时每30秒自动保存到服务器
   - 多设备编辑会自动检测冲突
   - 登录后编辑文章自动启用

4. 🖼️  图片自动优化
   - 上传图片自动生成thumbnail/medium/large尺寸
   - 优化后的图片保存在 static/uploads/optimized/
   - 自动转换为WebP格式

5. 🔍 静态资源版本控制
   - CSS/JS文件自动添加版本号 (?v=hash)
   - 文件修改后自动更新版本号
   - 解决浏览器缓存问题

📍 访问地址：
   - 首页: http://127.0.0.1:5001
   - 登录: http://127.0.0.1:5001/login
   - 管理后台: http://127.0.0.1:5001/admin

📝 备份位置：
   - $BACKUP_DIR

📋 应用日志：
   - tail -f /tmp/flask.log

🔄 回滚方法：
   - 如有问题，可使用备份恢复数据库和静态文件

================================================================================

EOF
}

# 主升级流程
main() {
    echo -e "${BLUE}"
    cat << "EOF"
   _____  ______ _____ _____  _____ _____ _____ ____  _____
  |  \|  || ___ |  _  |_   _|/  ___|  ___|_   _|  _ \|  ___|
  | . ` || |_  | | | | | |  \ `--.| |_    | | | | | | |__
  | |\  ||  _| | |_| | | |   `--. \  _|   | | | |_| |  __|
  | \ \ || |   |  _  | | |  /\__/ | |___  | | |  _  | |___
  | \_/ \_|   \_| |_/ \_/  \____/ \____/  \_/ \_| |_/\____/

            UX Enhancement Upgrade Script
EOF
    echo -e "${NC}"

    log "开始升级流程..."
    log "日志文件: $LOG_FILE"

    # 1. 创建备份
    create_backup_dir || exit 1
    backup_database || exit 1
    backup_static_assets || true
    backup_uploads || true

    # 2. 检查环境
    check_environment || exit 1

    # 3. 安装依赖
    install_dependencies || exit 1

    # 4. 创建目录
    create_directories || exit 1

    # 5. 运行迁移
    run_migrations || exit 1

    # 6. 生成manifest
    generate_manifest || log_warning "Manifest生成失败，但不影响核心功能"

    # 7. 重启应用
    stop_application || true
    start_application || exit 1

    # 8. 验证
    if verify_upgrade; then
        show_post_upgrade_info
        exit 0
    else
        log_error "升级验证失败，请检查日志"
        exit 1
    fi
}

# 捕获错误
trap 'log_error "升级过程中断，请检查日志: $LOG_FILE"; exit 1' ERR

# 运行主流程
main "$@"
