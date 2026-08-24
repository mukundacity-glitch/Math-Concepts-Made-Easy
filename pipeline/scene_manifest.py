"""Visual scene manifest builder.

The manifest is the contract between narration, audio timing, Manim rendering,
and quality assurance.  It deliberately contains no lesson-specific code.
"""

from __future__ import annotations

from pipeline.mathtext import split_sentences
from pipeline.visual_actions import build_visual_spec


STEP_META = {
    "opening": ("Hook", "Establish curiosity and the lesson goal", "TITLE_SEQUENCE", "fade"),
    "hook": ("Intuition", "Connect the idea to a concrete situation", "VISUAL_ONLY", "wipe_right"),
    "concept": ("Diagram / model", "Build the mental model", "VISUAL_ONLY", "transform"),
    "definition": ("Definition", "State the idea precisely", "VISUAL_ONLY", "wipe_right"),
    "formula": ("Formula / rule", "Build the rule progressively", "EQUATION_BUILD", "transform"),
    "worked_example": ("Worked example", "Apply every step without jumps", "BOARD_WRITE", "wipe_right"),
    "mistakes": ("Common mistake", "Contrast incorrect and correct reasoning", "BOARD_WRITE", "compare"),
    "practice": ("Student pause", "Prompt retrieval before revealing the solution", "BOARD_WRITE", "reveal"),
    "summary": ("Recap", "Compress the lesson into one reusable idea", "VISUAL_ONLY", "fade"),
}


def estimate_duration(text: str, words_per_minute: int = 125) -> float:
    return round(max(6.0, len(str(text).split()) * 60.0 / words_per_minute), 2)


def build_scene_manifest(lesson: dict, narrations: dict, plan: dict) -> dict:
    scenes = []
    stage_by_step = {
        item["renderer_step"]: item["stage"] for item in plan["selected_stages"]
    }
    for scene_id, step in enumerate(plan["scene_order"], start=1):
        block = narrations[step]
        narration = block.get("full", "") if isinstance(block, dict) else str(block)
        beats = block.get("beats", []) if isinstance(block, dict) else split_sentences(narration)
        beats = beats or split_sentences(narration)
        expected = estimate_duration(narration)
        objects, actions = build_visual_spec(step, beats, lesson, expected)
        label, purpose, animation_type, transition = STEP_META[step]
        scenes.append({
            "scene_id": scene_id,
            "stage": stage_by_step[step],
            "step": step,
            "label": label,
            "purpose": purpose,
            "learning_purpose": purpose,
            "narration": narration,
            "narration_beats": beats,
            "duration_seconds": 0.0,
            "expected_duration": expected,
            "estimated_seconds": expected,
            "objects": objects,
            "actions": actions,
            "timing_markers": [action["timing_marker"] for action in actions],
            "transition_style": transition,
            "animation_type": animation_type,
        })
    return {
        "schema_version": "1.0",
        "lesson_id": int(lesson.get("day", lesson.get("id"))),
        "hook_variant": plan["hook_variant"],
        "outro_variant": plan["outro_variant"],
        "selected_stages": plan["selected_stages"],
        "scenes": scenes,
    }
