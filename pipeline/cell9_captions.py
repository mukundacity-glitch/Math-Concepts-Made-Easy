# ==========================================
# CELL 9: CAPTION BURN-IN
# CHANNEL: MathConceptsMadeEasy
# Reads : final_videos/Day_XXX_<title>.mp4  (Cell 5's assembled video)
#         final_videos/Day_XXX_<title>.srt  (Cell 8's captions)
# Writes: burns captions into that same .mp4, atomically — the
#         uploader and the GitHub Actions artifact-upload step need
#         zero changes, they already point at this filename.
# ==========================================

import os
import sys
from pathlib import Path

# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config, safe_filename
from pipeline.captions import burn_captions
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")

lesson_data = cell1_config.CURRICULUM[0]
lesson_id   = lesson_data["id"]
safe_title  = safe_filename(lesson_data["seo_title"])

FINAL_DIR = cell1_config.FINAL_DIR
FINAL_VIDEO_PATH = FINAL_DIR / f"Day_{lesson_id:03d}_{safe_title}.mp4"
SRT_PATH         = FINAL_DIR / f"Day_{lesson_id:03d}_{safe_title}.srt"

if not FINAL_VIDEO_PATH.exists():
    raise SystemExit(
        f"🛑 Assembled video not found at {FINAL_VIDEO_PATH}. Run Cell 5 first.")
if not SRT_PATH.exists():
    raise SystemExit(f"🛑 Captions not found at {SRT_PATH}. Run Cell 8 first.")

print(f"{'═'*65}")
print(f"  BURNING CAPTIONS — Day {lesson_id}")
print(f"{'═'*65}\n")
print(f"  Video   : {FINAL_VIDEO_PATH.name}")
print(f"  Captions: {SRT_PATH.name}\n")

temp_path = FINAL_DIR / f"_captioned_{FINAL_VIDEO_PATH.name}"
burn_captions(FINAL_VIDEO_PATH, SRT_PATH, temp_path)
os.replace(temp_path, FINAL_VIDEO_PATH)

size_mb = FINAL_VIDEO_PATH.stat().st_size / (1024 * 1024)
print(f"{'═'*65}")
print(f"  ✅ CAPTIONS BURNED")
print(f"{'═'*65}")
print(f"  ✅ File     : {FINAL_VIDEO_PATH.name}")
print(f"  💾 Size     : {size_mb:.2f} MB")
print(f"{'═'*65}")
print(f"\n  ▶ Run Cell 6 for thumbnail. Run Cell 7 for shorts.\n")
