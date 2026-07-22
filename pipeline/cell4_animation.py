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
import json, math, random, re, textwrap
from pathlib import Path

# ── Data loading ──────────────────────────────────────────────
SCRIPT_PATH  = Path(r"__SCRIPT_PATH__")
LESSON_AUDIO = Path(r"__AUDIO_DIR__")
LOGO_PATH    = Path(r"__LOGO_PATH__")
BANNER_PATH  = Path(r"__BANNER_PATH__")

with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    SCRIPT_DATA = json.load(f)

LESSON_ID = SCRIPT_DATA["lesson_id"]

# Brand colors (injected from theme at render time)
C_BG      = "{C_BG}"
C_PRIMARY = "{C_PRIMARY}"
C_SECOND  = "{C_SECOND}"
C_BLUE    = "{C_BLUE}"
C_GREEN   = "{C_GREEN}"
C_YELLOW  = "{C_YELLOW}"
C_RED     = "{C_RED}"
C_CARD    = "{C_CARD}"

# Premium brand palette (fixed — never overridden by theme)
C_NAVY1  = "#081B33"
C_NAVY2  = "#102C57"
C_BLUE_P = "#2563EB"
C_BLUE_L = "#3B82F6"
C_BLUE_D = "#1D4ED8"
C_GOLD   = "#FACC15"
C_ORANGE = "#F59E0B"
C_GGREEN = "#22C55E"
C_PURPLE = "#8B5CF6"
C_RRED   = "#EF4444"
C_WHITE  = "#FFFFFF"
C_LGRAY  = "#E5E7EB"
C_HEADER = "#0A1628"
C_FOOTER = "#050D1A"
C_CBG    = "#0D2045"

CHANNEL = "Math Concept Made Easy"
TAGLINE = "LEARN  •  PRACTICE  •  MASTER"

config.background_color = C_NAVY1

def mc(h):
    return ManimColor(h)

# ── Frame layout constants ────────────────────────────────────
FW = 14.222   # config.frame_width default for 1080p60
FH = 8.0      # config.frame_height default

HEADER_TOP  =  3.70
HEADER_BOT  =  2.85
CONTENT_TOP =  2.75
CONTENT_BOT = -3.25
FOOTER_TOP  = -3.35
FOOTER_BOT  = -4.00

# ── Helpers ───────────────────────────────────────────────────

def get_scene_by_step(step):
    for s in SCRIPT_DATA["scenes"]:
        if s.get("step") == step:
            return s
    return SCRIPT_DATA["scenes"][0] if SCRIPT_DATA["scenes"] else {}

def _wrap(text, width=52):
    return "\n".join(textwrap.wrap(str(text), width))

def attach_audio(scene_obj, scene_id):
    mp3 = LESSON_AUDIO / f"scene_{scene_id:02d}.mp3"
    if mp3.exists():
        try:
            scene_obj.add_sound(str(mp3))
        except Exception:
            pass

def sync_to_audio(scene_obj, scene_id):
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


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — BACKGROUND
# ═════════════════════════════════════════════════════════════

def setup_bg(scene_obj):
    """Dark navy background + 4%-opacity grid + tiny floating accent dots."""
    import numpy as np

    scene_obj.camera.background_color = mc(C_NAVY1)

    # Full-frame dark gradient rect
    bg = Rectangle(
        width=FW + 1.0, height=FH + 1.0,
        fill_color=[mc(C_NAVY1), mc(C_NAVY2)],
        fill_opacity=1.0,
        stroke_width=0,
    )
    bg.set_z_index(-200)
    scene_obj.add(bg)

    # Faint grid (4 % opacity)
    grid = VGroup()
    for x in np.arange(-7.0, 7.5, 1.5):
        ln = Line(
            np.array([x, -4.2, 0]), np.array([x, 4.2, 0]),
            stroke_width=0.5, color=mc(C_BLUE_L),
        )
        ln.set_stroke(opacity=0.04)
        grid.add(ln)
    for y in np.arange(-4.0, 4.5, 1.0):
        ln = Line(
            np.array([-7.3, y, 0]), np.array([7.3, y, 0]),
            stroke_width=0.5, color=mc(C_BLUE_L),
        )
        ln.set_stroke(opacity=0.04)
        grid.add(ln)
    grid.set_z_index(-190)
    scene_obj.add(grid)

    # Tiny floating dots — atmospheric depth
    rng = random.Random(99)
    for _ in range(20):
        x   = rng.uniform(-6.9, 6.9)
        y   = rng.uniform(-3.9, 3.9)
        r   = rng.uniform(0.018, 0.055)
        op  = rng.uniform(0.05, 0.16)
        dot = Dot(
            point=np.array([x, y, 0]),
            radius=r,
            color=mc(C_BLUE_L),
            fill_opacity=op,
        )
        dot.set_z_index(-180)
        scene_obj.add(dot)


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — HEADER
# ═════════════════════════════════════════════════════════════

def make_header(lesson_title="", day=1):
    """
    Premium top bar (HEADER_BOT → HEADER_TOP).
    Left  : yellow 'M' logo circle + channel name + tagline
    Center: lesson title
    Right : purple DAY badge
    Returns a VGroup (z_index=80).
    """
    import numpy as np
    hcy = (HEADER_TOP + HEADER_BOT) / 2    # 3.275
    hh  = HEADER_TOP - HEADER_BOT           # 0.85

    # Background bar
    bg_bar = Rectangle(
        width=FW, height=hh,
        fill_color=mc(C_HEADER), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([0.0, hcy, 0.0]))

    # Bottom gold accent line
    accent = Rectangle(
        width=FW, height=0.04,
        fill_color=mc(C_GOLD), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([0.0, HEADER_BOT + 0.02, 0.0]))

    # Logo circle with 'M'
    logo_circ = Circle(
        radius=0.26,
        fill_color=mc(C_GOLD), fill_opacity=1.0, stroke_width=0,
    )
    logo_m = Text("M", font_size=18, color=mc(C_NAVY1),
                  font="Arial", weight=BOLD)
    logo_m.move_to(logo_circ.get_center())
    logo_grp = VGroup(logo_circ, logo_m)
    logo_grp.move_to(np.array([-6.45, hcy + 0.10, 0.0]))

    # Channel name + tagline stacked
    ch_name = Text(
        CHANNEL, font_size=13,
        color=mc(C_WHITE), font="Arial", weight=BOLD,
    ).next_to(logo_grp, RIGHT, buff=0.10).align_to(logo_grp, UP).shift(DOWN * 0.01)

    tagline_txt = Text(
        TAGLINE, font_size=9,
        color=mc(C_GOLD), font="Arial",
    ).next_to(ch_name, DOWN, buff=0.04).align_to(ch_name, LEFT)

    # Lesson title — centered
    lt = str(lesson_title) if lesson_title else str(SCRIPT_DATA.get("title", ""))
    lt = lt[:58]
    try:
        title_mob = Text(
            lt, font_size=17,
            color=mc(C_WHITE), font="Arial", weight=BOLD,
        )
    except Exception:
        title_mob = Text("Lesson", font_size=17,
                         color=mc(C_WHITE), font="Arial", weight=BOLD)
    if title_mob.width > 6.2:
        title_mob.scale_to_fit_width(6.2)
    title_mob.move_to(np.array([0.0, hcy, 0.0]))

    # DAY badge — purple pill
    day_bg = RoundedRectangle(
        width=1.25, height=0.46,
        corner_radius=0.10,
        fill_color=mc(C_PURPLE), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([6.22, hcy, 0.0]))
    day_txt = Text(
        "DAY " + str(day), font_size=13,
        color=mc(C_WHITE), font="Arial", weight=BOLD,
    ).move_to(day_bg.get_center())

    grp = VGroup(bg_bar, accent, logo_grp, ch_name, tagline_txt,
                 title_mob, day_bg, day_txt)
    grp.set_z_index(80)
    return grp


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — FOOTER
# ═════════════════════════════════════════════════════════════

def make_footer():
    """
    Premium bottom bar (FOOTER_BOT → FOOTER_TOP).
    Left  : red YouTube circle + 'NEW VIDEOS EVERY DAY'
    Center: bell + SUBSCRIBE & TURN ON NOTIFICATIONS in gold
    Right : @MathConceptMadeEasy handle
    Returns a VGroup (z_index=80).
    """
    import numpy as np
    fcy = (FOOTER_TOP + FOOTER_BOT) / 2    # -3.675
    fh  = FOOTER_TOP - FOOTER_BOT           #  0.65

    bg_bar = Rectangle(
        width=FW, height=fh,
        fill_color=mc(C_FOOTER), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([0.0, fcy, 0.0]))

    top_line = Rectangle(
        width=FW, height=0.03,
        fill_color=mc(C_GOLD), fill_opacity=0.55, stroke_width=0,
    ).move_to(np.array([0.0, FOOTER_TOP - 0.015, 0.0]))

    # YouTube red circle
    yt_circ = Circle(
        radius=0.17,
        fill_color=mc(C_RRED), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([-6.35, fcy, 0.0]))
    yt_arrow = Text(
        "▶", font_size=10,
        color=mc(C_WHITE), font="Arial",
    ).move_to(yt_circ.get_center()).shift(RIGHT * 0.01)

    new_vid = Text(
        "NEW VIDEOS EVERY DAY",
        font_size=9, color=mc(C_WHITE), font="Arial",
    ).next_to(yt_circ, RIGHT, buff=0.10).align_to(yt_circ, DOWN).shift(UP * 0.02)

    # Subscribe text in gold (center-left)
    sub_txt = Text(
        "\U0001f514  SUBSCRIBE & TURN ON NOTIFICATIONS",
        font_size=10, color=mc(C_GOLD), font="Arial", weight=BOLD,
    ).move_to(np.array([0.9, fcy, 0.0]))

    # Channel handle right
    handle = Text(
        "@MathConceptMadeEasy",
        font_size=11, color=mc(C_LGRAY), font="Arial",
    ).move_to(np.array([5.65, fcy, 0.0]))

    grp = VGroup(bg_bar, top_line, yt_circ, yt_arrow,
                 new_vid, sub_txt, handle)
    grp.set_z_index(80)
    return grp


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — CARD PRIMITIVES
# ═════════════════════════════════════════════════════════════

