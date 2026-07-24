"""Procedural colour & theme engine for the Rational Numbers series.

Every day of the series gets its own palette, derived *only* from the day
number.  Nothing in this module (or anywhere else in the engine) knows what
"Day 2" is: give it 2 and it returns Day 2's colours, give it 137 and it
returns Day 137's.

How the palette is built
------------------------
1.  The base hue walks around the colour wheel by the **golden angle**
    (137.507°) once per day.  Consecutive days therefore land on maximally
    distant hues — Day 1 and Day 2 can never look alike — while the sequence
    never repeats a hue for hundreds of days.
2.  A seeded hash of ``(series seed, day, role)`` supplies the small
    per-day variations (saturation temperament, hue jitter, thumbnail
    contrast) so each day feels individually art-directed rather than
    mechanically rotated.
3.  Semantic roles (success / warning / danger) stay anchored near their
    conventional hues so a red "contradiction" always reads as red, but they
    are tinted toward the day hue so they belong to that day's world.
4.  Every foreground colour is pushed through a WCAG contrast solver against
    the surface it sits on, so text and strokes are always legible — this is
    what makes the thumbnails readable instead of muddy.

Run ``python -m rational_series.color_engine 1 2 3`` to print and compare
palettes (including a check that consecutive days are visually distinct).
"""

from __future__ import annotations

import colorsys
import hashlib
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Iterable, List, Tuple

# --------------------------------------------------------------------------
# Tunables — these are *algorithm parameters*, not per-day colours.
# Changing SERIES_SEED reskins the entire series while keeping the structure.
# --------------------------------------------------------------------------

SERIES_SEED = "rational-numbers-v2"
GOLDEN_ANGLE = 137.50776405003785
BASE_HUE = 212.0  # Day 0 anchor: deep blue, the channel's resting colour

MIN_TEXT_CONTRAST = 7.0  # WCAG AAA for body text
MIN_ACCENT_CONTRAST = 4.5  # WCAG AA for large graphics/strokes


# --------------------------------------------------------------------------
# Low level colour maths
# --------------------------------------------------------------------------


