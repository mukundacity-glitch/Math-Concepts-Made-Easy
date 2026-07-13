# ==========================================
# CELL 5: VIDEO ASSEMBLY ENGINE
# CHANNEL: MathConceptsMadeEasy
# ==========================================

import sys, json, subprocess, shutil
from pathlib import Path

# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")
# ══════════════════════════════════════════════════════════════
# PATHS AND METADATA
# ══════════════════════════════════════════════════════════════

lesson_data = cell1_config.CURRICULUM[0]
lesson_id   = lesson_data['id']
seo_title   = lesson_data['seo_title'].replace(" ", "_").replace("—", "-")

SCRIPTS_DIR = cell1_config.SCRIPTS_DIR
AUDIO_DIR   = cell1_config.AUDIO_DIR
RENDERS_DIR = cell1_config.RENDERS_DIR
FINAL_DIR   = cell1_config.FINAL_DIR

TIMED_SCRIPT  = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
LESSON_AUDIO  = AUDIO_DIR   / f"lesson_{lesson_id:03d}"
LESSON_RENDER = RENDERS_DIR / f"lesson_{lesson_id:03d}"
LESSON_FINAL  = FINAL_DIR   / f"lesson_{lesson_id:03d}"

LESSON_FINAL.mkdir(parents=True, exist_ok=True)
TEMP_MUX_DIR = LESSON_FINAL / "temp_mux"
TEMP_MUX_DIR.mkdir(exist_ok=True)

FINAL_VIDEO_NAME = f"Day_{lesson_id:03d}_{seo_title}.mp4"
FINAL_VIDEO_PATH = FINAL_DIR / FINAL_VIDEO_NAME

if not TIMED_SCRIPT.exists():
    raise SystemExit(f"🛑 Timed script not found at {TIMED_SCRIPT}. Run Cell 3 first.")

with open(TIMED_SCRIPT, "r", encoding="utf-8") as f:
    SCRIPT = json.load(f)

print(f"✅ Timed script loaded → {TIMED_SCRIPT.name}")
print(f"   Lesson  : Day {lesson_id} — {SCRIPT['title']}")
print(f"   Scenes  : {len(SCRIPT['scenes'])}")
print(f"   Target  : {FINAL_VIDEO_NAME}\n")

# ══════════════════════════════════════════════════════════════
# FFmpeg HELPERS
# ══════════════════════════════════════════════════════════════

def mux_scene(scene_id, step, vid_path, aud_path, out_path):
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(vid_path),
        "-i", str(aud_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(out_path)
    ]
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"      ❌ Mux failed for scene {scene_id:02d}: {e}")
        return False

def concat_scenes(concat_txt, out_path):
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(out_path)
    ]
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Final concatenation failed: {e}")
        return False

# ══════════════════════════════════════════════════════════════
# ADD_CROSSFADES  ← NOW DEFINED HERE, ABOVE assemble_video
# ══════════════════════════════════════════════════════════════

def add_crossfades(muxed_files, out_path):
    """
    Applies 0.3s crossfade between every consecutive scene pair.
    Falls back to hard cut concat if xfade fails.
    """
    if len(muxed_files) < 2:
        # FIX: was calling undefined build_concat_txt() — now inline
        concat_txt = out_path.parent / "concat_fallback.txt"
        with open(concat_txt, "w") as f:
            for mf in sorted(muxed_files):
                f.write(f"file '{str(mf.absolute())}'\n")
        return concat_scenes(concat_txt, out_path)

    print("  🎞️  Applying crossfade transitions between scenes...")

    durations = []
    for f in muxed_files:
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(f)
        ], capture_output=True, text=True)
        try:
            durations.append(float(probe.stdout.strip()))
        except Exception:
            durations.append(10.0)

    FADE_DUR = 0.3
    inputs = []
    for f in muxed_files:
        inputs += ["-i", str(f)]

    filter_parts = []
    audio_parts  = []
    offset = 0.0

    for i in range(len(muxed_files) - 1):
        offset += durations[i] - FADE_DUR
        if i == 0:
            v_in = "[0:v][1:v]"
            a_in = "[0:a][1:a]"
        else:
            v_in = f"[vfade{i}][{i+1}:v]"
            a_in = f"[afade{i}][{i+1}:a]"

        v_out = f"[vfade{i+1}]" if i < len(muxed_files) - 2 else "[vout]"
        a_out = f"[afade{i+1}]" if i < len(muxed_files) - 2 else "[aout]"

        filter_parts.append(
            f"{v_in}xfade=transition=fade:duration={FADE_DUR}"
            f":offset={offset:.3f}{v_out}"
        )
        audio_parts.append(
            f"{a_in}acrossfade=d={FADE_DUR}{a_out}"
        )

    filter_complex = ";".join(filter_parts + audio_parts)

    cmd = (
        ["ffmpeg", "-y", "-v", "error"]
        + inputs
        + [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            str(out_path)
        ]
    )

    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Crossfade failed: {e}")
        print(f"   Falling back to hard cut concat...")
        concat_txt = out_path.parent / "concat_fallback.txt"
        with open(concat_txt, "w") as f:
            for mf in sorted(muxed_files):
                f.write(f"file '{str(mf.absolute())}'\n")
        return concat_scenes(concat_txt, out_path)