def make_card(w=4.5, h=5.5, border_color=None, fill_color=None,
              corner_radius=0.15):
    """Rounded-rectangle content card."""
    bc = border_color or C_BLUE_P
    fc = fill_color   or C_CBG
    return RoundedRectangle(
        width=w, height=h,
        corner_radius=corner_radius,
        fill_color=mc(fc), fill_opacity=0.97,
        stroke_color=mc(bc), stroke_width=2.0,
    )


def make_card_header(text, width=4.5, color=None):
    """
    Colored header strip with bold white label.
    Returns a VGroup(strip, label).
    """
    col   = color or C_BLUE_P
    strip = RoundedRectangle(
        width=width, height=0.46,
        corner_radius=0.12,
        fill_color=mc(col), fill_opacity=1.0, stroke_width=0,
    )
    try:
        label = Text(
            str(text), font_size=14,
            color=mc(C_WHITE), font="Arial", weight=BOLD,
        )
    except Exception:
        label = Text("Header", font_size=14,
                     color=mc(C_WHITE), font="Arial", weight=BOLD)
    if label.width > width - 0.22:
        label.scale_to_fit_width(width - 0.22)
    label.move_to(strip.get_center())
    return VGroup(strip, label)


def make_formula_box(latex_str, width=5.2, height=1.8):
    """
    Purple-bordered card containing MathTex (or plain Text fallback).
    Returns VGroup(box, formula_mob).
    """
    box = RoundedRectangle(
        width=width, height=height,
        corner_radius=0.18,
        fill_color=mc(C_CBG), fill_opacity=1.0,
        stroke_color=mc(C_PURPLE), stroke_width=2.5,
    )
    try:
        fml = MathTex(str(latex_str), font_size=54, color=mc(C_WHITE))
        if fml.width > width - 0.45:
            fml.scale_to_fit_width(width - 0.45)
        if fml.height > height - 0.35:
            fml.scale_to_fit_height(height - 0.35)
    except Exception:
        fml = Text(
            str(latex_str)[:42], font_size=24,
            color=mc(C_WHITE), font="Arial",
        )
        if fml.width > width - 0.45:
            fml.scale_to_fit_width(width - 0.45)
    fml.move_to(box.get_center())
    return VGroup(box, fml)


def make_bullet_list(items, color=None, font_size=16, max_width=4.0):
    """VGroup of bullet-point Text mobs, arranged vertically."""
    col  = color or C_LGRAY
    mobs = []
    for item in items:
        try:
            t = Text(
                "•  " + str(item), font_size=font_size,
                color=mc(col), font="Arial",
            )
        except Exception:
            t = Text("•  item", font_size=font_size,
                     color=mc(col), font="Arial")
        if t.width > max_width:
            t.scale_to_fit_width(max_width)
        mobs.append(t)
    grp = VGroup(*mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
    return grp


def make_step_solution(steps, max_width=3.4):
    """
    Build solution step mobs (MathTex with Text fallback).
    Returns (grp, list_of_mobs) — first step in gold, last in green.
    """
    mobs = []
    n    = len(steps)
    for i, step in enumerate(steps):
        if i == 0:
            col = C_GOLD
        elif i == n - 1:
            col = C_GGREEN
        else:
            col = C_WHITE
        try:
            m = MathTex(str(step), font_size=26, color=mc(col))
        except Exception:
            m = Text(str(step)[:55], font_size=15,
                     color=mc(col), font="Arial")
        if m.width > max_width:
            m.scale_to_fit_width(max_width)
        mobs.append(m)
    grp = VGroup(*mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.20)
    if grp.width > max_width:
        grp.scale_to_fit_width(max_width)
    return grp, mobs


def make_takeaway_bar(items):
    """Four numbered takeaway cards in a horizontal row."""
    colors    = [C_BLUE_P, C_GGREEN, C_ORANGE, C_PURPLE]
    card_list = []
    for i, item in enumerate(items[:4]):
        col = colors[i % 4]

        tc_bg = RoundedRectangle(
            width=5.4, height=0.90,
            corner_radius=0.13,
            fill_color=mc(C_CBG), fill_opacity=1.0,
            stroke_color=mc(col), stroke_width=1.8,
        )
        # Number badge on left
        num_circ = Circle(
            radius=0.22,
            fill_color=mc(col), fill_opacity=1.0, stroke_width=0,
        )
        num_txt = Text(
            str(i + 1), font_size=15,
            color=mc(C_WHITE), font="Arial", weight=BOLD,
        )
        num_txt.move_to(num_circ.get_center())
        num_grp = VGroup(num_circ, num_txt)
        num_grp.move_to(tc_bg.get_left() + RIGHT * 0.36)

        try:
            item_txt = Text(
                str(item)[:42], font_size=13,
                color=mc(C_WHITE), font="Arial",
            )
        except Exception:
            item_txt = Text("Key takeaway", font_size=13,
                            color=mc(C_WHITE), font="Arial")
        if item_txt.width > 4.5:
            item_txt.scale_to_fit_width(4.5)
        item_txt.move_to(tc_bg.get_center() + RIGHT * 0.24)

        card_list.append(VGroup(tc_bg, num_grp, item_txt))

    row = VGroup(*card_list).arrange(RIGHT, buff=0.25)
    return row


# ═════════════════════════════════════════════════════════════
# SCENE 01 — OPENING  (channel intro, no standard header)
# ─────────────────────────────────────────────────────────────
# Top-left : logo circle + "Math Concept / Made Easy" + tagline
# Top-center: gold pill "LEARN • PRACTICE • MASTER"
# Top-right : purple DAY badge
# Center    : lesson title (2 lines: white / gold)
# Below     : blue subtitle bar
# Bottom    : 4 badge circles
# Footer    : standard footer bar
# ═════════════════════════════════════════════════════════════

class Scene01_Opening(Scene):
    def construct(self):
        sd  = get_scene_by_step("opening")
        dur = float(sd.get("duration_seconds", 20.0))
        attach_audio(self, sd.get("scene_id", 1))

        setup_bg(self)

        import numpy as np

        lesson_title = SCRIPT_DATA.get("title", "Today's Lesson")

        # ── Scattered faint math symbols ─────────────────────────────
        syms = ["+", "-", r"\times", r"\div", "=", r"\pi",
                r"\Sigma", "f(x)", r"\infty", r"\alpha"]
        rng2 = random.Random(77)
        for _ in range(16):
            sym = rng2.choice(syms)
            x   = rng2.uniform(-6.5, 6.5)
            y   = rng2.uniform(-3.6, 3.6)
            try:
                sm = MathTex(sym, font_size=rng2.randint(18, 36),
                             color=mc(C_BLUE_L))
            except Exception:
                sm = Text(sym, font_size=22, color=mc(C_BLUE_L), font="Arial")
            sm.move_to(np.array([x, y, 0]))
            sm.set_opacity(rng2.uniform(0.04, 0.11))
            sm.set_z_index(-50)
            self.add(sm)

        # ── Branding block (top-left) ─────────────────────────────────
        logo_circ = Circle(
            radius=0.40,
            fill_color=mc(C_GOLD), fill_opacity=1.0, stroke_width=0,
        )
        logo_m = Text("M", font_size=28, color=mc(C_NAVY1),
                      font="Arial", weight=BOLD)
        logo_m.move_to(logo_circ.get_center())
        logo_grp = VGroup(logo_circ, logo_m)

        ch_line1 = Text("Math Concept", font_size=22,
                        color=mc(C_WHITE), font="Arial", weight=BOLD)
        ch_line2 = Text("Made Easy", font_size=22,
                        color=mc(C_GOLD),  font="Arial", weight=BOLD)
        ch_stack = VGroup(ch_line1, ch_line2).arrange(
            DOWN, buff=0.04, aligned_edge=LEFT)

        tagline_sm = Text(TAGLINE, font_size=10,
                          color=mc(C_LGRAY), font="Arial")

        brand_col = VGroup(ch_stack, tagline_sm).arrange(
            DOWN, buff=0.08, aligned_edge=LEFT)
        brand_row = VGroup(logo_grp, brand_col).arrange(
            RIGHT, buff=0.18, aligned_edge=UP)
        brand_row.move_to(np.array([-4.65, 3.15, 0]))

        # ── "LEARN • PRACTICE • MASTER" pill (top-center) ────────────
        pill_bg = RoundedRectangle(
            width=4.6, height=0.50,
            corner_radius=0.25,
            fill_color=mc(C_GOLD), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, 3.38, 0]))
        pill_txt = Text(
            "LEARN  •  PRACTICE  •  MASTER",
            font_size=13, color=mc(C_NAVY1), font="Arial", weight=BOLD,
        ).move_to(pill_bg.get_center())
        pill_grp = VGroup(pill_bg, pill_txt)

        # ── DAY badge (top-right) ─────────────────────────────────────
        day_bg = RoundedRectangle(
            width=1.55, height=0.62,
            corner_radius=0.12,
            fill_color=mc(C_PURPLE), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([6.15, 3.30, 0]))
        day_txt = Text(
            "DAY " + str(LESSON_ID), font_size=19,
            color=mc(C_WHITE), font="Arial", weight=BOLD,
        ).move_to(day_bg.get_center())
        day_grp = VGroup(day_bg, day_txt)

        # ── Lesson title (two lines — white / gold) ───────────────────
        words = lesson_title.split()
        half  = max(1, len(words) // 2)
        l1_str = " ".join(words[:half])
        l2_str = " ".join(words[half:]) if len(words) > half else lesson_title

        try:
            title_l1 = Text(l1_str, font_size=62,
                            color=mc(C_WHITE), font="Arial", weight=BOLD)
        except Exception:
            title_l1 = Text("Today's", font_size=62,
                            color=mc(C_WHITE), font="Arial", weight=BOLD)
        if title_l1.width > 11.8:
            title_l1.scale_to_fit_width(11.8)

        try:
            title_l2 = Text(l2_str, font_size=62,
                            color=mc(C_GOLD), font="Arial", weight=BOLD)
        except Exception:
            title_l2 = Text("Lesson", font_size=62,
                            color=mc(C_GOLD), font="Arial", weight=BOLD)
        if title_l2.width > 11.8:
            title_l2.scale_to_fit_width(11.8)

        title_grp = VGroup(title_l1, title_l2).arrange(DOWN, buff=0.10)
        title_grp.move_to(np.array([0.0, 0.65, 0]))

        # ── Subtitle bar ─────────────────────────────────────────────
        subject  = SCRIPT_DATA.get("subject", "Mathematics")
        sub_bg   = RoundedRectangle(
            width=8.2, height=0.60, corner_radius=0.14,
            fill_color=mc(C_BLUE_P), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, -0.92, 0]))
        try:
            sub_txt = Text(str(subject), font_size=20,
                           color=mc(C_WHITE), font="Arial", weight=BOLD)
        except Exception:
            sub_txt = Text("Mathematics", font_size=20,
                           color=mc(C_WHITE), font="Arial", weight=BOLD)
        if sub_txt.width > 7.6:
            sub_txt.scale_to_fit_width(7.6)
        sub_txt.move_to(sub_bg.get_center())
        sub_grp = VGroup(sub_bg, sub_txt)

        # ── Four badge circles ────────────────────────────────────────
        badge_data = [
            ("\U0001f4a1", "EASY",    "EXPLANATIONS", C_BLUE_P),
            ("\U0001f3af", "CONCEPT", "CLARITY",      C_GGREEN),
            ("⚡",     "SMART",   "STRATEGIES",   C_ORANGE),
            ("\U0001f3c6", "BETTER",  "RESULTS",      C_PURPLE),
        ]
        badge_mobs = []
        for icon_ch, top_lbl, bot_lbl, col in badge_data:
            circ = Circle(
                radius=0.64,
                fill_color=mc(col), fill_opacity=0.16,
                stroke_color=mc(col), stroke_width=2.0,
            )
            try:
                icon_m = Text(icon_ch, font_size=22)
            except Exception:
                icon_m = Text("*", font_size=22, color=mc(col), font="Arial")
            icon_m.move_to(circ.get_center() + UP * 0.19)
            top_m = Text(top_lbl, font_size=11, color=mc(col),
                         font="Arial", weight=BOLD)
            top_m.move_to(circ.get_center() + DOWN * 0.12)
            bot_m = Text(bot_lbl, font_size=9, color=mc(C_LGRAY), font="Arial")
            bot_m.move_to(circ.get_center() + DOWN * 0.28)
            badge_mobs.append(VGroup(circ, icon_m, top_m, bot_m))

        badges_row = VGroup(*badge_mobs).arrange(RIGHT, buff=0.52)
        badges_row.move_to(np.array([0.0, -2.55, 0]))

        # ── Footer ───────────────────────────────────────────────────
        footer = make_footer()
        self.add(footer)

        # ── Animate ──────────────────────────────────────────────────
        ta = 0.0   # total animation time accumulated

        self.play(FadeIn(brand_row, shift=DOWN * 0.12), run_time=0.65)
        ta += 0.65
        self.play(FadeIn(pill_grp, shift=DOWN * 0.08), run_time=0.50)
        ta += 0.50
        self.play(FadeIn(day_grp,  shift=LEFT * 0.08), run_time=0.40)
        ta += 0.40
        self.play(Write(title_l1),  run_time=0.85)
        ta += 0.85
        self.play(Write(title_l2),  run_time=0.85)
        ta += 0.85
        self.play(FadeIn(sub_grp,  shift=UP * 0.08), run_time=0.50)
        ta += 0.50
        self.play(
            LaggedStart(*[FadeIn(b, shift=UP * 0.14) for b in badge_mobs],
                        lag_ratio=0.22),
            run_time=1.00,
        )
        ta += 1.00

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 1))


