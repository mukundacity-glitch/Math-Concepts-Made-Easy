# ==========================================
# CELL 1: LESSON & NARRATION BUILDER
# CHANNEL: MathConceptsMadeEasy
# Reads : curriculum/*.json  (lesson data)
# Writes: <output>/cell1_config.py + logs/day_XXX_log.json
# ==========================================

import os, sys, json, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.paths import BASE_DIR, BANNER_PATH, ensure_output_folders, get_day_number
from pipeline.constants import (
    ANIMATION_PHILOSOPHY, PITCH_PROFILES,
    SCENE_ORDER, SCENE_PITCH_MAP, SCENE_ANIMATION_MAP,
)
from pipeline.curriculum import MASTER_CURRICULUM, get_lesson

ensure_output_folders()
DAY_NUMBER = get_day_number()

if BANNER_PATH.exists():
    print(f"✅ Banner found → {BANNER_PATH}")
else:
    print(f"⚠️  Banner 2.png not found at {BANNER_PATH} — plain background will be used.")

TODAY      = get_lesson(DAY_NUMBER)
TODAY["class_level"] = TODAY.get("class_level", TODAY.get("global_track", "Global"))
TODAY["board"]       = TODAY.get("board", "Global")
TODAY["chapter"]     = TODAY.get("chapter", TODAY.get("subject", TODAY.get("topic", "Untitled")))
TODAY_DATE = datetime.date.today().strftime("%A, %d %B %Y")
HEADING    = f"Day {DAY_NUMBER} — {TODAY['topic']}"
SUBHEADING = f"{TODAY.get('class_level','Unknown Class')} | {TODAY.get('subject','')} | {TODAY_DATE}"

INTRO_TEASER = ""
for row in MASTER_CURRICULUM:
    if row["day"] == DAY_NUMBER + 1:
        INTRO_TEASER = f"Next lesson: {row['topic']} — {row['subtopic']}"
        break
if not INTRO_TEASER:
    INTRO_TEASER = "Stay tuned — next lesson coming tomorrow on MathConceptsMadeEasy."

# Short spoken recap of the previous lesson, used in today's opening
PREV_RECAP = ""
for row in MASTER_CURRICULUM:
    if row["day"] == DAY_NUMBER - 1:
        PREV_RECAP = (
            f"Before we start, a quick recap. "
            f"In our last lesson, Day {row['day']}, we studied {row['topic']} — "
            f"{row['subtopic']}. "
            f"If any of that feels unclear, pause here and rewatch Day {row['day']} first, "
            f"because today builds directly on it. "
        )
        break

print(f"\n{'═'*60}")
print(f"  Channel    : MathConceptsMadeEasy")
print(f"  Day        : {DAY_NUMBER}")
print(f"  Date       : {TODAY_DATE}")
print(f"  Track      : {TODAY['global_track']}")
print(f"  Subject    : {TODAY['subject']}")
print(f"  Topic      : {TODAY['topic']}")
print(f"  Subtopic   : {TODAY['subtopic']}")
print(f"  Goal       : {TODAY['lesson_goal']}")
print(f"  Hook       : {TODAY.get('real_world_hook', '')[:55]}...")
print(f"  Est. Time  : {TODAY['estimated_minutes']} minutes")
print(f"  SEO Title  : {TODAY['seo_title']}")
print(f"  Playlist   : {TODAY['playlist']}")
print(f"  Teaser     : {INTRO_TEASER}")
print(f"{'═'*60}\n")

# ══════════════════════════════════════════════════════════════
# QUALITY GATE
# ══════════════════════════════════════════════════════════════

