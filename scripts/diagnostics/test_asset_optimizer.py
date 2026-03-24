#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.asset_optimizer import AssetOptimizer
from flask import Flask

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['USE_MINIFIED_ASSETS'] = True

asset_optimizer = AssetOptimizer()
asset_optimizer.init_app(app)

with app.test_request_context():
    print("=== 测试静态资源优化器 ===")
    print(f"构建版本: {asset_optimizer.build_version}")

    # 测试CSS文件
    test_css_files = [
        'css/style.css',
        'css/mobile-weibo.css',
        'css/pc-feed.css',
        'css/lightbox.css'
    ]

    print("\nCSS文件测试:")
    for path in test_css_files:
        url = asset_optimizer.static_file(path)
        print(f"  {path:<30} → {url}")

    # 测试JS文件
    test_js_files = [
        'js/main.js',
        'js/lazyload.js',
        'js/mobile-layout.js',
        'js/editor.js',
        'js/passkeys.js'
    ]

    print("\nJavaScript文件测试:")
    for path in test_js_files:
        url = asset_optimizer.static_file(path)
        print(f"  {path:<30} → {url}")

    print("\n=== 测试完成 ===")