# ═════════════════════════════════════════════════════════════
# SCENE 02 — HOOK
# ─────────────────────────────────────────────────────────────
# Orange "DID YOU KNOW?" pill at top-center.
# Large centered card (9 × 3.5) with hook text.
# "?" icon on the left side of the card.
# ═════════════════════════════════════════════════════════════

class Scene02_Hook(Scene):
    def construct(self):
        sd  = get_scene_by_step("hook")
        dur = float(sd.get("duration_seconds", 20.0))
        attach_audio(self, sd.get("scene_id", 2))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        header = make_header(lesson_title, LESSON_ID)
        footer = make_footer()
        self.add(header, footer)

        import numpy as np
        narration  = sd.get("narration", "")
        hook_text  = sd.get("real_world_hook", narration) or narration

        content_cy = (CONTENT_TOP + CONTENT_BOT) / 2   # -0.25

        # ── "DID YOU KNOW?" pill ──────────────────────────────────────
        pill_bg = RoundedRectangle(
            width=4.3, height=0.52, corner_radius=0.26,
            fill_color=mc(C_ORANGE), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, CONTENT_TOP - 0.45, 0]))
        pill_txt = Text(
            "DID YOU KNOW?", font_size=18,
            color=mc(C_WHITE), font="Arial", weight=BOLD,
        ).move_to(pill_bg.get_center())
        pill_grp = VGroup(pill_bg, pill_txt)

        # ── Main hook card ────────────────────────────────────────────
        card = make_card(9.2, 3.6, border_color=C_ORANGE, fill_color=C_CBG)
        card.move_to(np.array([0.4, content_cy - 0.2, 0]))

        # "?" bubble on the left
        q_circ = Circle(
            radius=0.52,
            fill_color=mc(C_ORANGE), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([-4.05, content_cy - 0.2, 0]))
        q_icon = Text("?", font_size=38, color=mc(C_WHITE),
                      font="Arial", weight=BOLD)
        q_icon.move_to(q_circ.get_center())
        q_grp = VGroup(q_circ, q_icon)

        # Hook text — split into lines
        lines = textwrap.wrap(str(hook_text), 62)[:5]
        if not lines:
            lines = ["Hook content will appear here."]
        line_mobs = []
        for ln in lines:
            try:
                t = Text(ln, font_size=21, color=mc(C_WHITE), font="Arial")
            except Exception:
                t = Text(ln[:60], font_size=21, color=mc(C_WHITE), font="Arial")
            if t.width > 7.9:
                t.scale_to_fit_width(7.9)
            line_mobs.append(t)
        text_grp = VGroup(*line_mobs).arrange(
            DOWN, buff=0.22, aligned_edge=LEFT)
        if text_grp.height > 3.2:
            text_grp.scale_to_fit_height(3.2)
        text_grp.move_to(np.array([0.55, content_cy - 0.2, 0]))

        # ── Animate ──────────────────────────────────────────────────
        ta = 0.0
        self.play(FadeIn(pill_grp, shift=DOWN * 0.10), run_time=0.55)
        ta += 0.55
        self.play(FadeIn(card),               run_time=0.40)
        ta += 0.40
        self.play(FadeIn(q_grp, scale=0.80),  run_time=0.45)
        ta += 0.45
        for lm in line_mobs:
            self.play(FadeIn(lm, shift=RIGHT * 0.10), run_time=0.42)
            ta += 0.42

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 2))


# ═════════════════════════════════════════════════════════════
# SCENE 03 — CONCEPT  (three-panel layout)
# ─────────────────────────────────────────────────────────────
# Left  (30 %) : "WHAT IS [TOPIC]?" — bullet sentences  (blue)
# Center(40 %) : "CONCEPT INTUITION" — explanation text (green)
# Right (30 %) : "KEY TERMS"         — keyword pills    (orange)
# Vertical dividers at x = ±1.9
# ═════════════════════════════════════════════════════════════

