#!/usr/bin/env python3
"""Build one day of the Rational Numbers series, end to end.

    python generate_day.py 2                # narration + video + captions + thumbnail
    python generate_day.py 2 --quality l    # fast preview
    python generate_day.py 2 --no-audio     # silent render, estimated timing

Everything lands in ``output/rational_series/dayNN/``:

    day02_irrational_numbers.mp4    the video
    day02_irrational_numbers.srt    captions, timed from the real render
    day02_thumbnail.png             thumbnail in the day's palette
    day02_cues.json                 block timings + palette + intro plan
    audio/                          cached narration (reused on re-renders)

``render_day.py`` is the thin CLI wrapper around this module.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rational_series.color_engine import palette_for_day  # noqa: E402
from rational_series.script_parser import (  # noqa: E402
    DayScript,
    ScriptError,
    available_days,
    load_day,
    load_script,
    script_path_for_day,
    srt_from_cues,
)

#: CLI shorthand -> manim quality preset
QUALITIES = {
    "l": "low_quality",  # 480p15  — fast iteration
    "m": "medium_quality",  # 720p30
    "h": "high_quality",  # 1080p60 — the publishing default
    "p": "production_quality",  # 1440p60
    "k": "fourk_quality",  # 2160p60
}

# Override with RS_OUTPUT_DIR (Colab/Drive, CI artefact dirs…).
OUTPUT_ROOT = Path(os.environ.get("RS_OUTPUT_DIR") or REPO_ROOT / "output" / "rational_series")
STATE_PATH = REPO_ROOT / "state" / "rational_series.json"


@dataclass
class DayArtifacts:
    """Where everything for a rendered day ended up."""

    day: int
    title: str
    video: Optional[Path]
    thumbnail: Optional[Path]
    captions: Optional[Path]
    cues: Optional[Path]
    duration: float
    seconds_to_render: float

    def summary(self) -> str:
        lines = [f"✅ Day {self.day} — {self.title}  ({self.duration:.1f}s of video in {self.seconds_to_render:.0f}s)"]
        for label, path in (
            ("video    ", self.video),
            ("thumbnail", self.thumbnail),
            ("captions ", self.captions),
            ("cues     ", self.cues),
        ):
            if path:
                lines.append(f"   {label} {path}")
        return "\n".join(lines)


def day_output_dir(day: int) -> Path:
    return OUTPUT_ROOT / f"day{day:02d}"


def generate_day(
    day: int,
    *,
    script_path: Optional[str] = None,
    quality: str = "h",
    audio: bool = True,
    thumbnail: bool = True,
    video: bool = True,
    block_limit: Optional[int] = None,
    scripts_dir: Optional[str] = None,
) -> DayArtifacts:
    """Render a whole day. The only day-specific input is its script file."""
    from manim import tempconfig

    from rational_series.rational_series_scene import RationalNumberDayScene

    started = time.time()
    script: DayScript = load_script(script_path) if script_path else load_day(day, scripts_dir)
    script.validate()
    day = script.day

    out_dir = day_output_dir(day)
    out_dir.mkdir(parents=True, exist_ok=True)
    palette = palette_for_day(day)

    print(f"\n🎨 Day {day} palette — hue {palette.hue:.0f}°  bg {palette.background}  accent {palette.accent}")
    print(f"📄 script: {script.source_path}")
    print(f"🗣  {len(script.blocks)} narration blocks, ~{script.total_duration/60:.1f} min\n")

    video_path: Optional[Path] = None
    cues_path: Optional[Path] = None
    captions_path: Optional[Path] = None
    duration = script.total_duration

    if video:
        cues_path = out_dir / f"day{day:02d}_cues.json"
        settings = {
            "quality": QUALITIES.get(quality, QUALITIES["h"]),
            "media_dir": str(out_dir / "media"),
            "output_file": script.slug,
            "disable_caching": True,
            "verbosity": "WARNING",
        }
        with tempconfig(settings):
            scene = RationalNumberDayScene(
                day_number=day,
                script_path=str(script.source_path),
                audio=audio,
                audio_dir=str(out_dir / "audio"),
                cue_path=str(cues_path),
                block_limit=block_limit,
            )
            try:
                scene.render()
            except BaseException:
                # Manim's frame-writing thread is not a daemon: without this
                # a failed render hangs the process at interpreter exit
                # instead of showing the traceback and stopping.
                _release_writer_thread(scene)
                raise
            rendered = Path(scene.renderer.file_writer.movie_file_path)

        video_path = out_dir / f"{script.slug}.mp4"
        shutil.copy2(rendered, video_path)

        cues = json.loads(cues_path.read_text(encoding="utf-8"))
        duration = float(cues.get("duration", duration))
        captions_path = out_dir / f"{script.slug}.srt"
        captions_path.write_text(srt_from_cues(cues["blocks"]), encoding="utf-8")

    thumbnail_path: Optional[Path] = None
    if thumbnail:
        try:
            from rational_series.thumbnail import render_for_script

            thumbnail_path = render_for_script(script, out_dir / f"day{day:02d}_thumbnail.png")
        except ImportError:
            print("⚠️  Pillow is not installed — skipping the thumbnail (pip install pillow)")

    _record_progress(day)

    return DayArtifacts(
        day=day,
        title=script.title,
        video=video_path,
        thumbnail=thumbnail_path,
        captions=captions_path,
        cues=cues_path,
        duration=duration,
        seconds_to_render=time.time() - started,
    )


def _release_writer_thread(scene: object) -> None:
    """Unblock Manim's writer thread after a failed render (best effort)."""
    try:
        writer = scene.renderer.file_writer  # type: ignore[attr-defined]
        writer.queue.put((-1, None))
        writer.writer_thread.join(timeout=5)
    except Exception:
        pass


