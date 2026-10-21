"""Build inspectable scene props without TTS, rendering, uploading or state writes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.curriculum import get_lesson
from pipeline.lesson_plan import plan_lesson
from pipeline.narration import write_narrations
from pipeline.paths import BASE_DIR
from pipeline.remotion_render import scene_props
from pipeline.scene_manifest import build_scene_manifest


def build_preview(day: int, destination: Path) -> dict:
    lesson = get_lesson(day)
    plan = plan_lesson(lesson)
    narrations = write_narrations(lesson,"Try the next chapter when ready.",lesson["topic"],plan)
    script = build_scene_manifest(lesson,narrations,plan)
    script.update(title=lesson["topic"],key_formula=lesson["key_formula"])
    for scene in script["scenes"]:
        original = scene["expected_duration"]-sum(pause["seconds"] for pause in scene.get("pauses", []))
        pauses = scene.get("pauses", [])
        beats=scene["narration_beats"]
        counts=[len(beat.split()) for beat in beats]
        total=sum(counts) or 1
        cursor=0.0
        timing=[]
        silence=0.0
        measured=[]
        for index,count in enumerate(counts):
            span=original*count/total
            timing.append({"sentence_index":index,"start":cursor+silence,"end":cursor+silence+span})
            cursor+=span
            for pause in pauses:
                if pause["after_sentence"]==index+1:
                    measured.append({"start":cursor+silence,"seconds":pause["seconds"]})
                    silence+=pause["seconds"]
        scene.update(duration_seconds=original+silence,statement_timing=timing,pause_timing=measured)
    destination.mkdir(parents=True,exist_ok=True)
    (destination/"script.json").write_text(json.dumps(script,ensure_ascii=False,indent=2),encoding="utf-8")
    for scene in script["scenes"]:
        (destination/f"{scene['step']}.json").write_text(json.dumps(scene_props(script,scene),ensure_ascii=False),encoding="utf-8")
    return script


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day",type=int,required=True)
    args=parser.parse_args()
    folder=BASE_DIR/"preview"/f"day_{args.day:03d}"
    script=build_preview(args.day,folder)
    print(f"Prepared {len(script['scenes'])} scenes in {folder}")
