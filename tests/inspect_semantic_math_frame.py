"""Inspect rendered Manim mathematical colors, not just Python role metadata."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from pipeline.semantic_math import MATH_PALETTE


def analyze_frame(path: Path) -> dict:
    data = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    count_by_role = {}
    # Antialiasing changes pixel values; a small RGB tolerance is allowed.
    for role in ("variable", "number", "operator", "relation", "exponent", "group"):
        code = MATH_PALETTE[role]
        rgb = np.array([int(code[i:i+2], 16) for i in (1, 3, 5)])
        nearby = np.all(np.abs(data - rgb) <= 27, axis=-1)
        count_by_role[role] = int(np.sum(nearby))
    missing = {role: count for role, count in count_by_role.items() if count < 12}
    return {
        "passed": not missing,
        "resolution": [data.shape[1], data.shape[0]],
        "pixels_by_role": count_by_role,
        "missing": missing,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("frame", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    outcome = analyze_frame(args.frame)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(outcome, indent=2))
    if not outcome["passed"]:
        raise SystemExit("Semantic equation colors not visible in actual Manim frame")