class Scene03_Concept(Scene):
    def construct(self):
        sd  = get_scene_by_step("concept")
        dur = float(sd.get("duration_seconds", 22.0))
        attach_audio(self, sd.get("scene_id", 3))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        header = make_header(lesson_title, LESSON_ID)
        footer = make_footer()
        self.add(header, footer)

        import numpy as np
        narration   = sd.get("narration", "")
        concept_int = sd.get("concept_intuition", narration)
        topic       = SCRIPT_DATA.get("topic", lesson_title)

        content_cy = (CONTENT_TOP + CONTENT_BOT) / 2   # -0.25
        content_h  = CONTENT_TOP - CONTENT_BOT          #  6.00
        card_h     = content_h - 0.22                   #  5.78

        left_w   = 4.5
        center_w = 3.8
        right_w  = 4.5

        # ── Three cards ───────────────────────────────────────────────
        left_card = make_card(left_w,   card_h, border_color=C_BLUE_P)
        left_card.move_to(np.array([-4.80, content_cy, 0]))

        center_card = make_card(center_w, card_h, border_color=C_GGREEN)
        center_card.move_to(np.array([0.00, content_cy, 0]))

        right_card = make_card(right_w,  card_h, border_color=C_ORANGE)
        right_card.move_to(np.array([4.80, content_cy, 0]))

        # ── Left: "WHAT IS [TOPIC]?" + bullets ───────────────────────
        l_hdr_str = "WHAT IS " + str(topic).upper()[:20] + "?"
        l_hdr = make_card_header(l_hdr_str, left_w, C_BLUE_P)
        l_hdr.move_to(
            left_card.get_top() + DOWN * (l_hdr.height / 2 + 0.07))

        sentences = [s.strip() for s in
                     re.split(r'[.!?]', str(narration)) if len(s.strip()) > 8][:5]
        if not sentences:
            sentences = ["Core concept explained here.",
                         "Study this definition.", "Apply to problems."]
        l_bullets = make_bullet_list(sentences, C_LGRAY,
                                     font_size=15, max_width=left_w - 0.38)
        if l_bullets.height > card_h - 0.80:
            l_bullets.scale_to_fit_height(card_h - 0.80)
        l_bullets.move_to(left_card.get_center() + DOWN * 0.22)
        l_bullets.align_to(left_card.get_left() + RIGHT * 0.22, LEFT)

        # ── Center: "CONCEPT INTUITION" + explanation ─────────────────
        c_hdr = make_card_header("CONCEPT INTUITION", center_w, C_GGREEN)
        c_hdr.move_to(
            center_card.get_top() + DOWN * (c_hdr.height / 2 + 0.07))

        int_lines = textwrap.wrap(str(concept_int), 32)[:9]
        if not int_lines:
            int_lines = ["Intuitive explanation here."]
        c_mobs = []
        for ln in int_lines:
            try:
                t = Text(ln, font_size=14, color=mc(C_LGRAY), font="Arial")
            except Exception:
                t = Text(ln[:30], font_size=14, color=mc(C_LGRAY), font="Arial")
            if t.width > center_w - 0.28:
                t.scale_to_fit_width(center_w - 0.28)
            c_mobs.append(t)
        c_grp = VGroup(*c_mobs).arrange(
            DOWN, buff=0.14, aligned_edge=LEFT)
        if c_grp.height > card_h - 0.80:
            c_grp.scale_to_fit_height(card_h - 0.80)
        c_grp.move_to(center_card.get_center() + DOWN * 0.22)

        # ── Right: "KEY TERMS" + keyword pills ────────────────────────
        r_hdr = make_card_header("KEY TERMS", right_w, C_ORANGE)
        r_hdr.move_to(
            right_card.get_top() + DOWN * (r_hdr.height / 2 + 0.07))

        keywords = SCRIPT_DATA.get("keywords", [])
        if not keywords:
            kw_raw  = SCRIPT_DATA.get("key_terms", "")
            keywords = [k.strip() for k in str(kw_raw).split(",")
                        if k.strip()][:7]
        if not keywords:
            keywords = [str(topic), "Definition", "Formula", "Application"]

        pill_mobs = []
        for kw in keywords[:8]:
            kw_str   = str(kw)[:24]
            pill_w   = min(right_w - 0.38, max(1.4, len(kw_str) * 0.13 + 0.55))
            p_bg = RoundedRectangle(
                width=pill_w, height=0.38, corner_radius=0.10,
                fill_color=mc(C_CBG), fill_opacity=1.0,
                stroke_color=mc(C_GOLD), stroke_width=1.4,
            )
            try:
                p_txt = Text(kw_str, font_size=12,
                             color=mc(C_GOLD), font="Arial", weight=BOLD)
            except Exception:
                p_txt = Text("term", font_size=12,
                             color=mc(C_GOLD), font="Arial", weight=BOLD)
            if p_txt.width > pill_w - 0.14:
                p_txt.scale_to_fit_width(pill_w - 0.14)
            p_txt.move_to(p_bg.get_center())
            pill_mobs.append(VGroup(p_bg, p_txt))

        r_pills = VGroup(*pill_mobs).arrange(
            DOWN, aligned_edge=LEFT, buff=0.13)
        if r_pills.width > right_w - 0.34:
            r_pills.scale_to_fit_width(right_w - 0.34)
        if r_pills.height > card_h - 0.80:
            r_pills.scale_to_fit_height(card_h - 0.80)
        r_pills.move_to(right_card.get_center() + DOWN * 0.22)
        r_pills.align_to(right_card.get_left() + RIGHT * 0.22, LEFT)

        # ── Vertical dividers ──────────────────────────────────────────
        div_l = Line(
            np.array([-1.90, CONTENT_TOP - 0.12, 0]),
            np.array([-1.90, CONTENT_BOT + 0.12, 0]),
            stroke_width=1.0, color=mc(C_SECOND),
        ).set_stroke(opacity=0.38)
        div_r = Line(
            np.array([ 1.90, CONTENT_TOP - 0.12, 0]),
            np.array([ 1.90, CONTENT_BOT + 0.12, 0]),
            stroke_width=1.0, color=mc(C_SECOND),
        ).set_stroke(opacity=0.38)

        # ── Animate ───────────────────────────────────────────────────
        ta = 0.0
        self.play(
            FadeIn(left_card), FadeIn(center_card), FadeIn(right_card),
            run_time=0.60,
        )
        ta += 0.60
        self.play(Create(div_l), Create(div_r), run_time=0.30)
        ta += 0.30
        self.play(
            FadeIn(l_hdr), FadeIn(c_hdr), FadeIn(r_hdr),
            run_time=0.45,
        )
        ta += 0.45
        if l_bullets:
            self.play(
                LaggedStart(*[FadeIn(b, shift=RIGHT * 0.07) for b in l_bullets],
                            lag_ratio=0.18),
                run_time=0.85,
            )
            ta += 0.85
        if c_grp:
            self.play(FadeIn(c_grp, shift=UP * 0.06), run_time=0.65)
            ta += 0.65
        if pill_mobs:
            self.play(
                LaggedStart(*[FadeIn(p, scale=0.85) for p in pill_mobs],
                            lag_ratio=0.14),
                run_time=0.75,
            )
            ta += 0.75

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 3))


# ═════════════════════════════════════════════════════════════
# SCENE 04 — DEFINITION
# ─────────────────────────────────────────────────────────────
# Large centered definition card (8.5 × 4.0) with blue header.
# Narration text inside card (wrapped, 3–4 lines).
# Two small cards below: orange "Prerequisite" / green "Goal".
# ═════════════════════════════════════════════════════════════

