"""Curriculum loader — the single source of lesson content.

Lessons live as structured data in curriculum/*.json, one file per
grade/track. Nothing topic-specific is ever hard-coded in the engine;
adding a new grade or subject means adding another JSON file here.
"""

import json
from pathlib import Path

CURRICULUM_DIR = Path(__file__).resolve().parents[1] / "curriculum"


def load_curriculum() -> list:
    lessons = []
    for path in sorted(CURRICULUM_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for lesson in data["lessons"]:
            lesson.setdefault("grade", data.get("grade"))
        lessons.extend(data["lessons"])

    lessons.sort(key=lambda l: l["day"])
    days = [l["day"] for l in lessons]
    dupes = sorted({d for d in days if days.count(d) > 1})
    if dupes:
        raise SystemExit(f"🛑 Duplicate day numbers in curriculum: {dupes}")
    return lessons


MASTER_CURRICULUM = load_curriculum()
TOTAL_DAYS = len(MASTER_CURRICULUM)


def get_lesson(day: int) -> dict:
    for row in MASTER_CURRICULUM:
        if row["day"] == day:
            return row
    raise ValueError(f"🛑 Day {day} not found in curriculum ({TOTAL_DAYS} lessons loaded).")
