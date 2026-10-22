"""Original word-timing to scene-local Remotion Caption JSON contract."""
import json
from pathlib import Path

import pytest
from pipeline.remotion_captions import load_scene_word_captions


def _write(tmp_path, data):
    path = tmp_path / "scene_01.words.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def words():
    return [
        {"word": "Solve", "start": 0.19, "end": 0.46},
        {"word": "x", "start": 0.50, "end": 0.63},
        {"word": "plus", "start": 0.68, "end": 0.86},
        {"word": "two.", "start": 0.89, "end": 1.15},
        {"word": "Subtract", "start": 1.3, "end": 1.6},
        {"word": "two.", "start": 1.64, "end": 1.91},
    ]


def test_precise_punctuation_pages_and_timestamp_contract(tmp_path):
    p = _write(tmp_path, words())
    lines = load_scene_word_captions(p, clip_seconds=2.2, audio_seconds=2.05)
    assert [v["text"] for v in lines] == [
        "Solve x plus two.", "Subtract two.",
    ]
    assert [(v["startMs"], v["endMs"]) for v in lines] == [
        (190, 1150), (1300, 1910),
    ]
    assert all(v["confidence"] is None and
               v["pageBreakAfter"] is True and
               v["timestampMs"] == v["startMs"] for v in lines)


def test_missing_or_empty_original_word_events_never_fabricate_captions(tmp_path):
    assert load_scene_word_captions(
        tmp_path / "no-words.json", clip_seconds=2, audio_seconds=2
    ) is None
    assert load_scene_word_captions(
        _write(tmp_path, []), clip_seconds=2, audio_seconds=2
    ) is None


@pytest.mark.parametrize("bad", [
    {"word": "Hello", "start": 0.25, "end": 0.25},
    {"word": "Hello", "start": float("nan"), "end": 0.5},
    {"word": "Hello", "start": -1, "end": 0.5},
    {"word": "", "start": 0.25, "end": 0.5},
    {"word": "A\nB", "start": 0.25, "end": 0.5},
])
def test_invalid_word_event_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        load_scene_word_captions(
            _write(tmp_path, [bad]), clip_seconds=2, audio_seconds=2,
        )


def test_caption_that_outlasts_original_sound_or_scene_is_rejected(tmp_path):
    for limit in [(1.5, 2.1), (2.1, 1.5)]:
        with pytest.raises(ValueError, match="beyond playable"):
            load_scene_word_captions(
                _write(tmp_path, words()),
                clip_seconds=limit[0], audio_seconds=limit[1],
            )


def test_large_backward_boundary_overlap_rejected(tmp_path):
    data = words()
    data[1]["start"] = 0.33
    with pytest.raises(ValueError, match="overlapping"):
        load_scene_word_captions(
            _write(tmp_path, data), clip_seconds=2.2, audio_seconds=2.1,
        )


def test_short_edge_tts_word_overlap_is_clamped_without_narration_drift(tmp_path):
    data = words()
    data[1]["start"] = 0.45
    result = load_scene_word_captions(
        _write(tmp_path, data), clip_seconds=2.2, audio_seconds=2.1,
    )
    assert result[0]["startMs"] == 190
    assert result[0]["endMs"] == 1150


def test_no_synthetic_text_or_discarded_words_in_long_group(tmp_path):
    raw = [
        {"word": "word" + str(n), "start": 0.15 + n * 0.22,
         "end": 0.31 + n * 0.22}
        for n in range(13)
    ]
    c = load_scene_word_captions(
        _write(tmp_path, raw), clip_seconds=3.5, audio_seconds=3.3,
    )
    assert " ".join(x["text"] for x in c) == " ".join(x["word"] for x in raw)
    assert len(c) >= 2
    assert max(len(x["text"]) for x in c) <= 52
