"""Opt-in bridge: original Manim scene pixels + Cell-3 audio -> Remotion props.

This is a staging/export command, NOT a production pipeline stage and NOT
a replacement for Cell 5 or the YouTube publisher. No alteration of source
media, scene order, published lessons, progress state or mathematical data.

From repository root:
  python -m pipeline.remotion_bridge \\
    --script output/scripts/lesson_043_script_timed.json \\
    --renders-dir output/renders/lesson_043 \\
    --audio-dir output/audio/lesson_043

Use the returned --props JSON for Remotion Studio/CLI after a local export.
Shorts and full hybrid demo are later phases. Captions are opt-in when original word boundaries exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pipeline.remotion_captions import load_scene_word_captions

FPS = 30
MAX_CHAPTERS = 40
STAGES = {"concept", "worked_example", "practice", "summary"}
SAFE_STEP = re.compile(r"^[a-z][a-z0-9_]*$")
SAFE_ID = re.compile(r"^[0-9]{1,5}$")


def _probe(path: Path, kind: str) -> tuple[float, dict]:
    if not path.is_file() or path.stat().st_size < 1024:
        raise ValueError(f"missing or empty {kind}: {path}")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height", "-of", "json",
         str(path)], capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise ValueError(f"ffprobe failed for {kind}: {path.name}")
    try:
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        stream = next(s for s in data["streams"] if s["codec_type"] == kind)
    except (ValueError, KeyError, StopIteration, TypeError) as exc:
        raise ValueError(f"{kind} has invalid media streams: {path.name}") from exc
    if not math.isfinite(duration) or not (1 < duration <= 3 * 3600):
        raise ValueError(f"invalid {kind} duration in {path.name}")
    if kind == "video" and (stream.get("width", 0) < 320 or
                            stream.get("height", 0) < 180):
        raise ValueError(f"unsupported {kind} resolution: {path.name}")
    return duration, stream


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(value: object, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} needs 1-{limit} meaningful characters")
    return value.strip()


def _positive_frames(value: int, field: str) -> int:
    if type(value) is not int or not 30 <= value <= 450:
        raise ValueError(f"{field} must be an integer from 30 through 450")
    return value


def export_lesson_package(
    timed_script: Path,
    renders_dir: Path,
    audio_dir: Path,
    remotion_dir: Path,
    output_props: Path | None = None,
    intro_frames: int = 60,
    outro_frames: int = 60,
    require_captions: bool = False,
) -> dict:
    """Inspect ALL inputs before writing; fail closed on missing/short media."""
    intro_frames = _positive_frames(intro_frames, "intro_frames")
    outro_frames = _positive_frames(outro_frames, "outro_frames")
    script = json.loads(timed_script.read_text(encoding="utf-8"))
    if not isinstance(script, dict):
        raise ValueError("timed script must be an object")
    scenes = script.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= MAX_CHAPTERS:
        raise ValueError("timed script requires 1-40 ordered scenes")
    lesson_id = script.get("lesson_id")
    if type(lesson_id) is not int or lesson_id < 1 or lesson_id > 99999:
        raise ValueError("lesson_id must be a positive integer <= 99999")
    series = _required_text(script.get("channel") or "MATH CONCEPTS MADE EASY",
                            "channel", 100)
    title = _required_text(script.get("title"), "title", 160)
    level = _required_text(script.get("subject") or script.get("global_track") or
                           "Mathematics", "level", 60)
    tagline = _required_text(script.get("lesson_goal") or
                             "Understand the concept, then practice.",
                             "lesson_goal", 240)

    assets = []
    seen = set()
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError("scene must be a JSON object")
        sid, step = scene.get("scene_id"), scene.get("step")
        if type(sid) is not int or sid < 1 or sid > 99 or sid in seen:
            raise ValueError("scene IDs must be distinct positive integers <= 99")
        seen.add(sid)
        if not isinstance(step, str) or not SAFE_STEP.fullmatch(step):
            raise ValueError("invalid stage for Manim filename")
        label = _required_text(scene.get("label") or step.replace("_", " ").title(),
                               "label", 140)
        goal = _required_text(scene.get("learning_purpose") or
                              scene.get("purpose") or
                              "Explore this mathematical concept.",
                              "learning_purpose", 260)
        source_video = renders_dir / f"scene_{sid:02d}_{step}.mp4"
        source_audio = audio_dir / f"scene_{sid:02d}.mp3"
        video_secs, _ = _probe(source_video, "video")
        audio_secs, _ = _probe(source_audio, "audio")
        try:
            declared = float(scene["duration_seconds"])
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"scene {sid}: missing real Cell-3 duration_seconds") from exc
        if not math.isfinite(declared) or declared <= 0:
            raise ValueError(f"scene {sid}: invalid narration duration")
        if audio_secs > declared + 0.10:
            raise ValueError(f"scene {sid}: narration exceeds declared duration")
        if video_secs + 0.06 < declared:
            raise ValueError(f"scene {sid}: Manim video shorter than narration timeline")
        if video_secs > declared + 2.00:
            raise ValueError(f"scene {sid}: Manim video too long for narration timeline")
        # Never generate frames beyond a source video's actual playable time.
        # The existing Cell-3 tail buffer means audio has stopped before this
        # frame-boundary truncation; any shortfall is rejected above.
        frames = math.floor(min(video_secs, declared) * FPS + 0.00001)
        if frames < 45 or audio_secs > frames / FPS + 0.04:
            raise ValueError(f"scene {sid}: frame-quantized clip would cut narrated audio")
        words_path = audio_dir / f"scene_{sid:02d}.words.json"
        captions = load_scene_word_captions(
            words_path, clip_seconds=frames / FPS, audio_seconds=audio_secs,
        )
        caption_digest = _sha256(words_path) if captions is not None else None
        digests = (_sha256(source_video), _sha256(source_audio))
        assets.append({
            "id": f"scene-{sid:02d}", "scene_id": sid, "step": step,
            "title": label, "learning_goal": goal, "durationInFrames": frames,
            "durationSeconds": frames / FPS,
            "sourceVideo": source_video, "sourceAudio": source_audio,
            "videoSha256": digests[0], "audioSha256": digests[1],
            "captions": captions, "captionsSha256": caption_digest,
        })

    have_captions = [item["captions"] is not None for item in assets]
    if any(have_captions) and not all(have_captions):
        raise ValueError("partial caption coverage: each scene requires original word timings")
    if require_captions and not all(have_captions):
        raise ValueError("original word timings are required for every scene")

    # Deterministic, content-addressed package identity. A later edit to one
    # video or voice file cannot silently reuse the older video/voice pair.
    identity = hashlib.sha256()
    identity.update(str(lesson_id).encode())
    for a in assets:
        identity.update((str(a["scene_id"]) + a["videoSha256"] +
                         a["audioSha256"] + (a["captionsSha256"] or "")).encode())
    package_id = f"lesson-{lesson_id:03d}-{identity.hexdigest()[:14]}"
    public_dir = remotion_dir / "public" / "manim" / package_id
    props = {
        "series": series, "level": level, "title": title, "tagline": tagline,
        "introFrames": intro_frames, "outroFrames": outro_frames,
        "chapters": [],
    }
    for item in assets:
        sid = item["scene_id"]
        stem = f"scene_{sid:02d}"
        props["chapters"].append({
            "id": item["id"], "stage":
                ("recap" if item["step"] == "summary" else
                 item["step"] if item["step"] in STAGES else "other"),
            "title": item["title"], "learningGoal": item["learning_goal"],
            "durationInFrames": item["durationInFrames"],
            "media": {
                "kind": "manim_scene", "sceneId": sid,
                "videoSrc": f"manim/{package_id}/{stem}_video.mp4",
                "audioSrc": f"manim/{package_id}/{stem}_audio.mp3",
                "videoSha256": item["videoSha256"],
                "audioSha256": item["audioSha256"],
                "durationSeconds": item["durationSeconds"],
                **({"captions": item["captions"],
                    "captionsSha256": item["captionsSha256"]}
                   if item["captions"] is not None else {}),
            },
        })
    total_frames = intro_frames + outro_frames + sum(
        chapter["durationInFrames"] for chapter in props["chapters"]
    )
    if total_frames > FPS * 3600 * 3:
        raise ValueError("package exceeds maximum supported lesson duration")

    # Stage full package in a private directory; avoid partial media exports
    # and never overwrite existing media under a prior content-addressed name.
    public_dir.parent.mkdir(parents=True, exist_ok=True)
    if not public_dir.exists():
        stage = Path(tempfile.mkdtemp(prefix=".manim-stage-", dir=public_dir.parent))
        try:
            for item in assets:
                stem = f"scene_{item['scene_id']:02d}"
                shutil.copyfile(item["sourceVideo"], stage / f"{stem}_video.mp4")
                shutil.copyfile(item["sourceAudio"], stage / f"{stem}_audio.mp3")
            stage.rename(public_dir)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    # Even existing package must have valid content; do not trust filenames.
    for item in assets:
        stem = f"scene_{item['scene_id']:02d}"
        if (_sha256(public_dir / f"{stem}_video.mp4") != item["videoSha256"] or
            _sha256(public_dir / f"{stem}_audio.mp3") != item["audioSha256"]):
            raise ValueError("existing Remotion package digest mismatch")

    output = output_props or remotion_dir / "build" / "bridged" / f"{package_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(props, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                    dir=output.parent, delete=False) as handle:
        handle.write(payload)
        staged = Path(handle.name)
    os.replace(staged, output)
    return {"packageId": package_id, "propsPath": str(output),
            "publicAssets": str(public_dir), "chapterCount": len(assets),
            "durationInFrames": total_frames, "fps": FPS,
            "mathPixelsTranscoded": False,
            "originalCell3VoicePreserved": True,
            "captionCoverage": "original_word_boundaries" if all(have_captions) else "unavailable"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--renders-dir", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--remotion-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "remotion")
    parser.add_argument("--output-props", type=Path, default=None)
    parser.add_argument("--intro-frames", type=int, default=60)
    parser.add_argument("--outro-frames", type=int, default=60)
    parser.add_argument("--require-captions", action="store_true",
                        help="Fail if any scene lacks real word-boundary timing")
    args = parser.parse_args()
    result = export_lesson_package(
        timed_script=args.script, renders_dir=args.renders_dir,
        audio_dir=args.audio_dir, remotion_dir=args.remotion_dir,
        output_props=args.output_props,
        intro_frames=args.intro_frames, outro_frames=args.outro_frames,
        require_captions=args.require_captions,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
