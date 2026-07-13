# ==========================================
# CELL 2: SCRIPT BUILDER
# CHANNEL: MathConceptsMadeEasy
# Reads narrations from Cell 1 config.
# Builds the master script JSON used by:
#   → Cell 3  (audio engine)
#   → Cell 4  (Manim animation)
#   → Cell 5  (video assembly)
# ==========================================

import sys, json
from pathlib import Path

# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")
# ══════════════════════════════════════════════════════════════
# SCENE REGISTRY
# Defines metadata for each of the 9 fixed scene slots.
# animation_type  → used by Cell 4 (Manim) to pick the scene class
# show_formula    → whether the key formula appears on screen
# show_logo       → whether the channel logo is visible (always top-left)
# color_key       → maps to THEME dict in cell1_config
# manim_hint      → plain-English description for the animator
# ══════════════════════════════════════════════════════════════

SCENE_REGISTRY = {
    "opening": {
        "scene_id"       : 1,
        "label"          : "Title Sequence",
        "animation_type" : "TITLE_SEQUENCE",
        "show_formula"   : False,
        "show_logo"      : True,
        "show_banner"    : True,
        "color_key"      : "blue",
        "manim_hint"     : (
            "Day number large and centered. "
            "Topic items slide in one by one below it. "
            "No narration text on screen. Logo top-left no margin."
        ),
        "transition_in"  : "fade",
        "transition_out" : "wipe_right",
    },
    "hook": {
        "scene_id"       : 2,
        "label"          : "Real World Hook",
        "animation_type" : "VISUAL_ONLY",
        "show_formula"   : False,
        "show_logo"      : True,
        "show_banner"    : False,
        "color_key"      : "blue",
        "manim_hint"     : (
            "Show the real world situation from real_world_hook. "
            "Relevant image or illustration. No narration text overlay. "
            "Visual supports what Ryan says without copying it."
        ),
        "transition_in"  : "wipe_right",
        "transition_out" : "wipe_right",
    },
    "concept": {
        "scene_id"       : 3,
        "label"          : "Core Concept",
        "animation_type" : "VISUAL_ONLY",
        "show_formula"   : False,
        "show_logo"      : True,
        "show_banner"    : False,
        "color_key"      : "primary",
        "manim_hint"     : (
            "Clean diagram or illustration supporting the concept. "
            "No bullet points of narration text. "
            "Visual only while Ryan explains."
        ),
        "transition_in"  : "wipe_right",
        "transition_out" : "wipe_right",
    },
    "definition": {
        "scene_id"       : 4,
        "label"          : "Formal Definition",
        "animation_type" : "VISUAL_ONLY",
        "show_formula"   : False,
        "show_logo"      : True,
        "show_banner"    : False,
        "color_key"      : "secondary",
        "manim_hint"     : (
            "Clean visual showing the structure of the definition. "
            "No word for word text of narration. "
            "Support the formal explanation with a relevant diagram."
        ),
        "transition_in"  : "wipe_right",
        "transition_out" : "wipe_right",
    },
    "formula": {
        "scene_id"       : 5,
        "label"          : "Formula Build",
        "animation_type" : "EQUATION_BUILD",
        "show_formula"   : True,
        "show_logo"      : True,
        "show_banner"    : False,
        "color_key"      : "yellow",
        "manim_hint"     : (
            "Formula builds on board one component at a time. "
            "Each part appears as Ryan reads it. "
            "Previous parts stay visible but slightly dimmed. "
            "Full formula never appears all at once."
        ),
        "transition_in"  : "wipe_right",
        "transition_out" : "wipe_right",
    },
    "worked_example": {
        "scene_id"       : 6,
        "label"          : "Worked Example",
        "animation_type" : "BOARD_WRITE",
        "show_formula"   : True,
        "show_logo"      : True,
        "show_banner"    : False,
        "color_key"      : "green",
        "manim_hint"     : (
            "Board write only. Each step of working appears "
            "line by line as Ryan explains it. "
            "No narration text overlay. Math only on board."
        ),
        "transition_in"  : "wipe_right",
        "transition_out" : "wipe_right",
    },
    "mistakes": {
        "scene_id"       : 7,
        "label"          : "Common Mistakes",
        "animation_type" : "BOARD_WRITE",
        "show_formula"   : False,
        "show_logo"      : True,
        "show_banner"    : False,
        "color_key"      : "red",
        "manim_hint"     : (
            "Wrong working shown first with red cross. "
            "Correct version written below in green. "
            "Board write style. No narration text."
        ),
        "transition_in"  : "wipe_right",
        "transition_out" : "wipe_right",
    },
    "practice": {
        "scene_id"       : 8,
        "label"          : "Practice Problem",
        "animation_type" : "BOARD_WRITE",
        "show_formula"   : True,
        "show_logo"      : True,
        "show_banner"    : False,
        "color_key"      : "green",
        "manim_hint"     : (
            "Question written at top. Solution builds step by step. "
            "Each line appears as Ryan works through it. "
            "Final answer in green box with tick."
        ),
        "transition_in"  : "wipe_right",
        "transition_out" : "wipe_right",
    },
    "summary": {
        "scene_id"       : 9,
        "label"          : "Summary and Close",
        "animation_type" : "VISUAL_ONLY",
        "show_formula"   : True,
        "show_logo"      : True,
        "show_banner"    : True,
        "color_key"      : "blue",
        "manim_hint"     : (
            "Clean summary card. Channel name at top. "
            "Key formula centered. Next lesson teaser below. "
            "No word for word narration text."
        ),
        "transition_in"  : "fade",
        "transition_out" : "fade",
    },
}

