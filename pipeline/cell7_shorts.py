# ==========================================
# CELL 7: SHORTS GENERATOR — standalone promo Shorts
# CHANNEL: MathConceptsMadeEasy
#
# These are NOT clips cut from the long lesson. Each is its own
# vertical (1080x1920) Manim render: no narration, no voice-over —
# procedurally generated beat-locked music (pipeline/shorts_music.py)
# plus fast, animated, text/graphics-driven storytelling built from the
# lesson's curriculum fields (thumbnail_angle, real_world_hook,
# key_formula, common_mistake, …), designed purely to tease the full
# lesson and drive the click.
#
# Two completely different Shorts are produced per day — different
# hook field, music (BPM + scale), color accent, camera-entry style,
# scene order and CTA — see build_profiles() below.
#
# Every cut lands exactly on a music beat: because the track is
# synthesized by this same run (not sourced externally), the beat grid
# is known in advance, so segment clips are trimmed to the nearest
# beat time before concatenation instead of guessing/detecting beats.
# ==========================================

import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.paths import load_cell1_config, safe_filename, LOGO_PATH
from pipeline.mathtext import latex_to_plain
from pipeline import shorts_music

cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")

lesson_data = cell1_config.CURRICULUM[0]
lesson_id   = lesson_data["id"]
safe_title  = safe_filename(lesson_data["seo_title"])

FINAL_DIR      = cell1_config.FINAL_DIR
THUMBNAILS_DIR = cell1_config.THUMBNAILS_DIR
THUMB_PATH     = THUMBNAILS_DIR / f"Day_{lesson_id:03d}_{safe_title}_Thumb.jpg"

TEMP_DIR = Path("/tmp/manim_shorts")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

TARGET_W, TARGET_H, TARGET_FPS = 1080, 1920, 30


# ══════════════════════════════════════════════════════════════
# CONTENT HELPERS — pull short, screen-safe text from curriculum data
# ══════════════════════════════════════════════════════════════

def _short(text, max_words=8, fallback=""):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        text = fallback
    words = text.split(" ")
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(",.;:") + "…"
    return text


def _first_sentence(text, max_words=10, fallback=""):
    text = str(text or "").strip()
    if not text:
        return fallback
    first = re.split(r"(?<=[.!?])\s+", text)[0]
    return _short(first, max_words=max_words, fallback=fallback)


def _plain(latex_ish):
    try:
        return latex_to_plain(latex_ish)
    except Exception:
        return str(latex_ish)


TOPIC       = lesson_data.get("topic", lesson_data["seo_title"])
SUBTOPIC    = lesson_data.get("subtopic", "")
KEY_FORMULA = lesson_data.get("key_formula", "")
PRACTICE    = (lesson_data.get("board_examples", {}) or {}).get("practice", [])
PRACTICE_PLAIN = _plain(PRACTICE[0]) if PRACTICE else ""


# ══════════════════════════════════════════════════════════════
# TWO STANDALONE SHORTS — different hook, music, colors, motion,
# scene order and CTA. Never reuse a scene between the two.
# ══════════════════════════════════════════════════════════════

