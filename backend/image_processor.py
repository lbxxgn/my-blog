"""
图片处理服务

提供图片压缩、缩略图生成、格式转换等功能
"""

import os
import io
from pathlib import Path
from PIL import Image, ImageOps
import hashlib
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# 配置
IMAGE_QUALITY = 85  # JPEG/WEBP 质量
MAX_WIDTH = 2560  # 最大宽度
MAX_HEIGHT = 1440  # 最大高度

# 图片尺寸定义
IMAGE_SIZES = {
    'thumbnail': (150, 150),
    'medium': (600, 400),
    'large': (1200, 800)
}


def get_image_hash(image_path: str) -> str:
    """
    计算图片的哈希值（用于去重）

    Args:
        image_path: 图片路径

    Returns:
        str: MD5哈希值
    """
    hash_md5 = hashlib.md5()
    with open(image_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def optimize_image(image_path: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    优化图片：压缩并转换为WebP格式

    Args:
        image_path: 原始图片路径
        output_path: 输出路径（如果为None，则覆盖原文件）

    Returns:
        (成功状态, 消息)
    """
    try:
        # 如果没有指定输出路径，生成新路径
        if output_path is None:
            path = Path(image_path)
            output_path = str(path.parent / f"{path.stem}_optimized{path.suffix}")

        # 打开图片
        with Image.open(image_path) as img:
            # 转换为RGB（如果需要）
            if img.mode in ('RGBA', 'P', 'LA', 'LA'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 调整大小（如果需要）
            if img.width > MAX_WIDTH or img.height > MAX_HEIGHT:
                img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)

            # 保存为WebP格式
            img.save(output_path, 'WEBP', quality=IMAGE_QUALITY, method=6)

            # 计算压缩率
            original_size = os.path.getsize(image_path)
            optimized_size = os.path.getsize(output_path)
            compression_ratio = (1 - optimized_size / original_size) * 100

            logger.info(f'Image optimized: {image_path} -> {output_path}')
            logger.info(f'Size: {original_size} -> {optimized_size} ({compression_ratio:.1f}% reduction)')

            return True, output_path

    except Exception as e:
        logger.error(f'Error optimizing image {image_path}: {e}')
        return False, str(e)


def generate_image_sizes(image_path: str, output_dir: str) -> dict:
    """
    生成多种尺寸的图片

    Args:
        image_path: 原始图片路径
        output_dir: 输出目录

    Returns:
        dict: 各尺寸图片的路径
        {
            'thumbnail': 'path/to/thumbnail.webp',
            'medium': 'path/to/medium.webp',
            'large': 'path/to/large.webp',
            'original': 'path/to/original.webp'
        }
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 计算图片哈希作为文件名（避免重复）
        img_hash = get_image_hash(image_path)
        base_path = os.path.join(output_dir, img_hash)

        result = {
            'original': image_path,
            'thumbnail': None,
            'medium': None,
            'large': None
        }

        # 打开原始图片
        with Image.open(image_path) as img:
            # 转换为RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 生成各种尺寸
            for size_name, (max_width, max_height) in IMAGE_SIZES.items():
                # 创建副本
                img_copy = img.copy()

                # 调整大小
                img_copy.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # 保存
                output_path = f"{base_path}_{size_name}.webp"
                img_copy.save(output_path, 'WEBP', quality=IMAGE_QUALITY)

                result[size_name] = output_path
                logger.debug(f'Generated {size_name}: {output_path}')

        return result

    except Exception as e:
        logger.error(f'Error generating image sizes: {e}')
        return {
            'original': image_path,
            'thumbnail': None,
            'medium': None,
            'large': None
        }


def create_thumbnail(image_path: str, size: Tuple[int, int] = (150, 150)) -> str:
    """
    创建缩略图

    Args:
        image_path: 原始图片路径
        size: 缩略图尺寸 (宽, 高)

    Returns:
        str: 缩略图路径
    """
    try:
        path = Path(image_path)
        thumbnail_path = path.parent / f"{path.stem}_thumb.webp"

        with Image.open(image_path) as img:
            # 转换为RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 创建缩略图（使用智能裁剪）
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # 如果图片是方形的，居中裁剪
            if img.width == img.height:
                img = ImageOps.fit(img, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))

            img.save(thumbnail_path, 'WEBP', quality=IMAGE_QUALITY)
            return str(thumbnail_path)

    except Exception as e:
        logger.error(f'Error creating thumbnail: {e}')
        return image_path  # 失败时返回原路径


def get_image_info(image_path: str) -> dict:
    """
    获取图片信息

    Args:
        image_path: 图片路径

    Returns:
        dict: 图片信息
    """
    try:
        with Image.open(image_path) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'size_bytes': os.path.getsize(image_path),
                'size_mb': os.path.getsize(image_path) / (1024 * 1024)
            }
    except Exception as e:
        logger.error(f'Error getting image info: {e}')
        return None


def is_image_file(filename: str) -> bool:
    """
    检查是否为图片文件

    Args:
        filename: 文件名

    Returns:
        bool: 是否为图片
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
    return Path(filename).suffix.lower() in image_extensions


def get_image_url(image_path: str, size: Optional[str] = None) -> str:
    """
    获取图片URL（用于响应式图片）

    Args:
        image_path: 图片路径
        size: 尺寸类型 (thumbnail/medium/large)

    Returns:
        str: 图片URL
    """
    path = Path(image_path)

    # 如果是WebP图片且有不同尺寸
    if path.suffix == '.webp':
        if size and f'_{size}' in path.stem:
            # 返回指定尺寸的图片
            return f"/static/uploads/{path.name}"
        else:
            # 返回原图片或默认尺寸
            return f"/static/uploads/{path.name}"

    # 非WebP图片，返回原路径
    return f"/static/uploads/{path.name}"
