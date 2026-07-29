# ==========================================
# CELL 6: THUMBNAIL ENGINE
# CHANNEL: Math Concept Made Easy
# Design: Premium purple/gold badge layout, matching the
# approved channel reference (circular logo badge, DAY ribbon,
# bordered feature strip, torn-paper "NEW SERIES" sticker).
# Every lesson gets a different accent palette and topic-matched
# math motif — both deterministically seeded by lesson_id, so
# re-rendering the same day always reproduces the same thumbnail.
# Renders at 4K then downscales to 1920×1080.
# ==========================================

import sys, json, random, urllib.request, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config, safe_filename, LOGO_PATH
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")

lesson_data = cell1_config.CURRICULUM[0]
lesson_id   = lesson_data['id']
seo_title   = safe_filename(lesson_data['seo_title'])

SCRIPTS_DIR    = cell1_config.SCRIPTS_DIR
THUMBNAILS_DIR = cell1_config.THUMBNAILS_DIR
ASSETS_DIR     = cell1_config.ASSETS_DIR
TIMED_SCRIPT   = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

THUMBNAIL_NAME = f"Day_{lesson_id:03d}_{seo_title}_Thumb.jpg"
THUMBNAIL_PATH = THUMBNAILS_DIR / THUMBNAIL_NAME

if not TIMED_SCRIPT.exists():
    raise SystemExit(f"🛑 Timed script not found at {TIMED_SCRIPT}. Run Cell 3 first.")

with open(TIMED_SCRIPT, "r", encoding="utf-8") as f:
    SCRIPT = json.load(f)

THUMB_ANGLE = SCRIPT.get("title", "Math Lesson").upper()
SUBJECT     = SCRIPT.get("subject", "MATH").upper()
GRADE_TEXT  = str(SCRIPT.get("grade", cell1_config.CURRICULUM[0].get("grade", ""))).strip()
DAY_TEXT    = f"DAY {lesson_id}"
TOPIC       = SCRIPT.get("title", "Math Lesson").upper()
FORMULA     = SCRIPT.get("formula_spoken", "")[:55]

print(f"✅ Timed script loaded → {TIMED_SCRIPT.name}")
print(f"   Angle   : {THUMB_ANGLE}")
print(f"   Topic   : {TOPIC}")
print(f"   Target  : {THUMBNAIL_NAME}\n")

# ── Font download ──────────────────────────────────────────
FONT_BLACK = ASSETS_DIR / "Montserrat-Black.ttf"
FONT_BOLD  = ASSETS_DIR / "Montserrat-Bold.ttf"

FONT_URLS = {
    "Montserrat-Black.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf",
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Black.ttf",
    ],
    "Montserrat-Bold.ttf": [
        "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf",
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Bold.ttf",
    ],
}

for fname, urls in FONT_URLS.items():
    fpath = ASSETS_DIR / fname
    if not fpath.exists():
        for url in urls:
            try:
                print(f"📥 Downloading {fname}...")
                urllib.request.urlretrieve(url, fpath)
                print(f"✅ {fname} downloaded.")
                break
            except Exception:
                continue

# ── Base palette (fixed brand colors — always present) ──────
NAVY1  = (18,   6,  38)    # rich purple-navy (brighter than pure black)
NAVY2  = (58,  16,  92)    # vivid deep purple
WHITE  = (255, 255, 255)
LGRAY  = (229, 231, 235)
BLACK  = (0,   0,   0)
GOLD   = (250, 204, 21)    # brand gold — always used for the wordmark/day number
CREAM  = (245, 238, 219)   # sticker paper color

# ── Per-lesson accent palette (deterministic by lesson_id) ──
# Rotates the *accent* hue (badge fill, glow, brushstroke) per lesson
# while GOLD + NAVY stay fixed, so every thumbnail is visibly
# different but the channel identity never drifts.
_ACCENT_PALETTES = [
    {"name": "purple", "accent": (124,  58, 237), "glow": (168,  85, 247)},
    {"name": "blue",   "accent": ( 37,  99, 235), "glow": ( 59, 130, 246)},
    {"name": "magenta","accent": (190,  24,  93), "glow": (236,  72, 153)},
    {"name": "teal",   "accent": ( 13, 148, 136), "glow": ( 45, 212, 191)},
    {"name": "orange", "accent": (194,  65,  12), "glow": (251, 146,  60)},
]
_palette = _ACCENT_PALETTES[lesson_id % len(_ACCENT_PALETTES)]
ACCENT = _palette["accent"]
GLOW   = _palette["glow"]

_star_seed    = 1000 + lesson_id
_scatter_seed = 2000 + lesson_id

