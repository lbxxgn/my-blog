"""
站点图标生成工具

后台上传一张原图后，由前端拖动选框选择图片中的一块区域（正方形），
后端按选框生成 favicon、iOS 主屏图标与 PWA 图标的多尺寸 PNG。

原始上传图会保留在 static/uploads/site/source.img，便于之后重新调整选区，
无需重新上传。生成文件同样固定存放于该目录，由 app.py 的动态路由对外提供，
未上传时回退到仓库自带的默认图标。
"""

import io
import os
from pathlib import Path

from PIL import Image, ImageOps

from backend.config import UPLOAD_FOLDER

# 需要生成的 PNG 尺寸（含站点导航 logo 用到的 48）
ICON_PNG_SIZES = (16, 32, 48, 180, 192, 512)
# favicon.ico 内嵌尺寸
FAVICON_SIZES = [(16, 16), (32, 32), (48, 48)]

# 源图限制
MAX_SOURCE_BYTES = 10 * 1024 * 1024  # 10MB
MIN_SOURCE_DIMENSION = 180
# 前端选中的裁切区域最小边长（允许从大图里裁小块）
MIN_CROP_DIMENSION = 64

# 保留的原始上传图（用于再次调整选区）
SOURCE_FILENAME = 'source.img'

RESAMPLING = getattr(Image, 'Resampling', Image).LANCZOS

# PIL 格式 -> 对外响应 MIME（用于把原图返回给裁剪界面）
_MIME_BY_FORMAT = {
    'PNG': 'image/png',
    'JPEG': 'image/jpeg',
    'GIF': 'image/gif',
    'WEBP': 'image/webp',
    'BMP': 'image/bmp',
    'HEIF': 'image/heic',
    'AVIF': 'image/avif',
}


def site_icon_dir() -> Path:
    """站点图标输出目录（按需创建）。"""
    path = Path(UPLOAD_FOLDER) / 'site'
    path.mkdir(parents=True, exist_ok=True)
    return path


def source_path() -> Path:
    """保留下来的原始上传图路径。"""
    return Path(UPLOAD_FOLDER) / 'site' / SOURCE_FILENAME


def has_custom_icons() -> bool:
    """是否已上传过自定义图标。"""
    return (Path(UPLOAD_FOLDER) / 'site' / 'icon-512.png').exists()


def has_custom_source() -> bool:
    """是否保留有可重新裁剪的原始图片。"""
    return source_path().exists()


def load_source_bytes():
    """读取保留的原始图片字节；不存在时返回 None。"""
    path = source_path()
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def source_mimetype() -> str:
    """探测原始图片的 MIME 类型，供裁剪界面 <img> 使用。"""
    data = load_source_bytes()
    if not data:
        return 'application/octet-stream'
    try:
        with Image.open(io.BytesIO(data)) as img:
            return _MIME_BY_FORMAT.get(img.format or '', 'application/octet-stream')
    except Exception:  # noqa: BLE001 - 探测失败时降级
        return 'application/octet-stream'


def _open_image(file_content: bytes, min_dimension: int = 0) -> Image.Image:
    """校验并解码图片（按 EXIF 方向摆正），返回 RGB/RGBA 图像。"""
    if not file_content:
        raise ValueError('未选择文件')
    if len(file_content) > MAX_SOURCE_BYTES:
        raise ValueError(f'文件过大（最大 {MAX_SOURCE_BYTES // 1024 // 1024}MB）')

    try:
        img = Image.open(io.BytesIO(file_content))
        img.load()
    except Exception as exc:  # noqa: BLE001 - 统一转成友好提示
        raise ValueError('图片文件损坏或格式不支持') from exc

    img = ImageOps.exif_transpose(img)
    width, height = img.size
    if min_dimension and min(width, height) < min_dimension:
        raise ValueError(f'图片尺寸过小，至少需要 {min_dimension}x{min_dimension}')

    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA')
    return img


def _center_square(img: Image.Image) -> Image.Image:
    """居中裁成正方形。"""
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return img.crop((left, top, left + side, top + side))


def _write_atomic(path: Path, data: bytes) -> None:
    """先写临时文件再替换，避免生成中途失败留下残缺图标。"""
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _render_icons(square: Image.Image) -> dict:
    """把正方形原图渲染成各尺寸图标字节，返回 {文件名: 内容}。"""
    rendered = {}
    for size in ICON_PNG_SIZES:
        buf = io.BytesIO()
        square.resize((size, size), RESAMPLING).save(
            buf, format='PNG', optimize=True
        )
        rendered[f'icon-{size}.png'] = buf.getvalue()

    buf = io.BytesIO()
    square.convert('RGBA').save(buf, format='ICO', sizes=FAVICON_SIZES)
    rendered['favicon.ico'] = buf.getvalue()
    return rendered


def generate_site_icons(file_content: bytes = None, cropped_content: bytes = None) -> Path:
    """生成全部尺寸图标，返回输出目录。

    - ``file_content``：新上传的原图。会校验并保留下来供以后重新裁剪。
    - ``cropped_content``：前端裁剪出的正方形图片，优先使用它。
    - 两者都为 None 时，使用之前保留的原图并居中裁剪。
    """
    # 先校验新图，避免损坏文件覆盖掉已有的原图
    uploaded = (
        _open_image(file_content, MIN_SOURCE_DIMENSION)
        if file_content is not None else None
    )

    if cropped_content is not None:
        square = _center_square(_open_image(cropped_content, MIN_CROP_DIMENSION))
    elif uploaded is not None:
        square = _center_square(uploaded)
    else:
        saved = load_source_bytes()
        if not saved:
            raise ValueError('请选择图片文件')
        square = _center_square(_open_image(saved, MIN_SOURCE_DIMENSION))

    rendered = _render_icons(square)
    out = site_icon_dir()
    for name, data in rendered.items():
        _write_atomic(out / name, data)

    if file_content is not None:
        _write_atomic(out / SOURCE_FILENAME, file_content)
    return out


def reset_site_icons() -> None:
    """删除所有自定义图标与原始图，回退到默认图标。"""
    out = Path(UPLOAD_FOLDER) / 'site'
    if not out.exists():
        return
    for pattern in ('icon-*.png', 'favicon.ico', SOURCE_FILENAME, '*.tmp'):
        for path in out.glob(pattern):
            try:
                path.unlink()
            except OSError:
                pass
