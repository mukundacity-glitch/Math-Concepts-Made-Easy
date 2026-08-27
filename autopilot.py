#!/usr/bin/env python3
"""Autopilot — produce one full daily lesson with a single command.

    python autopilot.py                # produce the next scheduled day
    python autopilot.py --day 5        # produce a specific day
    python autopilot.py --upload       # also post to YouTube (once linked)
    python autopilot.py --from-stage 4 # resume after a failed render

Runs every pipeline stage in order, then advances state/progress.json
so tomorrow's run automatically picks the next lesson. Uploading is a
no-op with a friendly warning until YouTube credentials are configured
(see README — "Linking your YouTube channel").
"""

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.paths import (
    BASE_DIR, load_cell1_config, read_state, safe_filename, write_state,
)
from pipeline.curriculum import TOTAL_DAYS, get_lesson
from pipeline.progress import mark_uploaded, validate_next_publish_day

STAGES = [
    ("Lesson & narration builder", "pipeline.cell1_lesson"),
    ("Script builder",             "pipeline.cell2_script"),
    ("Audio engine (Edge-TTS)",    "pipeline.cell3_audio"),
    ("Semantic manifest QA",       "pipeline.cell9_quality"),
    ("Manim animation engine",     "pipeline.cell4_animation"),
    ("Video assembly",             "pipeline.cell5_assembly"),
    ("Subtitle engine",            "pipeline.cell8_subtitles"),
    ("Thumbnail engine",           "pipeline.cell6_thumbnail"),
    ("Shorts generator",           "pipeline.cell7_shorts"),
]


def run_stage(index: int, name: str, module: str, day: int):
    print(f"\n{'█' * 65}")
    print(f"  STAGE {index}/{len(STAGES)} — {name}  (Day {day})")
    print(f"{'█' * 65}\n", flush=True)
    env = dict(os.environ, LESSON_DAY=str(day))
    subprocess.run([sys.executable, "-m", module],
                   cwd=REPO_ROOT, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--day", type=int, default=None,
                        help="lesson day to produce (default: next from state/progress.json)")
    parser.add_argument("--from-stage", type=int, default=1,
                        help="1-based stage number to resume from")
    parser.add_argument("--upload", action="store_true",
                        help="upload the finished video + short to YouTube")
    parser.add_argument("--skip-media-gate", action="store_true",
                        help="dangerous: allow upload without media gate (default off)")
    parser.add_argument("--no-advance", action="store_true",
                        help="do not advance state/progress.json (re-runs, tests)")
    parser.add_argument("--allow-locked-day", action="store_true",
                        help="EMERGENCY only: allow rendering a locked posted day. Default: blocked.")
    args = parser.parse_args()

    state = read_state()
    if args.allow_locked_day:
        day = args.day if args.day is not None else int(state["next_day"])
    else:
        try:
            day = validate_next_publish_day(state, args.day)
        except ValueError as exc:
            print(f"🛑 {exc}")
            print("   Refusing to run. (Emergency render override: --allow-locked-day)")
            return 2


    # ── Launch date guard ───────────────────────────────────────
    # Blocks any production/upload before the official Day 1 date.
    # Runs before any stage, before progress.json is touched.
    from pipeline.paths import START_DATE
    today = datetime.date.today()
    if today < START_DATE:
        print(f"⏸️  Publishing paused. Launch date is {START_DATE:%d/%m/%Y}. "
              f"Current date is before official Day 1.")
        return 0

    if day > TOTAL_DAYS:
        print(f"🎓 Curriculum complete — all {TOTAL_DAYS} lessons produced. "
              f"Add more lessons to curriculum/*.json to continue.")
        return 0

    lesson = get_lesson(day)
    print(f"{'═' * 65}")
    print(f"  🚀 AUTOPILOT — Day {day}/{TOTAL_DAYS}")
    print(f"  📚 {lesson['subject']} → {lesson['topic']}")
    print(f"  🗓  {datetime.date.today():%A, %d %B %Y}")
    print(f"  📂 Output: {BASE_DIR}")
    print(f"  🎨 Engine : ENGINE_VISUAL_V4 (scene manifest + semantic QA)")
    print(f"{'═' * 65}")

    for i, (name, module) in enumerate(STAGES, start=1):
        if i < args.from_stage:
            print(f"  ⏭  Skipping stage {i} — {name}")
            continue
        run_stage(i, name, module, day)

    # ── Optional YouTube upload ───────────────────────────────
    upload_succeeded = False
    if args.upload:
        # Fail-closed: refuse upload without real finished media package.
        if not getattr(args, "skip_media_gate", False):
            from pipeline.media_gate import assert_publishable
            assert_publishable(day)

        from uploader.youtube_upload import credentials_available, upload_day
        if not credentials_available():
            upload_succeeded = False
            print("\n⚠️  YouTube is not linked yet — skipping upload.")
            print("   See README → 'Linking your YouTube channel' for the "
                  "one-time setup. The finished video is waiting in "
                  f"{BASE_DIR / 'final_videos'}")
        else:
            upload_day(day)
            upload_succeeded = True

    # ── Record progress only after all requested work succeeds ──
    if not args.no_advance and args.upload and upload_succeeded:
        from pipeline.creative_history import record_lesson

        state = read_state()
        mark_uploaded(state, day)
        write_state(state)
        config = load_cell1_config()
        record_lesson(
            day,
            config.LESSON_PLAN["hook_variant"],
            config.LESSON_PLAN["outro_variant"],
        )
        print(f"\n✅ Progress saved — next scheduled lesson: Day {day + 1}")
    elif not args.no_advance and args.upload:
        print("\n⏸️  Progress not advanced because the requested upload did not succeed.")
    elif not args.no_advance:
        state = read_state()
        if day not in state.setdefault("completed", []):
            state["completed"].append(day)
            state["completed"].sort()
        write_state(state)
        print(
            f"\n⏸️  Render saved; publishing remains on Day {state['next_day']} "
            "until its YouTube upload succeeds."
        )

    safe = safe_filename(lesson["seo_title"])
    print(f"\n{'═' * 65}")
    print(f"  🎉 DAY {day} COMPLETE — {lesson['topic']}")
    print(f"  🎬 Video     : final_videos/Day_{day:03d}_{safe}.mp4")
    for short_key in ("HOOK", "FORMULA", "MISTAKE"):
        print(f"  📱 Short     : final_videos/Day_{day:03d}_{safe}_SHORT_{short_key}.mp4")
    print(f"  🖼  Thumbnail : thumbnails/Day_{day:03d}_{safe}_Thumb.jpg")
    print(f"  📝 Subtitles : final_videos/Day_{day:03d}_{safe}.srt / .vtt")
    print(f"{'═' * 65}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
