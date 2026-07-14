# ==========================================
# CELL 3: AUDIO ENGINE
# CHANNEL: MathConceptsMadeEasy
# Pattern: FPL Vortex streaming approach
#   → Edge-TTS Ryan (en-GB-RyanNeural)
#   → Streaming chunks (not .save())
#   → 3-attempt retry before gTTS failsafe
#   → Word boundary JSON saved per scene
#     (used by Cell 4 for animation sync)
#   → ffprobe exact duration per scene
#   → Writes duration_seconds back into
#     the timed script JSON
# ==========================================

import sys, json, subprocess, asyncio
from pathlib import Path


import nest_asyncio
nest_asyncio.apply()

import edge_tts
from gtts import gTTS

# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")
# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

VOICE      = cell1_config.TTS_CONFIG["voice"]
_RATE      = cell1_config.TTS_CONFIG["rate"]
_PITCH     = cell1_config.TTS_CONFIG["pitch"]
RETRIES    = 3
RETRY_WAIT = 2   # seconds between Edge-TTS retry attempts

# ── Paths ─────────────────────────────────────────────────────
lesson_data  = cell1_config.CURRICULUM[0]
lesson_id    = lesson_data['id']
SCRIPTS_DIR  = cell1_config.SCRIPTS_DIR
AUDIO_DIR    = cell1_config.AUDIO_DIR

SCRIPT_PATH  = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script.json"
TIMED_PATH   = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
LESSON_AUDIO = AUDIO_DIR   / f"lesson_{lesson_id:03d}"
LESSON_AUDIO.mkdir(parents=True, exist_ok=True)

# ── Load script from Cell 2 ───────────────────────────────────
if not SCRIPT_PATH.exists():
    raise SystemExit(f"🛑 Script not found at {SCRIPT_PATH}. Run Cell 2 first.")

with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    script = json.load(f)

