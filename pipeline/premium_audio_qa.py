"""Strict word-boundary quality gate for premium narrated Manim scenes.

The legacy pipeline may estimate timings, but the opt-in premium contract
never permits synthetic/default/empty word timing on a published lesson.
"""
from __future__ import annotations

from pipeline.mathtext import normalize_word


def _tokens(value: str) -> list[str]:
    return [x for t in str(value).split() if (x := normalize_word(t))]


def validate_premium_word_alignment(scene: dict, words: list[dict]) -> dict | None:
    """Every question/step/answer spoken cue must map to real ordered words."""
    items = scene.get("premium_items")
    if items is None:
        return None
    if not isinstance(items, list) or not items:
        raise ValueError("premium audio scene has no verified questions")
    if not isinstance(words, list) or not words:
        raise ValueError("premium audio requires Edge-TTS word boundaries")
    duration = float(scene.get("duration_seconds") or 0)
    if duration <= 0:
        raise ValueError("premium audio requires measured positive duration")
    last_end = -1.0
    for index, word in enumerate(words):
        if not isinstance(word, dict) or not isinstance(word.get("norm"), str):
            raise ValueError(f"invalid premium word data at index {index}")
        try:
            start, end = float(word["start"]), float(word["end"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"invalid premium word timestamp at index {index}") from exc
        if not 0 <= start < end <= duration + 0.05:
            raise ValueError(f"premium word timestamp out of range at index {index}")
        if start < last_end - 0.06:
            raise ValueError(f"premium word timestamps overlap/reverse at index {index}")
        last_end = end
    normalized = [w["norm"] for w in words]
    cursor, cues = 0, 0
    for item in items:
        anchors = [item["cue"]] + [s["anchor"] for s in item["steps"]] + [
            item["answer_anchor"]
        ]
        for phrase in anchors:
            target = _tokens(phrase)
            if not target:
                raise ValueError("premium audio contains empty spoken anchor")
            hit = next(
                (pos for pos in range(cursor, len(normalized) - len(target) + 1)
                 if normalized[pos:pos + len(target)] == target),
                None,
            )
            if hit is None:
                raise ValueError(f"premium spoken cue missing/out of order: {phrase}")
            cursor = hit + len(target)
            cues += 1
    if cues < len(items) * 4:
        raise ValueError("premium audio has incomplete step coverage")
    return {"verified_items": len(items), "verified_spoken_cues": cues,
            "spoken_word_count": len(words), "duration_seconds": duration}
