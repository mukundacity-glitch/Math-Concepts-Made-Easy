"""Declarative visual action registry used by scene manifests and QA."""

from __future__ import annotations

import math


ACTION_REGISTRY = {
    name: {"meaningful_change": True}
    for name in (
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
    )
}


STAGE_ACTIONS = {
    "opening": ("write_text", "reveal", "focus"),
    "hook": ("show_real_life", "reveal", "highlight"),
    "concept": ("compare_models", "draw_arrow", "focus"),
    "definition": ("write_text", "highlight", "unhighlight"),
    "formula": ("write_formula", "transform_equation", "highlight"),
    "worked_example": (
        "write_formula", "substitute_value", "simplify_expression", "box_final_answer"),
    "mistakes": ("show_wrong", "show_mistake", "show_correct", "compare_models"),
    "practice": ("show_pause", "reveal", "simplify_expression", "box_final_answer"),
    "summary": ("write_formula", "highlight", "reveal"),
}


def build_visual_spec(step: str, narration_beats: list[str], lesson: dict,
                      expected_duration: float) -> tuple[list[dict], list[dict]]:
    """Build stable object IDs and enough timed actions to prevent dead screens."""
    objects = [
        {"object_id": f"{step}_title", "type": "text", "source": lesson.get("topic", "")},
        {"object_id": f"{step}_main", "type": "model", "source": lesson.get("visual_hints", "")},
        {"object_id": f"{step}_formula", "type": "formula", "source": lesson.get("key_formula", "")},
    ]
    action_names = STAGE_ACTIONS.get(step, ("reveal", "focus"))
    beat_count = max(1, len(narration_beats))
    # A visual change at least every seven seconds, with every spoken
    # sentence explicitly covered by one of those changes.
    action_count = max(beat_count, int(math.ceil(max(expected_duration, 1.0) / 7.0)))
    actions = []
    for index in range(action_count):
        sentence_index = min(index, beat_count - 1)
        action = action_names[index % len(action_names)]
        target_suffix = "formula" if "formula" in action or action in {
            "substitute_value", "simplify_expression", "box_final_answer"
        } else "main"
        actions.append({
            "action_id": f"{step}_action_{index + 1:02d}",
            "action": action,
            "target": f"{step}_{target_suffix}",
            "narration_sentence_index": sentence_index,
            "timing_marker": {
                "sentence_index": sentence_index,
                "start_ratio": round(index / action_count, 4),
            },
        })
    return objects, actions


def validate_registered_actions(scenes: list[dict]) -> list[str]:
    errors = []
    for scene in scenes:
        object_ids = {obj.get("object_id") for obj in scene.get("objects", [])}
        for action in scene.get("actions", []):
            name = action.get("action")
            if name not in ACTION_REGISTRY:
                errors.append(f"scene {scene.get('scene_id')}: unregistered action {name!r}")
            if action.get("target") not in object_ids:
                errors.append(
                    f"scene {scene.get('scene_id')}: unknown target {action.get('target')!r}")
    return errors