# ── Topic-matched math motif (deterministic keyword match) ──
# Mirrors the story_visual() dispatch pattern used by the animation
# engine (pipeline/cell4_animation.py) — same idea, applied to the
# faint background scatter so the decoration actually relates to
# today's lesson instead of being a fixed generic list.
_MOTIF_SETS = {
    "fraction":    ["2/3 + 1/6 = 5/6", "a/b = a÷c / b÷c", "p/q, q≠0", "3/4", "-2/3 = 4/-5"],
    "algebra":     ["ax + b = 0", "x = (-b±√Δ)/2a", "f(x) = ax²+bx+c", "y = mx + c"],
    "geometry":    ["A = πr²", "a²+b²=c²", "△ABC", "∠θ", "C = 2πr"],
    "trigonometry":["sinθ", "cosθ", "tanθ = opp/adj", "sin²θ+cos²θ=1"],
    "calculus":    ["∫f(x)dx", "d/dx", "lim x→0", "f'(x)"],
    "function":    ["f(x)", "f(g(x))", "f⁻¹(x)", "domain → range"],
    "logarithm":   ["log₂(x)", "ln(x)", "eˣ", "logₐb = c"],
    "statistics":  ["μ, σ", "P(A∩B)", "x̄ = Σx/n", "Σ"],
    "default":     ["a²+b²=c²", "f(x)=ax²+bx+c", "A=πr²", "∑", "∫", "∞"],
}


def _pick_motif_set():
    s = f"{SUBJECT} {TOPIC}".lower()
    if "fraction" in s or "rational" in s:
        return _MOTIF_SETS["fraction"]
    if "trig" in s or "sin" in s or "cos" in s or "tan" in s:
        return _MOTIF_SETS["trigonometry"]
    if "calculus" in s or "derivative" in s or "integral" in s:
        return _MOTIF_SETS["calculus"]
    if "log" in s or "exponent" in s:
        return _MOTIF_SETS["logarithm"]
    if "function" in s or "domain" in s or "range" in s:
        return _MOTIF_SETS["function"]
    if "geometry" in s or "triangle" in s or "circle" in s or "angle" in s:
        return _MOTIF_SETS["geometry"]
    if "statistic" in s or "probability" in s or "mean" in s:
        return _MOTIF_SETS["statistics"]
    if "algebra" in s or "equation" in s or "polynomial" in s:
        return _MOTIF_SETS["algebra"]
    return _MOTIF_SETS["default"]


MOTIF_ITEMS = _pick_motif_set()


def draw_feature_icon(draw, kind, cx, cy, r):
    """Small drawn icon — reliable on every system, unlike emoji glyphs
    which many fonts (including Montserrat) don't include at all."""
    if kind == "target":
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=GOLD, width=6)
        draw.ellipse([cx-r*0.55, cy-r*0.55, cx+r*0.55, cy+r*0.55], outline=GOLD, width=5)
        draw.ellipse([cx-r*0.18, cy-r*0.18, cx+r*0.18, cy+r*0.18], fill=GOLD)
    elif kind == "pencil":
        draw.line([(cx-r*0.6, cy+r*0.6), (cx+r*0.6, cy-r*0.6)], fill=GOLD, width=14)
        draw.polygon([(cx+r*0.55, cy-r*0.75), (cx+r*0.75, cy-r*0.55),
                     (cx+r*0.62, cy-r*0.42)], fill=GOLD)
    elif kind == "check":
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=GOLD, width=6)
        draw.line([(cx-r*0.45, cy), (cx-r*0.1, cy+r*0.35), (cx+r*0.5, cy-r*0.35)],
                  fill=GOLD, width=8, joint="curve")
    elif kind == "bulb":
        draw.ellipse([cx-r*0.6, cy-r, cx+r*0.6, cy+r*0.3], outline=GOLD, width=6)
        draw.rectangle([cx-r*0.25, cy+r*0.2, cx+r*0.25, cy+r*0.5], outline=GOLD, width=5)
    else:
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=GOLD, width=6)


def load_font(path, size):
    try:
        if path and path.exists():
            return ImageFont.truetype(str(path), size)
    except Exception:
        pass
    return ImageFont.load_default()


def make_gradient(w, h, c1, c2):
    import numpy as np
    xs = np.linspace(0, 1, w)
    ys = np.linspace(0, 1, h)
    xv, yv = np.meshgrid(xs, ys)
    t = xv * 0.3 + yv * 0.55
    r = (c1[0]*(1-t) + c2[0]*t).astype('uint8')
    g = (c1[1]*(1-t) + c2[1]*t).astype('uint8')
    b = (c1[2]*(1-t) + c2[2]*t).astype('uint8')
    return Image.fromarray(np.stack([r, g, b], axis=2), 'RGB').filter(ImageFilter.GaussianBlur(4))


