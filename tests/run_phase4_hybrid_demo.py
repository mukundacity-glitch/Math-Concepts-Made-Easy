"""Opt-in real nine-scene demonstration. Never calls autopilot or an uploader.

Commands are separate checkpoints so CI can retain evidence if a provider fails.
The production Cell-1 functions and Cell-4 template are read through AST to avoid
their module-level production execution; their teaching/render code is unchanged.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import pprint
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = ROOT / "build/phase4-demo"
OUTPUT = BASE / "output"
EVIDENCE = BASE / "evidence"
SCRIPT = OUTPUT / "scripts/lesson_999_script_timed.json"
PROPS = ROOT / "remotion/build/phase4-demo/lesson.json"
PROTECTED = (
    "state/progress.json", "state/creative_history.json", "autopilot.py",
    ".github/workflows/daily-video.yml", ".github/workflows/publish-video.yml",
    "pipeline/cell7_shorts.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf8"))


def run(*command: str, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True, env={
        **os.environ, "MCME_OUTPUT_DIR": str(OUTPUT), "LESSON_DAY": "999",
        "PYTHONPATH": str(ROOT),
    })


def production_functions(path: str, names: set[str], globals_: dict) -> dict:
    tree = ast.parse((ROOT / path).read_text(encoding="utf8"))
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != names:
        raise ValueError("required production functions changed: " + path)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, "exec"), globals_)
    return globals_


def prepare() -> None:
    from pipeline.constants import PITCH_PROFILES, SCENE_ANIMATION_MAP, SCENE_PITCH_MAP
    from pipeline.lesson_contract import validate_premium_lesson
    from pipeline.lesson_plan import plan_lesson
    from pipeline.mathtext import latex_to_speech, split_sentences
    from pipeline.premium_animation import premium_narration

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE / "production-before.json", {p: digest(ROOT / p) for p in PROTECTED})
    fixture = read_json(ROOT / "examples/phase4_hybrid_demo.json")
    lesson = read_json(ROOT / fixture.pop("source"))
    lesson.update(fixture)
    lesson.update(id=999, title=lesson["topic"])
    verification = validate_premium_lesson(lesson)
    plan = plan_lesson(lesson)
    if len(plan["scene_order"]) != 9:
        raise ValueError("demo must exercise all nine production scenes")
    functions = production_functions("pipeline/cell1_lesson.py", {
        "clean_math_for_speech", "write_narrations", "validate_lesson",
    }, {"latex_to_speech": latex_to_speech, "split_sentences": split_sentences,
        "premium_narration": premium_narration, "validate_premium_lesson": validate_premium_lesson,
        "json": json})
    if not functions["validate_lesson"](lesson):
        raise ValueError("demo content failed the production Cell-1 quality gate")
    narrations = functions["write_narrations"](
        lesson, "Practice a fresh equation after the lesson.", lesson["title"], plan)
    lesson.update(heading="HYBRID DEMO — " + lesson["title"],
                  subheading="Grade 9 | Algebra | Review only",
                  intro_teaser="Practice a fresh equation after the lesson.",
                  outro_message=narrations["summary"]["full"], scene_narrations=narrations)
    for folder in ("scripts", "audio", "renders", "assets", "logs"):
        (OUTPUT / folder).mkdir(parents=True, exist_ok=True)
    theme = {"bg": "#0D1B2A", "primary": "#F0F4F8", "secondary": "#8899AA",
             "blue": "#3B9EFF", "green": "#2ECC71", "yellow": "#F6C90E",
             "red": "#E74C3C", "card_bg": "#1A2B3C"}
    config = "from pathlib import Path\nBASE_DIR = Path(" + repr(str(OUTPUT)) + ")\n"
    for name, relative in {"SCRIPTS_DIR": "scripts", "AUDIO_DIR": "audio",
                           "RENDERS_DIR": "renders", "ASSETS_DIR": "assets"}.items():
        config += f"{name} = BASE_DIR / {relative!r}\n"
    config += "BANNER_PATH = BASE_DIR / '2.png'\nLOGO_PATH = ASSETS_DIR / 'logo.png'\n"
    for name, value in {
        "CHANNEL_NAME": "Math Concepts Made Easy", "THEME": theme,
        "TTS_CONFIG": {"voice": "en-GB-RyanNeural", "rate": "-8%", "pitch": "+0Hz"},
        "PITCH_PROFILES": PITCH_PROFILES, "SCENE_PITCH_MAP": SCENE_PITCH_MAP,
        "SCENE_ANIMATION_MAP": SCENE_ANIMATION_MAP, "LESSON_PLAN": plan,
        "RESOLUTION": {"long_form": (1920, 1080), "shorts": (1080, 1920)},
        "CURRICULUM": [lesson],
    }.items():
        config += name + " = " + pprint.pformat(value, width=100) + "\n"
    (OUTPUT / "cell1_config.py").write_text(config, encoding="utf8")
    write_json(EVIDENCE / "lesson-verification.json", verification)
    run(sys.executable, "-m", "pipeline.cell2_script")


def audio() -> None:
    from pipeline.premium_audio_qa import validate_premium_word_alignment
    run(sys.executable, "-m", "pipeline.cell3_audio")
    script = read_json(SCRIPT)
    reports = []
    for scene in script["scenes"]:
        words = read_json(OUTPUT / f"audio/lesson_999/scene_{scene['scene_id']:02d}.words.json")
        if not words:
            raise ValueError("every demo scene requires real Edge-TTS word events")
        report = {"sceneId": scene["scene_id"], "wordEvents": len(words)}
        if "premium_items" in scene:
            report.update(validate_premium_word_alignment(scene, words))
        reports.append(report)
    write_json(EVIDENCE / "real-speech-verification.json", {"synthetic": False, "scenes": reports})


def manim() -> None:
    script = read_json(SCRIPT)
    tree = ast.parse((ROOT / "pipeline/cell4_animation.py").read_text(encoding="utf8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"MANIM_SCENE_CODE", "SCENE_CLASS_MAP"}:
                    values[target.id] = ast.literal_eval(node.value)
    theme = script["theme"]
    namespace = {"MANIM_SCENE_CODE": values["MANIM_SCENE_CODE"],
        "REPO_ROOT": ROOT, "TIMED_SCRIPT": SCRIPT,
        "LESSON_AUDIO": OUTPUT / "audio/lesson_999", "BANNER_PATH": OUTPUT / "2.png",
        "LOGO_PATH": OUTPUT / "assets/logo.png"}
    for variable, key in {"C_BG": "bg", "C_PRIMARY": "primary", "C_SECOND": "secondary",
                          "C_BLUE": "blue", "C_GREEN": "green", "C_YELLOW": "yellow",
                          "C_RED": "red", "C_CARD": "card_bg"}.items():
        namespace[variable] = theme[key]
    production_functions("pipeline/cell4_animation.py", {"build_manim_source"}, namespace)
    source = BASE / "production_math_scenes.py"
    source.write_text(namespace["build_manim_source"](script), encoding="utf8")
    write_json(EVIDENCE / "source-provenance.json", {
        "cell1": digest(ROOT / "pipeline/cell1_lesson.py"),
        "cell4": digest(ROOT / "pipeline/cell4_animation.py"),
        "generatedManim": digest(source), "resolution": [1920, 1080], "fps": 30,
    })
    renders = OUTPUT / "renders/lesson_999"
    renders.mkdir(parents=True, exist_ok=True)
    media_reports = []
    for scene in script["scenes"]:
        classname = values["SCENE_CLASS_MAP"][scene["step"]]
        run(sys.executable, "-m", "manim", "--resolution", "1920,1080", "--fps", "30",
            "--disable_caching", "--progress_bar", "none", "--media_dir", str(BASE / "manim"),
            str(source), classname)
        candidates = list((BASE / "manim/videos").rglob(classname + ".mp4"))
        if len(candidates) != 1:
            raise ValueError("Manim did not produce exactly one output for " + classname)
        shutil.copyfile(candidates[0], renders / f"scene_{scene['scene_id']:02d}_{scene['step']}.mp4")
        media_reports.append({"sceneId": scene["scene_id"], "step": scene["step"],
            "declaredSeconds": scene["duration_seconds"], "probe": json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(candidates[0]),
            ], text=True))})
        write_json(EVIDENCE / "source-media-probes.json", media_reports)


def bridge() -> None:
    from pipeline.remotion_bridge import export_lesson_package
    result = export_lesson_package(
        SCRIPT, OUTPUT / "renders/lesson_999", OUTPUT / "audio/lesson_999",
        ROOT / "remotion", output_props=PROPS, require_captions=True)
    if result["chapterCount"] != 9:
        raise ValueError("hybrid demo omitted a scene")
    props = read_json(PROPS)
    # A complete formula chapter is a coherent short and stays below the editorial cap.
    short = {**props, "chapterIds": ["scene-05"]}
    formula = next(c for c in props["chapters"] if c["id"] == "scene-05")
    if props["introFrames"] + props["outroFrames"] + formula["durationInFrames"] > 5400:
        raise ValueError("complete formula chapter exceeds Shorts editorial budget")
    write_json(PROPS.with_name("short.json"), short)
    write_json(EVIDENCE / "bridge-verification.json", result)


def protect() -> None:
    before = read_json(EVIDENCE / "production-before.json")
    after = {p: digest(ROOT / p) for p in PROTECTED}
    if before != after:
        raise ValueError("demo modified protected production files")
    write_json(EVIDENCE / "production-unchanged.json", {"passed": True, "hashes": after})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "audio", "manim", "bridge", "protect"])
    globals()[parser.parse_args().command]()
