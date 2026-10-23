"""Verify real final streams, source identity, speech alignment, and review frames."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from run_phase4_hybrid_demo import BASE, EVIDENCE, OUTPUT, PROPS, SCRIPT, digest, protect, read_json, write_json


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ], text=True))


def frame(video: Path, seconds: float, path: Path) -> None:
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(seconds),
                    "-i", str(video), "-frames:v", "1", str(path)], check=True)


def samples(path: Path, seconds: float, *, stereo_channel: str | None = None) -> np.ndarray:
    """Decode the original mono voice or ONE real output stereo channel.

    FFmpeg's default stereo->mono downmix uses sqrt(1/2) per channel: two
    identical channels therefore read 1.414x louder than the actual playback
    channel. That creates a false 'doubled narration' regression failure.
    Inspect FL/FR individually, not the synthetic downmix.
    """
    args = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(seconds), "-i", str(path),
            "-t", "2", "-vn"]
    if stereo_channel is not None:
        if stereo_channel not in ("FL", "FR"):
            raise ValueError("invalid output voice channel")
        args += ["-af", f"pan=mono|c0={stereo_channel}"]
    args += ["-ac", "1", "-ar", "8000", "-f", "f32le", "pipe:1"]
    return np.frombuffer(subprocess.check_output(args), dtype="<f4")


def check_video(path: Path, width: int, height: int, frames: int) -> dict:
    data = probe(path)
    video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    voices = [stream for stream in data["streams"] if stream["codec_type"] == "audio"]
    if (video["width"], video["height"], video["avg_frame_rate"]) != (width, height, "30/1"):
        raise ValueError("incorrect output geometry or frame rate: " + str(path))
    if int(video["nb_frames"]) != frames or len(voices) != 1:
        raise ValueError("output frame count or single narration stream failed")
    if abs(float(data["format"]["duration"]) - frames / 30) > .12:
        raise ValueError("rendered duration differs from the verified timeline")
    return {"path": str(path), "width": width, "height": height, "fps": 30,
            "frames": frames, "durationSeconds": frames / 30, "sha256": digest(path)}


def main() -> None:
    props, timed = read_json(PROPS), read_json(SCRIPT)
    full = ROOT / "remotion/build/phase4-demo/Phase4_Complete_Hybrid_Lesson.mp4"
    short = ROOT / "remotion/build/phase4-demo/Phase4_Formula_Short.mp4"
    full_frames = props["introFrames"] + props["outroFrames"] + sum(c["durationInFrames"] for c in props["chapters"])
    formula = next(chapter for chapter in props["chapters"] if chapter["id"] == "scene-05")
    short_frames = props["introFrames"] + props["outroFrames"] + formula["durationInFrames"]
    report = {"full": check_video(full, 1920, 1080, full_frames),
              "short": check_video(short, 1080, 1920, short_frames), "chapters": []}
    starts = props["introFrames"] / 30
    for chapter, scene in zip(props["chapters"], timed["scenes"], strict=True):
        media = chapter["media"]
        sid = media["sceneId"]
        original = OUTPUT / f"audio/lesson_999/scene_{sid:02d}.mp3"
        source_video = OUTPUT / f"renders/lesson_999/scene_{sid:02d}_{scene['step']}.mp4"
        if digest(original) != media["audioSha256"] or digest(source_video) != media["videoSha256"]:
            raise ValueError("source changed after bridge verification")
        if not media.get("captions"):
            raise ValueError("missing original scene-local captions")
        # Match decoded final AAC speech against original TTS, allowing codec rounding.
        source = samples(original, .5)
        rendered = samples(full, starts + .5, stereo_channel="FL")
        right = samples(full, starts + .5, stereo_channel="FR")
        if len(rendered) != len(right) or not np.allclose(rendered, right, rtol=0, atol=0.005):
            raise ValueError(f"scene {sid}: left/right output speech differs")
        length = min(len(source), len(rendered)) - 320
        correlations = []
        gains = []
        reference = source[160:160 + length]
        for offset in range(0, 321, 8):
            candidate = rendered[offset:offset + length]
            correlations.append(float(np.corrcoef(reference, candidate)[0, 1]))
            gains.append(float(np.sqrt(np.mean(candidate ** 2)) / np.sqrt(np.mean(reference ** 2))))
        best = int(np.nanargmax(correlations))
        if correlations[best] < .92 or not .75 < gains[best] < 1.25:
            raise ValueError(
                f"scene {sid}: real output speech channel is shifted or altered "
                f"(correlation={correlations[best]:.4f}, gain={gains[best]:.4f})"
            )
        duration = chapter["durationInFrames"] / 30
        review_time = min(duration - .2, max(2, duration * .45))
        path = EVIDENCE / f"chapter-{sid:02d}-{scene['step']}.png"
        frame(full, starts + review_time, path)
        report["chapters"].append({"sceneId": sid, "step": scene["step"],
            "startSeconds": starts, "durationSeconds": duration,
            "captionPages": len(media["captions"]), "speechCorrelation": correlations[best],
            "speechGain": gains[best], "reviewFrame": path.name})
        starts += duration
    frame(short, 12, EVIDENCE / "short-phone-review.png")
    image = Image.open(EVIDENCE / "short-phone-review.png")
    image.resize((360, 640)).save(EVIDENCE / "short-phone-360.png")
    if len(report["chapters"]) != 9:
        raise ValueError("final demonstration must have nine source scenes")
    protect()
    report["passed"] = True
    write_json(EVIDENCE / "final-render-verification.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
