"""Fail-closed media gate before YouTube publish.

Refuses upload when the finished lesson package is incomplete.
Does not touch Days 1–21 source curriculum entries.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from pipeline.paths import BASE_DIR


def _ok_file(path: Path, min_bytes: int = 1000) -> bool:
    try:
        return path.exists() and path.stat().st_size >= min_bytes
    except OSError:
        return False


def _duration(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        ).strip()
        return float(out)
    except Exception:
        return 0.0


def _name_matches_day(name: str, day: int) -> bool:
    n = name.lower()
    patterns = [
        f"day_{day:03d}", f"day_{day:02d}", f"day_{day}",
        f"day{day:03d}", f"day{day:02d}", f"day{day}",
        f"day-{day:03d}", f"day-{day}",
    ]
    return any(pat in n for pat in patterns)


def find_day_outputs(day: int) -> dict:
    """Locate final video/captions/thumbnail for a day under output/."""
    day = int(day)
    finals = list((BASE_DIR / "final_videos").glob("*.mp4")) if (BASE_DIR / "final_videos").exists() else []
    candidates = [p for p in sorted(finals)
                  if _name_matches_day(p.name, day) and "_short_" not in p.name.lower()]
    video = candidates[0] if candidates else None
    if video is None and len(finals) == 1 and "_short_" not in finals[0].name.lower():
        video = finals[0]

    thumbs = []
    tdir = BASE_DIR / "thumbnails"
    if tdir.exists():
        thumbs = list(tdir.glob("*.jpg")) + list(tdir.glob("*.png"))
    thumb = None
    for p in sorted(thumbs):
        if _name_matches_day(p.name, day):
            thumb = p
            break
    if thumb is None and len(thumbs) == 1:
        thumb = thumbs[0]

    caps = []
    if video:
        caps = list(video.parent.glob(video.stem + ".*"))
    vtt = next((p for p in caps if p.suffix.lower() == ".vtt"), None)
    srt = next((p for p in caps if p.suffix.lower() == ".srt"), None)
    shorts = {}
    for key in ("HOOK", "FORMULA", "MISTAKE"):
        shorts[key] = next(
            (
                path for path in sorted(finals)
                if _name_matches_day(path.name, day)
                and f"_short_{key.lower()}" in path.name.lower()
            ),
            None,
        )

    return {
        "video": video,
        "thumbnail": thumb,
        "vtt": vtt,
        "srt": srt,
        "shorts": shorts,
    }


def validate_publish_package(day: int) -> tuple[bool, list[str]]:
    """Return (ok, errors). Fail closed."""
    errors: list[str] = []
    if int(day) < 1:
        errors.append("invalid day")
        return False, errors

    outs = find_day_outputs(day)
    video = outs["video"]
    if video is None or not _ok_file(video, 50_000):
        errors.append("missing/too-small final MP4 in output/final_videos")
    else:
        dur = _duration(video)
        if dur < 60:
            errors.append(f"MP4 duration too short: {dur:.1f}s")
        # must have audio stream
        try:
            probe = subprocess.check_output(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "stream=codec_type", "-of", "csv=p=0", str(video),
                ],
                text=True,
            )
            if "audio" not in probe:
                errors.append("MP4 has no audio stream")
            if "video" not in probe:
                errors.append("MP4 has no video stream")
        except Exception as e:
            errors.append(f"ffprobe failed: {e}")

    if outs["thumbnail"] is None or not _ok_file(outs["thumbnail"], 1000):
        errors.append("missing thumbnail image")

    if outs["vtt"] is None and outs["srt"] is None:
        errors.append("missing captions (.vtt or .srt)")
    else:
        cap = outs["vtt"] or outs["srt"]
        if not _ok_file(cap, 50):
            errors.append("captions file too small")

    for key, short in outs["shorts"].items():
        if short is None or not _ok_file(short, 50_000):
            errors.append(f"missing/too-small {key} Short")
            continue
        duration = _duration(short)
        if duration <= 0 or duration > 180.05:
            errors.append(f"{key} Short duration invalid: {duration:.1f}s")
        try:
            streams = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(short),
            ], text=True))["streams"]
            picture = next(s for s in streams if s["codec_type"] == "video")
            if (picture["width"], picture["height"]) != (1080, 1920):
                errors.append(f"{key} Short is not native 1080x1920")
            if not any(s["codec_type"] == "audio" for s in streams):
                errors.append(f"{key} Short has no narration stream")
        except Exception as exc:
            errors.append(f"{key} Short stream verification failed: {exc}")

    if os.environ.get("MCME_REQUIRE_NATIVE_SHORTS") == "1":
        try:
            from pipeline.remotion_bridge import _sha256
            receipt = json.loads((BASE_DIR / "final_videos" / f"Day_{day:03d}_native-shorts.json").read_text())
            if receipt["format"] != "native-portrait-v1" or receipt["day"] != day:
                raise ValueError("wrong native Shorts provenance")
            for key, short in outs["shorts"].items():
                if receipt["shorts"][key]["sha256"] != _sha256(short):
                    raise ValueError(f"{key} differs from its verified native render")
        except Exception as exc:
            errors.append(f"native Shorts provenance failed: {exc}")

    if os.environ.get("MCME_REQUIRE_CINEMATIC") == "1":
        try:
            validate_cinematic_receipt(day, video)
        except Exception as exc:
            errors.append(f"cinematic master provenance failed: {exc}")

    return (len(errors) == 0, errors)


def validate_cinematic_receipt(day: int, video: Path | None) -> None:
    from pipeline.remotion_bridge import _sha256
    receipt_path = BASE_DIR / "final_videos" / f"Day_{day:03d}_cinematic-qa.json"
    receipt = json.loads(receipt_path.read_text())
    if (receipt["format"] != "cinematic-v1" or receipt["day"] != day or
        not video or receipt["videoSha256"] != _sha256(video) or
        not isinstance(receipt["narrationBeats"], int) or receipt["narrationBeats"] <= 0 or
        receipt["narrationBeats"] != receipt["verifiedNarrationBeats"] or
        (receipt["width"], receipt["height"]) != (1920, 1080) or
        receipt["minimumLabelSize"] < 42 or receipt["unreadableFallbackAllowed"]):
        raise ValueError("Cinematic picture, voice or readability evidence does not match the video")


def assert_publishable(day: int) -> None:
    ok, errors = validate_publish_package(day)
    if not ok:
        msg = " | ".join(errors)
        raise SystemExit(
            f"🛑 FAIL-CLOSED media gate for Day {day}: {msg}. "
            f"Refusing YouTube upload."
        )
    print(f"✅ Media gate passed for Day {day}")

