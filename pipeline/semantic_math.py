"""Single-source semantic mathematics typography for every Manim lesson stage.

No per-lesson variables, numeric literals or operator colors are hardcoded.
Pure tokenization/markup routines work without Manim and are safe for
user-authored mathematical text (XML escaping).  The actual rendering
dependency is imported lazily.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from html import escape
from types import MappingProxyType
from typing import Literal

from pipeline.mathtext import latex_to_plain

MathMode = Literal["auto", "math", "prose"]

# High-contrast colors on the existing dark navy stage background.
# Every scene, role and future Remotion bridge uses this one palette.
MATH_PALETTE = MappingProxyType({
    "variable": "#38BDF8",    # clear cyan
    "number": "#FDE68A",      # light golden numeric constants
    "operator": "#FB923C",    # orange +, −, ×, ÷, /
    "relation": "#4ADE80",    # equals and comparison signs
    "exponent": "#D8B4FE",    # powers/superscripts, visually distinct
    "group": "#CBD5E1",       # parentheses and grouping marks
    "function": "#F9A8D4",    # sin, cos, log, sqrt, ...
    "text": "#E5E7EB",        # plain words/unclassified glyphs
})

_FUNCTIONS = frozenset({
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos",
    "arctan", "log", "ln", "lim", "exp", "sqrt", "min", "max",
})
# Parse complete words before symbols; superscripts precede numbers.
_TOKEN = re.compile(
    r"(?P<space>\s+)"
    r"|(?P<exponent>\^(?:\{[^{}]{1,32}\}|[-+]?\d+|[A-Za-z])|[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)"
    r"|(?P<number>\d+(?:\.\d+)?)"
    r"|(?P<word>[^\W\d_]+(?:_[A-Za-z0-9]+)?)"
    r"|(?P<relation>[=≠≤≥≈≡<>∝⇔→])"
    r"|(?P<operator>[+\-−±×÷*/·])"
    r"|(?P<group>[()\[\]{}])"
    r"|(?P<text>.)",
    flags=re.UNICODE | re.DOTALL,
)

# Deliberately do not interpret narrative hyphens, grade numbers, dates,
# 'DAY 43', or punctuation as math.
_MATH_OPERATOR = re.compile(
    r"(?:\d\s*[+\-−×÷*/^]\s*(?:\d|[A-Za-z(]))"
    r"|(?:\b[A-Za-z]\s*[+\-−×÷*/^]\s*(?:\d|\b[A-Za-z]\b|\())"
)
_COEFFICIENT = re.compile(r"\d\s*[A-Za-z](?![A-Za-z])")
_POWER = re.compile(r"(?:[A-Za-z0-9\)])(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]|\^\{?\d)")
_RELATION = re.compile(r"[=≠≤≥≈≡<>∝⇔]")


@dataclass(frozen=True)
class MathSpan:
    text: str
    role: str
    start: int
    end: int


def is_mathematical(value: object) -> bool:
    """Detect meaningful expressions, leaving ordinary titles/prose intact."""
    s = latex_to_plain(value)
    return bool(
        _RELATION.search(s) or _MATH_OPERATOR.search(s)
        or _COEFFICIENT.search(s) or _POWER.search(s)
    )


def tokenize_math(value: object, *, mode: MathMode = "auto") -> list[MathSpan]:
    """Tokenize by role while preserving every original display character."""
    if mode not in {"auto", "math", "prose"}:
        raise ValueError(f"invalid semantic math mode: {mode!r}")
    s = latex_to_plain(value)
    active = mode == "math" or (mode == "auto" and is_mathematical(s))
    spans: list[MathSpan] = []
    for match in _TOKEN.finditer(s):
        kind = match.lastgroup or "text"
        value = match.group()
        role = "text"
        if active:
            if kind == "word":
                if value.casefold() in _FUNCTIONS:
                    role = "function"
                elif len(value) == 1 or (
                    "_" in value and len(value.split("_", 1)[0]) == 1
                ):
                    role = "variable"
            elif kind in {"number", "operator", "relation", "exponent", "group"}:
                role = kind
        spans.append(MathSpan(value, role, match.start(), match.end()))
    if "".join(v.text for v in spans) != s:
        raise ValueError("semantic tokenizer altered mathematical content")
    return spans


def markup_for_math(
    value: object, *, mode: MathMode = "auto", base_color: str | None = None,
    palette: dict | None = None,
) -> str:
    """Safe Pango markup: classify syntax rather than replace specific symbols.

    Neutral prose inherits its caller's text color; math roles use the shared
    high-contrast palette, including when surrounded by explanation text.
    """
    colors = dict(MATH_PALETTE)
    if palette:
        for role, color in palette.items():
            if role not in colors or not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(color)):
                raise ValueError(f"invalid semantic role color for {role}")
            colors[role] = color
    neutral = base_color or colors["text"]
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", neutral):
        raise ValueError("base semantic text color must be six-digit hex")
    output = []
    for span in tokenize_math(value, mode=mode):
        fg = neutral if span.role == "text" else colors[span.role]
        # Escaping also covers bare '<' and '>' comparisons and user input.
        output.append(f'<span foreground="{fg}">{escape(span.text)}</span>')
    return "".join(output) or f'<span foreground="{neutral}"> </span>'


def semantic_text(
    value: object, *, size: float = 28, base_color: str = "#E5E7EB",
    mode: MathMode = "auto", bold: bool = False, max_width: float | None = None,
    max_height: float | None = None, wrap: int | None = None,
    font: str = "DejaVu Sans", line_spacing: float = 0.95,
):
    """Manim Text/MarkupText factory; no silence-to-monochrome fallback.

    All math uses the same token palette; non-math prose retains its provided
    scene color.  Bounds are preserved after semantic markup is applied.
    """
    from manim import MarkupText, Text
    s = latex_to_plain(value) or " "
    if wrap:
        s = "\n".join(textwrap.wrap(s, wrap, break_long_words=False)) or " "
    colors = dict(MATH_PALETTE)
    if mode == "math" or (mode == "auto" and is_mathematical(s)):
        result = MarkupText(
            markup_for_math(s, mode="math", base_color=base_color),
            font=font, font_size=size, weight="BOLD" if bold else "NORMAL",
            line_spacing=line_spacing,
        )
    else:
        result = Text(
            s, font=font, font_size=size, color=base_color,
            weight="BOLD" if bold else "NORMAL", line_spacing=line_spacing,
        )
    if max_width and result.width > max_width:
        result.scale_to_fit_width(max_width)
    if max_height and result.height > max_height:
        result.scale_to_fit_height(max_height)
    return result
