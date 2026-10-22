"""Render-level smoke gate: inspect representative frames, not just JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def analyze(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    data = np.asarray(im, dtype=np.int16)
    # Original #081B33 Manim background; distinguish non-background pixels
    # without assuming a fixed scene title/diagram placement.
    bg = np.asarray([8, 27, 51], dtype=np.int16)
    differences = np.max(np.abs(data - bg), axis=-1)
    foreground = differences > 35
    # Exclude dark navy background: it is blue but NOT a plotted cyan curve.
    cyan = ((data[:, :, 1] > data[:, :, 0] + 60) &
            (data[:, :, 2] > data[:, :, 0] + 60) &
            (data[:, :, 1] > 90) & (data[:, :, 2] > 120))
    gold = (data[:, :, 0] > 150) & (data[:, :, 1] > 90) & (
        data[:, :, 2] < 185)
    return {
        "image": str(path),
        "width": im.width,
        "height": im.height,
        "foreground_fraction": round(float(np.mean(foreground)), 5),
        "cyan_fraction": round(float(np.mean(cyan)), 5),
        "gold_fraction": round(float(np.mean(gold)), 5),
        "rgb_stddev": round(float(np.std(data)), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    before = analyze(args.before)
    after = analyze(args.after)
    errors = []
    if after["width"] < 640 or after["height"] < 360:
        errors.append("render resolution too low")
    if after["foreground_fraction"] <= before["foreground_fraction"] + 0.006:
        errors.append("math graph does not introduce enough new foreground content")
    if after["cyan_fraction"] < 0.001:
        errors.append("computed cyan mathematical function not visible")
    if after["rgb_stddev"] < 15:
        errors.append("frame has insufficient variation")
    result = {"passed": not errors, "errors": errors,
              "before": before, "after": after}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit("Render visual inspection failed: " + "; ".join(errors))


if __name__ == "__main__":
    main()