def build_profiles():
    seed_a = lesson_id * 7 + 1
    seed_b = lesson_id * 13 + 5

    tease = {
        "key": "TEASE",
        "label": "Curiosity Tease",
        "bpm": 128,
        "scale_name": "major_pop",
        "seed": seed_a,
        "motion_style": "punch",
        "accent_hex":  "#FACC15",
        "accent2_hex": "#F59E0B",
        "segments": [
            {"id": "s1", "type": "flash_text", "target_sec": 2.0,
             "text": _short(lesson_data.get("thumbnail_angle") or TOPIC, 7),
             "subtext": "", "bg_variant": 0, "big": True},
            {"id": "s2", "type": "flash_text", "target_sec": 7.0,
             "text": _first_sentence(lesson_data.get("real_world_hook"), 9,
                                     fallback=f"Here's something about {TOPIC}…"),
             "subtext": "keep watching…", "bg_variant": 1},
            {"id": "s3", "type": "formula_demo", "target_sec": 14.0,
             "formula": KEY_FORMULA,
             "caption": _short(lesson_data.get("formula_spoken"), 8,
                               fallback=SUBTOPIC)},
            {"id": "s4", "type": "flash_text", "target_sec": 4.5,
             "text": "There's a simple trick", "bg_variant": 0},
            {"id": "s5", "type": "flash_text", "target_sec": 4.5,
             "text": "Most people miss this", "bg_variant": 1},
            {"id": "s6", "type": "flash_text", "target_sec": 4.5,
             "text": "It takes 10 seconds", "bg_variant": 0},
            {"id": "s7", "type": "near_reveal", "target_sec": 11.0,
             "formula": KEY_FORMULA,
             "text": "The full answer is in today's lesson"},
            {"id": "s8", "type": "cta", "target_sec": 6.0,
             "line1": "WATCH THE FULL LESSON",
             "line2": _short(TOPIC, 6)},
        ],
    }

    challenge = {
        "key": "CHALLENGE",
        "label": "Mistake Challenge",
        "bpm": 140,
        "scale_name": "minor_drive",
        "seed": seed_b,
        "motion_style": "slide",
        "accent_hex":  "#22D3EE",
        "accent2_hex": "#8B5CF6",
        "segments": [
            {"id": "c1", "type": "flash_text", "target_sec": 2.2,
             "text": "Would YOU make", "subtext": "this mistake?",
             "bg_variant": 1, "big": True},
            {"id": "c2", "type": "mistake_flash", "target_sec": 10.5,
             "text": _first_sentence(lesson_data.get("common_mistake"), 10,
                                     fallback=f"A common {TOPIC} mistake")},
            {"id": "c3", "type": "flash_text", "target_sec": 7.0,
             "text": _short(PRACTICE_PLAIN, 8,
                            fallback=f"So what's actually correct?"),
             "subtext": "think fast…", "bg_variant": 0},
            {"id": "c4", "type": "flash_text", "target_sec": 5.0,
             "text": "Ready for the fix?", "bg_variant": 1},
            {"id": "c5", "type": "flash_text", "target_sec": 5.0,
             "text": "It's easier than you think", "bg_variant": 0},
            {"id": "c6", "type": "near_reveal", "target_sec": 12.0,
             "formula": KEY_FORMULA,
             "text": "See the correct way in today's lesson"},
            {"id": "c7", "type": "cta", "target_sec": 6.0,
             "line1": "WATCH THE FULL LESSON",
             "line2": _short(TOPIC, 6)},
        ],
    }

    return [tease, challenge]


# ══════════════════════════════════════════════════════════════
# MANIM SOURCE TEMPLATE — portrait 1080x1920, no audio (music is
# mixed in during ffmpeg assembly), one Scene subclass per segment.
# ══════════════════════════════════════════════════════════════

