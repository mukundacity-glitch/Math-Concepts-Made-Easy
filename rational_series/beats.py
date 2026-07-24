"""Animation beats: one function per teaching concept.

The scene never decides what to draw.  It looks up ``block.concept`` in the
registry below, hands the beat a :class:`BeatContext` (style, camera,
storyboard pre-loaded with the narration's time budget) and lets the beat
build the visual from the block's parameters.

Adding a new kind of visual to the series = register one function here and
add a keyword rule in ``script_parser.CONCEPT_RULES``.  No other file
changes, ever.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import numpy as np
from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    AnimationGroup,
    Create,
    FadeIn,
    FadeOut,
    LaggedStart,
    Mobject,
    Scene,
    VGroup,
    Write,
    rate_functions,
)

from rational_series.color_engine import DayPalette
from rational_series.script_parser import NarrationBlock
from rational_series.visual_library import (
    CameraController,
    ClassifyBoard,
    ComparePanels,
    ConceptCard,
    DiagonalAnimator,
    EquationWriter,
    FractionVisualizer,
    HighlightSystem,
    MistakePanel,
    NumberLineBuilder,
    RecapBuilder,
    SquareBuilder,
    Storyboard,
    Style,
)

BeatFn = Callable[["BeatContext"], None]

#: concept name -> beat function
REGISTRY: Dict[str, BeatFn] = {}


def beat(*names: str) -> Callable[[BeatFn], BeatFn]:
    """Register a beat function under one or more concept names."""

    def decorator(fn: BeatFn) -> BeatFn:
        for name in names:
            REGISTRY[name] = fn
        return fn

    return decorator


@dataclass
class BeatContext:
    """Everything a beat needs, and nowhere else to reach."""

    scene: Scene
    style: Style
    block: NarrationBlock
    budget: float
    board: Storyboard
    camera: CameraController
    highlight: HighlightSystem
    stage: VGroup
    memory: Dict[str, Any] = field(default_factory=dict)

    # -- helpers -----------------------------------------------------------

    @property
    def palette(self) -> DayPalette:
        return self.style.palette

    @property
    def day(self) -> int:
        return self.palette.day

    def param(self, key: str, default: Any = None) -> Any:
        return self.block.params.get(key, default)

    def track(self, *mobjects: Mobject) -> None:
        """Mark mobjects as belonging to this beat, so the scene clears them."""
        for mob in mobjects:
            if mob is not None:
                self.stage.add(mob)

    def remember(self, key: str, value: Any) -> Any:
        """Keep something for a following ``keep_stage`` block (e.g. the square)."""
        self.memory[key] = value
        return value

    def recall(self, key: str, default: Any = None) -> Any:
        return self.memory.get(key, default)


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------


def key_phrase(narration: str, *, max_words: int = 9) -> str:
    """Pull a short headline out of narration when a script gives none."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration.strip()) if s.strip()]
    if not sentences:
        return ""
    # The shortest full sentence is almost always the punchy claim.
    candidates = [s for s in sentences if len(s.split()) >= 3] or sentences
    best = min(candidates, key=lambda s: len(s.split()))
    words = re.sub(r"[.!?]+$", "", best).split()
    return " ".join(words[:max_words])


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


# --------------------------------------------------------------------------
# Beats
# --------------------------------------------------------------------------


@beat("statement")
def statement_beat(ctx: BeatContext) -> None:
    """Default beat: a designed card, never a wall of narration text."""
    card = ConceptCard(
        ctx.style,
        ctx.param("headline") or key_phrase(ctx.block.narration),
        kicker=ctx.param("kicker", ""),
        math=ctx.param("math", ""),
        note=ctx.param("note", ""),
        accent=ctx.param("color"),
    )
    ctx.track(card)
    for step in card.reveal_animations():
        ctx.board.play(step, weight=1.0)
    ctx.board.play(ctx.highlight.pulse(card.headline), weight=0.5)
    ctx.board.wait(weight=0.6)


