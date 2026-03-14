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
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
        "static/js/shortcuts.js"
        "static/js/draft-sync.js"
        "templates/components/breadcrumb.html"
        "backend/models/draft.py"
        "backend/routes/drafts.py"
        "backend/tasks/image_optimization_task.py"
        "backend/utils/asset_version.py"
        "backend/utils/template_helpers.py"
        "static/manifest.json"
        "generate_manifest.py"
        "upgrade.sh"
        "rollback.sh"
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

    # 检查端口
    if lsof -ti:5001 > /dev/null 2>&1; then
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

# 6. 检查面包屑导航
check_breadcrumb() {
    print_header "6. 检查面包屑导航"

    # 获取第一个文章ID
    post_id=$(source .venv/bin/activate && python3 -c "
import sys
sys.path.insert(0, 'backend')
from models import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('SELECT id FROM posts LIMIT 1')
result = cursor.fetchone()
conn.close()
print(result[0] if result else '')
" 2>/dev/null)

    if [ -n "$post_id" ]; then
        post_html=$(curl -s "http://127.0.0.1:5001/post/$post_id" 2>/dev/null)

        if [ -n "$post_html" ]; then
            if echo "$post_html" | grep -q 'class="breadcrumb"'; then
                print_success "面包屑导航已显示 (文章ID: $post_id)"

                # 提取面包屑内容
                breadcrumb=$(echo "$post_html" | grep -A 5 'class="breadcrumb"' | grep -E '(首页|<span class="current">)' | sed 's/^[[:space:]]*//' | head -3)
                if [ -n "$breadcrumb" ]; then
                    print_info "面包屑示例: $(echo "$breadcrumb" | tr '\n' ' ' | sed 's/<[^>]*>//g')"
                fi
            else
                print_error "文章页面未显示面包屑导航"
            fi
        else
            print_warning "无法访问文章页面 (ID: $post_id)"
        fi
    else
        print_warning "数据库中没有文章，跳过面包屑检查"
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

2. 🍞 面包屑导航
   - 访问任意文章页面
   - 检查是否显示: 首页 > 分类 > 文章标题
   - 点击面包屑测试导航

3. 💾 草稿自动保存
   - 登录系统: http://127.0.0.1:5001/login
   - 编辑文章，等待30秒
   - 检查浏览器控制台是否有自动保存日志

4. 🖼️  图片优化
   - 上传一张图片
   - 检查 static/uploads/optimized/ 目录
   - 应该生成 thumbnail/medium/large 三个尺寸

5. 🔍 资源版本控制
   - 修改任意CSS文件
   - 重新运行: python3 generate_manifest.py
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
    check_breadcrumb
    check_api_endpoints
    show_test_suggestions
    print_summary
}

# 运行主流程
main
