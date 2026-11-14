"""Write a .webp copy of every PNG screenshot in showcase/ for the README.

The PNGs stay as the full-quality originals. At quality 90 the copies are about
a ninth of the size, and text and progress-bar edges stay crisp even zoomed in
(quality 85 starts to soften them).

Needs Pillow (pip install Pillow).
Run:  python tools/make_webp.py
"""
from pathlib import Path

from PIL import Image

SHOWCASE = Path(__file__).resolve().parent.parent / "showcase"
QUALITY = 90


def main():
    for png in sorted(SHOWCASE.glob("*.png")):
        webp = png.with_suffix(".webp")
        with Image.open(png) as im:
            img = im if im.mode in ("RGB", "RGBA") else im.convert("RGBA")
            img.save(webp, "WEBP", quality=QUALITY, method=6)
        print(f"{png.name}: {png.stat().st_size // 1024} KiB -> {webp.name}: {webp.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()