@beat("definition")
def definition_beat(ctx: BeatContext) -> None:
    """A definition, boxed and given weight."""
    card = ConceptCard(
        ctx.style,
        ctx.param("headline") or key_phrase(ctx.block.narration),
        kicker=ctx.param("kicker", "definition"),
        math=ctx.param("math", ""),
        note=ctx.param("note", ""),
        accent=ctx.param("color", ctx.palette.secondary),
    )
    box = ctx.highlight.box(card, color=ctx.param("color", ctx.palette.secondary), buff=0.5)
    ctx.track(card, box)
    for step in card.reveal_animations():
        ctx.board.play(step, weight=1.0)
    ctx.board.play(Create(box), weight=0.8)
    ctx.board.wait(weight=0.5)


@beat("recap")
def recap_beat(ctx: BeatContext) -> None:
    """Recap: previous-day points arrive one by one, each briefly spotlit.

    Script parameters
    -----------------
    ``items``    list of recap lines (required for a good recap)
    ``heading``  card heading, defaults to "Day N-1"
    """
    items = [str(i) for i in _as_list(ctx.param("items"))]
    if not items:
        items = [key_phrase(ctx.block.narration)]
    heading = ctx.param("heading") or f"Day {max(ctx.day - 1, 1)} — what we proved"

    recap = RecapBuilder(ctx.style, items, heading=heading)
    ctx.track(recap)

    reveals = recap.reveal_animations()
    for step in reveals:
        ctx.board.play(step, weight=1.0)
    # Brief visual highlight on each point, in order.
    for index, card in enumerate(recap.cards):
        underline = ctx.highlight.underline(card[2], color=recap.colors[index % len(recap.colors)])
        ctx.track(underline)
        ctx.board.play(
            AnimationGroup(ctx.highlight.pulse(card, color=recap.colors[index % len(recap.colors)]), Create(underline)),
            weight=0.55,
        )
    ctx.board.wait(weight=0.5)


@beat("draw_square")
def draw_square_beat(ctx: BeatContext) -> None:
    """Draw a square, edge by edge, in bold chalk — then measure it.

    Script parameters
    -----------------
    ``side_label``  measurement caption, e.g. "1 ft"
    ``size``        side length in scene units (default 3.6)
    ``inside``      optional label inside the square
    ``focus``       camera pushes in on the square (default True)
    """
    square = SquareBuilder(
        ctx.style,
        side=float(ctx.param("size", 3.6)),
        side_label=str(ctx.param("side_label", "1")),
        seed=ctx.day,
    )
    square.shift(np.array(ctx.param("shift", [0.0, -0.2, 0.0]), dtype=float))
    ctx.track(square)
    ctx.remember("square", square)

    if ctx.param("focus", True):
        # Frame the shape itself; the margin leaves room for the dimensions.
        ctx.board.play(
            ctx.camera.focus(square.edges, margin=2.5), weight=0.6, rate_func=rate_functions.ease_in_out_sine
        )

    # Four separate strokes: the audience watches the shape being built.
    for stroke in square.draw_animations():
        ctx.board.play(stroke, weight=0.9)

    dots = square.corner_dots()
    square.add(dots)  # travels with the square if a later beat moves it
    ctx.track(dots)
    ctx.board.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.15), weight=0.4)

    for step in square.label_animations():
        ctx.board.play(step, weight=0.9)

    inside = ctx.param("inside")
    if inside:
        label = square.interior_label(str(inside))
        ctx.track(label)
        ctx.board.play(FadeIn(label, scale=0.9), weight=0.6)
    ctx.board.wait(weight=0.5)


