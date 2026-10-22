"""Build two tiny **synthetic** media fixtures for Phase 4 Step 3 only.

This is a 2-chapter MEDIA-BRIDGE test, not a complete math lesson,
not authentic Manim math, and not the Step 6 full hybrid demo.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "remotion" / "build" / "phase4-step3-input"
RENDER = BASE / "renders"
AUDIO = BASE / "audio"


def ffmpeg(*args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *args],
        check=True,
    )


def main() -> None:
    RENDER.mkdir(parents=True, exist_ok=True)
    AUDIO.mkdir(parents=True, exist_ok=True)
    scenes = []
    for sid, step, color, tone in (
        (1, "concept", "#C0262D", "523"),
        (2, "worked_example", "#00B6D9", "659"),
    ):
        video = RENDER / f"scene_{sid:02d}_{step}.mp4"
        speech = AUDIO / f"scene_{sid:02d}.mp3"
        ffmpeg("-f", "lavfi", "-i",
               f"color=c={color}:s=1280x720:r=30:d=2.27",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video))
        ffmpeg("-f", "lavfi", "-i",
               f"sine=frequency={tone}:sample_rate=24000:duration=1.55",
               "-c:a", "libmp3lame", "-q:a", "4", str(speech))
        # Synthetic timestamp proof. These are NOT spoken sentences;
        # the audio fixture is a sine wave for transport-only QA.
        words = [
            {"word": "Caption", "start": 0.25, "end": 0.56},
            {"word": "bridge", "start": 0.58, "end": 0.91},
            {"word": f"scene{sid}.", "start": 0.95, "end": 1.40},
        ]
        (AUDIO / f"scene_{sid:02d}.words.json").write_text(
            json.dumps(words, indent=2) + "\\n", encoding="utf-8",
        )
        scenes.append({
            "scene_id": sid,
            "step": step,
            "label": f"Fixture {sid} — {step.replace('_', ' ').title()}",
            "learning_purpose": "Media timing fixture, not curriculum content.",
            "duration_seconds": 2.0,
        })
    data = {
        "lesson_id": 888,
        "title": "Media Bridge Engineering Check",
        "channel": "MATH CONCEPTS MADE EASY",
        "subject": "Mathematics",
        "lesson_goal": "Validate Remotion media transport without a full lesson.",
        "scenes": scenes,
    }
    script = BASE / "lesson_888_script_timed.json"
    script.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(str(script))


if __name__ == "__main__":
    main()
