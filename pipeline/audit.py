"""Audit all curriculum plans and the exact mathematical strings to be rendered."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from pipeline.curriculum import MASTER_CURRICULUM
from pipeline.lesson_plan import plan_lesson
from pipeline.narration import write_narrations
from pipeline.paths import BASE_DIR, REPO_ROOT


def audit() -> None:
    expressions=[]
    authored=[]
    legacy=[]
    for lesson in MASTER_CURRICULUM:
        plan=plan_lesson(lesson)
        blocks=write_narrations(lesson,"Next chapter",lesson["topic"],plan)
        (authored if plan.get("lesson_design") else legacy).append(lesson["day"])
        for step,block in blocks.items():
            for panel_index,panel in enumerate(block["panels"]):
                for line_index,line in enumerate(panel["lines"]):
                    expressions.append({"location":f"day {lesson['day']} {step} panel {panel_index} line {line_index}","latex":line})
    folder=BASE_DIR/"logs"
    folder.mkdir(parents=True,exist_ok=True)
    report=folder/"curriculum_audit.json"
    report.write_text(json.dumps({"lessons":len(MASTER_CURRICULUM),"authored_design_days":authored,
                                  "legacy_content_days":legacy,"math_expressions":expressions},ensure_ascii=False,indent=2),encoding="utf-8")
    math_path=folder/"math_expressions.json"
    math_path.write_text(json.dumps(expressions,ensure_ascii=False),encoding="utf-8")
    subprocess.run(["node","scripts/check-math.cjs",str(math_path)],cwd=REPO_ROOT/"remotion",check=True)
    print(f"Authored chapter designs: {len(authored)}; existing lesson content: {len(legacy)}")


if __name__ == "__main__":
    audit()