@beat("draw_diagonal")
def draw_diagonal_beat(ctx: BeatContext) -> None:
    """Draw the diagonal and reveal the two right triangles it creates.

    Reuses the square from the previous block when the script keeps the
    stage; otherwise it quietly draws its own so the beat always works.
    """
    square = ctx.recall("square")
    if square is None:
        square = SquareBuilder(
            ctx.style,
            side=float(ctx.param("size", 3.6)),
            side_label=str(ctx.param("side_label", "1")),
            seed=ctx.day,
        )
        square.shift(np.array(ctx.param("shift", [0.0, -0.2, 0.0]), dtype=float))
        ctx.track(square)
        ctx.remember("square", square)
        ctx.board.play(FadeIn(square), weight=0.5)

    diagonal = DiagonalAnimator(ctx.style, square, seed=ctx.day)
    ctx.track(diagonal.diagonal_dust, diagonal.diagonal, diagonal.lower, diagonal.upper, diagonal.right_angle)
    ctx.remember("diagonal", diagonal)

    # Keep the whole drawing together so a later beat can move it as one.
    figure = VGroup(square, diagonal.lower, diagonal.upper, diagonal.diagonal_dust, diagonal.diagonal,
                    diagonal.right_angle)
    ctx.remember("figure", figure)

    ctx.board.play(diagonal.draw_animation(), weight=1.4)
    for step in diagonal.triangle_animations():
        ctx.board.play(step, weight=0.8)

    label_text = ctx.param("label")
    if label_text:
        label = diagonal.label(str(label_text))
        ctx.track(label)
        figure.add(label)
        ctx.remember("diagonal_label", label)
        ctx.board.play(Write(label), weight=0.8)
        ctx.board.play(ctx.highlight.pulse(label), weight=0.4)
    ctx.board.wait(weight=0.4)


@beat("pythagoras")
def pythagoras_beat(ctx: BeatContext) -> None:
    """Measure the diagonal with Pythagoras, beside the figure it belongs to.

    Script parameters
    -----------------
    ``lines``  the derivation, LaTeX per line
    ``result`` final boxed value, e.g. ``\\sqrt{2}``
    """
    figure = ctx.recall("figure") or ctx.recall("square")
    lines = [str(l) for l in _as_list(ctx.param("lines"))] or [r"d^2 = 1^2 + 1^2", r"d^2 = 2", r"d = \sqrt{2}"]
    writer = EquationWriter(ctx.style, lines, size=ctx.style.size_heading, max_width=5.6)
    ctx.track(writer)

    if figure is not None:
        # The drawing moves to the left half, the derivation writes on the
        # right — the layout of an actual blackboard.
        writer.move_to(RIGHT * 3.3)
        ctx.board.play(
            AnimationGroup(
                figure.animate.scale(0.74).move_to(LEFT * 3.5),
                ctx.camera.reset(),
            ),
            weight=0.8,
            rate_func=rate_functions.ease_in_out_sine,
        )
    else:
        writer.move_to(ORIGIN)

    for step in writer.write_animations():
        ctx.board.play(step, weight=1.0)

    result = ctx.param("result")
    if result:
        box = writer.box(len(writer.lines) - 1, color=ctx.palette.accent)
        ctx.track(box)
        ctx.board.play(Create(box), weight=0.7)
        ctx.board.play(ctx.highlight.flash(writer.lines[-1], color=ctx.palette.accent), weight=0.5)
    ctx.board.wait(weight=0.4)


@beat("number_line")
def number_line_beat(ctx: BeatContext) -> None:
    """A number line with plotted points, and an optional zoom into a gap.

    Script parameters
    -----------------
    ``range``   ``[start, end, step]`` (default ``[0, 3, 1]``)
    ``points``  ``[{"value": 1.414, "label": "\\sqrt{2}", "color": "accent"}]``
    ``zoom``    value to zoom into after plotting
    ``band``    ``[low, high]`` stretch to highlight
    """
    x_range = [float(v) for v in _as_list(ctx.param("range", [0, 3, 1]))]
    line = NumberLineBuilder(ctx.style, x_range=x_range, length=float(ctx.param("length", 11.0)),
                             decimals=int(ctx.param("decimals", 0)))
    # Sit above centre so labels hung below the line clear the caption bar.
    line.shift(UP * float(ctx.param("raise", 1.0)))
    ctx.track(line)
    ctx.remember("number_line", line)
    ctx.board.play(Create(line.line), weight=1.1)

    band = _as_list(ctx.param("band"))
    if len(band) == 2:
        strip = line.bracket(float(band[0]), float(band[1]))
        ctx.track(strip)
        ctx.board.play(FadeIn(strip), weight=0.5)

    palette_lookup = {
        "accent": ctx.palette.accent,
        "secondary": ctx.palette.secondary,
        "highlight": ctx.palette.highlight,
        "success": ctx.palette.success,
        "danger": ctx.palette.danger,
        "ink": ctx.palette.ink,
    }
    plotted: List[Mobject] = []
    for spec in _as_list(ctx.param("points")):
        spec = spec if isinstance(spec, dict) else {"value": spec}
        colour = palette_lookup.get(str(spec.get("color", "accent")), spec.get("color"))
        point = line.plot(float(spec["value"]), str(spec.get("label", "")), color=colour,
                          above=bool(spec.get("above", True)))
        plotted.append(point)
        ctx.board.play(FadeIn(point, shift=DOWN * 0.2), weight=0.7)

    zoom = ctx.param("zoom")
    if zoom is not None and plotted:
        target = min(plotted, key=lambda p: abs(p.get_center()[0] - line.line.number_to_point(float(zoom))[0]))
        ctx.board.play(ctx.camera.focus(target, margin=1.1, max_zoom=3.0), weight=1.0,
                       rate_func=rate_functions.ease_in_out_sine)
        ctx.board.play(ctx.highlight.pulse(target), weight=0.5)
    ctx.board.wait(weight=0.4)