class Scene04_Definition(Scene):
    def construct(self):
        sd  = get_scene_by_step("definition")
        dur = float(sd.get("duration_seconds", 18.0))
        attach_audio(self, sd.get("scene_id", 4))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        header = make_header(lesson_title, LESSON_ID)
        footer = make_footer()
        self.add(header, footer)

        import numpy as np
        narration = sd.get("narration", "")
        topic     = SCRIPT_DATA.get("topic", lesson_title)

        # ── Large definition card ──────────────────────────────────────
        def_card = make_card(8.5, 4.00, border_color=C_BLUE_P)
        def_card.move_to(np.array([0.0, 0.42, 0]))

        hdr_str = "DEFINITION: " + str(topic).upper()[:30]
        def_hdr = make_card_header(hdr_str, 8.5, C_BLUE_P)
        def_hdr.move_to(
            def_card.get_top() + DOWN * (def_hdr.height / 2 + 0.07))

        nar_lines = textwrap.wrap(str(narration), 70)[:4]
        if not nar_lines:
            nar_lines = ["The formal definition will appear here."]
        nar_mobs = []
        for ln in nar_lines:
            try:
                t = Text(ln, font_size=19, color=mc(C_WHITE), font="Arial")
            except Exception:
                t = Text(ln[:68], font_size=19, color=mc(C_WHITE), font="Arial")
            if t.width > 7.8:
                t.scale_to_fit_width(7.8)
            nar_mobs.append(t)
        nar_grp = VGroup(*nar_mobs).arrange(
            DOWN, buff=0.22, aligned_edge=LEFT)
        if nar_grp.height > 2.9:
            nar_grp.scale_to_fit_height(2.9)
        nar_grp.move_to(def_card.get_center() + DOWN * 0.14)

        # ── Two small cards below ──────────────────────────────────────
        prereq = SCRIPT_DATA.get("prerequisite", "Basic arithmetic and number sense.")
        goal   = SCRIPT_DATA.get("lesson_goal",  "Understand and apply this concept.")

        pre_card = make_card(4.1, 1.05, border_color=C_ORANGE)
        pre_card.move_to(np.array([-2.35, -2.20, 0]))
        pre_hdr = make_card_header("Prerequisite:", 4.1, C_ORANGE)
        pre_hdr.move_to(
            pre_card.get_top() + DOWN * (pre_hdr.height / 2 + 0.07))
        try:
            pre_txt = Text(str(prereq)[:50], font_size=12,
                           color=mc(C_LGRAY), font="Arial")
        except Exception:
            pre_txt = Text("Basic concepts", font_size=12,
                           color=mc(C_LGRAY), font="Arial")
        if pre_txt.width > 3.6:
            pre_txt.scale_to_fit_width(3.6)
        pre_txt.move_to(pre_card.get_center() + DOWN * 0.08)

        goal_card = make_card(4.1, 1.05, border_color=C_GGREEN)
        goal_card.move_to(np.array([2.35, -2.20, 0]))
        goal_hdr = make_card_header("Goal:", 4.1, C_GGREEN)
        goal_hdr.move_to(
            goal_card.get_top() + DOWN * (goal_hdr.height / 2 + 0.07))
        try:
            goal_txt = Text(str(goal)[:50], font_size=12,
                            color=mc(C_LGRAY), font="Arial")
        except Exception:
            goal_txt = Text("Learn the concept", font_size=12,
                            color=mc(C_LGRAY), font="Arial")
        if goal_txt.width > 3.6:
            goal_txt.scale_to_fit_width(3.6)
        goal_txt.move_to(goal_card.get_center() + DOWN * 0.08)

        # ── Animate ───────────────────────────────────────────────────
        ta = 0.0
        self.play(FadeIn(def_card), run_time=0.50)
        ta += 0.50
        self.play(FadeIn(def_hdr),  run_time=0.40)
        ta += 0.40
        for nm in nar_mobs:
            self.play(FadeIn(nm, shift=RIGHT * 0.08), run_time=0.48)
            ta += 0.48
        self.play(
            FadeIn(pre_card), FadeIn(goal_card),
            run_time=0.48,
        )
        ta += 0.48
        self.play(
            FadeIn(pre_hdr), FadeIn(goal_hdr),
            FadeIn(pre_txt), FadeIn(goal_txt),
            run_time=0.45,
        )
        ta += 0.45

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 4))


# ═════════════════════════════════════════════════════════════
# SCENE 05 — FORMULA  (three-panel layout)
# ─────────────────────────────────────────────────────────────
# Left  : purple "THE FORMULA" — formula_spoken parts as bullets
# Center: purple label + large formula_box (MathTex)
# Right : orange "VARIABLES" — variable key-value pairs
# Circumscribe formula box at the end.
# ═════════════════════════════════════════════════════════════

class Scene05_Formula(Scene):
    def construct(self):
        sd  = get_scene_by_step("formula")
        dur = float(sd.get("duration_seconds", 20.0))
        attach_audio(self, sd.get("scene_id", 5))

        lesson_title   = SCRIPT_DATA.get("title", "")
        formula_latex  = SCRIPT_DATA.get("key_formula",    "")
        formula_spoken = SCRIPT_DATA.get("formula_spoken", "")

        setup_bg(self)
        header = make_header(lesson_title, LESSON_ID)
        footer = make_footer()
        self.add(header, footer)

        import numpy as np
        content_cy = (CONTENT_TOP + CONTENT_BOT) / 2
        content_h  = CONTENT_TOP - CONTENT_BOT
        card_h     = content_h - 0.25

        # ── Left card: formula introduction ───────────────────────────
        left_card = make_card(4.5, card_h, border_color=C_PURPLE)
        left_card.move_to(np.array([-4.80, content_cy, 0]))

        l_hdr = make_card_header("\U0001f4a1  THE FORMULA", 4.5, C_PURPLE)
        l_hdr.move_to(
            left_card.get_top() + DOWN * (l_hdr.height / 2 + 0.07))

        narration    = sd.get("narration", formula_spoken)
        spoken_parts = [p.strip()
                        for p in str(narration).split(",") if p.strip()][:7]
        if not spoken_parts:
            spoken_parts = ["Apply this formula", "step by step",
                            "to every problem."]
        left_w = 4.5 - 0.40
        l_bullets = make_bullet_list(spoken_parts, C_LGRAY,
                                     font_size=14, max_width=left_w)
        if l_bullets.height > card_h - 0.82:
            l_bullets.scale_to_fit_height(card_h - 0.82)
        l_bullets.move_to(left_card.get_center() + DOWN * 0.22)
        l_bullets.align_to(left_card.get_left() + RIGHT * 0.22, LEFT)

        # ── Center: label + formula box + spoken text below ───────────
        center_lbl = Text(
            "THE FORMULA", font_size=20,
            color=mc(C_PURPLE), font="Arial", weight=BOLD,
        ).move_to(np.array([0.0, CONTENT_TOP - 0.48, 0]))

        formula_box = make_formula_box(str(formula_latex), width=5.4, height=2.10)
        formula_box.move_to(np.array([0.0, content_cy + 0.35, 0]))

        var_lines = textwrap.wrap(str(formula_spoken), 36)[:4]
        v_mobs = []
        for ln in var_lines:
            try:
                t = Text(ln, font_size=15, color=mc(C_LGRAY), font="Arial")
            except Exception:
                t = Text(ln[:34], font_size=15, color=mc(C_LGRAY), font="Arial")
            if t.width > 5.5:
                t.scale_to_fit_width(5.5)
            v_mobs.append(t)
        var_grp = VGroup(*v_mobs).arrange(
            DOWN, buff=0.14, aligned_edge=LEFT) if v_mobs else VGroup()
        if var_grp.height > 2.0:
            var_grp.scale_to_fit_height(2.0)
        var_grp.next_to(formula_box, DOWN, buff=0.32)
        var_grp.move_to(np.array([0.0, var_grp.get_center()[1], 0]))

        # ── Right card: variable breakdown ────────────────────────────
        right_card = make_card(4.5, card_h, border_color=C_ORANGE)
        right_card.move_to(np.array([4.80, content_cy, 0]))

        r_hdr = make_card_header("⚡  VARIABLES", 4.5, C_ORANGE)
        r_hdr.move_to(
            right_card.get_top() + DOWN * (r_hdr.height / 2 + 0.07))

        board      = sd.get("board_examples", {})
        var_pairs  = board.get("worked_example", [])[:6]
        if not var_pairs:
            var_pairs = SCRIPT_DATA.get("keywords", [])[:6]
        if not var_pairs:
            var_pairs = ["Variable: see definition",
                         "Apply to formula", "Check conditions"]

        alt_cols = [C_GOLD, C_WHITE, C_GOLD, C_WHITE, C_GOLD, C_WHITE]
        r_var_mobs = []
        for i, vp in enumerate(var_pairs):
            col = alt_cols[i % len(alt_cols)]
            try:
                t = Text(str(vp)[:44], font_size=15, color=mc(col), font="Arial")
            except Exception:
                t = Text("term", font_size=15, color=mc(col), font="Arial")
            if t.width > 3.9:
                t.scale_to_fit_width(3.9)
            r_var_mobs.append(t)
        r_var_grp = VGroup(*r_var_mobs).arrange(
            DOWN, aligned_edge=LEFT, buff=0.22)
        if r_var_grp.height > card_h - 0.82:
            r_var_grp.scale_to_fit_height(card_h - 0.82)
        r_var_grp.move_to(right_card.get_center() + DOWN * 0.22)
        r_var_grp.align_to(right_card.get_left() + RIGHT * 0.22, LEFT)

        # ── Dividers ──────────────────────────────────────────────────
        div_l = Line(
            np.array([-1.90, CONTENT_TOP - 0.12, 0]),
            np.array([-1.90, CONTENT_BOT + 0.12, 0]),
            stroke_width=1.0, color=mc(C_SECOND),
        ).set_stroke(opacity=0.35)
        div_r = Line(
            np.array([ 1.90, CONTENT_TOP - 0.12, 0]),
            np.array([ 1.90, CONTENT_BOT + 0.12, 0]),
            stroke_width=1.0, color=mc(C_SECOND),
        ).set_stroke(opacity=0.35)

        # ── Animate ───────────────────────────────────────────────────
        ta = 0.0
        self.play(
            FadeIn(left_card), FadeIn(right_card),
            Create(div_l), Create(div_r),
            run_time=0.60,
        )
        ta += 0.60
        self.play(FadeIn(l_hdr), FadeIn(r_hdr), run_time=0.40)
        ta += 0.40
        self.play(FadeIn(l_bullets, shift=RIGHT * 0.05), run_time=0.60)
        ta += 0.60
        self.play(FadeIn(center_lbl, shift=DOWN * 0.08), run_time=0.38)
        ta += 0.38
        self.play(FadeIn(formula_box[0]), run_time=0.38)
        ta += 0.38
        self.play(Write(formula_box[1]), run_time=0.90)
        ta += 0.90
        if var_grp:
            self.play(FadeIn(var_grp), run_time=0.48)
            ta += 0.48
        self.play(
            LaggedStart(*[FadeIn(m, shift=RIGHT * 0.07) for m in r_var_mobs],
                        lag_ratio=0.18),
            run_time=0.80,
        )
        ta += 0.80

        # Circumscribe at the end
        pause = max(0.3, dur - ta - 1.60)
        self.wait(pause)
        ta += pause
        try:
            self.play(
                Circumscribe(formula_box, color=mc(C_GOLD), run_time=1.20),
            )
            ta += 1.20
        except Exception:
            pass

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 5))


