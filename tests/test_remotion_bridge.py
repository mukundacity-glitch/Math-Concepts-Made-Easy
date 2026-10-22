"""Phase 4 Step 3 bridge regression: genuine FFmpeg media files, not mocks."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from pipeline.remotion_bridge import export_lesson_package


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *args],
                   check=True, capture_output=True)


@pytest.fixture
def two_scenes(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("needs FFmpeg")
    media = tmp_path / "manim"
    audio = tmp_path / "voice"
    media.mkdir()
    audio.mkdir()
    for i, (step, color, hz) in enumerate((
        ("concept", "red", "523"), ("worked_example", "cyan", "659"),
    ), 1):
        _ffmpeg("-f", "lavfi", "-i",
                f"color=c={color}:s=320x180:r=30:d=2.25",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(media / f"scene_{i:02d}_{step}.mp4"))
        _ffmpeg("-f", "lavfi", "-i",
                f"sine=frequency={hz}:sample_rate=24000:duration=1.55",
                "-c:a", "libmp3lame", "-q:a", "4",
                str(audio / f"scene_{i:02d}.mp3"))
    script = {
        "lesson_id": 887, "title": "Test Lesson", "channel": "MATH CONCEPTS MADE EASY",
        "subject": "Algebra", "lesson_goal": "Understand the verified method.",
        "scenes": [
            {"scene_id": 1, "step": "concept", "label": "The Concept",
             "learning_purpose": "Observe an independently rendered scene.",
             "duration_seconds": 2.0},
            {"scene_id": 2, "step": "worked_example", "label": "Worked Example",
             "learning_purpose": "Follow the original Manim pixels.",
             "duration_seconds": 2.0},
        ],
    }
    script_path = tmp_path / "timed.json"
    script_path.write_text(json.dumps(script))
    remotion = tmp_path / "remotion"
    return script_path, media, audio, remotion, script


def _export(fixture):
    script, video, audio, root, _ = fixture
    result = export_lesson_package(script, video, audio, root)
    props = json.loads(Path(result["propsPath"]).read_text())
    return result, props


def test_exact_timeline_and_separate_original_tts_voice(two_scenes):
    result, props = _export(two_scenes)
    assert result["chapterCount"] == 2
    assert result["fps"] == 30
    assert result["durationInFrames"] == 60 + 60 + 60 + 60
    assert result["mathPixelsTranscoded"] is False
    assert result["originalCell3VoicePreserved"] is True
    assert [c["id"] for c in props["chapters"]] == ["scene-01", "scene-02"]
    assert [c["stage"] for c in props["chapters"]] == ["concept", "worked_example"]
    for i, chapter in enumerate(props["chapters"], 1):
        media = chapter["media"]
        assert chapter["durationInFrames"] == 60
        assert media["sceneId"] == i
        for key, origin in [("video", two_scenes[1] / (
                f"scene_{i:02d}_" + ["concept", "worked_example"][i-1] + ".mp4")),
                            ("audio", two_scenes[2] / f"scene_{i:02d}.mp3")]:
            copied = two_scenes[3] / "public" / media[f"{key}Src"]
            assert copied.read_bytes() == origin.read_bytes()
            assert hashlib.sha256(copied.read_bytes()).hexdigest() == media[f"{key}Sha256"]


def test_media_export_is_deterministic_and_idempotent(two_scenes):
    one, original = _export(two_scenes)
    two, again = _export(two_scenes)
    assert one["packageId"] == two["packageId"]
    assert original == again
    assert Path(one["publicAssets"]).is_dir()


def test_corrupted_content_addressed_package_is_rejected(two_scenes):
    result, props = _export(two_scenes)
    copied = two_scenes[3] / "public" / props["chapters"][0]["media"]["videoSrc"]
    copied.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="digest mismatch"):
        _export(two_scenes)


def test_missing_media_fails_before_any_writes(two_scenes):
    (two_scenes[2] / "scene_02.mp3").unlink()
    with pytest.raises(ValueError, match="missing or empty"):
        _export(two_scenes)
    assert not (two_scenes[3] / "public").exists()


def test_short_manim_clip_cannot_silently_cut_narration(two_scenes):
    script_path, _, _, _, script = two_scenes
    script["scenes"][1]["duration_seconds"] = 3.2
    script_path.write_text(json.dumps(script))
    with pytest.raises(ValueError, match="shorter than narration"):
        _export(two_scenes)


def test_duplicate_scene_ids_are_rejected(two_scenes):
    script_path, _, _, _, script = two_scenes
    script["scenes"][1]["scene_id"] = 1
    script_path.write_text(json.dumps(script))
    with pytest.raises(ValueError, match="distinct"):
        _export(two_scenes)


def test_unsafe_step_filename_is_rejected(two_scenes):
    script_path, _, _, _, script = two_scenes
    script["scenes"][1]["step"] = "../../upload-secret"
    script_path.write_text(json.dumps(script))
    with pytest.raises(ValueError, match="invalid stage"):
        _export(two_scenes)


def test_wrong_duration_does_not_produce_fake_alignment(two_scenes):
    script_path, _, _, _, script = two_scenes
    script["scenes"][0]["duration_seconds"] = 1.0
    script_path.write_text(json.dumps(script))
    with pytest.raises(ValueError, match="narration exceeds"):
        _export(two_scenes)


def test_export_never_edits_timed_script_or_source_media(two_scenes):
    before = [
        hashlib.sha256(x.read_bytes()).hexdigest() for x in [
            two_scenes[0], *sorted(two_scenes[1].glob("*.mp4")),
            *sorted(two_scenes[2].glob("*.mp3"))
        ]
    ]
    _export(two_scenes)
    after = [
        hashlib.sha256(x.read_bytes()).hexdigest() for x in [
            two_scenes[0], *sorted(two_scenes[1].glob("*.mp4")),
            *sorted(two_scenes[2].glob("*.mp3"))
        ]
    ]
    assert before == after


def _with_real_words(two_scenes):
    for sid in (1, 2):
        data = [
            {"word": "Observe", "start": 0.22, "end": 0.5},
            {"word": "the", "start": 0.52, "end": 0.68},
            {"word": f"scene{sid}.", "start": 0.73, "end": 1.31},
        ]
        (two_scenes[2] / f"scene_{sid:02d}.words.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8",
        )


def test_captioned_bridge_preserves_original_words_and_timing(two_scenes):
    _with_real_words(two_scenes)
    result = export_lesson_package(
        two_scenes[0], two_scenes[1], two_scenes[2], two_scenes[3],
        require_captions=True,
    )
    props = json.loads(Path(result["propsPath"]).read_text())
    assert result["captionCoverage"] == "original_word_boundaries"
    assert result["durationInFrames"] == 240
    for sid, chapter in enumerate(props["chapters"], 1):
        media = chapter["media"]
        assert len(media["captions"]) == 1
        c = media["captions"][0]
        assert c == {
            "text": f"Observe the scene{sid}.",
            "startMs": 220, "endMs": 1310, "timestampMs": 220,
            "confidence": None, "pageBreakAfter": True,
        }
        assert media["captionsSha256"] == hashlib.sha256(
            (two_scenes[2] / f"scene_{sid:02d}.words.json").read_bytes()
        ).hexdigest()
        assert "captionsSha256" not in chapter
        assert "caption" not in chapter["title"].lower()


def test_captioned_source_changes_package_identity(two_scenes):
    _with_real_words(two_scenes)
    first, _ = _export(two_scenes)
    words_path = two_scenes[2] / "scene_01.words.json"
    words = json.loads(words_path.read_text())
    words[0]["word"] = "Notice"
    words_path.write_text(json.dumps(words))
    second, props = _export(two_scenes)
    assert first["packageId"] != second["packageId"]
    assert props["chapters"][0]["media"]["captions"][0]["text"].startswith("Notice")


def test_missing_partial_timing_fails_without_staging(two_scenes):
    _with_real_words(two_scenes)
    (two_scenes[2] / "scene_02.words.json").unlink()
    with pytest.raises(ValueError, match="partial caption"):
        _export(two_scenes)
    assert not (two_scenes[3] / "public").exists()


def test_original_gtts_fallback_can_preserve_media_without_invented_captions(two_scenes):
    result, props = _export(two_scenes)
    assert result["captionCoverage"] == "unavailable"
    assert all("captions" not in c["media"] for c in props["chapters"])
    with pytest.raises(ValueError, match="word timings are required"):
        export_lesson_package(
            two_scenes[0], two_scenes[1], two_scenes[2], two_scenes[3],
            require_captions=True,
        )


def test_out_of_bounds_edge_word_cannot_be_rendered_as_fake_caption(two_scenes):
    _with_real_words(two_scenes)
    file = two_scenes[2] / "scene_01.words.json"
    words = json.loads(file.read_text())
    words[-1]["end"] = 4.0
    file.write_text(json.dumps(words))
    with pytest.raises(ValueError, match="beyond playable"):
        _export(two_scenes)