# ══════════════════════════════════════════════════════════════
# ASSEMBLY ENGINE
# ══════════════════════════════════════════════════════════════

def assemble_video(script):
    print(f"{'═'*65}")
    print(f"  ASSEMBLING FINAL VIDEO — Day {lesson_id}")
    print(f"{'═'*65}\n")

    muxed_files   = []
    missing_files = False

    # 1. Verification and Muxing Phase
    for scene in script["scenes"]:
        scene_id = scene["scene_id"]
        step     = scene["step"]
        label    = scene["label"]

        vid_path = LESSON_RENDER / f"scene_{scene_id:02d}_{step}.mp4"
        aud_path = LESSON_AUDIO  / f"scene_{scene_id:02d}.mp3"
        mux_path = TEMP_MUX_DIR  / f"muxed_{scene_id:02d}.mp4"

        print(f"  ▶ Scene {scene_id:02d} [{step:10s}] {label}")

        if not vid_path.exists():
            print(f"      ❌ Missing Video: {vid_path.name}")
            missing_files = True
        elif not aud_path.exists():
            print(f"      ❌ Missing Audio: {aud_path.name}")
            missing_files = True
        else:
            success = mux_scene(scene_id, step, vid_path, aud_path, mux_path)
            if success:
                muxed_files.append(mux_path)
                size_mb = mux_path.stat().st_size / (1024 * 1024)
                print(f"      ✅ Muxed   → {mux_path.name} ({size_mb:.1f} MB)")
            else:
                missing_files = True

    print()

    if missing_files or len(muxed_files) != len(script["scenes"]):
        raise SystemExit("🛑 Missing or failed chunks. Assembly aborted.")

    # 2. Concatenation Phase with crossfades
    print(f"  🎬 Rendering Final Output with Crossfades...")
    concat_success = add_crossfades(sorted(muxed_files), FINAL_VIDEO_PATH)

    # 3. Cleanup
    if concat_success:
        print("  🧹 Cleaning up temporary mux files...")
        shutil.rmtree(TEMP_MUX_DIR, ignore_errors=True)
        return True
    else:
        return False

# ══════════════════════════════════════════════════════════════
# EXECUTION & REPORTING
# ══════════════════════════════════════════════════════════════

success = assemble_video(SCRIPT)

if success:
    probe = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type",
        "-of", "default=noprint_wrappers=1",
        str(FINAL_VIDEO_PATH)
    ], capture_output=True, text=True)

    has_video     = "video" in probe.stdout
    has_audio     = "audio" in probe.stdout
    final_size_mb = FINAL_VIDEO_PATH.stat().st_size / (1024 * 1024)

    print(f"\n{'═'*65}")
    print(f"  🎉 VIDEO ASSEMBLY COMPLETE")
    print(f"{'═'*65}")
    print(f"  ✅ Status    : Success")
    print(f"  🎞️  Video     : {'✅ Present' if has_video else '❌ MISSING'}")
    print(f"  🔊 Audio     : {'✅ Present' if has_audio else '❌ MISSING'}")
    print(f"  🎞️  File      : {FINAL_VIDEO_NAME}")
    print(f"  💾 Size      : {final_size_mb:.2f} MB")
    print(f"  ⏱️  Duration  : {SCRIPT['total_duration_seconds']:.1f}s")
    print(f"  📂 Location  : {FINAL_VIDEO_PATH.parent}")
    print(f"{'═'*65}")
    print(f"\n  ▶ Run Cell 6 for thumbnail. Run Cell 7 to upload.\n")
else:
    print(f"\n🛑 Assembly failed. Check FFmpeg logs above.")

