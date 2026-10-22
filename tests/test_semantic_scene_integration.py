"""Phase 3 Step 2: exact color preservation across the four teaching contexts."""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline.semantic_math import (
    MATH_PALETTE, semantic_equation_transform, semantic_text,
)

ROOT = Path(__file__).resolve().parents[1]


class DummyText:
    def __init__(self, value, **options):
        self.value = value
        self.options = options
        self.width, self.height = 4.2, 0.6

    def scale_to_fit_width(self, width):
        self.width = width

    def scale_to_fit_height(self, height):
        self.height = height


class FakeScene:
    def __init__(self):
        self.calls = []

    def play(self, animation, *, run_time):
        self.calls.append((animation, run_time))


@pytest.fixture
def stub_manim(monkeypatch):
    monkeypatch.setitem(sys.modules, "manim", SimpleNamespace(
        MarkupText=DummyText,
        Text=DummyText,
        TransformMatchingShapes=lambda source, target: (source, target),
    ))


def test_actual_render_objects_have_math_role_certificates(stub_manim):
    equation = semantic_text("x² + 4x + 4 = 0", mode="math")
    assert set(equation.semantic_math_roles) >= {
        "variable", "exponent", "operator", "number", "relation"
    }
    for role, color in equation.semantic_math_colors.items():
        assert color == MATH_PALETTE[role]
    assert equation.semantic_math_display == "x² + 4x + 4 = 0"


def test_transition_keeps_single_palette_across_different_equation_states(stub_manim):
    scene = FakeScene()
    start = semantic_text("2x + 3x = 5x", mode="math")
    end = semantic_text("5x = 5x", mode="math")
    result = semantic_equation_transform(scene, start, end, run_time=0.35)
    assert result is end
    assert scene.calls == [((start, end), 0.35)]
    for role in set(start.semantic_math_roles) & set(end.semantic_math_roles):
        assert start.semantic_math_colors[role] == end.semantic_math_colors[role]
    assert start.semantic_math_colors["operator"] == MATH_PALETTE["operator"]


def test_transition_refuses_uncolored_content_and_palette_drift(stub_manim):
    scene = FakeScene()
    colored = semantic_text("x + 1 = 4", mode="math")
    prose = semantic_text("HELLO STUDENTS", mode="prose")
    with pytest.raises(ValueError, match="semantically colored"):
        semantic_equation_transform(scene, prose, colored)
    corrupted = semantic_text("x + 2 = 5", mode="math")
    corrupted.semantic_math_colors["operator"] = "#000000"
    with pytest.raises(ValueError, match="inconsistent role colors"):
        semantic_equation_transform(scene, colored, corrupted)
    assert scene.calls == []


@pytest.mark.parametrize("duration", [0, -1, 16])
def test_transition_rejects_invalid_timing(stub_manim, duration):
    scene = FakeScene()
    a = semantic_text("x + 1 = 4", mode="math")
    b = semantic_text("x = 3", mode="math")
    with pytest.raises(ValueError, match="duration"):
        semantic_equation_transform(scene, a, b, run_time=duration)


def test_production_legacy_and_premium_scene_paths_explicitly_apply_colors():
    engine = (ROOT / "pipeline/cell4_animation.py").read_text()
    helper = (ROOT / "pipeline/premium_manim_helpers.py").read_text()
    compiled = ast.parse(engine)
    embedded = next(
        ast.literal_eval(stmt.value) for stmt in compiled.body
        if isinstance(stmt, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "MANIM_SCENE_CODE"
            for target in stmt.targets
        )
    )
    assert 'label = MATH(model["equation"]' in embedded
    assert 'def TXT(s, size=28' in embedded
    assert 'math_mode="auto"' in embedded
    assert 'mode=math_mode' in embedded
    for stage in ("Scene03_Concept", "Scene06_WorkedExample", "Scene08_Practice"):
        assert stage in embedded
    assert 'question = _text(item["prompt"]' in helper
    assert 'math_mode="math"' in helper
    assert 'semantic_equation_transform(scene, previous_math, math' in helper


def test_visual_smoke_imports_original_production_row_and_formula_builders():
    smoke = (ROOT / "tests/smoke_render_semantic_contexts.py").read_text()
    for name in ("build_board_rows", "MATH", "TXT", "semantic_equation_transform",
                 "SemanticFourSceneContextsSmoke"):
        assert name in smoke
