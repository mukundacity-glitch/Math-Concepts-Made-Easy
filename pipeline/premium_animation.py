"""Phase-3 deterministic, narration-synchronised visual plan.

One verified question => one displayed panel, with stable object IDs.
No lesson-specific motion constants and no truncated worked examples.
Legacy scenes are unmodified until educational_content is explicitly provided.
"""
from __future__ import annotations

import re
from copy import deepcopy

from pipeline.lesson_contract import validate_premium_lesson
from pipeline.mathtext import latex_to_speech

NUMBER_NAMES = (
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
)
SECTION_MAP = {"worked_example": "worked_examples", "practice": "practice_questions"}


def _speak(value: str) -> str:
    # The source is validated independently by the schema-2 math contract.
    # Convert math notation for spoken English rather than reading symbols raw.
    return " ".join(latex_to_speech(value.replace("*", " times ")).split())


def _ordinal(index: int) -> str:
    if not 1 <= index <= len(NUMBER_NAMES):
        raise ValueError("premium narration supports 1 through 20 items per stage")
    return NUMBER_NAMES[index - 1]


def build_premium_visual_plan(lesson: dict) -> dict | None:
    """Pure content->narration/visual action conversion, fail closed."""
    if "educational_content" not in lesson:
        return None
    verification = validate_premium_lesson(lesson)
    payload = {
        "schema_version": "3.0",
        "concept_id": lesson["concept_id"],
        "verification": {
            "worked_examples": verification["worked_examples"],
            "practice_questions": verification["practice_questions"],
        },
        "stages": {},
    }
    for stage, section in SECTION_MAP.items():
        items = []
        paragraphs = []
        for number, question in enumerate(lesson["educational_content"][section], 1):
            digit = _ordinal(number)
            prefix = "Worked example" if stage == "worked_example" else "Practice question"
            cue = f"{prefix} number {digit}"
            item_id = question["id"]
            obj = f"premium_{section}_{item_id}"
            steps = []
            chunk = [f"{cue}.", f"{question['prompt'].rstrip('.')}."]
            if stage == "practice":
                chunk.append("Pause here and solve it independently before following the explanation.")
            for step_index, step in enumerate(question["steps"], 1):
                step_anchor = f"Step number {_ordinal(step_index)} for {digit}"
                chunk.extend([
                    f"{step_anchor}.",
                    f"{step['explanation'].rstrip('.')}.",
                    f"The mathematical state is {_speak(step['math'])}.",
                ])
                steps.append({
                    "object_id": f"{obj}_step_{step_index:02d}",
                    "anchor": step_anchor,
                    "math": step["math"],
                    "explanation": step["explanation"],
                    "mathematical_operation": "transform_equation",
                })
            answer_anchor = f"Verified answer for {digit}"
            chunk.extend([f"{answer_anchor}.", f"The answer is {_speak(question['answer'])}."])
            item = {
                "id": item_id,
                "object_id": obj,
                "cue": cue,
                "prompt": question["prompt"],
                "format": question["format"],
                "difficulty": question["difficulty"],
                "check": deepcopy(question["check"]),
                "steps": steps,
                "answer": question["answer"],
                "answer_anchor": answer_anchor,
            }
            items.append(item)
            paragraphs.append(" ".join(chunk))
        payload["stages"][stage] = {
            "stage": stage,
            "items": items,
            "narration": " ".join(paragraphs),
        }
    return payload


def premium_narration(lesson: dict, stage: str) -> str | None:
    plan = build_premium_visual_plan(lesson)
    if plan is None:
        return None
    if stage not in plan["stages"]:
        raise ValueError(f"unsupported premium stage {stage}")
    return plan["stages"][stage]["narration"]


def _anchor_sequence(item: dict) -> list[str]:
    return [item["cue"]] + [s["anchor"] for s in item["steps"]] + [
        item["answer_anchor"]
    ]


def validate_premium_scene_delivery(script: dict) -> dict | None:
    """Require every verified item/step/answer to survive into rendered scenes.

    This validates identity, ordering and narration evidence. It does NOT
    certify the final encoded MP4's pixels or production speech timing.
    """
    plan = build_premium_visual_plan(script)
    if plan is None:
        return None
    errors = []
    scenes = {s.get("step"): s for s in script.get("scenes", [])}
    validated_count = 0
    for stage in SECTION_MAP:
        expected = plan["stages"][stage]["items"]
        actual_scene = scenes.get(stage)
        if actual_scene is None:
            errors.append(f"missing premium renderer stage {stage}")
            continue
        actual = actual_scene.get("premium_items")
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{stage}: renderer missing one or more verified questions")
            continue
        transcript = actual_scene.get("narration", "")
        position = -1
        object_ids = {obj.get("object_id") for obj in actual_scene.get("objects", [])}
        actions = actual_scene.get("actions", [])
        action_map = {(a.get("target"), a.get("spoken_anchor")) for a in actions}
        for ix, (item, original) in enumerate(zip(actual, expected), 1):
            if item != original:
                errors.append(f"{stage} item {ix}: modified verified visual payload")
                continue
            if item["object_id"] not in object_ids:
                errors.append(f"{stage}: object {item['object_id']} missing")
            for anchor in _anchor_sequence(item):
                found = transcript.find(anchor, position + 1)
                if found < 0:
                    errors.append(f"{stage}: missing or out-of-order spoken anchor {anchor}")
                    break
                if (item["object_id"], anchor) not in action_map:
                    errors.append(f"{stage}: no visual action for {anchor}")
                position = found
            validated_count += 1
        if len(transcript.split()) < len(expected) * 18:
            errors.append(f"{stage}: narration too short for all verified steps")
    if errors:
        raise ValueError("premium video scene coverage failed: " + " | ".join(errors))
    return {
        "schema_version": "3.0",
        "verified_visual_items": validated_count,
        "worked_examples": len(plan["stages"]["worked_example"]["items"]),
        "practice_questions": len(plan["stages"]["practice"]["items"]),
        "each_item_has_narrated_steps": True,
    }


def attach_premium_stage(scene: dict, plan: dict) -> None:
    """Add explicit visual actions; stage registry no longer substitutes activity."""
    step = scene["step"]
    if step not in SECTION_MAP:
        return
    payload = plan["stages"][step]
    scene["premium_items"] = deepcopy(payload["items"])
    beats = scene["narration_beats"]
    for item in payload["items"]:
        scene["objects"].append({
            "object_id": item["object_id"],
            "type": "verified_equation_panel",
            "source": item["id"],
        })
        for sequence_index, anchor in enumerate(_anchor_sequence(item)):
            sentence_index = next(
                (i for i, line in enumerate(beats) if anchor in line),
                None,
            )
            if sentence_index is None:
                raise ValueError(f"{step}: narration missing required spoken anchor {anchor}")
            mathematical_operation = (
                "show_question" if sequence_index == 0 else
                "box_final_answer" if sequence_index == len(item["steps"]) + 1
                else "transform_equation"
            )
            entry = {
                "action_id": f"{item['object_id']}_action_{sequence_index:02d}",
                "action": mathematical_operation,
                "mathematical_operation": mathematical_operation,
                "target": item["object_id"],
                "spoken_anchor": anchor,
                "narration_sentence_index": sentence_index,
                "timing_marker": {"sentence_index": sentence_index, "start_ratio": 0.0},
            }
            scene["actions"].append(entry)
            scene["timing_markers"].append(entry["timing_marker"])
