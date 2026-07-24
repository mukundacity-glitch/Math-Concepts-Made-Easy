"""Rational Numbers video series — a data-driven Manim production engine.

Adding a day to the series requires exactly two things: a script file in
``rational_series/scripts/`` and its day number.  Every other property of
the video — palette, intro, motifs, pacing, thumbnail — is derived from that
number and that file.

    from rational_series import load_day, palette_for_day

    script  = load_day(2)                # rational_series/scripts/day2.json
    palette = palette_for_day(2)         # Day 2's colour world

    from rational_series.intro_generator import generate_intro   # needs manim
    intro = generate_intro(2)            # Day 2's opening sequence

The Manim-dependent parts (scene, visual library, intro playback) are
imported lazily so the data layer can be used — and tested — without a
Manim installation.
"""

from __future__ import annotations

from rational_series.color_engine import (
    DayPalette,
    contrast_ratio,
    days_are_distinct,
    hue_for_day,
    palette_for_day,
)
from rational_series.script_parser import (
    DayScript,
    NarrationBlock,
    ScriptError,
    available_days,
    estimate_duration,
    infer_concept,
    load_day,
    load_script,
    script_path_for_day,
)

__all__ = [
    "DayPalette",
    "DayScript",
    "NarrationBlock",
    "ScriptError",
    "available_days",
    "contrast_ratio",
    "days_are_distinct",
    "estimate_duration",
    "hue_for_day",
    "infer_concept",
    "load_day",
    "load_script",
    "palette_for_day",
    "script_path_for_day",
]

__version__ = "2.0.0"
