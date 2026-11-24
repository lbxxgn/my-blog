"""图片上传的统一校验与落盘。

后台编辑、移动端、知识库三个上传入口原先各自复制了一份「扩展名白名单 → PIL
深度校验 → HEIC 转 JPEG → 尺寸上限 → 时间戳命名」的流程，规则已经出现漂移。
这里收敛为单一实现，视图只负责鉴权与响应格式。

用法::

    try:
        stored = store_image_upload(request.files.get('file'))
    except ImageUploadError as exc:
        return jsonify({'success': False, 'error': str(exc)}), exc.status

    stored.url        # /static/uploads/images/20260101-120000-ab12cd34.jpg
    stored.path       # 绝对路径 Path
    stored.filename
"""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.config import ALLOWED_EXTENSIONS, MAX_IMAGE_BYTES, MAX_IMAGE_DIMENSION, UPLOAD_FOLDER

__all__ = [
    'ImageUploadError',
    'StoredImage',
    'is_allowed_image_filename',
    'read_image_upload',
    'save_original_image',
    'store_image_upload',
]

# Pillow 识别出的格式（小写）白名单
ALLOWED_PIL_TYPES = frozenset({
    'jpeg', 'jpg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'mpo', 'heic', 'heif',
})

# 需要重新编码为 JPEG 的格式（Pillow 不一定能直接写回原格式）
REENCODE_TO_JPEG = frozenset({'mpo', 'heic', 'heif'})


class ImageUploadError(ValueError):
    """上传校验失败；``code`` 供各入口映射为不同的提示文案。"""

    def __init__(self, message, code='invalid', status=400):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class StoredImage:
    path: Path
    filename: str
    url: str


def is_allowed_image_filename(filename):
    """按扩展名做第一道白名单校验。"""
    return bool(filename) and '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _extension_of(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'


def read_image_upload(upload):
    """读取并校验上传的图片，返回 (字节内容, 落盘扩展名)。

    Pillow 缺失时退化为扩展名校验（与历史行为一致）；文件损坏或类型不在白名单
    则抛 ``ImageUploadError``。
    """
    if upload is None:
        raise ImageUploadError('没有文件上传', code='missing_file')
    if not upload.filename:
        raise ImageUploadError('未选择文件', code='empty_filename')
    if not is_allowed_image_filename(upload.filename):
        raise ImageUploadError('不支持的文件类型', code='unsupported_type')

    content = upload.read()

    if len(content) > MAX_IMAGE_BYTES:
        limit_mb = MAX_IMAGE_BYTES // 1024 // 1024
        raise ImageUploadError(f'文件大小超过限制（最大{limit_mb}MB）', code='too_large')

    try:
        from PIL import Image
        import io

        with Image.open(io.BytesIO(content)) as img:
            detected_type = (img.format or '').lower() or None
            if detected_type not in ALLOWED_PIL_TYPES:
                raise ImageUploadError(
                    f'无效的图片文件类型: {detected_type}', code='invalid_type')

            width, height = img.size
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise ImageUploadError(
                    f'图片尺寸过大，最大允许{MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}',
                    code='too_large_dimensions')

            if detected_type in REENCODE_TO_JPEG:
                if img.mode not in ('RGB',):
                    img = img.convert('RGB')
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                return buffer.getvalue(), 'jpg'

            return content, 'jpg' if detected_type == 'jpeg' else detected_type
    except ImageUploadError:
        raise
    except ImportError:
        # 无 Pillow：仅按扩展名放行，交由后续使用方保底处理
        return content, _extension_of(upload.filename)
    except Exception as exc:
        raise ImageUploadError('图片文件损坏或格式错误', code='corrupt') from exc


def save_original_image(content, file_type='png', images_dir=None):
    """把原图写入 uploads/images，返回 ``StoredImage``。

    文件名使用「时间戳-随机串」，并用连字符而非下划线：下划线在 Markdown 纯文本
    中会被解析成斜体，破坏 URL。
    """
    images_dir = Path(images_dir) if images_dir else Path(UPLOAD_FOLDER) / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    base_filename = f"{timestamp}-{os.urandom(4).hex()}"
    path = images_dir / f"{base_filename}.{file_type or 'png'}"

    try:
        with open(path, 'wb') as fh:
            fh.write(content)
    except OSError as exc:
        raise ImageUploadError(f'文件保存失败: {exc}', code='save_failed', status=500) from exc

    return StoredImage(
        path=path,
        filename=path.name,
        url=f'/static/uploads/images/{path.name}',
    )


def store_image_upload(upload, images_dir=None):
    """校验并保存上传图片，返回 ``StoredImage``。"""
    content, file_type = read_image_upload(upload)
    return save_original_image(content, file_type, images_dir=images_dir)
