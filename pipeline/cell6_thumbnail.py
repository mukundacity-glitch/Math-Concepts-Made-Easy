# ==========================================
# CELL 6: THUMBNAIL ENGINE
# CHANNEL: MathConceptsMadeEasy
# Premium dark design: deep navy gradient,
# star field, gold accent bar, bold text.
# Renders at 4K then downscales to 1920x1080.
# ==========================================

import sys, os, json, random, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config, safe_filename
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")

lesson_data = cell1_config.CURRICULUM[0]
lesson_id   = lesson_data['id']
seo_title   = safe_filename(lesson_data['seo_title'])

SCRIPTS_DIR    = cell1_config.SCRIPTS_DIR
THUMBNAILS_DIR = cell1_config.THUMBNAILS_DIR
ASSETS_DIR     = cell1_config.ASSETS_DIR
TIMED_SCRIPT = SCRIPTS_DIR / f"lesson_{lesson_id:03d}_script_timed.json"
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
FORMULA     = SCRIPT.get("formula_spoken", "")[:60]

print(f"✅ Timed script loaded → {TIMED_SCRIPT.name}")
print(f"   Angle   : {THUMB_ANGLE}")
print(f"   Subject : {SUBJECT}")
print(f"   Target  : {THUMBNAIL_NAME}\n")

# ── Font management ───────────────────────────────────────────
FONT_PATH = ASSETS_DIR / "Montserrat-Black.ttf"
if not FONT_PATH.exists():
    for url in [
        "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf",
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Black.ttf",
    ]:
        try:
            print(f"📥 Downloading Montserrat-Black font...")
            urllib.request.urlretrieve(url, FONT_PATH)
            print("✅ Font downloaded.\n")
            break
        except Exception:
            continue

# ── Color palette ─────────────────────────────────────────────
NAVY1   = (6,   17,  30)   # deep navy
NAVY2   = (2,   6,   14)   # near-black
GOLD    = (255, 179,  0)   # warm gold
WHITE   = (240, 244, 248)  # near-white
TEAL    = ( 32, 178, 170)  # teal accent
DIM     = (120, 140, 160)  # dim blue-grey


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_gradient(w, h, c1, c2):
    import numpy as np
    xs = np.linspace(0, 1, w)
    ys = np.linspace(0, 1, h)
    xv, yv = np.meshgrid(xs, ys)
    t = (xv * 0.4 + yv * 0.6)          # diagonal blend
    r = (c1[0]*(1-t) + c2[0]*t).astype('uint8')
    g = (c1[1]*(1-t) + c2[1]*t).astype('uint8')
    b = (c1[2]*(1-t) + c2[2]*t).astype('uint8')
    return Image.fromarray(
        __import__('numpy').stack([r, g, b], axis=2), 'RGB'
    ).filter(ImageFilter.GaussianBlur(6))


def add_stars(draw, w, h, n=220, seed=42):
    rng = random.Random(seed)
    for _ in range(n):
        x = rng.randint(0, w)
        y = rng.randint(0, h)
        r = rng.randint(2, 9)
        v = rng.randint(80, 220)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(v, v, v))


def stroke_text(draw, x, y, text, font, fill, stroke_w=12, stroke_col=(0, 0, 0)):
    for dx in range(-stroke_w, stroke_w+1, 4):
        for dy in range(-stroke_w, stroke_w+1, 4):
            if dx or dy:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_col)
    draw.text((x + stroke_w, y + stroke_w), text, font=font,
              fill=tuple(max(0, c-80) for c in fill))
    draw.text((x, y), text, font=font, fill=fill)


def wrap_to_lines(text, font, max_w, draw, max_lines=3):
    words = text.split()
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if draw.textlength(" ".join(cur), font=font) > max_w:
            cur.pop()
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
        if len(lines) >= max_lines - 1:
            lines.append(" ".join(cur + words[words.index(w)+1:]))
            cur = []
            break
    if cur:
        lines.append(" ".join(cur))
    return lines[:max_lines]


