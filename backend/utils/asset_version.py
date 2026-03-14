"""静态资源版本管理 - 基于文件内容hash自动生成版本号"""
import os
import json
import hashlib
import base64
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class AssetVersionManager:
    """静态资源版本管理器"""

    def __init__(self, static_folder: str):
        self.static_folder = Path(static_folder)
        self.manifest_file = self.static_folder / 'manifest.json'
        self.manifest: Dict = self._load_or_generate_manifest()

    def _load_or_generate_manifest(self) -> Dict:
        """加载或生成manifest文件"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                logger.info(f'已加载manifest文件，共{len(manifest)}个资源')
                return manifest
            except Exception as e:
                logger.warning(f'加载manifest失败: {e}，将重新生成')

        return self._generate_manifest()

    def _generate_manifest(self) -> Dict:
        """生成文件hash映射"""
        manifest = {}
        extensions = ['.css', '.js']

        logger.info('开始生成manifest...')

        for ext in extensions:
            for file_path in self.static_folder.rglob(f'*{ext}'):
                # 跳过特定目录
                if any(skip in str(file_path) for skip in ['node_modules', '.venv', '__pycache__', '.git']):
                    continue

                try:
                    rel_path = str(file_path.relative_to(self.static_folder))
                    file_hash = self._calculate_hash(file_path)
                    versioned_name = self._version_filename(rel_path, file_hash)

                    manifest[rel_path] = {
                        'hash': file_hash,
                        'versioned': versioned_name,
                        'integrity': self._calculate_sri(file_path)
                    }

                    logger.debug(f'{rel_path} -> {versioned_name}')

                except Exception as e:
                    logger.error(f'处理文件{file_path}失败: {e}')

        self._save_manifest(manifest)
        return manifest

    def _calculate_hash(self, file_path: Path) -> str:
        """计算文件内容的MD5 hash（前8位）"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)
        return md5.hexdigest()[:8]

    def _calculate_sri(self, file_path: Path) -> str:
        """计算Subresource Integrity哈希（sha384）"""
        sha384 = hashlib.sha384()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha384.update(chunk)
        return f'sha384-{base64.b64encode(sha384.digest()).decode()}'

    def _version_filename(self, relative_path: str, file_hash: str) -> str:
        """生成版本化文件名"""
        path = Path(relative_path)
        stem = path.stem
        suffix = path.suffix
        # 保留原始路径结构（相对于static文件夹）
        parent = path.parent
        versioned_filename = f'{stem}.{file_hash}{suffix}'
        if parent == Path('.'):
            return versioned_filename
        else:
            # 返回相对于static文件夹的路径
            return str(parent / versioned_filename)

    def _save_manifest(self, manifest: Dict):
        """保存manifest文件"""
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info(f'Manifest已保存到 {self.manifest_file}')

    def get_versioned_path(self, relative_path: str) -> str:
        """获取版本化的文件路径"""
        if relative_path in self.manifest:
            return self.manifest[relative_path]['versioned']
        logger.warning(f'未找到资源版本信息: {relative_path}')
        return relative_path

    def get_integrity(self, relative_path: str) -> Optional[str]:
        """获取SRI哈希"""
        if relative_path in self.manifest:
            return self.manifest[relative_path].get('integrity')
        return None

    def regenerate(self):
        """强制重新生成manifest"""
        logger.info('重新生成manifest...')
        self.manifest = self._generate_manifest()
