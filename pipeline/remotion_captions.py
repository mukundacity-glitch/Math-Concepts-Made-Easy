"""Verified scene-local caption chunks from existing Cell-3 Edge-TTS words.

Caption timing is derived exclusively from original speech word boundaries.
No forced alignment, estimated timing, auto-transcription, or inferred words.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

MAX_WORDS_PER_SCENE = 6000
MAX_WORD_CHARS = 96
MAX_CAPTION_CHARS = 52
MAX_CAPTION_WORDS = 7
MAX_CAPTION_SPAN_MS = 3100


def load_scene_word_captions(path: Path, *, clip_seconds: float,
                             audio_seconds: float) -> list[dict] | None:
    """Return Remotion Caption records with relative ms, None if no words.

    Missing or empty original word boundaries mean captions are unavailable,
    never synthetic. A malformed nonempty source fails closed.
    """
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"invalid word-boundary JSON: {path.name}") from exc
    if not isinstance(raw, list):
        raise ValueError("scene word-boundary data must be a JSON array")
    if not raw:
        return None
    if len(raw) > MAX_WORDS_PER_SCENE:
        raise ValueError("scene word-boundary data exceeds supported word count")
    if not math.isfinite(clip_seconds) or not math.isfinite(audio_seconds):
        raise ValueError("non-finite caption duration")
    if clip_seconds <= 0 or audio_seconds <= 0:
        raise ValueError("caption durations must be positive")

    cleaned = []
    prev_start, prev_end = -1.0, -1.0
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise ValueError(f"word-boundary item {index} must be an object")
        word, start, end = value.get("word"), value.get("start"), value.get("end")
        if not isinstance(word, str) or not word.strip() or len(word) > MAX_WORD_CHARS:
            raise ValueError(f"invalid word-boundary text at {index}")
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in word):
            raise ValueError("word-boundary text contains control characters")
        if type(start) not in (int, float) or type(end) not in (int, float):
            raise ValueError("word boundaries must be numeric seconds")
        start, end = float(start), float(end)
        if (not math.isfinite(start) or not math.isfinite(end) or start < 0 or
            end <= start or start + 0.0001 < prev_start or
            end + 0.0001 < prev_end):
            raise ValueError(f"non-monotonic word boundaries at {index}")
        if end > clip_seconds + 0.04 or end > audio_seconds + 0.15:
            raise ValueError("caption word extends beyond playable original audio/scene")
        # Edge-TTS can overlap adjacent word boundary events by a few ms.
        # Clip only sub-20ms jitter; larger overlaps indicate broken alignment.
        if prev_end >= 0 and start < prev_end:
            if prev_end - start > 0.02:
                raise ValueError("overlapping word boundaries exceed tolerance")
            start = prev_end
        if end <= start:
            raise ValueError("word duration collapsed after alignment correction")
        cleaned.append((word.strip(), round(start * 1000), round(end * 1000)))
        prev_start, prev_end = start, end

    captions: list[dict] = []
    group: list[tuple[str, int, int]] = []
    def flush() -> None:
        if not group:
            return
        line = " ".join(word for word, _, _ in group)
        begin, finish = group[0][1], group[-1][2]
        if finish <= begin:
            raise ValueError("caption event has nonpositive duration")
        captions.append({
            "text": line, "startMs": begin, "endMs": finish,
            "timestampMs": begin, "confidence": None, "pageBreakAfter": True,
        })
        group.clear()

    for word, start, end in cleaned:
        proposed = " ".join([*(g[0] for g in group), word])
        if group and (len(group) >= MAX_CAPTION_WORDS or
                      len(proposed) > MAX_CAPTION_CHARS or
                      end - group[0][1] > MAX_CAPTION_SPAN_MS):
            flush()
        group.append((word, start, end))
        if re.search(r"[.!?][\\\"'’)]*$", word):
            flush()
    flush()
    if not captions:
        raise ValueError("nonempty word data generated zero captions")
    for previous, current in zip(captions, captions[1:]):
        if previous["endMs"] > current["startMs"]:
            raise ValueError("caption groups must not overlap")
    return captions
