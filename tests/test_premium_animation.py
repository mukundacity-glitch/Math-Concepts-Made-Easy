"""Phase 3: verify full narration, visual object identity and computed geometry."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from pipeline.curriculum import MASTER_CURRICULUM
from pipeline.geometry_models import build_geometry_model, validate_geometry_model
from pipeline.verified_visual_models import (
    build_verified_visual_model, validate_verified_visual_model,
)
from pipeline.lesson_plan import plan_lesson
from pipeline.lesson_qa import build_coverage_report
from pipeline.mathtext import split_sentences
from pipeline.premium_animation import (
    build_premium_visual_plan, premium_narration, validate_premium_scene_delivery,
)
from pipeline.scene_manifest import build_scene_manifest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def lesson():
    base = deepcopy(next(l for l in MASTER_CURRICULUM if l["day"] == 43))
    demo = json.loads((ROOT / "examples" / "premium_algebra_lesson.json").read_text())
    base.update({
        "concept_id": demo["concept_id"],
        "prerequisite_ids": demo["prerequisite_ids"],
        "educational_content": demo["educational_content"],
    })
    return base


def script_for(lesson):
    plan = plan_lesson(lesson)
    transcripts = {}
    for stage in plan["scene_order"]:
        narration = premium_narration(lesson, stage) if stage in {
            "worked_example", "practice"} else (
            "Observe the main idea as mathematical objects change and improve. "
            "We will apply the lesson carefully with precise mathematical reasoning."
        )
        transcripts[stage] = {
            "full": narration,
            "beats": split_sentences(narration),
        }
    manifest = build_scene_manifest(lesson, transcripts, plan)
    script = {
        "lesson_id": lesson["day"], "key_formula": lesson["key_formula"],
        "scenes": manifest["scenes"], "concept_id": lesson["concept_id"],
        "prerequisite_ids": lesson["prerequisite_ids"],
        "educational_content": lesson["educational_content"],
        "premium_visual_version": "3.0",
    }
    return script


def test_every_one_of_twenty_five_problems_is_narrated_and_renderable(lesson):
    script = script_for(lesson)
    report = validate_premium_scene_delivery(script)
    assert report["verified_visual_items"] == 25
    worked = next(s for s in script["scenes"] if s["step"] == "worked_example")
    practice = next(s for s in script["scenes"] if s["step"] == "practice")
    assert len(worked["premium_items"]) == 10
    assert len(practice["premium_items"]) == 15
    assert "Worked example number one" in worked["narration"]
    assert "Practice question number fifteen" in practice["narration"]
    ids = [i["object_id"] for s in (worked, practice) for i in s["premium_items"]]
    assert len(ids) == len(set(ids)) == 25
    # Keep each item math-state identity stable across the transformation.
    assert all(len(i["steps"]) >= 2 for s in (worked, practice)
               for i in s["premium_items"])


def test_qa_reports_fail_closed_for_missing_item_and_wrong_anchor(lesson):
    script = script_for(lesson)
    qa = build_coverage_report(script, check_history=False)
    assert qa["passed"], qa["errors"]
    scene = next(s for s in script["scenes"] if s["step"] == "practice")
    scene["premium_items"].pop()
    bad = build_coverage_report(script, check_history=False)
    assert not bad["passed"]
    assert any("renderer missing" in x for x in bad["errors"])
    script = script_for(lesson)
    scene = next(s for s in script["scenes"] if s["step"] == "worked_example")
    scene["narration"] = scene["narration"].replace(
        "Worked example number one", "Nothing is spoken for this first item", 1)
    bad = build_coverage_report(script, check_history=False)
    assert not bad["passed"]
    assert any("spoken anchor" in x for x in bad["errors"])


def test_qa_rejects_nonverified_visual_state_tampering(lesson):
    script = script_for(lesson)
    scene = next(s for s in script["scenes"] if s["step"] == "worked_example")
    scene["premium_items"][0]["steps"][1]["math"] = "x=999"
    report = build_coverage_report(script, check_history=False)
    assert not report["passed"]
    assert any("modified verified visual payload" in x for x in report["errors"])


def test_narration_completely_covers_worked_and_practice(lesson):
    plan = build_premium_visual_plan(lesson)
    for stage, required in (("worked_example", 10), ("practice", 15)):
        text = premium_narration(lesson, stage)
        items = plan["stages"][stage]["items"]
        assert len(items) == required
        assert text == plan["stages"][stage]["narration"]
        assert text.count("Verified answer for ") == required
        assert text.count("Step number one for ") == required
        for item in items:
            assert item["cue"] in text
            assert item["answer_anchor"] in text
            for s in item["steps"]:
                assert s["anchor"] in text


def test_legacy_curriculum_is_never_auto_promoted():
    legacy = next(l for l in MASTER_CURRICULUM if l["day"] == 43)
    assert build_premium_visual_plan(legacy) is None
    assert "educational_content" not in legacy


@pytest.mark.parametrize("spec,hyp,area", [
    ({"kind": "right_triangle", "legs": {"a": 3, "b": 4}}, 5, 6),
    ({"kind": "right_triangle", "legs": {"a": "5/2", "b": "6"}}, 6.5, 7.5),
])
def test_computed_triangle_uses_exact_actual_side_lengths(spec, hyp, area):
    model = build_verified_visual_model(spec)
    assert model["hypotenuse"] == pytest.approx(hyp)
    assert model["area"] == pytest.approx(area)
    assert model["pythagorean_residual"] == pytest.approx(0)
    validate_verified_visual_model(model)
    model["vertices"][1]["x"] += 1
    with pytest.raises(ValueError, match="altered"):
        validate_verified_visual_model(model)


def test_circle_uses_computed_area_and_circumference():
    model = build_geometry_model({"kind": "circle", "radius": "3/2"})
    assert model["radius"] == 1.5
    assert model["area"] == pytest.approx(7.0685834705770345)
    assert model["circumference"] == pytest.approx(9.42477796076938)
    validate_geometry_model(model)
    model["area"] *= 2
    with pytest.raises(ValueError, match="altered"):
        validate_geometry_model(model)


@pytest.mark.parametrize("spec", [
    {"kind": "right_triangle", "legs": {"a": -2, "b": 3}},
    {"kind": "right_triangle", "legs": {"a": 1, "b": 0}},
    {"kind": "right_triangle", "legs": {"a": "nan", "b": 3}},
    {"kind": "circle", "radius": 0},
    {"kind": "circle", "radius": 999999},
    {"kind": "circle", "radius": "x"},
    {"kind": "unsupported"},
])
def test_invalid_geometry_is_rejected(spec):
    with pytest.raises((ValueError, TypeError)):
        build_verified_visual_model(spec)


def test_geometry_route_participates_in_declarative_scene_plan(lesson):
    lesson["math_model"] = {"kind": "right_triangle", "legs": {"a": 3, "b": 4}}
    script = script_for(lesson)
    scene = next(s for s in script["scenes"] if s["step"] == "concept")
    assert scene["mathematical_model"]["hypotenuse"] == 5
    assert any(a.get("mathematical_operation") == "trace_computed_function"
               for a in scene["actions"])
    qa = build_coverage_report(script, check_history=False)
    assert qa["passed"], qa["errors"]
    scene["mathematical_model"]["area"] = 999
    assert not build_coverage_report(script, check_history=False)["passed"]
