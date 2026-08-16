# ==========================================
# CELL 4: MANIM ANIMATION ENGINE
# CHANNEL: MathConceptsMadeEasy
# Reads: lesson_XXX_script_timed.json
# Reads: audio/lesson_XXX/scene_XX.mp3
# Reads: audio/lesson_XXX/scene_XX.words.json
# Writes: renders/lesson_XXX/scene_XX.mp4
#
# Design contract (applies to every scene):
#   * NOTHING appears on screen as raw LaTeX — math is compiled with
#     MathTex or converted to clean unicode via pipeline.mathtext.
#   * Text is never truncated — it wraps and scales to fit.
#   * Every visual appears at the moment the narration speaks about it,
#     driven by the per-word timestamps from Cell 3 (words.json).
#   * Real-world sentences (pizza, chocolate, money, fruit …) get a
#     matching drawn illustration, generated dynamically from the words
#     of the narration — no lesson-specific hard-coding.
#   * Never a bare "?" as a stand-in visual. The opening "little mystery"
#     hook (Scene01) and any narration matching mystery/secret/unknown
#     picks from MYSTERY_VARIANTS (treasure chest, magnifying glass,
#     puzzle, lightbulb, brain+gears, door, detective board …) keyed off
#     LESSON_ID, so the same animation never repeats on back-to-back
#     days. Add new variants to that list rather than reusing one.
#   * The background (grid + floating dots) is tinted per day via
#     DAY_ACCENT/DAY_ACCENTS in setup_bg — every video gets a distinct
#     ambient theme without touching the fixed semantic foreground
#     palette (C_SEM_* — blue=definition, gold=key idea, etc. must stay
#     constant so students build that association over lessons).
#   * Geometric shapes named in narration (square, rectangle, triangle,
#     circle, angle, graph, area, perimeter) are drawn live via the
#     viz_square/viz_rectangle/viz_triangle/viz_circle_shape/viz_graph/
#     viz_angle/viz_area/viz_perimeter builders, each side/measure
#     labeled with its real unit, and Scene02_Hook uses Create()
#     (stroke-by-stroke) instead of FadeIn for anything tagged
#     `_geom_draw = True`.
#   * story_visual(sentence) matches the beat's own words first. When a
#     beat names nothing drawable, visual_for_beat(beat, hint_sentences)
#     falls back to the lesson's own author-written `visual_hints` field
#     (curriculum/*.json — stage directions like "Hook: show a pizza
#     divided into 4… Number line: plot these points… Box the rule in
#     red.") via a stemmed bag-of-words match — see hint_sentences_for()
#     and _best_hint_sentence(). This is curriculum-driven visual
#     selection, not natural-language understanding: it can only pick
#     among the illustrations story_visual() already knows how to draw,
#     and a beat with no lexical overlap to anything still falls through
#     to no visual. Scene02_Hook and Scene03_Concept use this path;
#     extend other scenes' beat loops the same way if they grow one.
#   * Crossfade *type* between scenes (pipeline/cell5_assembly.py,
#     XFADE_STYLES) also rotates by day, so consecutive videos don't all
#     cut the same way either.
# ==========================================

import sys, json, subprocess, shutil, os
from pathlib import Path


# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
REPO_ROOT = _Path(__file__).resolve().parents[1]
_sys.path.insert(0, str(REPO_ROOT))
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

