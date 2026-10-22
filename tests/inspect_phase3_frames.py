"""Reject blank or malformed 10/15-item premium Manim smoke output."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def main(directory: Path):
    checks = {}
    errors = []
    for name in ("PremiumWorkedExampleSmoke", "PremiumPracticeSmoke"):
        frame = directory / f"{name}.png"
        media = directory / f"{name}.json"
        if not frame.exists() or not media.exists():
            errors.append(f"{name}: missing independently inspectable evidence")
            continue
        image = np.asarray(Image.open(frame).convert("RGB"), dtype=np.float32)
        meta = json.loads(media.read_text())
        duration = float(meta.get("format", {}).get("duration", 0))
        bg = np.array([8, 27, 51], dtype=np.float32)
        changed = np.max(abs(image - bg), axis=2) > 40
        foreground_fraction = float(np.mean(changed))
        contrast = float(np.std(image))
        bright_text = float(np.mean((image.min(axis=2) > 145)))
        checks[name] = {
            "duration": duration, "resolution": list(image.shape[:2][::-1]),
            "foreground_fraction": foreground_fraction,
            "contrast": contrast, "bright_text_fraction": bright_text,
        }
        if duration < 15:
            errors.append(f"{name}: scene truncated (<15 seconds)")
        if image.shape[0] < 360 or image.shape[1] < 640:
            errors.append(f"{name}: preview resolution unexpectedly small")
        if foreground_fraction < 0.06 or contrast < 19 or bright_text < 0.002:
            errors.append(f"{name}: blank or insufficient mathematical content")
    report = {"passed": not errors, "checks": checks, "errors": errors}
    (directory / "quality-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit("Phase 3 visual validation failed: " + "; ".join(errors))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