def add_stars(draw, w, h, n=140, seed=_star_seed):
    rng = random.Random(seed)
    for _ in range(n):
        x = rng.randint(int(w*0.5), w)
        y = rng.randint(0, int(h * 0.65))
        r = rng.randint(2, 6)
        v = rng.randint(150, 255)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(v, v, min(255, int(v*0.85))))


def draw_math_scatter(draw, w, h, seed=_scatter_seed):
    """Faint scattered math notation, matched to today's lesson topic."""
    rng = random.Random(seed)
    small_f = load_font(FONT_BOLD, 46)
    for item in MOTIF_ITEMS:
        x = rng.randint(int(w*0.48), int(w*0.96))
        y = rng.randint(int(h*0.06), int(h*0.62))
        alpha = rng.randint(30, 70)
        draw.text((x, y), item, font=small_f, fill=(*GLOW, alpha))


def stroke_text(draw, x, y, text, font, fill, stroke_w=10, stroke_col=(0, 0, 0)):
    for dx in range(-stroke_w, stroke_w+1, 3):
        for dy in range(-stroke_w, stroke_w+1, 3):
            if dx or dy:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_col)
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(text, font, max_w, draw, max_lines=3):
    words = text.split()
    lines, cur = [], []
    for word in words:
        cur.append(word)
        if draw.textlength(" ".join(cur), font=font) > max_w:
            cur.pop()
            if cur:
                lines.append(" ".join(cur))
            cur = [word]
        if len(lines) >= max_lines - 1:
            rest = words[words.index(word):]
            lines.append(" ".join(cur[:-1] + rest) if cur[:-1] else " ".join(rest))
            cur = []
            break
    if cur:
        lines.append(" ".join(cur))
    return lines[:max_lines]


def draw_rounded_rect(draw, x1, y1, x2, y2, radius, fill=None, outline=None, outline_w=4):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=outline_w)


def draw_torn_ribbon(draw, x1, y1, x2, y2, fill, jag=14, seed=1):
    """A rectangle with a jagged (torn-cloth) right edge, matching the
    reference image's DAY badge and headline strip treatment."""
    rng = random.Random(seed)
    pts = [(x1, y1)]
    steps = 10
    for i in range(steps + 1):
        yy = y1 + (y2 - y1) * i / steps
        xx = x2 - rng.randint(0, jag)
        pts.append((xx, yy))
    pts.append((x1, y2))
    draw.polygon(pts, fill=fill)