# ══════════════════════════════════════════════════════════════
# MANIM SOURCE TEMPLATE
# Rendered per scene by the manim CLI. Placeholders (__X__ and
# {C_X}) are substituted by build_manim_source().
# ══════════════════════════════════════════════════════════════
MANIM_SCENE_CODE = r'''
from manim import *
import json, math, random, re, textwrap, sys
from pathlib import Path

# ── Repo imports (shared LaTeX → text/speech translation) ─────
sys.path.insert(0, r"__REPO_ROOT__")
from pipeline.mathtext import latex_to_plain, normalize_word, split_sentences

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

# Illustration palette
C_CRUST   = "#D97706"
C_CHEESE  = "#FBBF24"
C_PEPPER  = "#B91C1C"
C_CHOCO   = "#7C4A12"
C_CHOCO_D = "#5B3610"
C_COIN    = "#FDE68A"
C_APPLE   = "#DC2626"
C_LEAF    = "#16A34A"
C_SKIN    = "#F5C99B"
C_CYAN    = "#22D3EE"

# Semantic color system — every color means one thing, lesson after
# lesson, so students build the association over time:
#   definitions → blue, correct → green, examples → orange,
#   theorems/structure → purple, key ideas → gold, mistakes → red,
#   formulas → cyan
C_SEM_DEF     = C_BLUE_P
C_SEM_CORRECT = C_GGREEN
C_SEM_EXAMPLE = C_ORANGE
C_SEM_THEOREM = C_PURPLE
C_SEM_KEY     = C_GOLD
C_SEM_WRONG   = C_RRED
C_SEM_FORMULA = C_CYAN

CHANNEL = "Math Concept Made Easy"
TAGLINE = "LEARN  •  PRACTICE  •  MASTER"
FONT    = "DejaVu Sans"   # present on every CI runner, full unicode math

# Per-day background theme — the semantic palette above (blue=definition,
# gold=key idea, etc.) is deliberately FIXED for foreground/text elements
# so students build the color↔meaning association lesson after lesson.
# The ambient background (grid, floating dots, gradient tint) is not part
# of that system, so it rotates by day instead, otherwise every video
# renders a byte-identical backdrop (same seed, same hue, forever).
DAY_ACCENTS = [C_BLUE_L, C_CYAN, C_PURPLE, C_ORANGE, C_GGREEN, "#EC4899", "#6366F1", C_GOLD]
DAY_ACCENT  = DAY_ACCENTS[(LESSON_ID - 1) % len(DAY_ACCENTS)]


def _blend_hex(h1, h2, t):
    """Blend hex color h1 → h2 by fraction t (0 = h1, 1 = h2)."""
    h1, h2 = h1.lstrip("#"), h2.lstrip("#")
    r1, g1, b1 = int(h1[0:2], 16), int(h1[2:4], 16), int(h1[4:6], 16)
    r2, g2, b2 = int(h2[0:2], 16), int(h2[2:4], 16), int(h2[4:6], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


C_NAVY2_TINT = _blend_hex(C_NAVY2, DAY_ACCENT, 0.22)

config.background_color = C_NAVY1

def mc(h):
    return ManimColor(h)

# ── Frame layout constants ────────────────────────────────────
FW = 14.222   # config.frame_width default for 1080p60
FH = 8.0      # config.frame_height default

HEADER_TOP  =  4.00
HEADER_BOT  =  3.02
CONTENT_TOP =  2.92
CONTENT_BOT = -3.12
FOOTER_TOP  = -3.22
FOOTER_BOT  = -4.00

import numpy as np

# ── Basic helpers ─────────────────────────────────────────────

def get_scene_by_step(step):
    for s in SCRIPT_DATA["scenes"]:
        if s.get("step") == step:
            return s
    return SCRIPT_DATA["scenes"][0] if SCRIPT_DATA["scenes"] else {}

def attach_audio(scene_obj, scene_id):
    mp3 = LESSON_AUDIO / f"scene_{scene_id:02d}.mp3"
    if mp3.exists():
        try:
            scene_obj.add_sound(str(mp3))
        except Exception:
            pass

def scene_time(scene_obj):
    try:
        return float(scene_obj.renderer.time)
    except Exception:
        return 0.0

def sync_to_audio(scene_obj, scene_id):
    target = 20.0
    for s in SCRIPT_DATA["scenes"]:
        if s.get("scene_id") == scene_id:
            target = float(s.get("duration_seconds", 20.0))
            break
    remaining = target - scene_time(scene_obj) - 0.1
    if remaining > 0.05:
        scene_obj.wait(remaining)


# ═════════════════════════════════════════════════════════════
# NARRATION TIMELINE — the sync engine
#
# Cell 3 saved one timestamp per spoken word (scene_XX.words.json).
# Narration.when_spoken("three over four rational") returns the second
# at which the voice starts saying that phrase, so every visual can be
# scheduled to appear exactly when it is being talked about.
# ═════════════════════════════════════════════════════════════

class Narration:
    def __init__(self, sd):
        self.sd       = sd
        self.scene_id = int(sd.get("scene_id", 1))
        self.duration = float(sd.get("duration_seconds", 20.0))
        self.text     = str(sd.get("narration", ""))
        self.words    = self._load_words()
        self.cursor   = 0       # word index — matches advance forward only
        self.char_pos = 0       # char cursor for the estimate fallback

    def _load_words(self):
        path = LESSON_AUDIO / f"scene_{self.scene_id:02d}.words.json"
        if path.exists():
            try:
                with open(str(path), "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def when_spoken(self, phrase, advance=True):
        """Second at which `phrase` starts being spoken (None if unknown)."""
        toks = [normalize_word(w) for w in str(phrase).split()]
        toks = [t for t in toks if t]
        if not toks:
            return None
        if self.words:
            for need in (4, 3, 2, 1):
                if len(toks) < need:
                    continue
                idx = self._find(toks[:need])
                if idx is not None:
                    if advance:
                        self.cursor = idx + need
                    return float(self.words[idx]["start"])
        return self._estimate(phrase)

    def _find(self, sub):
        n, k = len(self.words), len(sub)
        for i in range(self.cursor, n - k + 1):
            if all(self.words[i + j].get("norm") == sub[j] for j in range(k)):
                return i
        return None

    def _estimate(self, phrase):
        """Proportional fallback when word timestamps are unavailable."""
        hay = self.text.lower()
        for probe_len in (32, 16, 8):
            probe = str(phrase)[:probe_len].lower().strip()
            if len(probe) < 4:
                continue
            pos = hay.find(probe, self.char_pos)
            if pos >= 0:
                self.char_pos = pos + 1
                frac = pos / max(len(hay), 1)
                return frac * max(self.duration - 1.2, 1.0)
        return None


def wait_until(scene_obj, t, lead=0.25):
    """Wait so the next animation lands just before second `t` of audio."""
    if t is None:
        return
    gap = (t - lead) - scene_time(scene_obj)
    if gap > 0.02:
        scene_obj.wait(gap)


def reveal(scene_obj, nar, mobj, spoken=None, run_time=0.55, anim=None, lead=0.30):
    """FadeIn `mobj` at the moment `spoken` is narrated (or now)."""
    if spoken is not None and nar is not None:
        wait_until(scene_obj, nar.when_spoken(spoken), lead=lead)
    a = (anim or FadeIn)(mobj)
    scene_obj.play(a, run_time=run_time)


# ═════════════════════════════════════════════════════════════
# TEXT FACTORIES — nothing raw, nothing truncated
# ═════════════════════════════════════════════════════════════

def TXT(s, size=28, color=None, bold=False, max_w=None, wrap=None,
        line_spacing=0.95):
    """Clean prose Text. Always passes through latex_to_plain first."""
    s = latex_to_plain(s)
    if not s:
        s = " "
    if wrap:
        s = "\n".join(textwrap.wrap(s, wrap)) or " "
    try:
        t = Text(s, font_size=size, color=mc(color or C_WHITE), font=FONT,
                 weight="BOLD" if bold else "NORMAL", line_spacing=line_spacing)
    except Exception:
        t = Text(s.encode("ascii", "ignore").decode() or " ",
                 font_size=size, color=mc(color or C_WHITE), font=FONT)
    if max_w and t.width > max_w:
        t.scale_to_fit_width(max_w)
    return t


def MATH(s, size=48, color=None, max_w=None):
    """Compiled math. Falls back to clean unicode text — NEVER raw LaTeX."""
    raw = str(s)
    try:
        m = MathTex(raw, font_size=size, color=mc(color or C_WHITE))
    except Exception:
        m = TXT(raw, size=max(18, int(size * 0.55)), color=color or C_WHITE)
    if max_w and m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m


# ═════════════════════════════════════════════════════════════
# VERDICT PARSING — board lines like "q ≠ 0 → Yes" get a clean
# YES / NO pill instead of trailing checkmark clutter.
# ═════════════════════════════════════════════════════════════

_VERDICT_RE = re.compile(
    r"(?:→\s*)?(?:✗\s*)?\b(Yes|No|Undefined)\b[!.]?\s*$", re.IGNORECASE)


def split_verdict(plain_line):
    m = _VERDICT_RE.search(plain_line)
    if not m:
        return plain_line.strip(), None
    head = plain_line[:m.start()].strip().rstrip("→✗ ,").strip()
    verdict = m.group(1).upper()
    return (head or plain_line.strip()), verdict


def verdict_pill(verdict):
    good = verdict.upper() == "YES"
    col  = C_GGREEN if good else C_RRED
    lbl  = "YES" if good else ("NO" if verdict.upper() == "NO" else "UNDEFINED")
    txt  = TXT(lbl, size=20, color=col, bold=True)
    box  = RoundedRectangle(
        width=txt.width + 0.42, height=0.52, corner_radius=0.14,
        fill_color=mc(col), fill_opacity=0.16,
        stroke_color=mc(col), stroke_width=2.2,
    )
    txt.move_to(box.get_center())
    return VGroup(box, txt)


def number_chip(n, col=None):
    c = Circle(radius=0.26, fill_color=mc(col or C_BLUE_P),
               fill_opacity=1.0, stroke_width=0)
    t = TXT(str(n), size=20, color=C_WHITE, bold=True)
    t.move_to(c.get_center())
    return VGroup(c, t)


# ═════════════════════════════════════════════════════════════
# REAL-WORLD ILLUSTRATION LIBRARY
# All drawn with vector shapes — no external assets, works for
# any lesson. story_visual(sentence) picks one from the words of
# the narration itself.
# ═════════════════════════════════════════════════════════════

def _sector(r, start_angle, angle, **kw):
    """Sector compatible with both Manim 0.18 (outer_radius) and 0.19 (radius)."""
    try:
        return Sector(radius=r, start_angle=start_angle, angle=angle, **kw)
    except TypeError:
        return Sector(outer_radius=r, start_angle=start_angle, angle=angle, **kw)


def viz_pizza(total=4, taken=3, r=1.15):
    """Pizza cut into `total` slices, `taken` of them highlighted (eaten)."""
    total = max(2, min(int(total or 4), 12))
    taken = max(0, min(int(taken if taken is not None else 0), total))
    g = VGroup()
    crust = Circle(radius=r, fill_color=mc(C_CRUST), fill_opacity=1.0,
                   stroke_color=mc("#92400E"), stroke_width=4)
    cheese = Circle(radius=r * 0.86, fill_color=mc(C_CHEESE),
                    fill_opacity=1.0, stroke_width=0)
    g.add(crust, cheese)
    slice_ang = TAU / total
    rng = random.Random(7)
    for i in range(total):
        a0 = i * slice_ang
        eaten = i < taken
        if eaten:
            sec = _sector(r * 0.86, a0, slice_ang,
                          fill_color=mc(C_ORANGE), fill_opacity=0.92,
                          stroke_color=mc("#92400E"), stroke_width=2)
            mid = a0 + slice_ang / 2
            sec.shift(0.10 * np.array([math.cos(mid), math.sin(mid), 0]))
            g.add(sec)
        # pepperoni on every slice
        mid = a0 + slice_ang / 2
        rr = r * rng.uniform(0.38, 0.62)
        g.add(Dot(point=np.array([rr * math.cos(mid), rr * math.sin(mid), 0]),
                  radius=0.09, color=mc(C_PEPPER)))
    for i in range(total):
        a0 = i * slice_ang
        g.add(Line(ORIGIN, r * np.array([math.cos(a0), math.sin(a0), 0]),
                   stroke_color=mc("#92400E"), stroke_width=3))
    lbl = TXT(f"{taken} of {total} slices  =  {taken}/{total}",
              size=24, color=C_GOLD, bold=True)
    lbl.next_to(g, DOWN, buff=0.30)
    return VGroup(g, lbl)


def viz_chocolate(pieces=5, people=None, per_share=None):
    """Chocolate bars and (optionally) the people sharing them."""
    pieces = max(1, min(int(pieces or 4), 12))
    bar = VGroup()
    for i in range(pieces):
        sq = RoundedRectangle(
            width=0.62, height=0.62, corner_radius=0.08,
            fill_color=mc(C_CHOCO), fill_opacity=1.0,
            stroke_color=mc(C_CHOCO_D), stroke_width=3)
        inner = RoundedRectangle(
            width=0.40, height=0.40, corner_radius=0.06,
            fill_color=mc(C_CHOCO_D), fill_opacity=0.55, stroke_width=0)
        inner.move_to(sq.get_center())
        bar.add(VGroup(sq, inner))
    per_row = min(pieces, 6)
    rows = VGroup()
    for start in range(0, pieces, per_row):
        rows.add(VGroup(*bar[start:start + per_row]).arrange(RIGHT, buff=0.06))
    g = rows.arrange(DOWN, buff=0.06)
    out = VGroup(g)
    if people:
        ppl = viz_people(people)
        ppl.next_to(g, DOWN, buff=0.34)
        out.add(ppl)
    cap = f"{pieces} pieces"
    if people:
        cap += f" ÷ {people} people"
        if per_share:
            cap += f"  =  {per_share} each"
    lbl = TXT(cap, size=24, color=C_GOLD, bold=True)
    lbl.next_to(out, DOWN, buff=0.28)
    out.add(lbl)
    return out


def viz_people(n=2):
    n = max(1, min(int(n), 6))
    g = VGroup()
    for _ in range(n):
        head = Circle(radius=0.16, fill_color=mc(C_SKIN),
                      fill_opacity=1.0, stroke_color=mc("#B45309"),
                      stroke_width=2)
        body = _sector(0.30, 0, PI,
                       fill_color=mc(C_BLUE_L), fill_opacity=1.0,
                       stroke_width=0)
        body.next_to(head, DOWN, buff=0.02)
        g.add(VGroup(head, body))
    g.arrange(RIGHT, buff=0.30)
    return g


def viz_money(amount=None):
    g = VGroup()
    for i in range(3):
        coin = Circle(radius=0.42, fill_color=mc(C_COIN), fill_opacity=1.0,
                      stroke_color=mc(C_ORANGE), stroke_width=4)
        sym = TXT("$", size=30, color=C_ORANGE, bold=True)
        sym.move_to(coin.get_center())
        c = VGroup(coin, sym).shift(RIGHT * i * 0.55 + UP * (i % 2) * 0.10)
        g.add(c)
    if amount:
        lbl = TXT(str(amount), size=24, color=C_GOLD, bold=True)
        lbl.next_to(g, DOWN, buff=0.28)
        g = VGroup(g, lbl)
    return g


def viz_fruits(n=3, kind="apple"):
    n = max(1, min(int(n), 8))
    g = VGroup()
    for _ in range(n):
        if kind == "orange":
            body = Circle(radius=0.30, fill_color=mc(C_ORANGE),
                          fill_opacity=1.0, stroke_width=0)
        else:
            body = Circle(radius=0.30, fill_color=mc(C_APPLE),
                          fill_opacity=1.0, stroke_width=0)
        stem = Line(body.get_top(), body.get_top() + UP * 0.14,
                    stroke_color=mc("#78350F"), stroke_width=4)
        leaf = Ellipse(width=0.20, height=0.10, fill_color=mc(C_LEAF),
                       fill_opacity=1.0, stroke_width=0)
        leaf.move_to(body.get_top() + UP * 0.10 + RIGHT * 0.12)
        g.add(VGroup(body, stem, leaf))
    g.arrange(RIGHT, buff=0.22)
    return g


def viz_fraction_pie(p, q, r=1.0, label=True):
    """Generic 'p of q parts' pie — the universal fraction picture."""
    q = max(1, min(int(q), 16))
    p = max(0, min(int(p), q))
    g = VGroup()
    base = Circle(radius=r, fill_color=mc(C_CBG), fill_opacity=1.0,
                  stroke_color=mc(C_BLUE_L), stroke_width=3)
    g.add(base)
    ang = TAU / q
    for i in range(q):
        if i < p:
            g.add(_sector(r, i * ang, ang,
                          fill_color=mc(C_BLUE_L), fill_opacity=0.85,
                          stroke_width=0))
    for i in range(q):
        g.add(Line(ORIGIN, r * np.array(
            [math.cos(i * ang), math.sin(i * ang), 0]),
            stroke_color=mc(C_NAVY1), stroke_width=2.5))
    if label:
        lbl = MATH(rf"\tfrac{{{p}}}{{{q}}}", size=44, color=C_GOLD)
        lbl.next_to(g, DOWN, buff=0.28)
        g = VGroup(g, lbl)
    return g


def viz_mystery_box(symbol=None):
    """Glowing mystery box with a '?' — one of several 'unknown' visuals
    (see MYSTERY_VARIANTS below); kept as the classic option."""
    box = RoundedRectangle(
        width=1.8, height=1.5, corner_radius=0.16,
        fill_color=mc(C_CBG), fill_opacity=1.0,
        stroke_color=mc(C_SEM_KEY), stroke_width=3.5)
    glow = RoundedRectangle(
        width=2.1, height=1.8, corner_radius=0.22,
        fill_color=mc(C_SEM_KEY), fill_opacity=0.14, stroke_width=0)
    glow.move_to(box.get_center())
    q = TXT("?", size=64, color=C_SEM_KEY, bold=True)
    q.move_to(box.get_center())
    g = VGroup(glow, box, q)
    if symbol:
        lab = TXT(str(symbol), size=30, color=C_CYAN, bold=True)
        lab.next_to(box, DOWN, buff=0.26)
        g.add(lab)
    return g


def viz_mystery_treasure(symbol=None):
    """A locked treasure chest — an unknown worth digging for."""
    lid = RoundedRectangle(width=2.0, height=0.55, corner_radius=0.18,
                           fill_color=mc("#92400E"), fill_opacity=1.0,
                           stroke_color=mc(C_GOLD), stroke_width=3)
    lid.move_to(np.array([0.0, 0.42, 0]))
    body = RoundedRectangle(width=2.0, height=0.95, corner_radius=0.10,
                            fill_color=mc("#7C4A12"), fill_opacity=1.0,
                            stroke_color=mc(C_GOLD), stroke_width=3)
    body.move_to(np.array([0.0, -0.28, 0]))
    band = Rectangle(width=0.20, height=1.5, fill_color=mc(C_GOLD),
                     fill_opacity=1.0, stroke_width=0)
    band.move_to(np.array([0.0, 0.05, 0]))
    lock = RoundedRectangle(width=0.44, height=0.36, corner_radius=0.06,
                            fill_color=mc(C_GOLD), fill_opacity=1.0, stroke_width=0)
    lock.move_to(np.array([0.0, 0.08, 0]))
    q = TXT("?", size=24, color=C_NAVY1, bold=True)
    q.move_to(lock.get_center())
    glow = RoundedRectangle(width=2.5, height=2.0, corner_radius=0.30,
                            fill_color=mc(C_GOLD), fill_opacity=0.12, stroke_width=0)
    glow.move_to(np.array([0.0, 0.05, 0]))
    g = VGroup(glow, body, band, lid, lock, q)
    if symbol:
        lab = TXT(str(symbol), size=28, color=C_CYAN, bold=True)
        lab.next_to(g, DOWN, buff=0.28)
        g.add(lab)
    return g


def viz_mystery_magnifier(symbol=None):
    """A magnifying glass zooming in on the unknown."""
    lens = Circle(radius=0.62, fill_color=mc(C_CBG), fill_opacity=0.85,
                  stroke_color=mc(C_CYAN), stroke_width=6)
    lens.move_to(np.array([-0.15, 0.25, 0]))
    handle = Line(lens.get_center() + np.array([0.46, -0.46, 0]),
                  lens.get_center() + np.array([1.05, -1.05, 0]),
                  stroke_color=mc(C_CYAN), stroke_width=10)
    glow = Circle(radius=0.80, fill_color=mc(C_CYAN), fill_opacity=0.10,
                 stroke_width=0)
    glow.move_to(lens.get_center())
    q = TXT("?", size=46, color=C_SEM_KEY, bold=True)
    q.move_to(lens.get_center())
    g = VGroup(glow, lens, q, handle)
    if symbol:
        lab = TXT(str(symbol), size=28, color=C_CYAN, bold=True)
        lab.next_to(g, DOWN, buff=0.30)
        g.add(lab)
    return g


def viz_mystery_puzzle(symbol=None):
    """Four puzzle pieces gathering around the unsolved question."""
    colors = [C_BLUE_L, C_ORANGE, C_GGREEN, C_PURPLE]
    offsets = [(-0.55, 0.42), (0.55, 0.42), (-0.55, -0.42), (0.55, -0.42)]
    pieces = VGroup()
    for (dx, dy), col in zip(offsets, colors):
        p = RoundedRectangle(width=0.85, height=0.85, corner_radius=0.14,
                             fill_color=mc(col), fill_opacity=0.85,
                             stroke_color=mc(C_WHITE), stroke_width=2)
        p.move_to(np.array([dx, dy, 0]))
        p.rotate(math.radians(6 if dx * dy > 0 else -6))
        pieces.add(p)
    q = TXT("?", size=44, color=C_NAVY1, bold=True)
    q.move_to(ORIGIN)
    g = VGroup(pieces, q)
    if symbol:
        lab = TXT(str(symbol), size=28, color=C_CYAN, bold=True)
        lab.next_to(g, DOWN, buff=0.32)
        g.add(lab)
    return g


def viz_mystery_lightbulb(symbol=None):
    """A lightbulb moment — the unknown about to click into place."""
    bulb = Circle(radius=0.58, fill_color=mc(C_GOLD), fill_opacity=0.22,
                  stroke_color=mc(C_GOLD), stroke_width=4)
    bulb.move_to(np.array([0.0, 0.35, 0]))
    base = RoundedRectangle(width=0.42, height=0.30, corner_radius=0.05,
                            fill_color=mc(C_LGRAY), fill_opacity=1.0, stroke_width=0)
    base.move_to(bulb.get_bottom() + DOWN * 0.12)
    rays = VGroup()
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        direction = np.array([math.cos(rad), math.sin(rad), 0])
        ln = Line(bulb.get_center() + 0.72 * direction,
                  bulb.get_center() + 0.95 * direction,
                  stroke_color=mc(C_GOLD), stroke_width=3)
        rays.add(ln)
    q = TXT("?", size=34, color=C_GOLD, bold=True)
    q.move_to(bulb.get_center())
    g = VGroup(rays, bulb, base, q)
    if symbol:
        lab = TXT(str(symbol), size=28, color=C_CYAN, bold=True)
        lab.next_to(g, DOWN, buff=0.30)
        g.add(lab)
    return g


def viz_mystery_brain(symbol=None):
    """A thinking brain, gears turning on the unsolved question."""
    lobes = [(-0.32, 0.20), (0.32, 0.20), (0.0, 0.42),
             (-0.20, -0.10), (0.20, -0.10)]
    blob = VGroup(*[
        Circle(radius=0.42, fill_color=mc(C_PURPLE), fill_opacity=0.85,
              stroke_width=0).move_to(np.array([dx, dy, 0]))
        for dx, dy in lobes
    ])
    outline = Circle(radius=0.78, fill_opacity=0.0,
                     stroke_color=mc(C_PURPLE), stroke_width=3)
    gears = VGroup()
    for dx, dy, r in [(0.55, 0.55, 0.20), (0.82, 0.28, 0.13)]:
        gear = Star(n=8, outer_radius=r, inner_radius=r * 0.65,
                   fill_color=mc(C_CYAN), fill_opacity=1.0, stroke_width=0)
        gear.move_to(np.array([dx, dy, 0]))
        gears.add(gear)
    q = TXT("?", size=30, color=C_WHITE, bold=True)
    q.move_to(ORIGIN)
    g = VGroup(blob, outline, q, gears)
    if symbol:
        lab = TXT(str(symbol), size=28, color=C_CYAN, bold=True)
        lab.next_to(g, DOWN, buff=0.34)
        g.add(lab)
    return g


def viz_mystery_door(symbol=None):
    """A door not yet opened."""
    door = RoundedRectangle(width=1.15, height=1.9, corner_radius=0.10,
                            fill_color=mc("#1E293B"), fill_opacity=1.0,
                            stroke_color=mc(C_GOLD), stroke_width=3.5)
    panel = RoundedRectangle(width=0.85, height=0.75, corner_radius=0.08,
                             fill_color=mc(C_CBG), fill_opacity=1.0,
                             stroke_color=mc(C_GOLD), stroke_width=1.5)
    panel.move_to(door.get_center() + UP * 0.42)
    knob = Dot(point=door.get_center() + np.array([0.38, -0.15, 0]),
              radius=0.08, color=mc(C_GOLD))
    keyhole = TXT("?", size=30, color=C_SEM_KEY, bold=True)
    keyhole.move_to(door.get_center() + DOWN * 0.35)
    glow = RoundedRectangle(width=1.5, height=2.3, corner_radius=0.20,
                            fill_color=mc(C_GOLD), fill_opacity=0.12, stroke_width=0)
    glow.move_to(door.get_center())
    g = VGroup(glow, door, panel, knob, keyhole)
    if symbol:
        lab = TXT(str(symbol), size=28, color=C_CYAN, bold=True)
        lab.next_to(g, DOWN, buff=0.30)
        g.add(lab)
    return g


def viz_mystery_detective(symbol=None):
    """A detective board, clues strung together toward the unknown."""
    board = RoundedRectangle(width=2.2, height=1.6, corner_radius=0.10,
                             fill_color=mc("#5B3610"), fill_opacity=1.0,
                             stroke_color=mc(C_GOLD), stroke_width=2.5)
    positions = [(-0.75, 0.45), (0.70, 0.35), (-0.55, -0.45), (0.60, -0.40)]
    center_pos = np.array([0.0, 0.0, 0])
    pins = [Dot(point=np.array([x, y, 0]), radius=0.06, color=mc(C_RRED))
            for x, y in positions]
    center_pin = Dot(point=center_pos, radius=0.06, color=mc(C_RRED))
    strings = VGroup(*[Line(p.get_center(), center_pin.get_center(),
                            stroke_color=mc(C_RRED), stroke_width=1.5)
                       for p in pins])
    q = TXT("?", size=26, color=C_GOLD, bold=True)
    q.move_to(center_pos + UP * 0.28)
    g = VGroup(board, strings, VGroup(*pins), center_pin, q)
    if symbol:
        lab = TXT(str(symbol), size=28, color=C_CYAN, bold=True)
        lab.next_to(g, DOWN, buff=0.30)
        g.add(lab)
    return g


# Every video's curiosity/mystery moment picks from this list by day,
# so the "little mystery before we start" hook is never the same
# animation twice in a row (see GLOBAL QUALITY RULES in the module
# docstring above: never reuse the same mystery animation).
MYSTERY_VARIANTS = [
    viz_mystery_box,
    viz_mystery_treasure,
    viz_mystery_magnifier,
    viz_mystery_puzzle,
    viz_mystery_lightbulb,
    viz_mystery_brain,
    viz_mystery_door,
    viz_mystery_detective,
]


def viz_mystery_reveal(symbol=None):
    """This video's mystery/hook visual, chosen by lesson day."""
    fn = MYSTERY_VARIANTS[(LESSON_ID - 1) % len(MYSTERY_VARIANTS)]
    return fn(symbol)


def viz_thermometer(temps=None):
    """Thermometer with a mercury level and the temperatures mentioned."""
    tube = RoundedRectangle(width=0.42, height=2.4, corner_radius=0.21,
                            fill_color=mc(C_CBG), fill_opacity=1.0,
                            stroke_color=mc(C_LGRAY), stroke_width=2.5)
    bulb = Circle(radius=0.34, fill_color=mc(C_RRED), fill_opacity=1.0,
                  stroke_color=mc(C_LGRAY), stroke_width=2.5)
    bulb.move_to(tube.get_bottom() + DOWN * 0.12)
    mercury = RoundedRectangle(width=0.20, height=1.35, corner_radius=0.10,
                               fill_color=mc(C_RRED), fill_opacity=1.0,
                               stroke_width=0)
    mercury.move_to(tube.get_bottom() + UP * (1.35 / 2 + 0.08))
    g = VGroup(tube, mercury, bulb)
    if temps:
        labs = VGroup(*[TXT(f"{t}°", size=24, color=C_GOLD, bold=True)
                        for t in temps[:3]]).arrange(DOWN, buff=0.18)
        labs.next_to(g, RIGHT, buff=0.35)
        g = VGroup(g, labs)
    return g


def viz_car(dist=None):
    """Car on a road with an optional distance label."""
    road = Line(LEFT * 2.6, RIGHT * 2.6, stroke_color=mc(C_LGRAY),
                stroke_width=6)
    dashes = VGroup(*[Line(LEFT * 0.18, RIGHT * 0.18,
                           stroke_color=mc(C_GOLD), stroke_width=3
                           ).shift(RIGHT * x + UP * 0.001)
                      for x in np.arange(-2.2, 2.4, 0.8)])
    body = RoundedRectangle(width=1.5, height=0.52, corner_radius=0.16,
                            fill_color=mc(C_BLUE_L), fill_opacity=1.0,
                            stroke_width=0)
    cabin = RoundedRectangle(width=0.75, height=0.38, corner_radius=0.12,
                             fill_color=mc(C_BLUE_D), fill_opacity=1.0,
                             stroke_width=0)
    cabin.move_to(body.get_top() + UP * 0.08)
    w1 = Circle(radius=0.15, fill_color=mc(C_NAVY1), fill_opacity=1.0,
                stroke_color=mc(C_LGRAY), stroke_width=2.5)
    w2 = w1.copy()
    w1.move_to(body.get_bottom() + LEFT * 0.45 + DOWN * 0.05)
    w2.move_to(body.get_bottom() + RIGHT * 0.45 + DOWN * 0.05)
    car = VGroup(body, cabin, w1, w2)
    car.move_to(road.get_left() + RIGHT * 1.0 + UP * 0.55)
    g = VGroup(road, dashes, car)
    if dist:
        lab = TXT(str(dist), size=26, color=C_GOLD, bold=True)
        lab.next_to(road, DOWN, buff=0.28)
        g.add(lab)
    return g


def viz_classroom(n=5):
    """A count of students as rows of people, with the number badge."""
    n = max(1, min(int(n), 12))
    rows = VGroup()
    remaining = n
    while remaining > 0:
        rows.add(viz_people(min(remaining, 6)))
        remaining -= 6
    rows.arrange(DOWN, buff=0.22)
    lab = TXT(f"{n} students", size=26, color=C_GOLD, bold=True)
    lab.next_to(rows, DOWN, buff=0.26)
    return VGroup(rows, lab)


def viz_cake(age=None):
    """Birthday cake with candles — ages and 'every year' stories."""
    base = RoundedRectangle(width=2.0, height=0.85, corner_radius=0.14,
                            fill_color=mc("#B45309"), fill_opacity=1.0,
                            stroke_width=0)
    icing = RoundedRectangle(width=2.0, height=0.30, corner_radius=0.12,
                             fill_color=mc("#FDF2F8"), fill_opacity=1.0,
                             stroke_width=0)
    icing.move_to(base.get_top() + DOWN * 0.13)
    candles = VGroup()
    for x in (-0.55, 0.0, 0.55):
        stick = Rectangle(width=0.09, height=0.42,
                          fill_color=mc(C_CYAN), fill_opacity=1.0,
                          stroke_width=0)
        stick.move_to(base.get_top() + UP * 0.21 + RIGHT * x)
        flame = Dot(radius=0.075, color=mc(C_GOLD))
        flame.move_to(stick.get_top() + UP * 0.07)
        candles.add(VGroup(stick, flame))
    g = VGroup(base, icing, candles)
    if age:
        lab = TXT(f"age = {age}", size=26, color=C_GOLD, bold=True)
        lab.next_to(g, DOWN, buff=0.26)
        g.add(lab)
    return g


def viz_number_line(values, x_min=None, x_max=None):
    """Number line with the given values plotted and labelled."""
    vals = []
    for v in values:
        try:
            vals.append(float(v))
        except Exception:
            pass
    vals = sorted(set(round(v, 3) for v in vals))
    # keep at most 4 values, dropping near-duplicates so labels never collide
    spaced = []
    for v in vals:
        if not spaced or v - spaced[-1] >= 0.4:
            spaced.append(v)
    vals = spaced[:4]
    if not vals:
        vals = [0.5, 1.5]
    lo = math.floor(min(vals + [0])) - 1
    hi = math.ceil(max(vals + [1])) + 1
    if hi - lo > 8:
        lo, hi = math.floor(min(vals)) - 1, math.floor(min(vals)) + 7
    # include_numbers=False: MathTex-free so this never depends on LaTeX
    nl = NumberLine(x_range=[lo, hi, 1], length=6.4,
                    color=mc(C_LGRAY), include_numbers=False)
    g = VGroup(nl)
    for n in range(int(lo), int(hi) + 1):
        tick_lab = TXT(str(n), size=22, color=C_LGRAY)
        tick_lab.next_to(nl.number_to_point(n), DOWN, buff=0.18)
        g.add(tick_lab)
    for i, v in enumerate(vals):
        if v < lo or v > hi:
            continue
        pt = nl.number_to_point(v)
        dot = Dot(point=pt, radius=0.09, color=mc(C_GOLD))
        lab = TXT(f"{v:g}", size=20, color=C_GOLD, bold=True)
        # alternate label heights so nearby values never overlap
        lab.next_to(dot, UP, buff=0.14 if i % 2 == 0 else 0.52)
        g.add(dot, lab)
    return g


# ── Geometric shapes — drawn live with labeled sides whenever the
# narration names one (e.g. "draw a square 1 meter by 1 meter"). Each
# returned VGroup is tagged `_geom_draw = True` so the calling scene can
# Create() it stroke-by-stroke instead of just fading it in.
# ═════════════════════════════════════════════════════════════

def _labeled_side(p1, p2, label, color=None):
    """A line segment with its length labelled just outside the midpoint."""
    ln = Line(p1, p2, stroke_color=mc(color or C_GOLD), stroke_width=5)
    mid = (np.array(p1) + np.array(p2)) / 2
    normal = np.array([-(p2[1] - p1[1]), p2[0] - p1[0], 0.0])
    n_len = np.linalg.norm(normal)
    normal = normal / n_len if n_len > 1e-6 else np.array([0.0, -1.0, 0.0])
    lab = TXT(str(label), size=22, color=C_WHITE, bold=True)
    lab.move_to(mid + normal * 0.32)
    return VGroup(ln, lab)


def viz_square(side=1, unit="m"):
    """A square, drawn live with every side labeled."""
    side = max(0.5, min(float(side), 6.0))
    s = min(1.6, 0.7 + side * 0.15)
    hs = s / 2
    corners = [np.array([-hs, -hs, 0]), np.array([hs, -hs, 0]),
               np.array([hs, hs, 0]), np.array([-hs, hs, 0])]
    lbl = f"{side:g} {unit}"
    sides = VGroup(*[_labeled_side(corners[i], corners[(i + 1) % 4], lbl)
                     for i in range(4)])
    fill = Square(side_length=s, fill_color=mc(C_SEM_DEF),
                 fill_opacity=0.10, stroke_width=0)
    g = VGroup(fill, sides)
    g._geom_draw = True
    return g


def viz_rectangle(w=2, h=1, unit="m"):
    """A rectangle, drawn live with every side labeled."""
    w = max(0.5, min(float(w), 8.0))
    h = max(0.5, min(float(h), 8.0))
    sw = min(3.4, 0.7 + w * 0.35)
    sh = min(2.4, 0.7 + h * 0.35)
    hw, hh = sw / 2, sh / 2
    corners = [np.array([-hw, -hh, 0]), np.array([hw, -hh, 0]),
               np.array([hw, hh, 0]), np.array([-hw, hh, 0])]
    labels = [f"{w:g} {unit}", f"{h:g} {unit}", f"{w:g} {unit}", f"{h:g} {unit}"]
    sides = VGroup(*[_labeled_side(corners[i], corners[(i + 1) % 4], labels[i])
                     for i in range(4)])
    fill = Rectangle(width=sw, height=sh, fill_color=mc(C_SEM_DEF),
                     fill_opacity=0.10, stroke_width=0)
    g = VGroup(fill, sides)
    g._geom_draw = True
    return g


def viz_triangle(base=2, height=1.5, unit="m"):
    """A triangle, drawn live: base labeled with its length, height shown
    as a dashed altitude — never a bare '?' for a side we don't know."""
    base = max(0.5, min(float(base), 8.0))
    height = max(0.5, min(float(height), 8.0))
    sb = min(3.2, 0.7 + base * 0.30)
    sh = min(2.6, 0.7 + height * 0.30)
    p1 = np.array([-sb / 2, -sh / 2, 0])
    p2 = np.array([sb / 2, -sh / 2, 0])
    p3 = np.array([0.0, sh / 2, 0])
    base_side = _labeled_side(p1, p2, f"{base:g} {unit}")
    left_side = Line(p1, p3, stroke_color=mc(C_GOLD), stroke_width=5)
    right_side = Line(p2, p3, stroke_color=mc(C_GOLD), stroke_width=5)
    altitude = DashedLine(np.array([0.0, -sh / 2, 0]), p3,
                          stroke_color=mc(C_CYAN), stroke_width=3)
    alt_lab = TXT(f"h = {height:g} {unit}", size=20, color=C_CYAN, bold=True)
    alt_lab.next_to(altitude, RIGHT, buff=0.12)
    fill = Polygon(p1, p2, p3, fill_color=mc(C_SEM_DEF), fill_opacity=0.10,
                  stroke_width=0)
    g = VGroup(fill, base_side, left_side, right_side, altitude, alt_lab)
    g._geom_draw = True
    return g


def viz_circle_shape(r=1, unit="m"):
    """A circle, drawn live with its radius labeled."""
    r = max(0.5, min(float(r), 6.0))
    sr = min(1.5, 0.5 + r * 0.25)
    circ = Circle(radius=sr, fill_color=mc(C_SEM_DEF), fill_opacity=0.10,
                 stroke_color=mc(C_GOLD), stroke_width=5)
    radius_line = Line(ORIGIN, np.array([sr, 0.0, 0.0]),
                       stroke_color=mc(C_GOLD), stroke_width=5)
    lab = TXT(f"r = {r:g} {unit}", size=22, color=C_WHITE, bold=True)
    lab.next_to(radius_line, DOWN, buff=0.12)
    g = VGroup(circ, radius_line, lab)
    g._geom_draw = True
    return g


def viz_graph():
    """A coordinate-plane graph — animated axes with a plotted curve."""
    x_axis = Arrow(LEFT * 1.6, RIGHT * 1.6, buff=0, stroke_width=3,
                   color=mc(C_LGRAY))
    y_axis = Arrow(DOWN * 1.3, UP * 1.3, buff=0, stroke_width=3,
                   color=mc(C_LGRAY))
    x_lab = TXT("x", size=20, color=C_LGRAY)
    x_lab.next_to(x_axis, RIGHT, buff=0.08)
    y_lab = TXT("y", size=20, color=C_LGRAY)
    y_lab.next_to(y_axis, UP, buff=0.08)
    pts = [np.array([x, 0.5 * x, 0]) for x in np.linspace(-1.4, 1.4, 12)]
    curve = VMobject(stroke_color=mc(C_CYAN), stroke_width=4)
    curve.set_points_smoothly(pts)
    dots = VGroup(*[Dot(p, radius=0.045, color=mc(C_GOLD)) for p in pts[::3]])
    g = VGroup(x_axis, y_axis, x_lab, y_lab, curve, dots)
    g._geom_draw = True
    return g


def viz_angle(deg=60):
    """An angle, drawn live between two rays with its measure labeled."""
    deg = max(10.0, min(float(deg), 170.0))
    rad = math.radians(deg)
    ray1 = Line(ORIGIN, RIGHT * 1.4, stroke_color=mc(C_GOLD), stroke_width=5)
    ray2 = Line(ORIGIN, np.array([1.4 * math.cos(rad), 1.4 * math.sin(rad), 0]),
               stroke_color=mc(C_GOLD), stroke_width=5)
    arc = Arc(radius=0.45, start_angle=0, angle=rad, color=mc(C_CYAN),
             stroke_width=3)
    lab = TXT(f"{int(round(deg))}°", size=24, color=C_CYAN, bold=True)
    mid = rad / 2
    lab.move_to(0.75 * np.array([math.cos(mid), math.sin(mid), 0]))
    g = VGroup(ray1, ray2, arc, lab)
    g._geom_draw = True
    return g


def viz_area(w=2, h=1, unit="m"):
    """A rectangle with its interior filled in, to show area."""
    w = max(0.5, min(float(w), 6.0))
    h = max(0.5, min(float(h), 6.0))
    sw = min(2.6, 0.7 + w * 0.30)
    sh = min(2.0, 0.7 + h * 0.30)
    rect = Rectangle(width=sw, height=sh, stroke_color=mc(C_GOLD),
                     stroke_width=4, fill_color=mc(C_SEM_DEF),
                     fill_opacity=0.55)
    lab = TXT(f"Area = {w:g} × {h:g} {unit}²", size=20, color=C_WHITE,
              bold=True)
    lab.next_to(rect, DOWN, buff=0.22)
    g = VGroup(rect, lab)
    g._geom_draw = True
    return g


def viz_perimeter(w=2, h=1, unit="m"):
    """A rectangle with only its boundary highlighted, to show perimeter."""
    w = max(0.5, min(float(w), 6.0))
    h = max(0.5, min(float(h), 6.0))
    sw = min(2.6, 0.7 + w * 0.30)
    sh = min(2.0, 0.7 + h * 0.30)
    rect = Rectangle(width=sw, height=sh, stroke_color=mc(C_GOLD),
                     stroke_width=7, fill_opacity=0.0)
    total = 2 * (w + h)
    lab = TXT(f"Perimeter = {total:g} {unit}", size=20, color=C_GOLD,
              bold=True)
    lab.next_to(rect, DOWN, buff=0.22)
    g = VGroup(rect, lab)
    g._geom_draw = True
    return g


def viz_callout(text, color=None):
    """A highlighted callout box around a short rule/warning phrase —
    used instead of narrating a rule with no matching visual."""
    col = color or C_RRED
    txt = TXT(str(text), size=26, color=C_WHITE, bold=True, wrap=30,
              max_w=4.6)
    box = SurroundingRectangle(txt, color=mc(col), stroke_width=4,
                               buff=0.28, corner_radius=0.14)
    return VGroup(box, txt)


# ── Dispatcher: sentence → matching illustration ──────────────

_FRAC_WORD_RE = re.compile(r"(\d+)\s*(?:over|/)\s*(\d+)")
_INTO_RE      = re.compile(r"into\s+(\d+)")
_TAKE_RE      = re.compile(r"(?:eat|ate|take|took|use|used|shade|remove|colou?r)\s+(\d+)")
_COUNT_RE     = re.compile(r"(\d+)\s+(pizzas?|chocolates?|apples?|oranges?|mangoes|fruits?|coins?|dollars?|rupees?|cookies?|slices?|pieces?|people|friends?|students?)")
_AMONG_RE     = re.compile(r"(?:among|between)\s+(\d+)")
_UNIT_RE      = re.compile(r"\b(centimeters?|cm|kilometers?|km|meters?|m|feet|ft|units?)\b")


def _first_unit(s):
    m = _UNIT_RE.search(s)
    return m.group(1) if m else "units"


def story_visual(sentence):
    """Return a drawn illustration matching this narration sentence, or None."""
    s = str(sentence).lower()
    frac = _FRAC_WORD_RE.search(s)
    p, q = (int(frac.group(1)), int(frac.group(2))) if frac else (None, None)
    n_into  = int(_INTO_RE.search(s).group(1))  if _INTO_RE.search(s)  else None
    n_take  = int(_TAKE_RE.search(s).group(1))  if _TAKE_RE.search(s)  else None
    n_among = int(_AMONG_RE.search(s).group(1)) if _AMONG_RE.search(s) else None
    n_count = int(_COUNT_RE.search(s).group(1)) if _COUNT_RE.search(s) else None

    ints = [int(x) for x in re.findall(r"-?\d+", s)][:3]

    try:
        if "pizza" in s or ("slice" in s and (n_into or q)):
            return viz_pizza(n_into or q or 4, n_take if n_take is not None else (p or 3))
        if "chocolate" in s or "candy" in s or "cookie" in s:
            share = f"{p}/{q}" if p is not None else None
            return viz_chocolate(n_count or p or 4, n_among, share)
        if any(k in s for k in ("temperature", "thermometer", "degrees",
                                "weather", "celsius")):
            return viz_thermometer(ints)
        if any(k in s for k in ("students", "classroom", "class of")):
            return viz_classroom(n_count or (ints[0] if ints else 5))
        if any(k in s for k in ("birthday", "years old", "your age",
                                "age changes")):
            return viz_cake(ints[0] if ints else None)
        if any(k in s for k in ("car ", " road", " km", " miles", "travel",
                                "distance", "speed")):
            return viz_car(f"{ints[0]} km" if ints else None)
        if any(k in s for k in ("money", "dollar", "rupee", "coin", "price",
                                "cost", "cent", "pound", "euro", "wallet",
                                "earn", "spend")):
            return viz_money(f"${ints[0]}" if ints else None)
        if any(k in s for k in ("apple", "orange", "mango", "fruit", "banana")):
            kind = "orange" if "orange" in s else "apple"
            return viz_fruits(n_count or 3, kind)
        if any(k in s for k in ("mystery", "secret", "unknown number",
                                "chooses a number", "choose a number",
                                "hidden", "guess my number")):
            m_sym = re.search(r"call (?:it|this) ([a-z])\b", s)
            return viz_mystery_reveal(m_sym.group(1) if m_sym else None)
        if "area" in s:
            w = ints[0] if ints else 2
            h = ints[1] if len(ints) > 1 else w
            return viz_area(w, h, _first_unit(s))
        if "perimeter" in s:
            w = ints[0] if ints else 2
            h = ints[1] if len(ints) > 1 else w
            return viz_perimeter(w, h, _first_unit(s))
        if any(k in s for k in ("graph", "coordinate plane", "plot the",
                                "x-axis", "y-axis")):
            return viz_graph()
        if "angle" in s:
            return viz_angle(ints[0] if ints else 60)
        if "square" in s and ("side" in s or "meter" in s or "metre" in s or
                              "cm" in s or "centimet" in s or "unit" in s or
                              ints):
            return viz_square(ints[0] if ints else 1, _first_unit(s))
        if "rectangle" in s and len(ints) >= 2:
            return viz_rectangle(ints[0], ints[1], _first_unit(s))
        if "triangle" in s:
            b = ints[0] if ints else 2
            h = ints[1] if len(ints) > 1 else max(1, round(b * 0.75))
            return viz_triangle(b, h, _first_unit(s))
        if "circle" in s and ("radius" in s or "diameter" in s or ints):
            return viz_circle_shape(ints[0] if ints else 1, _first_unit(s))
        if "number line" in s and p is not None:
            return viz_number_line([p / q if q else p])
        if ("share" in s or "divid" in s) and n_among:
            return viz_chocolate(n_count or p or 4, n_among,
                                 f"{p}/{q}" if p is not None else None)
        if p is not None and q and q != 0 and p <= q:
            return viz_fraction_pie(p, q)
        if p is not None and q:
            return viz_fraction_pie(min(p, 16), max(q, 1))
    except Exception:
        return None
    return None


# ── visual_hints bridge ─────────────────────────────────────────
# Every lesson in curriculum/*.json already carries a human-written
# `visual_hints` field — e.g. "Hook: show a pizza divided into 4,
# highlight 3. Number line: plot these points. Box the 'q ≠ 0' rule
# in red." — describing exactly what to draw, in order. Cell 1/2
# already thread it into the timed script as SCRIPT_DATA["visual_hints"],
# but until now nothing in Cell 4 ever read it back out: every visual
# was guessed from the narration surface words alone. visual_for_beat()
# uses it as a fallback so the curriculum author's own intent — not just
# a keyword guess — decides what appears on screen.

_STOPWORDS = frozenset("""
the a an is are was were be been being to of in on at for with and or but
this that these those it its he she they we you your our their his her
show shows showing draw drawing drawn then now here there so as by from
""".split())


def hint_sentences_for(script_data):
    """Split this lesson's author-written visual_hints into sentences."""
    text = str(script_data.get("visual_hints", ""))
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]


def _stem(word):
    """Crude plural/suffix trim so 'numbers' matches 'number' — good
    enough for a bag-of-words overlap score, not a real stemmer."""
    for suf in ("ing", "es", "ed", "s"):
        if len(word) > len(suf) + 3 and word.endswith(suf):
            return word[: -len(suf)]
    return word


def _best_hint_sentence(beat, hint_sentences):
    """The visual_hints sentence sharing the most significant words with
    this narration beat (simple stemmed bag-of-words overlap)."""
    beat_words = {_stem(w) for w in re.findall(r"[a-z]+", str(beat).lower())
                  if w not in _STOPWORDS}
    if not beat_words:
        return None
    best, best_score = None, 0
    for hs in hint_sentences:
        hs_words = {_stem(w) for w in re.findall(r"[a-z]+", hs.lower())
                    if w not in _STOPWORDS}
        score = len(beat_words & hs_words)
        if score > best_score:
            best, best_score = hs, score
    return best


def visual_for_beat(beat, hint_sentences):
    """The illustration for one narration beat: the beat's own words
    first; if those name nothing drawable, fall back to whichever
    visual_hints sentence overlaps it most."""
    vis = story_visual(beat)
    if vis is not None:
        return vis
    hint = _best_hint_sentence(beat, hint_sentences)
    return story_visual(hint) if hint else None


def fractions_in(texts):
    """All p/q values found in a list of plain-text lines."""
    vals = []
    for t in texts:
        for m in re.finditer(r"(-?\d+)\s*/\s*(\d+)", str(t)):
            p, q = int(m.group(1)), int(m.group(2))
            if q != 0 and abs(p / q) < 50:
                vals.append(p / q)
    return vals


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — BACKGROUND
# ═════════════════════════════════════════════════════════════

def setup_bg(scene_obj):
    """Dark navy background + faint grid + floating accent dots, tinted
    and re-seeded per DAY_ACCENT/LESSON_ID so consecutive videos don't
    share an identical backdrop (foreground/text colors are untouched)."""
    scene_obj.camera.background_color = mc(C_NAVY1)

    bg = Rectangle(
        width=FW + 1.0, height=FH + 1.0,
        fill_color=[mc(C_NAVY1), mc(C_NAVY2_TINT)],
        fill_opacity=1.0,
        stroke_width=0,
    )
    bg.set_z_index(-200)
    scene_obj.add(bg)

    grid = VGroup()
    for x in np.arange(-7.0, 7.5, 1.5):
        ln = Line(np.array([x, -4.2, 0]), np.array([x, 4.2, 0]),
                  stroke_width=0.5, color=mc(DAY_ACCENT))
        ln.set_stroke(opacity=0.04)
        grid.add(ln)
    for y in np.arange(-4.0, 4.5, 1.0):
        ln = Line(np.array([-7.3, y, 0]), np.array([7.3, y, 0]),
                  stroke_width=0.5, color=mc(DAY_ACCENT))
        ln.set_stroke(opacity=0.04)
        grid.add(ln)
    grid.set_z_index(-190)
    scene_obj.add(grid)

    rng = random.Random(1000 + LESSON_ID)
    for _ in range(20):
        x   = rng.uniform(-6.9, 6.9)
        y   = rng.uniform(-3.9, 3.9)
        dot = Dot(point=np.array([x, y, 0]),
                  radius=rng.uniform(0.018, 0.055),
                  color=mc(DAY_ACCENT),
                  fill_opacity=rng.uniform(0.05, 0.16))
        dot.set_z_index(-180)
        scene_obj.add(dot)


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — HEADER
# ═════════════════════════════════════════════════════════════

def make_header(lesson_title="", day=1):
    """Premium top bar: brand block · bold lesson title · DAY badge."""
    hcy = (HEADER_TOP + HEADER_BOT) / 2
    hh  = HEADER_TOP - HEADER_BOT

    bg_bar = Rectangle(
        width=FW, height=hh,
        fill_color=mc(C_HEADER), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([0.0, hcy, 0.0]))

    accent = Rectangle(
        width=FW, height=0.05,
        fill_color=mc(C_GOLD), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([0.0, HEADER_BOT + 0.025, 0.0]))

    logo_circ = Circle(radius=0.30, fill_color=mc(C_GOLD),
                       fill_opacity=1.0, stroke_width=0)
    logo_m = TXT("M", size=24, color=C_NAVY1, bold=True)
    logo_m.move_to(logo_circ.get_center())
    logo_grp = VGroup(logo_circ, logo_m)
    logo_grp.move_to(np.array([-6.35, hcy + 0.06, 0.0]))

    ch_name = TXT(CHANNEL, size=17, color=C_WHITE, bold=True)
    ch_name.next_to(logo_grp, RIGHT, buff=0.14).align_to(logo_grp, UP)

    tagline_txt = TXT(TAGLINE, size=12, color=C_GOLD, bold=True)
    tagline_txt.next_to(ch_name, DOWN, buff=0.06).align_to(ch_name, LEFT)

    lt = str(lesson_title) if lesson_title else str(SCRIPT_DATA.get("title", ""))
    title_mob = TXT(lt, size=24, color=C_WHITE, bold=True, max_w=6.0)
    title_mob.move_to(np.array([0.6, hcy, 0.0]))

    day_bg = RoundedRectangle(
        width=1.55, height=0.58, corner_radius=0.12,
        fill_color=mc(C_PURPLE), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([6.10, hcy, 0.0]))
    day_txt = TXT("DAY " + str(day), size=19, color=C_WHITE, bold=True)
    day_txt.move_to(day_bg.get_center())

    grp = VGroup(bg_bar, accent, logo_grp, ch_name, tagline_txt,
                 title_mob, day_bg, day_txt)
    grp.set_z_index(80)
    return grp


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — FOOTER
# Lesson-journey chips (CONCEPT → EXAMPLE → PRACTICE → MASTER),
# large and bold, with the current stage highlighted.
# ═════════════════════════════════════════════════════════════

_FOOTER_STAGES = [
    ("?",  "CONCEPT",  C_BLUE_L,  ("hook", "concept", "definition")),
    ("★",  "EXAMPLE",  C_GGREEN,  ("formula", "worked_example")),
    ("✎",  "PRACTICE", C_ORANGE,  ("mistakes", "practice")),
    ("✓",  "MASTER",   C_PURPLE,  ("summary",)),
]


def make_footer(active_step=None):
    fcy = (FOOTER_TOP + FOOTER_BOT) / 2
    fh  = FOOTER_TOP - FOOTER_BOT

    bg_bar = Rectangle(
        width=FW, height=fh,
        fill_color=mc(C_FOOTER), fill_opacity=1.0, stroke_width=0,
    ).move_to(np.array([0.0, fcy, 0.0]))

    top_line = Rectangle(
        width=FW, height=0.04,
        fill_color=mc(C_GOLD), fill_opacity=0.55, stroke_width=0,
    ).move_to(np.array([0.0, FOOTER_TOP - 0.02, 0.0]))

    chips = VGroup()
    for icon, label, col, steps in _FOOTER_STAGES:
        active = active_step in steps
        circ = Circle(
            radius=0.27,
            fill_color=mc(col), fill_opacity=1.0 if active else 0.28,
            stroke_color=mc(C_GOLD if active else col),
            stroke_width=3.0 if active else 1.6,
        )
        ic = TXT(icon, size=22, color=C_WHITE if active else C_LGRAY, bold=True)
        ic.move_to(circ.get_center())
        lab = TXT(label, size=17, color=C_GOLD if active else C_LGRAY, bold=True)
        lab.next_to(circ, RIGHT, buff=0.14)
        chips.add(VGroup(circ, ic, lab))
    chips.arrange(RIGHT, buff=0.75)
    chips.move_to(np.array([-1.4, fcy, 0.0]))

    handle = TXT("@MathConceptMadeEasy", size=15, color=C_LGRAY)
    handle.move_to(np.array([5.55, fcy, 0.0]))

    grp = VGroup(bg_bar, top_line, chips, handle)
    grp.set_z_index(80)
    return grp


# ═════════════════════════════════════════════════════════════
# DESIGN SYSTEM — CARD PRIMITIVES
# ═════════════════════════════════════════════════════════════

def make_card(w=4.5, h=5.5, border_color=None, fill_color=None,
              corner_radius=0.15):
    return RoundedRectangle(
        width=w, height=h,
        corner_radius=corner_radius,
        fill_color=mc(fill_color or C_CBG), fill_opacity=0.97,
        stroke_color=mc(border_color or C_BLUE_P), stroke_width=2.0,
    )


def make_card_header(text, width=4.5, color=None):
    strip = RoundedRectangle(
        width=width, height=0.56, corner_radius=0.12,
        fill_color=mc(color or C_BLUE_P), fill_opacity=1.0, stroke_width=0,
    )
    label = TXT(text, size=21, color=C_WHITE, bold=True, max_w=width - 0.30)
    label.move_to(strip.get_center())
    return VGroup(strip, label)


def make_formula_box(latex_str, width=5.6, height=2.0, font_size=60):
    box = RoundedRectangle(
        width=width, height=height, corner_radius=0.18,
        fill_color=mc(C_CBG), fill_opacity=1.0,
        stroke_color=mc(C_SEM_FORMULA), stroke_width=2.5,
    )
    fml = MATH(latex_str, size=font_size, color=C_WHITE, max_w=width - 0.5)
    if fml.height > height - 0.35:
        fml.scale_to_fit_height(height - 0.35)
    fml.move_to(box.get_center())
    return VGroup(box, fml)


def section_pill(text, color=None, width=None, size=22):
    txt = TXT(text, size=size, color=C_WHITE, bold=True)
    w = width or (txt.width + 0.7)
    bg = RoundedRectangle(
        width=w, height=0.60, corner_radius=0.30,
        fill_color=mc(color or C_ORANGE), fill_opacity=1.0, stroke_width=0,
    )
    txt.move_to(bg.get_center())
    return VGroup(bg, txt)


# ═════════════════════════════════════════════════════════════
# SCENE 01 — OPENING  (channel intro, no standard header)
# Five-second curiosity hook FIRST: a glowing mystery box and the
# lesson's real-world question, with a slow documentary zoom.
# Then the title sequence lands on the beat of the narration:
# DAY badge on "Day N", the big title on the topic words,
# the goal bar on "By the end of this lesson".
# ═════════════════════════════════════════════════════════════

class Scene01_Opening(MovingCameraScene):
    def construct(self):
        sd  = get_scene_by_step("opening")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 1))
        setup_bg(self)

        lesson_title = SCRIPT_DATA.get("title", "Today's Lesson")
        beats = sd.get("narration_beats") or split_sentences(sd.get("narration", ""))

        # Scattered faint math symbols
        syms = ["+", "-", "×", "÷", "=", "π", "Σ", "f(x)", "∞", "α"]
        rng2 = random.Random(77)
        for _ in range(16):
            sm = TXT(rng2.choice(syms), size=rng2.randint(20, 40), color=C_BLUE_L)
            sm.move_to(np.array([rng2.uniform(-6.5, 6.5),
                                 rng2.uniform(-3.4, 3.4), 0]))
            sm.set_opacity(rng2.uniform(0.04, 0.11))
            sm.set_z_index(-50)
            self.add(sm)

        # Branding block (top-left)
        logo_circ = Circle(radius=0.42, fill_color=mc(C_GOLD),
                           fill_opacity=1.0, stroke_width=0)
        logo_m = TXT("M", size=32, color=C_NAVY1, bold=True)
        logo_m.move_to(logo_circ.get_center())
        logo_grp = VGroup(logo_circ, logo_m)

        ch_line1 = TXT("Math Concept", size=26, color=C_WHITE, bold=True)
        ch_line2 = TXT("Made Easy",   size=26, color=C_GOLD,  bold=True)
        ch_stack = VGroup(ch_line1, ch_line2).arrange(
            DOWN, buff=0.05, aligned_edge=LEFT)
        brand_row = VGroup(logo_grp, ch_stack).arrange(
            RIGHT, buff=0.20, aligned_edge=UP)
        brand_row.move_to(np.array([-4.75, 3.10, 0]))

        # "LEARN • PRACTICE • MASTER" — a headline element on its own
        # band below the brand row, big and bold
        pill_txt = TXT("LEARN  •  PRACTICE  •  MASTER",
                       size=28, color=C_NAVY1, bold=True)
        pill_bg = RoundedRectangle(
            width=pill_txt.width + 0.9, height=0.82, corner_radius=0.41,
            fill_color=mc(C_GOLD), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, 2.28, 0]))
        pill_glow = RoundedRectangle(
            width=pill_txt.width + 1.10, height=0.98, corner_radius=0.49,
            fill_color=mc(C_GOLD), fill_opacity=0.18, stroke_width=0,
        ).move_to(pill_bg.get_center())
        pill_txt.move_to(pill_bg.get_center())
        pill_grp = VGroup(pill_glow, pill_bg, pill_txt)

        # DAY badge (top-right)
        day_bg = RoundedRectangle(
            width=1.85, height=0.72, corner_radius=0.14,
            fill_color=mc(C_PURPLE), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([5.95, 3.22, 0]))
        day_txt = TXT("DAY " + str(LESSON_ID), size=24, color=C_WHITE, bold=True)
        day_txt.move_to(day_bg.get_center())
        day_grp = VGroup(day_bg, day_txt)

        # Lesson title (two lines — white / gold)
        words = lesson_title.split()
        half  = max(1, len(words) // 2)
        l1_str = " ".join(words[:half])
        l2_str = " ".join(words[half:]) if len(words) > half else lesson_title
        title_l1 = TXT(l1_str, size=68, color=C_WHITE, bold=True, max_w=11.8)
        title_l2 = TXT(l2_str, size=68, color=C_GOLD,  bold=True, max_w=11.8)
        title_grp = VGroup(title_l1, title_l2).arrange(DOWN, buff=0.12)
        title_grp.move_to(np.array([0.0, 0.52, 0]))

        # Goal bar
        goal = SCRIPT_DATA.get("lesson_goal", "")
        goal_txt = TXT("Today: " + goal, size=24, color=C_WHITE,
                       bold=True, wrap=78, max_w=11.6)
        goal_bg = RoundedRectangle(
            width=min(12.4, goal_txt.width + 0.9),
            height=goal_txt.height + 0.42,
            corner_radius=0.16,
            fill_color=mc(C_BLUE_P), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, -1.10, 0]))
        goal_txt.move_to(goal_bg.get_center())
        goal_grp = VGroup(goal_bg, goal_txt)

        # Four bigger promise badges
        badge_data = [
            ("?", "EASY",    "EXPLANATIONS", C_BLUE_P),
            ("◆", "CONCEPT", "CLARITY",      C_GGREEN),
            ("★", "SMART",   "STRATEGIES",   C_ORANGE),
            ("✓", "BETTER",  "RESULTS",      C_PURPLE),
        ]
        badge_mobs = []
        for icon_ch, top_lbl, bot_lbl, col in badge_data:
            circ = Circle(radius=0.80,
                          fill_color=mc(col), fill_opacity=0.16,
                          stroke_color=mc(col), stroke_width=2.6)
            icon_m = TXT(icon_ch, size=30, color=col, bold=True)
            icon_m.move_to(circ.get_center() + UP * 0.24)
            top_m = TXT(top_lbl, size=16, color=col, bold=True)
            top_m.move_to(circ.get_center() + DOWN * 0.14)
            bot_m = TXT(bot_lbl, size=12, color=C_LGRAY, bold=True)
            bot_m.move_to(circ.get_center() + DOWN * 0.40)
            badge_mobs.append(VGroup(circ, icon_m, top_m, bot_m))
        badges_row = VGroup(*badge_mobs).arrange(RIGHT, buff=0.62)
        badges_row.move_to(np.array([0.0, -2.45, 0]))

        footer = make_footer("opening")
        self.add(footer)

        # ── LAYER 1: the mystery hook (first ~8 seconds) ──────
        # The curiosity question is the 2nd narration beat (after
        # "Here is a little mystery before we start.").
        curiosity = beats[1] if len(beats) > 1 else ""
        mystery = viz_mystery_reveal()
        mystery.move_to(np.array([0.0, 1.05, 0]))
        q_txt = TXT(curiosity, size=30, color=C_WHITE, bold=True,
                    wrap=50, max_w=11.0)
        q_txt.move_to(np.array([0.0, -0.85, 0]))

        self.play(FadeIn(mystery, scale=0.6), run_time=0.7)
        try:
            self.play(self.camera.frame.animate.scale(0.92).move_to(
                np.array([0.0, 0.35, 0])), run_time=1.4)
        except Exception:
            pass
        wait_until(self, nar.when_spoken(curiosity), lead=0.25)
        self.play(Write(q_txt), run_time=1.0)
        try:
            self.play(Indicate(mystery, scale_factor=1.06,
                               color=mc(C_SEM_KEY)), run_time=0.8)
        except Exception:
            pass

        # ── Transition: mystery dissolves into the title card ──
        wait_until(self, nar.when_spoken("Hold that thought"), lead=0.20)
        anims = [FadeOut(mystery, scale=0.8), FadeOut(q_txt, shift=DOWN * 0.3)]
        try:
            anims.append(self.camera.frame.animate.scale(1 / 0.92).move_to(ORIGIN))
        except Exception:
            pass
        self.play(*anims, run_time=0.9)

        # ── Title sequence on the narration beat ──────────────
        reveal(self, nar, brand_row, spoken="Welcome to Math Concepts",
               run_time=0.6, anim=lambda m: FadeIn(m, shift=DOWN * 0.12))
        self.play(FadeIn(pill_grp, shift=DOWN * 0.08), run_time=0.5)

        reveal(self, nar, day_grp, spoken="Today is Day", run_time=0.45,
               anim=lambda m: FadeIn(m, shift=LEFT * 0.10))
        wait_until(self, nar.when_spoken(SCRIPT_DATA.get("title", "")), lead=0.25)
        self.play(Write(title_l1), run_time=0.8)
        self.play(Write(title_l2), run_time=0.8)

        reveal(self, nar, goal_grp, spoken="By the end of this lesson",
               run_time=0.5, anim=lambda m: FadeIn(m, shift=UP * 0.08))
        self.play(
            LaggedStart(*[FadeIn(b, shift=UP * 0.14) for b in badge_mobs],
                        lag_ratio=0.22),
            run_time=1.0,
        )
        sync_to_audio(self, sd.get("scene_id", 1))


# ═════════════════════════════════════════════════════════════
# SCENE 02 — HOOK
# The real-world story scene. Each narration sentence that
# mentions a real object (pizza, chocolate, money …) triggers a
# drawn illustration at the exact second it is spoken, with the
# sentence as a clean caption below.
# ═════════════════════════════════════════════════════════════

class Scene02_Hook(Scene):
    def construct(self):
        sd  = get_scene_by_step("hook")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 2))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        self.add(make_header(lesson_title, LESSON_ID), make_footer("hook"))

        beats = sd.get("narration_beats") or split_sentences(sd.get("narration", ""))
        hint_sentences = hint_sentences_for(SCRIPT_DATA)

        pill = section_pill("SEEN IN REAL LIFE", C_ORANGE, size=24)
        pill.move_to(np.array([0.0, CONTENT_TOP - 0.42, 0]))

        stage_c  = np.array([0.0, 0.45, 0])       # where illustrations live
        cap_y    = -2.30                           # caption band

        self.play(FadeIn(pill, shift=DOWN * 0.10), run_time=0.5)

        visuals_on_stage = []
        caption = None

        def set_caption(text):
            nonlocal caption
            new_cap = TXT(text, size=25, color=C_WHITE, wrap=64, max_w=11.8)
            new_cap.move_to(np.array([0.0, cap_y, 0]))
            underline = Rectangle(width=min(new_cap.width + 0.4, 12.0),
                                  height=0.03,
                                  fill_color=mc(C_GOLD), fill_opacity=0.6,
                                  stroke_width=0)
            underline.next_to(new_cap, DOWN, buff=0.16)
            grp = VGroup(new_cap, underline)
            if caption is None:
                self.play(FadeIn(grp, shift=UP * 0.10), run_time=0.45)
            else:
                self.play(FadeOut(caption, run_time=0.25),
                          FadeIn(grp, shift=UP * 0.10, run_time=0.45))
            caption = grp

        for beat in beats:
            t = nar.when_spoken(beat)
            wait_until(self, t, lead=0.35)
            vis = visual_for_beat(beat, hint_sentences)
            if vis is not None:
                if vis.height > 3.1:
                    vis.scale_to_fit_height(3.1)
                if vis.width > 5.4:
                    vis.scale_to_fit_width(5.4)
                visuals_on_stage.append(vis)
                # Re-arrange all visuals side by side on the stage
                stage = VGroup(*visuals_on_stage)
                targets = VGroup(*[v.copy() for v in visuals_on_stage])
                targets.arrange(RIGHT, buff=0.9)
                if targets.width > 12.6:
                    targets.scale_to_fit_width(12.6)
                targets.move_to(stage_c)
                anims = []
                for v, tgt in zip(visuals_on_stage[:-1], targets[:-1]):
                    anims.append(v.animate.become(tgt))
                vis.move_to(targets[-1].get_center())
                vis.scale(targets[-1].width / max(vis.width, 1e-6))
                # Shapes named in the narration (square, triangle …) get
                # drawn stroke-by-stroke instead of just fading in.
                if getattr(vis, "_geom_draw", False):
                    anims.append(Create(vis))
                else:
                    anims.append(FadeIn(vis, scale=0.7))
                self.play(*anims, run_time=0.7)
            set_caption(beat)

        sync_to_audio(self, sd.get("scene_id", 2))


# ═════════════════════════════════════════════════════════════
# SCENE 03 — CONCEPT
# Left: the key idea, sentence by sentence, timed to the voice.
# Right: an automatic visual — a number line of the lesson's
# actual values, a story illustration, or the formula.
# ═════════════════════════════════════════════════════════════

class Scene03_Concept(Scene):
    def construct(self):
        sd  = get_scene_by_step("concept")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 3))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        self.add(make_header(lesson_title, LESSON_ID), make_footer("concept"))

        beats = sd.get("narration_beats") or split_sentences(sd.get("narration", ""))
        content_cy = (CONTENT_TOP + CONTENT_BOT) / 2

        # ── Left: THE KEY IDEA card ───────────────────────────
        left_card = make_card(7.0, 5.4, border_color=C_GGREEN)
        left_card.move_to(np.array([-3.30, content_cy, 0]))
        l_hdr = make_card_header("THE KEY IDEA", 7.0, C_GGREEN)
        l_hdr.move_to(left_card.get_top() + DOWN * (l_hdr.height / 2 + 0.07))

        idea_mobs = []
        for b in beats:
            m = TXT(b, size=24, color=C_WHITE, wrap=44, max_w=6.3)
            idea_mobs.append(m)
        idea_grp = VGroup(*idea_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.34)
        if idea_grp.height > 4.3:
            idea_grp.scale_to_fit_height(4.3)
        idea_grp.move_to(left_card.get_center() + DOWN * 0.24)
        idea_grp.align_to(left_card.get_left() + RIGHT * 0.30, LEFT)

        # ── Right: automatic visual ───────────────────────────
        right_card = make_card(5.6, 5.4, border_color=C_BLUE_P)
        right_card.move_to(np.array([3.60, content_cy, 0]))
        r_hdr = make_card_header("SEE IT", 5.6, C_BLUE_P)
        r_hdr.move_to(right_card.get_top() + DOWN * (r_hdr.height / 2 + 0.07))

        board_plain = sd.get("board_plain", {})
        all_lines   = (board_plain.get("worked_example", []) +
                       board_plain.get("practice", []))
        vals = fractions_in(all_lines)

        hint_sentences = hint_sentences_for(SCRIPT_DATA)
        vis = None
        if vals:
            vis = viz_number_line(vals)
        if vis is None:
            for b in beats:
                vis = visual_for_beat(b, hint_sentences)
                if vis is not None:
                    break
        if vis is None:
            vis = make_formula_box(sd.get("key_formula", ""), 4.8, 1.9)

        if vis.width > 5.0:
            vis.scale_to_fit_width(5.0)
        if vis.height > 3.9:
            vis.scale_to_fit_height(3.9)
        vis.move_to(right_card.get_center() + DOWN * 0.24)

        # ── Animate on the narration beat ─────────────────────
        self.play(FadeIn(left_card), FadeIn(right_card), run_time=0.5)
        self.play(FadeIn(l_hdr), FadeIn(r_hdr), run_time=0.4)

        shown_vis = False
        for b, m in zip(beats, idea_mobs):
            t = nar.when_spoken(b)
            wait_until(self, t, lead=0.30)
            self.play(FadeIn(m, shift=RIGHT * 0.10), run_time=0.45)
            if not shown_vis:
                self.play(FadeIn(vis, scale=0.85), run_time=0.6)
                shown_vis = True

        sync_to_audio(self, sd.get("scene_id", 3))


# ═════════════════════════════════════════════════════════════
# SCENE 04 — DEFINITION
# Big definition card: focus statement in large type, the formula
# compiled below it. Prerequisite and goal chips arrive when the
# narration reaches them.
# ═════════════════════════════════════════════════════════════

class Scene04_Definition(Scene):
    def construct(self):
        sd  = get_scene_by_step("definition")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 4))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        self.add(make_header(lesson_title, LESSON_ID), make_footer("definition"))

        topic    = SCRIPT_DATA.get("title", lesson_title)
        subtopic = SCRIPT_DATA.get("subtopic", "")
        formula  = sd.get("key_formula", SCRIPT_DATA.get("key_formula", ""))

        def_card = make_card(11.6, 3.9, border_color=C_BLUE_P)
        def_card.move_to(np.array([0.0, 0.55, 0]))
        def_hdr = make_card_header("DEFINITION — " + str(topic).upper(),
                                   11.6, C_BLUE_P)
        def_hdr.move_to(def_card.get_top() + DOWN * (def_hdr.height / 2 + 0.07))

        sub_txt = TXT(subtopic, size=30, color=C_WHITE, bold=True,
                      wrap=52, max_w=10.6)
        sub_txt.move_to(def_card.get_center() + UP * 0.55)

        fml = make_formula_box(formula, 6.2, 1.5, font_size=56)
        fml.move_to(def_card.get_center() + DOWN * 0.90)

        prereq = SCRIPT_DATA.get("prerequisite", "Basic arithmetic")
        goal   = SCRIPT_DATA.get("lesson_goal",  "Understand this concept")

        pre_card = make_card(5.6, 1.30, border_color=C_ORANGE)
        pre_card.move_to(np.array([-3.05, -2.25, 0]))
        pre_hdr = make_card_header("YOU ALREADY KNOW", 5.6, C_ORANGE)
        pre_hdr.move_to(pre_card.get_top() + DOWN * (pre_hdr.height / 2 + 0.06))
        pre_txt = TXT(prereq, size=18, color=C_LGRAY, wrap=44, max_w=5.1)
        pre_txt.move_to(pre_card.get_center() + DOWN * 0.16)

        goal_card = make_card(5.6, 1.30, border_color=C_GGREEN)
        goal_card.move_to(np.array([3.05, -2.25, 0]))
        goal_hdr = make_card_header("TODAY'S GOAL", 5.6, C_GGREEN)
        goal_hdr.move_to(goal_card.get_top() + DOWN * (goal_hdr.height / 2 + 0.06))
        goal_txt = TXT(goal, size=18, color=C_LGRAY, wrap=44, max_w=5.1)
        goal_txt.move_to(goal_card.get_center() + DOWN * 0.16)

        # ── Animate on the narration beat ─────────────────────
        self.play(FadeIn(def_card), FadeIn(def_hdr), run_time=0.55)
        reveal(self, nar, sub_txt, spoken="Here is our focus",
               run_time=0.6, anim=lambda m: FadeIn(m, shift=RIGHT * 0.10))
        wait_until(self, nar.when_spoken("In symbols"), lead=0.20)
        self.play(FadeIn(fml[0]), run_time=0.3)
        self.play(Write(fml[1]), run_time=0.9)
        reveal(self, nar, VGroup(pre_card, pre_hdr, pre_txt),
               spoken="You already know", run_time=0.55)
        self.play(FadeIn(goal_card), FadeIn(goal_hdr), FadeIn(goal_txt),
                  run_time=0.5)
        sync_to_audio(self, sd.get("scene_id", 4))


# ═════════════════════════════════════════════════════════════
# SCENE 05 — FORMULA
# The formula is the hero: huge, centered, written exactly when
# the voice says "The formula is". The spoken meaning appears as
# highlighted phrase chips underneath.
# ═════════════════════════════════════════════════════════════

class Scene05_Formula(Scene):
    def construct(self):
        sd  = get_scene_by_step("formula")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 5))

        lesson_title   = SCRIPT_DATA.get("title", "")
        formula_latex  = sd.get("key_formula", SCRIPT_DATA.get("key_formula", ""))
        formula_spoken = sd.get("formula_spoken",
                                SCRIPT_DATA.get("formula_spoken", ""))

        setup_bg(self)
        self.add(make_header(lesson_title, LESSON_ID), make_footer("formula"))

        label = TXT("THE KEY FORMULA", size=34, color=C_GOLD, bold=True)
        label.move_to(np.array([0.0, CONTENT_TOP - 0.55, 0]))

        box = RoundedRectangle(
            width=9.4, height=2.8, corner_radius=0.22,
            fill_color=mc(C_CBG), fill_opacity=1.0,
            stroke_color=mc(C_SEM_FORMULA), stroke_width=3.0,
        ).move_to(np.array([0.0, 0.45, 0]))
        glow = RoundedRectangle(
            width=9.8, height=3.2, corner_radius=0.26,
            fill_color=mc(C_SEM_FORMULA), fill_opacity=0.10, stroke_width=0,
        ).move_to(box.get_center())
        fml = MATH(formula_latex, size=96, color=C_WHITE, max_w=8.6)
        if fml.height > 2.3:
            fml.scale_to_fit_height(2.3)
        fml.move_to(box.get_center())

        # Meaning chips — the formula in words, split into phrases
        parts = [p.strip() for p in
                 re.split(r",|\bwhere\b", str(formula_spoken)) if p.strip()]
        chip_cols = [C_BLUE_P, C_GGREEN, C_ORANGE, C_PURPLE]
        chips = []
        for i, p in enumerate(parts[:4]):
            col = chip_cols[i % 4]
            t = TXT(p, size=22, color=C_WHITE, bold=True, max_w=5.4)
            bg = RoundedRectangle(
                width=t.width + 0.55, height=0.66, corner_radius=0.16,
                fill_color=mc(col), fill_opacity=0.22,
                stroke_color=mc(col), stroke_width=2.0,
            )
            t.move_to(bg.get_center())
            chips.append(VGroup(bg, t))
        chips_row = VGroup(*chips).arrange(RIGHT, buff=0.35)
        if chips_row.width > 12.8:
            chips_row.arrange(DOWN, buff=0.22)
            if chips_row.height > 2.2:
                chips_row.scale_to_fit_height(2.2)
        chips_row.move_to(np.array([0.0, -1.95, 0]))

        # ── Animate on the narration beat ─────────────────────
        self.play(FadeIn(label, shift=DOWN * 0.10), run_time=0.5)
        self.play(FadeIn(glow), FadeIn(box), run_time=0.4)
        wait_until(self, nar.when_spoken("The formula is"), lead=0.15)
        self.play(Write(fml), run_time=1.4)
        wait_until(self, nar.when_spoken("Watch how each part"), lead=0.25)
        self.play(
            LaggedStart(*[FadeIn(c, shift=UP * 0.12) for c in chips],
                        lag_ratio=0.25),
            run_time=1.0,
        )
        try:
            self.play(Circumscribe(box, color=mc(C_GOLD)), run_time=1.1)
        except Exception:
            pass
        sync_to_audio(self, sd.get("scene_id", 5))


# ═════════════════════════════════════════════════════════════
# SCENE 06 — WORKED EXAMPLES
# Full-width board. Every line of working appears at the exact
# second the voice reads it (matched via board_spoken ↔ word
# timestamps). Verdicts render as clean YES / NO pills.
# ═════════════════════════════════════════════════════════════

def build_board_rows(plain_lines, max_w=11.6):
    """Rows for a worked board: question lines bold + numbered,
    working lines in gold, verdict pills at line ends."""
    rows, ex_no = [], 0
    for line in plain_lines:
        head, verdict = split_verdict(line)
        is_q = bool(re.match(r"(?i)ex\s*\d", head)) or head.rstrip().endswith("?")
        parts = []
        if is_q:
            ex_no += 1
            head_clean = re.sub(r"(?i)^ex\s*\d+\s*:\s*", "", head)
            parts.append(number_chip(ex_no))
            parts.append(TXT(head_clean, size=29, color=C_WHITE, bold=True,
                             max_w=max_w - 2.2))
        else:
            parts.append(TXT(head, size=26, color=C_GOLD, max_w=max_w - 2.2))
        if verdict:
            parts.append(verdict_pill(verdict))
        row = VGroup(*parts).arrange(RIGHT, buff=0.30)
        if row.width > max_w:
            row.scale_to_fit_width(max_w)
        rows.append((row, is_q))
    return rows


class Scene06_WorkedExample(Scene):
    def construct(self):
        sd  = get_scene_by_step("worked_example")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 6))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        self.add(make_header(lesson_title, LESSON_ID),
                 make_footer("worked_example"))

        plain_lines  = (sd.get("board_plain", {}) or {}).get("worked_example", [])
        spoken_lines = (sd.get("board_spoken", {}) or {}).get("worked_example", [])
        if not plain_lines:
            plain_lines = ["Apply the formula step by step",
                           "Check every condition", "Verify the answer"]
            spoken_lines = [""] * len(plain_lines)

        pill = section_pill("★  WORKED EXAMPLES", C_BLUE_P, size=24)
        pill.move_to(np.array([0.0, CONTENT_TOP - 0.42, 0]))

        board = make_card(12.6, 4.9, border_color=C_BLUE_P)
        board.move_to(np.array([0.0, -0.42, 0]))

        rows = build_board_rows(plain_lines, max_w=11.6)
        grp = VGroup(*[r for r, _ in rows])
        # extra breathing room before each new question
        grp.arrange(DOWN, aligned_edge=LEFT, buff=0.26)
        for i, (row, is_q) in enumerate(rows):
            if is_q and i > 0:
                row.shift(DOWN * 0.10)
        if grp.height > 4.3:
            grp.scale_to_fit_height(4.3)
        if grp.width > 11.6:
            grp.scale_to_fit_width(11.6)
        grp.move_to(board.get_center())
        grp.align_to(board.get_left() + RIGHT * 0.45, LEFT)

        # ── Animate on the narration beat ─────────────────────
        self.play(FadeIn(pill, shift=DOWN * 0.08), FadeIn(board), run_time=0.6)
        for (row, is_q), spoken in zip(rows, spoken_lines):
            t = nar.when_spoken(spoken) if spoken else None
            wait_until(self, t, lead=0.30)
            if is_q:
                self.play(FadeIn(row, shift=RIGHT * 0.12), run_time=0.5)
            else:
                self.play(Write(row), run_time=0.6)
        sync_to_audio(self, sd.get("scene_id", 6))


def play_countdown(scene_obj, nar, number_words, pos, color=None):
    """Big pulsing countdown digits, each landing on its spoken word.

    The narration literally says "Five. Four. Three. Two. One." so every
    digit appears at the exact moment the voice says it.
    """
    col = color or C_SEM_KEY
    digit_of = {"five": "5", "four": "4", "three": "3", "two": "2", "one": "1"}
    for w in number_words:
        t = nar.when_spoken(w)
        wait_until(scene_obj, t, lead=0.15)
        ring = Circle(radius=0.72, stroke_color=mc(col), stroke_width=4,
                      fill_color=mc(col), fill_opacity=0.10)
        ring.move_to(pos)
        num = TXT(digit_of.get(w.lower(), w), size=64, color=col, bold=True)
        num.move_to(pos)
        grp = VGroup(ring, num)
        grp.set_z_index(90)
        scene_obj.play(FadeIn(grp, scale=1.35), run_time=0.28)
        scene_obj.play(FadeOut(grp, scale=0.75), run_time=0.30)


# ═════════════════════════════════════════════════════════════
# SCENE 07 — COMMON MISTAKES
# The actual mistake sentence(s) on the red side, the actual
# correction on the green side — pulled from the lesson data and
# revealed as the voice reaches each part.
# ═════════════════════════════════════════════════════════════

class Scene07_Mistakes(Scene):
    def construct(self):
        sd  = get_scene_by_step("mistakes")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 7))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        self.add(make_header(lesson_title, LESSON_ID), make_footer("mistakes"))

        cm = sd.get("common_mistake",
                    SCRIPT_DATA.get("common_mistake", ""))
        cm_sents = split_sentences(cm)
        wrong_sents = [s for s in cm_sents
                       if not re.match(r"(?i)\s*correct", s)] or cm_sents[:1]
        right_sents = [s for s in cm_sents
                       if re.match(r"(?i)\s*correct", s)]
        if not right_sents:
            right_sents = cm_sents[1:] or ["Apply the rule carefully, step by step."]

        content_cy = (CONTENT_TOP + CONTENT_BOT) / 2

        warn = section_pill("!  COMMON MISTAKE — DON'T DO THIS", C_RRED,
                            size=24)
        warn.move_to(np.array([0.0, CONTENT_TOP - 0.42, 0]))

        panel_h  = 4.35
        panel_cy = content_cy - 0.48

        left_card = make_card(5.85, panel_h, border_color=C_RRED)
        left_card.move_to(np.array([-3.45, panel_cy, 0]))
        l_hdr = make_card_header("✗  THE WRONG WAY", 5.85, C_RRED)
        l_hdr.move_to(left_card.get_top() + DOWN * (l_hdr.height / 2 + 0.07))

        right_card = make_card(5.85, panel_h, border_color=C_GGREEN)
        right_card.move_to(np.array([3.45, panel_cy, 0]))
        r_hdr = make_card_header("✓  THE RIGHT WAY", 5.85, C_GGREEN)
        r_hdr.move_to(right_card.get_top() + DOWN * (r_hdr.height / 2 + 0.07))

        wrong_mobs = [TXT(s, size=23, color=C_LGRAY, wrap=40, max_w=5.3)
                      for s in wrong_sents[:3]]
        wrong_grp = VGroup(*wrong_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.30)
        if wrong_grp.height > panel_h - 1.3:
            wrong_grp.scale_to_fit_height(panel_h - 1.3)
        wrong_grp.move_to(left_card.get_center() + DOWN * 0.10)

        right_mobs = [TXT(s, size=23, color=C_WHITE, wrap=40, max_w=5.3)
                      for s in right_sents[:3]]
        right_grp = VGroup(*right_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.30)
        if right_grp.height > panel_h - 1.3:
            right_grp.scale_to_fit_height(panel_h - 1.3)
        right_grp.move_to(right_card.get_center() + DOWN * 0.10)

        vs_txt = TXT("VS", size=36, color=C_GOLD, bold=True)
        vs_txt.move_to(np.array([0.0, panel_cy, 0]))

        cross_chip = VGroup(
            Circle(radius=0.34, fill_color=mc(C_RRED), fill_opacity=1.0,
                   stroke_width=0),
            TXT("✗", size=34, color=C_WHITE, bold=True))
        cross_chip[1].move_to(cross_chip[0].get_center())
        cross_chip.move_to(left_card.get_bottom() + UP * 0.50)

        tick_chip = VGroup(
            Circle(radius=0.34, fill_color=mc(C_GGREEN), fill_opacity=1.0,
                   stroke_width=0),
            TXT("✓", size=34, color=C_WHITE, bold=True))
        tick_chip[1].move_to(tick_chip[0].get_center())
        tick_chip.move_to(right_card.get_bottom() + UP * 0.50)

        # ── Animate on the narration beat ─────────────────────
        self.play(FadeIn(warn, shift=DOWN * 0.06), run_time=0.5)

        # ACTIVE LEARNING: "think about what could go wrong" + 3-2-1
        think = TXT("What could go wrong here? Think…", size=28,
                    color=C_SEM_KEY, bold=True, max_w=11.0)
        think.move_to(np.array([0.0, panel_cy + 0.9, 0]))
        reveal(self, nar, think, spoken="think about what could possibly",
               run_time=0.5)
        play_countdown(self, nar, ["Three", "Two", "One"],
                       np.array([0.0, panel_cy - 0.4, 0]), C_SEM_KEY)
        self.play(FadeOut(think), run_time=0.3)

        self.play(FadeIn(left_card), FadeIn(right_card),
                  FadeIn(l_hdr), FadeIn(r_hdr),
                  FadeIn(vs_txt, scale=0.8), run_time=0.6)

        for s, m in zip(wrong_sents[:3], wrong_mobs):
            wait_until(self, nar.when_spoken(s), lead=0.30)
            self.play(FadeIn(m, shift=RIGHT * 0.08), run_time=0.45)
        self.play(FadeIn(cross_chip, scale=0.6), run_time=0.35)

        for s, m in zip(right_sents[:3], right_mobs):
            wait_until(self, nar.when_spoken(s), lead=0.30)
            self.play(FadeIn(m, shift=LEFT * 0.08), run_time=0.45)
        self.play(FadeIn(tick_chip, scale=0.6), run_time=0.35)

        try:
            r_glow = SurroundingRectangle(
                right_card, color=mc(C_GGREEN),
                stroke_width=3.0, buff=0.08, corner_radius=0.18)
            self.play(Create(r_glow), run_time=0.5)
        except Exception:
            pass
        sync_to_audio(self, sd.get("scene_id", 7))


# ═════════════════════════════════════════════════════════════
# SCENE 08 — PRACTICE
# The question appears when it is read out; each solution line
# lands exactly when the voice reaches it; verdicts as pills.
# ═════════════════════════════════════════════════════════════

class Scene08_Practice(Scene):
    def construct(self):
        sd  = get_scene_by_step("practice")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 8))

        lesson_title = SCRIPT_DATA.get("title", "")
        setup_bg(self)
        self.add(make_header(lesson_title, LESSON_ID), make_footer("practice"))

        plain_lines  = (sd.get("board_plain", {}) or {}).get("practice", [])
        spoken_lines = (sd.get("board_spoken", {}) or {}).get("practice", [])
        if not plain_lines:
            plain_lines  = ["Solve today's problem with the formula."]
            spoken_lines = [""]

        # First line(s) up to the one ending in '?' form the question
        q_count = 1
        for i, l in enumerate(plain_lines):
            if l.rstrip().endswith("?"):
                q_count = i + 1
                break
        # include a following enumeration line (e.g. the list of numbers)
        if (q_count < len(plain_lines)
                and not _VERDICT_RE.search(plain_lines[q_count])
                and len(plain_lines[q_count]) < 60
                and "→" not in plain_lines[q_count]):
            q_count += 1
        q_lines, sol_lines = plain_lines[:q_count], plain_lines[q_count:]
        q_spoken, sol_spoken = spoken_lines[:q_count], spoken_lines[q_count:]

        pill = section_pill("✎  YOUR TURN — PRACTICE!", C_ORANGE, size=24)
        pill.move_to(np.array([0.0, CONTENT_TOP - 0.42, 0]))

        q_card = make_card(12.6, 1.65, border_color=C_ORANGE)
        q_card.move_to(np.array([0.0, 1.25, 0]))
        q_mobs = []
        for i, l in enumerate(q_lines):
            m = TXT(l, size=30 if i == 0 else 27,
                    color=C_WHITE if i == 0 else C_GOLD,
                    bold=(i == 0), max_w=11.6)
            q_mobs.append(m)
        q_grp = VGroup(*q_mobs).arrange(DOWN, buff=0.18)
        if q_grp.height > 1.3:
            q_grp.scale_to_fit_height(1.3)
        q_grp.move_to(q_card.get_center())

        sol_card = make_card(12.6, 3.15, border_color=C_GGREEN)
        sol_card.move_to(np.array([0.0, -1.55, 0]))
        sol_hdr = make_card_header("SOLUTION — STEP BY STEP", 12.6, C_GGREEN)
        sol_hdr.move_to(sol_card.get_top() + DOWN * (sol_hdr.height / 2 + 0.07))

        rows = build_board_rows(sol_lines, max_w=11.6)
        sol_grp = VGroup(*[r for r, _ in rows])
        sol_grp.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        if sol_grp.height > 2.2:
            sol_grp.scale_to_fit_height(2.2)
        if sol_grp.width > 11.6:
            sol_grp.scale_to_fit_width(11.6)
        sol_grp.move_to(sol_card.get_center() + DOWN * 0.20)
        sol_grp.align_to(sol_card.get_left() + RIGHT * 0.45, LEFT)

        # ── Animate on the narration beat ─────────────────────
        self.play(FadeIn(pill, shift=DOWN * 0.08), run_time=0.5)
        self.play(FadeIn(q_card), run_time=0.35)
        for m, spoken in zip(q_mobs, q_spoken):
            t = nar.when_spoken(spoken) if spoken else None
            wait_until(self, t, lead=0.30)
            self.play(FadeIn(m, shift=RIGHT * 0.10), run_time=0.45)

        # ACTIVE LEARNING: pause invitation + spoken 5-4-3-2-1 countdown
        pause_pill = section_pill("⏸  PAUSE & TRY IT YOURSELF", C_SEM_THEOREM,
                                  size=22)
        pause_pill.move_to(np.array([0.0, -0.35, 0]))
        reveal(self, nar, pause_pill, spoken="Pause the video now",
               run_time=0.5)
        play_countdown(self, nar, ["Five", "Four", "Three", "Two", "One"],
                       np.array([0.0, -1.7, 0]), C_SEM_KEY)
        self.play(FadeOut(pause_pill), run_time=0.3)

        wait_until(self, nar.when_spoken("let us solve it together"), lead=0.25)
        self.play(FadeIn(sol_card), FadeIn(sol_hdr), run_time=0.5)
        for (row, is_q), spoken in zip(rows, sol_spoken):
            t = nar.when_spoken(spoken) if spoken else None
            wait_until(self, t, lead=0.30)
            self.play(Write(row), run_time=0.55)
        sync_to_audio(self, sd.get("scene_id", 8))


# ═════════════════════════════════════════════════════════════
# SCENE 09 — SUMMARY  (closing slide, no standard header)
# Takeaways land as the voice recaps each one.
# ═════════════════════════════════════════════════════════════

class Scene09_Summary(Scene):
    def construct(self):
        sd  = get_scene_by_step("summary")
        nar = Narration(sd)
        attach_audio(self, sd.get("scene_id", 9))

        lesson_title   = SCRIPT_DATA.get("title", "Today's Lesson")
        formula_plain  = sd.get("formula_plain",
                                latex_to_plain(SCRIPT_DATA.get("key_formula", "")))
        lesson_goal    = SCRIPT_DATA.get("lesson_goal", "")
        subtopic       = SCRIPT_DATA.get("subtopic", "")

        setup_bg(self)
        self.add(make_footer("summary"))

        banner_bg = Rectangle(
            width=FW, height=0.85,
            fill_color=mc(C_BLUE_P), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, 2.85, 0]))
        banner_txt = TXT("✓  LESSON COMPLETE!", size=34, color=C_WHITE, bold=True)
        banner_txt.move_to(banner_bg.get_center())
        banner_grp = VGroup(banner_bg, banner_txt)

        title_mob = TXT(lesson_title, size=46, color=C_GOLD, bold=True,
                        max_w=12.2)
        title_mob.move_to(np.array([0.0, 1.85, 0]))

        # ── MIND MAP — the whole lesson in one picture ────────
        # Center node = the topic; branches draw themselves as the
        # voice recaps each idea (spoken cue → branch appears).
        center_txt = TXT(lesson_title, size=26, color=C_NAVY1, bold=True,
                         wrap=18, max_w=2.6)
        center_bg = Circle(radius=max(1.05, center_txt.width / 2 + 0.28),
                           fill_color=mc(C_GOLD), fill_opacity=1.0,
                           stroke_color=mc(C_ORANGE), stroke_width=3.0)
        center_txt.move_to(center_bg.get_center())
        center_node = VGroup(center_bg, center_txt)
        map_c = np.array([0.0, -0.15, 0])
        center_node.move_to(map_c)

        branch_data = [
            (subtopic or "Master this concept",              C_SEM_DEF,
             "We explored",                np.array([-4.6,  1.10, 0])),
            ("Formula:  " + (formula_plain or "see lesson"), C_SEM_FORMULA,
             "The one formula",            np.array([ 4.6,  1.10, 0])),
            ("Watch out for the common trap",                C_SEM_WRONG,
             "common trap",                np.array([-4.6, -1.55, 0])),
            (lesson_goal or "Apply it with confidence",      C_SEM_CORRECT,
             "our goal",                   np.array([ 4.6, -1.55, 0])),
        ]
        branches = []
        for item, col, cue, pos in branch_data:
            node_txt = TXT(item, size=19, color=C_WHITE, wrap=30, max_w=3.6)
            if node_txt.height > 1.05:
                node_txt.scale_to_fit_height(1.05)
            node_bg = RoundedRectangle(
                width=min(4.2, node_txt.width + 0.5),
                height=node_txt.height + 0.40, corner_radius=0.15,
                fill_color=mc(C_CBG), fill_opacity=1.0,
                stroke_color=mc(col), stroke_width=2.4,
            ).move_to(pos)
            node_txt.move_to(node_bg.get_center())
            node = VGroup(node_bg, node_txt)
            edge = Line(map_c, pos, stroke_color=mc(col), stroke_width=3.0,
                        buff=1.1)
            edge.set_stroke(opacity=0.8)
            branches.append((edge, node, cue))

        cta_txt = TXT("▶  SUBSCRIBE FOR MORE LESSONS!",
                      size=26, color=C_WHITE, bold=True)
        cta_bg = RoundedRectangle(
            width=cta_txt.width + 0.8, height=0.80, corner_radius=0.20,
            fill_color=mc(C_RRED), fill_opacity=1.0, stroke_width=0,
        ).move_to(np.array([0.0, -2.45, 0]))
        cta_txt.move_to(cta_bg.get_center())
        cta_grp = VGroup(cta_bg, cta_txt)

        # ── Animate on the narration beat ─────────────────────
        self.play(FadeIn(banner_grp, shift=DOWN * 0.08), run_time=0.6)
        self.play(Write(title_mob), run_time=0.8)
        wait_until(self, nar.when_spoken("At the center of everything"),
                   lead=0.25)
        self.play(GrowFromCenter(center_node), run_time=0.7)
        for edge, node, cue in branches:
            wait_until(self, nar.when_spoken(cue), lead=0.25)
            self.play(Create(edge), run_time=0.35)
            self.play(FadeIn(node, scale=0.85), run_time=0.40)
        self.play(FadeIn(cta_grp, scale=0.92), run_time=0.5)
        try:
            self.play(Flash(cta_bg, color=mc(C_GOLD),
                            line_length=0.25, num_lines=16,
                            flash_radius=0.9), run_time=0.8)
        except Exception:
            pass
        sync_to_audio(self, sd.get("scene_id", 9))
'''

