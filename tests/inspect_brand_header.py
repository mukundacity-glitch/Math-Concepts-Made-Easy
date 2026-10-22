"""Fail CI if the real Manim frame has no original logo in its header."""
from pathlib import Path
import sys
from PIL import Image


def main(path: Path):
    image = Image.open(path).convert("RGB")
    width, height = image.size
    # The canonical production header's ImageMobject is centered at
    # x=-6.35, y=3.57 on Manim's 14.222 x 8.0 scene coordinate system.
    # Inspect the emblem itself, not the yellow bottom border of the header.
    sx = width / 14.222
    sy = height / 8.0
    cx = round((7.111 - 6.35) * sx)
    cy = round((4.0 - 3.57) * sy)
    half = max(8, round(0.63 * sy / 2))
    x0, x1 = max(0, cx-half), min(width, cx+half)
    y0, y1 = max(0, cy-half), min(height, cy+half)
    crop = image.crop((x0, y0, x1, y1))
    gold = 0
    white = 0
    for r,g,b in crop.getdata():
        if r > 150 and g > 95 and b < 145 and r > b * 1.4:
            gold += 1
        if r > 180 and g > 180 and b > 175:
            white += 1
    if gold < 20 or white < 20:
        raise SystemExit(
            f"Brand logo missing from real Manim slide (gold={gold}, white={white})"
        )
    print(f"Verified stored logo at top left: gold={gold}, white={white}; {width}x{height}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
