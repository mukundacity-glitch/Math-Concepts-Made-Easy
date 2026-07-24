"""Procedural intro engine.

``generate_intro(day_number)`` returns a deterministic :class:`IntroPlan` —
motif, backdrop, title entrance, camera path and particle settings — chosen
by a seeded hash of the day number.  Two different days can never get the
same opening, and the same day always renders identically.

``play_intro(...)`` turns that plan into the actual animation, fitted to the
narration budget of the opening block.

Nothing here knows anything about a specific day's content: it receives the
title and subtitle from the script.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, asdict
from typing import Any, List, Optional

import numpy as np
from manim import (
    DOWN,
    LEFT,
    PI,
    RIGHT,
    UP,
    AnimationGroup,
    Circle,
    Create,
    Dot,
    FadeIn,
    FadeOut,
    LaggedStart,
    Line,
    ManimColor,
    Mobject,
    Polygon,
    Scene,
    VGroup,
    Write,
    config,
    rate_functions,
)

from rational_series.visual_library import (
    CameraController,
    GridBackdrop,
    ParticleField,
    Storyboard,
    Style,
    TitleCard,
)

#: Geometric motifs the intro can be built from.  Each is drawn procedurally
#: from the day's palette; adding one here immediately enters the rotation
#: for every future day.
MOTIFS = ("lattice", "orbit", "spiral", "waveform", "tiling", "radial")

#: How the title arrives on screen.
ENTRANCES = ("write", "cascade", "rise", "expand", "unfold")

#: What the camera does while the title is on screen.
CAMERA_PATHS = ("push_in", "pull_back", "drift_left", "drift_right", "settle")

#: Backdrop treatment behind the motif.
BACKDROPS = ("grid", "dots", "void")


def _rng(day: int) -> random.Random:
    digest = hashlib.sha256(f"rational-intro|{day}".encode()).hexdigest()
    return random.Random(digest)


@dataclass(frozen=True)
class IntroPlan:
    """Everything that makes one day's opening unique."""

    day: int
    motif: str
    backdrop: str
    entrance: str
    camera_path: str
    motif_count: int
    motif_scale: float
    motif_rotation: float
    particle_count: int
    particle_speed: float
    build_weight: float
    title_weight: float
    settle_weight: float

    def as_dict(self) -> dict:
        return asdict(self)

    def describe(self) -> str:
        return (
            f"Day {self.day} intro — motif={self.motif} backdrop={self.backdrop} "
            f"entrance={self.entrance} camera={self.camera_path} "
            f"({self.motif_count} elements, {self.particle_count} particles)"
        )


def generate_intro(day_number: int) -> IntroPlan:
    """Deterministically design the opening sequence for a day."""
    rng = _rng(day_number)
    return IntroPlan(
        day=day_number,
        # Rotate the motif list by the day so consecutive days differ, then
        # let the seed break the pattern from time to time.
        motif=MOTIFS[(day_number + rng.randrange(0, len(MOTIFS))) % len(MOTIFS)],
        backdrop=BACKDROPS[(day_number + rng.randrange(0, len(BACKDROPS))) % len(BACKDROPS)],
        entrance=ENTRANCES[(day_number * 2 + rng.randrange(0, len(ENTRANCES))) % len(ENTRANCES)],
        camera_path=CAMERA_PATHS[(day_number + rng.randrange(0, len(CAMERA_PATHS))) % len(CAMERA_PATHS)],
        motif_count=rng.randint(5, 11),
        motif_scale=rng.uniform(0.85, 1.35),
        motif_rotation=rng.uniform(-PI / 5, PI / 5),
        particle_count=rng.randint(35, 90),
        particle_speed=rng.uniform(0.03, 0.11),
        build_weight=rng.uniform(0.8, 1.4),
        title_weight=rng.uniform(1.5, 2.4),
        settle_weight=rng.uniform(0.6, 1.1),
    )


# --------------------------------------------------------------------------
# Motif construction
# --------------------------------------------------------------------------


def _motif_lattice(style: Style, plan: IntroPlan) -> VGroup:
    """Concentric squares, rotated — a nod to the geometry of the series."""
    palette = style.palette
    group = VGroup()
    for i in range(plan.motif_count):
        size = (i + 1) * 0.62 * plan.motif_scale
        colour = palette.cycle(plan.motif_count)[i]
        square = Polygon(
            np.array([-size, -size, 0]),
            np.array([size, -size, 0]),
            np.array([size, size, 0]),
            np.array([-size, size, 0]),
            stroke_color=ManimColor(colour),
            stroke_width=2.2,
            fill_opacity=0.0,
        )
        square.rotate(plan.motif_rotation * (i + 1) * 0.4)
        square.set_stroke(opacity=max(0.08, 0.7 - i * 0.06))
        group.add(square)
    return group