def build_thumbnail():
    print(f"{'═'*65}")
    print(f"  RENDERING THUMBNAIL — Premium Dark Design (4K→1080p)")
    print(f"{'═'*65}\n")

    W, H = 3840, 2160          # render at 4K
    MARGIN = 180               # left text margin (after accent bar)

    # ── 1. Dark diagonal gradient background ─────────────────
    bg = make_gradient(W, H, NAVY1, NAVY2)
    draw = ImageDraw.Draw(bg)

    # ── 2. Star field ─────────────────────────────────────────
    add_stars(draw, W, H)

    # ── 3. Subtle diagonal light band (top-right) ────────────
    from PIL import ImageDraw as ID2
    overlay = Image.new("RGB", (W, H), (0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon([(W//2, 0), (W, 0), (W, H//2)], fill=(20, 40, 70))
    bg = Image.blend(bg, overlay, alpha=0.25)
    draw = ImageDraw.Draw(bg)

    # ── 4. Left gold accent bar ───────────────────────────────
    BAR = 50
    draw.rectangle([0, 0, BAR, H], fill=GOLD)

    # ── 5. Load fonts ─────────────────────────────────────────
    try:
        fp = str(FONT_PATH) if FONT_PATH and FONT_PATH.exists() else None
        f_huge  = ImageFont.truetype(fp, 420) if fp else ImageFont.load_default()
        f_big   = ImageFont.truetype(fp, 280) if fp else ImageFont.load_default()
        f_med   = ImageFont.truetype(fp, 180) if fp else ImageFont.load_default()
        f_small = ImageFont.truetype(fp, 120) if fp else ImageFont.load_default()
    except Exception as e:
        raise SystemExit(f"🛑 Font error: {e}")

    # ── 6. SUBJECT tag (top left, below bar top) ─────────────
    sub_y = 160
    # teal pill behind subject
    sub_w = int(draw.textlength(SUBJECT, font=f_small)) + 80
    draw.rounded_rectangle([MARGIN - 20, sub_y - 20,
                             MARGIN + sub_w, sub_y + 140],
                            radius=30, fill=(0, 80, 80))
    draw.text((MARGIN + 20, sub_y), SUBJECT, font=f_small, fill=TEAL)

    # ── 7. DAY badge (top right, gold) ───────────────────────
    badge_w, badge_h = 800, 260
    bx = W - badge_w - 120
    by = 100
    draw.rounded_rectangle([bx, by, bx + badge_w, by + badge_h],
                            radius=40, fill=GOLD)
    dw = int(draw.textlength(DAY_TEXT, font=f_med))
    draw.text((bx + (badge_w - dw)//2, by + 30), DAY_TEXT,
              font=f_med, fill=(10, 15, 25))

    # ── 8. Main hook text (center-left, big) ─────────────────
    max_text_w = W - MARGIN - 300
    lines = wrap_to_lines(THUMB_ANGLE, f_huge, max_text_w, draw, max_lines=3)

    line_h = 460
    n = len(lines)
    total_h = n * line_h
    text_start_y = (H - total_h) // 2 + 100   # slightly below center

    for i, line in enumerate(lines):
        color = GOLD if i == 0 else WHITE       # first line gold, rest white
        stroke_col = (40, 20, 0) if i == 0 else (0, 0, 0)
        stroke_text(draw, MARGIN, text_start_y + i * line_h,
                    line, f_huge, color, stroke_w=18, stroke_col=stroke_col)

    # ── 9. Formula / tagline at bottom ───────────────────────
    if FORMULA:
        fy = H - 280
        stroke_text(draw, MARGIN, fy, FORMULA, f_small, DIM, stroke_w=6,
                    stroke_col=(0, 0, 0))

    # ── 10. Gold bottom bar (thin) ───────────────────────────
    draw.rectangle([BAR + 10, H - 14, W, H], fill=GOLD)

    # ── 11. Downscale 4K → 1920×1080 ────────────────────────
    print("  🔬 Downsampling 4K → 1920×1080 (LANCZOS)...")
    final = bg.resize((1920, 1080), Image.LANCZOS)
    final.save(THUMBNAIL_PATH, format="JPEG", quality=96)

    size_kb = THUMBNAIL_PATH.stat().st_size // 1024
    print(f"\n{'═'*65}")
    print(f"  🎉 THUMBNAIL GENERATED — Premium Dark Design")
    print(f"{'═'*65}")
    print(f"  ✅ File     : {THUMBNAIL_NAME}")
    print(f"  💾 Size     : {size_kb} KB")
    print(f"  📂 Location : {THUMBNAIL_PATH.parent}")
    print(f"{'═'*65}")


build_thumbnail()
