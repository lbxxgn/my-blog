#!/bin/bash
###############################################################################
# Simple Blog 升级验证脚本
# 快速验证所有新功能是否正常工作
#
# 使用方法:
#   chmod +x verify_upgrade.sh
#   ./verify_upgrade.sh
#
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
# 项目根目录（脚本在 scripts/ 子目录时取上一级，兼容被复制到根目录的情况）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
fi
cd "$PROJECT_ROOT"

# 统计变量
total_checks=0
passed_checks=0
failed_checks=0
warnings=0

# 打印函数
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((passed_checks++))
    ((total_checks++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((failed_checks++))
    ((total_checks++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((warnings++))
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# 1. 检查文件存在性
check_files() {
    print_header "1. 检查新增文件"

    local files=(
        # 2026-09 个人效率功能版本
        "backend/routes/review.py"
        "backend/routes/search_helpers.py"
        "backend/services/weekly_review.py"
        "backend/models/embeddings.py"
        "backend/tasks/embedding_task.py"
        "templates/review.html"
        "templates/quick_capture.html"
        "static/js/command-palette.js"
        "static/js/review.js"
        "static/js/quick-capture.js"
        "static/sw.js"
        # 历史版本
        "static/js/shortcuts.js"
        "static/js/draft-sync.js"
        "backend/models/draft.py"
        "backend/routes/drafts.py"
        "backend/tasks/image_optimization_task.py"
        "backend/utils/asset_version.py"
        "backend/utils/template_helpers.py"
        "static/manifest.json"
        "scripts/generate_manifest.py"
        "scripts/upgrade.sh"
        "scripts/rollback.sh"
    )

    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            print_success "$file"
        else
            print_error "$file 缺失"
        fi
    done
}

# 2. 检查数据库
check_database() {
    print_header "2. 检查数据库"

    if [ ! -f "db/simple_blog.db" ]; then
        print_error "数据库文件不存在"
        return
    fi

    print_success "数据库文件存在"

    # 检查表结构
    source .venv/bin/activate
    export DATABASE_URL="sqlite:///db/simple_blog.db"

    # 检查drafts表
    drafts_exists=$(python3 -c "
import sys
sys.path.insert(0, 'backend')
from models import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='drafts'\")
result = cursor.fetchone()
conn.close()
print(1 if result else 0)
" 2>/dev/null)

    if [ "$drafts_exists" = "1" ]; then
        print_success "drafts表已创建"

        # 检查索引
        drafts_indexes=$(python3 -c "
import sys
sys.path.insert(0, 'backend')
from models import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute(\"SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name='drafts'\")
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null)

        if [ "$drafts_indexes" -ge 2 ]; then
            print_success "drafts表索引已创建 ($drafts_indexes 个)"
        else
            print_warning "drafts表索引可能缺失"
        fi
    else
        print_error "drafts表未创建"
    fi

    # 检查optimized_images表
    images_exists=$(python3 -c "
import sys
sys.path.insert(0, 'backend')
from models import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='optimized_images'\")
result = cursor.fetchone()
conn.close()
print(1 if result else 0)
" 2>/dev/null)

    if [ "$images_exists" = "1" ]; then
        print_success "optimized_images表已创建"
    else
        print_error "optimized_images表未创建"
    fi
}

# 3. 检查静态资源
check_static_assets() {
    print_header "3. 检查静态资源"

    # 检查manifest
    if [ -f "static/manifest.json" ]; then
        manifest_count=$(python3 -c "import json; print(len(json.load(open('static/manifest.json'))))" 2>/dev/null || echo "0")
        if [ "$manifest_count" -gt 0 ]; then
            print_success "manifest.json已生成 ($manifest_count 个资源)"
        else
            print_error "manifest.json为空或无效"
        fi
    else
        print_error "manifest.json不存在"
    fi

    # 检查uploads/optimized目录
    if [ -d "static/uploads/optimized" ]; then
        print_success "uploads/optimized目录已创建"
    else
        print_error "uploads/optimized目录不存在"
    fi
}

# 4. 检查应用运行状态
check_app_status() {
    print_header "4. 检查应用运行状态"

    # 检查端口（优先 lsof，缺失时退回 ss，再退回 curl 探测）
    local port_open=0
    if command -v lsof > /dev/null 2>&1; then
        lsof -ti:5001 > /dev/null 2>&1 && port_open=1
    elif command -v ss > /dev/null 2>&1; then
        ss -tln 2>/dev/null | grep -q ':5001' && port_open=1
    else
        curl -s -o /dev/null --max-time 3 http://127.0.0.1:5001 > /dev/null 2>&1 && port_open=1
    fi

    # 检查端口
    if [ "$port_open" = "1" ]; then
        print_success "应用在端口5001运行"

        # 检查首页
        http_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001 2>/dev/null || echo "000")
        if [ "$http_code" = "200" ]; then
            print_success "首页可访问 (HTTP 200)"
        else
            print_error "首页访问失败 (HTTP $http_code)"
        fi

        # 检查CSS文件
        css_code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:5001/static/css/style.css" 2>/dev/null || echo "000")
        if [ "$css_code" = "200" ]; then
            print_success "CSS文件可访问 (HTTP 200)"
        else
            print_error "CSS文件访问失败 (HTTP $css_code)"
        fi

        # 检查快捷键JS
        js_code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:5001/static/js/shortcuts.js" 2>/dev/null || echo "000")
        if [ "$js_code" = "200" ]; then
            print_success "快捷键JS可访问 (HTTP 200)"
        else
            print_error "快捷键JS访问失败 (HTTP $js_code)"
        fi
    else
        print_error "应用未在端口5001运行"
    fi
}

# 5. 检查版本化URL
check_versioned_urls() {
    print_header "5. 检查静态资源版本化"

    homepage_html=$(curl -s http://127.0.0.1:5001 2>/dev/null)

    if [ -n "$homepage_html" ]; then
        # 检查CSS链接
        if echo "$homepage_html" | grep -q 'href="[^"]*\.css?v='; then
            print_success "CSS文件使用版本化URL (?v=hash)"
        else
            print_error "CSS文件未使用版本化URL"
        fi

        # 检查JS链接
        if echo "$homepage_html" | grep -q 'src="[^"]*\.js?v='; then
            print_success "JS文件使用版本化URL (?v=hash)"
        else
            print_error "JS文件未使用版本化URL"
        fi

        # 显示示例URL
        example_css=$(echo "$homepage_html" | grep -o 'href="[^"]*style\.css[^"]*"' | head -1)
        if [ -n "$example_css" ]; then
            print_info "示例CSS链接: $example_css"
        fi
    else
        print_error "无法获取首页HTML"
    fi
}

# 6. 检查个人效率功能（2026-09 版本）
check_personal_features() {
    print_header "6. 检查个人效率功能"

    # service worker（PWA 安装前提）
    sw_js=$(curl -s "http://127.0.0.1:5001/sw.js" 2>/dev/null)
    if echo "$sw_js" | grep -q "addEventListener"; then
        print_success "service worker 可访问 (/sw.js)"
    else
        print_error "service worker 不可访问或内容异常"
    fi

    # PWA share_target
    manifest=$(curl -s "http://127.0.0.1:5001/static/site.webmanifest" 2>/dev/null)
    if echo "$manifest" | grep -q "share_target"; then
        print_success "PWA share_target 已配置"
    else
        print_error "site.webmanifest 缺少 share_target"
    fi

    # 命令面板资源注入
    homepage_html=$(curl -s http://127.0.0.1:5001 2>/dev/null)
    if echo "$homepage_html" | grep -q "command-palette"; then
        print_success "命令面板资源已注入首页"
    else
        print_error "首页未引入命令面板 (command-palette.js)"
    fi

    # 回顾页路由（未登录 302 / 已登录 200 均为正常）
    review_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/review 2>/dev/null || echo "000")
    if [ "$review_code" = "302" ] || [ "$review_code" = "200" ]; then
        print_success "回顾页 /review 路由存在 (HTTP $review_code)"
    else
        print_error "回顾页 /review 异常 (HTTP $review_code)"
    fi
}

# 7. 检查API端点
check_api_endpoints() {
    print_header "7. 检查API端点"

    # 检查草稿API（应该返回401未授权）
    draft_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:5001/api/drafts \
        -H "Content-Type: application/json" \
        -d '{"title":"test"}' 2>/dev/null || echo "000")

    if [ "$draft_response" = "401" ] || [ "$draft_response" = "400" ]; then
        print_success "草稿API端点响应正常 (HTTP $draft_response - 需要认证)"
    else
        print_warning "草稿API端点响应异常 (HTTP $draft_response)"
    fi

    # 检查回顾API（未登录应 401）
    review_response=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/api/review/today 2>/dev/null || echo "000")

    if [ "$review_response" = "401" ]; then
        print_success "回顾API端点响应正常 (HTTP 401 - 需要认证)"
    else
        print_warning "回顾API端点响应异常 (HTTP $review_response)"
    fi
}

# 8. 功能测试建议
show_test_suggestions() {
    print_header "8. 手动功能测试建议"

    cat << 'EOF'

请手动测试以下功能:

1. ⌨️  键盘快捷键
   - 访问首页: http://127.0.0.1:5001
   - 按 Ctrl+N 应该跳转到新建文章
   - 在编辑器按 ESC 应该提示确认关闭

2. ⌘K 命令面板（桌面端，需登录）
   - 按 Ctrl+K 应弹出命令面板
   - 输入关键词可跨文章/卡片/文档/批注搜索

3. 💾 草稿自动保存
   - 登录系统: http://127.0.0.1:5001/login
   - 编辑文章，等待30秒
   - 检查浏览器控制台是否有自动保存日志

4. 🖼️  图片优化
   - 上传一张图片
   - 检查 static/uploads/optimized/ 目录
   - 应该生成 thumbnail/medium/large 三个尺寸

5. 📅 回顾页与每周回顾
   - 访问 /review，应显示热力图、那年今日、随机漫步
   - 手动生成一次每周回顾，约1分钟内出现在列表
   - crontab 可挂: flask weekly-review

6. ⚡ 快捷捕捉与语音（移动端）
   - 访问 /quick-capture，可存为卡片或快速记事
   - 手机安装 PWA 后系统分享可直达本页
   - Chrome/Edge/Safari 下麦克风按钮可说中文转文字

7. 🔍 资源版本控制
   - 修改任意CSS文件
   - 重新运行: python3 scripts/generate_manifest.py
   - 刷新页面查看URL中的hash值是否改变

EOF
}

# 9. 生成总结报告
print_summary() {
    print_header "验证总结"

    success_rate=0
    if [ $total_checks -gt 0 ]; then
        success_rate=$((passed_checks * 100 / total_checks))
    fi

    echo ""
    echo -e "总检查项: ${BLUE}$total_checks${NC}"
    echo -e "通过: ${GREEN}$passed_checks${NC}"
    echo -e "失败: ${RED}$failed_checks${NC}"
    echo -e "警告: ${YELLOW}$warnings${NC}"
    echo -e "通过率: ${BLUE}${success_rate}%${NC}"
    echo ""

    if [ $failed_checks -eq 0 ]; then
        echo -e "${GREEN}🎉 所有检查通过！升级成功！${NC}"
        return 0
    else
        echo -e "${RED}❌ 发现 $failed_checks 个问题，请检查并修复${NC}"
        echo ""
        echo "常见问题解决方案:"
        echo "  1. 应用未运行: ./upgrade.sh 重新启动"
        echo "  2. 数据库表缺失: source .venv/bin/activate && python3 backend/migrations/migrate_*.py"
        echo "  3. manifest缺失: python3 generate_manifest.py"
        echo "  4. 文件缺失: 检查文件是否被正确创建"
        return 1
    fi
}

# 主流程
main() {
    echo -e "${BLUE}"
    cat << "EOF"
   _____  ______ _____ _____  _____ _____ _____ ____  _____
  |  \|  || ___ |  _  |_   _|/  ___|  ___|_   _|  _ \|  ___|
  | . ` || |_  | | | | | |  \ `--.| |_    | | | | | | |__
  | |\  ||  _| | |_| | | |   `--. \  _|   | | | |_| |  __|
  | \ \ || |   |  _  | | |  /\__/ | |___  | | |  _  | |___
  | \_/ \_|   \_| |_/ \_/  \____/ \____/  \_/ \_| |_/\____/

            Upgrade Verification Script
EOF
    echo -e "${NC}"

    # 执行所有检查
    check_files
    check_database
    check_static_assets
    check_app_status
    check_versioned_urls
    check_personal_features
    check_api_endpoints
    show_test_suggestions
    print_summary
}

# 运行主流程
main
