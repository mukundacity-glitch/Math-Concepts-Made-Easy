"""Real Manim integration: four contexts use the production math factories.

This renders production worked/practice row builders, a computed
concept-equation label and an actual color-certified vector equation morph.
The preview uses no YouTube credentials, curriculum mutations or uploads.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import manim
from manim import (
    DOWN, FadeIn, LEFT, RIGHT, Scene, Text, UP, VGroup, config,
)

from pipeline.semantic_math import semantic_equation_transform, semantic_text
from pipeline.mathtext import latex_to_plain

ENGINE = Path(__file__).resolve().parents[1] / "pipeline" / "cell4_animation.py"
tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
template = next(
    ast.literal_eval(node.value) for node in tree.body
    if isinstance(node, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "MANIM_SCENE_CODE"
        for t in node.targets
    )
)
sources = ast.parse(template)
functions = {
    "TXT", "MATH", "build_board_rows", "number_chip", "split_verdict",
    "verdict_pill",
}
nodes = [
    node for node in sources.body
    if isinstance(node, ast.FunctionDef) and node.name in functions
]
if {node.name for node in nodes} != functions:
    raise RuntimeError("one or more production scene math factories missing")

globals_ = dict(vars(manim))
globals_.update({
    "semantic_text": semantic_text,
    "latex_to_plain": latex_to_plain,
    "re": re,
    "_VERDICT_RE": re.compile(r"\b(Yes|No|Undefined)\b[!.]?\s*$", re.I),
    "mc": manim.ManimColor,
    "FONT": "DejaVu Sans",
    "C_WHITE": "#E5E7EB", "C_GOLD": "#FDE68A",
    "C_GGREEN": "#4ADE80", "C_RRED": "#FB7185",
    "C_BLUE_P": "#38BDF8",
})
exec(compile(ast.Module(body=nodes, type_ignores=[]),
             "<verified-production-Manim-math-factories>", "exec"), globals_)

TXT = globals_["TXT"]
MATH = globals_["MATH"]
build_board_rows = globals_["build_board_rows"]

config.background_color = "#081B33"


def section(heading, obj, x, y):
    title = Text(heading, font="DejaVu Sans", font_size=22, color="#E5E7EB")
    obj.scale_to_fit_width(5.5) if obj.width > 5.5 else None
    content = VGroup(title, obj).arrange(DOWN, buff=0.24)
    content.move_to(x * RIGHT + y * UP)
    return content


class SemanticFourSceneContextsSmoke(Scene):
    def construct(self):
        worked = build_board_rows([
            "Ex 1: 2x + 3x = 5x", "x + -3 = 5"
        ], max_w=5.6)
        practice = build_board_rows([
            "Ex 1: (x + 3)(x - 2) = 0", "x = 2"
        ], max_w=5.6)
        work_obj = VGroup(*[row for row, _ in worked]).arrange(
            DOWN, aligned_edge=LEFT, buff=0.18
        )
        practice_obj = VGroup(*[row for row, _ in practice]).arrange(
            DOWN, aligned_edge=LEFT, buff=0.18
        )
        concept = MATH("y = x² - 3x + 2", size=34, color="#E5E7EB",
                       max_w=5.45)
        initial = semantic_text("2x + 3x = 5x", size=32, mode="math",
                                bold=True, max_width=5.45)
        final = semantic_text("5x = 5x", size=32, mode="math",
                              bold=True, max_width=5.45)

        cards = [
            section("WORKED EXAMPLE", work_obj, -3.35, 1.65),
            section("PRACTICE BOARD", practice_obj, 3.35, 1.65),
            section("CONCEPT EQUATION", concept, -3.35, -1.55),
        ]
        for item in cards:
            self.add(item)
        transform_heading = Text("EQUATION TRANSFORMATION",
                                 font="DejaVu Sans", font_size=22,
                                 color="#E5E7EB")
        transform_heading.move_to(3.35 * RIGHT + -1.00 * UP)
        initial.move_to(3.35 * RIGHT + -1.67 * UP)
        final.move_to(initial.get_center())
        self.add(transform_heading, initial)
        self.wait(0.25)
        semantic_equation_transform(self, initial, final, run_time=0.65)
        self.wait(0.35)