# ═════════════════════════════════════════════════════════════
# SCENE 06 — WORKED EXAMPLE  (three-panel)
# ─────────────────────────────────────────────────────────────
# Left  : blue  "EXAMPLE 1"  — question text + calc icon
# Center: green "SOLUTION"   — steps one-by-one + answer box + Flash
# Right : blue  "CONCLUSION" — concept_intuition text
# ═════════════════════════════════════════════════════════════

class Scene06_WorkedExample(Scene):
    def construct(self):
        sd  = get_scene_by_step("worked_example")
        dur = float(sd.get("duration_seconds", 24.0))
        attach_audio(self, sd.get("scene_id", 6))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        header = make_header(lesson_title, LESSON_ID)
        footer = make_footer()
        self.add(header, footer)

        import numpy as np
        board       = sd.get("board_examples", {})
        steps       = board.get("worked_example", [])
        practice_q  = (board.get("practice",   [""])[0]
                       if board.get("practice") else "")
        concept_int = sd.get("concept_intuition",
                             sd.get("narration", ""))

        if not steps:
            steps = [
                r"\text{Step 1: Read the problem}",
                r"\text{Step 2: Apply the formula}",
                r"\text{Step 3: Simplify}",
                r"\text{Answer verified}",
            ]

        content_cy = (CONTENT_TOP + CONTENT_BOT) / 2
        content_h  = CONTENT_TOP - CONTENT_BOT
        card_h     = content_h - 0.25

        # ── Left card — question ──────────────────────────────────────
        left_card = make_card(4.5, card_h, border_color=C_BLUE_P)
        left_card.move_to(np.array([-4.80, content_cy, 0]))
        l_hdr = make_card_header("★  EXAMPLE 1", 4.5, C_BLUE_P)
        l_hdr.move_to(
            left_card.get_top() + DOWN * (l_hdr.height / 2 + 0.07))

        q_raw   = (str(practice_q)
                   or str(sd.get("narration", "Solve using the formula."))[:90])
        q_lines = textwrap.wrap(q_raw, 30)[:5]
        q_mobs  = []
        for ln in q_lines:
            try:
                t = Text(ln, font_size=15, color=mc(C_WHITE), font="Arial")
            except Exception:
                t = Text(ln[:28], font_size=15, color=mc(C_WHITE), font="Arial")
            if t.width > 3.90:
                t.scale_to_fit_width(3.90)
            q_mobs.append(t)
        q_grp = VGroup(*q_mobs).arrange(
            DOWN, buff=0.15, aligned_edge=LEFT)
        q_grp.move_to(left_card.get_center() + UP * 0.30)
        q_grp.align_to(left_card.get_left() + RIGHT * 0.20, LEFT)

        # Calculator emoji box at bottom-left card
        calc_bg = RoundedRectangle(
            width=1.65, height=0.55, corner_radius=0.10,
            fill_color=mc(C_NAVY2), fill_opacity=1.0,
            stroke_color=mc(C_BLUE_L), stroke_width=1.4,
        )
        try:
            calc_icon = Text("\U0001f5a9", font_size=22)
        except Exception:
            calc_icon = Text("=", font_size=22,
                             color=mc(C_GOLD), font="Arial", weight=BOLD)
        calc_icon.move_to(calc_bg.get_center())
        calc_grp = VGroup(calc_bg, calc_icon)
        calc_grp.move_to(left_card.get_bottom() + UP * 0.44)

        # ── Center card — solution steps ──────────────────────────────
        center_card = make_card(3.8, card_h, border_color=C_GGREEN)
        center_card.move_to(np.array([0.00, content_cy, 0]))
        c_hdr = make_card_header("SOLUTION", 3.8, C_GGREEN)
        c_hdr.move_to(
            center_card.get_top() + DOWN * (c_hdr.height / 2 + 0.07))

        _, step_mobs = make_step_solution(steps, max_width=3.35)
        # Re-arrange vertically with spacing
        sol_grp = VGroup(*step_mobs).arrange(
            DOWN, aligned_edge=LEFT, buff=0.18)
        avail_h = card_h - 1.55
        if sol_grp.height > avail_h:
            sol_grp.scale_to_fit_height(avail_h)
        if sol_grp.width > 3.35:
            sol_grp.scale_to_fit_width(3.35)
        sol_grp.move_to(center_card.get_center() + DOWN * 0.30)
        sol_grp.align_to(center_card.get_left() + RIGHT * 0.22, LEFT)

        # Green answer box at bottom-center
        ans_bg = RoundedRectangle(
            width=3.30, height=0.48, corner_radius=0.10,
            fill_color=mc(C_GGREEN), fill_opacity=0.22,
            stroke_color=mc(C_GGREEN), stroke_width=2.0,
        )
        ans_lbl = Text(
            "ANSWER", font_size=13,
            color=mc(C_GGREEN), font="Arial", weight=BOLD,
        ).move_to(ans_bg.get_center())
        ans_grp = VGroup(ans_bg, ans_lbl)
        ans_grp.move_to(center_card.get_bottom() + UP * 0.42)

        # ── Right card — conclusion ────────────────────────────────────
        right_card = make_card(4.5, card_h, border_color=C_BLUE_P)
        right_card.move_to(np.array([4.80, content_cy, 0]))
        r_hdr = make_card_header("CONCLUSION", 4.5, C_BLUE_P)
        r_hdr.move_to(
            right_card.get_top() + DOWN * (r_hdr.height / 2 + 0.07))

        conc_lines = textwrap.wrap(str(concept_int), 32)[:7]
        if not conc_lines:
            conc_lines = ["Apply this concept widely.",
                          "Practice regularly.",
                          "You can do this!"]
        conc_mobs = []
        for ln in conc_lines:
            try:
                t = Text(ln, font_size=15, color=mc(C_LGRAY), font="Arial")
            except Exception:
                t = Text(ln[:30], font_size=15, color=mc(C_LGRAY), font="Arial")
            if t.width > 3.90:
                t.scale_to_fit_width(3.90)
            conc_mobs.append(t)
        conc_grp = VGroup(*conc_mobs).arrange(
            DOWN, buff=0.18, aligned_edge=LEFT)
        if conc_grp.height > card_h - 0.82:
            conc_grp.scale_to_fit_height(card_h - 0.82)
        conc_grp.move_to(right_card.get_center() + DOWN * 0.22)
        conc_grp.align_to(right_card.get_left() + RIGHT * 0.22, LEFT)

        # ── Dividers ──────────────────────────────────────────────────
        div_l = Line(
            np.array([-1.90, CONTENT_TOP - 0.12, 0]),
            np.array([-1.90, CONTENT_BOT + 0.12, 0]),
            stroke_width=1.0, color=mc(C_SECOND),
        ).set_stroke(opacity=0.35)
        div_r = Line(
            np.array([ 1.90, CONTENT_TOP - 0.12, 0]),
            np.array([ 1.90, CONTENT_BOT + 0.12, 0]),
            stroke_width=1.0, color=mc(C_SECOND),
        ).set_stroke(opacity=0.35)

        # ── Animate ───────────────────────────────────────────────────
        ta = 0.0
        self.play(
            FadeIn(left_card), FadeIn(center_card), FadeIn(right_card),
            Create(div_l), Create(div_r),
            run_time=0.60,
        )
        ta += 0.60
        self.play(FadeIn(l_hdr), FadeIn(c_hdr), FadeIn(r_hdr), run_time=0.40)
        ta += 0.40

        # Left: question
        for qm in q_mobs:
            self.play(FadeIn(qm, shift=RIGHT * 0.06), run_time=0.30)
            ta += 0.30
        self.play(FadeIn(calc_grp, scale=0.85), run_time=0.32)
        ta += 0.32

        # Center: steps one by one
        per_step = max(0.40, (dur - ta - 2.80) / max(len(step_mobs), 1))
        for m in step_mobs:
            write_t = min(0.60, per_step * 0.70)
            self.play(Write(m), run_time=write_t)
            ta += write_t
            gap = max(0.05, per_step - write_t)
            self.wait(gap)
            ta += gap

        # Answer reveal + Flash
        self.play(FadeIn(ans_grp), run_time=0.38)
        ta += 0.38
        try:
            self.play(
                Flash(ans_bg, color=mc(C_GGREEN),
                      line_length=0.20, num_lines=12, flash_radius=0.55),
                run_time=0.60,
            )
            ta += 0.60
        except Exception:
            pass

        # Right: conclusion
        self.play(
            LaggedStart(*[FadeIn(m, shift=LEFT * 0.06) for m in conc_mobs],
                        lag_ratio=0.18),
            run_time=0.68,
        )
        ta += 0.68

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 6))


