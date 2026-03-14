#!/usr/bin/env python3
"""简化版manifest生成脚本"""
import sys
import os
import json
import hashlib
from pathlib import Path

def calculate_hash(file_path):
    """计算文件MD5 hash（前8位）"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5.update(chunk)
    return md5.hexdigest()[:8]

def generate_manifest():
    """生成manifest.json"""
    static_folder = Path('static')
    manifest_file = static_folder / 'manifest.json'
    manifest = {}

    # 处理CSS和JS文件
    for ext in ['.css', '.js']:
        for file_path in static_folder.rglob(f'*{ext}'):
            # 跳过特定目录
            if any(skip in str(file_path) for skip in ['node_modules', '.venv', '__pycache__', '.git']):
                continue

            try:
                rel_path = str(file_path.relative_to(static_folder))
                file_hash = calculate_hash(file_path)
                path = Path(file_path)
                stem = path.stem
                suffix = path.suffix
                versioned_name = f'{stem}.{file_hash}{suffix}'

                manifest[rel_path] = {
                    'hash': file_hash,
                    'versioned': versioned_name
                }

                print(f'✓ {rel_path} -> {versioned}')

            except Exception as e:
                print(f'✗ {file_path}: {e}')

    # 保存manifest
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f'\n✅ Manifest已保存，共 {len(manifest)} 个资源')
    return manifest

if __name__ == '__main__':
    generate_manifest()
