"""Write a .webp copy of every screenshot in assets/originals/ to assets/compressed/.

The README shows the compressed copies; the PNGs stay as the full-quality
originals. At quality 90 the copies are about a ninth of the size, and text and
progress-bar edges stay crisp even zoomed in (quality 85 starts to soften them).

Needs Pillow (pip install Pillow).
Run:  python tools/make_webp.py
"""
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ORIGINALS = ASSETS / "originals"
COMPRESSED = ASSETS / "compressed"
QUALITY = 90


def main():
    COMPRESSED.mkdir(exist_ok=True)
    for png in sorted(ORIGINALS.glob("*.png")):
        webp = COMPRESSED / f"{png.stem}.webp"
        with Image.open(png) as im:
            img = im if im.mode in ("RGB", "RGBA") else im.convert("RGBA")
            img.save(webp, "WEBP", quality=QUALITY, method=6)
        print(f"{png.name}: {png.stat().st_size // 1024} KiB -> {webp.name}: {webp.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()
