"""Isolated real-Manim smoke scene for phase-1 computed quadratic rendering.

Extracts the *actual* text/curve renderer helpers from cell4's embedded Manim
template, without launching the 9-stage production pipeline or touching
publishing credentials/progress.
"""
from __future__ import annotations

import ast
from pathlib import Path
import textwrap

import manim
from manim import *
from pipeline.math_models import build_computed_model, validate_computed_model
from pipeline.semantic_math import semantic_text
from pipeline.mathtext import latex_to_plain

ENGINE = Path(__file__).resolve().parents[1] / "pipeline" / "cell4_animation.py"
tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
embedded = next(
    ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "MANIM_SCENE_CODE"
            for target in node.targets)
)
source = ast.parse(embedded)
function_nodes = [
    node for node in source.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {"TXT", "MATH", "computed_concept_visual"}
]
if len(function_nodes) != 3:
    raise RuntimeError("production Manim text/graph helpers missing")
globals_for_helpers = dict(vars(manim))
globals_for_helpers.update({
    "latex_to_plain": latex_to_plain,
    "semantic_text": semantic_text,
    "textwrap": textwrap,
    "FONT": "DejaVu Sans",
    "C_WHITE": "#FFFFFF",
    "C_LGRAY": "#E5E7EB",
    "C_CYAN": "#22D3EE",
    "C_GOLD": "#FACC15",
    "C_GGREEN": "#22C55E",
    "mc": manim.ManimColor,
})
exec(compile(ast.Module(body=function_nodes, type_ignores=[]),
             "<production-Manim-helpers>", "exec"), globals_for_helpers)
computed_concept_visual = globals_for_helpers["computed_concept_visual"]


class Phase1QuadraticSmoke(Scene):
    """Manim frames genuinely depend on exact quadratic coefficients."""

    def construct(self):
        self.camera.background_color = "#081B33"
        model = build_computed_model({
            "kind": "quadratic_function",
            "coefficients": {"a": "1", "b": "-3", "c": "2"},
            "domain": [-2, 4],
            "samples": 101,
        })
        validate_computed_model(model)
        heading = Text("QUADRATIC FUNCTIONS", font_size=28, color="#FACC15")
        heading.to_edge(UP, buff=0.40)
        self.add(heading)
        self.wait(0.45)
        diagram = computed_concept_visual(model)
        if diagram is None:
            raise RuntimeError("quadratic graph renderer unexpectedly returned None")
        diagram.scale_to_fit_height(4.45)
        diagram.move_to(DOWN * 0.10)
        # Exact same Create animation used by the opt-in concept scene.
        self.play(Create(diagram), run_time=2.7)
        self.wait(0.5)



class SemanticMathColorsSmoke(Scene):
    """Actual Pango render: variable/number/operator/equality/power roles."""

    def construct(self):
        from pipeline.semantic_math import semantic_text
        self.camera.background_color = "#081B33"
        title = Text("THE SAME COLORS IN EVERY EQUATION",
                     font="DejaVu Sans", font_size=29, color="#E5E7EB")
        title.to_edge(UP, buff=0.42)
        expressions = [
            "x + 2 = 5",
            "2x + 3x = 5x",
            "x² + 4x + 4 = 0",
            "a² + b² = c²",
            "(x + 3)(x - 2) = 0",
        ]
        board = VGroup(*[
            semantic_text(item, size=40, mode="math", max_width=10.9,
                          bold=True)
            for item in expressions
        ]).arrange(DOWN, buff=0.24)
        board.move_to(DOWN * 0.12)
        self.add(title, board)
        self.wait(1.2)
