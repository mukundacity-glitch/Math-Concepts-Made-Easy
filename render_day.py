#!/usr/bin/env python3
"""Render days of the Rational Numbers series.

    python render_day.py --day 2                 # 1080p60 with narration
    python render_day.py --day 3
    python render_day.py --day 2 --quality l     # 480p15 preview
    python render_day.py --next                  # the next unrendered day
    python render_day.py --all                   # every script that has a file
    python render_day.py --list                  # what's available / done

Adding Day 4 means dropping ``rational_series/scripts/day4.json`` in place
and running ``python render_day.py --day 4``.  Nothing else.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generate_day import QUALITIES, generate_day, next_unrendered_day  # noqa: E402
from rational_series.color_engine import palette_for_day  # noqa: E402
from rational_series.script_parser import ScriptError, available_days, load_day  # noqa: E402


def _list_days(scripts_dir: Optional[str]) -> int:
    days = available_days(scripts_dir)
    if not days:
        print("No day scripts found in rational_series/scripts/")
        return 1
    pending = next_unrendered_day()
    print(f"{'day':>4}  {'title':<34} {'blocks':>6} {'minutes':>8}  palette")
    for day in days:
        try:
            script = load_day(day, scripts_dir)
        except ScriptError as exc:
            print(f"{day:>4}  ⚠️  {exc}")
            continue
        palette = palette_for_day(day)
        marker = "→" if day == pending else " "
        print(
            f"{day:>4}{marker} {script.title:<34} {len(script.blocks):>6} "
            f"{script.total_duration/60:>8.1f}  {palette.background} / {palette.accent}"
        )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--day", type=int, help="day number to render")
    target.add_argument("--all", action="store_true", help="render every day that has a script")
    target.add_argument("--next", action="store_true", help="render the next unrendered day")
    target.add_argument("--list", action="store_true", help="show available days and exit")
    parser.add_argument("--quality", choices=sorted(QUALITIES), default="h", help="l/m/h/p/k (default h = 1080p60)")
    parser.add_argument("--no-audio", action="store_true", help="silent render, timing from the speaking model")
    parser.add_argument("--no-thumbnail", action="store_true")
    parser.add_argument("--thumbnail-only", action="store_true")
    parser.add_argument("--blocks", type=int, help="render only the first N blocks (preview)")
    parser.add_argument("--scripts-dir", help="alternate scripts directory")
    args = parser.parse_args(argv)

    if args.list:
        return _list_days(args.scripts_dir)

    if args.all:
        days = available_days(args.scripts_dir)
    elif args.next:
        pending = next_unrendered_day()
        if pending is None:
            print("Every available day has been rendered.")
            return 0
        days = [pending]
    elif args.day is not None:
        days = [args.day]
    else:
        parser.error("choose --day N, --next, --all or --list")
        return 2

    failures = 0
    for day in days:
        try:
            artifacts = generate_day(
                day,
                quality=args.quality,
                audio=not args.no_audio,
                thumbnail=not args.no_thumbnail,
                video=not args.thumbnail_only,
                block_limit=args.blocks,
                scripts_dir=args.scripts_dir,
            )
            print("\n" + artifacts.summary())
        except ScriptError as exc:
            failures += 1
            print(f"🛑 Day {day}: {exc}")
        except Exception as exc:  # keep a batch run going
            failures += 1
            print(f"🛑 Day {day} failed: {exc.__class__.__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