print(f"✅ Script loaded  → {SCRIPT_PATH}")
print(f"   Lesson        : Day {lesson_id} — {script['title']}")
print(f"   Scenes        : {len(script['scenes'])}")
print(f"   Voice         : {VOICE}  |  Rate: {_RATE}  |  Pitch: {_PITCH}")
print(f"   Audio folder  : {LESSON_AUDIO}\n")

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
async def get_exact_duration_async(file_path: Path) -> float:
    """Uses asynchronous ffprobe to prevent event loop blocking."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return round(float(stdout.decode().strip()), 3)
    except Exception as e:
        print(f"      ⚠️  ffprobe failed for {file_path.name}: {e}")
        return 0.0


def normalize_word(w: str) -> str:
    """Strips punctuation for word-matching in animation sync."""
    import re, unicodedata
    w = unicodedata.normalize("NFKD", str(w)).encode("ASCII", "ignore").decode()
    w = re.sub(r"[^\w]", "", w)
    return w.lower()


# ══════════════════════════════════════════════════════════════
# EDGE-TTS STREAMING ENGINE (FPL VORTEX PATTERN)
# Streams audio chunks and word boundary events simultaneously.
# Word boundaries are saved as scene_XX.words.json — used by
# Cell 4 (Manim) to sync text highlights with narration timing.
# ══════════════════════════════════════════════════════════════

async def _stream_edge_tts(
    text: str,
    audio_path: Path,
    words_path: Path,
    pitch_profile: str = "calm_explain",
) -> bool:
    """
    Attempts to generate audio via Edge-TTS streaming.
    Saves MP3 and word-boundary JSON.
    Returns True on success, False on failure.
    """
    for attempt in range(1, RETRIES + 1):
        try:
            profile    = cell1_config.PITCH_PROFILES.get(
                pitch_profile, {"rate": "+0%", "pitch": "+0Hz"}
            )
            comm       = edge_tts.Communicate(
                text, VOICE,
                rate=profile["rate"],
                pitch=profile["pitch"],
            )
            word_list  = []

            with open(str(audio_path), "wb") as audio_f:
                async for chunk in comm.stream():

                    if chunk["type"] == "audio":
                        audio_f.write(chunk["data"])

                    elif chunk["type"] == "WordBoundary":
                        # Convert 100-nanosecond ticks → seconds
                        start_s = chunk["offset"]   / 10_000_000
                        dur_s   = chunk["duration"] / 10_000_000
                        word_list.append({
                            "word"  : chunk["text"],
                            "norm"  : normalize_word(chunk["text"]),
                            "start" : round(start_s, 4),
                            "end"   : round(start_s + dur_s, 4),
                        })

            # Save word boundary data for animation sync
            with open(str(words_path), "w", encoding="utf-8") as wf:
                json.dump(word_list, wf, indent=2, ensure_ascii=False)

            return True   # ✅ Success

        except Exception as e:
            if attempt < RETRIES:
                print(f"      ⚠️  Edge-TTS attempt {attempt}/{RETRIES} failed: "
                      f"{type(e).__name__}. Retrying in {RETRY_WAIT}s...")
                await asyncio.sleep(RETRY_WAIT)
            else:
                print(f"      ❌ Edge-TTS failed after {RETRIES} attempts: {e}")
                return False


def _gtts_fallback(text: str, audio_path: Path, words_path: Path):
    """
    Google TTS failsafe. No word boundaries available.
    Saves an empty words JSON so downstream cells do not crash.
    """
    print("      🔄 Activating failsafe: Google TTS (en, co.uk)...")
    try:
        tts = gTTS(text=text, lang='en', tld='co.uk')
        tts.save(str(audio_path))
        # Save empty word list — Cell 4 will use estimated timing instead
        with open(str(words_path), "w", encoding="utf-8") as wf:
            json.dump([], wf)
        print("      ✓ Failsafe audio saved (Google TTS).")
        return True
    except Exception as e:
        print(f"      ❌ Google TTS also failed: {e}")
        return False
        # ══════════════════════════════════════════════════════════════
# CONCURRENT AUDIO GENERATION ENGINE
# ══════════════════════════════════════════════════════════════

async def process_single_scene(scene: dict) -> dict:
    """Handles TTS streaming and duration calculation for a single scene."""
    scene_id  = scene["scene_id"]
    step      = scene["step"]
    text      = scene["narration"]

    audio_path = LESSON_AUDIO / f"scene_{scene_id:02d}.mp3"
    words_path = LESSON_AUDIO / f"scene_{scene_id:02d}.words.json"

    # Attempt Edge-TTS
    pitch_profile = scene.get("pitch_profile", "calm_explain")
    success = await _stream_edge_tts(text, audio_path, words_path, pitch_profile)

    if not success:
        success = _gtts_fallback(text, audio_path, words_path)
        if not success:
            return {
                "scene_id"     : scene_id,
                "step"         : step,
                "success"      : False,
                "engine"       : "none",
                "duration"     : 0.0,
                "pitch_profile": pitch_profile,
            }

    # Calculate exact duration asynchronously
    exact_dur = await get_exact_duration_async(audio_path)
    # 0.4s buffer already added by Manim scene hold
    # Add 0.25s silence pad to prevent abrupt cuts between scenes
    duration_with_buffer = round(exact_dur + 0.65, 3)
    scene["duration_seconds"] = duration_with_buffer

    # Determine engine used
    engine = "edge-tts" if await _check_words_populated(words_path) else "gtts"

    print(f"      ✅ Scene {scene_id:02d} [{step}] complete. ({duration_with_buffer}s | {engine})")

    return {
        "scene_id"      : scene_id,
        "step"          : step,
        "success"       : True,
        "engine"        : engine,
        "duration"      : duration_with_buffer,
        "audio"         : str(audio_path),
        "words"         : str(words_path),
        "pitch_profile" : pitch_profile,
    }

async def generate_all_audio():
    print(f"🎙️  Audio Engine initialising (Concurrent Mode)...")
    print(f"   Primary  : Ryan {VOICE}  (en-US)")
    print(f"   Scenes   : {len(script['scenes'])}")
    print(f"   Profiles : {list(cell1_config.PITCH_PROFILES.keys())}\n")
    print(f"{'─'*65}")

    # Launch all scenes concurrently
    tasks = [process_single_scene(scene) for scene in script["scenes"]]
    results = await asyncio.gather(*tasks)

    # Sort results to maintain ordered logging/reporting downstream
    results.sort(key=lambda x: x["scene_id"])

    total_duration = sum(r["duration"] for r in results if r["success"])
    script["total_duration_seconds"] = round(total_duration, 3)

    return results, total_duration



async def _check_words_populated(words_path: Path) -> bool:
    """Returns True if word boundary file has actual entries."""
    try:
        with open(str(words_path), "r") as f:
            data = json.load(f)
        return len(data) > 0
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# SAVE TIMED SCRIPT
# ══════════════════════════════════════════════════════════════

def save_timed_script(script: dict, path: Path):
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Timed script saved → {path}")


# ══════════════════════════════════════════════════════════════
# PRINT FINAL REPORT
# ══════════════════════════════════════════════════════════════

def print_report(results: list, total: float):
    succeeded = [r for r in results if r["success"]]
    failed    = [r for r in results if not r["success"]]
    total_min = total / 60

    print(f"\n{'═'*65}")
    print(f"  AUDIO REPORT — Day {lesson_id}: {script['title']}")
    print(f"{'═'*65}")
    print(f"  {'#':<4} {'Step':<14} {'Profile':<18} {'Engine':<10} {'Dur':>8}  Status")
    print(f"  {'─'*65}")

    for s in script["scenes"]:
        r = next((x for x in results if x["scene_id"] == s["scene_id"]), None)
        if r and r["success"]:
            eng     = r.get("engine", "edge-tts")
            dur     = r["duration"]
            profile = r.get("pitch_profile", "unknown")
            status  = "✅"
        else:
            eng, dur, profile, status = "FAILED", 0.0, "—", "❌"
        print(f"  {s['scene_id']:<4} {s['step']:<14} {profile:<18} "
              f"{eng:<10} {dur:>7.3f}s  {status}")

    print(f"  {'─'*63}")
    print(f"  {'TOTAL':>28} {total:>9.3f}s  (~{total_min:.1f} min)")
    print(f"{'═'*65}")
    print(f"\n  Succeeded : {len(succeeded)}/{len(results)} scenes")
    if failed:
        print(f"  ❌ Failed  : {[r['step'] for r in failed]}")
    print(f"\n  Audio folder : {LESSON_AUDIO}")
    print(f"  Timed script : {TIMED_PATH}")
    print(f"\n  ▶ Run Cell 4 next to build Manim animations.\n")


# ══════════════════════════════════════════════════════════════
# EXECUTE & CLEANUP
# ══════════════════════════════════════════════════════════════

# Run the concurrent engine
results, total_duration = asyncio.run(generate_all_audio())

# Finalize the script and report
save_timed_script(script, TIMED_PATH)
print_report(results, total_duration)

# Fail the pipeline if any narration is missing — a lesson must never
# ship with silent scenes.
_failed = [r["step"] for r in results if not r["success"]]
if _failed:
    raise SystemExit(f"🛑 Audio generation failed for scenes: {_failed}. "
                     f"Fix connectivity and re-run (autopilot.py --from-stage 3).")

