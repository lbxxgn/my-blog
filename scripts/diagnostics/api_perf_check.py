#!/usr/bin/env python3
"""后端接口性能检查脚本。"""

from datetime import datetime
from pathlib import Path
import sys
import time

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://localhost:5001"

def test_api_endpoint(url, name, iterations=5):
    """测试API端点性能"""
    print(f"\n=== 测试 {name} ===")

    # 预热
    requests.get(f"{BASE_URL}{url}")

    total_time = 0
    min_time = float('inf')
    max_time = 0

    for i in range(iterations):
        start_time = time.time()
        response = requests.get(f"{BASE_URL}{url}")
        elapsed = (time.time() - start_time) * 1000

        total_time += elapsed
        min_time = min(min_time, elapsed)
        max_time = max(max_time, elapsed)

        print(f"请求 {i+1}: {elapsed:.2f}ms")

    avg_time = total_time / iterations
    print(f"平均: {avg_time:.2f}ms, 最小: {min_time:.2f}ms, 最大: {max_time:.2f}ms")
    return avg_time

def test_tags_page():
    """测试标签页面性能"""
    print("\n=== 测试标签页面性能 ===")

    from backend.models import get_db_connection

    # 先获取标签数量
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tags")
    tag_count = cursor.fetchone()[0]
    conn.close()

    print(f"总共有 {tag_count} 个标签")

    # 测试未优化版本（模拟）
    print("\n未优化版本（模拟）: 每个标签需要单独查询")
    print(f"预估时间: {tag_count * 50:.2f}ms ({tag_count}个标签 × 50ms/查询)")

    # 测试优化后的实际页面
    return test_api_endpoint("/tags", "标签页面")

def main():
    print("博客系统性能测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试服务器: {BASE_URL}")

    # 测试各个端点
    test_api_endpoint("/api/posts", "文章列表API (无缓存)")

    # 第二次测试API（应该会命中缓存）
    test_api_endpoint("/api/posts", "文章列表API (缓存命中)")

    test_api_endpoint("/api/posts?per_page=40", "文章列表API (40条/页)")
    test_api_endpoint("/api/share/qrcode?url=https://example.com", "二维码生成API")
    test_api_endpoint("/", "首页")

    # 测试标签页面
    test_tags_page()

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