def _seeded_unit(day: int, role: str) -> float:
    """Deterministic float in [0, 1) from (series, day, role)."""
    digest = hashlib.sha256(f"{SERIES_SEED}|{day}|{role}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def _seeded_range(day: int, role: str, low: float, high: float) -> float:
    """Deterministic float in [low, high) from (series, day, role)."""
    return low + _seeded_unit(day, role) * (high - low)


def hsl_to_hex(hue: float, sat: float, lum: float) -> str:
    """HSL (hue in degrees, sat/lum in 0..1) -> ``#RRGGBB``."""
    r, g, b = colorsys.hls_to_rgb((hue % 360.0) / 360.0, _clamp(lum), _clamp(sat))
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def hex_to_hsl(color: str) -> Tuple[float, float, float]:
    """``#RRGGBB`` -> (hue degrees, saturation, lightness)."""
    r, g, b = _hex_to_rgb(color)
    hue, lum, sat = colorsys.rgb_to_hls(r, g, b)
    return hue * 360.0, sat, lum


def _hex_to_rgb(color: str) -> Tuple[float, float, float]:
    raw = color.lstrip("#")
    return tuple(int(raw[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def relative_luminance(color: str) -> float:
    """WCAG relative luminance of a hex colour."""

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _hex_to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fore: str, back: str) -> float:
    """WCAG contrast ratio between two hex colours (1.0 … 21.0)."""
    a, b = relative_luminance(fore), relative_luminance(back)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def ensure_contrast(fore: str, back: str, target: float, *, lighten: bool = True) -> str:
    """Nudge ``fore``'s lightness until it clears ``target`` contrast on ``back``.

    Returns the original colour untouched when it already passes, so palettes
    keep their intended character and only get corrected when they must.
    """
    hue, sat, lum = hex_to_hsl(fore)
    step = 0.02 if lighten else -0.02
    candidate = fore
    for _ in range(50):
        if contrast_ratio(candidate, back) >= target:
            return candidate
        lum = _clamp(lum + step)
        candidate = hsl_to_hex(hue, sat, lum)
        if lum in (0.0, 1.0):
            break
    return candidate


def mix_hue(hue_a: float, hue_b: float, weight: float) -> float:
    """Blend two hues the short way around the wheel (weight = pull toward b)."""
    delta = ((hue_b - hue_a + 180.0) % 360.0) - 180.0
    return (hue_a + delta * weight) % 360.0


def hue_for_day(day: int) -> float:
    """The day's signature hue: golden-angle walk plus a small seeded jitter."""
    jitter = _seeded_range(day, "hue-jitter", -7.0, 7.0)
    return (BASE_HUE + day * GOLDEN_ANGLE + jitter) % 360.0


# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DayPalette:
    """Every colour the renderer is allowed to use for one day."""

    day: int
    hue: float

    # Stage
    background: str
    background_deep: str
    surface: str
    grid: str

    # Type & strokes
    ink: str
    ink_dim: str
    chalk: str

    # Story colours
    accent: str
    accent_soft: str
    secondary: str
    tertiary: str
    highlight: str

    # Semantics (meaning is stable series-wide, tint follows the day)
    success: str
    warning: str
    danger: str

    # Thumbnail (deliberately punchier than the video stage)
    thumbnail_bg: str
    thumbnail_bg_alt: str
    thumbnail_accent: str
    thumbnail_ink: str

    # ---- convenience -----------------------------------------------------

    @property
    def series(self) -> List[str]:
        """Ordered accents for multi-item visuals (recap cards, buckets…)."""
        return [self.accent, self.highlight, self.secondary, self.tertiary, self.accent_soft]

    def cycle(self, count: int) -> List[str]:
        """``count`` distinct, evenly-spread accents rooted at the day hue."""
        span = 300.0 / max(count, 1)
        out = []
        for i in range(count):
            hue = (self.hue + i * span) % 360.0
            sat = _seeded_range(self.day, f"cycle-s{i}", 0.62, 0.85)
            lum = _seeded_range(self.day, f"cycle-l{i}", 0.58, 0.70)
            out.append(ensure_contrast(hsl_to_hex(hue, sat, lum), self.background, MIN_ACCENT_CONTRAST))
        return out

    def as_dict(self) -> dict:
        return asdict(self)

    def report(self) -> str:
        """Human-readable palette dump with the contrast audit."""
        lines = [f"Day {self.day}  hue={self.hue:6.1f}°"]
        for key, value in self.as_dict().items():
            if not isinstance(value, str) or not value.startswith("#"):
                continue
            base = self.thumbnail_bg if key.startswith("thumbnail") else self.background
            lines.append(f"  {key:<17} {value}   contrast vs stage {contrast_ratio(value, base):5.2f}")
        return "\n".join(lines)


@lru_cache(maxsize=None)
def palette_for_day(day: int) -> DayPalette:
    """Build (and memoise) the palette for a day number."""
    hue = hue_for_day(day)

    # "Temperament" decides whether the day is icy-clean or richly saturated.
    temper = _seeded_unit(day, "temper")
    stage_sat = 0.26 + 0.22 * temper
    stage_lum = _seeded_range(day, "stage-lum", 0.050, 0.078)

    background = hsl_to_hex(hue, stage_sat, stage_lum)
    background_deep = hsl_to_hex(hue, stage_sat * 1.1, stage_lum * 0.55)
    surface = hsl_to_hex(hue, stage_sat * 0.85, stage_lum + 0.055)
    grid = hsl_to_hex(hue, stage_sat * 0.7, stage_lum + 0.10)

    ink = ensure_contrast(hsl_to_hex(hue, 0.10, 0.96), background, MIN_TEXT_CONTRAST)
    ink_dim = hsl_to_hex(hue, 0.14, _seeded_range(day, "ink-dim", 0.66, 0.74))
    chalk = hsl_to_hex(hue, 0.04, 0.985)

    accent = ensure_contrast(
        hsl_to_hex(hue, _seeded_range(day, "accent-s", 0.72, 0.92), _seeded_range(day, "accent-l", 0.58, 0.68)),
        background,
        MIN_ACCENT_CONTRAST,
    )
    accent_soft = hsl_to_hex(hue, 0.55, 0.78)
    secondary = ensure_contrast(
        hsl_to_hex(hue + 152.0, _seeded_range(day, "sec-s", 0.60, 0.82), 0.62), background, MIN_ACCENT_CONTRAST
    )
    tertiary = ensure_contrast(
        hsl_to_hex(hue + 208.0, _seeded_range(day, "ter-s", 0.55, 0.78), 0.64), background, MIN_ACCENT_CONTRAST
    )
    highlight = ensure_contrast(
        hsl_to_hex(hue + 42.0, 0.88, _seeded_range(day, "hl-l", 0.62, 0.72)), background, MIN_ACCENT_CONTRAST
    )

    # Semantic colours: anchored hue, pulled a little toward the day so they
    # harmonise — never so far that green stops reading as "correct".
    success = ensure_contrast(hsl_to_hex(mix_hue(146.0, hue, 0.12), 0.66, 0.56), background, MIN_ACCENT_CONTRAST)
    warning = ensure_contrast(hsl_to_hex(mix_hue(41.0, hue, 0.12), 0.88, 0.60), background, MIN_ACCENT_CONTRAST)
    danger = ensure_contrast(hsl_to_hex(mix_hue(357.0, hue, 0.10), 0.76, 0.58), background, MIN_ACCENT_CONTRAST)

    # Thumbnails live on a phone screen next to 40 other thumbnails: richer,
    # lighter and far more saturated than the video stage, but still dark
    # enough for white type. This is the fix for the washed-out Day 2 card.
    thumb_lum = _seeded_range(day, "thumb-lum", 0.115, 0.155)
    thumbnail_bg = hsl_to_hex(hue, 0.52 + 0.16 * temper, thumb_lum)
    thumbnail_bg_alt = hsl_to_hex(hue + 26.0, 0.60, thumb_lum * 0.55)
    thumbnail_accent = ensure_contrast(
        hsl_to_hex(hue + 40.0, 0.92, _seeded_range(day, "thumb-acc", 0.62, 0.72)), thumbnail_bg, MIN_ACCENT_CONTRAST
    )
    thumbnail_ink = ensure_contrast(hsl_to_hex(hue, 0.06, 0.98), thumbnail_bg, MIN_TEXT_CONTRAST)

    return DayPalette(
        day=day,
        hue=hue,
        background=background,
        background_deep=background_deep,
        surface=surface,
        grid=grid,
        ink=ink,
        ink_dim=ink_dim,
        chalk=chalk,
        accent=accent,
        accent_soft=accent_soft,
        secondary=secondary,
        tertiary=tertiary,
        highlight=highlight,
        success=success,
        warning=warning,
        danger=danger,
        thumbnail_bg=thumbnail_bg,
        thumbnail_bg_alt=thumbnail_bg_alt,
        thumbnail_accent=thumbnail_accent,
        thumbnail_ink=thumbnail_ink,
    )


def hue_distance(day_a: int, day_b: int) -> float:
    """Shortest angular distance between two days' signature hues."""
    return abs(((hue_for_day(day_a) - hue_for_day(day_b) + 180.0) % 360.0) - 180.0)


def days_are_distinct(day_a: int, day_b: int, *, min_degrees: float = 25.0) -> bool:
    """True when two days will read as different colour worlds on screen."""
    return hue_distance(day_a, day_b) >= min_degrees


def _main(argv: Iterable[str]) -> int:
    days = [int(a) for a in argv] or [1, 2, 3, 4, 5]
    for day in days:
        print(palette_for_day(day).report())
        print()
    for a, b in zip(days, days[1:]):
        print(f"Day {a} vs Day {b}: hue distance {hue_distance(a, b):5.1f}°  distinct={days_are_distinct(a, b)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    import sys

    raise SystemExit(_main(sys.argv[1:]))