# ══════════════════════════════════════════════════════════════
# INJECT RUNTIME VALUES INTO MANIM CODE
# ══════════════════════════════════════════════════════════════

def build_manim_source(script: dict) -> str:
    source = MANIM_SCENE_CODE

    # Path placeholders
    source = source.replace("__REPO_ROOT__",   str(REPO_ROOT))
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
# copies each rendered MP4 to renders/lesson_XXX/
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

        # MCME_RENDER_QUALITY: h = 1080p60 (default), k = 4K, l = fast preview
        quality_flag = {
            "k": "-qk", "h": "-qh", "l": "-ql",
        }.get(os.environ.get("MCME_RENDER_QUALITY", "h").lower(), "-qh")

        cmd = [
            "manim",
            quality_flag,
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
            # QA: rendered video must cover the narration audio
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of",
                     "default=noprint_wrappers=1:nokey=1", str(dest)],
                    capture_output=True, text=True)
                vid_dur = float(probe.stdout.strip())
                want = float(scene.get("duration_seconds", 0.0))
                if want and vid_dur < want - 1.5:
                    print(f"    ⚠️  QA: video {vid_dur:.1f}s shorter than "
                          f"audio {want:.1f}s — check sync for this scene.")
            except Exception:
                pass
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

_failed_scenes = [r["step"] for r in render_results if not r["success"]]
if _failed_scenes:
    raise SystemExit(
        f"🛑 Render failed for scenes: {_failed_scenes}. "
        f"Fix the errors above and re-run (autopilot.py --from-stage 4)."
    )
