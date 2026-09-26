"""
站点图标生成工具

后台上传一张方形原图 -> 生成 favicon、iOS 主屏图标与 PWA 图标的多尺寸 PNG。
生成文件固定存放于 static/uploads/site/，由 app.py 的动态路由对外提供，
未上传时回退到仓库自带的默认图标。
"""

import io
from pathlib import Path

from PIL import Image

from backend.config import UPLOAD_FOLDER

# 需要生成的 PNG 尺寸（含站点导航 logo 用到的 48）
ICON_PNG_SIZES = (16, 32, 48, 180, 192, 512)
# favicon.ico 内嵌尺寸
FAVICON_SIZES = [(16, 16), (32, 32), (48, 48)]

# 源图限制
MAX_SOURCE_BYTES = 10 * 1024 * 1024  # 10MB
MIN_SOURCE_DIMENSION = 180

RESAMPLING = getattr(Image, 'Resampling', Image).LANCZOS


def site_icon_dir() -> Path:
    """站点图标输出目录（按需创建）。"""
    path = Path(UPLOAD_FOLDER) / 'site'
    path.mkdir(parents=True, exist_ok=True)
    return path


def has_custom_icons() -> bool:
    """是否已上传过自定义图标。"""
    return (Path(UPLOAD_FOLDER) / 'site' / 'icon-512.png').exists()


def _load_square(file_content: bytes) -> Image.Image:
    """校验并居中裁成正方形，返回可缩放的 PIL 图像。"""
    if not file_content:
        raise ValueError('未选择文件')
    if len(file_content) > MAX_SOURCE_BYTES:
        raise ValueError(f'文件过大（最大 {MAX_SOURCE_BYTES // 1024 // 1024}MB）')

    try:
        img = Image.open(io.BytesIO(file_content))
        img.load()
    except Exception as exc:  # noqa: BLE001 - 统一转成友好提示
        raise ValueError('图片文件损坏或格式不支持') from exc

    width, height = img.size
    if min(width, height) < MIN_SOURCE_DIMENSION:
        raise ValueError(
            f'图片尺寸过小，至少需要 {MIN_SOURCE_DIMENSION}x{MIN_SOURCE_DIMENSION}'
        )

    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA')
    return img


def generate_site_icons(file_content: bytes) -> Path:
    """由上传内容生成全部尺寸图标，返回输出目录。失败抛 ValueError。"""
    img = _load_square(file_content)
    out = site_icon_dir()

    for size in ICON_PNG_SIZES:
        resized = img.resize((size, size), RESAMPLING)
        resized.save(out / f'icon-{size}.png', format='PNG', optimize=True)

    img.convert('RGBA').save(
        out / 'favicon.ico', format='ICO', sizes=FAVICON_SIZES
    )
    return out


def reset_site_icons() -> None:
    """删除所有自定义图标文件，回退到默认图标。"""
    out = Path(UPLOAD_FOLDER) / 'site'
    if not out.exists():
        return
    for pattern in ('icon-*.png', 'favicon.ico'):
        for path in out.glob(pattern):
            try:
                path.unlink()
            except OSError:
                pass
