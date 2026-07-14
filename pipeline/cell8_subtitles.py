# ==========================================
# CELL 8: SUBTITLE ENGINE
# CHANNEL: MathConceptsMadeEasy
# Reads : lesson_XXX_script_timed.json
#         audio/lesson_XXX/scene_XX.words.json (Edge-TTS word timings)
# Writes: final_videos/Day_XXX_<title>.srt and .vtt
# Timing matches Cell 5's assembly: each scene overlaps the next
# by the 0.3s crossfade, so scene N starts at
#   sum(durations[:N]) - N * 0.3
# ==========================================

import json
from pathlib import Path

# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")

CROSSFADE = 0.3          # must match FADE_DUR in cell5_assembly
MAX_CHARS = 42           # max characters per caption line
MAX_CAPTION_SECONDS = 6  # split captions longer than this

lesson_data = cell1_config.CURRICULUM[0]
lesson_id   = lesson_data["id"]
safe_title  = lesson_data["seo_title"].replace(" ", "_").replace("—", "-")

SCRIPTS_DIR = cell1_config.SCRIPTS_DIR
AUDIO_DIR   = cell1_config.AUDIO_DIR
FINAL_DIR   = cell1_config.FINAL_DIR

TIMED_SCRIPT = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
LESSON_AUDIO = AUDIO_DIR / f"lesson_{lesson_id:03d}"
SRT_PATH     = FINAL_DIR / f"Day_{lesson_id:03d}_{safe_title}.srt"
VTT_PATH     = FINAL_DIR / f"Day_{lesson_id:03d}_{safe_title}.vtt"

if not TIMED_SCRIPT.exists():
    raise SystemExit(f"🛑 Timed script not found at {TIMED_SCRIPT}. Run Cell 3 first.")

with open(TIMED_SCRIPT, encoding="utf-8") as f:
    SCRIPT = json.load(f)


def load_words(scene_id: int) -> list:
    p = LESSON_AUDIO / f"scene_{scene_id:02d}.words.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def captions_from_words(words: list, offset: float) -> list:
    """Group word-boundary entries into readable caption chunks."""
    captions, chunk, chunk_start = [], [], None
    for w in words:
        word = str(w.get("word", "")).strip()
        if not word:
            continue
        start = float(w.get("start", 0.0))
        end = float(w.get("end", start))
        if chunk_start is None:
            chunk_start = start
        chunk.append(word)
        text = " ".join(chunk)
        long_enough = len(text) >= MAX_CHARS or (end - chunk_start) >= MAX_CAPTION_SECONDS
        sentence_end = word.endswith((".", "!", "?"))
        if long_enough or sentence_end:
            captions.append((offset + chunk_start, offset + end, text))
            chunk, chunk_start = [], None
    if chunk:
        last_end = float(words[-1].get("end", chunk_start or 0.0))
        captions.append((offset + (chunk_start or 0.0), offset + last_end, " ".join(chunk)))
    return captions


def captions_from_text(text: str, offset: float, duration: float) -> list:
    """Fallback when word timings are missing: distribute narration
    across the scene proportionally to chunk length."""
    words = text.split()
    chunks, chunk = [], []
    for w in words:
        chunk.append(w)
        if len(" ".join(chunk)) >= MAX_CHARS or w.endswith((".", "!", "?")):
            chunks.append(" ".join(chunk))
            chunk = []
    if chunk:
        chunks.append(" ".join(chunk))
    total_chars = sum(len(c) for c in chunks) or 1
    captions, t = [], offset
    for c in chunks:
        dur = duration * len(c) / total_chars
        captions.append((t, t + dur, c))
        t += dur
    return captions


def fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_vtt(t: float) -> str:
    return fmt_srt(t).replace(",", ".")


# ── Build caption list across all scenes ──────────────────────
all_captions = []
offset = 0.0
for i, scene in enumerate(SCRIPT["scenes"]):
    duration = float(scene.get("duration_seconds") or scene.get("estimated_seconds") or 10.0)
    words = load_words(scene["scene_id"])
    if words:
        caps = captions_from_words(words, offset)
    else:
        caps = captions_from_text(scene["narration"], offset, duration)
    all_captions.extend(caps)
    offset += duration - CROSSFADE  # next scene starts inside the crossfade

# Clamp overlaps introduced by the crossfade
for i in range(len(all_captions) - 1):
    s, e, txt = all_captions[i]
    ns = all_captions[i + 1][0]
    if e > ns:
        all_captions[i] = (s, ns, txt)

# ── Write SRT ─────────────────────────────────────────────────
with open(SRT_PATH, "w", encoding="utf-8") as f:
    for n, (s, e, txt) in enumerate(all_captions, 1):
        f.write(f"{n}\n{fmt_srt(s)} --> {fmt_srt(e)}\n{txt}\n\n")

# ── Write VTT ─────────────────────────────────────────────────
with open(VTT_PATH, "w", encoding="utf-8") as f:
    f.write("WEBVTT\n\n")
    for s, e, txt in all_captions:
        f.write(f"{fmt_vtt(s)} --> {fmt_vtt(e)}\n{txt}\n\n")

print(f"\n{'═' * 65}")
print("  📝 SUBTITLES GENERATED")
print(f"{'═' * 65}")
print(f"  ✅ Captions : {len(all_captions)}")
print(f"  ✅ SRT      : {SRT_PATH}")
print(f"  ✅ VTT      : {VTT_PATH}")
print(f"{'═' * 65}")