def _motif_orbit(style: Style, plan: IntroPlan) -> VGroup:
    """Rings of dots, like a number system orbiting its origin."""
    palette = style.palette
    group = VGroup()
    colours = palette.cycle(plan.motif_count)
    for i in range(plan.motif_count):
        radius = (i + 1) * 0.55 * plan.motif_scale
        ring = Circle(radius=radius, stroke_color=ManimColor(colours[i]), stroke_width=1.6)
        ring.set_stroke(opacity=max(0.06, 0.45 - i * 0.035))
        group.add(ring)
        count = 3 + i
        for k in range(count):
            angle = plan.motif_rotation + 2 * PI * k / count
            dot = Dot(
                np.array([radius * math.cos(angle), radius * math.sin(angle), 0.0]),
                radius=0.05,
                color=ManimColor(colours[i]),
            ).set_opacity(0.65)
            group.add(dot)
    return group


def _motif_spiral(style: Style, plan: IntroPlan) -> VGroup:
    """A golden spiral of dots — the same golden angle that drives colour."""
    palette = style.palette
    colours = palette.cycle(6)
    group = VGroup()
    total = plan.motif_count * 22
    for i in range(total):
        angle = i * 2.39996323  # golden angle in radians
        radius = 0.13 * math.sqrt(i) * plan.motif_scale * 2.4
        dot = Dot(
            np.array([radius * math.cos(angle), radius * math.sin(angle), 0.0]),
            radius=0.028 + 0.02 * (i / total),
            color=ManimColor(colours[i % len(colours)]),
        )
        dot.set_opacity(0.25 + 0.5 * (i / total))
        group.add(dot)
    return group


def _motif_waveform(style: Style, plan: IntroPlan) -> VGroup:
    """Stacked sine curves — decimals that never settle."""
    palette = style.palette
    colours = palette.cycle(plan.motif_count)
    group = VGroup()
    for i in range(plan.motif_count):
        points = []
        freq = 0.6 + i * 0.28
        amp = 0.32 * plan.motif_scale
        for k in range(121):
            x = -6.5 + 13.0 * k / 120
            y = amp * math.sin(freq * x + plan.motif_rotation * i)
            points.append(np.array([x, y + (i - plan.motif_count / 2) * 0.62, 0.0]))
        curve = VGroup()
        line = Line(points[0], points[1])
        line.set_points_smoothly(points)
        line.set_stroke(color=ManimColor(colours[i]), width=2.0, opacity=max(0.08, 0.55 - i * 0.04))
        line.set_fill(opacity=0.0)
        curve.add(line)
        group.add(curve)
    return group


def _motif_tiling(style: Style, plan: IntroPlan) -> VGroup:
    """A diagonal-split tiling — squares cut by their diagonals."""
    palette = style.palette
    colours = palette.cycle(4)
    group = VGroup()
    cell = 1.15 * plan.motif_scale
    cols = int(config.frame_width / cell) + 2
    rows = int(config.frame_height / cell) + 2
    rng = random.Random(f"tiling-{plan.day}")
    for r in range(rows):
        for c in range(cols):
            x = -cols * cell / 2 + c * cell + cell / 2
            y = -rows * cell / 2 + r * cell + cell / 2
            flip = rng.random() < 0.5
            a = np.array([x - cell / 2, y - cell / 2, 0.0])
            b = np.array([x + cell / 2, y + cell / 2, 0.0])
            if flip:
                a = np.array([x - cell / 2, y + cell / 2, 0.0])
                b = np.array([x + cell / 2, y - cell / 2, 0.0])
            line = Line(a, b, stroke_width=1.6, color=ManimColor(colours[(r + c) % len(colours)]))
            line.set_stroke(opacity=rng.uniform(0.08, 0.3))
            group.add(line)
    return group


def _motif_radial(style: Style, plan: IntroPlan) -> VGroup:
    """Spokes radiating from the centre, unequal lengths — irrationality."""
    palette = style.palette
    colours = palette.cycle(plan.motif_count)
    rng = random.Random(f"radial-{plan.day}")
    group = VGroup()
    spokes = plan.motif_count * 6
    for i in range(spokes):
        angle = plan.motif_rotation + 2 * PI * i / spokes
        length = (2.2 + rng.uniform(0.0, 3.4)) * plan.motif_scale
        start = np.array([math.cos(angle), math.sin(angle), 0.0]) * 0.9
        end = np.array([math.cos(angle), math.sin(angle), 0.0]) * length
        line = Line(start, end, stroke_width=1.8, color=ManimColor(colours[i % len(colours)]))
        line.set_stroke(opacity=rng.uniform(0.1, 0.4))
        group.add(line)
    return group


_MOTIF_BUILDERS = {
    "lattice": _motif_lattice,
    "orbit": _motif_orbit,
    "spiral": _motif_spiral,
    "waveform": _motif_waveform,
    "tiling": _motif_tiling,
    "radial": _motif_radial,
}


def build_motif(style: Style, plan: IntroPlan) -> VGroup:
    """Construct the plan's motif as a mobject (centred, un-animated)."""
    motif = _MOTIF_BUILDERS[plan.motif](style, plan)
    motif.set_z_index(-5)
    return motif


