from __future__ import annotations

import copy
import ast
from pathlib import Path

import pytest

from pipeline.lesson_plan import plan_lesson
from pipeline.lesson_qa import assert_lesson_quality
from pipeline.scene_manifest import build_scene_manifest
from pipeline.visual_actions import ACTION_REGISTRY


ROOT = Path(__file__).resolve().parents[1]


BASE_LESSON = {
    "day": 100,
    "topic": "Sample Topic",
    "subtopic": "A precise definition",
    "lesson_goal": "solve and explain one example",
    "real_world_hook": "A concrete situation creates a useful mathematical question.",
    "concept_intuition": "The model shows why the rule works before symbols appear.",
    "visual_hints": "Draw the matching model and label each changing quantity.",
    "key_formula": "x+3=10",
    "common_mistake": "Do not change only one side of an equation.",
    "board_examples": {
        "worked_example": ["x+3=10", "x=7"],
        "practice": ["y+4=12", "y=8"],
    },
}


@pytest.fixture(params=[
    {
        "day": 101,
        "topic": "One Half",
        "subtopic": "Fractions as equal parts",
        "key_formula": r"\frac{1}{2}",
        "visual_hints": "Divide a pizza into two equal slices and shade one.",
    },
    {
        "day": 102,
        "topic": "Sine in a Right Triangle",
        "subtopic": "Opposite over hypotenuse",
        "key_formula": r"\sin\theta=\frac{\text{opposite}}{\text{hypotenuse}}",
        "visual_hints": "Draw a right triangle, mark the right angle, and label its sides.",
    },
    {
        "day": 103,
        "topic": "Solve x Plus Three Equals Ten",
        "subtopic": "Inverse operations",
        "key_formula": "x+3=10",
        "visual_hints": "Use a balance model, subtract three from both sides, and reveal x=7.",
    },
])
def lesson(request):
    value = copy.deepcopy(BASE_LESSON)
    value.update(request.param)
    return value


def _narrations(plan):
    return {
        step: {
            "full": (
                f"This is the {step} statement. "
                "Watch the model change with the explanation. "
                "Now connect that visual change to the mathematical rule."
            ),
            "beats": [
                f"This is the {step} statement.",
                "Watch the model change with the explanation.",
                "Now connect that visual change to the mathematical rule.",
            ],
        }
        for step in plan["scene_order"]
    }


def test_three_lesson_types_produce_complete_manifests(lesson):
    plan = plan_lesson(lesson)
    manifest = build_scene_manifest(lesson, _narrations(plan), plan)
    script = {
        **manifest,
        "key_formula": lesson["key_formula"],
        "lesson_id": lesson["day"],
    }

    report = assert_lesson_quality(script, check_history=False)
    assert report["passed"]
    assert {"worked_example", "practice"}.issubset(
        {scene["step"] for scene in manifest["scenes"]})
    for scene in manifest["scenes"]:
        covered = {a["narration_sentence_index"] for a in scene["actions"]}
        assert covered == set(range(len(scene["narration_beats"])))
        assert scene["objects"]
        assert scene["expected_duration"] > 0


def test_required_visual_action_registry_is_complete():
    required = {
        "write_text", "write_formula", "erase", "fade", "move", "scale",
        "focus", "highlight", "unhighlight", "draw_arrow", "draw_line",
        "draw_right_triangle", "draw_triangle", "mark_right_angle",
        "label_side", "label_angle", "draw_circle", "divide_circle",
        "shade_fraction", "draw_number_line", "place_number",
        "draw_coordinate_plane", "plot_point", "plot_line", "plot_curve",
        "draw_table", "fill_table_cell", "transform_equation",
        "substitute_value", "simplify_expression", "box_final_answer",
        "show_wrong", "show_correct", "show_pause", "reveal", "show_mistake",
        "show_real_life", "animate_cut", "compare_models",
    }
    assert required.issubset(ACTION_REGISTRY)


def test_embedded_manim_source_is_valid_python():
    source = (ROOT / "pipeline/cell4_animation.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    template = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "MANIM_SCENE_CODE"
            for target in node.targets
        ):
            template = ast.literal_eval(node.value)
            break
    assert template
    ast.parse(template)
