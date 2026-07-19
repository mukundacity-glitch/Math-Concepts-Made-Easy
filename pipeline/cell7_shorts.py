# ==========================================
# CELL 7: SHORTS GENERATOR
# CHANNEL: MathConceptsMadeEasy
# Takes the final assembled video.
# Crops center to 1080x1920 vertical.
# Exports hook + worked_example scenes only.
# Max 60 seconds. Adds large formula overlay.
# ==========================================

import sys, json, subprocess
from pathlib import Path

# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config, safe_filename
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")
lesson_data   = cell1_config.CURRICULUM[0]
lesson_id     = lesson_data['id']
safe_title    = safe_filename(lesson_data['seo_title'])

SCRIPTS_DIR   = cell1_config.SCRIPTS_DIR
AUDIO_DIR     = cell1_config.AUDIO_DIR
RENDERS_DIR   = cell1_config.RENDERS_DIR
FINAL_DIR     = cell1_config.FINAL_DIR

TIMED_SCRIPT  = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
LESSON_AUDIO  = AUDIO_DIR   / f"lesson_{lesson_id:03d}"
LESSON_RENDER = RENDERS_DIR / f"lesson_{lesson_id:03d}"
SHORTS_PATH   = FINAL_DIR   / f"Day_{lesson_id:03d}_{safe_title}_SHORTS.mp4"

with open(TIMED_SCRIPT, "r", encoding="utf-8") as f:
    SCRIPT = json.load(f)

# Use hook + worked_example scenes only
TARGET_STEPS  = ["hook", "worked_example"]
SHORT_SCENES  = [s for s in SCRIPT["scenes"] if s["step"] in TARGET_STEPS]

# Build temp concat for just those scenes
TEMP_SHORT_CONCAT = FINAL_DIR / "shorts_concat.txt"
with open(TEMP_SHORT_CONCAT, "w") as f:
    for scene in SHORT_SCENES:
        step     = scene["step"]
        scene_id = scene["scene_id"]
        vid      = LESSON_RENDER / f"scene_{scene_id:02d}_{step}.mp4"
        aud      = LESSON_AUDIO  / f"scene_{scene_id:02d}.mp3"
        mux_out  = FINAL_DIR     / f"short_mux_{scene_id:02d}.mp4"

        if vid.exists() and aud.exists():
            subprocess.run([
                "ffmpeg", "-y", "-v", "error",
                "-i", str(vid), "-i", str(aud),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                str(mux_out)
            ], check=True)
            f.write(f"file '{str(mux_out.absolute())}'\n")

# Concat selected scenes
TEMP_JOINED = FINAL_DIR / "shorts_joined.mp4"
subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-f", "concat", "-safe", "0",
    "-i", str(TEMP_SHORT_CONCAT),
    "-c", "copy",
    str(TEMP_JOINED)
], check=True)

# Crop to vertical 1080x1920 and trim to 59 seconds max
subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-i", str(TEMP_JOINED),
    "-t", "59",
    "-vf", (
        "crop=ih*9/16:ih,"
        "scale=1080:1920,"
        f"drawtext=text='{SCRIPT['title']}':"
        "fontsize=60:fontcolor=white:"
        "x=(w-text_w)/2:y=100:"
        "shadowcolor=black:shadowx=3:shadowy=3,"
        f"drawtext=text='MathConceptsMadeEasy':"
        "fontsize=36:fontcolor=yellow:"
        "x=(w-text_w)/2:y=h-120:"
        "shadowcolor=black:shadowx=2:shadowy=2"
    ),
    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
    "-pix_fmt", "yuv420p",
    str(SHORTS_PATH)
], check=True)

size_mb = SHORTS_PATH.stat().st_size / (1024 * 1024)
print(f"\n{'═'*65}")
print(f"  🎉 SHORTS GENERATED")
print(f"{'═'*65}")
print(f"  ✅ File     : {SHORTS_PATH.name}")
print(f"  💾 Size     : {size_mb:.2f} MB")
print(f"  📐 Format   : 1080x1920 vertical")
print(f"  ⏱️  Duration : max 59 seconds")
print(f"  📂 Location : {SHORTS_PATH.parent}")
print(f"{'═'*65}")
print(f"\n  ▶ Upload this to YouTube Shorts separately.\n")