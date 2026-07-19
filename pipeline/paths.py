"""Environment-agnostic paths, day tracking and config loading.

Works in three environments with zero code changes:
  1. Local machine / server → output goes to <repo>/output
  2. Google Colab           → mounts Drive, output goes to MyDrive/Math-9
  3. Any CI runner          → set MCME_OUTPUT_DIR to choose the folder

The day to produce is resolved in this order:
  1. LESSON_DAY environment variable (explicit override)
  2. state/progress.json → "next_day" (advanced by autopilot.py)
  3. Day 1
"""

import importlib.util
import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\r\n]')


def safe_filename(title: str) -> str:
    """Return a filesystem- and artifact-safe version of a lesson title."""
    return _INVALID_CHARS.sub('', title).replace(" ", "_").replace("—", "-")
STATE_PATH = REPO_ROOT / "state" / "progress.json"

OUTPUT_FOLDERS = [
    "scripts", "audio", "renders", "final_videos",
    "thumbnails", "practice_sheets", "logs", "assets", "png",
]


def _detect_base_dir():
    env = os.environ.get("MCME_OUTPUT_DIR")
    if env:
        return Path(env), False
    try:
        from google.colab import drive  # noqa: F401
        print("📂 Mounting Google Drive...")
        drive.mount("/content/drive")
        return Path("/content/drive/MyDrive/Math-9"), True
    except ImportError:
        return REPO_ROOT / "output", False


BASE_DIR, IN_COLAB = _detect_base_dir()
BANNER_PATH = BASE_DIR / "2.png"
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


def ensure_output_folders():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    for folder in OUTPUT_FOLDERS:
        (BASE_DIR / folder).mkdir(exist_ok=True)
    print(f"✅ All output folders ready inside: {BASE_DIR}")


def read_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"next_day": 1, "completed": [], "uploaded": []}


def write_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def get_day_number() -> int:
    env = os.environ.get("LESSON_DAY")
    if env:
        return int(env)
    return int(read_state().get("next_day", 1))


def load_cell1_config():
    """Import the cell1_config.py that Cell 1 wrote into BASE_DIR."""
    cfg_path = BASE_DIR / "cell1_config.py"
    if not cfg_path.exists():
        raise SystemExit(
            f"🛑 {cfg_path} not found. Run Cell 1 first "
            f"(python -m pipeline.cell1_lesson)."
        )
    spec = importlib.util.spec_from_file_location("cell1_config", cfg_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
