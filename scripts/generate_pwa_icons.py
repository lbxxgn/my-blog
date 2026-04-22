#!/usr/bin/env python3
"""Generate PWA icons from the blog theme color."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

THEME_COLOR = (16, 185, 129)  # #10b981
TEXT_COLOR = (255, 255, 255)
SIZES = {
    180: 'static/icon-180.png',
    192: 'static/icon-192.png',
    512: 'static/icon-512.png',
}


def generate_icon(size: int, output_path: str) -> None:
    """Generate a circular icon with '博' character."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 20
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=THEME_COLOR
    )

    text = '博'
    font_size = int(size * 0.55)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, 'PNG')
    print(f'Generated: {output_path} ({size}x{size})')


if __name__ == '__main__':
    for size, path in SIZES.items():
        generate_icon(size, path)
    print('All icons generated.')
