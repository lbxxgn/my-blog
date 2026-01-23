#!/usr/bin/env python3
"""
导入网易博客数据到新系统
"""
import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models import (
    get_db_connection, init_db, create_post, create_category,
    get_all_categories
)

def timestamp_to_datetime(ts_str):
    """将毫秒时间戳转换为 datetime 对象"""
    try:
        timestamp = int(ts_str) / 1000  # 转换为秒
        return datetime.fromtimestamp(timestamp)
    except (ValueError, TypeError):
        return datetime.now()

def clean_html_content(html_content):
    """
    清理 HTML 内容，移除一些多余的标签和样式
    但保留基本的 HTML 结构，因为系统支持 markdown2
    """
    if not html_content:
        return ""

    # 移除一些网易特有的标签
    html_content = html_content.replace('<wbr>', '')
    html_content = html_content.replace('</wbr>', '')

    # 移除 style="white-space:pre;" 这种样式标签（保留文本）
    import re
    html_content = re.sub(r'<span style="white-space:pre;"\s*>\s*</span>', '\n', html_content)
    html_content = re.sub(r'<span style="white-space:pre;"\s*>([^<]*)</span>', r'\1', html_content)

    return html_content.strip()

def import_blogs_from_xml(xml_file_path):
    """从 XML 文件导入博客数据"""

    # 解析 XML
    print(f"正在解析 XML 文件: {xml_file_path}")
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # 获取所有博客条目
    blogs = root.findall('blog')
    print(f"找到 {len(blogs)} 篇博客文章\n")

    # 确保数据库已初始化
    init_db()

    # 获取或创建分类映射
    category_map = {}
    existing_categories = get_all_categories()
    for cat in existing_categories:
        category_map[cat['name']] = cat['id']

    success_count = 0
    skip_count = 0
    error_count = 0

    for blog in blogs:
        try:
            # 提取数据
            title_elem = blog.find('title')
            title = title_elem.text if title_elem is not None else '无标题'

            # 如果标题在 CDATA 中，直接使用
            if title and title.startswith('[') and 'CDATA' in title:
                import re
                match = re.search(r'<!\[CDATA\[(.*?)\]\]', title)
                if match:
                    title = match.group(1)

            content_elem = blog.find('content')
            content = content_elem.text if content_elem is not None else ''

            # 清理内容
            content = clean_html_content(content)

            # 发布状态
            ispublished_elem = blog.find('ispublished')
            is_published = ispublished_elem.text == '1' if ispublished_elem is not None else False

            # 发布时间
            publish_time_elem = blog.find('publishTime')
            created_at = timestamp_to_datetime(publish_time_elem.text) if publish_time_elem is not None else datetime.now()

            # 分类
            class_name_elem = blog.find('className')
            category_name = class_name_elem.text if class_name_elem is not None else None

            if category_name and category_name.startswith('[') and 'CDATA' in category_name:
                import re
                match = re.search(r'<!\[CDATA\[(.*?)\]\]', category_name)
                if match:
                    category_name = match.group(1)

            # 获取或创建分类
            category_id = None
            if category_name and category_name not in category_map:
                cat_id = create_category(category_name)
                if cat_id:
                    category_map[category_name] = cat_id
                    print(f"  创建分类: {category_name}")

            if category_name and category_name in category_map:
                category_id = category_map[category_name]

            # 检查是否已存在（根据标题和时间判断）
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id FROM posts WHERE title = ? AND created_at >= ? AND created_at <= ?',
                (title, created_at, created_at)
            )
            existing = cursor.fetchone()
            conn.close()

            if existing:
                print(f"⏭️  跳过（已存在）: {title} ({created_at.strftime('%Y-%m-%d')})")
                skip_count += 1
                continue

            # 插入数据库
            post_id = create_post(
                title=title,
                content=content,
                is_published=is_published,
                category_id=category_id
            )

            # 更新创建时间为原始发布时间
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE posts SET created_at = ?, updated_at = ? WHERE id = ?',
                (created_at, created_at, post_id)
            )
            conn.commit()
            conn.close()

            status = "✓ 已发布" if is_published else "○ 草稿"
            print(f"✓ 导入成功: {title} ({created_at.strftime('%Y-%m-%d')}) [{status}]")
            success_count += 1

        except Exception as e:
            print(f"✗ 导入失败: {title} - 错误: {str(e)}")
            error_count += 1

    # 打印统计
    print("\n" + "="*60)
    print(f"导入完成！")
    print(f"  成功: {success_count} 篇")
    print(f"  跳过: {skip_count} 篇（已存在）")
    print(f"  失败: {error_count} 篇")
    print("="*60)

if __name__ == '__main__':
    xml_file = '网易博客日志列表.xml'

    # 检查文件是否存在
    if not Path(xml_file).exists():
        # 尝试在项目根目录查找
        root_path = Path(__file__).parent.parent
        xml_file = root_path / '网易博客日志列表.xml'

        if not xml_file.exists():
            print(f"错误: 找不到文件 {xml_file}")
            print("请确保 '网易博客日志列表.xml' 文件在项目根目录下")
            sys.exit(1)

    print("="*60)
    print("网易博客导入工具")
    print("="*60 + "\n")

    import_blogs_from_xml(str(xml_file))