@beat("fraction")
def fraction_beat(ctx: BeatContext) -> None:
    """p/q as a symbol plus a bar or pie model of the same quantity.

    Script parameters
    -----------------
    ``p``, ``q``  the numbers (default 3 and 4)
    ``model``     ``bar`` | ``pie`` | ``none``
    ``caption``   line under the models
    """
    p, q = int(ctx.param("p", 3)), int(ctx.param("q", 4))
    viz = FractionVisualizer(ctx.style)
    symbol = viz.symbol(ctx.param("numerator", p), ctx.param("denominator", q), size=ctx.style.size_hero)
    model_kind = str(ctx.param("model", "bar"))
    model = viz.bar_model(p, q) if model_kind == "bar" else (viz.pie_model(p, q) if model_kind == "pie" else VGroup())

    group = VGroup(symbol, model).arrange(RIGHT, buff=1.4) if len(model) else VGroup(symbol)
    group.move_to(ORIGIN)
    caption_text = ctx.param("caption")
    caption = None
    if caption_text:
        caption = ctx.style.label(str(caption_text), color=ctx.palette.ink_dim)
        caption.next_to(group, DOWN, buff=0.7)
    ctx.track(group, caption)

    ctx.board.play(Write(symbol), weight=1.0)
    if len(model):
        ctx.board.play(LaggedStart(*[FadeIn(cell, scale=0.85) for cell in model], lag_ratio=0.12), weight=1.0)
    if caption is not None:
        ctx.board.play(FadeIn(caption, shift=UP * 0.15), weight=0.6)
    ctx.board.play(ctx.highlight.pulse(symbol), weight=0.4)
    ctx.board.wait(weight=0.4)


@beat("equation")
def equation_beat(ctx: BeatContext) -> None:
    """A derivation written line by line, earlier steps dimmed.

    Script parameters
    -----------------
    ``lines``    LaTeX per line (required)
    ``title``    optional heading above the derivation
    ``box``      index of the line to box at the end
    ``box_color`` palette role name for that box
    """
    lines = [str(l) for l in _as_list(ctx.param("lines"))]
    if not lines:
        statement_beat(ctx)
        return

    writer = EquationWriter(ctx.style, lines, size=ctx.param("size", ctx.style.size_body))
    title_text = ctx.param("title")
    group = VGroup(writer)
    title = None
    if title_text:
        title = ctx.style.heading(str(title_text))
        group = VGroup(title, writer).arrange(DOWN, buff=0.62)
    group.move_to(ORIGIN)
    ctx.track(group)

    if title is not None:
        ctx.board.play(Write(title), weight=0.7)
    for step in writer.write_animations():
        ctx.board.play(step, weight=1.0)

    box_index = ctx.param("box")
    if box_index is not None:
        colour = {
            "danger": ctx.palette.danger,
            "success": ctx.palette.success,
            "accent": ctx.palette.accent,
            "highlight": ctx.palette.highlight,
        }.get(str(ctx.param("box_color", "accent")), ctx.palette.accent)
        box = writer.box(int(box_index), color=colour)
        ctx.track(box)
        ctx.remember("last_box", box)
        ctx.board.play(Create(box), weight=0.7)
    ctx.remember("writer", writer)
    ctx.board.wait(weight=0.4)


