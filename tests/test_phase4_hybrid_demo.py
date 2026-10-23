"""Integration preparation and the source scene-duration regression."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

from pipeline.lesson_contract import validate_premium_lesson

ROOT = Path(__file__).resolve().parents[1]


def test_real_demo_keeps_all_independently_verified_questions():
    fixture = json.loads((ROOT / "examples/phase4_hybrid_demo.json").read_text())
    lesson = json.loads((ROOT / fixture.pop("source")).read_text())
    lesson.update(fixture)
    result = validate_premium_lesson(lesson)
    assert result["worked_examples"] == 10
    assert result["practice_questions"] == 15
    assert result["verified_solutions"] == 25


def test_production_hold_covers_declared_tail_without_negative_wait():
    tree = ast.parse((ROOT / "pipeline/cell4_animation.py").read_text())
    template = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == "MANIM_SCENE_CODE"
                        for target in node.targets))
    nodes = [node for node in ast.parse(template).body if isinstance(node, ast.FunctionDef)
             and node.name in {"scene_time", "sync_to_audio"}]
    scope = {"SCRIPT_DATA": {"scenes": [{"scene_id": 1, "duration_seconds": 10.65}]}}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<production-hold>", "exec"), scope)
    waits = []
    scene = SimpleNamespace(renderer=SimpleNamespace(time=10.0), wait=waits.append)
    scope["sync_to_audio"](scene, 1)
    assert abs(waits[0] - .65) < 1e-8
    waits.clear()
    scene.renderer.time = 10.8
    scope["sync_to_audio"](scene, 1)
    assert waits == []


def test_premium_board_tail_covers_declared_duration_at_frame_boundary():
    tree = ast.parse((ROOT / "pipeline/premium_manim_helpers.py").read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "render_premium_board")
    # Execute the actual final hold branch without needing the drawing runtime.
    tail = function.body[-2:]
    waits = []
    scope = {"nar": SimpleNamespace(duration=10.653),
             "scene": SimpleNamespace(renderer=SimpleNamespace(time=10.0), wait=waits.append)}
    exec(compile(ast.Module(body=tail, type_ignores=[]), "<premium-tail>", "exec"), scope)
    assert abs(waits[0] - .653) < 1e-8
