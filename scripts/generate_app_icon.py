"""Generate IVO app icons (PNG/ICO/ICNS) from a programmatic design.

Usage:
    uv run --with pillow python scripts/generate_app_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
SIZE = 1024

# Palette
BG_TOP = (15, 23, 42)       # slate-900
BG_BOTTOM = (30, 27, 75)    # indigo-950
RING = (99, 102, 241)       # indigo-500
ACCENT_1 = (34, 211, 238)   # cyan-400
ACCENT_2 = (167, 139, 250)  # violet-400
WHITE = (255, 255, 255)


def linear_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Create a vertical linear gradient image."""
    img = Image.new("RGB", (size, size))
    for y in range(size):
        ratio = y / (size - 1)
        r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
        g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
        b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
        img.paste((r, g, b), (0, y, size, y + 1))
    return img


def rounded_rectangle_mask(size: int, radius: int) -> Image.Image:
    """Create an alpha mask for a rounded rectangle."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def draw_icon() -> Image.Image:
    """Draw the IVO app icon at 1024x1024."""
    img = linear_gradient(SIZE, BG_TOP, BG_BOTTOM)

    # Add subtle rounded-corner clipping mask
    mask = rounded_rectangle_mask(SIZE, SIZE // 6)
    rgba = img.convert("RGBA")
    rgba.putalpha(mask)

    draw = ImageDraw.Draw(rgba)
    cx, cy = SIZE // 2, SIZE // 2

    # Outer ring
    ring_outer = SIZE * 0.38
    draw.ellipse(
        (cx - ring_outer, cy - ring_outer, cx + ring_outer, cy + ring_outer),
        outline=RING,
        width=SIZE // 60,
    )

    # Sound wave bars
    bar_count = 5
    bar_width = SIZE * 0.045
    max_height = SIZE * 0.22
    gap = SIZE * 0.035
    total_width = bar_count * bar_width + (bar_count - 1) * gap
    start_x = cx - total_width / 2 + bar_width / 2
    heights = [max_height * 0.45, max_height * 0.75, max_height, max_height * 0.75, max_height * 0.45]
    for i, h in enumerate(heights):
        x = start_x + i * (bar_width + gap)
        top = cy - h / 2
        bottom = cy + h / 2
        draw.rounded_rectangle(
            (x - bar_width / 2, top, x + bar_width / 2, bottom),
            radius=int(bar_width / 2),
            fill=ACCENT_1,
        )

    # Play triangle overlay at the bottom right
    tri_size = SIZE * 0.14
    tri_margin = SIZE * 0.08
    tx = SIZE - tri_margin - tri_size
    ty = SIZE - tri_margin - tri_size
    triangle = [
        (tx, ty),
        (tx, ty + tri_size),
        (tx + tri_size * 0.866, ty + tri_size / 2),
    ]
    draw.polygon(triangle, fill=ACCENT_2)

    # Top-left sparkle dot
    spark_r = SIZE * 0.025
    draw.ellipse(
        (SIZE * 0.18 - spark_r, SIZE * 0.18 - spark_r,
         SIZE * 0.18 + spark_r, SIZE * 0.18 + spark_r),
        fill=WHITE,
    )

    return rgba


def save_png(img: Image.Image) -> Path:
    path = BUILD_DIR / "icon.png"
    img.save(path, "PNG")
    return path


def save_ico(img: Image.Image) -> Path:
    path = BUILD_DIR / "icon.ico"
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(path, "ICO", sizes=sizes)
    return path


def save_icns(img: Image.Image) -> Path:
    path = BUILD_DIR / "icon.icns"
    # Pillow ICNS writer needs a source image and will create the iconset
    img.save(path, "ICNS")
    return path


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    icon = draw_icon()
    png_path = save_png(icon)
    ico_path = save_ico(icon)
    icns_path = save_icns(icon)
    print(f"Generated icons:\n  {png_path}\n  {ico_path}\n  {icns_path}")


if __name__ == "__main__":
    main()
