"""Validate premium TTS cues against genuine-style Edge word boundary data."""
import copy
import json
from pathlib import Path

import pytest

from pipeline.mathtext import normalize_word
from pipeline.premium_animation import build_premium_visual_plan
from pipeline.premium_audio_qa import validate_premium_word_alignment

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def prepared():
    lesson = json.loads((ROOT / "examples/premium_algebra_lesson.json").read_text())
    plan = build_premium_visual_plan(lesson)["stages"]["worked_example"]
    tokens = [t for t in plan["narration"].split() if normalize_word(t)]
    words = [
        {"word": token, "norm": normalize_word(token),
         "start": i * 0.12, "end": (i + 1) * 0.12}
        for i, token in enumerate(tokens)
    ]
    scene = {"premium_items": plan["items"],
             "duration_seconds": len(tokens) * 0.12 + 0.65}
    return scene, words


def test_all_worked_example_audio_anchors_present(prepared):
    scene, words = prepared
    result = validate_premium_word_alignment(scene, words)
    assert result["verified_items"] == 10
    assert result["verified_spoken_cues"] == 40
    assert result["spoken_word_count"] > 100


def test_missing_real_word_boundaries_blocks_premium_publication(prepared):
    scene, _ = prepared
    with pytest.raises(ValueError, match="Edge-TTS word boundaries"):
        validate_premium_word_alignment(scene, [])


def test_corrupt_or_missing_spoken_cue_is_rejected(prepared):
    scene, words = prepared
    words = copy.deepcopy(words)
    words[0]["norm"] = "injected"
    with pytest.raises(ValueError, match="spoken cue missing"):
        validate_premium_word_alignment(scene, words)


def test_out_of_order_and_out_of_duration_timestamp_fail(prepared):
    scene, words = prepared
    words = copy.deepcopy(words)
    words[2]["start"] = -0.2
    with pytest.raises(ValueError, match="out of range"):
        validate_premium_word_alignment(scene, words)
    scene, words = prepared
    scene["duration_seconds"] = 1
    with pytest.raises(ValueError, match="out of range"):
        validate_premium_word_alignment(scene, words)


def test_legacy_audio_does_not_require_premium_fields():
    assert validate_premium_word_alignment({"step": "practice"}, []) is None
