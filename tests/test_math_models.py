"""Computed mathematical visuals: accuracy, corruption, and opt-in coverage."""

import copy

import pytest

from pipeline.math_models import build_computed_model, validate_computed_model
from pipeline.lesson_plan import plan_lesson
from pipeline.scene_manifest import build_scene_manifest
from pipeline.lesson_qa import build_coverage_report


def _quadratic(a=1, b=-3, c=2):
    return {
        "kind": "quadratic_function",
        "coefficients": {"a": a, "b": b, "c": c},
        "domain": [-2, 4],
        "samples": 41,
    }


def test_quadratic_graph_and_roots_derive_from_coefficients():
    model = build_computed_model(_quadratic())
    assert model["equation"] == "y = x² - 3x + 2"
    assert model["vertex"]["x"] == pytest.approx(1.5)
    assert model["vertex"]["y"] == pytest.approx(-0.25)
    assert [p["x"] for p in model["x_intercepts"]] == pytest.approx([1, 2])
    assert model["y_intercept"]["y"] == pytest.approx(2)
    assert model["discriminant"] == pytest.approx(1)
    assert len(model["curve"]) == 41
    for point in model["curve"]:
        assert point["y"] == pytest.approx(point["x"] ** 2 - 3 * point["x"] + 2)
    validate_computed_model(model)


def test_model_supports_no_real_roots_and_decimal_coefficients():
    model = build_computed_model(_quadratic("0.5", 0, 2))
    assert model["x_intercepts"] == []
    assert model["discriminant"] < 0
    assert model["vertex"]["y"] == 2
    validate_computed_model(model)


@pytest.mark.parametrize("change", [
    {"kind": "unknown"},
    {"coefficients": {"a": 0, "b": 2, "c": 3}},
    {"coefficients": {"a": 1, "b": "not a number", "c": 2}},
    {"domain": [2, -2]},
    {"domain": [0, 0]},
    {"samples": 2},
    {"samples": True},
])
def test_bad_specs_fail_closed(change):
    spec = _quadratic()
    spec.update(change)
    with pytest.raises(ValueError):
        build_computed_model(spec)


def test_tampered_graph_is_rejected():
    model = build_computed_model(_quadratic())
    corrupt = copy.deepcopy(model)
    corrupt["curve"][10]["y"] += 0.2
    with pytest.raises(ValueError, match="curve"):
        validate_computed_model(corrupt)
    corrupt = copy.deepcopy(model)
    corrupt["vertex"]["y"] += 1
    with pytest.raises(ValueError, match="vertex"):
        validate_computed_model(corrupt)


def test_opt_in_concept_manifest_binds_computed_curve_to_narration():
    lesson = {
        "day": 100,
        "topic": "Quadratic Graph",
        "subtopic": "How coefficients change the curve",
        "real_world_hook": "A projectile has a parabolic path.",
        "concept_intuition": "Trace the actual parabola as its values vary.",
        "visual_hints": "Use computed coordinates.",
        "lesson_goal": "read vertex and intercepts",
        "key_formula": "y=x^2-3x+2",
        "common_mistake": "The vertex is not necessarily a root.",
        "board_examples": {
            "worked_example": ["x^2-3x+2=0", "x=1", "x=2"],
            "practice": ["Find the vertex", "x=1.5"],
        },
        "math_model": _quadratic(),
    }
    plan = plan_lesson(lesson)
    narration = {
        step: {"full": "Visualize the quantities. See what changes.",
               "beats": ["Visualize the quantities.", "See what changes."]}
        for step in plan["scene_order"]
    }
    manifest = build_scene_manifest(lesson, narration, plan)
    concept = next(s for s in manifest["scenes"] if s["step"] == "concept")
    assert concept["mathematical_model"]["vertex"]["x"] == pytest.approx(1.5)
    assert any(obj["type"] == "computed_curve" for obj in concept["objects"])
    assert any(action["action"] == "plot_curve" and
               action["target"] == "concept_computed_curve"
               for action in concept["actions"])
    report = build_coverage_report({
        **manifest, "lesson_id": 100, "key_formula": lesson["key_formula"]
    }, check_history=False)
    assert report["passed"], report["errors"]


def test_legacy_lessons_remain_without_an_opt_in_model():
    lesson = {
        "day": 100,
        "topic": "Linear equations", "subtopic": "Balance",
        "real_world_hook": "Balance both sides.",
        "concept_intuition": "Equal weights.",
        "lesson_goal": "solve",
        "key_formula": "x+3=5",
        "board_examples": {"worked_example": ["x+3=5"], "practice": ["x+2=3"]},
    }
    plan = plan_lesson(lesson)
    narration = {step: {"full": "Watch this.", "beats": ["Watch this."]}
                 for step in plan["scene_order"]}
    manifest = build_scene_manifest(lesson, narration, plan)
    assert all("mathematical_model" not in s for s in manifest["scenes"])


def test_readable_signed_quadratic_equations():
    assert build_computed_model(_quadratic(-1, 0, 0))["equation"] == "y = -x²"
    assert build_computed_model(_quadratic("1/2", 1, -3))["equation"] == "y = 1/2x² + x - 3"
