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

def clean_math_for_speech(text_or_list) -> str:
    """Translates LaTeX into spoken English so Rayan literally reads the math."""
    if not text_or_list: return ""
    if isinstance(text_or_list, list):
        text = " ... ".join(text_or_list)
    else:
        text = str(text_or_list)

    # Translate fractions: \frac{p}{q} -> p over q
    text = re.sub(r'\\frac{([^}]+)}{([^}]+)}', r'\1 over \2', text)
    # Extract plain text
    text = re.sub(r'\\text{([^}]+)}', r'\1', text)

    replacements = [
        (r'\Rightarrow', ' which gives '), (r'\iff', ' if and only if '),
        (r'\neq', ' is not equal to '), (r'\approx', ' is approximately '),
        (r'\perp', ' is perpendicular to '), (r'\parallel', ' is parallel to '),
        (r'\cong', ' is perfectly congruent to '), (r'\triangle', ' triangle '),
        (r'\angle', ' angle '), (r'\sqrt', ' the square root of '),
        (r'^2', ' squared '), (r'^3', ' cubed '), (r'\cdot', ' times '),
        (r'\times', ' times '), (r'\div', ' divided by '), (r'\dots', ' dot dot dot '),
        (r'\pi', ' pi '), (r'\theta', ' theta '), (r'\alpha', ' alpha '),
        (r'\beta', ' beta '), (r'\Delta', ' delta '), (r'\sin', ' sine '),
        (r'\cos', ' cosine '), (r'\tan', ' tangent '), ('=', ' equals '),
        ('+', ' plus '), ('-', ' minus '), ('$', ''), ('\\', ''), ('{', ''), ('}', '')
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return " ".join(text.split())

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
    visual_hints      = lesson.get('visual_hints', '')

    board             = lesson.get('board_examples', {})
    # Dynamically translate the math for this specific day!
    spoken_worked     = clean_math_for_speech(board.get('worked_example', []))
    spoken_practice   = clean_math_for_speech(board.get('practice', []))

    # ════════════════════════════════════════════════════════
    # SCENE 1: OPENING
    # ════════════════════════════════════════════════════════
    hook = (
        f"Welcome to Math Concepts Made Easy. "
        f"Today is Day {day}. "
        f"Our lesson is on {topic}. "
        f"{recap}"
        f"Look at the screen right now. "
        f"{real_world_hook} "
        f"By the end of this lesson, {goal}. "
        f"Let us begin."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 2 & 3: CONCEPT INTUITION & VISUALS
    # ════════════════════════════════════════════════════════
    concept = (
        f"Okay students. Before we write any formulas, let us look at the concept. "
        f"Watch the screen carefully as I explain. "
        f"{concept_intuition} "
        f"Do you see what is happening here? Every part of this diagram has a purpose."
    )

    concrete = (
        f"Let us watch this happen step by step on the screen. "
        f"{visual_hints} "
        f"See how the visual perfectly reveals the structure of the math?"
    )

    # ════════════════════════════════════════════════════════
    # SCENE 4: FORMAL DEFINITION
    # ════════════════════════════════════════════════════════
    pictorial = (
        f"Okay students. Now let us learn the formal definition. "
        f"Watch the board. "
        f"A {topic} is defined as: {subtopic}. "
        f"Every word in this definition matters. "
        f"You already know {prereq}. This definition builds directly on those ideas."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 5: FORMULA BUILD
    # ════════════════════════════════════════════════════════
    abstract = (
        f"Now watch the board carefully. The key formula for {topic} is about to appear. "
        f"The formula is: {formula}. "
        f"Read along with me as each symbol appears on the board. "
        f"Do not just memorise the symbols. Understand what each one represents."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 6: WORKED EXAMPLE (Dynamically reads the math)
    # ════════════════════════════════════════════════════════
    why_rule = (
        f"Now students, watch the board. We are going to work through a complete example. "
        f"I will explain every single step as it appears. Read it with me: "
        f"{spoken_worked}. "
        f"Notice how each line logically follows the one before it. Always verify your answer."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 7: COMMON MISTAKES
    # ════════════════════════════════════════════════════════
    mistakes = (
        f"Before we practice, let us talk about mistakes. "
        f"Watch the board carefully. I am going to show you where students go wrong. "
        f"Here is the most common mistake: {common_mistake}. "
        f"Look at the difference between the wrong version and the correct version. "
        f"This mistake costs students marks every year. Do not make it."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 8: PRACTICE (Dynamically reads the math)
    # ════════════════════════════════════════════════════════
    practice = (
        f"Now it is your turn. Watch the top of the board. A question is appearing right now. "
        f"Let us solve it together step by step. Follow along with me: "
        f"{spoken_practice}. "
        f"There it is. Check your working against mine on the board."
    )

    # ════════════════════════════════════════════════════════
    # SCENE 9: SUMMARY
    # ════════════════════════════════════════════════════════
    summary = (
        f"Let us bring today together. Watch the summary card on screen. "
        f"First: {subtopic}. "
        f"Second: The formula is {formula}. "
        f"Today was Day {day}. Topic: {topic}. {goal}. "
        f"{teaser}. "
        f"New lessons every day on Math Concepts Made Easy. See you tomorrow."
    )
    def split_beats(text):
        return [
            s.strip() + "."
            for s in text.split(".")
            if s.strip()
        ]

    return {
        "opening": {
            "full": hook,
            "beats": split_beats(hook),
        },

        "hook": {
            "full": concept,
            "beats": split_beats(concept),
        },

        "concept": {
            "full": concrete,
            "beats": split_beats(concrete),
        },

        "definition": {
            "full": pictorial,
            "beats": split_beats(pictorial),
        },

        "formula": {
            "full": abstract,
            "beats": split_beats(abstract),
        },

        "worked_example": {
            "full": why_rule,
            "beats": split_beats(why_rule),
        },

        "mistakes": {
            "full": mistakes,
            "beats": split_beats(mistakes),
        },

        "practice": {
            "full": practice,
            "beats": split_beats(practice),
        },

        "summary": {
            "full": summary,
            "beats": split_beats(summary),
        },
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

