"""Fail-closed semantic, pacing, LaTeX, and narration-sync quality gates."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.creative_history import recent_variants
from pipeline.visual_actions import validate_registered_actions


def _balanced_latex(value: str) -> bool:
    return str(value).count("{") == str(value).count("}")


def build_coverage_report(script: dict, check_history: bool = True) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    scenes = script.get("scenes", [])
    steps = {scene.get("step") for scene in scenes}

    for required in ("worked_example", "practice"):
        if required not in steps:
            errors.append(f"missing required {required} stage")

    errors.extend(validate_registered_actions(scenes))
    for scene in scenes:
        scene_id = scene.get("scene_id")
        narration = str(scene.get("narration", "")).strip()
        beats = scene.get("narration_beats", [])
        actions = scene.get("actions", [])
        if not narration:
            errors.append(f"scene {scene_id}: empty narration")
        covered = {action.get("narration_sentence_index") for action in actions}
        missing = [index for index in range(len(beats)) if index not in covered]
        if missing:
            errors.append(f"scene {scene_id}: narration statements without visuals {missing}")
        duration = float(scene.get("duration_seconds") or scene.get("expected_duration") or 0.0)
        if duration > 0 and actions:
            maximum_static = duration / len(actions)
            if maximum_static > 10.0:
                errors.append(f"scene {scene_id}: static interval {maximum_static:.1f}s exceeds 10s")
            elif maximum_static > 8.0:
                warnings.append(f"scene {scene_id}: visual interval {maximum_static:.1f}s exceeds 8s target")
        expected = float(scene.get("expected_duration") or scene.get("estimated_seconds") or 0.0)
        actual = float(scene.get("duration_seconds") or 0.0)
        if actual and expected and abs(actual - expected) > max(12.0, expected * 0.45):
            errors.append(
                f"scene {scene_id}: narration/render estimate mismatch "
                f"({actual:.1f}s vs {expected:.1f}s)")

    formula = script.get("key_formula", "")
    if not _balanced_latex(formula):
        errors.append("invalid LaTeX: unbalanced braces in key_formula")

    if check_history:
        hook = script.get("hook_variant")
        outro = script.get("outro_variant")
        if hook and hook in recent_variants("hook_variant", 3):
            errors.append(f"hook variant {hook!r} appeared in the previous three lessons")
        if outro and outro in recent_variants("outro_variant", 1):
            errors.append(f"outro variant {outro!r} repeats consecutively")

    return {
        "lesson_id": script.get("lesson_id"),
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "scene_coverage": [
            {
                "scene_id": scene.get("scene_id"),
                "stage": scene.get("stage"),
                "narration_statements": len(scene.get("narration_beats", [])),
                "visual_actions": len(scene.get("actions", [])),
            }
            for scene in scenes
        ],
    }


def assert_lesson_quality(script: dict, report_path: Path | None = None,
                          check_history: bool = True) -> dict:
    report = build_coverage_report(script, check_history=check_history)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise ValueError("lesson QA failed: " + " | ".join(report["errors"]))
    return report
