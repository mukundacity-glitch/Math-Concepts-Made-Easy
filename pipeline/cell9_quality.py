"""Pre-render semantic QA for the timed scene manifest."""

from __future__ import annotations

import json

from pipeline.lesson_qa import assert_lesson_quality
from pipeline.paths import BASE_DIR, load_cell1_config


config = load_cell1_config()
lesson_id = int(config.CURRICULUM[0]["id"])
script_path = config.SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
if not script_path.exists():
    raise SystemExit(f"🛑 Timed manifest not found: {script_path}")

script = json.loads(script_path.read_text(encoding="utf-8"))
report_path = BASE_DIR / "logs" / f"day_{lesson_id:03d}_coverage.json"
try:
    report = assert_lesson_quality(script, report_path=report_path)
except ValueError as exc:
    raise SystemExit(f"🛑 {exc}") from exc

print(f"✅ Semantic QA passed — {len(script['scenes'])} scenes")
print(f"✅ Coverage report → {report_path}")
for warning in report["warnings"]:
    print(f"   ⚠️  {warning}")
