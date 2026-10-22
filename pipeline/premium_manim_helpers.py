"""Premium Manim board renderer: full item pagination and strict timed reveals.

This module is imported only by opt-in Manim scenes, so baseline pytest
does not require Manim. Motion uses validated question-state transitions;
it never synthesizes mathematics from decoration or unverified prose.
"""
from __future__ import annotations

from pathlib import Path
import textwrap

from pipeline.mathtext import latex_to_plain, normalize_word


def _anchor_time(narrator, phrase: str) -> float:
    """Require real per-word timestamps, never estimate premium cue placement."""
    tokens = [normalize_word(w) for w in phrase.split()]
    tokens = [t for t in tokens if t]
    if not narrator.words:
        raise ValueError("premium renderer requires real narration word boundaries")
    if not tokens:
        raise ValueError("empty premium audio marker")
    # Prefer whole cue; use the same constrained prefix convention as EdgeTTS.
    index = narrator._find(tokens)
    if index is None:
        raise ValueError(f"premium narration marker absent from audio: {phrase}")
    narrator.cursor = index + len(tokens)
    return float(narrator.words[index]["start"])


def _wait_for(scene, when: float, lead: float = 0.20) -> None:
    now = float(scene.renderer.time)
    remaining = when - lead - now
    if remaining > 0.02:
        scene.wait(remaining)
    if when < now - 0.65:
        raise ValueError(
            f"premium animation ran behind speech: cue {when:.2f}s, visual clock {now:.2f}s"
        )


def _text(value, size, color, *, max_width=11.4, max_height=None, wrap=62, bold=False):
    from manim import Text
    readable = latex_to_plain(value)
    readable = textwrap.fill(readable, width=wrap, break_long_words=False,
                             break_on_hyphens=False)
    obj = Text(readable or " ", font="DejaVu Sans", font_size=size,
               weight="BOLD" if bold else "NORMAL", color=color)
    if obj.width > max_width:
        obj.scale_to_fit_width(max_width)
    if max_height is not None and obj.height > max_height:
        obj.scale_to_fit_height(max_height)
    return obj


def render_premium_board(scene, stage: str, sd: dict, nar, audio_dir: Path) -> None:
    from manim import (
        Create, DOWN, FadeIn, FadeOut, GREEN, LEFT, RIGHT, RoundedRectangle,
        SurroundingRectangle, Text, TransformMatchingShapes, UP, VGroup, WHITE,
    )
    if stage not in ("worked_example", "practice"):
        raise ValueError(f"unsupported premium board stage: {stage}")
    expected_audio = Path(audio_dir) / f"scene_{sd['scene_id']:02d}.mp3"
    if not expected_audio.is_file() or expected_audio.stat().st_size == 0:
        raise ValueError("premium scene requires generated narration audio")
    items = sd.get("premium_items", [])
    min_count = 10 if stage == "worked_example" else 15
    if len(items) < min_count:
        raise ValueError(f"{stage} renderer received fewer than {min_count} items")
    if not nar.words:
        raise ValueError("premium Manim scene requires timestamped narration")

    gold, cyan, pale, green = "#FACC15", "#22D3EE", "#E5E7EB", "#22C55E"
    border = cyan if stage == "worked_example" else "#F59E0B"
    title = "VERIFIED WORKED EXAMPLES" if stage == "worked_example" else "YOUR TURN: PRACTICE"
    board = RoundedRectangle(width=12.8, height=5.55, corner_radius=0.22,
                             fill_color="#0D2045", fill_opacity=0.94,
                             stroke_color=border, stroke_width=2.0)
    board.move_to(DOWN * 0.22)
    heading = _text(title, 27, gold, bold=True, max_width=10.5, wrap=70)
    heading.move_to(board.get_top() + DOWN * 0.40)
    scene.play(FadeIn(board), FadeIn(heading), run_time=0.30)

    previous = VGroup()
    displayed_ids = []
    for index, item in enumerate(items, 1):
        when = _anchor_time(nar, item["cue"])
        _wait_for(scene, when)
        if len(previous):
            scene.play(FadeOut(previous), run_time=0.14)
        progress = _text(f"{index} / {len(items)}    {item['difficulty'].upper()}",
                         20, border, bold=True, max_width=9)
        progress.move_to(board.get_top() + DOWN * 0.87)
        question = _text(item["prompt"], 27, WHITE, max_width=11.6,
                         max_height=1.15, wrap=67, bold=True)
        question.move_to(board.get_center() + UP * 1.05)
        scene.play(FadeIn(progress), FadeIn(question, shift=RIGHT * 0.12),
                   run_time=0.24)
        page = VGroup(progress, question)
        previous_math = None
        previous_explanation = None
        for step in item["steps"]:
            cue_time = _anchor_time(nar, step["anchor"])
            _wait_for(scene, cue_time)
            explanation = _text(step["explanation"], 24, pale,
                                max_width=11.5, max_height=0.85, wrap=72)
            explanation.move_to(board.get_center() + DOWN * 0.05)
            math = _text(step["math"], 38, cyan, max_width=11.2,
                         max_height=0.9, wrap=60, bold=True)
            math.move_to(board.get_center() + DOWN * 1.08)
            animations = [FadeIn(explanation)]
            if previous_explanation is not None:
                animations.append(FadeOut(previous_explanation))
            if previous_math is None:
                animations.append(FadeIn(math))
                scene.play(*animations, run_time=0.30)
                previous_math = math
            else:
                # A real mathematical transformation retains the equation as
                # one persistent visual object instead of flashing slides.
                scene.play(*animations, run_time=0.15)
                scene.play(TransformMatchingShapes(previous_math, math),
                           run_time=0.24)
                previous_math = math
            previous_explanation = explanation
        answer_time = _anchor_time(nar, item["answer_anchor"])
        _wait_for(scene, answer_time)
        answer = _text(f"Verified answer: {item['answer']}", 26, green,
                       max_width=10.6, max_height=0.55, wrap=66, bold=True)
        answer.move_to(board.get_bottom() + UP * 0.43)
        frame = SurroundingRectangle(answer, color=green, buff=0.11,
                                      stroke_width=1.7)
        scene.play(FadeIn(answer), Create(frame), run_time=0.26)
        page.add(answer, frame)
        if previous_explanation is not None:
            page.add(previous_explanation)
        if previous_math is not None:
            page.add(previous_math)
        previous = page
        displayed_ids.append(item["id"])
    if len(displayed_ids) != len(set(displayed_ids)) or len(displayed_ids) != len(items):
        raise ValueError("premium visual renderer omitted or repeated question IDs")
    if float(scene.renderer.time) > nar.duration + 1.2:
        raise ValueError("premium visual animations overrun narrated scene length")
    remaining = nar.duration - float(scene.renderer.time) - 0.05
    if remaining > 0.01:
        scene.wait(remaining)


