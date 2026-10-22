"""Real Manim renderer verifies the production header uses uploaded art.

Extract actual production TXT/brand_logo/make_header definitions. Never
touch a YouTube upload, state record, or daily production curriculum.
"""
from __future__ import annotations

import ast
from pathlib import Path
import manim
from manim import *

from pipeline.semantic_math import semantic_text
from pipeline.mathtext import latex_to_plain

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "pipeline/cell4_animation.py"
data = ast.parse(path.read_text(encoding="utf8"))
template = next(ast.literal_eval(stmt.value)
                for stmt in data.body if isinstance(stmt, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "MANIM_SCENE_CODE"
                        for target in stmt.targets))
source = ast.parse(template)
methods = {"TXT", "brand_logo", "make_header"}
nodes = [node for node in source.body
         if isinstance(node, ast.FunctionDef) and node.name in methods]
if {x.name for x in nodes} != methods:
    raise RuntimeError("production Manim header/logo function missing")
globals_ = dict(vars(manim))
globals_.update({
    "semantic_text": semantic_text, "latex_to_plain": latex_to_plain,
    "mc": manim.ManimColor, "FONT": "DejaVu Sans",
    "BRAND_LOGO_PATH": ROOT / "remotion/public/branding/math-concepts-made-easy-logo.webp",
    "CHANNEL": "MATH CONCEPTS MADE EASY",
    "TAGLINE": "LEARN  •  PRACTICE  •  MASTER",
    "SCRIPT_DATA": {"title": "Premium Mathematics"},
    "C_GOLD": "#FACC15", "C_NAVY1": "#081B33", "C_WHITE": "#FFFFFF",
    "C_HEADER": "#0A1628", "C_PURPLE": "#8B5CF6",
    "HEADER_TOP": 4.0, "HEADER_BOT": 3.02, "FW": 14.222,
})
exec(compile(ast.Module(body=nodes, type_ignores=[]),
             "<actual-production-brand-header>", "exec"), globals_)
make_header = globals_["make_header"]


class BrandLogoHeaderSmoke(Scene):
    def construct(self):
        self.camera.background_color = "#081B33"
        bar = make_header("Premium Mathematics", day=43)
        self.add(bar)
        self.add(
            Text("VERIFIED MATH SCENE", font="DejaVu Sans",
                 font_size=38, color="#E5E7EB").move_to(DOWN * 0.40)
        )
        self.wait(0.25)