# ══════════════════════════════════════════════════════════════
# DURATION ESTIMATOR
# Assumes 140 words per minute for calm educational TTS.
# Cell 3 will overwrite duration_seconds with exact ffprobe value.
# ══════════════════════════════════════════════════════════════

WPM = 140

SCENE_WPM = {
    "calm_intro"       : 130,
    "excited_hook"     : 155,
    "calm_explain"     : 125,
    "slow_formal"      : 110,
    "slow_formula"     : 85,
    "emphasis"         : 120,
    "friendly_mistake" : 135,
    "encouraging"      : 140,
    "warm_close"       : 125,
}

def estimate_duration(text: str, pitch_profile: str = "calm_explain") -> float:
    wpm = SCENE_WPM.get(pitch_profile, 135)
    words = len(text.split())
    return round((words / wpm) * 60.0, 2)

def word_count(text: str) -> int:
    return len(text.split())

# ══════════════════════════════════════════════════════════════
# SCRIPT BUILDER
# ══════════════════════════════════════════════════════════════

def build_script(config) -> dict:
    lesson       = config.CURRICULUM[0]
    narrations   = lesson['scene_narrations']
    lesson_id    = lesson['id']

    print(f"🏗️  Building script for Day {lesson_id}: {lesson['title']}")
    print(f"   Channel  : {config.CHANNEL_NAME}")
    print(f"   Track    : {lesson['global_track']}")
    print(f"   Subject  : {lesson['subject']}")
    print()

    # ── Build scene list ─────────────────────────────────────
    scenes = []
    total_estimated = 0.0

    step_order = cell1_config.SCENE_ORDER

    for step in step_order:
        narration_block = narrations.get(step, {})
        narration_text = narration_block["full"] if isinstance(narration_block, dict) else narration_block
        if not narration_text.strip():
            print(f"   ⚠️  Scene '{step}' has empty narration — skipping.")
            continue

        registry      = SCENE_REGISTRY[step]
        wc            = word_count(narration_text)
        pitch         = cell1_config.SCENE_PITCH_MAP.get(step, "calm_explain")
        est_secs      = estimate_duration(narration_text, pitch)
        total_estimated += est_secs

        scene = {
            # ── Identity ──────────────────────────────────────
            "scene_id"        : registry["scene_id"],
            "step"            : step,
            "label"           : registry["label"],
            "pitch_profile"   : cell1_config.SCENE_PITCH_MAP.get(step, "calm_explain"),

            # ── Narration (used by Cell 3 for TTS) ───────────
            "narration"       : narration_text,
            "word_count"      : wc,
            "estimated_seconds": est_secs,
            "duration_seconds": 0.0,   # filled by Cell 3 (ffprobe)

            # ── Visual metadata (used by Cell 4 for Manim) ───
            "animation_type"  : registry["animation_type"],
            "show_formula"    : registry["show_formula"],
            "show_logo"       : registry["show_logo"],
            "show_banner"     : registry["show_banner"],
            "color_key"       : registry["color_key"],
            "manim_hint"      : registry["manim_hint"],
            "transition_in"   : registry["transition_in"],
            "transition_out"  : registry["transition_out"],

            # ── Lesson content for on-screen rendering ────────
            "key_formula"     : lesson["key_formula"],
            "formula_spoken"  : lesson["formula_spoken"],
            "visual_type"     : lesson.get("visual_type", "board_write"),
            "real_world_hook" : lesson.get("real_world_hook", ""),
            "visual_hints"    : lesson.get("visual_hints", ""),
            "board_examples"  : lesson.get("board_examples", {}),
            "animation_type"  : cell1_config.SCENE_ANIMATION_MAP.get(step, "VISUAL_ONLY"),
        }
        scenes.append(scene)
        print(f"   ✅ Scene {registry['scene_id']:02d} [{step:10s}]  "
              f"{wc:>4} words  ~{est_secs:>6.1f}s  [{registry['animation_type']}]")

    print()

    # ── Assemble full script document ────────────────────────
    script = {
        # ── Header ────────────────────────────────────────────
        "channel"              : config.CHANNEL_NAME,
        "lesson_id"            : lesson_id,
        "title"                : lesson["title"],
        "subtopic"             : lesson["subtopic"],
        "global_track"         : lesson["global_track"],
        "subject"              : lesson["subject"],
        "concept_cluster"      : lesson["concept_cluster"],
        "exam_tags"            : lesson["exam_tags"],
        "lesson_goal"          : lesson["lesson_goal"],
        "prerequisite"         : lesson["prerequisite"],
        "key_formula"          : lesson["key_formula"],
        "formula_spoken"       : lesson["formula_spoken"],
        "visual_type"          : lesson["visual_type"],
        "video_type"           : lesson["video_type"],
        "seo_title"            : lesson["seo_title"],
        "thumbnail_angle"      : lesson["thumbnail_angle"],
        "playlist"             : lesson["playlist"],
        "heading"              : lesson["heading"],
        "subheading"           : lesson["subheading"],
        "intro_teaser"         : lesson["intro_teaser"],
        "outro_message"        : lesson["outro_message"],

        # ── Asset paths ───────────────────────────────────────
        "banner_path"          : str(config.BANNER_PATH),

        # ── Theme ─────────────────────────────────────────────
        "theme"                : config.THEME,
        "tts_config"           : config.TTS_CONFIG,
        "resolution"           : config.RESOLUTION,

        # ── Scenes ────────────────────────────────────────────
        "scenes"               : scenes,

        # ── Timing (Cell 3 fills in duration_seconds per scene
        #            and total_duration_seconds) ───────────────
        "estimated_total_seconds" : round(total_estimated, 2),
        "total_duration_seconds"  : 0.0,
    }

    return script


