# ==========================================
# CELL 7: SHORTS GENERATOR
# CHANNEL: MathConceptsMadeEasy
# Takes the final assembled video and cuts THREE distinct vertical
# Shorts from it — a different scene pair each, so the channel can
# post 3 times a day without repeating the same clip:
#   HOOK    → curiosity teaser   (hook + concept)
#   FORMULA → the key trick      (formula + worked_example)
#   MISTAKE → fix + try-it CTA   (mistakes + practice)
# Each Short is scaled to fit the full 1080x1920 frame with a blurred
# background fill — never cropped — so no board writing or formula
# is ever cut off at the edges.
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

with open(TIMED_SCRIPT, "r", encoding="utf-8") as f:
    SCRIPT = json.load(f)

SCENES_BY_STEP = {s["step"]: s for s in SCRIPT["scenes"]}

# ══════════════════════════════════════════════════════════════
# THREE SHORT TYPES — one per daily posting slot
# ══════════════════════════════════════════════════════════════

def _caption_for(field: str, fallback_field: str = None) -> str:
    text = (lesson_data.get(field) or "").strip()
    if not text and fallback_field:
        text = (lesson_data.get(fallback_field) or "").strip()
    return text or lesson_data["seo_title"]


SHORT_TYPES = [
    {
        "key"     : "HOOK",
        "label"   : "Curiosity Hook",
        "steps"   : ["hook", "concept"],
        "caption" : _caption_for("real_world_hook", "thumbnail_angle"),
    },
    {
        "key"     : "FORMULA",
        "label"   : "The Key Formula",
        "steps"   : ["formula", "worked_example"],
        "caption" : _caption_for("formula_spoken"),
    },
    {
        "key"     : "MISTAKE",
        "label"   : "Fix This Mistake",
        "steps"   : ["mistakes", "practice"],
        "caption" : _caption_for("common_mistake"),
    },
]


def _wrap_lines(text: str, max_chars: int = 26, max_lines: int = 2) -> list:
    """Greedy word-wrap so drawtext never overflows the 1080px-wide canvas."""
    words = text.split()
    lines, current = [], ""
    for i, word in enumerate(words):
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            # Final allowed line — fold in everything left, then truncate.
            remaining = " ".join([current] + words[i + 1:])
            if len(remaining) > max_chars:
                remaining = remaining[:max_chars - 1].rstrip() + "…"
            return lines + [remaining]
    if current:
        lines.append(current)
    return lines[:max_lines]


def _escape_drawtext(text: str) -> str:
    return (text.replace("\\", "\\\\")
                .replace(":", "\\:")
                .replace("'", "’"))


def build_short(short_type: dict) -> Path:
    key   = short_type["key"]
    steps = short_type["steps"]
    scenes = [SCENES_BY_STEP[s] for s in steps if s in SCENES_BY_STEP]
    if not scenes:
        raise SystemExit(f"🛑 No scenes found for Short type {key} ({steps}).")

    out_path = FINAL_DIR / f"Day_{lesson_id:03d}_{safe_title}_SHORT_{key}.mp4"

    concat_list = FINAL_DIR / f"shorts_concat_{key}.txt"
    mux_files = []
    with open(concat_list, "w") as f:
        for scene in scenes:
            step, scene_id = scene["step"], scene["scene_id"]
            vid = LESSON_RENDER / f"scene_{scene_id:02d}_{step}.mp4"
            aud = LESSON_AUDIO  / f"scene_{scene_id:02d}.mp3"
            mux_out = FINAL_DIR / f"short_mux_{key}_{scene_id:02d}.mp4"
            if vid.exists() and aud.exists():
                subprocess.run([
                    "ffmpeg", "-y", "-v", "error",
                    "-i", str(vid), "-i", str(aud),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                    str(mux_out)
                ], check=True)
                f.write(f"file '{str(mux_out.absolute())}'\n")
                mux_files.append(mux_out)

    joined = FINAL_DIR / f"shorts_joined_{key}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(joined)
    ], check=True)

    title_lines = _wrap_lines(SCRIPT["title"], max_chars=26, max_lines=2)
    caption_lines = _wrap_lines(short_type["caption"], max_chars=30, max_lines=2)

    # ── Fit the whole landscape frame inside 1080x1920 — never crop.
    # A blurred, scaled-up copy of the same frame fills the canvas
    # behind it so there are no dead black bars.
    title_draws = ""
    for i, line in enumerate(title_lines):
        y = 90 + i * 70
        title_draws += (
            f",drawtext=text='{_escape_drawtext(line)}':"
            f"fontsize=58:fontcolor=white:"
            f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.45:boxborderw=18:"
            "shadowcolor=black:shadowx=2:shadowy=2"
        )

    caption_draws = ""
    for i, line in enumerate(caption_lines):
        y = f"h-{260 - i * 66}"
        caption_draws += (
            f",drawtext=text='{_escape_drawtext(line)}':"
            f"fontsize=44:fontcolor=white:"
            f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.45:boxborderw=14:"
            "shadowcolor=black:shadowx=2:shadowy=2"
        )

    filter_complex = (
        "[0:v]split=2[bg_src][fg_src];"
        "[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=24,eq=brightness=-0.08[bg];"
        "[fg_src]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[framed];"
        "[framed]drawtext=text='"
        f"{_escape_drawtext('MathConceptsMadeEasy')}':fontsize=34:"
        "fontcolor=yellow:x=(w-text_w)/2:y=h-90:"
        "shadowcolor=black:shadowx=2:shadowy=2"
        f"{title_draws}{caption_draws}[out]"
    )

    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(joined),
        "-t", "59",
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(out_path)
    ], check=True)

    joined.unlink(missing_ok=True)
    concat_list.unlink(missing_ok=True)
    for mux_out in mux_files:
        mux_out.unlink(missing_ok=True)
    return out_path


generated = []
for short_type in SHORT_TYPES:
    path = build_short(short_type)
    size_mb = path.stat().st_size / (1024 * 1024)
    generated.append((short_type["key"], short_type["label"], path, size_mb))

print(f"\n{'═'*65}")
print(f"  🎉 {len(generated)} SHORTS GENERATED — exact 1080x1920 (9:16), nothing cropped")
print(f"{'═'*65}")
for key, label, path, size_mb in generated:
    print(f"  📱 [{key:7s}] {label:18s} {path.name}  ({size_mb:.2f} MB)")
print(f"  ⏱️  Duration : max 59 seconds each")
print(f"  📂 Location : {FINAL_DIR}")
print(f"{'═'*65}")
print(f"\n  ▶ All 3 Shorts are picked up automatically by uploader.youtube_upload,\n"
      f"    spread across the day in America/New_York local time.\n")
