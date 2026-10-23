"""Production Remotion assembly using the verified original-media bridge."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from pipeline.remotion_bridge import export_lesson_package

ROOT = Path(__file__).resolve().parents[1]


def render(composition: str, props: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["npx", "remotion", "render", "src/index.ts", composition,
        str(output.resolve()), "--props=" + str(props.resolve()), "--codec=h264",
        "--crf=20", "--concurrency=2", "--log=error"], cwd=ROOT / "remotion", check=True)


def main():
    from pipeline.paths import BASE_DIR, load_cell1_config, safe_filename
    cfg = load_cell1_config()
    lesson = cfg.CURRICULUM[0]
    day = lesson["id"]
    stem = f"Day_{day:03d}_{safe_filename(lesson['seo_title'])}"
    props_path = BASE_DIR / "hybrid" / f"lesson-{day:03d}.json"
    export_lesson_package(cfg.SCRIPTS_DIR / f"lesson_{day:03d}_script_timed.json",
        cfg.RENDERS_DIR / f"lesson_{day:03d}", cfg.AUDIO_DIR / f"lesson_{day:03d}",
        ROOT / "remotion", output_props=props_path, require_captions=True)
    render("PremiumLesson", props_path, cfg.FINAL_DIR / (stem + ".mp4"))
    # Sidecar captions follow exactly the same frame-quantized Remotion timeline.
    props = json.loads(props_path.read_text())
    offset = props["introFrames"] / 30
    captions = []
    speech = []
    for chapter in props["chapters"]:
        speech.append((ROOT / "remotion/public" / chapter["media"]["audioSrc"], offset))
        for cap in chapter["media"]["captions"]:
            captions.append((offset + cap["startMs"] / 1000,
                             offset + cap["endMs"] / 1000, cap["text"]))
        offset += chapter["durationInFrames"] / 30
    from pipeline.narration_integrity import verify_narration
    report = verify_narration(cfg.FINAL_DIR / (stem + ".mp4"), speech)
    props_path.with_name(f"lesson-{day:03d}-audio-qa.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    def timestamp(seconds, separator):
        millis = round(seconds * 1000)
        hours, rest = divmod(millis, 3600000)
        minutes, rest = divmod(rest, 60000)
        secs, ms = divmod(rest, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02}{separator}{ms:03}"
    for suffix, sep in [("srt", ","), ("vtt", ".")]:
        text = "WEBVTT\n\n" if suffix == "vtt" else ""
        for index, (start, end, caption) in enumerate(captions, 1):
            if suffix == "srt": text += f"{index}\n"
            text += f"{timestamp(start, sep)} --> {timestamp(end, sep)}\n{caption}\n\n"
        (cfg.FINAL_DIR / f"{stem}.{suffix}").write_text(text, encoding="utf8")


if __name__ == "__main__":
    main()
