"""Content-driven lesson planning.

The planner selects teaching stages from the lesson data instead of requiring
every lesson to follow a hard-coded template.  Renderer step names are retained
as a compatibility boundary for the existing Manim scene implementations.
"""

from __future__ import annotations

from pipeline.creative_history import recent_variants


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
    available = [option for option in options if option not in recent[-3:]] or list(options)
    return available[(int(day) - 1) % len(available)]


def plan_lesson(lesson: dict) -> dict:
    """Return selected stages and fresh creative variants for one lesson."""
    day = int(lesson["day"])
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
            HOOK_VARIANTS, recent_variants("hook_variant"), day),
        "outro_variant": _choose_variant(
            OUTRO_VARIANTS, recent_variants("outro_variant"), day),
    }
