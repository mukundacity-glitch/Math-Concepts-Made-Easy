"""Stable curriculum IDs and prerequisite ordering without history rewrites."""

from __future__ import annotations


def lesson_concept_id(lesson: dict) -> str:
    """An explicit ID for premium material, a stable implicit ID for legacy."""
    return str(lesson.get("concept_id") or f"day-{int(lesson['day']):03d}")


def validate_curriculum_dependencies(lessons: list[dict]) -> None:
    """Each declared prerequisite must exist and precede the current day."""
    by_id = {}
    by_day = {}
    for lesson in lessons:
        day = lesson.get("day")
        if type(day) is not int or day <= 0:
            raise ValueError(f"invalid curriculum day: {day!r}")
        if day in by_day:
            raise ValueError(f"duplicate curriculum day: {day}")
        by_day[day] = lesson
        concept = lesson_concept_id(lesson)
        if not concept.strip():
            raise ValueError(f"day {day}: empty concept_id")
        if concept in by_id:
            raise ValueError(f"duplicate concept_id: {concept}")
        by_id[concept] = lesson

    for lesson in lessons:
        day = lesson["day"]
        deps = lesson.get("prerequisite_ids", [])
        if not isinstance(deps, list):
            raise ValueError(f"day {day}: prerequisite_ids must be a list")
        if any(not isinstance(dep, str) or not dep.strip() for dep in deps):
            raise ValueError(f"day {day}: prerequisites must be nonempty string IDs")
        if len(deps) != len(set(deps)):
            raise ValueError(f"day {day}: duplicate prerequisites")
        for dep in deps:
            if not isinstance(dep, str) or dep not in by_id:
                raise ValueError(f"day {day}: unknown prerequisite {dep!r}")
            if by_id[dep]["day"] >= day:
                raise ValueError(
                    f"day {day}: prerequisite {dep!r} must be from an earlier day"
                )


def prerequisite_report(lessons: list[dict], day: int) -> dict:
    validate_curriculum_dependencies(lessons)
    current = next((x for x in lessons if x["day"] == day), None)
    if current is None:
        raise ValueError(f"missing curriculum day {day}")
    by_id = {lesson_concept_id(x): x for x in lessons}
    return {
        "day": day,
        "concept_id": lesson_concept_id(current),
        "prerequisites": [
            {"concept_id": dep, "day": by_id[dep]["day"],
             "topic": by_id[dep].get("topic", "")}
            for dep in current.get("prerequisite_ids", [])
        ],
    }