MANIM_SHORTS_CODE = r'''
from manim import *
import json, math, random, re, textwrap, sys
from pathlib import Path

sys.path.insert(0, r"__REPO_ROOT__")
from pipeline.mathtext import latex_to_plain

PLAN_PATH  = Path(r"__PLAN_PATH__")
THUMB_PATH = Path(r"__THUMB_PATH__")
LOGO_PATH  = Path(r"__LOGO_PATH__")

with open(PLAN_PATH, "r", encoding="utf-8") as f:
    PLAN = json.load(f)

config.frame_height = 8.0
config.frame_width  = 8.0 * 1080 / 1920
FW, FH = config.frame_width, config.frame_height

C_NAVY1 = "#081B33"
C_NAVY2 = "#0D2045"
C_WHITE = "#FFFFFF"
C_GOLD  = "#FACC15"
C_RRED  = "#EF4444"
C_GGREEN= "#22C55E"
ACCENT  = PLAN["accent_hex"]
ACCENT2 = PLAN["accent2_hex"]
MOTION  = PLAN["motion_style"]

def mc(h):
    return ManimColor(h)

FONT = "DejaVu Sans"

def TXT(s, size=44, color=C_WHITE, bold=True, max_w=None, wrap=None):
    """Clean prose text. Always passes through latex_to_plain first —
    nothing ever appears on screen as raw LaTeX (same contract as the
    main lesson pipeline, pipeline/cell4_animation.py)."""
    s = latex_to_plain(s) or " "
    if wrap:
        s = "\n".join(textwrap.wrap(s, wrap)) or " "
    try:
        t = Text(s, font_size=size, color=mc(color), font=FONT,
                 weight="BOLD" if bold else "NORMAL")
    except Exception:
        t = Text(s.encode("ascii", "ignore").decode() or " ",
                 font_size=size, color=mc(color), font=FONT)
    if max_w and t.width > max_w:
        t.scale_to_fit_width(max_w)
    return t

def MATH(s, size=64, color=C_WHITE, max_w=None):
    """Compiled math. Falls back to clean unicode text — NEVER raw
    LaTeX (e.g. when texlive isn't available in this environment)."""
    raw = str(s)
    try:
        m = MathTex(raw, font_size=size, color=mc(color))
    except Exception:
        m = TXT(raw, size=max(18, int(size * 0.55)), color=color)
    if max_w and m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m

def bg_card(scene_obj, variant=0):
    """Full-bleed background: dark base + accent glow blob, alternating
    corner per variant so consecutive segments don't look identical."""
    scene_obj.camera.background_color = mc(C_NAVY1)
    base = Rectangle(width=FW + 0.4, height=FH + 0.4,
                     fill_color=[mc(C_NAVY1), mc(C_NAVY2)],
                     fill_opacity=1.0, stroke_width=0)
    base.set_z_index(-100)
    corner = np.array([FW * 0.3, FH * 0.28, 0]) * (1 if variant == 0 else -1)
    glow = Circle(radius=FW * 0.65, fill_color=mc(ACCENT if variant == 0 else ACCENT2),
                 fill_opacity=0.12, stroke_width=0)
    glow.move_to(corner)
    glow.set_z_index(-90)
    scene_obj.add(base, glow)
    return base, glow

def camera_entry(scene_obj):
    """A distinct camera move at the start of every segment, so no
    scene ever sits static even before its content animates in."""
    try:
        if MOTION == "punch":
            scene_obj.camera.frame.save_state()
            scene_obj.camera.frame.scale(1.22)
            scene_obj.play(scene_obj.camera.frame.animate.scale(1 / 1.22),
                           run_time=0.35, rate_func=rush_from)
        else:
            scene_obj.camera.frame.save_state()
            scene_obj.camera.frame.shift(RIGHT * 0.9)
            scene_obj.play(scene_obj.camera.frame.animate.shift(LEFT * 0.9),
                           run_time=0.35, rate_func=rush_from)
    except Exception:
        pass

def entry_anim(mobj):
    if MOTION == "punch":
        return FadeIn(mobj, scale=1.35)
    return FadeIn(mobj, shift=(LEFT if MOTION == "slide" else UP) * 1.2)

def pad_to(scene_obj, target_sec):
    try:
        elapsed = float(scene_obj.renderer.time)
    except Exception:
        elapsed = 0.0
    remaining = target_sec - elapsed - 0.05
    if remaining > 0.03:
        scene_obj.wait(remaining)


class _ShortBase(MovingCameraScene):
    SEGMENT_ID = None

    def get_seg(self):
        return next(s for s in PLAN["segments"] if s["id"] == self.SEGMENT_ID)


class ShortFlashText(_ShortBase):
    def construct(self):
        seg = self.get_seg()
        bg_card(self, seg.get("bg_variant", 0))
        camera_entry(self)

        size = 66 if seg.get("big") else 52
        main = TXT(seg.get("text", ""), size=size, color=C_WHITE,
                   max_w=FW - 0.6)
        main.move_to(np.array([0.0, 0.35 if seg.get("subtext") else 0.0, 0]))
        self.play(entry_anim(main), run_time=0.35)

        sub = seg.get("subtext", "")
        if sub:
            sub_m = TXT(sub, size=32, color=ACCENT, max_w=FW - 0.8)
            sub_m.next_to(main, DOWN, buff=0.45)
            self.play(FadeIn(sub_m, shift=UP * 0.15), run_time=0.3)

        try:
            self.play(Indicate(main, scale_factor=1.05, color=mc(ACCENT)),
                      run_time=0.4)
        except Exception:
            pass
        pad_to(self, seg["target_sec"])


class ShortFormulaDemo(_ShortBase):
    def construct(self):
        seg = self.get_seg()
        bg_card(self, 0)
        camera_entry(self)

        box = RoundedRectangle(width=FW - 0.7, height=2.6, corner_radius=0.22,
                               fill_color=mc(C_NAVY2), fill_opacity=1.0,
                               stroke_color=mc(ACCENT), stroke_width=3.5)
        box.move_to(np.array([0.0, 1.0, 0]))
        glow = RoundedRectangle(width=FW - 0.3, height=3.0, corner_radius=0.28,
                                fill_color=mc(ACCENT), fill_opacity=0.10,
                                stroke_width=0)
        glow.move_to(box.get_center())

        label = TXT("THE KEY IDEA", size=30, color=ACCENT, max_w=FW - 0.5)
        label.next_to(box, UP, buff=0.30)
        self.play(FadeIn(label, shift=DOWN * 0.1), run_time=0.3)
        self.play(FadeIn(glow), FadeIn(box), run_time=0.35)

        fml = MATH(seg.get("formula") or r"a=b", size=72, color=C_WHITE,
                   max_w=FW - 1.2)
        fml.move_to(box.get_center())
        self.play(Write(fml), run_time=1.1)

        cap = TXT(seg.get("caption", ""), size=30, color=C_WHITE,
                  max_w=FW - 0.6)
        cap.move_to(np.array([0.0, -1.3, 0]))
        self.play(FadeIn(cap, shift=UP * 0.12), run_time=0.4)

        try:
            self.play(Circumscribe(box, color=mc(ACCENT)), run_time=0.9)
        except Exception:
            pass
        pad_to(self, seg["target_sec"])


class ShortMistakeFlash(_ShortBase):
    def construct(self):
        seg = self.get_seg()
        self.camera.background_color = mc("#2A0A0A")
        base = Rectangle(width=FW + 0.4, height=FH + 0.4,
                         fill_color=[mc("#2A0A0A"), mc(C_NAVY1)],
                         fill_opacity=1.0, stroke_width=0)
        base.set_z_index(-100)
        self.add(base)
        camera_entry(self)

        cross = TXT("✗", size=110, color=C_RRED, max_w=FW - 0.5)
        cross.move_to(np.array([0.0, 1.9, 0]))
        self.play(FadeIn(cross, scale=1.6), run_time=0.3)
        try:
            self.play(Wiggle(cross), run_time=0.5)
        except Exception:
            pass

        tag = TXT("DON'T DO THIS", size=38, color=C_RRED, max_w=FW - 0.5)
        tag.move_to(np.array([0.0, 0.85, 0]))
        self.play(FadeIn(tag, shift=UP * 0.1), run_time=0.3)

        body = TXT(seg.get("text", ""), size=34, color=C_WHITE,
                   max_w=FW - 0.7)
        body.move_to(np.array([0.0, -0.6, 0]))
        self.play(FadeIn(body, shift=UP * 0.1), run_time=0.4)
        pad_to(self, seg["target_sec"])


class ShortNearReveal(_ShortBase):
    def construct(self):
        seg = self.get_seg()
        bg_card(self, 1)
        camera_entry(self)

        fml = MATH(seg.get("formula") or r"?", size=80, color=C_WHITE,
                   max_w=FW - 1.0)
        fml.move_to(np.array([0.0, 0.9, 0]))
        fml.set_opacity(0.22)
        self.play(FadeIn(fml), run_time=0.4)

        body = RoundedRectangle(width=0.62, height=0.5, corner_radius=0.08,
                                fill_color=mc(ACCENT), fill_opacity=1.0,
                                stroke_width=0)
        body.move_to(np.array([0.0, 0.05, 0]))
        shackle = Arc(radius=0.26, start_angle=0, angle=PI,
                     stroke_color=mc(ACCENT), stroke_width=8)
        shackle.move_to(body.get_top() + UP * 0.02)
        lock = VGroup(shackle, body)
        lock.move_to(np.array([0.0, 0.9, 0]))
        self.play(FadeIn(lock, scale=1.4), run_time=0.35)

        txt = TXT(seg.get("text", ""), size=36, color=C_WHITE,
                  max_w=FW - 0.7)
        txt.move_to(np.array([0.0, -1.5, 0]))
        self.play(FadeIn(txt, shift=UP * 0.12), run_time=0.45)
        try:
            self.play(Indicate(lock, color=mc(ACCENT)), run_time=0.5)
        except Exception:
            pass
        pad_to(self, seg["target_sec"])


class ShortCTA(_ShortBase):
    def construct(self):
        seg = self.get_seg()
        bg_card(self, 0)
        camera_entry(self)

        if THUMB_PATH.exists():
            try:
                thumb = ImageMobject(str(THUMB_PATH))
                thumb.scale_to_fit_width(FW - 0.9)
                thumb.move_to(np.array([0.0, 1.55, 0]))
                border = RoundedRectangle(
                    width=thumb.width + 0.08, height=thumb.height + 0.08,
                    corner_radius=0.08, stroke_color=mc(ACCENT),
                    stroke_width=4, fill_opacity=0)
                border.move_to(thumb.get_center())
                self.play(FadeIn(thumb, scale=1.1), FadeIn(border), run_time=0.4)
            except Exception:
                pass

        line1 = TXT(seg.get("line1", "WATCH THE FULL LESSON"), size=40,
                   color=C_WHITE, max_w=FW - 0.5)
        line1.move_to(np.array([0.0, -0.55, 0]))
        self.play(FadeIn(line1, shift=UP * 0.12), run_time=0.35)

        line2 = TXT(seg.get("line2", ""), size=26, color=ACCENT,
                   max_w=FW - 0.6)
        line2.move_to(np.array([0.0, -1.05, 0]))
        self.play(FadeIn(line2), run_time=0.3)

        channel = TXT("Math Concept Made Easy", size=24, color=C_WHITE,
                      max_w=FW - 0.5)
        channel.move_to(np.array([0.0, -1.75, 0]))
        self.play(FadeIn(channel), run_time=0.25)

        # A drawn bell shape (not an emoji glyph — DejaVu Sans doesn't
        # reliably cover the emoji block, which risks a blank tofu box).
        bell_ring = Circle(radius=0.34, stroke_color=mc(ACCENT),
                           stroke_width=4, fill_color=mc(ACCENT),
                           fill_opacity=0.15)
        bell_body = AnnularSector(inner_radius=0.0, outer_radius=0.16,
                                  angle=PI, start_angle=0,
                                  fill_color=mc(C_WHITE), fill_opacity=1.0,
                                  stroke_width=0)
        bell_body.move_to(bell_ring.get_center() + UP * 0.02)
        bell_base = Rectangle(width=0.24, height=0.045,
                              fill_color=mc(C_WHITE), fill_opacity=1.0,
                              stroke_width=0)
        bell_base.move_to(bell_body.get_bottom() + DOWN * 0.02)
        bell_clap = Dot(radius=0.035, color=mc(C_WHITE))
        bell_clap.move_to(bell_base.get_center() + DOWN * 0.06)
        bell_txt = VGroup(bell_body, bell_base, bell_clap)
        bell = VGroup(bell_ring, bell_txt)
        bell.move_to(np.array([0.0, -2.55, 0]))
        sub_txt = TXT("SUBSCRIBE", size=22, color=ACCENT, max_w=FW - 1.2)
        sub_txt.next_to(bell, RIGHT, buff=0.18)
        cta_row = VGroup(bell, sub_txt)
        if cta_row.width > FW - 0.4:
            cta_row.scale_to_fit_width(FW - 0.4)
        cta_row.move_to(np.array([0.0, -2.55, 0]))
        self.play(FadeIn(cta_row, scale=0.85), run_time=0.3)
        try:
            self.play(Indicate(bell_ring, scale_factor=1.25, color=mc(ACCENT)),
                      run_time=0.5)
        except Exception:
            pass
        pad_to(self, seg["target_sec"])


_TYPE_TO_BASE = {
    "flash_text":    ShortFlashText,
    "formula_demo":  ShortFormulaDemo,
    "mistake_flash": ShortMistakeFlash,
    "near_reveal":   ShortNearReveal,
    "cta":           ShortCTA,
}

for _seg in PLAN["segments"]:
    _base = _TYPE_TO_BASE[_seg["type"]]
    _name = f"Seg_{_seg['id']}"
    globals()[_name] = type(_name, (_base,), {"SEGMENT_ID": _seg["id"]})
'''


