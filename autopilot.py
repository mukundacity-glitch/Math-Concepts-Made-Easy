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

from pipeline.paths import BASE_DIR, read_state, write_state
from pipeline.curriculum import MASTER_CURRICULUM, TOTAL_DAYS, get_lesson

STAGES = [
    ("Lesson & narration builder", "pipeline.cell1_lesson"),
    ("Script builder",             "pipeline.cell2_script"),
    ("Audio engine (Edge-TTS)",    "pipeline.cell3_audio"),
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
    parser.add_argument("--no-advance", action="store_true",
                        help="do not advance state/progress.json (re-runs, tests)")
    args = parser.parse_args()

    state = read_state()
    day = args.day if args.day is not None else int(state.get("next_day", 1))

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
    print(f"{'═' * 65}")

    for i, (name, module) in enumerate(STAGES, start=1):
        if i < args.from_stage:
            print(f"  ⏭  Skipping stage {i} — {name}")
            continue
        run_stage(i, name, module, day)

    # ── Record progress ───────────────────────────────────────
    if not args.no_advance:
        state = read_state()
        if day not in state.setdefault("completed", []):
            state["completed"].append(day)
        state["next_day"] = day + 1
        state["last_run"] = datetime.datetime.now().isoformat(timespec="seconds")
        write_state(state)
        print(f"\n✅ Progress saved — next scheduled lesson: Day {day + 1}")

    # ── Optional YouTube upload ───────────────────────────────
    if args.upload:
        from uploader.youtube_upload import credentials_available, upload_day
        if not credentials_available():
            print("\n⚠️  YouTube is not linked yet — skipping upload.")
            print("   See README → 'Linking your YouTube channel' for the "
                  "one-time setup. The finished video is waiting in "
                  f"{BASE_DIR / 'final_videos'}")
        else:
            upload_day(day)
            state = read_state()
            if day not in state.setdefault("uploaded", []):
                state["uploaded"].append(day)
            write_state(state)

    safe = lesson["seo_title"].replace(" ", "_").replace("—", "-")
    print(f"\n{'═' * 65}")
    print(f"  🎉 DAY {day} COMPLETE — {lesson['topic']}")
    print(f"  🎬 Video     : final_videos/Day_{day:03d}_{safe}.mp4")
    print(f"  📱 Short     : final_videos/Day_{day:03d}_{safe}_SHORTS.mp4")
    print(f"  🖼  Thumbnail : thumbnails/Day_{day:03d}_{safe}_Thumb.jpg")
    print(f"  📝 Subtitles : final_videos/Day_{day:03d}_{safe}.srt / .vtt")
    print(f"{'═' * 65}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
