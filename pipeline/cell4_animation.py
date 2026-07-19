# ==========================================
# CELL 4: MANIM ANIMATION ENGINE
# CHANNEL: MathConceptsMadeEasy
# Reads: lesson_001_script_timed.json
# Reads: Math-9/audio/lesson_001/scene_XX.mp3
# Reads: Math-9/audio/lesson_001/scene_XX.words.json
# Writes: Math-9/renders/lesson_001/scene_XX.mp4
# Logo: always top-left corner, no margin
# ==========================================

import sys, json, subprocess, shutil, os
from pathlib import Path


# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")
# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

lesson_data  = cell1_config.CURRICULUM[0]
lesson_id    = lesson_data['id']

SCRIPTS_DIR  = cell1_config.SCRIPTS_DIR
AUDIO_DIR    = cell1_config.AUDIO_DIR
RENDERS_DIR  = cell1_config.RENDERS_DIR
BANNER_PATH  = cell1_config.BANNER_PATH
LOGO_PATH    = getattr(cell1_config, "LOGO_PATH", cell1_config.ASSETS_DIR / "logo.png")

TIMED_SCRIPT = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
LESSON_AUDIO = AUDIO_DIR   / f"lesson_{lesson_id:03d}"
LESSON_RENDER= RENDERS_DIR / f"lesson_{lesson_id:03d}"
LESSON_RENDER.mkdir(parents=True, exist_ok=True)

TEMP_DIR     = Path("/tmp/manim_math")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── Load timed script ─────────────────────────────────────────
if not TIMED_SCRIPT.exists():
    raise SystemExit(
        f"🛑 Timed script not found at {TIMED_SCRIPT}. Run Cell 3 first."
    )

with open(TIMED_SCRIPT, "r", encoding="utf-8") as f:
    SCRIPT = json.load(f)

print(f"✅ Timed script loaded → {TIMED_SCRIPT}")
print(f"   Lesson  : Day {lesson_id} — {SCRIPT['title']}")
print(f"   Scenes  : {len(SCRIPT['scenes'])}")
print(f"   Total   : {SCRIPT['total_duration_seconds']:.1f}s\n")

# ══════════════════════════════════════════════════════════════
# THEME CONSTANTS  (pulled from config)
# ══════════════════════════════════════════════════════════════

T = SCRIPT["theme"]

C_BG       = T["bg"]        # #0D1B2A  dark navy
C_PRIMARY  = T["primary"]   # #F0F4F8  near-white
C_SECOND   = T["secondary"] # #8899AA  muted blue-grey
C_BLUE     = T["blue"]      # #3B9EFF  bright blue
C_GREEN    = T["green"]     # #2ECC71  bright green
C_YELLOW   = T["yellow"]    # #F6C90E  gold/yellow
C_RED      = T["red"]       # #E74C3C  red
C_CARD     = T["card_bg"]   # #1A2B3C  card background

# Manim colour helper
def mc(hex_color: str):
    """Convert hex string to Manim ManimColor."""
    from manim import ManimColor
    return ManimColor(hex_color)

# ══════════════════════════════════════════════════════════════
# WORD BOUNDARY LOADER
# Returns list of {word, norm, start, end} dicts.
# Used by scenes that sync text highlights to audio.
# ══════════════════════════════════════════════════════════════