def build_shorts_source(plan_path: Path) -> str:
    source = MANIM_SHORTS_CODE
    source = source.replace("__REPO_ROOT__", str(REPO_ROOT))
    source = source.replace("__PLAN_PATH__", str(plan_path))
    source = source.replace("__THUMB_PATH__", str(THUMB_PATH))
    source = source.replace("__LOGO_PATH__", str(LOGO_PATH))
    return source


# ══════════════════════════════════════════════════════════════
# RENDER — one manim invocation per segment (portrait resolution),
# then trim every clip to its beat-aligned duration.
# ══════════════════════════════════════════════════════════════

def _beat_align(plan):
    """Snap each segment's target duration to the nearest music beat,
    using this Short's own generated beat grid — so every cut in the
    final concat lands exactly on a beat, not an approximation."""
    total_target = sum(s["target_sec"] for s in plan["segments"])
    _, beat_times = shorts_music.generate_track(
        total_target + 2.0, plan["bpm"], plan["scale_name"], seed=plan["seed"])

    cursor = 0.0
    aligned = []
    for seg in plan["segments"]:
        want_end = cursor + seg["target_sec"]
        best = min(beat_times, key=lambda b: abs(b - want_end)) if beat_times else want_end
        best = max(best, cursor + 0.6)  # never collapse a segment to ~0s
        aligned.append(best - cursor)
        cursor = best
    return aligned, cursor