# ═════════════════════════════════════════════════════════════
# SCENE 07 — MISTAKES  (two-panel comparison)
# ─────────────────────────────────────────────────────────────
# Red warning banner at top of content area.
# Left panel  (red border) : "THE WRONG WAY" + wrong steps + ✗
# Right panel (green border): "THE RIGHT WAY" + right steps + ✓
# "VS" in gold between panels.
# Green glow on right panel at the end.
# ═════════════════════════════════════════════════════════════

class Scene07_Mistakes(Scene):
    def construct(self):
        sd  = get_scene_by_step("mistakes")
        dur = float(sd.get("duration_seconds", 22.0))
        attach_audio(self, sd.get("scene_id", 7))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        header = make_header(lesson_title, LESSON_ID)
        footer = make_footer()
        self.add(header, footer)

        import numpy as np
        board     = sd.get("board_examples", {})
        narration = sd.get("narration", "")
        cm        = SCRIPT_DATA.get("common_mistake", "")

        # Classify steps into wrong / right
        raw_steps   = board.get("worked_example", [])
        wrong_steps = []
        right_steps = []
        for s in raw_steps:
            st = str(s)
            if any(k in st for k in ["Wrong", "Mistake", "WRONG",
                                     "✗", "incorrect", "error"]):
                wrong_steps.append(st)
            elif any(k in st for k in ["Correct", "RIGHT", "✓",
                                       "right", "checkmark", "Fix"]):
                right_steps.append(st)
            else:
                if len(wrong_steps) <= len(right_steps):
                    wrong_steps.append(st)
                else:
                    right_steps.append(st)

        if not wrong_steps:
            cm_s = str(cm)[:50] or "Skipping the key condition"
            wrong_steps = [
                r"\text{" + cm_s + r"}",
                r"\text{Result: incorrect answer}",
            ]
        if not right_steps:
            right_steps = [
                r"\text{Always check conditions first}",
                r"\text{Apply the formula step by step}",
                r"\text{Verify your final answer}",
            ]

        content_cy = (CONTENT_TOP + CONTENT_BOT) / 2
        content_h  = CONTENT_TOP - CONTENT_BOT

        # ── Red warning banner ─────────────────────────────────────────
        warn_bg = RoundedRectangle(
            width=11.2, height=0.56, corner_radius=0.10,
            fill_color=mc(C_RRED), fill_opacity=0.90, stroke_width=0,
        ).move_to(np.array([0.0, CONTENT_TOP - 0.42, 0]))
        warn_txt = Text(
            "⚠️  COMMON MISTAKE  —  DON'T DO THIS!",
            font_size=18, color=mc(C_WHITE), font="Arial", weight=BOLD,
        ).move_to(warn_bg.get_center())
        warn_grp = VGroup(warn_bg, warn_txt)

        # ── Two comparison panels ──────────────────────────────────────
        panel_h  = content_h - 1.40
        panel_cy = content_cy - 0.32

        left_card = make_card(5.65, panel_h, border_color=C_RRED)
        left_card.move_to(np.array([-3.25, panel_cy, 0]))
        l_hdr = make_card_header("✗  THE WRONG WAY", 5.65, C_RRED)
        l_hdr.move_to(
            left_card.get_top() + DOWN * (l_hdr.height / 2 + 0.07))

        right_card = make_card(5.65, panel_h, border_color=C_GGREEN)
        right_card.move_to(np.array([3.25, panel_cy, 0]))
        r_hdr = make_card_header("✓  THE RIGHT WAY", 5.65, C_GGREEN)
        r_hdr.move_to(
            right_card.get_top() + DOWN * (r_hdr.height / 2 + 0.07))

        # Wrong mobs
        wrong_mobs = []
        for txt in wrong_steps[:4]:
            try:
                m = MathTex(str(txt), font_size=24, color=mc(C_RRED))
            except Exception:
                m = Text(str(txt)[:52], font_size=15,
                         color=mc(C_RRED), font="Arial")
            if m.width > 5.05:
                m.scale_to_fit_width(5.05)
            wrong_mobs.append(m)
        wrong_grp = VGroup(*wrong_mobs).arrange(
            DOWN, aligned_edge=LEFT, buff=0.24)
        if wrong_grp.height > panel_h - 1.05:
            wrong_grp.scale_to_fit_height(panel_h - 1.05)
        wrong_grp.move_to(left_card.get_center() + DOWN * 0.12)
        wrong_grp.align_to(left_card.get_left() + RIGHT * 0.24, LEFT)

        # Right mobs
        right_mobs = []
        for txt in right_steps[:4]:
            try:
                m = MathTex(str(txt), font_size=24, color=mc(C_GGREEN))
            except Exception:
                m = Text(str(txt)[:52], font_size=15,
                         color=mc(C_GGREEN), font="Arial")
            if m.width > 5.05:
                m.scale_to_fit_width(5.05)
            right_mobs.append(m)
        right_grp = VGroup(*right_mobs).arrange(
            DOWN, aligned_edge=LEFT, buff=0.24)
        if right_grp.height > panel_h - 1.05:
            right_grp.scale_to_fit_height(panel_h - 1.05)
        right_grp.move_to(right_card.get_center() + DOWN * 0.12)
        right_grp.align_to(right_card.get_left() + RIGHT * 0.24, LEFT)

        # "VS" gold label between panels
        vs_txt = Text(
            "VS", font_size=30, color=mc(C_GOLD),
            font="Arial", weight=BOLD,
        ).move_to(np.array([0.0, panel_cy, 0]))

        # ✗ ✓ marks at bottom of each panel
        cross_mark = Text("✗", font_size=50,
                          color=mc(C_RRED), font="Arial", weight=BOLD)
        cross_mark.move_to(left_card.get_bottom() + UP * 0.44)
        tick_mark  = Text("✓", font_size=50,
                          color=mc(C_GGREEN), font="Arial", weight=BOLD)
        tick_mark.move_to(right_card.get_bottom() + UP * 0.44)

        # ── Animate ───────────────────────────────────────────────────
        ta = 0.0
        self.play(FadeIn(warn_grp, shift=DOWN * 0.06), run_time=0.50)
        ta += 0.50
        self.play(FadeIn(left_card), FadeIn(right_card), run_time=0.48)
        ta += 0.48
        self.play(FadeIn(l_hdr), FadeIn(r_hdr), run_time=0.38)
        ta += 0.38
        self.play(FadeIn(vs_txt, scale=0.80), run_time=0.32)
        ta += 0.32

        # Wrong side first
        for m in wrong_mobs:
            self.play(Write(m), run_time=0.48)
            ta += 0.48
        self.play(FadeIn(cross_mark, scale=0.60), run_time=0.38)
        ta += 0.38
        self.wait(0.38)
        ta += 0.38

        # Right side
        for m in right_mobs:
            self.play(Write(m), run_time=0.48)
            ta += 0.48
        self.play(FadeIn(tick_mark, scale=0.60), run_time=0.38)
        ta += 0.38

        # Glow on correct panel
        try:
            r_glow = SurroundingRectangle(
                right_card, color=mc(C_GGREEN),
                stroke_width=3.0, buff=0.08, corner_radius=0.18,
            )
            self.play(Create(r_glow), run_time=0.48)
            ta += 0.48
        except Exception:
            pass

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 7))


# ═════════════════════════════════════════════════════════════
# SCENE 08 — PRACTICE
# ─────────────────────────────────────────────────────────────
# Orange "YOUR TURN — PRACTICE!" pill at top.
# Large question card (9.5 × 1.8).
# Three hint boxes below: STEP 1, STEP 2, STEP 3.
# ═════════════════════════════════════════════════════════════

