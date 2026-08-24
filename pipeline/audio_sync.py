"""Map Edge-TTS word boundaries back to narration statements and actions."""

from __future__ import annotations

import re


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", str(text)))


def apply_word_timing(scene: dict, words: list[dict]) -> dict:
    """Add statement/action timing while preserving the original word list."""
    beats = scene.get("narration_beats") or [scene.get("narration", "")]
    duration = float(scene.get("duration_seconds") or scene.get("expected_duration") or 1.0)
    counts = [_word_count(beat) for beat in beats]
    total = sum(counts) or 1
    cursor = 0
    statement_timing = []
    for index, count in enumerate(counts):
        if words:
            start_pos = min(cursor, len(words) - 1)
            end_pos = min(max(cursor + count - 1, start_pos), len(words) - 1)
            start = float(words[start_pos].get("start", 0.0))
            end = float(words[end_pos].get("end", start))
        else:
            start = duration * cursor / total
            end = duration * min(cursor + count, total) / total
        statement_timing.append({
            "sentence_index": index,
            "start": round(start, 3),
            "end": round(end, 3),
        })
        cursor += count

    by_sentence = {row["sentence_index"]: row for row in statement_timing}
    for action in scene.get("actions", []):
        timing = by_sentence.get(action.get("narration_sentence_index", 0), {})
        action["start_seconds"] = timing.get("start", 0.0)
        action["end_seconds"] = timing.get("end", duration)
    scene["statement_timing"] = statement_timing
    return scene
