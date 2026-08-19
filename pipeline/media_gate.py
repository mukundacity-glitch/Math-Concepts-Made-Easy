"""Fail-closed media gate before YouTube publish.

Refuses upload when the finished lesson package is incomplete.
Does not touch Days 1–19 source curriculum entries.
"""

from __future__ import annotations

import json
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

    return {
        "video": video,
        "thumbnail": thumb,
        "vtt": vtt,
        "srt": srt,
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

    return (len(errors) == 0, errors)


def assert_publishable(day: int) -> None:
    ok, errors = validate_publish_package(day)
    if not ok:
        msg = " | ".join(errors)
        raise SystemExit(
            f"🛑 FAIL-CLOSED media gate for Day {day}: {msg}. "
            f"Refusing YouTube upload."
        )
    print(f"✅ Media gate passed for Day {day}")