def render_segment(source_file: Path, class_name: str) -> Path:
    cmd = [
        "manim", "-r", f"{TARGET_W},{TARGET_H}", "--fps", str(TARGET_FPS),
        "--media_dir", str(TEMP_DIR / "media"),
        str(source_file), class_name,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(TEMP_DIR))
    found = sorted(TEMP_DIR.rglob(f"{class_name}.mp4"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not found:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise SystemExit(f"🛑 Segment render failed: {class_name}")
    return found[0]


def render_short(plan: dict) -> Path:
    key = plan["key"]
    print(f"\n  ▶ Rendering Short [{key}] — {len(plan['segments'])} segments…")

    plan_path = TEMP_DIR / f"plan_{key}.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    source_file = TEMP_DIR / f"shorts_{key}.py"
    source_file.write_text(build_shorts_source(plan_path), encoding="utf-8")

    aligned_durations, total_dur = _beat_align(plan)

    clip_paths = []
    for seg, dur in zip(plan["segments"], aligned_durations):
        class_name = f"Seg_{seg['id']}"
        raw = render_segment(source_file, class_name)
        trimmed = TEMP_DIR / f"trim_{key}_{seg['id']}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(raw),
            # tpad clones the last frame if the render came in a hair
            # short of `dur` (rounding); -t then trims to the exact
            # beat-aligned duration either way.
            "-vf", f"tpad=stop_mode=clone:stop_duration={max(dur, 0.5):.2f}",
            "-t", f"{dur:.3f}",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(trimmed),
        ], check=True)
        clip_paths.append(trimmed)
        print(f"    ✅ {seg['type']:14s} [{seg['id']}] → {dur:.2f}s (beat-aligned)")

    return assemble_short(plan, clip_paths, total_dur)


