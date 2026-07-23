# ==========================================
# CELL 6: THUMBNAIL ENGINE
# CHANNEL: Math Concept Made Easy
# Design: Premium dark navy — matches channel brand
# Renders at 4K then downscales to 1920×1080
# ==========================================

import sys, json, random, re, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config, safe_filename
from pipeline.constants import day_color
from pipeline.mathtext import latex_to_plain
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

THUMB_ANGLE = SCRIPT.get("thumbnail_angle", SCRIPT["title"]).upper()
SUBJECT     = SCRIPT.get("subject", "MATH").upper()
DAY_TEXT    = f"DAY {lesson_id:02d}"
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

# ── Color palette ──────────────────────────────────────────
NAVY1  = (8,   27,  51)    # #081B33
NAVY2  = (16,  44,  87)    # #102C57
BLUE_P = (37,  99,  235)   # #2563EB
BLUE_L = (59,  130, 246)   # #3B82F6
BLUE_D = (29,  78,  216)   # #1D4ED8
GOLD   = (250, 204, 21)    # #FACC15
ORANGE = (245, 158, 11)    # #F59E0B
GREEN  = (34,  197, 94)    # #22C55E
PURPLE = (139, 92,  246)   # #8B5CF6
WHITE  = (255, 255, 255)
LGRAY  = (229, 231, 235)   # #E5E7EB
BLACK  = (0,   0,   0)
FOOTER = (5,   13,  26)    # #050D1A

# Rotating per-day theme (same source as Cell 4's video background and
# DAY badge, so a given day matches across the video and its thumbnail).
# Only the background gradient, DAY badge, title accent line, and hero
# symbol use this — logo, footer, and feature badges stay fixed.
def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


_PALETTE   = day_color(lesson_id)
DAY_BG1    = hex_rgb(_PALETTE["bg1"])
DAY_BG2    = hex_rgb(_PALETTE["bg2"])
DAY_ACCENT = hex_rgb(_PALETTE["accent"])


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
    t = xv * 0.35 + yv * 0.65
    r = (c1[0]*(1-t) + c2[0]*t).astype('uint8')
    g = (c1[1]*(1-t) + c2[1]*t).astype('uint8')
    b = (c1[2]*(1-t) + c2[2]*t).astype('uint8')
    return Image.fromarray(
        __import__('numpy').stack([r, g, b], axis=2), 'RGB'
    ).filter(ImageFilter.GaussianBlur(4))


def add_stars(draw, w, h, n=180, seed=42):
    rng = random.Random(seed)
    for _ in range(n):
        x = rng.randint(0, w)
        y = rng.randint(0, int(h * 0.72))
        r = rng.randint(2, 7)
        v = rng.randint(60, 180)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(v, v, int(v*1.2)))


def draw_math_scatter(draw, w, h, font, seed=77):
    """Faint scattered math formulas in background."""
    rng = random.Random(seed)
    items = ["a²+b²=c²", "f(x)=ax²+bx+c", "A=πr²",
             "x = (-b±√Δ)/2a", "sinθ", "∑", "∫", "∞"]
    for item in items:
        x = rng.randint(int(w*0.05), int(w*0.95))
        y = rng.randint(int(h*0.08), int(h*0.70))
        alpha = rng.randint(25, 60)
        col = (BLUE_L[0], BLUE_L[1], BLUE_L[2])
        # Use smaller font for scatter
        try:
            small_f = ImageFont.truetype(str(FONT_BOLD), 52) if FONT_BOLD.exists() else font
        except Exception:
            small_f = font
        draw.text((x, y), item, font=small_f, fill=(*col, alpha))