def computed_geometry_visual(model: dict):
    """Draw true computed triangle/circle metrics, not decorative motifs."""
    from manim import (
        Circle, DashedLine, Dot, DOWN, LEFT, Line, Polygon, RIGHT, Square,
        Text, UP, VGroup,
    )
    if not isinstance(model, dict):
        return None
    kind = model.get("kind")
    cyan, gold, green = "#22D3EE", "#FACC15", "#22C55E"
    if kind == "right_triangle":
        a, b = model["legs"]["a"], model["legs"]["b"]
        scale = 3.1 / max(a, b)
        origin = LEFT * 1.45 + DOWN * 1.20
        pa = origin + RIGHT * a * scale
        pb = origin + UP * b * scale
        shape = Polygon(origin, pa, pb, stroke_color=cyan, stroke_width=4,
                        fill_color=cyan, fill_opacity=0.12)
        marker = Square(side_length=min(0.34, a * scale / 4, b * scale / 4),
                        stroke_color=gold, stroke_width=2)
        marker.move_to(origin + RIGHT * marker.width/2 + UP * marker.height/2)
        la = Text(f"a = {a:g}", font_size=22, color=gold)
        lb = Text(f"b = {b:g}", font_size=22, color=gold)
        lc = Text(f"c = {model['hypotenuse']:.3g}", font_size=22, color=green)
        la.move_to((origin + pa) / 2 + DOWN*0.36)
        lb.move_to((origin + pb) / 2 + LEFT*0.57)
        lc.move_to((pa + pb) / 2 + RIGHT*0.48 + UP*0.19)
        group = VGroup(shape, marker, la, lb, lc)
        return group
    if kind == "circle":
        radius = float(model["radius"])
        display_r = 1.38
        shape = Circle(radius=display_r, stroke_color=cyan, stroke_width=4,
                       fill_color=cyan, fill_opacity=0.09)
        spoke = Line(shape.get_center(), shape.get_center() + RIGHT*display_r,
                     color=gold, stroke_width=4)
        marker = Dot(spoke.get_end(), color=gold, radius=0.055)
        labels = [
            Text(f"r = {radius:g}", font_size=23, color=gold),
            Text(f"Area = {model['area']:.3g}", font_size=23, color=green),
            Text(f"Circumference = {model['circumference']:.3g}",
                 font_size=22, color=green),
        ]
        labels[0].next_to(spoke, UP, buff=0.1)
        labels[1].next_to(shape, DOWN, buff=0.32)
        labels[2].next_to(labels[1], DOWN, buff=0.13)
        return VGroup(shape, spoke, marker, *labels)
    return None
