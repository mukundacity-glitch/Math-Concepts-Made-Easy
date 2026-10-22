"""System-wide mathematical typography: no per-lesson character-color table."""
from __future__ import annotations

import ast
import re
from html import unescape
from pathlib import Path
import pytest

from pipeline.semantic_math import (
    MATH_PALETTE, is_mathematical, markup_for_math, tokenize_math,
)

ROOT = Path(__file__).resolve().parents[1]


def _roles(expr, mode="math"):
    return [(span.text, span.role) for span in tokenize_math(expr, mode=mode)]


@pytest.mark.parametrize("input_text,expected", [
    ("x + 2 = 5", [("x", "variable"), ("+", "operator"),
                    ("2", "number"), ("=", "relation"), ("5", "number")]),
    ("2x + 3x = 5x", [("2", "number"), ("x", "variable"),
                      ("+", "operator"), ("3", "number"),
                      ("x", "variable"), ("=", "relation")]),
    ("x² + 4x + 4 = 0", [("x", "variable"), ("²", "exponent"),
                         ("+", "operator"), ("4", "number")]),
    ("a² + b² = c²", [("a", "variable"), ("²", "exponent"),
                       ("b", "variable"), ("=", "relation")]),
    ("(x + 3)(x - 2) = 0", [("(", "group"), (")", "group"),
                            ("-", "operator"), ("=", "relation")]),
    ("x + -3 = 5", [("+", "operator"), ("-", "operator"),
                     ("3", "number"), ("=", "relation")]),
    ("sin(x) + log(2) = 0", [("sin", "function"),
                             ("log", "function"), ("x", "variable")]),
    ("4.25 ÷ (x - 2) ≤ 7", [("4.25", "number"),
                             ("÷", "operator"), ("≤", "relation")]),
    (r"\tfrac{3}{4} \neq x^2", [("3", "number"), ("/", "operator"),
                                   ("4", "number"), ("≠", "relation"),
                                   ("²", "exponent")]),
])
def test_expression_roles_are_formula_generic(input_text, expected):
    roles = _roles(input_text)
    for token in expected:
        assert token in roles, (input_text, token, roles)


@pytest.mark.parametrize("s", [
    "x+2=4", "x + -3", "x - 2", "x²", "2x", "a^3", "7÷2", "b≥a",
])
def test_auto_detects_math_not_just_hardcoded_x(s):
    assert is_mathematical(s), s


@pytest.mark.parametrize("s", [
    "DAY 43", "Algebra foundations", "Mathematics - Made Easy",
    "3 students today", "WELCOME TO THE LESSON", "Grade 9",
    "Read 2 pages", "2026-10-22", "Keep your progress",
])
def test_auto_does_not_color_ordinary_titles_and_hyphens(s):
    assert not is_mathematical(s), s
    assert {sp.role for sp in tokenize_math(s, mode="auto")} == {"text"}


def test_force_math_for_isolated_variables_and_labels():
    assert ("x", "variable") in _roles("x")
    assert ("θ", "variable") in _roles("θ")
    assert ("x", "text") in _roles("x", "auto")
    assert ("x", "text") in _roles("x + 2", "prose")


def test_complete_display_string_is_preserved_with_correct_offsets():
    expression = "(x + -3)(x - 2) = 0"
    spans = tokenize_math(expression)
    display = "".join(sp.text for sp in spans)
    assert display == expression
    for span in spans:
        assert display[span.start:span.end] == span.text


def test_safe_pango_markup_does_not_inject_tags():
    value = "<span foreground='red'>x + 2</span> = 5 & 7"
    markup = markup_for_math(value, mode="math")
    # The '<' token is independently wrapped and escaped, so markup
    # must contain the entity but not a forged embedded tag.
    assert "&lt;" in markup
    assert "&amp;" in markup
    assert "<span foreground='red'>" not in markup
    assert "foreground=" in markup


def test_palette_roles_are_distinct_and_readable_on_navy():
    values = list(MATH_PALETTE.values())
    assert len(values) == len(set(values))
    assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", color) for color in values)
    # WCAG relative luminance contrast on the '#0D2045' cards.
    def luminance(hex_color):
        rgb = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4
                  for v in rgb]
        return sum(a*b for a, b in zip(linear, (0.2126, 0.7152, 0.0722)))
    background = luminance("#0D2045")
    for role, color in MATH_PALETTE.items():
        light, dark = sorted((background, luminance(color)), reverse=True)
        assert (light + 0.05) / (dark + 0.05) >= 4.5, (role, color)


def test_any_palette_override_must_be_known_and_hex():
    with pytest.raises(ValueError, match="invalid semantic"):
        markup_for_math("x+2", mode="math", palette={"x": "red"})
    with pytest.raises(ValueError, match="invalid semantic"):
        markup_for_math("x+2", mode="math", palette={"variable": "red"})


def test_markup_uses_same_palette_without_math_injection_in_prose():
    markup = markup_for_math("2x + 3 = 7", mode="math")
    for role in ("variable", "number", "operator", "relation"):
        assert f'foreground="{MATH_PALETTE[role]}"' in markup
    heading = markup_for_math("DAY 43", mode="auto", base_color="#123456")
    assert MATH_PALETTE["number"] not in heading
    assert '#123456' in heading


def test_premium_board_and_universal_manim_factory_share_one_engine():
    helper = (ROOT / "pipeline/premium_manim_helpers.py").read_text()
    engine = (ROOT / "pipeline/cell4_animation.py").read_text()
    assert "from pipeline.semantic_math import semantic_text" in helper
    assert 'math_mode="math"' in helper
    assert 'mode="auto"' in engine
    assert 'mode="math"' in engine
    assert "from pipeline.semantic_math import semantic_text" in engine
    # Formula, concept graph equation, legacy board, mistakes and recap
    # all use the central TXT/MATH factories in the production scene code.
    tree = ast.parse(engine)
    template = next(
        ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "MANIM_SCENE_CODE" for t in n.targets)
    )
    for part in ("Scene03_Concept", "Scene05_Formula", "Scene06_WorkedExample",
                 "Scene07_Mistakes", "Scene08_Practice", "Scene09_Summary"):
        assert part in template
    assert "semantic_text(" in template


def test_prose_preserves_neutral_role_on_nonmath_label():
    tokens = tokenize_math("The lesson starts here", mode="auto")
    assert all(s.role == "text" for s in tokens)


def test_roles_unchanged_across_equation_transformations():
    transformations = ["3*x+5=20", "3*x=15", "x=5"]
    for expression in transformations:
        spans = tokenize_math(expression, mode="math")
        assert any(s.role == "variable" for s in spans)
        assert any(s.role == "relation" for s in spans)
        assert any(s.role == "number" for s in spans)
        assert all(s.role != "text" for s in spans if s.text.strip())