def stroke_text(draw, x, y, text, font, fill, stroke_w=10, stroke_col=(0, 0, 0)):
    for dx in range(-stroke_w, stroke_w+1, 3):
        for dy in range(-stroke_w, stroke_w+1, 3):
            if dx or dy:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_col)
    draw.text((x + stroke_w//2, y + stroke_w//2), text, font=font,
              fill=tuple(max(0, c-60) for c in fill))
    draw.text((x, y), text, font=font, fill=fill)


def center_text_x(draw, text, font, canvas_w):
    w = int(draw.textlength(text, font=font))
    return (canvas_w - w) // 2


def wrap_text(text, font, max_w, draw):
    """Greedy word-wrap — every returned line is guaranteed to fit
    within max_w. If the result needs more lines than the caller wants,
    build_thumbnail() shrinks the font and retries rather than letting
    a line overflow the canvas."""
    words = text.split()
    lines, cur = [], []
    for word in words:
        trial = cur + [word]
        if draw.textlength(" ".join(trial), font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines


def draw_rounded_rect(draw, x1, y1, x2, y2, radius, fill=None, outline=None, outline_w=4):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=outline_w)


def hero_symbol(script: dict, lesson_id: int) -> str:
    """A short, thumbnail-worthy symbol for this lesson (e.g. '√2'),
    extracted from the key formula. Falls back to the day number so
    every lesson — not just ones with a clean root/fraction — gets a
    hero badge."""
    plain = latex_to_plain(script.get("key_formula", ""))
    m = re.search(r"√\(([^)]{1,4})\)", plain)
    if m:
        return "√" + m.group(1)
    tokens = [t for t in re.split(r"[\s,]+", plain) if t]
    short = [t for t in tokens if 1 <= len(t) <= 5 and re.search(r"[0-9A-Za-zπ√]", t)]
    if short:
        return short[0]
    return f"D{lesson_id}"


def build_thumbnail():
    print(f"{'═'*65}")
    print(f"  RENDERING THUMBNAIL — Premium Brand Design (4K→1080p)")
    print(f"{'═'*65}\n")

    W, H = 3840, 2160
    MG   = 120      # margin

    # ── 1. Gradient background (rotates per day) ──────────────
    bg = make_gradient(W, H, DAY_BG1, DAY_BG2)

    # Use RGBA for transparency support
    bg_rgba = bg.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Diagonal light band top-right
    od.polygon([(W//2, 0), (W, 0), (W, H//3)],
               fill=(BLUE_L[0], BLUE_L[1], BLUE_L[2], 30))

    bg_rgba = Image.alpha_composite(bg_rgba, overlay)
    bg = bg_rgba.convert("RGB")
    draw = ImageDraw.Draw(bg)

    # ── 2. Stars ──────────────────────────────────────────────
    add_stars(draw, W, H)

    # ── 3. Load fonts ─────────────────────────────────────────
    f_huge   = load_font(FONT_BLACK, 380)
    f_large  = load_font(FONT_BLACK, 280)
    f_medium = load_font(FONT_BLACK, 180)
    f_small  = load_font(FONT_BOLD,  120)
    f_tiny   = load_font(FONT_BOLD,   90)
    f_badge  = load_font(FONT_BLACK, 140)

    # ── 4. Scattered math (very faint, behind everything) ─────
    # Use an RGBA layer so we can set opacity
    math_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(math_layer)
    draw_math_scatter(md, W, H, f_small)
    bg_rgba = Image.alpha_composite(bg.convert("RGBA"), math_layer)
    bg = bg_rgba.convert("RGB")
    draw = ImageDraw.Draw(bg)

    # ── 5. Top bar: Logo + channel name ───────────────────────
    TOP_BAR_H = 280

    # Logo circle (yellow)
    logo_cx, logo_cy, logo_r = 200, 140, 100
    draw.ellipse([logo_cx-logo_r, logo_cy-logo_r,
                  logo_cx+logo_r, logo_cy+logo_r], fill=GOLD)
    # M inside
    m_w = int(draw.textlength("M", font=f_medium))
    draw.text((logo_cx - m_w//2, logo_cy - 80), "M",
              font=f_medium, fill=(8, 27, 51))

    # Channel name
    ch1 = "Math Concept"
    ch2 = "Made Easy"
    draw.text((340, 50),  ch1, font=f_small, fill=WHITE)
    draw.text((340, 160), ch2, font=f_small, fill=GOLD)

    # Tagline under channel name
    tag = "LEARN  •  PRACTICE  •  MASTER"
    draw.text((345, 265), tag, font=f_tiny, fill=LGRAY)

    # ── 6. LEARN • PRACTICE • MASTER pill (top center) ───────
    pill_text = "LEARN  •  PRACTICE  •  MASTER"
    pill_w = int(draw.textlength(pill_text, font=f_small)) + 100
    logo_right = 340 + max(int(draw.textlength(ch1, font=f_small)),
                          int(draw.textlength(ch2, font=f_small)))
    pill_x = max((W - pill_w) // 2 + 300, logo_right + 60)
    pill_y = 50
    pill_h = 140
    draw_rounded_rect(draw, pill_x, pill_y,
                      pill_x + pill_w, pill_y + pill_h,
                      radius=70, fill=GOLD)
    pt_w = int(draw.textlength(pill_text, font=f_small))
    draw.text((pill_x + (pill_w - pt_w)//2, pill_y + 22),
              pill_text, font=f_small, fill=(8, 27, 51))

    # ── 7. DAY badge (top right, rotates per day) ─────────────
    badge_w, badge_h = 520, 190
    bx = W - badge_w - 80
    by = 60
    draw_rounded_rect(draw, bx, by, bx+badge_w, by+badge_h,
                      radius=30, fill=DAY_ACCENT)
    dt_w = int(draw.textlength(DAY_TEXT, font=f_badge))
    draw.text((bx + (badge_w - dt_w)//2, by + 25),
              DAY_TEXT, font=f_badge, fill=WHITE)

    # ── 7b. Hero symbol badge — glow pedestal, rotates per day ─
    # Kept small and tucked under the DAY badge, with the title's max
    # width reserving this corner (below), so long titles never collide.
    hero = hero_symbol(SCRIPT, lesson_id)
    hero_r = 150
    hero_cx = bx + badge_w // 2
    hero_cy = by + badge_h + 40 + hero_r

    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    gd.ellipse([hero_cx-hero_r-60, hero_cy-hero_r-60,
                hero_cx+hero_r+60, hero_cy+hero_r+60],
               fill=(*DAY_ACCENT, 70))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(40))
    bg_rgba = Image.alpha_composite(bg.convert("RGBA"), glow_layer)
    bg = bg_rgba.convert("RGB")
    draw = ImageDraw.Draw(bg)

    draw.ellipse([hero_cx-hero_r, hero_cy-hero_r,
                  hero_cx+hero_r, hero_cy+hero_r], fill=NAVY2)
    draw.ellipse([hero_cx-hero_r, hero_cy-hero_r,
                  hero_cx+hero_r, hero_cy+hero_r],
                 outline=DAY_ACCENT, width=8)
    hero_accent_stroke = tuple(max(0, c - 80) for c in DAY_ACCENT)
    hw = int(draw.textlength(hero, font=f_medium))
    stroke_text(draw, hero_cx - hw//2, hero_cy - 90, hero, f_medium, WHITE,
               stroke_w=8, stroke_col=hero_accent_stroke)

    # ── 8. Main hook text (center, auto-shrinks to fit 3 lines) ──
    # Extra margin reserved so the title never reaches into the hero
    # badge's top-right corner regardless of wrapping.
    max_tw = W - MG*2 - 700
    title_size = 380
    for candidate in (380, 340, 300, 260, 220, 190):
        f_try = load_font(FONT_BLACK, candidate)
        trial = wrap_text(THUMB_ANGLE, f_try, max_tw, draw)
        if len(trial) <= 3:
            title_size = candidate
            break
    f_huge = load_font(FONT_BLACK, title_size)
    lines = wrap_text(THUMB_ANGLE, f_huge, max_tw, draw)[:3]

    line_h = int(title_size * 1.12)
    n = len(lines)
    total_text_h = n * line_h
    text_start_y = (H - total_text_h) // 2 - 50

    accent_stroke = tuple(max(0, c - 80) for c in DAY_ACCENT)
    for i, line in enumerate(lines):
        if n == 1:
            fill, stroke = DAY_ACCENT, accent_stroke
        elif i == 0 or i == n - 1:
            fill, stroke = WHITE, (0, 0, 0)
        else:
            fill, stroke = DAY_ACCENT, accent_stroke
        tw = int(draw.textlength(line, font=f_huge))
        tx = max(MG, (W - tw) // 2)
        stroke_text(draw, tx, text_start_y + i * line_h, line,
                    f_huge, fill, stroke_w=16, stroke_col=stroke)

    # Accent-colored brushstroke behind bottom title line (rotates per day)
    if len(lines) >= 2:
        last_y = text_start_y + (len(lines)-1) * line_h
        last_w = int(draw.textlength(lines[-1], font=f_huge))
        brush_x = max(MG - 40, (W - last_w)//2 - 40)
        brush_col = tuple(int(c * 0.55) for c in DAY_ACCENT)
        draw_rounded_rect(draw,
                          brush_x, last_y - 20,
                          brush_x + last_w + 80, last_y + 380,
                          radius=20,
                          fill=brush_col,
                          outline=None)
        # Redraw last line on top
        tw = int(draw.textlength(lines[-1], font=f_huge))
        tx = max(MG, (W - tw) // 2)
        stroke_text(draw, tx, last_y, lines[-1],
                    f_huge, WHITE, stroke_w=10, stroke_col=(0, 0, 0))

    # ── 9. Feature badge circles ──────────────────────────────
    badges = [
        ("📖", "EASY\nEXPLANATIONS",  PURPLE),
        ("🎯", "CONCEPT\nCLARITY",     BLUE_P),
        ("🧠", "SMART\nSTRATEGIES",    GREEN),
        ("📈", "BETTER\nRESULTS",       ORANGE),
    ]
    badge_r    = 160
    badge_zone_y = text_start_y + total_text_h + 120
    badge_spacing = W // (len(badges) + 1)

    for i, (icon, label, col) in enumerate(badges):
        bx_c = badge_spacing * (i + 1)
        by_c = badge_zone_y + badge_r + 20
        # Circle
        draw.ellipse([bx_c-badge_r, by_c-badge_r,
                      bx_c+badge_r, by_c+badge_r], fill=col)
        # Icon
        ico_w = int(draw.textlength(icon, font=f_medium))
        draw.text((bx_c - ico_w//2, by_c - 90), icon, font=f_medium, fill=WHITE)
        # Label
        for j, lline in enumerate(label.split("\n")):
            lw = int(draw.textlength(lline, font=f_tiny))
            draw.text((bx_c - lw//2, by_c + badge_r + 20 + j*110),
                      lline, font=f_tiny, fill=GOLD)

    # ── 10. Footer bar ────────────────────────────────────────
    footer_h = 160
    fy = H - footer_h
    draw.rectangle([0, fy, W, H], fill=FOOTER)

    # Gold top line
    draw.rectangle([0, fy, W, fy+6], fill=GOLD)

    fy_mid = fy + footer_h // 2

    # YouTube
    yt_r = 55
    yt_x, yt_y = 200, fy_mid
    draw.ellipse([yt_x-yt_r, yt_y-yt_r, yt_x+yt_r, yt_y+yt_r],
                 fill=(220, 0, 0))
    draw.text((yt_x - 30, yt_y - 42), "▶", font=f_tiny, fill=WHITE)

    # Footer text uses a smaller dedicated font and is placed left to
    # right, each block starting only after the previous one's right
    # edge, so long strings can never overlap regardless of length.
    f_footer = load_font(FONT_BOLD, 68)

    nv_text = "NEW VIDEOS EVERY DAY"
    nv_x = yt_x + yt_r + 30
    draw.text((nv_x, fy_mid - 34), nv_text, font=f_footer, fill=WHITE)
    nv_right = nv_x + int(draw.textlength(nv_text, font=f_footer))

    sub_text = "🔔  SUBSCRIBE & TURN ON NOTIFICATIONS"
    st_w = int(draw.textlength(sub_text, font=f_footer))
    sub_x = max(nv_right + 80, (W - st_w)//2)
    draw.text((sub_x, fy_mid - 34), sub_text, font=f_footer, fill=GOLD)
    sub_right = sub_x + st_w

    social = "@MathConceptMadeEasy"
    sw = int(draw.textlength(social, font=f_footer))
    social_x = max(sub_right + 80, W - sw - 150)
    draw.text((social_x, fy_mid - 34), social, font=f_footer, fill=LGRAY)

    # ── 11. Downscale 4K → 1920×1080 ────────────────────────
    print("  🔬 Downsampling 4K → 1920×1080 (LANCZOS)...")
    final = bg.resize((1920, 1080), Image.LANCZOS)
    final.save(THUMBNAIL_PATH, format="JPEG", quality=96)

    size_kb = THUMBNAIL_PATH.stat().st_size // 1024
    print(f"\n{'═'*65}")
    print(f"  🎉 THUMBNAIL GENERATED — Premium Brand Design")
    print(f"{'═'*65}")
    print(f"  ✅ File     : {THUMBNAIL_NAME}")
    print(f"  💾 Size     : {size_kb} KB")
    print(f"  📐 Size     : 1920×1080 px")
    print(f"  📂 Location : {THUMBNAIL_PATH.parent}")
    print(f"{'═'*65}")


build_thumbnail()