class Scene08_Practice(Scene):
    def construct(self):
        sd  = get_scene_by_step("practice")
        dur = float(sd.get("duration_seconds", 20.0))
        attach_audio(self, sd.get("scene_id", 8))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        header = make_header(lesson_title, LESSON_ID)
        footer = make_footer()
        self.add(header, footer)

        import numpy as np
        board     = sd.get("board_examples", {})
        practice  = board.get("practice", [])
        narration = sd.get("narration", "")

        if not practice:
            pq = str(sd.get("practice_question",
                            "Solve the following using today's formula."))
            practice = [
                pq,
                r"\text{Step 1: Read the problem carefully}",
                r"\text{Step 2: Write down what is given}",
                r"\text{Step 3: Apply the formula and simplify}",
            ]

        # ── "YOUR TURN" pill ──────────────────────────────────────────
        pill_bg = RoundedRectangle(
            width=5.10, height=0.52, corner_radius=0.26,
            fill_color=mc(C_ORANGE), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, CONTENT_TOP - 0.44, 0]))
        pill_txt = Text(
            "✏️  YOUR TURN  —  PRACTICE!",
            font_size=18, color=mc(C_WHITE), font="Arial", weight=BOLD,
        ).move_to(pill_bg.get_center())
        pill_grp = VGroup(pill_bg, pill_txt)

        # ── Question card ──────────────────────────────────────────────
        q_raw   = str(practice[0]) if practice else "Solve the problem."
        q_card  = make_card(9.5, 1.80, border_color=C_ORANGE)
        q_card.move_to(np.array([0.0, 0.82, 0]))

        q_lines = textwrap.wrap(q_raw, 66)[:3]
        q_mobs  = []
        for ln in q_lines:
            try:
                t = Text(ln, font_size=19, color=mc(C_WHITE), font="Arial")
            except Exception:
                t = Text(ln[:64], font_size=19, color=mc(C_WHITE), font="Arial")
            if t.width > 8.8:
                t.scale_to_fit_width(8.8)
            q_mobs.append(t)
        q_grp = VGroup(*q_mobs).arrange(
            DOWN, buff=0.18, aligned_edge=LEFT)
        q_grp.move_to(q_card.get_center())

        # ── Three hint boxes ───────────────────────────────────────────
        hint_data = [
            ("STEP 1", "Read carefully",  C_BLUE_P),
            ("STEP 2", "Write given",     C_GGREEN),
            ("STEP 3", "Apply formula",   C_ORANGE),
        ]
        hint_cards = []
        for step_lbl, desc, col in hint_data:
            h_card = make_card(3.55, 1.22, border_color=col)
            h_hdr  = make_card_header(step_lbl, 3.55, col)
            h_hdr.move_to(
                h_card.get_top() + DOWN * (h_hdr.height / 2 + 0.07))
            try:
                h_desc = Text(desc, font_size=15,
                              color=mc(C_LGRAY), font="Arial")
            except Exception:
                h_desc = Text("hint", font_size=15,
                              color=mc(C_LGRAY), font="Arial")
            if h_desc.width > 3.10:
                h_desc.scale_to_fit_width(3.10)
            h_desc.move_to(h_card.get_center() + DOWN * 0.08)
            hint_cards.append(VGroup(h_card, h_hdr, h_desc))

        hints_row = VGroup(*hint_cards).arrange(RIGHT, buff=0.30)
        hints_row.move_to(np.array([0.0, -1.65, 0]))

        # ── Animate ───────────────────────────────────────────────────
        ta = 0.0
        self.play(FadeIn(pill_grp, shift=DOWN * 0.08), run_time=0.48)
        ta += 0.48
        self.play(FadeIn(q_card),                       run_time=0.38)
        ta += 0.38
        for qm in q_mobs:
            self.play(FadeIn(qm, shift=RIGHT * 0.06),   run_time=0.38)
            ta += 0.38
        self.play(
            LaggedStart(*[FadeIn(hc, scale=0.90) for hc in hint_cards],
                        lag_ratio=0.24),
            run_time=0.88,
        )
        ta += 0.88

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 8))


# ═════════════════════════════════════════════════════════════
# SCENE 09 — SUMMARY  (closing slide, no standard header)
# ─────────────────────────────────────────────────────────────
# Blue "LESSON COMPLETE!" full-width banner.
# Lesson title in gold below.
# Four numbered takeaway cards in 2×2 grid.
# Red "SUBSCRIBE FOR MORE LESSONS!" CTA + Flash.
# Standard footer.
# ═════════════════════════════════════════════════════════════

class Scene09_Summary(Scene):
    def construct(self):
        sd  = get_scene_by_step("summary")
        dur = float(sd.get("duration_seconds", 24.0))
        attach_audio(self, sd.get("scene_id", 9))

        lesson_title   = SCRIPT_DATA.get("title",          "Today's Lesson")
        formula_spoken = SCRIPT_DATA.get("formula_spoken", "")
        lesson_goal    = SCRIPT_DATA.get("lesson_goal",    "")

        setup_bg(self)
        footer = make_footer()
        self.add(footer)

        import numpy as np

        # ── "LESSON COMPLETE!" banner ─────────────────────────────────
        banner_bg = Rectangle(
            width=FW, height=0.75,
            fill_color=mc(C_BLUE_P), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, 2.82, 0]))
        banner_txt = Text(
            "LESSON COMPLETE!", font_size=28,
            color=mc(C_WHITE), font="Arial", weight=BOLD,
        ).move_to(banner_bg.get_center())
        try:
            check_m = Text("✅", font_size=26)
        except Exception:
            check_m = Text("OK", font_size=18, color=mc(C_GGREEN),
                           font="Arial", weight=BOLD)
        check_m.next_to(banner_txt, LEFT, buff=0.25)
        banner_grp = Group(banner_bg, banner_txt, check_m)

        # ── Lesson title in gold ──────────────────────────────────────
        try:
            title_mob = Text(
                str(lesson_title), font_size=40,
                color=mc(C_GOLD), font="Arial", weight=BOLD,
            )
        except Exception:
            title_mob = Text("Today's Lesson", font_size=40,
                             color=mc(C_GOLD), font="Arial", weight=BOLD)
        if title_mob.width > 12.2:
            title_mob.scale_to_fit_width(12.2)
        title_mob.move_to(np.array([0.0, 1.88, 0]))

        # ── Four takeaway items ───────────────────────────────────────
        takeaways = [
            str(lesson_goal)[:44]    or "Master this concept",
            str(formula_spoken)[:44] or "Apply the formula correctly",
            "Always verify conditions before applying",
            "Practice with varied examples daily",
        ]
        take_colors = [C_BLUE_P, C_GGREEN, C_ORANGE, C_PURPLE]
        take_cards  = []
        for i, item in enumerate(takeaways):
            col = take_colors[i % 4]
            tc_bg = RoundedRectangle(
                width=5.45, height=0.88, corner_radius=0.13,
                fill_color=mc(C_CBG), fill_opacity=1.0,
                stroke_color=mc(col), stroke_width=1.8,
            )
            num_circ = Circle(
                radius=0.22,
                fill_color=mc(col), fill_opacity=1.0, stroke_width=0,
            )
            num_txt = Text(
                str(i + 1), font_size=15,
                color=mc(C_WHITE), font="Arial", weight=BOLD,
            )
            num_txt.move_to(num_circ.get_center())
            num_grp = VGroup(num_circ, num_txt)
            num_grp.move_to(tc_bg.get_left() + RIGHT * 0.36)
            try:
                item_txt = Text(
                    str(item), font_size=13,
                    color=mc(C_WHITE), font="Arial",
                )
            except Exception:
                item_txt = Text("Key point", font_size=13,
                                color=mc(C_WHITE), font="Arial")
            if item_txt.width > 4.50:
                item_txt.scale_to_fit_width(4.50)
            item_txt.move_to(tc_bg.get_center() + RIGHT * 0.25)
            take_cards.append(VGroup(tc_bg, num_grp, item_txt))

        # 2 × 2 grid
        row1 = VGroup(take_cards[0], take_cards[1]).arrange(RIGHT, buff=0.28)
        row2 = VGroup(take_cards[2], take_cards[3]).arrange(RIGHT, buff=0.28)
        take_grp = VGroup(row1, row2).arrange(DOWN, buff=0.22)
        take_grp.move_to(np.array([0.0, 0.35, 0]))

        # ── Subscribe CTA ─────────────────────────────────────────────
        cta_bg = RoundedRectangle(
            width=7.60, height=0.72, corner_radius=0.18,
            fill_color=mc(C_RRED), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, -2.58, 0]))
        cta_txt = Text(
            "SUBSCRIBE FOR MORE LESSONS!",
            font_size=22, color=mc(C_WHITE), font="Arial", weight=BOLD,
        ).move_to(cta_bg.get_center())
        play_arr = Text(
            "▶", font_size=20,
            color=mc(C_WHITE), font="Arial",
        ).next_to(cta_txt, LEFT, buff=0.24)
        cta_grp = Group(cta_bg, cta_txt, play_arr)

        # ── Animate ───────────────────────────────────────────────────
        ta = 0.0
        self.play(FadeIn(banner_grp, shift=DOWN * 0.08), run_time=0.68)
        ta += 0.68
        self.play(Write(title_mob), run_time=0.80)
        ta += 0.80
        self.play(
            LaggedStart(*[FadeIn(tc, scale=0.90) for tc in take_cards],
                        lag_ratio=0.22),
            run_time=1.00,
        )
        ta += 1.00
        self.play(FadeIn(cta_grp, scale=0.92), run_time=0.50)
        ta += 0.50
        try:
            self.play(
                Flash(cta_bg, color=mc(C_GOLD),
                      line_length=0.25, num_lines=16, flash_radius=0.88),
                run_time=0.80,
            )
            ta += 0.80
        except Exception:
            pass

        self.wait(max(0.5, dur - ta - 0.5))
        sync_to_audio(self, sd.get("scene_id", 9))
'''

# ══════════════════════════════════════════════════════════════
# INJECT RUNTIME VALUES INTO MANIM CODE
# ══════════════════════════════════════════════════════════════

def build_manim_source(script: dict) -> str:
    source = MANIM_SCENE_CODE

    # Path placeholders
    source = source.replace("__SCRIPT_PATH__", str(TIMED_SCRIPT))
    source = source.replace("__AUDIO_DIR__",   str(LESSON_AUDIO))
    source = source.replace("__BANNER_PATH__", str(BANNER_PATH))
    source = source.replace("__LOGO_PATH__",   str(LOGO_PATH))

    # Colour constants from theme
    source = source.replace("{C_BG}",      C_BG)
    source = source.replace("{C_PRIMARY}", C_PRIMARY)
    source = source.replace("{C_SECOND}",  C_SECOND)
    source = source.replace("{C_BLUE}",    C_BLUE)
    source = source.replace("{C_GREEN}",   C_GREEN)
    source = source.replace("{C_YELLOW}",  C_YELLOW)
    source = source.replace("{C_RED}",     C_RED)
    source = source.replace("{C_CARD}",    C_CARD)

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
            "-qh",                          # quality: high 1080p60
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