# ══════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════

def validate_script(script: dict) -> bool:
    print("🔍 Validating script...")
    passed = True

    required_top = [
        "channel", "lesson_id", "title", "subtopic", "lesson_goal",
        "key_formula", "formula_spoken", "seo_title", "scenes",
    ]
    for field in required_top:
        if not script.get(field):
            print(f"   ❌ MISSING top-level field: {field}")
            passed = False
        else:
            print(f"   ✅ {field}")

    scenes = script.get("scenes", [])
    if len(scenes) != 9:
        print(f"   ❌ Expected 9 scenes, got {len(scenes)}")
        passed = False
    else:
        print(f"   ✅ Scene count: {len(scenes)}")

    for s in scenes:
        narration = s.get("narration", {})
        narration_text = narration["full"] if isinstance(narration, dict) else narration
        if not str(narration_text).strip():
            print(f"   ❌ Scene {s['scene_id']} [{s['step']}] has empty narration")
            passed = False
        if s.get("word_count", 0) < 20:
            print(f"   ⚠️  Scene {s['scene_id']} [{s['step']}] is very short "
                  f"({s['word_count']} words) — consider expanding")

    if passed:
        print("✅ Script validation passed.\n")
    else:
        print("🛑 Script validation FAILED.\n")
    return passed


# ══════════════════════════════════════════════════════════════
# SAVE SCRIPT
# ══════════════════════════════════════════════════════════════

def save_script(script: dict, config) -> Path:
    lesson_id   = script["lesson_id"]
    out_path    = config.SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    print(f"✅ Script saved → {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════
# PRINT SUMMARY TABLE
# ══════════════════════════════════════════════════════════════

def print_summary(script: dict):
    lesson_id  = script["lesson_id"]
    title      = script["title"]
    scenes     = script["scenes"]
    est_total  = script["estimated_total_seconds"]
    est_min    = est_total / 60

    print(f"\n{'═'*65}")
    print(f"  SCRIPT SUMMARY — Day {lesson_id}: {title}")
    print(f"{'═'*65}")
    print(f"  {'#':<4} {'Step':<12} {'Label':<28} {'Words':>6} {'Est.s':>7}")
    print(f"  {'─'*63}")
    for s in scenes:
        print(f"  {s['scene_id']:<4} {s['step']:<12} {s['label']:<28} "
              f"{s['word_count']:>6} {s['estimated_seconds']:>7.1f}s")
    print(f"  {'─'*63}")
    print(f"  {'TOTAL':>46} {est_total:>7.1f}s  (~{est_min:.1f} min)")
    print(f"{'═'*65}")
    print(f"\n  Channel   : {script['channel']}")
    print(f"  SEO Title : {script['seo_title']}")
    print(f"  Playlist  : {script['playlist']}")
    print(f"  Banner    : {script['banner_path']}")
    print(f"\n  ▶ Run Cell 3 next to generate audio.\n")


# ══════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════

SCRIPT = build_script(cell1_config)

if not validate_script(SCRIPT):
    raise SystemExit("🛑 Script validation failed. Fix issues above before continuing.")

SCRIPT_PATH = save_script(SCRIPT, cell1_config)
print_summary(SCRIPT)