@beat("contradiction")
def contradiction_beat(ctx: BeatContext) -> None:
    """The punchline of a proof by contradiction: two facts that can't coexist.

    Script parameters
    -----------------
    ``facts``    the two (or more) clashing statements, LaTeX
    ``verdict``  the stamp text (default "CONTRADICTION")
    """
    facts = [str(f) for f in _as_list(ctx.param("facts"))]
    verdict = str(ctx.param("verdict", "CONTRADICTION"))

    rows = VGroup(*[ctx.style.math(f, size=ctx.style.size_heading) for f in facts]).arrange(DOWN, buff=0.62)
    stamp = ctx.style.text(verdict, size=ctx.style.size_title, color=ctx.palette.danger, weight="BOLD")
    # Facts above, verdict below, the whole clash centred on the stage.
    VGroup(rows, stamp).arrange(DOWN, buff=1.05).move_to(ORIGIN) if facts else stamp.move_to(ORIGIN)
    ctx.track(rows, stamp)

    for row in rows:
        ctx.board.play(FadeIn(row, shift=UP * 0.2), weight=0.9)
    boxes = VGroup(*[ctx.highlight.box(row, color=ctx.palette.danger) for row in rows])
    ctx.track(boxes)
    if len(boxes):
        ctx.board.play(LaggedStart(*[Create(b) for b in boxes], lag_ratio=0.3), weight=0.8)
    stamp.rotate(-0.06)
    ctx.board.play(FadeIn(stamp, scale=1.8), weight=0.8)
    ctx.board.play(ctx.highlight.flash(stamp, color=ctx.palette.danger), weight=0.5)
    ctx.board.wait(weight=0.5)


@beat("classify")
def classify_beat(ctx: BeatContext) -> None:
    """Sort values into labelled buckets, one flight per value.

    Script parameters
    -----------------
    ``buckets``  bucket names, e.g. ``["Rational", "Irrational"]``
    ``items``    ``[{"value": "\\pi", "bucket": 1}]``
    """
    buckets = [str(b) for b in _as_list(ctx.param("buckets", ["Rational", "Irrational"]))]
    items = [i if isinstance(i, dict) else {"value": i, "bucket": 0} for i in _as_list(ctx.param("items"))]
    if not items:
        statement_beat(ctx)
        return

    board = ClassifyBoard(ctx.style, buckets, items)
    ctx.track(board)
    for step in board.setup_animations():
        ctx.board.play(step, weight=0.8)
    for step in board.sort_animations():
        ctx.board.play(step, weight=1.0, rate_func=rate_functions.ease_in_out_sine)
    ctx.board.wait(weight=0.4)


@beat("compare")
def compare_beat(ctx: BeatContext) -> None:
    """Two panels side by side.

    Script parameters: ``left``/``right`` titles, ``left_items``/``right_items``.
    """
    panels = ComparePanels(
        ctx.style,
        str(ctx.param("left", "This")),
        str(ctx.param("right", "That")),
        [str(i) for i in _as_list(ctx.param("left_items"))],
        [str(i) for i in _as_list(ctx.param("right_items"))],
    )
    ctx.track(panels)
    for step in panels.reveal_animations():
        ctx.board.play(step, weight=1.0)
    ctx.board.play(ctx.highlight.pulse(panels.right, color=ctx.palette.warning), weight=0.6)
    ctx.board.wait(weight=0.5)


