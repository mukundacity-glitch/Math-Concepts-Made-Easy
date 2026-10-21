"""Content-driven lesson planning.

The planner selects teaching stages from the lesson data instead of requiring
every lesson to follow a hard-coded template.  Renderer step names are retained
as a compatibility boundary for the existing Manim scene implementations.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from pipeline.creative_history import recent_variants
from pipeline.visual_models import STYLES, validate_visual


HOOK_VARIANTS = (
    "mystery",
    "prediction",
    "real_life_problem",
    "visual_puzzle",
    "wrong_answer",
    "before_and_after",
    "two_choices",
    "surprising_shortcut",
    "pattern_spotting",
    "student_challenge",
)

OUTRO_VARIANTS = (
    "one_line_recap",
    "tomorrow_teaser",
    "confidence_close",
    "practice_prompt",
    "exam_tip",
    "teach_it_back",
)


STAGE_DEFINITIONS = (
    ("hook", "opening", lambda lesson: bool(lesson.get("topic"))),
    ("intuition", "hook", lambda lesson: bool(lesson.get("real_world_hook"))),
    ("diagram_model", "concept", lambda lesson: bool(
        lesson.get("concept_intuition") or lesson.get("visual_hints"))),
    ("definition", "definition", lambda lesson: bool(lesson.get("subtopic"))),
    ("formula_rule", "formula", lambda lesson: bool(lesson.get("key_formula"))),
    ("worked_example", "worked_example", lambda lesson: bool(
        (lesson.get("board_examples") or {}).get("worked_example"))),
    ("common_mistake", "mistakes", lambda lesson: bool(lesson.get("common_mistake"))),
    ("student_pause", "practice", lambda lesson: bool(
        (lesson.get("board_examples") or {}).get("practice"))),
    ("recap", "summary", lambda lesson: bool(lesson.get("lesson_goal"))),
)


def _choose_variant(options: tuple[str, ...], recent: list[str], day: int) -> str:
    if not options:
        raise ValueError("creative variant options must not be empty")
    available = [option for option in options if option not in recent[-5:]]
    if not available:
        raise ValueError("no creative variant satisfies the five-lesson exclusion")
    return available[(int(day) - 1) % len(available)]


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value.strip()


def _validate_design(design: Any) -> dict[str, Any]:
    """Validate explicit lesson data without inventing examples or renderers."""
    if not isinstance(design, dict):
        raise ValueError("lesson_design must be an object")
    result = deepcopy(design)
    grade = result.get("grade")
    if type(grade) is not int or grade not in (9, 10, 11, 12):
        raise ValueError("lesson_design.grade must be an integer from 9 to 12")
    advanced = result.get("advanced", False)
    if not isinstance(advanced, bool):
        raise ValueError("lesson_design.advanced must be a boolean")
    minimum_examples = 3 if grade >= 11 and advanced else 2
    examples = result.get("worked_examples")
    if not isinstance(examples, list) or len(examples) < minimum_examples:
        raise ValueError(
            f"lesson_design.worked_examples requires {minimum_examples} worked problems")
    identifiers: set[str] = set()
    prompts: set[str] = set()
    representations: set[str] = set()
    models: set[str] = set()
    for index, example in enumerate(examples):
        prefix = f"lesson_design.worked_examples[{index}]"
        if not isinstance(example, dict):
            raise ValueError(f"{prefix} must be an object")
        for field in ("id", "prompt", "representation", "visual_model"):
            example[field] = _nonempty_text(example.get(field), f"{prefix}.{field}")
        if example["id"] in identifiers:
            raise ValueError(f"{prefix}.id duplicates another worked problem")
        prompt_key = " ".join(example["prompt"].casefold().split())
        if prompt_key in prompts:
            raise ValueError(f"{prefix}.prompt duplicates another worked problem")
        identifiers.add(example["id"])
        prompts.add(prompt_key)
        representations.add(example["representation"])
        models.add(example["visual_model"])
        example["visual"] = validate_visual(example.get("visual"))
        if example["visual"]["model"] != example["visual_model"]:
            raise ValueError(f"{prefix}.visual_model does not match visual.model")
        steps = example.get("solution_steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"{prefix}.solution_steps must contain the worked solution")
        example["solution_steps"] = [
            _nonempty_text(step, f"{prefix}.solution_steps[{step_index}]")
            for step_index, step in enumerate(steps)
        ]
    supporting = result.get("supporting_representations", [])
    if not isinstance(supporting, list):
        raise ValueError("lesson_design.supporting_representations must be a list")
    for index, representation in enumerate(supporting):
        if not isinstance(representation, dict):
            raise ValueError(f"supporting_representations[{index}] must be an object")
        for field in ("representation", "visual_model", "learning_goal"):
            representation[field] = _nonempty_text(
                representation.get(field), f"supporting_representations[{index}].{field}")
        representations.add(representation["representation"])
        models.add(representation["visual_model"])
    if len(representations) < 3 or len(models) < 2:
        raise ValueError("lesson_design requires three representations and two visual models")
    mistake = result.get("misconception")
    if not isinstance(mistake, dict):
        raise ValueError("lesson_design.misconception must be an object")
    for field in ("wrong_reasoning", "correction"):
        mistake[field] = _nonempty_text(mistake.get(field), f"misconception.{field}")
    pause = result.get("student_pause")
    if not isinstance(pause, dict):
        raise ValueError("lesson_design.student_pause must be an object")
    for field in ("prompt", "answer"):
        pause[field] = _nonempty_text(pause.get(field), f"student_pause.{field}")
    seconds = pause.get("pause_seconds")
    if (isinstance(seconds, bool) or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds) or seconds <= 0):
        raise ValueError("student_pause.pause_seconds must be a positive finite number")
    scene_panels = result.get("scene_panels", {})
    if not isinstance(scene_panels, dict):
        raise ValueError("lesson_design.scene_panels must be an object")
    supported_steps = {item[1] for item in STAGE_DEFINITIONS}
    for step, panels in scene_panels.items():
        if step not in supported_steps or not isinstance(panels, list) or not panels:
            raise ValueError(f"invalid scene panels for {step}")
        for panel in panels:
            if not isinstance(panel, dict):
                raise ValueError("each panel must be an object")
            _nonempty_text(panel.get("title"), "panel.title")
            narration = panel.get("narration")
            if not isinstance(narration, list) or not narration:
                raise ValueError("panel.narration must be nonempty")
            for line in narration:
                _nonempty_text(line, "panel.narration line")
            lines = panel.get("lines")
            if not isinstance(lines, list) or any(not isinstance(line, str) for line in lines):
                raise ValueError("panel.lines must be a list of strings")
            panel["visual"] = validate_visual(panel.get("visual"))
    if "visual" in pause:
        pause["visual"] = validate_visual(pause["visual"])
    practice_set = result.get("practice_set", [pause])
    if not isinstance(practice_set, list) or not practice_set:
        raise ValueError("practice_set must contain independent questions")
    for practice in practice_set:
        if not isinstance(practice, dict):
            raise ValueError("each practice question must be an object")
        for field in ("prompt", "answer"):
            _nonempty_text(practice.get(field), f"practice.{field}")
        seconds = practice.get("pause_seconds")
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 60:
            raise ValueError("practice pauses must last between 0 and 60 seconds")
        if "visual" in practice:
            practice["visual"] = validate_visual(practice["visual"])
    result["minimum_worked_examples"] = minimum_examples
    return result


def plan_lesson(lesson: dict) -> dict:
    """Keep legacy scene names; validate richer design data when supplied.

    lesson_design is a planning contract, not a renderer implementation.
    Existing consumers continue to use the legacy scene order until upgraded.
    """
    if not isinstance(lesson, dict):
        raise ValueError("lesson must be an object")
    raw_day = lesson.get("day")
    if isinstance(raw_day, bool) or not isinstance(raw_day, (int, str)):
        raise ValueError("lesson.day must be a positive integer")
    try:
        day = int(raw_day)
    except ValueError as exc:
        raise ValueError("lesson.day must be a positive integer") from exc
    if day <= 0:
        raise ValueError("lesson.day must be a positive integer")
    board = lesson.get("board_examples")
    if not isinstance(board, dict):
        raise ValueError("lesson.board_examples must be an object")
    for field in ("worked_example", "practice"):
        lines = board.get(field)
        if not isinstance(lines, list) or not lines:
            raise ValueError(f"board_examples.{field} must be a nonempty list of strings")
        for index, line in enumerate(lines):
            _nonempty_text(line, f"board_examples.{field}[{index}]")
    design = _validate_design(lesson["lesson_design"]) if "lesson_design" in lesson else None
    selected = [
        {"stage": stage, "renderer_step": renderer_step}
        for stage, renderer_step, predicate in STAGE_DEFINITIONS
        if predicate(lesson)
    ]
    steps = {item["renderer_step"] for item in selected}
    required = {"opening", "worked_example", "practice", "summary"}
    missing = sorted(required - steps)
    if missing:
        raise ValueError(f"lesson is missing required teaching stages: {', '.join(missing)}")

    return {
        "day": day,
        "selected_stages": selected,
        "scene_order": [item["renderer_step"] for item in selected],
        "hook_variant": _choose_variant(
            HOOK_VARIANTS, recent_variants("hook_variant", count=5), day),
        "outro_variant": _choose_variant(
            OUTRO_VARIANTS, recent_variants("outro_variant", count=5), day),
        "visual_style": _choose_variant(STYLES, recent_variants("visual_style", count=1), day),
        "lesson_design": design,
        "design_status": "validated" if design is not None else "legacy",
    }