def validate_lesson(lesson: dict) -> bool:
    required = [
        "day", "global_track", "subject", "concept_cluster",
        "topic", "subtopic", "lesson_goal", "prerequisite",
        "key_formula", "formula_spoken",
        "seo_title", "playlist", "status",
        # ── PREMIUM EDUCATIONAL FIELDS ENFORCEMENT ──
        "real_world_hook", "concept_intuition", "common_mistake"
]

    passed = True
    print("🔍 Running quality gate...")
    for field in required:
        if not lesson.get(field):
            print(f"   ❌ MISSING: {field}")
            passed = False
        else:
            print(f"   ✅ {field}")

    if lesson.get("status") != "active":
        print(f"   ❌ Status is '{lesson.get('status')}' — must be 'active'.")
        passed = False

    if passed:
        print("✅ Quality gate passed.\n")
    else:
        print("\n🛑 Quality gate FAILED. Please fill in the missing premium fields.\n")
    return passed

# ══════════════════════════════════════════════════════════════
# DEDICATED NARRATION ENGINE — NO API, PURE PYTHON
# Produces 9 teacher-quality scenes for any lesson in the
# curriculum. Reads every field from the lesson dict and
# builds narrations that sound like a real classroom teacher.
# ══════════════════════════════════════════════════════════════

import re

from pipeline.mathtext import latex_to_speech, split_sentences


def clean_math_for_speech(text_or_list) -> str:
    """Translates LaTeX into spoken English so Ryan literally reads the math."""
    return latex_to_speech(text_or_list)