@beat("mistake")
def mistake_beat(ctx: BeatContext) -> None:
    """The common error, struck out, next to the correct version."""
    panel = MistakePanel(
        ctx.style,
        str(ctx.param("wrong", "?")),
        str(ctx.param("right", "?")),
        wrong_note=str(ctx.param("wrong_note", "")),
        right_note=str(ctx.param("right_note", "")),
    )
    ctx.track(panel, panel.strike)
    for step in panel.reveal_animations():
        ctx.board.play(step, weight=1.0)
    ctx.board.play(ctx.highlight.pulse(panel.right, color=ctx.palette.success), weight=0.6)
    ctx.board.wait(weight=0.5)


@beat("practice")
def practice_beat(ctx: BeatContext) -> None:
    """Question on screen, a beat to think, then the answer.

    Script parameters: ``question``, ``answer``, ``hint``.
    """
    question = ctx.style.text(
        str(ctx.param("question") or key_phrase(ctx.block.narration)),
        size=ctx.style.size_title,
        color=ctx.palette.ink,
        weight="BOLD",
    )
    if question.width > 11.0:
        question.set(width=11.0)
    question.move_to(UP * 1.1)
    ctx.track(question)
    ctx.board.play(Write(question), weight=1.2)

    hint = ctx.param("hint")
    if hint:
        hint_text = ctx.style.label(str(hint), color=ctx.palette.ink_dim)
        hint_text.next_to(question, DOWN, buff=0.6)
        ctx.track(hint_text)
        ctx.board.play(FadeIn(hint_text, shift=UP * 0.15), weight=0.7)

    pause = ctx.style.text("pause the video", size=ctx.style.size_label, color=ctx.palette.ink_dim)
    pause.next_to(question, DOWN, buff=1.5)
    ctx.track(pause)
    ctx.board.play(FadeIn(pause), weight=0.5)
    ctx.board.wait(weight=1.0)

    answer_text = ctx.param("answer")
    if answer_text:
        answer = ctx.style.math(str(answer_text), size=ctx.style.size_hero, color=ctx.palette.success)
        answer.next_to(question, DOWN, buff=1.4)
        ctx.track(answer)
        ctx.board.play(AnimationGroup(FadeOut(pause), FadeIn(answer, scale=0.85)), weight=1.0)
        ctx.board.play(ctx.highlight.flash(answer, color=ctx.palette.success), weight=0.5)
    ctx.board.wait(weight=0.4)


@beat("outro")
def outro_beat(ctx: BeatContext) -> None:
    """Closing card: the takeaway, then tomorrow's hook.

    Script parameters: ``takeaway``, ``next_up``, ``cta``.
    """
    palette = ctx.palette
    takeaway = ConceptCard(
        ctx.style,
        str(ctx.param("takeaway") or key_phrase(ctx.block.narration)),
        kicker=str(ctx.param("kicker", "today's takeaway")),
        math=str(ctx.param("math", "")),
        accent=palette.accent,
    )

    # Lay the whole closing card out first, then reveal it piece by piece —
    # nothing moves once it is on screen.
    parts: List[Any] = [takeaway]
    teaser = None
    next_up = ctx.param("next_up")
    if next_up:
        teaser = ctx.style.text(
            f"Day {ctx.day + 1} — {next_up}", size=ctx.style.size_heading, color=palette.highlight, weight="BOLD"
        )
        if teaser.width > 11.0:
            teaser.set(width=11.0)
        parts.append(teaser)
    cta_text = None
    cta = ctx.param("cta")
    if cta:
        cta_text = ctx.style.label(str(cta), color=palette.ink_dim)
        parts.append(cta_text)

    VGroup(*parts).arrange(DOWN, buff=0.95).move_to(UP * 0.35)  # positions the parts
    ctx.track(*parts)

    for step in takeaway.reveal_animations():
        ctx.board.play(step, weight=1.0)
    if teaser is not None:
        ctx.board.play(FadeIn(teaser, shift=UP * 0.25), weight=1.0)
    if cta_text is not None:
        ctx.board.play(FadeIn(cta_text), weight=0.6)
    ctx.board.wait(weight=0.8)


def get_beat(concept: str) -> BeatFn:
    """Look up a beat, falling back to the statement card."""
    return REGISTRY.get(concept, statement_beat)


__all__ = ["BeatContext", "REGISTRY", "beat", "get_beat", "key_phrase"]