def assemble_short(plan: dict, clip_paths, total_dur: float) -> Path:
    key = plan["key"]

    concat_txt = TEMP_DIR / f"concat_{key}.txt"
    with open(concat_txt, "w") as f:
        for c in clip_paths:
            f.write(f"file '{str(c.absolute())}'\n")
    video_only = TEMP_DIR / f"video_{key}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", str(concat_txt), "-c", "copy", str(video_only),
    ], check=True)

    # ── Music + whoosh SFX on every cut, mixed as one audio track ──
    music, _ = shorts_music.generate_track(
        total_dur, plan["bpm"], plan["scale_name"], seed=plan["seed"])
    # Cut points come from the trimmed clips' real durations (via
    # ffprobe), not the nominal targets, so SFX lands exactly on cut.
    cursor = 0.0
    for idx, clip in enumerate(clip_paths):
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(clip),
        ], capture_output=True, text=True)
        try:
            d = float(probe.stdout.strip())
        except Exception:
            d = 0.0
        cursor += d
        if idx < len(clip_paths) - 1:
            whoosh = shorts_music.generate_whoosh(0.16, seed=plan["seed"] + idx)
            music = shorts_music.mix_into(music, whoosh, max(cursor - 0.05, 0), gain=0.8)

    audio_wav = TEMP_DIR / f"audio_{key}.wav"
    shorts_music.write_wav(audio_wav, music)

    out_path = FINAL_DIR / f"Day_{lesson_id:03d}_{safe_title}_SHORT_{key}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video_only), "-i", str(audio_wav),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-shortest", "-movflags", "+faststart",
        str(out_path),
    ], check=True)

    for p in clip_paths + [concat_txt, video_only, audio_wav]:
        Path(p).unlink(missing_ok=True)

    return out_path


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════

print(f"{'═'*65}")
print(f"  SHORTS ENGINE — Day {lesson_id} (2 standalone promo Shorts, no narration)")
print(f"{'═'*65}")

profiles = build_profiles()
generated = []
for plan in profiles:
    path = render_short(plan)
    size_mb = path.stat().st_size / (1024 * 1024)
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], capture_output=True, text=True)
    dur = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
    generated.append((plan["key"], plan["label"], path, size_mb, dur))

shutil.rmtree(TEMP_DIR, ignore_errors=True)

print(f"\n{'═'*65}")
print(f"  🎉 {len(generated)} STANDALONE SHORTS GENERATED — 1080x1920 (9:16)")
print(f"{'═'*65}")
for key, label, path, size_mb, dur in generated:
    print(f"  📱 [{key:9s}] {label:18s} {path.name}  ({size_mb:.2f} MB, {dur:.1f}s)")
print(f"  📂 Location : {FINAL_DIR}")
print(f"{'═'*65}")
print(f"\n  ▶ Both Shorts are picked up automatically by uploader.youtube_upload,\n"
      f"    posted the same day (see uploader/youtube_upload.py SHORTS_SCHEDULE_UTC).\n")
