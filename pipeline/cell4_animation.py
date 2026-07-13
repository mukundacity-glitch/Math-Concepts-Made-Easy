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

def set_background(scene_obj):
    if BANNER_PATH.exists():
        try:
            bg_img = ImageMobject(str(BANNER_PATH))
            bg_img.set_width(config.frame_width)
            bg_img.set_height(config.frame_height)
            bg_img.move_to(ORIGIN)
            scene_obj.add(bg_img)
        except Exception:
            scene_obj.camera.background_color = mc(C_BG)
    else:
        scene_obj.camera.background_color = mc(C_BG)

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
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 1))

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
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 2))

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
        self.wait(max(0.5, dur - 4.5))
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
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 3))

        heading = Text(
            "The Concept",
            font_size=42, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        self.play(Write(heading), run_time=0.6)

        if "graph" in vis_type:
            self._draw_axes(dur)
        elif "diagram" in vis_type:
            self._draw_diagram(dur)
        elif "table" in vis_type:
            self._draw_table(dur)
        else:
            self._draw_visual_card(dur)

    def _draw_axes(self, dur):
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
        self.wait(max(0.5, dur - 3.5))

    def _draw_diagram(self, dur):
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
        self.wait(max(0.5, dur - 3.5))

    def _draw_table(self, dur):
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
        self.wait(max(0.5, dur - 3.5))

    def _draw_visual_card(self, dur):
        # Number line
        nl = NumberLine(
            x_range=[-3, 3, 1],
            length=11,
            include_numbers=True,
            color=mc(C_SECOND),
            numbers_with_elongated_ticks=[-2,-1,0,1,2],
        ).shift(DOWN * 0.2)

        rational_points = [
            (Dot(nl.n2p(-1.5), color=mc(C_GREEN), radius=0.1),
             MathTex(r"-\tfrac{3}{2}", font_size=28, color=mc(C_GREEN))),
            (Dot(nl.n2p(0.333), color=mc(C_BLUE),  radius=0.1),
             MathTex(r"\tfrac{1}{3}",  font_size=28, color=mc(C_BLUE))),
            (Dot(nl.n2p(0.75),  color=mc(C_GREEN), radius=0.1),
             MathTex(r"\tfrac{3}{4}",  font_size=28, color=mc(C_GREEN))),
            (Dot(nl.n2p(2.0),   color=mc(C_YELLOW),radius=0.1),
             MathTex(r"2",             font_size=28, color=mc(C_YELLOW))),
        ]

        heading2 = Text(
            "Rational numbers live on the number line",
            font_size=26, color=mc(C_SECOND), font="Arial"
        ).shift(UP * 2.5)

        self.play(Create(nl), run_time=1.0)
        self.play(FadeIn(heading2), run_time=0.4)
        for dot, lbl in rational_points:
            lbl.next_to(dot, UP, buff=0.25)
            self.play(FadeIn(dot), Write(lbl), run_time=0.45)
            self.wait(0.2)
        self.wait(max(0.5, dur - 4.0))
# ════════════════════════════════════════════════════════════
# SCENE 04 — DEFINITION (VISUAL_ONLY)
# Formal definition shown on clean card.
# No narration text overlay.
# ════════════════════════════════════════════════════════════

class Scene04_Definition(Scene):
    def construct(self):
        sd  = get_scene_data("definition")
        dur = sd.get("duration_seconds", 16.0)
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 4))

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
        self.wait(max(0.5, dur - 4.5))
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
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 5))

        heading = Text(
            "The Formula",
            font_size=42, color=mc(C_YELLOW),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        self.play(Write(heading), run_time=0.6)

        # Read board_examples formula field
        board   = sd.get("board_examples", {})
        formula_str = board.get("formula",
                      SCRIPT_DATA.get("key_formula", "p/q"))

        # Build formula components from worked_example steps
        steps   = board.get("worked_example", [])

        if steps:
            # Write each step one at a time — EQUATION_BUILD pattern
            visible_mobs = []
            y_pos = 1.8
            per_step = max(0.5, (dur - 2.5) / len(steps))

            for i, step_tex in enumerate(steps):
                try:
                    mob = MathTex(
                        step_tex, font_size=52,
                        color=mc(C_YELLOW if i == 0 else C_PRIMARY)
                    )
                except Exception:
                    mob = Text(
                        step_tex, font_size=28,
                        color=mc(C_PRIMARY), font="Arial"
                    )

                mob.to_edge(LEFT, buff=1.0)
                mob.shift(UP * y_pos)

                # Dim previous mobs
                if visible_mobs:
                    self.play(
                        *[m.animate.set_opacity(0.4)
                          for m in visible_mobs],
                        Write(mob),
                        run_time=0.7
                    )
                else:
                    self.play(Write(mob), run_time=0.7)

                visible_mobs.append(mob)
                self.wait(per_step - 0.7)
                y_pos -= 0.95
        else:
            # Fallback: write full formula centered
            try:
                fml = MathTex(formula_str, font_size=80,
                              color=mc(C_PRIMARY))
            except Exception:
                fml = Text(SCRIPT_DATA.get("formula_spoken", ""),
                           font_size=32, color=mc(C_PRIMARY),
                           font="Arial")
            fml.shift(UP * 0.5)
            box = SurroundingRectangle(
                fml, color=mc(C_YELLOW),
                stroke_width=2.5, buff=0.4, corner_radius=0.2
            )
            self.play(Write(fml), run_time=1.4)
            self.play(Create(box), run_time=0.5)
            self.wait(max(0.5, dur - 4.0))


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
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 6))

        heading = Text(
            "Worked Example",
            font_size=42, color=mc(C_GREEN),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        self.play(Write(heading), run_time=0.6)

        board = sd.get("board_examples", {})
        steps = board.get("worked_example", [])

        if not steps:
            # Fallback if board_examples not populated yet
            steps = [
                SCRIPT_DATA.get("key_formula", ""),
                r"\text{Apply the definition step by step}",
                r"\text{Check your answer}",
            ]

        per_step = max(0.5, (dur - 2.0) / max(len(steps), 1))

        y_pos  = 2.2
        mobs   = []
        for i, step_tex in enumerate(steps):
            if not step_tex.strip():
                y_pos -= 0.4
                continue
            try:
                mob = MathTex(
                    step_tex, font_size=44,
                    color=mc(C_YELLOW if i == 0 else C_PRIMARY)
                )
            except Exception:
                mob = Text(
                    step_tex, font_size=26,
                    color=mc(C_PRIMARY), font="Arial"
                )
            mob.to_edge(LEFT, buff=0.9)
            mob.shift(UP * y_pos)
            self.play(Write(mob), run_time=0.65)
            self.wait(per_step - 0.65)
            mobs.append(mob)
            y_pos -= 0.92

        # Final answer highlight
        if mobs:
            self.play(
                mobs[-1].animate.set_color(mc(C_GREEN)),
                run_time=0.4
            )
        self.wait(0.5)


# ════════════════════════════════════════════════════════════
# SCENE 07 — MISTAKES (BOARD_WRITE)
# Wrong working shown with red cross.
# Correct version written below in green.
# ════════════════════════════════════════════════════════════

class Scene07_Mistakes(Scene):
    def construct(self):
        sd  = get_scene_data("mistakes")
        dur = sd.get("duration_seconds", 22.0)
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 7))

        heading = Text(
            "Common Mistakes",
            font_size=42, color=mc(C_RED),
            font="Arial", weight=BOLD
        ).to_edge(UP, buff=0.55)

        self.play(Write(heading), run_time=0.6)

        board  = sd.get("board_examples", {})
        steps  = board.get("worked_example", [
            r"\text{Mistake: skipping the condition check}",
            r"\text{Correct: always verify conditions first}",
            r"\text{Mistake: wrong sign after rearranging}",
            r"\text{Correct: apply inverse operation carefully}",
        ])

        per_step = max(0.5, (dur - 2.0) / max(len(steps), 1))
        y_pos    = 2.0

        for i, step_tex in enumerate(steps):
            if not step_tex.strip():
                continue
            is_wrong   = "Mistake" in step_tex or "Wrong" in step_tex
            is_correct = "Correct" in step_tex or "checkmark" in step_tex or "\\checkmark" in step_tex
            color      = C_RED if is_wrong else (C_GREEN if is_correct else C_PRIMARY)

            try:
                mob = MathTex(step_tex, font_size=40, color=mc(color))
            except Exception:
                mob = Text(step_tex, font_size=24,
                           color=mc(color), font="Arial")

            mob.to_edge(LEFT, buff=0.9)
            mob.shift(UP * y_pos)

            if is_wrong:
                cross = Text("✗", font_size=36,
                             color=mc(C_RED)).next_to(mob, LEFT, buff=0.2)
                self.play(Write(mob), FadeIn(cross), run_time=0.65)
            elif is_correct:
                tick = Text("✓", font_size=36,
                            color=mc(C_GREEN)).next_to(mob, LEFT, buff=0.2)
                self.play(Write(mob), FadeIn(tick), run_time=0.65)
            else:
                self.play(Write(mob), run_time=0.65)

            self.wait(per_step - 0.65)
            y_pos -= 0.95

        self.wait(0.5)


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
        set_background(self)
        add_logo(self)
        attach_audio(self, sd.get("scene_id", 8))

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
        y_pos    = 1.8

        sol_mobs = []
        for step_tex in solution_steps:
            if not step_tex.strip():
                continue
            try:
                mob = MathTex(step_tex, font_size=42,
                              color=mc(C_PRIMARY))
            except Exception:
                mob = Text(step_tex, font_size=26,
                           color=mc(C_PRIMARY), font="Arial")

            mob.to_edge(LEFT, buff=0.9)
            mob.shift(UP * y_pos)
            self.play(Write(mob), run_time=0.6)
            self.wait(per_step - 0.6)
            sol_mobs.append(mob)
            y_pos -= 0.88

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

        self.wait(0.5)


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
        set_background(self)
        add_logo(self)
        add_banner(self)
        attach_audio(self, sd.get("scene_id", 9))

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