def write_narrations(lesson: dict, teaser: str, heading: str, recap: str = "") -> dict:
    topic             = lesson['topic']
    subtopic          = lesson['subtopic']
    goal              = lesson['lesson_goal']
    prereq            = lesson['prerequisite']
    formula           = lesson['formula_spoken']
    day               = lesson['day']
    real_world_hook   = lesson.get('real_world_hook', '')
    concept_intuition = lesson.get('concept_intuition', '')
    common_mistake    = lesson.get('common_mistake', '')

    board             = lesson.get('board_examples', {})
    # Dynamically translate the math for this specific day!
    spoken_worked     = clean_math_for_speech(board.get('worked_example', []))
    spoken_practice   = clean_math_for_speech(board.get('practice', []))

    # Every scene narrates ITS OWN on-screen content, so Cell 4 can show
    # each visual at the exact moment it is spoken. Never narrate stage
    # directions (visual_hints) — they drive visuals, not the voice.

    # ════════════════════════════════════════════════════════
    # SCENE 1: OPENING — welcome, orientation, goal
    # ════════════════════════════════════════════════════════
    opening = (
        f"Welcome to Math Concepts Made Easy. "
        f"Today is Day {day}, and our lesson is all about {topic}. "
        f"{recap}"
        f"By the end of this lesson, {goal}. "
        f"Grab a notebook, get comfortable, and let us begin."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 2: HOOK — the real-world story, spoken while the
    # matching illustration plays on screen
    # ════════════════════════════════════════════════════════
    hook = (
        f"Before we touch any formulas, let me show you where this idea "
        f"already lives in your everyday life. "
        f"{real_world_hook} "
        f"You have been using this idea all along — today we simply give "
        f"it a name and learn its rules."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 3: CONCEPT — the intuition behind the idea
    # ════════════════════════════════════════════════════════
    concept = (
        f"So what is really going on here? "
        f"{concept_intuition} "
        f"Keep that picture in your mind, because everything else in this "
        f"lesson grows out of it."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 4: FORMAL DEFINITION
    # ════════════════════════════════════════════════════════
    definition = (
        f"Now we are ready to say this precisely, the way mathematicians do. "
        f"Here is our focus for today: {subtopic}. "
        f"In symbols, we write it as {formula}. "
        f"Every word of that definition matters, so read it slowly. "
        f"You already know {prereq} — this definition simply builds on "
        f"those familiar ideas."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 5: FORMULA BUILD
    # ════════════════════════════════════════════════════════
    formula_scene = (
        f"Here is the key formula for {topic}. "
        f"The formula is: {formula}. "
        f"Watch how each part appears as I say it. "
        f"Do not just memorise the symbols — make sure you understand "
        f"what each one represents, because that is what the exam really tests."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 6: WORKED EXAMPLE (dynamically reads the math)
    # ════════════════════════════════════════════════════════
    worked_example = (
        f"Let us put this to work with real examples, one step at a time. "
        f"{spoken_worked} "
        f"Notice how every line follows logically from the one before it. "
        f"That habit — checking each step — is what makes your answers reliable."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 7: COMMON MISTAKES
    # ════════════════════════════════════════════════════════
    mistakes = (
        f"Now, a quick warning, because I see students lose marks on this "
        f"every single year. "
        f"{common_mistake} "
        f"Compare the wrong way and the right way on screen, and promise "
        f"yourself you will never fall for this one."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 8: PRACTICE (dynamically reads the math)
    # ════════════════════════════════════════════════════════
    practice = (
        f"Time to try it yourself. Here is your practice question. "
        f"Pause the video if you want to attempt it first — then we will "
        f"solve it together. "
        f"{spoken_practice} "
        f"How did you do? If you slipped anywhere, rewind and watch that "
        f"step again — that is exactly how strong students learn."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 9: SUMMARY
    # ════════════════════════════════════════════════════════
    summary = (
        f"Let us bring today's lesson together. "
        f"We explored {topic} — {subtopic}. "
        f"The one formula to remember is {formula}. "
        f"And remember our goal: {goal}. "
        f"{teaser}. "
        f"New lessons every day on Math Concepts Made Easy. "
        f"Thank you for learning with me — see you tomorrow."
    )
    def block(text):
        text = " ".join(str(text).split())
        return {"full": text, "beats": split_sentences(text)}

    return {
        "opening"       : block(opening),
        "hook"          : block(hook),
        "concept"       : block(concept),
        "definition"    : block(definition),
        "formula"       : block(formula_scene),
        "worked_example": block(worked_example),
        "mistakes"      : block(mistakes),
        "practice"      : block(practice),
        "summary"       : block(summary),
    }



if not validate_lesson(TODAY):
    raise SystemExit("🛑 Pipeline stopped: lesson failed the quality gate.")

print("✍️  Writing dedicated narrations (no API)...")
NARRATIONS = write_narrations(TODAY, INTRO_TEASER, HEADING, PREV_RECAP)
print("✅ All 9 narrations written.\n")

# ── Preview first 120 chars of each scene ────────────────────
for scene, text in NARRATIONS.items():
    preview = text["full"] if isinstance(text, dict) else text
    print(f"  [{scene:10s}] {preview[:110]}...")
print()

# ══════════════════════════════════════════════════════════════
# MATH CORRECTNESS CHECK
# ══════════════════════════════════════════════════════════════

def check_math(lesson: dict) -> bool:
    print("🔢 Running math syntax check...")
    formula = lesson.get('key_formula', '')

    # 1. Check for unbalanced LaTeX brackets
    if formula.count('{') != formula.count('}'):
        print(f"   🛑 CRITICAL: Unbalanced braces in formula: {formula}")
        return False

    # 2. Check for missing backslashes on standard trig/limit operators
    for operator in ['sin', 'cos', 'tan', 'lim', 'int', 'sum']:
        # If the operator is present but not preceded by a backslash
        if f"{operator}" in formula and f"\\{operator}" not in formula:
            print(f"   ⚠️ WARNING: Missing backslash for operator '{operator}' in {formula}")

    print(f"   Formula     : {formula}")
    print(f"   Spoken form : {lesson['formula_spoken']}")
    print("✅ Math syntax check passed.\n")
    return True

if not check_math(TODAY):
    raise SystemExit("🛑 Pipeline stopped: Invalid mathematical syntax detected.")

# ══════════════════════════════════════════════════════════════
# OUTRO NARRATION
# ══════════════════════════════════════════════════════════════

OUTRO_NARRATION = (
    f"That brings us to the end of Day {DAY_NUMBER} — {TODAY['topic']}. "
    f"Today we worked carefully through the key ideas step by step. "
    f"And hopefully what once felt confusing now feels much clearer. "
    f"{TODAY['lesson_goal'].capitalize()}. "
    f"But remember something important: "
    f"understanding grows through practice. "
    f"Watching a lesson is the first step, "
    f"but trying questions on your own is where real learning begins. "
    f"So before the next lesson, "
    f"take a few minutes to review your notes and practice what we covered today. "
    f"Even ten or fifteen minutes of focused practice can make a huge difference. "
    f"If something still feels difficult, "
    f"that is completely normal. "
    f"Learning difficult ideas takes time, repetition, and patience. "
    f"Keep showing up, keep practicing, and trust the process. "
    f"{INTRO_TEASER}. "
    f"We are building understanding one lesson at a time, one step at a time. "
    f"New lessons every day on MathConceptsMadeEasy. "
    f"Thank you for learning with me today, and I will see you tomorrow."
)

# ══════════════════════════════════════════════════════════════
# BUILD CELL1_CONFIG.PY  — used by all downstream cells
# ══════════════════════════════════════════════════════════════

import json
import pprint

# Calculate these safely outside the f-string
teacher_style_val = f"Elite {TODAY.get('class_level', 'University')}-level {TODAY.get('subject', 'Mathematics')} Professor"
student_level_val = TODAY.get('class_level', 'Undergraduate')

# Build the dictionary natively to avoid f-string brace crashing
curriculum_data = {
    "id"              : DAY_NUMBER,
    "title"           : TODAY['topic'],
    "subtopic"        : TODAY['subtopic'],
    "global_track"    : TODAY['global_track'],
    "subject"         : TODAY['subject'],
    "concept_cluster" : TODAY['concept_cluster'],
    "exam_tags"       : TODAY.get('exam_tags', []),
    "lesson_goal"     : TODAY['lesson_goal'],
    "prerequisite"    : TODAY['prerequisite'],
    "key_formula"     : TODAY['key_formula'],
    "formula_spoken"  : TODAY['formula_spoken'],
    "visual_type"     : TODAY.get('visual_type', 'board_write'),
    "real_world_hook" : TODAY.get('real_world_hook', ''),
    "concept_intuition": TODAY.get('concept_intuition', ''),
    "common_mistake"  : TODAY.get('common_mistake', ''),
    "visual_hints"    : TODAY.get('visual_hints', ''),
    "board_examples"  : TODAY.get('board_examples', {}),
    "video_type"      : TODAY['video_type'],
    "seo_title"       : TODAY['seo_title'],
    "thumbnail_angle" : TODAY['thumbnail_angle'],
    "playlist"        : TODAY['playlist'],
    "teacher_style"   : teacher_style_val,
    "teaching_tone"   : "Natural, humanized, detailed, calm, authoritative",
    "explanation_depth": "High",
    "teaching_method" : "Explain step-by-step, never skip logic, teach why before formula",
    "student_level"   : student_level_val,
    "pace"            : "Medium slow for understanding",
    "voice_personality": "Professional classroom teacher",
    "real_world_focus": True,
    "human_pause_style": True,
    "repeat_key_ideas": True,
    "mistake_prevention": True,
    "exam_focus"      : True,
    "professional_teacher_mode": True,
    "heading"         : HEADING,
    "subheading"      : SUBHEADING,
    "intro_teaser"    : INTRO_TEASER,
    "outro_message"   : OUTRO_NARRATION,
        "scene_narrations": {
    "opening"       : NARRATIONS.get('opening', {}),
    "hook"          : NARRATIONS.get('hook', {}),
    "concept"       : NARRATIONS.get('concept', {}),
    "definition"    : NARRATIONS.get('definition', {}),
    "formula"       : NARRATIONS.get('formula', {}),
    "worked_example": NARRATIONS.get('worked_example', {}),
    "mistakes"      : NARRATIONS.get('mistakes', {}),
    "practice"      : NARRATIONS.get('practice', {}),
    "summary"       : NARRATIONS.get('summary', {})
}
}

# Format it perfectly as a string
curriculum_str = pprint.pformat(curriculum_data, sort_dicts=False, width=100)

config_code = f"""
from pathlib import Path

CHANNEL_NAME    = "MathConceptsMadeEasy"
BASE_DIR        = Path(r"{BASE_DIR}")
SCRIPTS_DIR     = BASE_DIR / "scripts"
AUDIO_DIR       = BASE_DIR / "audio"
ASSETS_DIR      = BASE_DIR / "assets"
RENDERS_DIR     = BASE_DIR / "renders"
FINAL_DIR       = BASE_DIR / "final_videos"
PNG_DIR         = BASE_DIR / "png"
THUMBNAILS_DIR  = BASE_DIR / "thumbnails"
BANNER_PATH     = BASE_DIR / "2.png"
LOGO_PATH       = ASSETS_DIR / "logo.png"


THEME = {{
    "bg"        : "#0D1B2A",
    "primary"   : "#F0F4F8",
    "secondary" : "#8899AA",
    "blue"      : "#3B9EFF",
    "green"     : "#2ECC71",
    "yellow"    : "#F6C90E",
    "red"       : "#E74C3C",
    "card_bg"   : "#1A2B3C",
}}

TTS_CONFIG = {{
    "voice" : "en-GB-RyanNeural",
    "rate"  : "-12%",
    "pitch" : "-1Hz",
}}

RESOLUTION = {{
    "long_form" : (1920, 1080),
    "shorts"    : (1080, 1920),
}}

ANIMATION_PHILOSOPHY = {repr(ANIMATION_PHILOSOPHY)}
PITCH_PROFILES = {repr(PITCH_PROFILES)}
SCENE_ORDER = {repr(SCENE_ORDER)}
SCENE_PITCH_MAP = {repr(SCENE_PITCH_MAP)}
SCENE_ANIMATION_MAP = {repr(SCENE_ANIMATION_MAP)}

CURRICULUM = [
{curriculum_str}
]
"""

config_path = BASE_DIR / "cell1_config.py"
with open(config_path, "w", encoding="utf-8") as f:
    f.write(config_code.strip())

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ── Save log ──────────────────────────────────────────────────
log_path = BASE_DIR / "logs" / f"day_{DAY_NUMBER:03d}_log.json"
with open(log_path, "w", encoding="utf-8") as f:
    json.dump({
        "day"               : DAY_NUMBER,
        "date"              : TODAY_DATE,
        "channel"           : "MathConceptsMadeEasy",
        "topic"             : TODAY["topic"],
        "subject"           : TODAY["subject"],
        "track"             : TODAY["global_track"],
        "seo_title"         : TODAY["seo_title"],
        "playlist"          : TODAY["playlist"],
        "heading"           : HEADING,
        "teaser"            : INTRO_TEASER,
        "real_world_hook"   : TODAY.get("real_world_hook", ""),
        "concept_intuition" : TODAY.get("concept_intuition", ""),
        "common_mistake"    : TODAY.get("common_mistake", ""),
        "narrations"        : NARRATIONS,
        "outro"             : OUTRO_NARRATION,
        "banner_path"       : str(BANNER_PATH),
        "output_base"       : str(BASE_DIR),
    }, f, indent=2, ensure_ascii=False)

print(f"✅ cell1_config.py  → {config_path}")
print(f"✅ Log saved        → {log_path}")
print(f"\n{'═'*60}")
print(f"  Day {DAY_NUMBER} complete — {TODAY['topic']}")
print(f"  Output base : {BASE_DIR}")
print(f"  Run Cell 2 (script builder) next.")
print(f"{'═'*60}")