def draw_logo_badge(bg, cx, cy, r):
    """Circular logo badge. Uses the real logo file if the channel has
    uploaded one to assets/logo.png; otherwise draws a placeholder
    monogram badge in the same position/size so the layout is correct
    and the real logo can drop in later with zero code changes."""
    if LOGO_PATH.exists():
        try:
            logo_img = Image.open(LOGO_PATH).convert("RGBA")
            logo_img = logo_img.resize((r*2, r*2), Image.LANCZOS)
            mask = Image.new("L", (r*2, r*2), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, r*2, r*2], fill=255)
            bg.paste(logo_img, (cx - r, cy - r), mask)
            return
        except Exception as e:
            print(f"      ⚠️  Could not load logo at {LOGO_PATH}: {e} — using placeholder badge.")

    # ── Placeholder monogram badge (replace by adding assets/logo.png) ──
    draw = ImageDraw.Draw(bg)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=GOLD, width=14, fill=(12, 6, 22))
    f_m = load_font(FONT_BLACK, int(r * 1.1))
    m_w = int(draw.textlength("M", font=f_m))
    draw.text((cx - m_w//2, cy - int(r*0.62)), "M", font=f_m, fill=ACCENT)
    f_name = load_font(FONT_BOLD, int(r * 0.24))
    name = "MATH CONCEPTS"
    nw = int(draw.textlength(name, font=f_name))
    draw.text((cx - nw//2, cy + int(r*0.42)), name, font=f_name, fill=WHITE)


def build_thumbnail():
    print(f"{'═'*65}")
    print(f"  RENDERING THUMBNAIL — Day {lesson_id} (accent: {_palette['name']}, 4K→1080p)")
    print(f"{'═'*65}\n")

    W, H = 3840, 2160
    MG   = 130

    # ── 1. Gradient background ────────────────────────────────
    bg = make_gradient(W, H, NAVY1, NAVY2)
    bg_rgba = bg.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Radial-ish accent glow behind the logo position (right side)
    glow_cx, glow_cy = int(W*0.74), int(H*0.5)
    for rr in range(1000, 0, -25):
        a = int(55 * (rr / 1000))
        od.ellipse([glow_cx-rr, glow_cy-rr, glow_cx+rr, glow_cy+rr],
                   fill=(*GLOW, a))
    bg_rgba = Image.alpha_composite(bg_rgba, overlay)
    bg = bg_rgba.convert("RGB")
    draw = ImageDraw.Draw(bg)

    # ── 2. Stars + topic-matched math scatter ──────────────────
    add_stars(draw, W, H)
    scatter_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_math_scatter(ImageDraw.Draw(scatter_layer), W, H)
    bg = Image.alpha_composite(bg.convert("RGBA"), scatter_layer).convert("RGB")
    draw = ImageDraw.Draw(bg)

    # ── 3. Fonts ─────────────────────────────────────────────
    f_huge    = load_font(FONT_BLACK, 300)
    f_topic   = load_font(FONT_BLACK, 250)
    f_sub     = load_font(FONT_BOLD,  70)
    f_day     = load_font(FONT_BLACK, 100)
    f_grade   = load_font(FONT_BOLD,  46)
    f_grade_n = load_font(FONT_BLACK, 90)
    f_icon    = load_font(FONT_BLACK, 60)
    f_feat    = load_font(FONT_BOLD,  34)
    f_sticker = load_font(FONT_BLACK, 46)
    f_sticker2= load_font(FONT_BOLD,  34)

    # ── 4. DAY badge — top-left, torn purple ribbon (matches ref) ──
    draw_torn_ribbon(draw, MG-20, 60, MG+520, 220, fill=ACCENT,
                     jag=18, seed=lesson_id)
    day_label = "DAY"
    dl_w = int(draw.textlength(day_label, font=f_day))
    draw.text((MG+20, 95), day_label, font=f_day, fill=WHITE)
    day_num = str(lesson_id)
    draw.text((MG+40+dl_w, 88), day_num, font=f_day, fill=GOLD)

    # ── 5. GRADE ribbon — top-right vertical tag ────────────────
    if GRADE_TEXT:
        grade_w, grade_h = 260, 300
        gx, gy = W - grade_w - 60, 20
        draw.polygon([
            (gx, gy), (gx+grade_w, gy),
            (gx+grade_w, gy+grade_h), (gx+grade_w//2, gy+grade_h-70),
            (gx, gy+grade_h),
        ], fill=(20, 10, 34), outline=GOLD, width=6)
        gt = "GRADE"
        gtw = int(draw.textlength(gt, font=f_grade))
        draw.text((gx + (grade_w-gtw)//2, gy+50), gt, font=f_grade, fill=WHITE)
        gnw = int(draw.textlength(GRADE_TEXT, font=f_grade_n))
        draw.text((gx + (grade_w-gnw)//2, gy+120), GRADE_TEXT, font=f_grade_n, fill=GOLD)

    # ── 6. Logo badge — right side, prominent (matches ref) ─────
    logo_r = 430
    draw_logo_badge(bg, glow_cx, glow_cy, logo_r)
    draw = ImageDraw.Draw(bg)  # bg was pasted into directly; refresh handle

    # ── 7. Headline — large, bold, left-aligned (matches ref) ───
    max_tw = int(W * 0.48)
    lines = wrap_text(THUMB_ANGLE, f_topic, max_tw, draw, max_lines=2)
    ty = 300
    for i, line in enumerate(lines):
        fill = WHITE if i == 0 else GOLD
        stroke_text(draw, MG, ty, line, f_topic, fill, stroke_w=8,
                   stroke_col=(0, 0, 0))
        ty += 270

    # Subtitle strip ("COMPLETE CONCEPT & EXAMPLES" style)
    sub_text = SCRIPT.get("thumbnail_subtitle", "COMPLETE CONCEPT & EXAMPLES").upper()
    sub_y = ty + 20
    sub_w = int(draw.textlength(sub_text, font=f_sub)) + 80
    draw_rounded_rect(draw, MG-20, sub_y, MG-20+sub_w, sub_y+110,
                      radius=8, fill=ACCENT)
    draw.text((MG+20, sub_y+18), sub_text, font=f_sub, fill=WHITE)

    # ── 8. Feature strip — bordered box, 2-4 small feature cards ──
    # Icons are drawn shapes, not emoji glyphs: Montserrat has no emoji
    # coverage, so relying on emoji text silently renders nothing on
    # most systems. A checkmark/target/pencil drawn with primitives
    # always renders, on every machine, every time.
    features = SCRIPT.get("thumbnail_features") or [
        ("target", "VISUAL", "LEARNING"),
        ("pencil", "STEP-BY-STEP", "EXPLANATION"),
    ]
    feat_y = sub_y + 180
    feat_h = 220
    feat_w = int(W * 0.56)
    draw_rounded_rect(draw, MG-20, feat_y, MG-20+feat_w, feat_y+feat_h,
                      radius=14, outline=GOLD, outline_w=5)
    cell_w = feat_w // len(features)
    for i, (icon_kind, line1, line2) in enumerate(features):
        ccx = MG - 20 + cell_w * i + cell_w // 2
        icy = feat_y + 60
        draw_feature_icon(draw, icon_kind, ccx, icy, 42)
        l1w = int(draw.textlength(line1, font=f_feat))
        draw.text((ccx - l1w//2, feat_y + 125), line1, font=f_feat, fill=WHITE)
        l2w = int(draw.textlength(line2, font=f_feat))
        draw.text((ccx - l2w//2, feat_y + 168), line2, font=f_feat, fill=LGRAY)
        if i > 0:
            sep_x = MG - 20 + cell_w * i
            draw.line([(sep_x, feat_y+20), (sep_x, feat_y+feat_h-20)],
                      fill=GOLD, width=3)

    # ── 9. "NEW SERIES · DAILY VIDEOS" torn-paper sticker ────────
    sticker_w, sticker_h = 560, 190
    sx, sy = W - sticker_w - 70, H - sticker_h - 260
    rng = random.Random(lesson_id + 500)
    pts = []
    top_jag = [ (sx + int(sticker_w*f), sy + rng.randint(-14, 14))
                for f in (0, 0.25, 0.5, 0.75, 1.0) ]
    pts.extend(top_jag)
    pts.append((sx+sticker_w, sy+sticker_h))
    pts.append((sx, sy+sticker_h))
    draw.polygon(pts, fill=CREAM)
    ns1, ns2 = "NEW", "SERIES"
    draw.text((sx+30, sy+25), ns1, font=f_sticker, fill=(20, 10, 34))
    n1w = int(draw.textlength(ns1, font=f_sticker))
    draw.text((sx+40+n1w, sy+25), ns2, font=f_sticker, fill=ACCENT)
    daily_x, daily_y = sx+30, sy+95
    draw.polygon([(daily_x, daily_y+5), (daily_x, daily_y+38),
                 (daily_x+28, daily_y+21)], fill=(20, 10, 34))
    draw.text((daily_x+42, daily_y), "DAILY VIDEOS", font=f_sticker2, fill=(20, 10, 34))

    # ── 10. Bottom tagline banner ────────────────────────────────
    banner_h = 130
    by0 = H - banner_h
    draw.rectangle([0, by0, W, H], fill=(6, 2, 14))
    draw.rectangle([0, by0, W, by0+5], fill=GOLD)
    tagline_a, tagline_b = "FROM BASICS", " TO BRILLIANCE"
    ta_w = int(draw.textlength(tagline_a, font=f_sub))
    tb_w = int(draw.textlength(tagline_b, font=f_sub))
    total_w = ta_w + tb_w
    tx0 = MG
    draw.text((tx0, by0 + 35), tagline_a, font=f_sub, fill=WHITE)
    draw.text((tx0 + ta_w, by0 + 35), tagline_b, font=f_sub, fill=GOLD)

    # ── 11. Downscale 4K → 1920×1080 ────────────────────────────
    print("  🔬 Downsampling 4K → 1920×1080 (LANCZOS)...")
    final = bg.resize((1920, 1080), Image.LANCZOS)
    final.save(THUMBNAIL_PATH, format="JPEG", quality=96)

    size_kb = THUMBNAIL_PATH.stat().st_size // 1024
    print(f"\n{'═'*65}")
    print(f"  🎉 THUMBNAIL GENERATED — accent: {_palette['name']}")
    print(f"{'═'*65}")
    print(f"  ✅ File     : {THUMBNAIL_NAME}")
    print(f"  💾 Size     : {size_kb} KB")
    print(f"  📐 Size     : 1920×1080 px")
    print(f"  🎨 Accent   : {_palette['name']}")
    print(f"  🧩 Motif set: {MOTIF_ITEMS[:3]}...")
    if not LOGO_PATH.exists():
        print(f"  ⚠️  No logo file at {LOGO_PATH} — placeholder monogram badge used.")
    print(f"  📂 Location : {THUMBNAIL_PATH.parent}")
    print(f"{'═'*65}")


build_thumbnail()