def _record_progress(day: int) -> None:
    """Track which days exist so ``--next`` can pick the following one up."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {"rendered": [], "next_day": 2, "last_run": None}
    if STATE_PATH.exists():
        try:
            state.update(json.loads(STATE_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    rendered = sorted(set(state.get("rendered", [])) | {day})
    remaining = [d for d in available_days() if d not in rendered]
    state.update(
        {
            "rendered": rendered,
            "next_day": remaining[0] if remaining else max(rendered) + 1,
            "last_run": datetime.now().isoformat(timespec="seconds"),
        }
    )
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def next_unrendered_day() -> Optional[int]:
    """The lowest day that has a script but has not been rendered yet."""
    rendered = set()
    if STATE_PATH.exists():
        try:
            rendered = set(json.loads(STATE_PATH.read_text(encoding="utf-8")).get("rendered", []))
        except json.JSONDecodeError:
            pass
    for day in available_days():
        if day not in rendered:
            return day
    return None


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render one day of the Rational Numbers series.")
    parser.add_argument("day", type=int, nargs="?", help="day number (defaults to the next unrendered day)")
    parser.add_argument("--script", help="explicit script path (overrides the day lookup)")
    parser.add_argument("--quality", choices=sorted(QUALITIES), default="h", help="l=480p15 … k=4K (default h=1080p60)")
    parser.add_argument("--no-audio", action="store_true", help="skip TTS; time the visuals from the speaking model")
    parser.add_argument("--no-thumbnail", action="store_true")
    parser.add_argument("--thumbnail-only", action="store_true", help="regenerate just the thumbnail")
    parser.add_argument("--blocks", type=int, help="render only the first N blocks (quick preview)")
    parser.add_argument("--scripts-dir", help="where day scripts live (default rational_series/scripts)")
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv)
    day = args.day if args.day is not None else next_unrendered_day()
    if day is None:
        print("Nothing to render: every script in rational_series/scripts has been rendered.")
        return 0
    try:
        if args.script is None and not args.scripts_dir:
            script_path_for_day(day)  # fail fast with a helpful message
        artifacts = generate_day(
            day,
            script_path=args.script,
            quality=args.quality,
            audio=not args.no_audio,
            thumbnail=not args.no_thumbnail,
            video=not args.thumbnail_only,
            block_limit=args.blocks,
            scripts_dir=args.scripts_dir,
        )
    except ScriptError as exc:
        print(f"🛑 {exc}")
        return 2
    print("\n" + artifacts.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