def build_backdrop(style: Style, plan: IntroPlan) -> Optional[Mobject]:
    if plan.backdrop == "grid":
        return GridBackdrop(style, spacing=1.0, opacity=0.10)
    if plan.backdrop == "dots":
        return GridBackdrop(style, spacing=0.62, opacity=0.09, dots=True)
    return None


# --------------------------------------------------------------------------
# Title entrances
# --------------------------------------------------------------------------


def _entrance_animations(card: TitleCard, entrance: str) -> List[Any]:
    """Animations that bring the title card in, per entrance style."""
    parts = [part for part in card.submobjects]
    if entrance == "write":
        return [
            AnimationGroup(FadeIn(card.day_label, shift=DOWN * 0.2), Write(card.title), lag_ratio=0.35),
            AnimationGroup(Create(card.rule), *[FadeIn(p) for p in parts[3:]], lag_ratio=0.3),
        ]
    if entrance == "cascade":
        letters = card.title
        return [
            LaggedStart(*[FadeIn(m, shift=UP * 0.3) for m in letters], lag_ratio=0.06),
            LaggedStart(FadeIn(card.day_label), Create(card.rule), *[FadeIn(p) for p in parts[3:]], lag_ratio=0.3),
        ]
    if entrance == "rise":
        card.save_state()
        card.shift(DOWN * 0.9).set_opacity(0.0)
        from manim import Restore

        return [Restore(card, rate_func=rate_functions.ease_out_cubic)]
    if entrance == "expand":
        card.save_state()
        card.scale(0.72).set_opacity(0.0)
        from manim import Restore

        return [Restore(card, rate_func=rate_functions.ease_out_back)]
    # "unfold": rule sweeps open, text arrives from both sides
    card.day_label.save_state()
    card.title.save_state()
    card.day_label.shift(LEFT * 1.2).set_opacity(0.0)
    card.title.shift(RIGHT * 1.2).set_opacity(0.0)
    from manim import Restore

    return [
        Create(card.rule),
        AnimationGroup(Restore(card.day_label), Restore(card.title), *[FadeIn(p) for p in parts[3:]], lag_ratio=0.2),
    ]


def _camera_animation(camera: CameraController, path: str):
    if path == "push_in":
        return camera.push_in(0.86)
    if path == "pull_back":
        return camera.pull_back(1.12)
    if path == "drift_left":
        return camera.drift(LEFT * 0.6)
    if path == "drift_right":
        return camera.drift(RIGHT * 0.6)
    return None


# --------------------------------------------------------------------------
# Playback
# --------------------------------------------------------------------------


def play_intro(
    scene: Scene,
    plan: IntroPlan,
    style: Style,
    *,
    title: str,
    subtitle: str = "",
    budget: float,
    camera: Optional[CameraController] = None,
) -> VGroup:
    """Play the day's opening inside ``budget`` seconds.

    Returns the mobjects that were left on screen so the caller can clear
    them when the first teaching beat starts.
    """
    camera = camera or CameraController(scene)

    backdrop = build_backdrop(style, plan)
    motif = build_motif(style, plan)
    particles = ParticleField(style, count=plan.particle_count, seed=plan.day, speed=plan.particle_speed)
    card = TitleCard(style, plan.day, title, subtitle)

    stage = VGroup(*[m for m in (backdrop, motif, particles) if m is not None])

    board = Storyboard(scene, budget)
    if backdrop is not None:
        board.play(FadeIn(backdrop), weight=0.5)
    board.play(
        LaggedStart(*[Create(part) for part in motif.submobjects], lag_ratio=min(0.9 / max(len(motif), 1), 0.08)),
        weight=plan.build_weight,
    )
    board.call(lambda: (scene.add(particles), particles.start()))
    board.play(FadeIn(particles), weight=0.4)

    # The motif recedes so the title owns the frame.
    board.play(motif.animate.set_opacity(0.28).scale(1.08), weight=0.5)
    for step in _entrance_animations(card, plan.entrance):
        board.play(step, weight=plan.title_weight / 2.0)

    move = _camera_animation(camera, plan.camera_path)
    if move is not None:
        board.play(move, weight=plan.settle_weight, rate_func=rate_functions.ease_in_out_sine)
    else:
        board.wait(weight=plan.settle_weight)

    board.run()

    stage.add(card)
    return stage


def clear_intro(scene: Scene, stage: VGroup, camera: CameraController, *, run_time: float = 0.9) -> None:
    """Dissolve the intro and return the camera home."""
    for mob in stage.submobjects:
        mob.clear_updaters()
    scene.play(
        AnimationGroup(*[FadeOut(m) for m in stage.submobjects], lag_ratio=0.08),
        camera.reset(),
        run_time=run_time,
    )
    scene.remove(stage)


__all__ = [
    "BACKDROPS",
    "CAMERA_PATHS",
    "ENTRANCES",
    "IntroPlan",
    "MOTIFS",
    "build_motif",
    "clear_intro",
    "generate_intro",
    "play_intro",
]
