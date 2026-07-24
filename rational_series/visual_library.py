"""Reusable visual components for the Rational Numbers series.

Everything on screen is built from the classes in this module, and every one
of them takes a :class:`Style` (which carries the day's palette).  No colour,
coordinate or piece of lesson content is hard-coded here — the builders take
parameters, the beats supply them from the script.

Contents
--------
``Style``               fonts, sizes, palette-aware text/maths factories
``Chalk``               hand-drawn chalk strokes (jittered, with dust bloom)
``Storyboard``          fits a list of animation steps into an exact budget
``CameraController``    smooth focus / reset / push-in on the moving frame
``HighlightSystem``     boxes, underlines, pulses, dim-the-rest
``CaptionTrack``        subtitle overlay pinned to the camera frame
``HUD``                 day badge + progress bar, always on top
``TitleCard``           day opening card
``RecapBuilder``        "previously on…" cards revealed one by one
``SquareBuilder``       chalk square + dimension labels
``DiagonalAnimator``    diagonal, right triangles, right-angle marker
``NumberLineBuilder``   styled number line with plotted points and zooms
``FractionVisualizer``  p/q symbol, bar model and pie model
``EquationWriter``      line-by-line derivations with dimming and highlights
``ConceptCard``         headline card for statements and definitions
``ComparePanels``       two-column comparison
``ClassifyBoard``       sort items into labelled buckets
``MistakePanel``        wrong-vs-right correction
``ParticleField``       drifting motes for the intro backdrops
``GridBackdrop``        faint lattice for depth
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence, Tuple

import numpy as np
from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    PI,
    RIGHT,
    UP,
    AnimationGroup,
    Circle,
    Create,
    Dot,
    DashedLine,
    FadeIn,
    Flash,
    Indicate,
    Line,
    LaggedStart,
    ManimColor,
    MathTex,
    Mobject,
    NumberLine,
    Polygon,
    Rectangle,
    Restore,
    RightAngle,
    RoundedRectangle,
    Scene,
    SurroundingRectangle,
    Text,
    Underline,
    VGroup,
    VMobject,
    Write,
    config,
    rate_functions,
)

from rational_series.color_engine import DayPalette

# --------------------------------------------------------------------------
# Environment probes (fonts / LaTeX) — done once, cached
# --------------------------------------------------------------------------

_FONT_PREFERENCES = ("Lato", "Nimbus Sans", "DejaVu Sans", "Liberation Sans", "FreeSans")
_LATEX_STATE: Optional[bool] = None


def pick_font() -> str:
    """First installed font from the house preference list."""
    try:
        import manimpango

        installed = set(manimpango.list_fonts())
    except Exception:  # pragma: no cover - pango always present with manim
        return _FONT_PREFERENCES[-1]
    for name in _FONT_PREFERENCES:
        if name in installed:
            return name
    return "sans-serif"


def latex_available() -> bool:
    """True when a working LaTeX toolchain can compile ``MathTex``.

    Probed once; on CI images without TeX the whole library silently falls
    back to unicode maths so a render never dies over a missing binary.
    """
    global _LATEX_STATE
    if _LATEX_STATE is None:
        import os

        if os.environ.get("RS_NO_LATEX"):
            _LATEX_STATE = False
        else:
            try:
                MathTex("x")
                _LATEX_STATE = True
            except Exception:
                _LATEX_STATE = False
    return _LATEX_STATE


_UNICODE_MAP = (
    (r"\\sqrt\{([^{}]*)\}", "√\\1"),
    (r"\\frac\{([^{}]*)\}\{([^{}]*)\}", "\\1/\\2"),
    (r"\\tfrac\{([^{}]*)\}\{([^{}]*)\}", "\\1/\\2"),
    (r"\\text\{([^{}]*)\}", "\\1"),
    (r"\\mathbb\{Q\}", "ℚ"),
    (r"\\mathbb\{R\}", "ℝ"),
    (r"\\mathbb\{Z\}", "ℤ"),
    (r"\\neq", "≠"),
    (r"\\notin", "∉"),
    (r"\\in\b", "∈"),
    (r"\\Rightarrow", "⇒"),
    (r"\\rightarrow", "→"),
    (r"\\times", "×"),
    (r"\\cdot", "·"),
    (r"\\div", "÷"),
    (r"\\pm", "±"),
    (r"\\pi\b", "π"),
    (r"\\checkmark", "✓"),
    (r"\\ldots|\\dots", "…"),
    (r"\^2", "²"),
    (r"\^3", "³"),
    (r"[{}]", ""),
    (r"\\[,;!]", " "),
    (r"\\quad|\\ ", " "),
)


def latex_to_unicode(tex: str) -> str:
    """Best-effort LaTeX -> unicode, for the no-TeX fallback path."""
    out = tex
    for pattern, repl in _UNICODE_MAP:
        out = re.sub(pattern, repl, out)
    return re.sub(r"\s+", " ", out).strip()


# --------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------


@dataclass
class Style:
    """Palette + typography, passed to every builder."""

    palette: DayPalette
    font: str = field(default_factory=pick_font)

    # Typographic scale (frame heights of 8.0 units)
    size_hero: float = 84.0
    size_title: float = 54.0
    size_heading: float = 40.0
    size_body: float = 30.0
    size_label: float = 24.0
    size_caption: float = 26.0

    stroke_bold: float = 8.0
    stroke_normal: float = 5.0
    stroke_thin: float = 2.5

    # ---- text factories --------------------------------------------------

    def text(
        self,
        content: str,
        *,
        size: Optional[float] = None,
        color: Optional[str] = None,
        weight: str = "NORMAL",
        slant: str = "NORMAL",
    ) -> Text:
        return Text(
            content,
            font=self.font,
            font_size=size or self.size_body,
            color=ManimColor(color or self.palette.ink),
            weight=weight,
            slant=slant,
        )

    def title(self, content: str, *, color: Optional[str] = None, size: Optional[float] = None) -> Text:
        return self.text(content, size=size or self.size_title, color=color or self.palette.ink, weight="BOLD")

    def heading(self, content: str, *, color: Optional[str] = None) -> Text:
        return self.text(content, size=self.size_heading, color=color or self.palette.accent, weight="BOLD")

    def label(self, content: str, *, color: Optional[str] = None) -> Text:
        return self.text(content, size=self.size_label, color=color or self.palette.ink_dim)

    def math(self, tex: str, *, size: Optional[float] = None, color: Optional[str] = None) -> Mobject:
        """LaTeX maths, degrading to unicode text when TeX is unavailable."""
        colour = ManimColor(color or self.palette.ink)
        if latex_available():
            # font_size keeps LaTeX on the same optical scale as Text.
            return MathTex(tex, color=colour, font_size=size or self.size_body)
        return self.text(latex_to_unicode(tex), size=size or self.size_body, color=color)

    # ---- panels ----------------------------------------------------------

    def panel(self, width: float, height: float, *, color: Optional[str] = None, opacity: float = 0.55) -> RoundedRectangle:
        return RoundedRectangle(
            width=width,
            height=height,
            corner_radius=0.18,
            stroke_color=ManimColor(color or self.palette.accent),
            stroke_width=self.stroke_thin,
            fill_color=ManimColor(self.palette.surface),
            fill_opacity=opacity,
        )

    def rule(self, width: float, *, color: Optional[str] = None) -> Line:
        return Line(
            LEFT * width / 2,
            RIGHT * width / 2,
            stroke_width=self.stroke_thin,
            color=ManimColor(color or self.palette.accent),
        )


# --------------------------------------------------------------------------
# Chalk strokes
# --------------------------------------------------------------------------


class Chalk:
    """Hand-drawn chalk strokes: slightly wobbly lines with a dust bloom.

    The wobble is deterministic (seeded per day) so re-renders are identical.
    """

    def __init__(self, style: Style, *, seed: int = 0, jitter: float = 0.006, samples: int = 16):
        self.style = style
        self.jitter = jitter
        self.samples = samples
        self._rng = random.Random(f"chalk-{seed}")

    # -- primitives --------------------------------------------------------

    def _wobble(self, start: np.ndarray, end: np.ndarray) -> List[np.ndarray]:
        """Points along a segment, nudged sideways by smooth seeded noise."""
        direction = end - start
        length = float(np.linalg.norm(direction))
        if length < 1e-6:
            return [start, end]
        normal = np.array([-direction[1], direction[0], 0.0]) / length
        phase = self._rng.uniform(0, PI * 2)
        freq = self._rng.uniform(1.2, 2.6)
        amp = self.jitter * min(length, 4.0)
        points = []
        for i in range(self.samples + 1):
            t = i / self.samples
            # Envelope keeps the ends pinned so corners still meet exactly.
            envelope = math.sin(PI * t)
            offset = amp * envelope * math.sin(phase + freq * PI * 2 * t)
            points.append(start + direction * t + normal * offset)
        return points

    def line(
        self,
        start: Sequence[float],
        end: Sequence[float],
        *,
        color: Optional[str] = None,
        width: Optional[float] = None,
    ) -> VMobject:
        stroke = VMobject()
        stroke.set_points_smoothly(self._wobble(np.array(start, dtype=float), np.array(end, dtype=float)))
        stroke.set_stroke(
            color=ManimColor(color or self.style.palette.chalk),
            width=width or self.style.stroke_bold,
            opacity=1.0,
        )
        stroke.set_fill(opacity=0.0)
        return stroke

    def dust(self, stroke: VMobject, *, spread: float = 2.3, opacity: float = 0.11) -> VMobject:
        """A wider, faint copy that sits behind a stroke — chalk bloom."""
        halo = stroke.copy()
        halo.set_stroke(width=stroke.stroke_width * spread, opacity=opacity)
        halo.set_z_index(stroke.z_index - 1)
        return halo

    def stroke_with_dust(self, *args: Any, **kwargs: Any) -> VGroup:
        stroke = self.line(*args, **kwargs)
        return VGroup(self.dust(stroke), stroke)

    def path(self, points: Sequence[Sequence[float]], *, closed: bool = False, **kwargs: Any) -> VGroup:
        """A chalk polyline: one wobbly stroke per segment."""
        pts = [np.array(p, dtype=float) for p in points]
        if closed:
            pts = pts + [pts[0]]
        return VGroup(*[self.line(a, b, **kwargs) for a, b in zip(pts, pts[1:])])


# --------------------------------------------------------------------------
# Timing
# --------------------------------------------------------------------------


@dataclass
class _Step:
    kind: str  # "play" | "wait" | "call"
    weight: float
    payload: Any = None
    kwargs: dict = field(default_factory=dict)
    fixed: Optional[float] = None  # seconds, overrides the weight share


class Storyboard:
    """Fits a beat's animation steps into an exact narration budget.

    Beats declare *what* happens and roughly how much of the sentence each
    step deserves; the storyboard converts that into real ``run_time``s so
    the visuals always land with the voice — never early, never clipped.
    """

    MIN_STEP = 0.28

    def __init__(self, scene: Scene, budget: float):
        self.scene = scene
        self.budget = max(budget, 0.0)
        self._steps: List[_Step] = []

    # -- declaration -------------------------------------------------------

    def play(self, *animations: Any, weight: float = 1.0, seconds: Optional[float] = None, **kwargs: Any) -> "Storyboard":
        """Queue ``scene.play(*animations)`` taking ``weight`` share of the budget."""
        flat = [a for a in animations if a is not None]
        if flat:
            self._steps.append(_Step("play", weight, flat, kwargs, seconds))
        return self

    def wait(self, weight: float = 1.0, *, seconds: Optional[float] = None) -> "Storyboard":
        self._steps.append(_Step("wait", weight, None, {}, seconds))
        return self

    def call(self, fn: Callable[[], None]) -> "Storyboard":
        """Run a zero-time callback in sequence (adds/removes, z-order…)."""
        self._steps.append(_Step("call", 0.0, fn, {}, 0.0))
        return self

    # -- execution ---------------------------------------------------------

    def _allocate(self) -> List[float]:
        timed = [s for s in self._steps if s.kind != "call"]
        if not timed:
            return []
        fixed_total = sum(s.fixed for s in timed if s.fixed is not None)
        flexible = [s for s in timed if s.fixed is None]
        remaining = max(self.budget - fixed_total, 0.0)
        weights = sum(max(s.weight, 0.0) for s in flexible) or 1.0

        shares = {id(s): (s.fixed if s.fixed is not None else remaining * max(s.weight, 0.0) / weights) for s in timed}

        # Nothing may be so short that it reads as a glitch; steal the extra
        # time from the longest steps.
        deficit = 0.0
        for step in timed:
            if shares[id(step)] < self.MIN_STEP:
                deficit += self.MIN_STEP - shares[id(step)]
                shares[id(step)] = self.MIN_STEP
        if deficit > 0:
            donors = sorted((s for s in timed if shares[id(s)] > self.MIN_STEP), key=lambda s: -shares[id(s)])
            pool = sum(shares[id(s)] - self.MIN_STEP for s in donors)
            if pool > 0:
                scale = min(deficit / pool, 1.0)
                for donor in donors:
                    shares[id(donor)] -= (shares[id(donor)] - self.MIN_STEP) * scale
        return [shares[id(s)] for s in timed]

    def run(self) -> float:
        """Execute every step; returns the number of seconds consumed."""
        durations = iter(self._allocate())
        spent = 0.0
        for step in self._steps:
            if step.kind == "call":
                step.payload()
                continue
            seconds = next(durations)
            if step.kind == "wait":
                if seconds > 0.01:
                    self.scene.wait(seconds)
            else:
                self.scene.play(*step.payload, run_time=max(seconds, 0.05), **step.kwargs)
            spent += seconds
        return spent


# --------------------------------------------------------------------------
# Camera
# --------------------------------------------------------------------------


class CameraController:
    """Cinematic moves on a ``MovingCameraScene`` frame."""

    def __init__(self, scene: Scene):
        self.scene = scene
        self.frame = scene.camera.frame  # type: ignore[attr-defined]
        self.home_width = float(self.frame.width)
        self.home_center = self.frame.get_center().copy()

    def focus(self, target: Mobject, *, margin: float = 1.6, max_zoom: float = 2.2):
        """Animation that frames ``target`` with breathing room around it."""
        width = max(target.width + margin * 2, (target.height + margin * 2) * config.frame_width / config.frame_height)
        width = max(width, self.home_width / max_zoom)
        width = min(width, self.home_width)
        return self.frame.animate.set(width=width).move_to(target.get_center())

    def reset(self):
        return self.frame.animate.set(width=self.home_width).move_to(self.home_center)

    def push_in(self, factor: float = 0.88):
        return self.frame.animate.set(width=self.frame.width * factor)

    def pull_back(self, factor: float = 1.14):
        return self.frame.animate.set(width=min(self.frame.width * factor, self.home_width * 1.35))

    def drift(self, shift: Sequence[float]):
        return self.frame.animate.shift(np.array(shift, dtype=float))

    def is_home(self, tolerance: float = 0.02) -> bool:
        return (
            abs(self.frame.width - self.home_width) < tolerance
            and float(np.linalg.norm(self.frame.get_center() - self.home_center)) < tolerance
        )


# --------------------------------------------------------------------------
# Highlights
# --------------------------------------------------------------------------


class HighlightSystem:
    """One place for every "look here" gesture in the series."""

    def __init__(self, style: Style):
        self.style = style

    def box(self, target: Mobject, *, color: Optional[str] = None, buff: float = 0.18) -> SurroundingRectangle:
        return SurroundingRectangle(
            target,
            color=ManimColor(color or self.style.palette.highlight),
            buff=buff,
            corner_radius=0.08,
            stroke_width=self.style.stroke_normal * 0.7,
        )

    def underline(self, target: Mobject, *, color: Optional[str] = None) -> Underline:
        line = Underline(target, color=ManimColor(color or self.style.palette.accent))
        line.set_stroke(width=self.style.stroke_normal)
        return line

    def sweep_underline(self, target: Mobject, *, color: Optional[str] = None):
        return Create(self.underline(target, color=color))

    def pulse(self, target: Mobject, *, color: Optional[str] = None, scale: float = 1.12):
        return Indicate(target, color=ManimColor(color or self.style.palette.highlight), scale_factor=scale)

    def flash(self, target: Mobject, *, color: Optional[str] = None):
        return Flash(
            target,
            color=ManimColor(color or self.style.palette.highlight),
            line_length=0.24,
            num_lines=14,
            flash_radius=max(target.width, target.height) * 0.62,
        )

    def dim(self, *targets: Mobject, amount: float = 0.28):
        return AnimationGroup(*[t.animate.set_opacity(amount) for t in targets], lag_ratio=0.0)

    def restore(self, *targets: Mobject):
        return AnimationGroup(*[t.animate.set_opacity(1.0) for t in targets], lag_ratio=0.0)


# --------------------------------------------------------------------------
# Frame-pinned overlays (captions + HUD)
# --------------------------------------------------------------------------


def pin_to_frame(
    scene: Scene,
    mobject: Mobject,
    *,
    anchor: Sequence[float] = DOWN,
    margin: float = 0.45,
    z_index: int = 60,
) -> Mobject:
    """Keep ``mobject`` locked to a screen position while the camera moves.

    Overlays must not zoom with the stage, so each frame the mobject is
    re-scaled from its *original* size (absolute, never cumulative) and
    re-anchored to the current camera frame.
    """
    frame = scene.camera.frame  # type: ignore[attr-defined]
    base_height = float(mobject.height) or 0.001
    base_frame_height = float(config.frame_height)
    anchor_vec = np.array(anchor, dtype=float)
    mobject.set_z_index(z_index)

    def _update(mob: Mobject) -> None:
        scale = frame.height / base_frame_height
        mob.set(height=base_height * scale)
        point = frame.get_center() + np.array(
            [anchor_vec[0] * frame.width / 2.0, anchor_vec[1] * frame.height / 2.0, 0.0]
        )
        point -= anchor_vec * margin * scale
        mob.move_to(point, aligned_edge=anchor_vec)

    _update(mobject)
    mobject.add_updater(_update)
    return mobject


class CaptionTrack(VGroup):
    """Subtitle overlay: clean caption bar, one phrase at a time.

    The captions are decoration — the teaching happens in the animation —
    so they sit low, stay quiet, and cross-fade instead of popping.
    """

    FADE = 0.16

    def __init__(self, style: Style, lines: Sequence[str], duration: float, *, width: float = 10.4):
        super().__init__()
        self.style = style
        self._elapsed = 0.0
        self._cues: List[Tuple[float, float, VGroup]] = []
        if not lines or duration <= 0:
            return

        total_chars = sum(len(line) for line in lines) or 1
        cursor = 0.0
        for line in lines:
            share = duration * (len(line) / total_chars)
            cue = self._build_cue(line, width)
            cue.set_opacity(0.0)
            self._cues.append((cursor, cursor + share, cue))
            self.add(cue)
            cursor += share

    def _build_cue(self, line: str, width: float) -> VGroup:
        text = self.style.text(line, size=self.style.size_caption, color=self.style.palette.ink)
        if text.width > width:
            text.set(width=width)
        bar = RoundedRectangle(
            width=text.width + 0.6,
            height=text.height + 0.42,
            corner_radius=0.14,
            stroke_width=0.0,
            fill_color=ManimColor(self.style.palette.background_deep),
            fill_opacity=0.78,
        )
        group = VGroup(bar, text)
        text.move_to(bar.get_center())
        return group

    def _alpha(self, start: float, end: float) -> float:
        """Fade in *after* the cue starts and out *before* it ends.

        Keeping both ramps inside the cue's own window means two captions
        are never legible at once.
        """
        t = self._elapsed
        fade = min(self.FADE, max((end - start) / 3.0, 0.01))
        if t < start or t > end:
            return 0.0
        if t < start + fade:
            return (t - start) / fade
        if t > end - fade:
            return max(0.0, (end - t) / fade)
        return 1.0

    def attach(self, scene: Scene, *, margin: float = 0.55) -> "CaptionTrack":
        """Add to the scene, pin to the frame and start the cue clock."""
        if not self._cues:
            return self
        frame = scene.camera.frame  # type: ignore[attr-defined]
        base_frame_height = float(config.frame_height)
        bases = [(cue, float(cue.height)) for _s, _e, cue in self._cues]
        self.set_z_index(70)

        def _update(_mob: Mobject, dt: float) -> None:
            self._elapsed += dt
            scale = frame.height / base_frame_height
            anchor = frame.get_center() + DOWN * frame.height / 2.0 + UP * margin * scale
            for (start, end, cue), (_c, base_height) in zip(self._cues, bases):
                alpha = self._alpha(start, end)
                if alpha <= 0.0:
                    cue.set_opacity(0.0)
                    continue
                cue.set(height=base_height * scale)
                cue.move_to(anchor, aligned_edge=DOWN)
                cue[0].set_opacity(0.78 * alpha)
                cue[1].set_opacity(alpha)

        self.add_updater(_update)
        scene.add(self)
        return self

    def detach(self, scene: Scene) -> None:
        self.clear_updaters()
        scene.remove(self)


class HUD:
    """Persistent screen furniture: day badge and series progress bar."""

    def __init__(self, style: Style, day: int, *, topic: str = ""):
        self.style = style
        palette = style.palette
        badge_text = style.text(f"DAY {day:02d}", size=style.size_label, color=palette.background, weight="BOLD")
        badge_bg = RoundedRectangle(
            width=badge_text.width + 0.5,
            height=badge_text.height + 0.32,
            corner_radius=0.1,
            stroke_width=0.0,
            fill_color=ManimColor(palette.accent),
            fill_opacity=1.0,
        )
        self.badge = VGroup(badge_bg, badge_text)
        badge_text.move_to(badge_bg.get_center())
        if topic:
            label = style.label(topic.upper(), color=palette.ink_dim)
            label.next_to(self.badge, RIGHT, buff=0.22)
            self.badge = VGroup(self.badge, label)

        # Rectangles, not lines: a flat line has zero height and would be
        # skipped by the frame-pinning rescale, so it would not follow zooms.
        self.bar_width = 13.0
        self.bar_height = 0.055
        self.progress_bg = Rectangle(
            width=self.bar_width,
            height=self.bar_height,
            stroke_width=0.0,
            fill_color=ManimColor(palette.ink_dim),
            fill_opacity=0.24,
        )
        self.progress_fill = Rectangle(
            width=self.bar_width * 0.001,
            height=self.bar_height,
            stroke_width=0.0,
            fill_color=ManimColor(palette.accent),
            fill_opacity=1.0,
        )
        self.progress_fill.align_to(self.progress_bg, LEFT)
        self.progress = VGroup(self.progress_bg, self.progress_fill)

    def attach(self, scene: Scene) -> None:
        pin_to_frame(scene, self.badge, anchor=UP + LEFT, margin=0.42)
        pin_to_frame(scene, self.progress, anchor=UP, margin=0.24)
        scene.add(self.badge, self.progress)

    def set_progress(self, fraction: float) -> None:
        """Grow the progress bar (called between beats, costs no time)."""
        fraction = max(0.001, min(1.0, fraction))
        left_edge = self.progress_bg.get_left()
        self.progress_fill.stretch_to_fit_width(self.progress_bg.width * fraction)
        self.progress_fill.move_to(left_edge, aligned_edge=LEFT)


# --------------------------------------------------------------------------
# Content builders
# --------------------------------------------------------------------------


class TitleCard(VGroup):
    """Day opening: big number, title, rule, subtitle."""

    def __init__(self, style: Style, day: int, title: str, subtitle: str = ""):
        super().__init__()
        palette = style.palette
        self.day_label = style.text(f"DAY {day}", size=style.size_heading, color=palette.accent, weight="BOLD")
        self.title = style.text(title, size=style.size_hero, color=palette.ink, weight="BOLD")
        if self.title.width > 12.0:
            self.title.set(width=12.0)
        self.rule = style.rule(min(self.title.width, 11.0), color=palette.accent)
        self.subtitle = style.text(subtitle, size=style.size_body, color=palette.ink_dim) if subtitle else VGroup()

        self.add(self.day_label, self.title, self.rule)
        self.title.next_to(self.day_label, DOWN, buff=0.34)
        self.rule.next_to(self.title, DOWN, buff=0.3)
        if subtitle:
            self.subtitle.next_to(self.rule, DOWN, buff=0.3)
            if self.subtitle.width > 11.0:
                self.subtitle.set(width=11.0)
            self.add(self.subtitle)
        self.move_to(ORIGIN)


class RecapBuilder(VGroup):
    """"Previously on…" — recap points that arrive one at a time.

    Each item gets a numbered badge, its own accent from the day's palette
    and a sweeping underline as it lands, so the recap *moves* instead of
    being a wall of bullet text.
    """

    def __init__(self, style: Style, items: Sequence[str], *, heading: str = "", width: float = 9.6):
        super().__init__()
        self.style = style
        palette = style.palette
        self.colors = palette.cycle(max(len(items), 1))
        self.heading = style.heading(heading, color=palette.accent) if heading else None
        self.cards: List[VGroup] = []

        for i, item in enumerate(items):
            colour = self.colors[i % len(self.colors)]
            badge = Circle(
                radius=0.28,
                stroke_color=ManimColor(colour),
                stroke_width=style.stroke_thin,
                fill_color=ManimColor(colour),
                fill_opacity=0.16,
            )
            number = style.text(str(i + 1), size=style.size_label, color=colour, weight="BOLD")
            number.move_to(badge.get_center())
            label = style.text(item, size=style.size_body, color=palette.ink)
            if label.width > width - 1.4:
                label.set(width=width - 1.4)
            label.next_to(badge, RIGHT, buff=0.38)
            card = VGroup(badge, number, label)
            self.cards.append(card)

        stack = VGroup(*self.cards).arrange(DOWN, buff=0.46, aligned_edge=LEFT)
        if self.heading is not None:
            self.heading.next_to(stack, UP, buff=0.62).align_to(stack, LEFT)
            self.add(self.heading)
        self.add(stack)
        self.stack = stack
        self.move_to(ORIGIN)

    def reveal_animations(self) -> List[Any]:
        """One animation per card: it slides in from the left and settles."""
        animations: List[Any] = []
        if self.heading is not None:
            animations.append(Write(self.heading))
        for card in self.cards:
            card.save_state()
            card.shift(LEFT * 1.1).set_opacity(0.0)
            animations.append(Restore(card, rate_func=rate_functions.ease_out_cubic))
        return animations

    def spotlight(self, index: int) -> Any:
        """Bring one card forward and push the others back."""
        others = [c for i, c in enumerate(self.cards) if i != index]
        return AnimationGroup(
            self.cards[index].animate.set_opacity(1.0).scale(1.06),
            *[c.animate.set_opacity(0.32) for c in others],
        )


class SquareBuilder(VGroup):
    """A chalk square that is *drawn*, edge by edge, with real dimensions."""

    def __init__(
        self,
        style: Style,
        *,
        side: float = 3.6,
        side_label: str = "1",
        seed: int = 0,
        show_labels: bool = True,
    ):
        super().__init__()
        self.style = style
        self.side = side
        self.chalk = Chalk(style, seed=seed)
        half = side / 2.0
        self.corners = [
            np.array([-half, -half, 0.0]),
            np.array([half, -half, 0.0]),
            np.array([half, half, 0.0]),
            np.array([-half, half, 0.0]),
        ]
        self.edges = VGroup(
            *[
                self.chalk.line(self.corners[i], self.corners[(i + 1) % 4], width=style.stroke_bold)
                for i in range(4)
            ]
        )
        self.dust = VGroup(*[self.chalk.dust(edge) for edge in self.edges])
        self.add(self.dust, self.edges)

        self.labels = VGroup()
        if show_labels and side_label:
            self.labels.add(
                self._dimension_label(side_label, DOWN, self.corners[0], self.corners[1]),
                self._dimension_label(side_label, LEFT, self.corners[0], self.corners[3]),
            )
            self.add(self.labels)

    def _dimension_label(self, text: str, side: np.ndarray, a: np.ndarray, b: np.ndarray) -> VGroup:
        """Tick marks plus a measurement caption on the outside of an edge."""
        palette = self.style.palette
        offset = np.array(side, dtype=float) * 0.42
        tick_a = Line(a, a + offset * 1.5, stroke_width=self.style.stroke_thin, color=ManimColor(palette.ink_dim))
        tick_b = Line(b, b + offset * 1.5, stroke_width=self.style.stroke_thin, color=ManimColor(palette.ink_dim))
        arrow = DashedLine(
            a + offset,
            b + offset,
            stroke_width=self.style.stroke_thin,
            color=ManimColor(palette.ink_dim),
            dash_length=0.09,
        )
        caption = self.style.text(text, size=self.style.size_label, color=palette.ink_dim)
        caption.move_to((a + b) / 2 + offset * 2.1)
        return VGroup(tick_a, tick_b, arrow, caption)

    # -- animations --------------------------------------------------------

    def draw_animations(self) -> List[Any]:
        """Four strokes, drawn in order, exactly like drawing on a board."""
        return [
            AnimationGroup(FadeIn(self.dust[i], run_time=0.4), Create(self.edges[i]), lag_ratio=0.0)
            for i in range(4)
        ]

    def label_animations(self) -> List[Any]:
        if not len(self.labels):
            return []
        return [LaggedStart(*[FadeIn(label, shift=UP * 0.12) for label in self.labels], lag_ratio=0.35)]

    def corner_dots(self) -> VGroup:
        palette = self.style.palette
        return VGroup(*[Dot(c, radius=0.055, color=ManimColor(palette.accent)) for c in self.corners])

    def interior_label(self, text: str, *, color: Optional[str] = None) -> Text:
        label = self.style.text(text, size=self.style.size_body, color=color or self.style.palette.ink_dim)
        label.move_to(self.edges.get_center())
        return label


class DiagonalAnimator:
    """The diagonal of a square, and the two right triangles it creates."""

    def __init__(self, style: Style, square: SquareBuilder, *, seed: int = 0):
        self.style = style
        self.square = square
        self.chalk = Chalk(style, seed=seed + 11)
        palette = style.palette
        a, c = square.corners[0], square.corners[2]
        self.diagonal = self.chalk.line(a, c, color=palette.accent, width=style.stroke_bold)
        self.diagonal_dust = self.chalk.dust(self.diagonal, opacity=0.22)
        self.lower = Polygon(
            square.corners[0],
            square.corners[1],
            square.corners[2],
            stroke_width=0.0,
            fill_color=ManimColor(palette.accent),
            fill_opacity=0.18,
        )
        self.upper = Polygon(
            square.corners[0],
            square.corners[2],
            square.corners[3],
            stroke_width=0.0,
            fill_color=ManimColor(palette.secondary),
            fill_opacity=0.18,
        )
        self.right_angle = RightAngle(
            Line(square.corners[1], square.corners[0]),
            Line(square.corners[1], square.corners[2]),
            length=0.34,
            color=ManimColor(palette.ink_dim),
            stroke_width=style.stroke_thin,
        )

    def draw_animation(self) -> Any:
        return AnimationGroup(FadeIn(self.diagonal_dust, run_time=0.5), Create(self.diagonal), lag_ratio=0.0)

    def triangle_animations(self) -> List[Any]:
        return [
            LaggedStart(FadeIn(self.lower), FadeIn(self.upper), lag_ratio=0.5),
            Create(self.right_angle),
        ]

    def label(
        self,
        text: str,
        *,
        color: Optional[str] = None,
        buff: float = 0.42,
        rotate: bool = False,
    ) -> Mobject:
        """A label sitting just off the diagonal (upright unless asked)."""
        label = self.style.math(text, size=self.style.size_title, color=color or self.style.palette.accent)
        mid = self.diagonal.get_center()
        direction = self.square.corners[2] - self.square.corners[0]
        angle = math.atan2(direction[1], direction[0])
        normal = np.array([-math.sin(angle), math.cos(angle), 0.0])
        if rotate:
            label.rotate(angle)
        label.move_to(mid + normal * (buff + label.height / 2))
        return label


class NumberLineBuilder(VGroup):
    """A styled number line with plotted, labelled points."""

    def __init__(
        self,
        style: Style,
        *,
        x_range: Sequence[float] = (0, 3, 1),
        length: float = 11.0,
        decimals: int = 0,
    ):
        super().__init__()
        self.style = style
        palette = style.palette
        self.line = NumberLine(
            x_range=list(x_range),
            length=length,
            color=ManimColor(palette.ink_dim),
            stroke_width=style.stroke_normal,
            include_numbers=True,
            decimal_number_config={"num_decimal_places": decimals, "color": ManimColor(palette.ink_dim)},
            font_size=style.size_body,
        )
        self.add(self.line)
        # NB: not `self.points` — that name belongs to Mobject's geometry.
        self.markers = VGroup()
        self.add(self.markers)

    def plot(self, value: float, label: str = "", *, color: Optional[str] = None, above: bool = True) -> VGroup:
        palette = self.style.palette
        colour = ManimColor(color or palette.accent)
        position = self.line.number_to_point(value)
        dot = Dot(position, radius=0.12, color=colour)
        stem = Line(
            position,
            position + (UP if above else DOWN) * 0.7,
            stroke_width=self.style.stroke_normal * 0.8,
            color=colour,
        )
        group = VGroup(dot, stem)
        if label:
            tag = self.style.math(label, size=self.style.size_heading, color=color or palette.accent)
            tag.next_to(stem, UP if above else DOWN, buff=0.18)
            group.add(tag)
        self.markers.add(group)
        return group

    def bracket(self, low: float, high: float, *, color: Optional[str] = None) -> Rectangle:
        """Highlight the stretch of line between two values."""
        palette = self.style.palette
        left, right = self.line.number_to_point(low), self.line.number_to_point(high)
        band = Rectangle(
            width=max(float(right[0] - left[0]), 0.05),
            height=0.72,
            stroke_width=0.0,
            fill_color=ManimColor(color or palette.highlight),
            fill_opacity=0.16,
        )
        band.move_to((left + right) / 2)
        return band


class FractionVisualizer:
    """p/q shown three ways: as a symbol, as a bar and as a pie."""

    def __init__(self, style: Style):
        self.style = style

    def symbol(self, p: Any, q: Any, *, size: Optional[float] = None, color: Optional[str] = None) -> Mobject:
        return self.style.math(rf"\frac{{{p}}}{{{q}}}", size=size or self.style.size_heading, color=color)

    def bar_model(self, p: int, q: int, *, width: float = 5.4, height: float = 0.9, color: Optional[str] = None) -> VGroup:
        palette = self.style.palette
        colour = ManimColor(color or palette.accent)
        cells = VGroup()
        cell_width = width / q
        for i in range(q):
            cell = Rectangle(
                width=cell_width,
                height=height,
                stroke_color=ManimColor(palette.ink_dim),
                stroke_width=self.style.stroke_thin,
                fill_color=colour,
                fill_opacity=0.72 if i < p else 0.0,
            )
            cell.move_to(RIGHT * (i * cell_width))
            cells.add(cell)
        cells.move_to(ORIGIN)
        return cells

    def pie_model(self, p: int, q: int, *, radius: float = 1.5, color: Optional[str] = None) -> VGroup:
        from manim import AnnularSector

        palette = self.style.palette
        colour = ManimColor(color or palette.accent)
        slices = VGroup()
        for i in range(q):
            wedge = AnnularSector(
                inner_radius=0.0,
                outer_radius=radius,
                angle=2 * PI / q,
                start_angle=PI / 2 + i * 2 * PI / q,
                stroke_color=ManimColor(palette.ink_dim),
                stroke_width=self.style.stroke_thin,
                fill_color=colour,
                fill_opacity=0.75 if i < p else 0.05,
            )
            slices.add(wedge)
        return slices


class EquationWriter(VGroup):
    """A derivation written one line at a time, previous lines dimmed.

    This is the workhorse for proofs: the audience always sees the whole
    argument so far, with attention on the line being spoken.
    """

    def __init__(
        self,
        style: Style,
        lines: Sequence[str],
        *,
        line_buff: float = 0.52,
        size: Optional[float] = None,
        align: Sequence[float] = LEFT,
        max_width: float = 11.0,
    ):
        super().__init__()
        self.style = style
        self.lines = [style.math(line, size=size or style.size_body) for line in lines]
        for mob in self.lines:
            if mob.width > max_width:
                mob.set(width=max_width)
        self.stack = VGroup(*self.lines).arrange(DOWN, buff=line_buff, aligned_edge=align)
        self.add(self.stack)
        self._written = 0

    def write_animations(self, *, dim: float = 0.45) -> List[Any]:
        """One step per line: write it, fade the previous one back.

        Lines are only added to the scene as they are written, so the block
        can be positioned freely beforehand without anything showing early.
        """
        steps: List[Any] = []
        for i, line in enumerate(self.lines):
            animations: List[Any] = [Write(line)]
            if i:
                animations.append(self.lines[i - 1].animate.set_opacity(dim))
            steps.append(AnimationGroup(*animations, lag_ratio=0.0))
        return steps

    def box(self, index: int, *, color: Optional[str] = None) -> SurroundingRectangle:
        return SurroundingRectangle(
            self.lines[index],
            color=ManimColor(color or self.style.palette.danger),
            buff=0.18,
            corner_radius=0.08,
            stroke_width=self.style.stroke_normal * 0.7,
        )


class ConceptCard(VGroup):
    """A designed statement: kicker, headline, optional maths and note."""

    def __init__(
        self,
        style: Style,
        headline: str,
        *,
        kicker: str = "",
        math: str = "",
        note: str = "",
        accent: Optional[str] = None,
        width: float = 11.0,
    ):
        super().__init__()
        palette = style.palette
        colour = accent or palette.accent
        parts: List[Mobject] = []

        if kicker:
            kick = style.text(kicker.upper(), size=style.size_label, color=colour, weight="BOLD")
            parts.append(kick)
        head = style.text(headline, size=style.size_title, color=palette.ink, weight="BOLD")
        if head.width > width:
            head.set(width=width)
        parts.append(head)
        if math:
            expr = style.math(math, size=style.size_title, color=colour)
            parts.append(expr)
        if note:
            sub = style.text(note, size=style.size_body, color=palette.ink_dim)
            if sub.width > width:
                sub.set(width=width)
            parts.append(sub)

        stack = VGroup(*parts).arrange(DOWN, buff=0.42)
        bar = Line(
            stack.get_corner(UP + LEFT) + LEFT * 0.42,
            stack.get_corner(DOWN + LEFT) + LEFT * 0.42,
            stroke_width=style.stroke_normal,
            color=ManimColor(colour),
        )
        self.headline = head
        self.stack = stack
        self.bar = bar
        self.add(bar, stack)
        self.move_to(ORIGIN)

    def reveal_animations(self) -> List[Any]:
        return [
            Create(self.bar),
            LaggedStart(*[FadeIn(part, shift=UP * 0.18) for part in self.stack], lag_ratio=0.4),
        ]


class ComparePanels(VGroup):
    """Two labelled panels, side by side, for A-versus-B moments."""

    def __init__(
        self,
        style: Style,
        left_title: str,
        right_title: str,
        left_items: Sequence[str],
        right_items: Sequence[str],
        *,
        left_color: Optional[str] = None,
        right_color: Optional[str] = None,
    ):
        super().__init__()
        palette = style.palette
        self.left = self._panel(style, left_title, left_items, left_color or palette.success)
        self.right = self._panel(style, right_title, right_items, right_color or palette.warning)
        VGroup(self.left, self.right).arrange(RIGHT, buff=0.9)
        self.add(self.left, self.right)
        self.move_to(ORIGIN)

    @staticmethod
    def _panel(style: Style, title: str, items: Sequence[str], colour: str) -> VGroup:
        head = style.text(title, size=style.size_heading, color=colour, weight="BOLD")
        rows = VGroup(*[style.math(item, size=style.size_body) for item in items]).arrange(DOWN, buff=0.34)
        body = VGroup(head, rows).arrange(DOWN, buff=0.5)
        frame = style.panel(max(body.width + 1.0, 4.6), body.height + 1.1, color=colour, opacity=0.35)
        body.move_to(frame.get_center())
        return VGroup(frame, body)

    def reveal_animations(self) -> List[Any]:
        return [FadeIn(self.left, shift=RIGHT * 0.3), FadeIn(self.right, shift=LEFT * 0.3)]


class ClassifyBoard(VGroup):
    """Items that fly into labelled buckets — the classification beat."""

    def __init__(
        self,
        style: Style,
        buckets: Sequence[str],
        items: Sequence[dict],
        *,
        bucket_colors: Optional[Sequence[str]] = None,
    ):
        super().__init__()
        self.style = style
        palette = style.palette
        colours = list(bucket_colors or [palette.success, palette.danger, palette.secondary])
        self.buckets: List[VGroup] = []
        for i, name in enumerate(buckets):
            colour = colours[i % len(colours)]
            title = style.text(name, size=style.size_heading, color=colour, weight="BOLD")
            box = style.panel(5.0, 3.1, color=colour, opacity=0.22)
            title.next_to(box, UP, buff=0.24)
            self.buckets.append(VGroup(box, title))
        bucket_row = VGroup(*self.buckets).arrange(RIGHT, buff=1.0).shift(DOWN * 0.55)

        self.items: List[Tuple[Mobject, int]] = []
        chips = VGroup()
        for item in items:
            chip = style.math(str(item.get("value", "")), size=style.size_heading, color=palette.ink)
            target = int(item.get("bucket", 0))
            chips.add(chip)
            self.items.append((chip, target))
        chips.arrange(RIGHT, buff=0.9).next_to(bucket_row, UP, buff=1.25)
        self.chip_row = chips
        self.bucket_row = bucket_row
        self.add(bucket_row, chips)
        self._slots = [0] * len(self.buckets)

    def setup_animations(self) -> List[Any]:
        return [
            LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in self.buckets], lag_ratio=0.3),
            LaggedStart(*[FadeIn(chip, scale=0.8) for chip, _ in self.items], lag_ratio=0.25),
        ]

    def sort_animations(self) -> List[Any]:
        """One animation per item: it flies into its bucket and takes colour."""
        steps = []
        for chip, target in self.items:
            box = self.buckets[target][0]
            colour = box.get_stroke_color()
            slot = self._slots[target]
            self._slots[target] += 1
            destination = box.get_center() + UP * (0.9 - slot * 0.72) + LEFT * 0.0
            steps.append(chip.animate.move_to(destination).set_color(colour))
        return steps


class MistakePanel(VGroup):
    """The classic wrong-then-right correction, with a struck-out error."""

    def __init__(self, style: Style, wrong: str, right: str, *, wrong_note: str = "", right_note: str = ""):
        super().__init__()
        palette = style.palette
        self.wrong = style.math(wrong, size=style.size_heading, color=palette.danger)
        self.right = style.math(right, size=style.size_heading, color=palette.success)
        self.strike = Line(
            self.wrong.get_left() + LEFT * 0.12,
            self.wrong.get_right() + RIGHT * 0.12,
            stroke_width=style.stroke_normal,
            color=ManimColor(palette.danger),
        )
        wrong_group = VGroup(self.wrong)
        right_group = VGroup(self.right)
        if wrong_note:
            note = style.label(wrong_note, color=palette.danger)
            note.next_to(self.wrong, DOWN, buff=0.28)
            wrong_group.add(note)
        if right_note:
            note = style.label(right_note, color=palette.success)
            note.next_to(self.right, DOWN, buff=0.28)
            right_group.add(note)
        VGroup(wrong_group, right_group).arrange(RIGHT, buff=1.6)
        self.strike.move_to(self.wrong.get_center())
        self.strike.set(width=self.wrong.width + 0.3)
        self.add(wrong_group, right_group)
        self.move_to(ORIGIN)

    def reveal_animations(self) -> List[Any]:
        return [
            FadeIn(self[0], shift=UP * 0.2),
            Create(self.strike),
            FadeIn(self[1], shift=UP * 0.2),
        ]


# --------------------------------------------------------------------------
# Atmosphere
# --------------------------------------------------------------------------


class ParticleField(VGroup):
    """Slow drifting motes — depth for intros without stealing attention."""

    def __init__(
        self,
        style: Style,
        *,
        count: int = 60,
        seed: int = 0,
        speed: float = 0.06,
        radius: Tuple[float, float] = (0.012, 0.05),
        spread: Tuple[float, float] = (15.0, 9.0),
    ):
        super().__init__()
        rng = random.Random(f"particles-{seed}")
        palette = style.palette
        colours = [palette.accent, palette.accent_soft, palette.ink_dim, palette.highlight]
        self._velocities: List[np.ndarray] = []
        self._spread = spread
        for _ in range(count):
            dot = Dot(
                point=np.array(
                    [rng.uniform(-spread[0] / 2, spread[0] / 2), rng.uniform(-spread[1] / 2, spread[1] / 2), 0.0]
                ),
                radius=rng.uniform(*radius),
                color=ManimColor(rng.choice(colours)),
            )
            dot.set_opacity(rng.uniform(0.12, 0.5))
            self.add(dot)
            angle = rng.uniform(0, 2 * PI)
            self._velocities.append(np.array([math.cos(angle), math.sin(angle), 0.0]) * speed * rng.uniform(0.4, 1.6))

    def start(self) -> "ParticleField":
        spread = self._spread

        def _drift(group: Mobject, dt: float) -> None:
            for dot, velocity in zip(group.submobjects, self._velocities):
                dot.shift(velocity * dt)
                x, y, _ = dot.get_center()
                # Wrap softly so the field never empties out.
                if abs(x) > spread[0] / 2:
                    dot.shift(LEFT * np.sign(x) * spread[0])
                if abs(y) > spread[1] / 2:
                    dot.shift(DOWN * np.sign(y) * spread[1])

        self.add_updater(_drift)
        return self

    def stop(self) -> "ParticleField":
        self.clear_updaters()
        return self


class GridBackdrop(VGroup):
    """A faint lattice: gives the stage a floor without drawing attention."""

    def __init__(self, style: Style, *, spacing: float = 1.0, opacity: float = 0.12, dots: bool = False):
        super().__init__()
        palette = style.palette
        width, height = config.frame_width * 1.3, config.frame_height * 1.3
        colour = ManimColor(palette.grid)
        if dots:
            x = -width / 2
            while x <= width / 2:
                y = -height / 2
                while y <= height / 2:
                    self.add(Dot(np.array([x, y, 0.0]), radius=0.018, color=colour).set_opacity(opacity * 2.2))
                    y += spacing
                x += spacing
        else:
            steps = int(width / spacing) + 1
            for i in range(steps + 1):
                x = -width / 2 + i * spacing
                self.add(Line([x, -height / 2, 0], [x, height / 2, 0], stroke_width=1.0, color=colour).set_opacity(opacity))
            steps = int(height / spacing) + 1
            for i in range(steps + 1):
                y = -height / 2 + i * spacing
                self.add(Line([-width / 2, y, 0], [width / 2, y, 0], stroke_width=1.0, color=colour).set_opacity(opacity))
        self.set_z_index(-10)


__all__ = [
    "CameraController",
    "CaptionTrack",
    "Chalk",
    "ClassifyBoard",
    "ComparePanels",
    "ConceptCard",
    "DiagonalAnimator",
    "EquationWriter",
    "FractionVisualizer",
    "GridBackdrop",
    "HUD",
    "HighlightSystem",
    "MistakePanel",
    "NumberLineBuilder",
    "ParticleField",
    "RecapBuilder",
    "SquareBuilder",
    "Storyboard",
    "Style",
    "TitleCard",
    "latex_available",
    "latex_to_unicode",
    "pick_font",
    "pin_to_frame",
]
