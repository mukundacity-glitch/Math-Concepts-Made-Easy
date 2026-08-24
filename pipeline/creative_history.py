"""Persistent hook/outro rotation for future lessons.

Only successful lessons are recorded.  Planning a failed or preview render does
not consume a creative variant, so reruns stay deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.paths import REPO_ROOT


HISTORY_PATH = REPO_ROOT / "state" / "creative_history.json"


def read_creative_history(path: Path = HISTORY_PATH) -> dict:
    if not path.exists():
        return {"lessons": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"lessons": []}
    lessons = data.get("lessons", [])
    return {"lessons": lessons if isinstance(lessons, list) else []}


def recent_variants(kind: str, count: int = 3, path: Path = HISTORY_PATH) -> list[str]:
    rows = read_creative_history(path)["lessons"]
    return [str(row.get(kind, "")) for row in rows[-count:] if row.get(kind)]


def record_lesson(day: int, hook_variant: str, outro_variant: str,
                  path: Path = HISTORY_PATH) -> None:
    history = read_creative_history(path)
    rows = [row for row in history["lessons"] if int(row.get("day", -1)) != int(day)]
    rows.append({
        "day": int(day),
        "hook_variant": str(hook_variant),
        "outro_variant": str(outro_variant),
    })
    history["lessons"] = sorted(rows, key=lambda row: int(row["day"]))[-20:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
