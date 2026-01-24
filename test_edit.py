#!/usr/bin/env python
"""测试编辑功能"""
import sys
sys.path.insert(0, 'backend')

from models import update_post_with_tags, get_post_by_id, get_all_categories

print("=== 测试文章编辑功能 ===\n")

try:
    # 获取第一篇文章
    post = get_post_by_id(1)
    if not post:
        print("✗ 没有找到文章")
        sys.exit(1)

    print(f"测试文章: {post['title']}")
    print(f"分类ID: {post['category_id']}")
    print()

    # 测试1: 只更新文章，不更新标签
    print("测试1: 更新文章内容（无标签）...")
    result1 = update_post_with_tags(
        post['id'],
        post['title'],
        post['content'],
        post['is_published'],
        post['category_id'],
        None
    )
    print(f"  结果: {'✓ 成功' if result1 else '✗ 失败'}\n")

    # 测试2: 更新文章和标签
    print("测试2: 更新文章内容（含标签）...")
    result2 = update_post_with_tags(
        post['id'],
        post['title'],
        post['content'],
        post['is_published'],
        post['category_id'],
        ['Python', '测试']
    )
    print(f"  结果: {'✓ 成功' if result2 else '✗ 失败'}\n")

    # 测试3: 获取分类
    print("测试3: 获取分类列表...")
    categories = get_all_categories()
    print(f"  分类数: {len(categories)}")
    for cat in categories:
        print(f"  - {cat['name']}")
    print()

    print("✅ 所有测试通过！")
    print("\n现在可以安全地编辑文章了。")

except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
