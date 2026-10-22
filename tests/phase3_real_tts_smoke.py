"""Generate real (not synthetic) premium Edge-TTS speech and validate all 25 cues.

CI smoke only. Does not touch publishing state, channel credentials, or
production curriculum. Fails closed when the speech provider is unavailable.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

from pipeline.mathtext import normalize_word
from pipeline.premium_animation import build_premium_visual_plan
from pipeline.premium_audio_qa import validate_premium_word_alignment

ROOT = Path(__file__).resolve().parents[1]
LESSON = json.loads((ROOT / "examples/premium_algebra_lesson.json").read_text())
OUT = ROOT / "build" / "phase3-smoke" / "real_audio"


async def synthesize(scene_id: int, stage: dict) -> dict:
    audio_file = OUT / f"scene_{scene_id:02d}.mp3"
    words_file = OUT / f"scene_{scene_id:02d}.words.json"
    voice = "en-GB-RyanNeural"
    last_error = None
    for attempt in range(3):
        try:
            words = []
            communication = edge_tts.Communicate(
                text=stage["narration"], voice=voice, rate="+20%"
            )
            with audio_file.open("wb") as outfile:
                async for chunk in communication.stream():
                    if chunk["type"] == "audio":
                        outfile.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start = chunk["offset"] / 10_000_000
                        end = (chunk["offset"] + chunk["duration"]) / 10_000_000
                        words.append({
                            "word": chunk["text"], "norm": normalize_word(chunk["text"]),
                            "start": round(start, 4), "end": round(end, 4),
                        })
            if not audio_file.is_file() or audio_file.stat().st_size < 10000:
                raise ValueError("Edge-TTS returned an empty audio asset")
            if not words:
                raise ValueError("Edge-TTS emitted no word boundaries")
            duration = float(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(audio_file),
            ], text=True).strip()) + 0.65
            scene = {
                "premium_items": stage["items"],
                "duration_seconds": duration,
            }
            report = validate_premium_word_alignment(scene, words)
            words_file.write_text(json.dumps(words, indent=2) + "\n")
            return {
                "stage": stage["stage"], "scene_id": scene_id,
                "duration_seconds": duration,
                "audio_file": str(audio_file),
                "words_file": str(words_file),
                "verified": report,
            }
        except (ValueError, RuntimeError, OSError, edge_tts.exceptions.NoAudioReceived) as exc:
            last_error = exc
            await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"real premium TTS failed to verify {stage['stage']}: {last_error}")


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stages = build_premium_visual_plan(LESSON)["stages"]
    reports = []
    for scene_id, stage_key in ((6, "worked_example"), (8, "practice")):
        reports.append(await synthesize(scene_id, stages[stage_key]))
    if sum(r["verified"]["verified_items"] for r in reports) != 25:
        raise RuntimeError("real TTS skipped a verified problem")
    report = {"passed": True, "synthetic": False, "scenes": reports}
    (OUT / "audio-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
