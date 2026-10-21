"""Render narration-timed visual panels into the existing assembly contract."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess

from pipeline.paths import REPO_ROOT, load_cell1_config
from pipeline.visual_models import validate_visual


def scene_props(script: dict, scene: dict) -> dict:
    duration = float(scene["duration_seconds"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("rendering requires a positive measured audio duration")
    timing = scene.get("statement_timing") or []
    if len(timing) != len(scene.get("narration_beats", [])):
        raise ValueError("every narration statement needs timing before rendering")
    panels = []
    for panel in scene.get("panels", []):
        first, end = panel["start_sentence"], panel["end_sentence"]
        start = timing[first]["start"]
        stop = timing[end]["start"] if end < len(timing) else duration
        lines = panel["lines"]
        line_starts = [timing[index]["start"] for index in panel["line_sentences"]]
        visual = validate_visual(panel["visual"])
        if panel.get("pause_after"):
            visual["showValues"] = False
            visual["static"] = True
        artwork = panel.get("artwork")
        if artwork and (Path(artwork).is_absolute() or ".." in Path(artwork).parts
                        or not (REPO_ROOT / "remotion" / "public" / artwork).is_file()):
            raise ValueError("panel artwork must be an existing public asset")
        panels.append({"title":panel["title"], "start":start, "end":stop,
                       "lines":lines,"lineStarts":line_starts,"visual":visual,"artwork":artwork})
    if not panels:
        raise ValueError("Remotion scenes require authored visual panels")
    return {"title":script["title"],"stage":scene["step"],"label":scene["label"],
            "duration":duration,"styleName":script.get("visual_style","paper"),
            "lines":[],"lineStarts":[],"visual":panels[0]["visual"],"panels":panels,
            "beats":[{"text":text,**row} for text,row in zip(scene["narration_beats"],timing)],
            "pauses":scene.get("pause_timing",[])}


def render_lesson() -> None:
    config = load_cell1_config()
    day = int(config.CURRICULUM[0]["id"])
    script_path = config.SCRIPTS_DIR / f"lesson_{day:03d}_script_timed.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    destination = config.RENDERS_DIR / f"lesson_{day:03d}"
    destination.mkdir(parents=True,exist_ok=True)
    log_dir = config.BASE_DIR / "logs"
    log_dir.mkdir(parents=True,exist_ok=True)
    project = REPO_ROOT / "remotion"
    cli = project / "node_modules" / ".bin" / "remotion"
    if not cli.exists():
        raise SystemExit("Install the renderer first: npm ci --prefix remotion")
    for scene in script["scenes"]:
        name = f"scene_{scene['scene_id']:02d}_{scene['step']}"
        props = destination / f"{name}.props.json"
        props.write_text(json.dumps(scene_props(script,scene),allow_nan=False),encoding="utf-8")
        output = destination / f"{name}.mp4"
        temporary = destination / f"{name}.partial.mp4"
        temporary.unlink(missing_ok=True)
        command = [str(cli),"render","src/index.ts","MathScene",str(temporary),
                   "--props",str(props),"--codec=h264","--concurrency=2","--log=error"]
        if os.environ.get("MCME_RENDER_QUALITY") == "l":
            command += ["--scale=0.5"]
        result = subprocess.run(command,cwd=project,capture_output=True,text=True)
        (log_dir/f"day_{day:03d}_{scene['step']}_render.log").write_text(
            result.stdout+"\n"+result.stderr,encoding="utf-8")
        if result.returncode or not temporary.is_file():
            raise RuntimeError(f"Rendering {name} failed; see its render log")
        probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                              "-of","default=noprint_wrappers=1:nokey=1",str(temporary)],
                             capture_output=True,text=True,check=True)
        if float(probe.stdout)<float(scene["duration_seconds"])-0.1:
            raise RuntimeError(f"{name} is shorter than its narration")
        temporary.replace(output)
        print(f"Rendered {output.name}",flush=True)


if __name__ == "__main__":
    render_lesson()
