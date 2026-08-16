"""Shared teaching constants: animation philosophy, pacing budget, voice
pitch profiles and the fixed 9-scene lesson structure.
Read by cells 1, 2, 3 and 4. Lesson CONTENT never lives here —
it comes from curriculum/*.json.
"""

# ══════════════════════════════════════════════════════════════
# PACING BUDGET — the contract Cell 4 renders against
#
# A finished lesson is judged on movement, not just on looks: if the
# voice is talking, the board must be changing. These numbers are the
# limits the Director enforces at render time, scene after scene, for
# every lesson. Change them here — never in a scene.
# ══════════════════════════════════════════════════════════════

PACING = {
    # Hard ceiling on a motionless screen. The Director fills anything
    # longer with an ambient beat (camera drift, highlight, progress).
    "max_static_seconds"   : 3.2,
    # Below this a beat is not worth playing — the gap is just held.
    "min_beat_seconds"     : 0.9,
    # How long a single ambient beat runs.
    "ambient_run_seconds"  : 1.6,
    # Slow documentary camera move: fraction of frame width to breathe
    # through, and how far the centre may wander from home.
    "camera_zoom_range"    : (0.955, 1.0),
    "camera_pan_limit"     : 0.34,
    "camera_run_seconds"   : 2.6,
    # Zoom onto the line being talked about, then return.
    "spotlight_zoom"       : 0.62,
    "spotlight_run_seconds": 0.9,
    # Stroke-by-stroke writing speed for math (seconds per part).
    "write_run_seconds"    : 0.7,
    # Digit-by-digit decimal reveal.
    "digit_run_seconds"    : 0.34,
}

ANIMATION_PHILOSOPHY = {
    "BOARD_WRITE": (
        "Mathematical content ONLY writes on screen like a whiteboard. "
        "Equations build one term at a time. Working appears line by line. "
        "Formulas write as Ryan reads each part. "
        "No word-for-word narration text overlay ever."
    ),
    "VISUAL_ONLY": (
        "Explanation scenes show a clean relevant visual while Ryan speaks. "
        "Visual supports understanding without copying narration as text. "
        "Can be: diagram, graph, real world image, illustration, colored shape. "
        "Screen is never empty during narration."
    ),
    "TITLE_SEQUENCE": (
        "Day number appears large and centered first. "
        "Topic items slide in one by one below it. "
        "Student knows what they will learn before Ryan speaks. "
        "Elegant, not cluttered."
    ),
    "EQUATION_BUILD": (
        "Each formula component appears as Ryan reads it aloud. "
        "New term highlights briefly as spoken. "
        "Previous terms stay visible but slightly dimmed. "
        "Full formula never appears all at once."
    ),
    "LIVE_SOLVE": (
        "The answer is worked out on screen rather than displayed. "
        "Decimals appear one digit at a time, powers expand into the "
        "multiplication they stand for, numbers break into factor trees. "
        "The student watches the mathematics being produced."
    ),
    "COMPARE": (
        "Two cases built side by side so the difference is visible, not "
        "described. Both panels animate together, each ending on its own "
        "verdict."
    ),
}

# ══════════════════════════════════════════════════════════════
# PITCH PROFILES — 9 profiles. Cell 3 applies as SSML prosody.
# ══════════════════════════════════════════════════════════════

PITCH_PROFILES = {
    "calm_intro"       : {"rate": "-5%",  "pitch": "+0Hz",  "volume": "+0%"},
    "excited_hook"     : {"rate": "+8%",  "pitch": "+3Hz",  "volume": "+8%"},
    "calm_explain"     : {"rate": "-8%",  "pitch": "+0Hz",  "volume": "+0%"},
    "slow_formal"      : {"rate": "-12%", "pitch": "-2Hz",  "volume": "+0%"},
    "slow_formula"     : {"rate": "-18%", "pitch": "-3Hz",  "volume": "+0%"},
    "emphasis"         : {"rate": "-5%",  "pitch": "+5Hz",  "volume": "+10%"},
    "friendly_mistake" : {"rate": "+0%",  "pitch": "+2Hz",  "volume": "+0%"},
    "encouraging"      : {"rate": "+3%",  "pitch": "+4Hz",  "volume": "+5%"},
    "warm_close"       : {"rate": "-5%",  "pitch": "+1Hz",  "volume": "-3%"},
}

# ══════════════════════════════════════════════════════════════
# SCENE ORDER + MAPS — READ BY CELLS 2, 3, 4
# ══════════════════════════════════════════════════════════════

SCENE_ORDER = [
    "opening", "hook", "concept", "definition",
    "formula", "worked_example", "mistakes", "practice", "summary"
]

SCENE_PITCH_MAP = {
    "opening"       : "calm_intro",
    "hook"          : "excited_hook",
    "concept"       : "calm_explain",
    "definition"    : "slow_formal",
    "formula"       : "slow_formula",
    "worked_example": "calm_explain",
    "mistakes"      : "friendly_mistake",
    "practice"      : "encouraging",
    "summary"       : "warm_close",
}

SCENE_ANIMATION_MAP = {
    "opening"       : "TITLE_SEQUENCE",
    "hook"          : "VISUAL_ONLY",
    "concept"       : "VISUAL_ONLY",
    "definition"    : "VISUAL_ONLY",
    "formula"       : "EQUATION_BUILD",
    "worked_example": "BOARD_WRITE",
    "mistakes"      : "BOARD_WRITE",
    "practice"      : "BOARD_WRITE",
    "summary"       : "VISUAL_ONLY",
}