def load_word_boundaries(scene_id: int) -> list:
    path = LESSON_AUDIO / f"scene_{scene_id:02d}.words.json"
    if path.exists():
        try:
            with open(str(path), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


# ══════════════════════════════════════════════════════════════
# BASE SCENE CLASS
# All 9 scene types inherit from this.
# Handles: background colour, logo, audio attachment,
#          scene duration from timed script.
# ══════════════════════════════════════════════════════════════
MANIM_SCENE_CODE = r'''
from manim import *
import json
from pathlib import Path

# ── Safe Data Loading (Fixes the SyntaxError) ─────────────────
SCRIPT_PATH   = Path(r"__SCRIPT_PATH__")
LESSON_AUDIO  = Path(r"__AUDIO_DIR__")
LOGO_PATH     = Path(r"__LOGO_PATH__")
BANNER_PATH   = Path(r"__BANNER_PATH__")

# Read script data directly from disk to avoid string injection crashes
with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    SCRIPT_DATA = json.load(f)

LESSON_ID = SCRIPT_DATA["lesson_id"]

C_BG      = "{C_BG}"
C_PRIMARY = "{C_PRIMARY}"
C_SECOND  = "{C_SECOND}"
C_BLUE    = "{C_BLUE}"
C_GREEN   = "{C_GREEN}"
C_YELLOW  = "{C_YELLOW}"
C_RED     = "{C_RED}"
C_CARD    = "{C_CARD}"

# ── Premium design-system constants (hardcoded, not per-theme) ──
C_GOLD    = "#FFB300"   # warm amber gold — key equations, curves
C_TEAL    = "#1A7070"   # teal — graph area fill, coordinate shading
C_NEON    = "#1C72CC"   # electric blue — neon wireframe geometry
C_CHALK   = "#E0EAD8"   # warm chalk white — chalkboard text
C_COPPER  = "#B87333"   # copper — alternate title accent

# Per-scene background colours — richer darks match reference palette
C_BG_SPACE = "#06111E"  # deep navy/space for opening, summary, hook
C_BG_TEAL  = "#091E1E"  # dark teal chalkboard for concept, practice
C_BG_BLACK = "#070707"  # near-black for formula, graph
C_BG_DARK  = "#0C0C0C"  # charcoal for worked_example, mistakes

config.background_color = C_BG

CHANNEL   = "MathConceptsMadeEasy"

# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════

def mc(h): return ManimColor(h)

def get_scene_data(step: str) -> dict:
    for s in SCRIPT_DATA["scenes"]:
        if s["step"] == step:
            return s
    return {}

def load_words(scene_id: int) -> list:
    p = LESSON_AUDIO / f"scene_{scene_id:02d}.words.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def add_logo(scene_obj):
    import numpy as np
    if LOGO_PATH.exists():
        try:
            logo = ImageMobject(str(LOGO_PATH))
            logo.set_height(0.55)
            logo.move_to(np.array([-7.1, 3.8, 0]))
            scene_obj.add(logo)
            return logo
        except Exception:
            pass
    logo = Text(
        CHANNEL, font_size=13,
        color=mc(C_YELLOW), font="Arial"
    ).to_corner(UL, buff=0.0)
    scene_obj.add(logo)
    return logo

def add_banner(scene_obj):
    if BANNER_PATH.exists():
        try:
            banner = ImageMobject(str(BANNER_PATH))
            banner.set_width(config.frame_width)
            banner.to_edge(DOWN, buff=0)
            scene_obj.add(banner)
            return banner
        except Exception:
            pass
    return None

def set_background(scene_obj, bg_hex=None):
    # Belt-and-braces: set on camera AND draw a full-frame dark rect BEHIND
    # everything so no LaTeX SVG bounding-box ever bleeds pale artefacts.
    color = bg_hex or C_BG
    scene_obj.camera.background_color = mc(color)
    bg_rect = Rectangle(
        width=config.frame_width + 2,
        height=config.frame_height + 2,
        fill_color=mc(color), fill_opacity=1.0,
        stroke_width=0,
    )
    bg_rect.set_z_index(-100)
    scene_obj.add(bg_rect)

SCENE_BG_MAP = {
    "opening"       : C_BG_SPACE,
    "hook"          : C_BG_SPACE,
    "concept"       : C_BG_TEAL,
    "definition"    : C_BG_TEAL,
    "formula"       : C_BG_BLACK,
    "worked_example": C_BG_DARK,
    "mistakes"      : C_BG_DARK,
    "practice"      : C_BG_TEAL,
    "summary"       : C_BG_SPACE,
}

def set_scene_bg(scene_obj, step: str):
    """Apply a rich, scene-specific dark background matching the visual brief."""
    set_background(scene_obj, SCENE_BG_MAP.get(step, C_BG))

def attach_audio(scene_obj, scene_id: int):
    mp3 = LESSON_AUDIO / f"scene_{scene_id:02d}.mp3"
    if mp3.exists():
        scene_obj.add_sound(str(mp3))

def wrap_text(text: str, max_chars: int = 52) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(text, max_chars))

def board_write_steps(scene_obj, steps: list, start_y: float = 2.0, color: str = None):
    """
    Writes LaTeX steps one by one down the board.
    Each line appears as Ryan reads it.
    Used by formula, worked_example, mistakes, practice scenes.
    """
    color = color or C_PRIMARY
    y = start_y
    for step_tex in steps:
        try:
            mob = MathTex(step_tex, font_size=44, color=mc(color))
        except Exception:
            mob = Text(step_tex, font_size=28, color=mc(color), font="Arial")
        mob.to_edge(LEFT, buff=0.9)
        mob.shift(UP * y)
        scene_obj.play(Write(mob), run_time=0.7)
        scene_obj.wait(0.3)
        y -= 0.95

def build_step_column(steps, font_size=44, buff=0.42, first_color=None,
                      other_color=None, per_line_color=None,
                      top_y=2.55, left_buff=0.9, max_height=5.9, max_width=12.4):
    """
    Build a VGroup of math/text steps arranged straight down with GUARANTEED
    no overlap. VGroup.arrange measures each rendered mob's real height, so
    tall fractions (\\tfrac, \\frac) never collide.

    Returns the list of individual mobs so scenes can .play(Write(m)) one
    at a time in sync with narration.
    """
    first_color = first_color or C_YELLOW
    other_color = other_color or C_PRIMARY
    mobs = []
    for i, step_tex in enumerate(steps):
        if not step_tex or not step_tex.strip():
            continue
        if per_line_color:
            col = per_line_color(i, step_tex)
        else:
            col = first_color if i == 0 else other_color
        try:
            m = MathTex(step_tex, font_size=font_size, color=mc(col))
        except Exception:
            m = Text(step_tex, font_size=max(20, font_size - 14),
                     color=mc(col), font="Arial")
        mobs.append(m)

    if not mobs:
        return mobs

    grp = VGroup(*mobs).arrange(DOWN, aligned_edge=LEFT, buff=buff)

    # Auto-shrink so the whole column fits inside the safe area
    scale_h = min(1.0, max_height / max(grp.height, 0.01))
    scale_w = min(1.0, max_width  / max(grp.width,  0.01))
    scale   = min(scale_h, scale_w)
    if scale < 1.0:
        grp.scale(scale)

    # Anchor: left-aligned, top of column at top_y
    grp.to_edge(LEFT, buff=left_buff)
    grp.shift(UP * (top_y - grp.get_top()[1]))
    return mobs

def sync_to_audio(scene_obj, scene_id: int):
    """Extend scene duration to match audio. Call as last line of every construct()."""
    target = 20.0
    for s in SCRIPT_DATA["scenes"]:
        if s.get("scene_id") == scene_id:
            target = float(s.get("duration_seconds", 20.0))
            break
    try:
        elapsed = scene_obj.renderer.time
    except Exception:
        elapsed = 0.0
    remaining = target - elapsed - 0.1
    if remaining > 0.05:
        scene_obj.wait(remaining)


# ═════════════════════════════════════════════════════════════════
# BROADCAST DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────────
# One shared design language across all 9 scenes.  Each scene gets
# a unique accent colour but the same chrome so the channel feels
# like a real broadcast product, not a slideshow.
# ═════════════════════════════════════════════════════════════════

ACCENT_MAP = {
    "opening"       : "{C_BLUE}",
    "hook"          : "{C_YELLOW}",
    "concept"       : "{C_BLUE}",
    "definition"    : "{C_YELLOW}",
    "formula"       : "{C_YELLOW}",
    "worked_example": "{C_GREEN}",
    "mistakes"      : "{C_RED}",
    "practice"      : "{C_GREEN}",
    "summary"       : "{C_YELLOW}",
}

SCENE_INDEX_MAP = {
    "opening"       : 1,
    "hook"          : 2,
    "concept"       : 3,
    "definition"    : 4,
    "formula"       : 5,
    "worked_example": 6,
    "mistakes"      : 7,
    "practice"      : 8,
    "summary"       : 9,
}

STEP_LABEL_MAP = {
    "opening"       : "01  ·  OPENING",
    "hook"          : "02  ·  REAL-WORLD HOOK",
    "concept"       : "03  ·  THE CONCEPT",
    "definition"    : "04  ·  DEFINITION",
    "formula"       : "05  ·  THE FORMULA",
    "worked_example": "06  ·  WORKED EXAMPLE",
    "mistakes"      : "07  ·  COMMON MISTAKES",
    "practice"      : "08  ·  YOUR TURN",
    "summary"       : "09  ·  SUMMARY",
}


def add_broadcast_chrome(scene_obj, step: str):
    """
    Premium broadcast chrome added to every scene.

    Elements:
      • Thin accent bar across the top (scene-specific colour)
      • Corner logo top-left
      • Scene tag ("06 · WORKED EXAMPLE") top-right in accent colour
      • Nine progress dots along the bottom-right — completed dots
        glow in the accent colour, upcoming dots stay muted grey
      • Faint bottom hairline in accent colour for consistency

    Returns the chrome VGroup so scenes can fade it in/out if needed.
    """
    accent  = ACCENT_MAP.get(step, "{C_YELLOW}")
    idx     = SCENE_INDEX_MAP.get(step, 1)
    tag_txt = STEP_LABEL_MAP.get(step, step.upper())

    top_bar = Rectangle(
        width=config.frame_width, height=0.09,
        fill_color=mc(accent), fill_opacity=1.0, stroke_width=0,
    ).to_edge(UP, buff=0)

    bottom_hair = Rectangle(
        width=config.frame_width, height=0.025,
        fill_color=mc(accent), fill_opacity=0.55, stroke_width=0,
    ).to_edge(DOWN, buff=0)

    # Channel wordmark top-left, sitting neatly below the accent bar
    import numpy as np
    if LOGO_PATH.exists():
        try:
            wordmark = ImageMobject(str(LOGO_PATH))
            wordmark.set_height(0.45)
            wordmark.move_to(np.array([-7.15, 3.62, 0]))
        except Exception:
            wordmark = Text(
                CHANNEL, font_size=15,
                color=mc(accent), font="Arial", weight=BOLD,
            ).move_to(np.array([-6.35, 3.62, 0]))
    else:
        wordmark = Text(
            CHANNEL, font_size=15,
            color=mc(accent), font="Arial", weight=BOLD,
        ).move_to(np.array([-6.35, 3.62, 0]))

    # Scene tag in top-right — sits just below the accent bar
    tag = Text(
        tag_txt, font_size=16, color=mc(accent),
        font="Arial", weight=BOLD,
    ).to_corner(UR, buff=0.30).shift(DOWN * 0.18)

    # Nine progress dots bottom-right
    dots = VGroup(*[
        Dot(
            radius=0.075,
            color=mc(accent if i <= idx else "{C_SECOND}"),
            fill_opacity=1.0 if i <= idx else 0.35,
        )
        for i in range(1, 10)
    ]).arrange(RIGHT, buff=0.18)
    dots.to_corner(DR, buff=0.35).shift(UP * 0.05)

    # Group supports mixed VMobject + ImageMobject
    chrome = Group(top_bar, bottom_hair, tag, dots, wordmark)
    for m in [top_bar, bottom_hair, tag, dots]:
        m.set_z_index(50)  # above content
    scene_obj.add(chrome)
    return chrome


# ═════════════════════════════════════════════════════════════════
# WORD-TIMELINE SYNCHRONISATION
# ─────────────────────────────────────────────────────────────────
# Edge-TTS emits a per-word timing file at scene_XX.words.json.
# These helpers let scenes fire visual events exactly when Ryan
# begins speaking a specific word, rather than on manual `wait()`.
# ═════════════════════════════════════════════════════════════════

def _norm_key(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def word_timestamp(scene_id: int, keyword: str, occurrence: int = 1):
    """
    Return the seconds-into-scene when Ryan first (or Nth) says
    a keyword.  Returns None if not found.
    """
    words = load_words(scene_id)
    if not words:
        return None
    target = _norm_key(keyword)
    hits = 0
    for w in words:
        raw = w.get("norm") or w.get("word") or ""
        if _norm_key(raw) == target or target in _norm_key(raw):
            hits += 1
            if hits >= occurrence:
                start = w.get("start", w.get("offset", 0))
                # Edge-TTS emits ticks (100-ns units); many pipelines
                # store as ms or s — normalise conservatively.
                if start > 10_000_000:
                    return start / 10_000_000.0   # ticks → s
                if start > 1000:
                    return start / 1000.0          # ms → s
                return float(start)                # already s
    return None


def wait_until(scene_obj, target_seconds):
    """Wait until scene renderer elapsed time reaches target_seconds."""
    if target_seconds is None:
        return
    try:
        elapsed = scene_obj.renderer.time
    except Exception:
        elapsed = 0.0
    remaining = target_seconds - elapsed
    if remaining > 0.05:
        scene_obj.wait(remaining)


def play_at_word(scene_obj, scene_id, keyword, *anims, occurrence=1, run_time=0.6):
    """
    Wait until Ryan says `keyword`, then play the animations.  Falls
    back to just playing them immediately if timing data is missing,
    so scenes never stall waiting for a word that was never spoken.
    """
    t = word_timestamp(scene_id, keyword, occurrence=occurrence)
    if t is not None:
        wait_until(scene_obj, t)
    if anims:
        scene_obj.play(*anims, run_time=run_time)


# ═════════════════════════════════════════════════════════════════
# MOTION-GRAPHICS PRIMITIVES
# ─────────────────────────────────────────────────────────────────
# Reusable atoms every scene can compose into rich, broadcast-style
# visuals: glow highlights, callout arrows, count-up numbers,
# equation part-builds, panel cards, comparison rows.
# ═════════════════════════════════════════════════════════════════

def glow_highlight(scene_obj, mob, color=None, run_time=0.55, hold=0.35):
    """
    Draw eye attention: pulsing accent-coloured rectangle appears
    around the mob, colour flips to accent, glow fades after `hold`.
    """
    col = color or "{C_YELLOW}"
    glow = SurroundingRectangle(
        mob, color=mc(col), stroke_width=4.0,
        buff=0.18, corner_radius=0.12,
    )
    original_color = mob.get_color()
    scene_obj.play(
        Create(glow),
        mob.animate.set_color(mc(col)),
        run_time=run_time,
    )
    scene_obj.wait(hold)
    scene_obj.play(FadeOut(glow), run_time=0.35)


def callout_arrow(scene_obj, target_mob, text: str,
                  direction=None, offset=1.6, color=None,
                  font_size=22, run_time=0.55):
    """
    Animated arrow with a text label pointing at a target mob.
    Direction defaults to RIGHT (side of the target the label sits on).
    """
    import numpy as np
    col = color or "{C_YELLOW}"
    dir_vec = direction if direction is not None else np.array([1.0, 0.0, 0.0])
    label_pos = target_mob.get_center() + dir_vec * offset
    label = Text(text, font_size=font_size, color=mc(col), font="Arial")
    label.move_to(label_pos)
    arrow = Arrow(
        label.get_center() - dir_vec * (label.width * 0.55 + 0.05),
        target_mob.get_edge_center(dir_vec),
        color=mc(col), stroke_width=3.5, buff=0.1,
    )
    scene_obj.play(GrowArrow(arrow), FadeIn(label), run_time=run_time)
    return VGroup(arrow, label)


def build_equation_parts(scene_obj, parts, colors=None, position=None,
                         font_size=64, per_part_time=0.55, direction=None):
    """
    Reveal an equation one LaTeX chunk at a time so students see
    every piece being built. `parts` is a list of LaTeX strings.
    """
    import numpy as np
    colors = colors or ["{C_PRIMARY}"] * len(parts)
    if len(colors) < len(parts):
        colors = colors + ["{C_PRIMARY}"] * (len(parts) - len(colors))
    dir_vec = direction if direction is not None else np.array([1.0, 0.0, 0.0])
    mobs = []
    for tex, col in zip(parts, colors):
        try:
            m = MathTex(tex, font_size=font_size, color=mc(col))
        except Exception:
            m = Text(tex, font_size=max(24, font_size - 20),
                     color=mc(col), font="Arial")
        mobs.append(m)
    grp = VGroup(*mobs).arrange(dir_vec, buff=0.18)
    if position is not None:
        grp.move_to(position)
    for m in mobs:
        scene_obj.play(Write(m), run_time=per_part_time)
    return grp, mobs


def count_up_number(scene_obj, target: float, position, decimals=0,
                    font_size=72, color=None, duration=1.0,
                    prefix="", suffix=""):
    """Animate a number counting up from 0 → target."""
    col = color or "{C_YELLOW}"
    tracker = ValueTracker(0.0)
    num = DecimalNumber(
        0.0, num_decimal_places=decimals,
        color=mc(col), font_size=font_size,
    )
    num.add_updater(lambda m: m.set_value(tracker.get_value()))

    parts = []
    if prefix:
        parts.append(Text(prefix, font_size=font_size, color=mc(col), font="Arial"))
    parts.append(num)
    if suffix:
        parts.append(Text(suffix, font_size=font_size, color=mc(col), font="Arial"))

    if len(parts) > 1:
        grp = VGroup(*parts).arrange(RIGHT, buff=0.12).move_to(position)
    else:
        num.move_to(position)
        grp = num

    scene_obj.add(grp)
    scene_obj.play(tracker.animate.set_value(target), run_time=duration)
    num.clear_updaters()
    return grp


def panel_card(width=6.0, height=3.5, fill=None, stroke=None,
               stroke_width=2.0, corner_radius=0.28, opacity=0.9):
    """A rounded card matte for scenes that need side panels."""
    fill   = fill   or "{C_CARD}"
    stroke = stroke or "{C_SECOND}"
    return RoundedRectangle(
        width=width, height=height,
        fill_color=mc(fill), fill_opacity=opacity,
        stroke_color=mc(stroke), stroke_width=stroke_width,
        corner_radius=corner_radius,
    )


def comparison_split(scene_obj, left_title, right_title,
                     left_color=None, right_color=None):
    """
    Two-panel split — left vs right comparison card.  Returns the two
    empty panel groups so the caller can fill them in with content.
    Used by Mistakes scene (wrong vs correct).
    """
    left_color  = left_color  or "{C_RED}"
    right_color = right_color or "{C_GREEN}"

    left_panel  = panel_card(width=6.4, height=5.2,
                             stroke=left_color, stroke_width=2.5)
    right_panel = panel_card(width=6.4, height=5.2,
                             stroke=right_color, stroke_width=2.5)
    left_panel.shift(LEFT * 3.35 + DOWN * 0.3)
    right_panel.shift(RIGHT * 3.35 + DOWN * 0.3)

    left_hdr  = Text(left_title, font_size=26,
                     color=mc(left_color), font="Arial", weight=BOLD)
    right_hdr = Text(right_title, font_size=26,
                     color=mc(right_color), font="Arial", weight=BOLD)
    left_hdr .move_to(left_panel .get_top() + DOWN * 0.35)
    right_hdr.move_to(right_panel.get_top() + DOWN * 0.35)

    scene_obj.play(
        FadeIn(left_panel), FadeIn(right_panel),
        run_time=0.55,
    )
    scene_obj.play(
        Write(left_hdr), Write(right_hdr),
        run_time=0.55,
    )
    return (left_panel, left_hdr), (right_panel, right_hdr)


def scene_title_reveal(scene_obj, title_text: str, accent_color: str,
                       subtitle: str = "", run_time=0.9):
    """
    Consistent scene-opening title animation:
      • Big title slides down from the top
      • Accent underline sweeps left-to-right
      • Optional subtitle fades in below
    Returns the title group so scenes can fade it out later.
    """
    title = Text(
        title_text, font_size=44, color=mc(accent_color),
        font="Arial", weight=BOLD,
    ).to_edge(UP, buff=0.55)

    underline = Line(
        title.get_left() + DOWN * 0.35,
        title.get_right() + DOWN * 0.35,
        color=mc(accent_color), stroke_width=3.0,
    ).set_length(0.01).move_to(
        title.get_bottom() + DOWN * 0.15 + LEFT * (title.width * 0.4)
    )

    scene_obj.play(
        FadeIn(title, shift=DOWN * 0.2),
        run_time=run_time * 0.6,
    )
    scene_obj.play(
        Create(Line(
            title.get_bottom() + DOWN * 0.15 + LEFT * (title.width * 0.5),
            title.get_bottom() + DOWN * 0.15 + RIGHT * (title.width * 0.5),
            color=mc(accent_color), stroke_width=3.0,
        )),
        run_time=run_time * 0.4,
    )

    sub_mob = None
    if subtitle:
        sub_mob = Text(
            subtitle, font_size=22, color=mc("{C_SECOND}"),
            font="Arial",
        ).next_to(title, DOWN, buff=0.5)
        scene_obj.play(FadeIn(sub_mob, shift=UP * 0.1), run_time=0.4)

    return VGroup(*[m for m in [title, sub_mob] if m is not None])

# ═════════════════════════════════════════════════════════════════
# VISUAL ENVIRONMENT PRIMITIVES
# ─────────────────────────────────────────────────────────────────
# Three scene-level atmosphere helpers that match the premium
# reference image palette (deep space, chalkboard, near-black).
# Call these right after set_scene_bg() in every scene.
# ═════════════════════════════════════════════════════════════════

def add_star_field(scene_obj, n_stars=90, max_opacity=0.55):
    """
    Tiny white dots scattered across the frame — creates the deep-space
    depth seen in the dark-navy reference slides. Deterministic seed so
    every render looks identical.
    """
    import numpy as np, random as _r
    rng = _r.Random(42)
    hw  = config.frame_width  / 2 - 0.1
    hh  = config.frame_height / 2 - 0.1
    for _ in range(n_stars):
        x  = rng.uniform(-hw, hw)
        y  = rng.uniform(-hh, hh)
        r  = rng.uniform(0.012, 0.046)
        op = rng.uniform(0.15, max_opacity)
        s  = Dot(point=np.array([x, y, 0]), radius=r,
                 color=WHITE, fill_opacity=op)
        s.set_z_index(-50)
        scene_obj.add(s)


def add_floating_geometry(scene_obj, style="tech"):
    """
    Corner wireframe 3D-looking shapes — the premium signature seen in
    the reference images (circle+inscribed triangle, diamond, frustum,
    rectangle). Three presets:
      'tech'   → neon blue, semi-opaque  (opening / summary / hook)
      'chalk'  → warm off-white, softer  (concept / definition / practice)
      'subtle' → very faint grey         (formula / worked_example / mistakes)
    """
    import numpy as np
    col_map = {"tech": C_NEON, "chalk": "#A8BEA0", "subtle": "#283848"}
    op_map  = {"tech": 0.55,   "chalk": 0.42,       "subtle": 0.22}
    sw_map  = {"tech": 1.8,    "chalk": 1.6,         "subtle": 1.1}
    col = col_map.get(style, C_NEON)
    op  = op_map .get(style, 0.55)
    sw  = sw_map .get(style, 1.8)

    shapes = []

    # ── Top-right: large circle with inscribed triangle + inner circle ──
    TRCX, TRCY = 5.7, 3.0
    big_c = Circle(radius=1.55, color=mc(col), stroke_width=sw)
    big_c.move_to(np.array([TRCX, TRCY, 0])).set_stroke(opacity=op)
    inn_c = Circle(radius=0.88, color=mc(col), stroke_width=sw * 0.75)
    inn_c.move_to(np.array([TRCX, TRCY, 0])).set_stroke(opacity=op * 0.65)
    # Inscribed triangle
    tri_pts = [big_c.point_at_angle(a)
               for a in [np.pi / 2, -np.pi / 6, -5 * np.pi / 6]]
    tri = Polygon(*tri_pts, color=mc(col), stroke_width=sw * 0.75)
    tri.set_fill(opacity=0).set_stroke(opacity=op * 0.60)
    # Altitude from apex to base midpoint
    alt = Line(tri_pts[0], (tri_pts[1] + tri_pts[2]) / 2,
               color=mc(col), stroke_width=sw * 0.55)
    alt.set_stroke(opacity=op * 0.45)
    shapes += [big_c, inn_c, tri, alt]

    # ── Bottom-right: diamond / rhombus ──
    cx, cy = 5.9, -2.8
    diamond = Polygon(
        np.array([cx,        cy + 0.85, 0]),
        np.array([cx + 0.85, cy,        0]),
        np.array([cx,        cy - 0.85, 0]),
        np.array([cx - 0.85, cy,        0]),
        color=mc(col), stroke_width=sw
    ).set_fill(opacity=0).set_stroke(opacity=op * 0.60)
    shapes.append(diamond)

    # ── Bottom-left: truncated cone (frustum) ──
    fx, fy = -5.7, -2.4
    tw, bw, h = 0.95, 1.45, 1.55
    frustum = VMobject(color=mc(col), stroke_width=sw)
    frustum.set_points_as_corners([
        np.array([fx - tw, fy,     0]),
        np.array([fx + tw, fy,     0]),
        np.array([fx + bw, fy - h, 0]),
        np.array([fx - bw, fy - h, 0]),
        np.array([fx - tw, fy,     0]),
    ])
    frustum.set_fill(opacity=0).set_stroke(opacity=op * 0.52)
    ell_t = Ellipse(width=tw * 2 + 0.08, height=0.36,
                    color=mc(col), stroke_width=sw * 0.7)
    ell_t.move_to(np.array([fx, fy,     0])).set_stroke(opacity=op * 0.46)
    ell_b = Ellipse(width=bw * 2,         height=0.46,
                    color=mc(col), stroke_width=sw * 0.7)
    ell_b.move_to(np.array([fx, fy - h, 0])).set_stroke(opacity=op * 0.42)
    shapes += [frustum, ell_t, ell_b]

    # ── Top-left: rectangle tablet outline ──
    rect = Rectangle(width=1.85, height=1.25,
                     color=mc(col), stroke_width=sw * 0.85)
    rect.move_to(np.array([-6.05, 2.85, 0]))
    rect.set_fill(opacity=0).set_stroke(opacity=op * 0.48)
    shapes.append(rect)

    # Tiny crosshair / plus marks — atmospheric scatter
    for pos in [
        np.array([ 1.6,  3.6, 0]),
        np.array([ 4.0, -0.6, 0]),
        np.array([-2.2,  1.1, 0]),
    ]:
        arm = 0.14
        for ln in [
            Line(pos + LEFT * arm, pos + RIGHT * arm,
                 color=mc(col), stroke_width=sw * 0.6),
            Line(pos + UP   * arm, pos + DOWN  * arm,
                 color=mc(col), stroke_width=sw * 0.6),
        ]:
            ln.set_stroke(opacity=op * 0.38)
            shapes.append(ln)

    for s in shapes:
        s.set_z_index(-30)
        scene_obj.add(s)
    return shapes


def add_math_scatter(scene_obj, opacity=0.07, n=24):
    """
    Faint math symbols scattered across the background as a texture layer —
    inspired by the 'math symbol pattern' reference slide. Gives educational
    depth without cluttering content.
    """
    import numpy as np, random as _r
    symbols = [
        "\\div", "\\times", "+", "=", "-", "\\sqrt{x}",
        "\\pi", "\\infty", "f(x)", "\\Delta", "\\Sigma", "\\alpha",
    ]
    rng = _r.Random(13)
    hw  = config.frame_width  / 2 - 0.6
    hh  = config.frame_height / 2 - 0.4
    for _ in range(n):
        sym = rng.choice(symbols)
        x   = rng.uniform(-hw, hw)
        y   = rng.uniform(-hh, hh)
        sz  = rng.uniform(16, 30)
        try:
            m = MathTex(sym, font_size=sz, color=mc(C_PRIMARY))
        except Exception:
            m = Text(sym, font_size=int(sz), color=mc(C_PRIMARY), font="Arial")
        m.move_to(np.array([x, y, 0]))
        m.set_opacity(opacity)
        m.set_z_index(-20)
        scene_obj.add(m)


# ════════════════════════════════════════════════════════════
# SCENE 01 — WHAT IS A RATIONAL NUMBER?
# Layout  : Title top | Fraction large center | Content below
# Style   : One idea per beat, narration matches board exactly
# Beats   : 7 phases — bridge → title → fraction → where →
#           plain English → examples → memory sentence
# Audio   : Placeholder timing — sync to MP3 later
# ════════════════════════════════════════════════════════════

class Scene01_Opening(Scene):
    def construct(self):
        sd = get_scene_data("opening")
        set_scene_bg(self, "opening")
        add_star_field(self)
        add_floating_geometry(self, "tech")
        attach_audio(self, sd.get("scene_id", 1))
        add_broadcast_chrome(self, "opening")

        # ── Timing constants ───────────────────────────────────
        # Change only these 3 values when narration MP3 is ready
        WAIT_S = 1.6   # short  — narration names the element
        WAIT_M = 2.8   # medium — narration reads the full line
        WAIT_L = 3.8   # long   — key concept, let it land fully

        # ══════════════════════════════════════════════════════
        # BEAT 1 — PRIOR KNOWLEDGE BRIDGE
        # Show familiar fractions before the word "rational"
        # Student relaxes seeing something they already know
        # ══════════════════════════════════════════════════════

        bridge_txt = Text(
            "You already know this...",
            font_size=36, color=mc(C_SECOND),
            font="Arial"
        ).shift(UP * 2.2)

        self.play(FadeIn(bridge_txt, shift=UP * 0.1), run_time=0.8)
        self.wait(WAIT_S)

        # Three familiar fractions — one at a time, not all at once
        f1 = MathTex(r"\frac{1}{2}", font_size=88, color=mc(C_BLUE))
        f2 = MathTex(r"\frac{3}{4}", font_size=88, color=mc(C_BLUE))
        f3 = MathTex(r"\frac{7}{1}", font_size=88, color=mc(C_BLUE))
        fracs_row = VGroup(f1, f2, f3).arrange(RIGHT, buff=1.8)
        fracs_row.next_to(bridge_txt, DOWN, buff=0.7)

        self.play(Write(f1), run_time=0.8)
        self.wait(0.4)
        self.play(Write(f2), run_time=0.8)
        self.wait(0.4)
        self.play(Write(f3), run_time=0.8)
        self.wait(WAIT_M)

        bridge_note = Text(
            "These are fractions.  You have seen them before.",
            font_size=24, color=mc(C_PRIMARY), font="Arial"
        ).next_to(fracs_row, DOWN, buff=0.55)

        self.play(FadeIn(bridge_note, shift=UP * 0.1), run_time=0.7)
        self.wait(WAIT_L)

        # Clear bridge entirely before title appears
        self.play(
            FadeOut(VGroup(bridge_txt, fracs_row, bridge_note)),
            run_time=0.6
        )
        self.wait(0.6)  # breathing room — brain files what it saw

        # ══════════════════════════════════════════════════════
        # BEAT 2 — TITLE + ONE-SENTENCE DEFINITION
        # Simplest possible language — no jargon yet
        # ══════════════════════════════════════════════════════

        title = Text(
            "What is a Rational Number?",
            font_size=44, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.45)

        self.play(Write(title), run_time=1.0)
        self.wait(WAIT_S)

        defn = Text(
            "A rational number is just the math name for a fraction.",
            font_size=26, color=mc(C_PRIMARY), font="Arial"
        ).next_to(title, DOWN, buff=0.38)

        self.play(FadeIn(defn, shift=UP * 0.1), run_time=0.7)
        self.wait(WAIT_M)

        sep = Line(
            LEFT * 5.5, RIGHT * 5.5,
            color=mc(C_SECOND), stroke_width=1.0
        ).next_to(defn, DOWN, buff=0.35)

        self.play(Create(sep), run_time=0.35)
        self.wait(0.6)  # breathing room

        # ══════════════════════════════════════════════════════
        # BEAT 3 — LARGE FRACTION WITH TRIPLE CODING
        # Layer 1 : math symbol p/q  (appears alone, held 4s)
        # Layer 2 : plain English    (top ÷ bottom)
        # Layer 3 : real example     (slice of pizza idea)
        # Each layer waits — student hears, reads, sees together
        # ══════════════════════════════════════════════════════

        pq = MathTex(
            r"\frac{p}{q}",
            font_size=110, color=mc(C_BLUE)
        ).next_to(sep, DOWN, buff=0.65)

        # Layer 1 — symbol alone with full breathing room
        self.play(Write(pq), run_time=1.3)
        self.wait(WAIT_L)

        # Layer 2 — English translation appears below
        layer2 = Text(
            "top number  ÷  bottom number",
            font_size=24, color=mc(C_PRIMARY), font="Arial"
        ).next_to(pq, DOWN, buff=0.42)

        self.play(FadeIn(layer2, shift=UP * 0.1), run_time=0.7)
        self.wait(WAIT_M)

        # Layer 3 — real life idea appears below layer 2
        layer3 = Text(
            "like  1 slice out of 2 equal slices",
            font_size=24, color=mc(C_GREEN), font="Arial"
        ).next_to(layer2, DOWN, buff=0.28)

        self.play(FadeIn(layer3, shift=UP * 0.1), run_time=0.7)
        self.wait(WAIT_L)

        # Clear layers 2 and 3 — keep p/q visible as anchor
        self.play(FadeOut(VGroup(layer2, layer3)), run_time=0.45)
        self.wait(0.6)  # breathing room

        # ══════════════════════════════════════════════════════
        # BEAT 4 — WHERE CLAUSE + STOP AND ANCHOR ON q≠0
        # p appears → wait → q appears → wait → q≠0 appears
        # Then: dim everything, box q≠0, hold, restore
        # ══════════════════════════════════════════════════════

        where = Text(
            "where:",
            font_size=27, color=mc(C_SECOND), font="Arial"
        ).next_to(pq, DOWN, buff=0.55).to_edge(LEFT, buff=1.3)

        self.play(FadeIn(where), run_time=0.4)
        self.wait(WAIT_S)

        p_line = MathTex(
            r"p \;\text{— any integer  (top number)}",
            font_size=32, color=mc(C_GREEN)
        ).next_to(where, DOWN, buff=0.30).to_edge(LEFT, buff=1.75)

        self.play(Write(p_line), run_time=0.8)
        self.wait(WAIT_M)

        q_line = MathTex(
            r"q \;\text{— any integer  (bottom number)}",
            font_size=32, color=mc(C_GREEN)
        ).next_to(p_line, DOWN, buff=0.26).to_edge(LEFT, buff=1.75)

        self.play(Write(q_line), run_time=0.8)
        self.wait(WAIT_M)

        # q≠0 in red — most important rule
        q_zero = MathTex(
            r"q \neq 0 \;\text{— bottom can NEVER be zero}",
            font_size=32, color=mc(C_RED)
        ).next_to(q_line, DOWN, buff=0.26).to_edge(LEFT, buff=1.75)

        self.play(Write(q_zero), run_time=0.9)
        self.wait(0.5)

        # ── STOP AND ANCHOR ────────────────────────────────────
        # Dim everything except q_zero — box draws around it
        # Narration delivers: "You can never divide by zero. Never."
        dim_group = VGroup(title, defn, sep, pq, where, p_line, q_line)

        anchor_box = SurroundingRectangle(
            q_zero,
            color=mc(C_RED),
            stroke_width=2.5,
            buff=0.22,
            corner_radius=0.12
        )

        self.play(
            dim_group.animate.set_opacity(0.15),
            Create(anchor_box),
            run_time=0.7
        )
        self.wait(WAIT_L + 0.5)  # hold — let the rule sink in

        # Restore screen fully
        self.play(
            dim_group.animate.set_opacity(1.0),
            FadeOut(anchor_box),
            run_time=0.6
        )
        self.wait(0.6)  # breathing room

        # ══════════════════════════════════════════════════════
        # BEAT 5 — PLAIN ENGLISH, ONE BULLET AT A TIME
        # Fade where-clause — title and p/q stay as anchors
        # Never more than 2 bullets visible at once
        # ══════════════════════════════════════════════════════

        self.play(
            FadeOut(VGroup(where, p_line, q_line, q_zero)),
            run_time=0.5
        )
        self.wait(0.6)  # breathing room

        eng_head = Text(
            "In plain English:",
            font_size=27, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).next_to(pq, DOWN, buff=0.55).to_edge(LEFT, buff=1.3)

        self.play(FadeIn(eng_head), run_time=0.45)
        self.wait(WAIT_S)

        b1 = Text(
            "•   Top number   →   any whole number, positive or negative",
            font_size=24, color=mc(C_PRIMARY), font="Arial"
        ).next_to(eng_head, DOWN, buff=0.36).to_edge(LEFT, buff=1.55)

        self.play(FadeIn(b1, shift=RIGHT * 0.12), run_time=0.65)
        self.wait(WAIT_M)

        b2 = Text(
            "•   Bottom number   →   any whole number   EXCEPT zero",
            font_size=24, color=mc(C_PRIMARY), font="Arial"
        ).next_to(b1, DOWN, buff=0.28).to_edge(LEFT, buff=1.55)

        self.play(FadeIn(b2, shift=RIGHT * 0.12), run_time=0.65)
        self.wait(WAIT_L)

        # ══════════════════════════════════════════════════════
        # BEAT 6 — REAL-LIFE EXAMPLES, ONE AT A TIME
        # Each example at same screen position — no crowding
        # Fraction appears first → description after
        # Previous clears before next arrives
        # ══════════════════════════════════════════════════════

        self.play(
            FadeOut(VGroup(eng_head, b1, b2)),
            run_time=0.5
        )
        self.wait(0.6)  # breathing room

        rl_head = Text(
            "Real-life idea:",
            font_size=27, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).next_to(pq, DOWN, buff=0.55).to_edge(LEFT, buff=1.3)

        self.play(FadeIn(rl_head), run_time=0.45)
        self.wait(WAIT_S)

        # (fraction_latex, color, description)
        examples = [
            (r"\frac{1}{2}", C_GREEN,
             "one part out of two equal parts"),
            (r"\frac{3}{4}", C_GREEN,
             "three parts out of four equal parts"),
            (r"-\frac{2}{5}", C_RED,
             "a negative fraction — still rational"),
        ]

        for frac_tex, frac_col, desc_str in examples:
            ex_frac = MathTex(
                frac_tex, font_size=72, color=mc(frac_col)
            )
            ex_desc = Text(
                desc_str,
                font_size=24, color=mc(C_PRIMARY), font="Arial"
            )
            # Fraction left — description right — bottom-aligned
            ex_row = VGroup(ex_frac, ex_desc).arrange(
                RIGHT, buff=0.55, aligned_edge=DOWN
            )
            ex_row.next_to(rl_head, DOWN, buff=0.48).to_edge(LEFT, buff=1.55)

            # Fraction first — narration reads the number
            self.play(Write(ex_frac), run_time=0.8)
            self.wait(0.45)

            # Description after — narration explains in words
            self.play(FadeIn(ex_desc, shift=RIGHT * 0.1), run_time=0.6)
            self.wait(WAIT_M)

            # Clear before next — guaranteed zero overlap
            self.play(FadeOut(ex_row), run_time=0.4)
            self.wait(0.3)

        self.play(FadeOut(rl_head), run_time=0.4)
        self.wait(0.6)  # breathing room

        # ══════════════════════════════════════════════════════
        # BEAT 7 — MEMORY SENTENCE
        # Everything fades — one sentence alone in the center
        # Recency effect: last thing seen = thing remembered
        # Narration reads it once, slowly, then silence
        # ══════════════════════════════════════════════════════

        self.play(
            FadeOut(VGroup(defn, sep, pq)),
            run_time=0.7
        )
        self.wait(0.6)

        memory = Text(
            "A rational number is any number\nyou can write as a fraction.",
            font_size=38, color=mc(C_PRIMARY),
            font="Arial", weight=BOLD,
            line_spacing=1.4
        ).move_to(ORIGIN)

        self.play(FadeIn(memory, shift=UP * 0.15), run_time=1.0)
        self.wait(WAIT_L + 0.5)  # narration reads it once, slowly

        # Fade everything to black — clean scene end
        self.play(
            FadeOut(VGroup(title, memory)),
            run_time=1.0
        )
        self.wait(0.5)
        sync_to_audio(self, sd.get("scene_id", 1))

# ════════════════════════════════════════════════════════════
# SCENE 02 — HOOK (VISUAL_ONLY)
# Real world situation shown as visual.
# No narration text on screen.
# Visual from real_world_hook field.
# ════════════════════════════════════════════════════════════

class Scene02_Hook(Scene):
    def construct(self):
        sd  = get_scene_data("hook")
        dur = sd.get("duration_seconds", 20.0)
        set_scene_bg(self, "hook")
        add_star_field(self, n_stars=60, max_opacity=0.40)
        add_floating_geometry(self, "tech")
        attach_audio(self, sd.get("scene_id", 2))
        add_broadcast_chrome(self, "hook")

        # Unit square
        square = Square(side_length=3.0,
                        color=mc(C_BLUE), stroke_width=3)
        square.shift(LEFT * 1.5 + DOWN * 0.3)

        # Side labels
        lbl_1a = MathTex("1", font_size=36, color=mc(C_PRIMARY))
        lbl_1b = MathTex("1", font_size=36, color=mc(C_PRIMARY))
        lbl_1a.next_to(square, DOWN, buff=0.2)
        lbl_1b.next_to(square, LEFT, buff=0.2)

        # Diagonal
        diag = Line(
            square.get_corner(DL), square.get_corner(UR),
            color=mc(C_YELLOW), stroke_width=4
        )
        diag_lbl = MathTex(r"\sqrt{2}", font_size=48,
                           color=mc(C_YELLOW))
        diag_lbl.next_to(diag.get_center(), UR, buff=0.2)

        # Right panel — can never write as fraction
        note = Text(
            "Can never be written\nas a fraction",
            font_size=28, color=mc(C_RED),
            font="Arial", line_spacing=1.3
        ).shift(RIGHT * 3.5 + UP * 0.5)

        arrow = Arrow(
            diag.get_center(), note.get_left(),
            color=mc(C_RED), stroke_width=2.5
        )

        self.play(Create(square), run_time=0.8)
        self.play(FadeIn(lbl_1a), FadeIn(lbl_1b), run_time=0.4)
        self.play(Create(diag), run_time=0.7)
        self.play(Write(diag_lbl), run_time=0.5)
        self.play(Create(arrow), FadeIn(note), run_time=0.7)
        sync_to_audio(self, sd.get("scene_id", 2))
# ════════════════════════════════════════════════════════════
# SCENE 03 — CONCEPT (VISUAL_ONLY)
# Clean diagram or illustration.
# Driven by visual_type from lesson.
# No narration text overlay.
# ════════════════════════════════════════════════════════════

class Scene03_Concept(Scene):
    def construct(self):
        sd       = get_scene_data("concept")
        dur      = sd.get("duration_seconds", 22.0)
        vis_type = SCRIPT_DATA.get("visual_type", "board_write")
        set_scene_bg(self, "concept")
        add_floating_geometry(self, "chalk")
        add_math_scatter(self)
        attach_audio(self, sd.get("scene_id", 3))
        add_broadcast_chrome(self, "concept")

        heading = Text(
            "The Concept",
            font_size=42, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        self.play(Write(heading), run_time=0.6)

        if "graph" in vis_type:
            self._draw_axes()
        elif "diagram" in vis_type:
            self._draw_diagram()
        elif "table" in vis_type:
            self._draw_table()
        else:
            self._draw_visual_card()
        sync_to_audio(self, sd.get("scene_id", 3))

    def _draw_axes(self):
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            axis_config={"color": mc(C_SECOND), "include_tip": True},
            x_length=9, y_length=5.0,
        ).shift(DOWN * 0.3)
        x_lbl = axes.get_x_axis_label(
            Text("x", font_size=24, color=mc(C_SECOND))
        )
        y_lbl = axes.get_y_axis_label(
            Text("y", font_size=24, color=mc(C_SECOND))
        )
        self.play(Create(axes), FadeIn(x_lbl), FadeIn(y_lbl), run_time=1.2)

    def _draw_diagram(self):
        circle = Circle(radius=2.2, color=mc(C_BLUE), stroke_width=3)
        circle.shift(DOWN * 0.3)
        dot    = Dot(circle.get_center(), color=mc(C_YELLOW))
        r_line = Line(circle.get_center(),
                      circle.point_at_angle(0),
                      color=mc(C_GREEN), stroke_width=2.5)
        r_lbl  = Text("r", font_size=24,
                      color=mc(C_GREEN)).next_to(r_line, UP, buff=0.1)
        self.play(Create(circle), run_time=0.9)
        self.play(FadeIn(dot), Create(r_line), FadeIn(r_lbl), run_time=0.6)

    def _draw_table(self):
        rows = [["Value", "Type"], ["1/2", "Rational"],
                ["-3", "Rational"], ["√2", "Irrational"]]
        tbl = Table(
            rows[1:],
            col_labels=[Text(h, font_size=22, color=mc(C_YELLOW))
                        for h in rows[0]],
            include_outer_lines=True,
            line_config={"stroke_width": 1.5, "color": mc(C_SECOND)},
        ).scale(0.7).shift(DOWN * 0.3)
        self.play(Create(tbl), run_time=1.4)

    def _draw_visual_card(self):
        # Number line with rational vs irrational distinction
        nl = NumberLine(
            x_range=[-3, 3, 1],
            length=11,
            include_numbers=True,
            color=mc(C_SECOND),
            numbers_with_elongated_ticks=[-2,-1,0,1,2],
        ).shift(DOWN * 0.5)

        heading2 = Text(
            "Rational numbers fit exactly on the number line",
            font_size=26, color=mc(C_SECOND), font="Arial"
        ).shift(UP * 3.0)

        rational_label = Text(
            "RATIONAL  (exact fraction)",
            font_size=20, color=mc(C_GREEN), font="Arial"
        ).to_corner(UL, buff=1.0).shift(DOWN * 1.2)

        irrational_label = Text(
            "IRRATIONAL  (no exact fraction)",
            font_size=20, color=mc(C_RED), font="Arial"
        ).to_corner(UR, buff=1.0).shift(DOWN * 1.2)

        rational_points = [
            (nl.n2p(-1.5),  r"-\tfrac{3}{2}",  C_GREEN, UP),
            (nl.n2p(0.333), r"\tfrac{1}{3}",   C_GREEN, UP),
            (nl.n2p(0.75),  r"\tfrac{3}{4}",   C_GREEN, DOWN),
            (nl.n2p(2.0),   r"2 = \tfrac{2}{1}", C_GREEN, UP),
        ]
        irrational_point = (nl.n2p(1.4142), r"\sqrt{2}", C_RED)

        self.play(Create(nl), run_time=1.0)
        self.play(FadeIn(heading2), run_time=0.4)
        self.play(FadeIn(rational_label), FadeIn(irrational_label), run_time=0.4)

        for pos, tex, col, direction in rational_points:
            dot = Dot(pos, color=mc(col), radius=0.1)
            lbl = MathTex(tex, font_size=26, color=mc(col))
            lbl.next_to(dot, direction, buff=0.25)
            self.play(FadeIn(dot), Write(lbl), run_time=0.45)
            self.wait(0.15)

        # Irrational point shown in red — never a clean fraction
        irr_pos, irr_tex, irr_col = irrational_point
        irr_dot = Dot(irr_pos, color=mc(irr_col), radius=0.1)
        irr_lbl = MathTex(irr_tex, font_size=28, color=mc(irr_col))
        irr_lbl.next_to(irr_dot, DOWN, buff=0.25)
        irr_note = Text("≈ 1.41421…  never ends, never repeats",
                        font_size=18, color=mc(irr_col), font="Arial")
        irr_note.next_to(irr_lbl, DOWN, buff=0.15)
        self.play(FadeIn(irr_dot), Write(irr_lbl), run_time=0.5)
        self.play(FadeIn(irr_note), run_time=0.4)
        self.wait(0.3)
# ════════════════════════════════════════════════════════════
# SCENE 04 — DEFINITION (VISUAL_ONLY)
# Formal definition shown on clean card.
# No narration text overlay.
# ════════════════════════════════════════════════════════════

class Scene04_Definition(Scene):
    def construct(self):
        sd  = get_scene_data("definition")
        dur = sd.get("duration_seconds", 16.0)
        set_scene_bg(self, "definition")
        add_floating_geometry(self, "chalk")
        attach_audio(self, sd.get("scene_id", 4))
        add_broadcast_chrome(self, "definition")

        heading = Text(
            "Definition",
            font_size=42, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        def_card = RoundedRectangle(
            corner_radius=0.3,
            width=12.5, height=3.5,
            fill_color=mc(C_CARD),
            fill_opacity=0.95,
            stroke_color=mc(C_YELLOW),
            stroke_width=2.5
        ).shift(UP * 0.3)

        # Key formula as the formal definition centrepiece
        formula_str = SCRIPT_DATA.get("key_formula", "")
        try:
            formula_mob = MathTex(
                formula_str, font_size=72, color=mc(C_PRIMARY)
            ).move_to(def_card.get_center()).shift(UP * 0.3)
        except Exception:
            formula_mob = Text(
                SCRIPT_DATA.get("formula_spoken", ""),
                font_size=28, color=mc(C_PRIMARY), font="Arial"
            ).move_to(def_card.get_center()).shift(UP * 0.3)

        spoken_txt = Text(
            wrap_text(SCRIPT_DATA.get("formula_spoken", ""), 60),
            font_size=24, color=mc(C_BLUE), font="Arial"
        ).move_to(def_card.get_center()).shift(DOWN * 0.55)

        prereq_card = RoundedRectangle(
            corner_radius=0.2,
            width=12.5, height=1.1,
            fill_color=mc(C_CARD),
            fill_opacity=0.85,
            stroke_color=mc(C_SECOND),
            stroke_width=1.5
        ).shift(DOWN * 2.2)

        prereq_txt = Text(
            f"Requires: {SCRIPT_DATA.get('prerequisite', '')[:60]}",
            font_size=22, color=mc(C_SECOND), font="Arial"
        ).move_to(prereq_card.get_center())

        self.play(Write(heading), run_time=0.6)
        self.play(FadeIn(def_card), run_time=0.4)
        p_mob = MathTex("p", font_size=72,
                        color=mc(C_GREEN)).move_to(def_card).shift(UP*0.3+LEFT*0.6)
        bar   = MathTex(r"\over", font_size=72,
                        color=mc(C_PRIMARY)).move_to(def_card).shift(UP*0.3)
        q_mob = MathTex("q", font_size=72,
                        color=mc(C_BLUE)).move_to(def_card).shift(UP*0.3+RIGHT*0.6)
        cond  = MathTex(r"q \neq 0", font_size=40,
                        color=mc(C_RED)).move_to(def_card).shift(UP*0.3+RIGHT*2.2)

        self.play(Write(p_mob), run_time=0.5)
        self.play(Create(Line(LEFT*0.35, RIGHT*0.35,
                  color=mc(C_PRIMARY), stroke_width=3
                  ).move_to(def_card).shift(UP*0.3)), run_time=0.3)
        self.play(Write(q_mob), run_time=0.5)
        self.play(Write(cond),  run_time=0.6)
        self.play(FadeIn(spoken_txt), run_time=0.6)
        self.play(FadeIn(prereq_card), FadeIn(prereq_txt), run_time=0.5)
        sync_to_audio(self, sd.get("scene_id", 4))
# ════════════════════════════════════════════════════════════
# SCENE 05 — FORMULA (EQUATION_BUILD)
# Formula builds one component at a time.
# Each part appears as Ryan reads it.
# Previous parts stay visible but dimmed.
# Full formula never appears all at once.
# ════════════════════════════════════════════════════════════

class Scene05_Formula(Scene):
    def construct(self):
        sd  = get_scene_data("formula")
        dur = sd.get("duration_seconds", 20.0)
        set_scene_bg(self, "formula")
        add_math_scatter(self, opacity=0.05)
        attach_audio(self, sd.get("scene_id", 5))
        add_broadcast_chrome(self, "formula")

        # Gold/amber heading on near-black — matches the premium
        # "pure black + gold curve" reference image
        heading = Text(
            "The Formula",
            font_size=42, color=mc(C_GOLD),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        underline = Line(
            heading.get_left() + DOWN * 0.1,
            heading.get_right() + DOWN * 0.1,
            color=mc(C_GOLD), stroke_width=2.5,
        )
        underline.shift(DOWN * heading.height * 0.5 + DOWN * 0.08)

        self.play(Write(heading), run_time=0.6)
        self.play(Create(underline), run_time=0.4)

        # Read board_examples formula field
        board   = sd.get("board_examples", {})
        formula_str = board.get("formula",
                      SCRIPT_DATA.get("key_formula", "p/q"))

        # Build formula components from worked_example steps
        steps   = board.get("worked_example", [])

        if steps:
            per_step = max(0.5, (dur - 2.5) / len(steps))

            fs = 46 if len(steps) <= 4 else (38 if len(steps) <= 6 else 30)
            # First line in gold, rest in chalk-white
            visible_mobs = build_step_column(
                steps, font_size=fs, buff=0.45,
                first_color=C_GOLD, other_color=C_CHALK,
                top_y=2.4, left_buff=1.0, max_height=5.6,
            )

            shown = []
            for mob in visible_mobs:
                if shown:
                    self.play(
                        *[m.animate.set_opacity(0.4) for m in shown],
                        Write(mob),
                        run_time=0.7,
                    )
                else:
                    self.play(Write(mob), run_time=0.7)
                shown.append(mob)
                self.wait(max(0.1, per_step - 0.7))
        else:
            # Fallback: gold formula centred on black — premium look
            try:
                fml = MathTex(formula_str, font_size=80,
                              color=mc(C_GOLD))
            except Exception:
                fml = Text(SCRIPT_DATA.get("formula_spoken", ""),
                           font_size=32, color=mc(C_GOLD),
                           font="Arial")
            fml.shift(UP * 0.5)
            box = SurroundingRectangle(
                fml, color=mc(C_GOLD),
                stroke_width=2.0, buff=0.4, corner_radius=0.2
            )
            self.play(Write(fml), run_time=1.4)
            self.play(Create(box), run_time=0.5)
        sync_to_audio(self, sd.get("scene_id", 5))


# ════════════════════════════════════════════════════════════
# SCENE 06 — WORKED EXAMPLE (BOARD_WRITE)
# Each step of working appears line by line.
# Reads directly from board_examples worked_example list.
# No narration text. Math only on board.
# ════════════════════════════════════════════════════════════

class Scene06_WorkedExample(Scene):
    def construct(self):
        sd  = get_scene_data("worked_example")
        dur = sd.get("duration_seconds", 24.0)
        set_scene_bg(self, "worked_example")
        add_floating_geometry(self, "subtle")
        attach_audio(self, sd.get("scene_id", 6))
        add_broadcast_chrome(self, "worked_example")

        # ── Broadcast-style scene title with underline sweep ──
        scene_title_reveal(
            self, "Worked Example", C_GREEN,
            subtitle="Follow each step — logic builds line by line",
        )

        board = sd.get("board_examples", {})
        steps = board.get("worked_example", [])

        if not steps:
            steps = [
                SCRIPT_DATA.get("key_formula", ""),
                r"\text{Apply the definition step by step}",
                r"\text{Check your answer}",
            ]

        per_step = max(0.5, (dur - 3.0) / max(len(steps), 1))

        if len(steps) <= 4:
            fs = 40
        elif len(steps) <= 6:
            fs = 32
        else:
            fs = 26

        # Auto-arranged column, offset right so numbered step markers can sit left of it
        mobs = build_step_column(
            steps, font_size=fs, buff=0.5,
            first_color=C_YELLOW, other_color=C_PRIMARY,
            top_y=2.0, left_buff=1.75, max_height=5.4,
        )

        # Numbered progress markers to the LEFT of each step — turns the
        # column into a proper visual walkthrough rather than a text dump.
        markers = []
        for i, mob in enumerate(mobs, start=1):
            circ = Circle(radius=0.24, color=mc(C_GREEN), stroke_width=2.5)
            circ.set_fill(mc(C_BG), opacity=1.0)
            num = Text(str(i), font_size=20,
                       color=mc(C_GREEN), font="Arial", weight=BOLD)
            marker = VGroup(circ, num)
            marker.next_to(mob, LEFT, buff=0.35, aligned_edge=UP)
            marker.shift(DOWN * 0.05)
            markers.append(marker)

        # Vertical connector line down the marker column
        if len(markers) >= 2:
            top    = markers[0].get_center()
            bottom = markers[-1].get_center()
            spine  = Line(top, bottom, color=mc(C_GREEN), stroke_width=1.5)
            spine.set_opacity(0.35).set_z_index(-1)
            self.add(spine)

        for i, (m, marker) in enumerate(zip(mobs, markers)):
            # Marker appears first (as Ryan says "step N")
            self.play(
                FadeIn(marker, scale=0.7),
                run_time=0.35,
            )
            self.play(Write(m), run_time=0.6)
            self.wait(max(0.1, per_step - 0.95))

        # Final answer glow — the big payoff at the end
        if mobs:
            glow_highlight(self, mobs[-1], color=C_GREEN,
                           run_time=0.55, hold=0.5)
            # Marker for final step turns solid gold
            if markers:
                self.play(
                    markers[-1][0].animate.set_fill(mc(C_GREEN), opacity=1.0),
                    markers[-1][1].animate.set_color(mc(C_BG)),
                    run_time=0.35,
                )

        sync_to_audio(self, sd.get("scene_id", 6))


# ════════════════════════════════════════════════════════════
# SCENE 07 — MISTAKES (BOARD_WRITE)
# Wrong working shown with red cross.
# Correct version written below in green.
# ════════════════════════════════════════════════════════════

class Scene07_Mistakes(Scene):
    def construct(self):
        sd  = get_scene_data("mistakes")
        dur = sd.get("duration_seconds", 22.0)
        set_scene_bg(self, "mistakes")
        add_floating_geometry(self, "subtle")
        attach_audio(self, sd.get("scene_id", 7))
        add_broadcast_chrome(self, "mistakes")

        # ── Scene title ────────────────────────────────────────
        scene_title_reveal(
            self, "Common Mistakes", C_RED,
            subtitle="Learn what to avoid — before it costs you marks",
        )

        board = sd.get("board_examples", {})
        raw   = board.get("worked_example", [])

        wrong_lines   = []
        correct_lines = []
        neutral_lines = []
        for txt in raw:
            if "Mistake" in txt or "Wrong" in txt:
                wrong_lines.append(txt)
            elif "Correct" in txt or "checkmark" in txt or "\\checkmark" in txt:
                correct_lines.append(txt)
            else:
                neutral_lines.append(txt)

        # Fallback content pulled from the common_mistake field on the lesson
        cm = SCRIPT_DATA.get("common_mistake", "")
        if not wrong_lines:
            wrong_lines = [
                r"\text{" + (cm[:44] or "Skipping a key rule") + r"}",
                r"\text{Result: wrong answer, lost marks}",
            ]
        if not correct_lines:
            correct_lines = [
                r"\text{Always check the condition first}",
                r"\text{Then apply the formula carefully}",
            ]

        # ── Split-panel comparison: WRONG (red) │ RIGHT (green) ──
        (l_panel, l_hdr), (r_panel, r_hdr) = comparison_split(
            self,
            left_title  = "WRONG  ✗",
            right_title = "CORRECT  ✓",
            left_color  = C_RED,
            right_color = C_GREEN,
        )

        # Fill left panel with wrong lines
        left_mobs = []
        for txt in wrong_lines[:4]:
            try:
                m = MathTex(txt, font_size=28, color=mc(C_RED))
            except Exception:
                m = Text(txt, font_size=20, color=mc(C_RED), font="Arial")
            left_mobs.append(m)
        left_grp = VGroup(*left_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        # Auto-shrink if too wide/tall for panel
        max_w = l_panel.width  - 0.5
        max_h = l_panel.height - 1.1
        if left_grp.width  > max_w or left_grp.height > max_h:
            left_grp.scale(min(max_w / max(left_grp.width, 0.01),
                               max_h / max(left_grp.height, 0.01)))
        left_grp.move_to(l_panel.get_center() + DOWN * 0.2)

        # Fill right panel with correct lines
        right_mobs = []
        for txt in correct_lines[:4]:
            try:
                m = MathTex(txt, font_size=28, color=mc(C_GREEN))
            except Exception:
                m = Text(txt, font_size=20, color=mc(C_GREEN), font="Arial")
            right_mobs.append(m)
        right_grp = VGroup(*right_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        if right_grp.width  > max_w or right_grp.height > max_h:
            right_grp.scale(min(max_w / max(right_grp.width, 0.01),
                                max_h / max(right_grp.height, 0.01)))
        right_grp.move_to(r_panel.get_center() + DOWN * 0.2)

        # Reveal wrong side first (build tension), then correct side
        for m in left_mobs:
            self.play(Write(m), run_time=0.55)
            self.wait(0.35)

        # Big red ✗ pulse
        big_cross = Text("✗", font_size=110, color=mc(C_RED),
                         font="Arial", weight=BOLD).move_to(l_panel.get_center())
        big_cross.set_opacity(0.0)
        self.add(big_cross)
        self.play(big_cross.animate.set_opacity(0.25).scale(1.2), run_time=0.5)

        # Reveal correct side
        for m in right_mobs:
            self.play(Write(m), run_time=0.55)
            self.wait(0.35)

        # Green ✓ pulse and glow on correct panel
        big_tick = Text("✓", font_size=110, color=mc(C_GREEN),
                        font="Arial", weight=BOLD).move_to(r_panel.get_center())
        big_tick.set_opacity(0.0)
        self.add(big_tick)
        self.play(big_tick.animate.set_opacity(0.25).scale(1.2), run_time=0.5)

        # Emphasise the correct panel with a border glow
        r_glow = SurroundingRectangle(
            r_panel, color=mc(C_GREEN), stroke_width=3.5,
            buff=0.1, corner_radius=0.32,
        )
        self.play(Create(r_glow), run_time=0.5)

        sync_to_audio(self, sd.get("scene_id", 7))


# ════════════════════════════════════════════════════════════
# SCENE 08 — PRACTICE (BOARD_WRITE)
# Question at top. Solution steps build line by line.
# Final answer in green box with tick.
# Reads from board_examples practice list.
# ════════════════════════════════════════════════════════════

class Scene08_Practice(Scene):
    def construct(self):
        sd  = get_scene_data("practice")
        dur = sd.get("duration_seconds", 20.0)
        set_scene_bg(self, "practice")
        add_floating_geometry(self, "chalk")
        add_math_scatter(self)
        attach_audio(self, sd.get("scene_id", 8))
        add_broadcast_chrome(self, "practice")

        heading = Text(
            "Practice Problem",
            font_size=42, color=mc(C_GREEN),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        self.play(Write(heading), run_time=0.6)

        board    = sd.get("board_examples", {})
        practice = board.get("practice", [])

        if not practice:
            practice = [
                r"\text{Question: Apply today's formula to a new example}",
                r"\text{Step 1 — Write the given information}",
                r"\text{Step 2 — Substitute into the formula}",
                r"\text{Step 3 — Simplify and verify}",
            ]

        # First item is the question
        question_tex = practice[0] if practice else r"\text{Solve the problem}"
        solution_steps = practice[1:] if len(practice) > 1 else []

        # Question box
        try:
            q_mob = MathTex(question_tex, font_size=40,
                            color=mc(C_YELLOW))
        except Exception:
            q_mob = Text(question_tex, font_size=26,
                         color=mc(C_YELLOW), font="Arial")

        q_box = SurroundingRectangle(
            q_mob, color=mc(C_YELLOW),
            stroke_width=2.0, buff=0.3, corner_radius=0.2
        )
        q_mob.to_edge(LEFT, buff=0.9)
        q_mob.shift(UP * 2.8)
        q_box.move_to(q_mob.get_center()).match_width(q_mob)

        self.play(Write(q_mob), Create(q_box), run_time=0.8)

        per_step = max(0.5, (dur - 3.0) / max(len(solution_steps), 1))

        n = len(solution_steps)
        if n <= 3:
            fs = 40
        elif n <= 5:
            fs = 32
        else:
            fs = 26

        # Anchor top of solution column just below the question box
        q_bottom_y = q_box.get_bottom()[1] - 0.35

        sol_mobs = build_step_column(
            solution_steps, font_size=fs, buff=0.42,
            first_color=C_PRIMARY, other_color=C_PRIMARY,
            top_y=q_bottom_y, left_buff=0.9, max_height=q_bottom_y + 3.4,
        )

        for m in sol_mobs:
            self.play(Write(m), run_time=0.6)
            self.wait(max(0.1, per_step - 0.6))

        # Final answer green highlight
        if sol_mobs:
            ans_box = SurroundingRectangle(
                sol_mobs[-1],
                color=mc(C_GREEN),
                stroke_width=2.5,
                buff=0.2,
                corner_radius=0.15
            )
            tick = Text("✓", font_size=38,
                        color=mc(C_GREEN)).next_to(sol_mobs[-1], RIGHT, buff=0.3)
            self.play(
                Create(ans_box),
                FadeIn(tick),
                sol_mobs[-1].animate.set_color(mc(C_GREEN)),
                run_time=0.55
            )

        sync_to_audio(self, sd.get("scene_id", 8))


# ════════════════════════════════════════════════════════════
# SCENE 09 — SUMMARY (VISUAL_ONLY)
# Clean summary card.
# Channel name, formula, three recap points,
# next lesson teaser, subscribe call to action.
# Logo top-left. Banner bottom.
# ════════════════════════════════════════════════════════════

class Scene09_Summary(Scene):
    def construct(self):
        sd  = get_scene_data("summary")
        dur = sd.get("duration_seconds", 24.0)
        set_scene_bg(self, "summary")
        add_star_field(self, n_stars=70, max_opacity=0.45)
        add_floating_geometry(self, "tech")
        attach_audio(self, sd.get("scene_id", 9))
        add_broadcast_chrome(self, "summary")

        channel_txt = Text(
            CHANNEL,
            font_size=26, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        day_txt = Text(
            f"Day {{LESSON_ID}} — {{SCRIPT_DATA.get('title', '')}}",
            font_size=34, color=mc(C_PRIMARY),
            font="Arial", weight=BOLD
        ).next_to(channel_txt, DOWN, buff=0.25)

        divider = Line(
            LEFT * 6, RIGHT * 6,
            color=mc(C_YELLOW), stroke_width=1.5
        ).next_to(day_txt, DOWN, buff=0.2)

        formula_str = SCRIPT_DATA.get("key_formula", "")
        try:
            formula = MathTex(
                formula_str, font_size=56, color=mc(C_YELLOW)
            ).next_to(divider, DOWN, buff=0.3)
        except Exception:
            formula = Text(
                SCRIPT_DATA.get("formula_spoken", ""),
                font_size=26, color=mc(C_YELLOW), font="Arial"
            ).next_to(divider, DOWN, buff=0.3)

        bullets = [
            f"✓  {SCRIPT_DATA.get('lesson_goal', '')[:58]}",
            f"✓  Formula: {SCRIPT_DATA.get('formula_spoken', '')[:50]}",
            f"✓  Check conditions before applying any formula.",
        ]
        bullet_group = VGroup(*[
            Text(b, font_size=21,
                 color=mc(C_PRIMARY), font="Arial")
            for b in bullets
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        bullet_group.next_to(formula, DOWN, buff=0.4)
        bullet_group.to_edge(LEFT, buff=0.85)

        teaser_txt = Text(
            wrap_text(SCRIPT_DATA.get("intro_teaser", ""), 58),
            font_size=19, color=mc(C_BLUE), font="Arial"
        ).shift(DOWN * 2.75)

        sub_box = RoundedRectangle(
            corner_radius=0.2,
            width=7.0, height=0.65,
            fill_color=mc(C_RED),
            fill_opacity=0.88,
            stroke_color=mc(C_RED),
            stroke_width=1.5
        ).shift(DOWN * 3.55)

        sub_txt = Text(
            "▶  Subscribe to MathConceptsMadeEasy",
            font_size=21, color=mc(C_PRIMARY), font="Arial"
        ).move_to(sub_box.get_center())

        self.play(Write(channel_txt), run_time=0.55)
        self.play(FadeIn(day_txt, shift=UP * 0.1), run_time=0.5)
        self.play(Create(divider), run_time=0.3)
        self.play(Write(formula), run_time=0.9)

        per_b = max(0.4, (dur - 5.5) / (len(bullets) + 2))
        for b in bullet_group:
            self.play(FadeIn(b, shift=RIGHT * 0.1), run_time=0.4)
            self.wait(per_b - 0.4)

        self.play(FadeIn(teaser_txt), run_time=0.5)
        self.wait(per_b)
        self.play(FadeIn(sub_box), FadeIn(sub_txt), run_time=0.5)
        self.wait(0.8)
        sync_to_audio(self, sd.get("scene_id", 9))
'''

# ══════════════════════════════════════════════════════════════
# INJECT RUNTIME VALUES INTO MANIM CODE
# ══════════════════════════════════════════════════════════════

def build_manim_source(script: dict) -> str:
    source = MANIM_SCENE_CODE

    # Fix: placeholder names must match what's in the r-string exactly
    source = source.replace("__SCRIPT_PATH__", str(TIMED_SCRIPT))
    source = source.replace("__AUDIO_DIR__",   str(LESSON_AUDIO))
    source = source.replace("__BANNER_PATH__", str(BANNER_PATH))
    source = source.replace("__LOGO_PATH__",   str(LOGO_PATH))

    # Colour constants — these placeholders ARE correct in the string
    source = source.replace("{C_BG}",      C_BG)
    source = source.replace("{C_PRIMARY}", C_PRIMARY)
    source = source.replace("{C_SECOND}",  C_SECOND)
    source = source.replace("{C_BLUE}",    C_BLUE)
    source = source.replace("{C_GREEN}",   C_GREEN)
    source = source.replace("{C_YELLOW}",  C_YELLOW)
    source = source.replace("{C_RED}",     C_RED)
    source = source.replace("{C_CARD}",    C_CARD)

    # Note: LESSON_ID and SCRIPT_DATA_PLACEHOLDER replacements removed —
    # LESSON_ID is already read from SCRIPT_DATA inside the generated file,
    # and replacing {LESSON_ID} breaks the f-strings in Scene01 and Scene09.
    return source

# ══════════════════════════════════════════════════════════════
# MANIM RENDERER
# Writes the .py file, calls manim CLI per scene,
# copies each rendered MP4 to Math-9/renders/lesson_001/
# ══════════════════════════════════════════════════════════════

SCENE_CLASS_MAP = {
    "opening"       : "Scene01_Opening",
    "hook"          : "Scene02_Hook",
    "concept"       : "Scene03_Concept",
    "definition"    : "Scene04_Definition",
    "formula"       : "Scene05_Formula",
    "worked_example": "Scene06_WorkedExample",
    "mistakes"      : "Scene07_Mistakes",
    "practice"      : "Scene08_Practice",
    "summary"       : "Scene09_Summary",
}

def render_all_scenes(script: dict):
    source_code = build_manim_source(script)
    source_file = TEMP_DIR / "math_scenes.py"

    with open(str(source_file), "w", encoding="utf-8") as f:
        f.write(source_code)

    print(f"✅ Manim source written → {source_file}\n")
    print(f"{'═'*65}")
    print(f"  RENDERING {len(script['scenes'])} SCENES")
    print(f"{'═'*65}\n")

    results     = []
    render_root = TEMP_DIR / "media" / "videos" / "math_scenes" / "1080p60"
    render_root_fallback = TEMP_DIR / "media" / "videos" / "math_scenes"

    for scene in script["scenes"]:
        step        = scene["step"]
        scene_id    = scene["scene_id"]
        class_name  = SCENE_CLASS_MAP.get(step)
        label       = scene["label"]

        if not class_name:
            print(f"  ⚠️  No class mapped for step '{step}' — skipping.")
            continue

        print(f"  ▶ Scene {scene_id:02d} [{step:10s}] {label}")
        print(f"    Class : {class_name}")

        cmd = [
            "manim",
            "-qh",                          # quality: high 1080p60                          # quality: low for fast preview
            "--media_dir", str(TEMP_DIR / "media"),
            str(source_file),
            class_name,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(TEMP_DIR)
        )

        # ── Locate rendered file ──────────────────────────────
        expected_mp4 = render_root / f"{class_name}.mp4"

        # Manim sometimes puts it one level up — search broadly
        if not expected_mp4.exists():
            found = sorted(
                TEMP_DIR.rglob(f"{class_name}.mp4"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            expected_mp4 = found[0] if found else None

        if expected_mp4 and Path(expected_mp4).exists():
            dest = LESSON_RENDER / f"scene_{scene_id:02d}_{step}.mp4"
            shutil.copy(str(expected_mp4), str(dest))
            size_kb = dest.stat().st_size // 1024
            print(f"    ✅ Rendered → {dest.name}  ({size_kb} KB)")
            results.append({
                "scene_id" : scene_id,
                "step"     : step,
                "success"  : True,
                "path"     : str(dest),
                "size_kb"  : size_kb,
            })
        else:
            print(f"    ❌ Render FAILED for {class_name}")
            if result.stderr:
                # Show last 8 lines of Manim stderr
                err_lines = result.stderr.strip().split("\n")
                for line in err_lines[-8:]:
                    print(f"       {line}")
            results.append({
                "scene_id" : scene_id,
                "step"     : step,
                "success"  : False,
                "path"     : None,
            })

        print()

    return results

# ══════════════════════════════════════════════════════════════
# PRINT RENDER REPORT
# ══════════════════════════════════════════════════════════════

def print_render_report(results: list):
    succeeded = [r for r in results if r["success"]]
    failed    = [r for r in results if not r["success"]]

    print(f"{'═'*65}")
    print(f"  RENDER REPORT — Day {lesson_id}: {SCRIPT['title']}")
    print(f"{'═'*65}")
    print(f"  {'#':<4} {'Step':<12} {'Status':<8} {'Size':>8}")
    print(f"  {'─'*63}")

    for r in results:
        status  = "✅" if r["success"] else "❌"
        size_s  = f"{r.get('size_kb', 0)} KB" if r["success"] else "—"
        print(f"  {r['scene_id']:<4} {r['step']:<12} {status:<8} {size_s:>8}")

    print(f"  {'─'*63}")
    print(f"  Succeeded : {len(succeeded)}/{len(results)}")
    if failed:
        print(f"  ❌ Failed : {[r['step'] for r in failed]}")
    print(f"\n  Renders saved to : {LESSON_RENDER}")
    print(f"\n  ▶ Run Cell 5 next to assemble final video.\n")

# ══════════════════════════════════════════════════════════════
# EXECUTE
# ══════════════════════════════════════════════════════════════

render_results = render_all_scenes(SCRIPT)
print_render_report(render_results)

