"""Compatibility helpers for legacy image-processing imports used in tests."""

from io import BytesIO
import re

from PIL import Image

from backend.image_processor import *  # noqa: F401,F403
from backend.image_processor import optimize_image as optimize_image_file


def process_image(image_data, max_size=(800, 600)):
    """Open raw image bytes and resize them in memory."""
    with Image.open(BytesIO(image_data)) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img.copy()


def resize_image(image, width=0, height=0):
    """Resize an in-memory PIL image when dimensions are valid."""
    if image is None or width <= 0 or height <= 0:
        return image
    return image.resize((width, height), Image.Resampling.LANCZOS)


def optimize_image(image_data, quality=85):
    """Best-effort in-memory optimization helper for older tests."""
    if isinstance(image_data, (bytes, bytearray)):
        try:
            with Image.open(BytesIO(image_data)) as img:
                output = BytesIO()
                fmt = 'WEBP' if img.mode in ('RGB', 'RGBA') else 'PNG'
                save_kwargs = {'quality': max(0, int(quality))}
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                    fmt = 'WEBP'
                img.save(output, fmt, **save_kwargs)
                return output.getvalue()
        except Exception:
            return bytes(image_data)
    return optimize_image_file(image_data)


def extract_image_urls(content):
    """Extract image src values from HTML content."""
    if not content:
        return []
    pattern = r'<img[^>]+src=["\']?([^"\'>\s]+)'
    return re.findall(pattern, content, flags=re.IGNORECASE)
