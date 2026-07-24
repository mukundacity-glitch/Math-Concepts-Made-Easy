"""Thumbnail generator — the day's palette, rendered at 1280x720.

The old thumbnails failed for one reason: the background colour was fixed
and the type sat on top of it with almost no contrast.  Here the card is
built from :mod:`rational_series.color_engine`, which guarantees

* a different, saturated background hue for every day,
* a headline that always clears WCAG AAA contrast on that background,
* an accent that always clears AA,

so the card is legible at phone size no matter which day is rendered.
Rendered at 4x and downsampled for clean edges.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional, Tuple

from rational_series.color_engine import DayPalette, palette_for_day
from rational_series.intro_generator import generate_intro
from rational_series.script_parser import DayScript

WIDTH, HEIGHT = 1280, 720
SUPERSAMPLE = 4

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
    "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)


def _load_font(size: int):
    from PIL import ImageFont

    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
    raw = color.lstrip("#")
    return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _gradient(size: Tuple[int, int], top: str, bottom: str, angle: float = 0.35):
    """Diagonal two-stop gradient, drawn per row/column mix."""
    from PIL import Image

    width, height = size
    base = Image.new("RGB", size)
    r0, g0, b0 = _hex_to_rgb(top)
    r1, g1, b1 = _hex_to_rgb(bottom)
    pixels = base.load()
    for y in range(height):
        for x in range(0, width, 4):  # 4px columns: fast and invisible after blur
            t = min(1.0, max(0.0, (x / width) * angle + (y / height) * (1 - angle)))
            colour = (
                int(r0 + (r1 - r0) * t),
                int(g0 + (g1 - g0) * t),
                int(b0 + (b1 - b0) * t),
            )
            for dx in range(4):
                if x + dx < width:
                    pixels[x + dx, y] = colour
    return base


def _draw_motif(draw, palette: DayPalette, motif: str, size: Tuple[int, int], seed: int) -> None:
    """Faint geometry on the right-hand third, matching the day's intro."""
    width, height = size
    accent = _hex_to_rgb(palette.thumbnail_accent)
    faint = accent + (72,)
    cx, cy = int(width * 0.76), int(height * 0.52)

    if motif in ("lattice", "tiling", "square"):
        for i in range(7):
            half = int(width * 0.05 * (i + 1))
            draw.rectangle([cx - half, cy - half, cx + half, cy + half], outline=faint, width=max(2, 8 - i))
        draw.line([cx - int(width * 0.35), cy + int(width * 0.35), cx + int(width * 0.35), cy - int(width * 0.35)],
                  fill=accent + (165,), width=10)
    elif motif in ("orbit", "radial"):
        for i in range(9):
            radius = int(width * 0.045 * (i + 1))
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=faint, width=max(2, 7 - i))
    elif motif in ("spiral",):
        for i in range(220):
            angle = i * 2.39996323
            radius = 9.0 * math.sqrt(i) * (width / 1280) * 4
            x, y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
            r = 3 + i * 0.02
            draw.ellipse([x - r, y - r, x + r, y + r], fill=accent + (90,))
    else:  # waveform / line
        for i in range(6):
            points = []
            for k in range(0, width, 12):
                x = k
                y = cy + int(math.sin(k / (90.0 + i * 24) + i) * (26 + i * 8)) + (i - 3) * 52
                points.append((x, y))
            draw.line(points, fill=faint, width=5, joint="curve")


def _fit_text(draw, text: str, font_loader, max_width: int, start_size: int) -> Tuple[object, int]:
    """Largest font size at which ``text`` fits inside ``max_width``."""
    size = start_size
    while size > 18:
        font = font_loader(size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font, size
        size -= 4
    return font_loader(18), 18


def render_thumbnail(
    day: int,
    out_path: Path,
    *,
    headline: str,
    headline_2: str = "",
    kicker: str = "",
    motif: Optional[str] = None,
    palette: Optional[DayPalette] = None,
) -> Path:
    """Draw the day's thumbnail card to ``out_path`` (PNG, 1280x720)."""
    from PIL import Image, ImageDraw, ImageFilter

    palette = palette or palette_for_day(day)
    motif = motif or generate_intro(day).motif
    scale = SUPERSAMPLE
    size = (WIDTH * scale, HEIGHT * scale)

    base = _gradient((WIDTH, HEIGHT), palette.thumbnail_bg, palette.thumbnail_bg_alt)
    base = base.resize(size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=scale * 2))

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_motif(draw, palette, motif, size, day)

    # Left-hand type column with a soft scrim so text always wins.
    scrim = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(scrim).rectangle([0, 0, int(size[0] * 0.66), size[1]], fill=_hex_to_rgb(palette.thumbnail_bg) + (170,))
    overlay = Image.alpha_composite(overlay, scrim.filter(ImageFilter.GaussianBlur(radius=scale * 26)))

    card = Image.alpha_composite(base.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(card)

    margin = int(88 * scale)
    text_width = int(size[0] * 0.58)
    cursor = int(150 * scale)

    # Day badge
    badge_font = _load_font(int(34 * scale))
    badge_text = f"DAY {day:02d}"
    badge_box = draw.textbbox((0, 0), badge_text, font=badge_font)
    pad = int(18 * scale)
    draw.rounded_rectangle(
        [margin, cursor, margin + (badge_box[2] - badge_box[0]) + pad * 2, cursor + (badge_box[3] - badge_box[1]) + pad * 2],
        radius=int(10 * scale),
        fill=_hex_to_rgb(palette.thumbnail_accent),
    )
    draw.text((margin + pad, cursor + pad - badge_box[1]), badge_text, font=badge_font, fill=_hex_to_rgb(palette.thumbnail_bg))
    cursor += (badge_box[3] - badge_box[1]) + pad * 2 + int(38 * scale)

    # Headline (up to two lines, auto-fitted)
    for line in [headline, headline_2]:
        if not line:
            continue
        font, _ = _fit_text(draw, line, _load_font, text_width, int(112 * scale))
        box = draw.textbbox((0, 0), line, font=font)
        draw.text((margin, cursor - box[1]), line, font=font, fill=_hex_to_rgb(palette.thumbnail_ink))
        cursor += (box[3] - box[1]) + int(26 * scale)

    # Accent rule + kicker
    cursor += int(18 * scale)
    draw.rounded_rectangle(
        [margin, cursor, margin + int(220 * scale), cursor + int(10 * scale)],
        radius=int(5 * scale),
        fill=_hex_to_rgb(palette.thumbnail_accent),
    )
    if kicker:
        cursor += int(44 * scale)
        kicker_font = _load_font(int(38 * scale))
        draw.text((margin, cursor), kicker, font=kicker_font, fill=_hex_to_rgb(palette.thumbnail_accent))

    # Channel strip
    strip_font = _load_font(int(28 * scale))
    draw.text(
        (margin, size[1] - int(78 * scale)),
        "MATH CONCEPTS MADE EASY",
        font=strip_font,
        fill=_hex_to_rgb(palette.thumbnail_ink),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    card.convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS).save(out_path, "PNG", optimize=True)
    return out_path


def render_for_script(script: DayScript, out_path: Path) -> Path:
    """Build the thumbnail from a day script's ``thumbnail`` block."""
    spec = script.thumbnail or {}
    headline = str(spec.get("headline") or script.title.upper())
    return render_thumbnail(
        script.day,
        out_path,
        headline=headline,
        headline_2=str(spec.get("headline_2", "")),
        kicker=str(spec.get("kicker") or script.subtitle.upper()),
        motif=spec.get("motif"),
    )


__all__ = ["render_for_script", "render_thumbnail"]
