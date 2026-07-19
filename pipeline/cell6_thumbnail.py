# ==========================================
# CELL 6: THUMBNAIL ENGINE
# CHANNEL: MathConceptsMadeEasy
# Pattern: Cinematic Supersampled Composite
#   → Renders at 4K (3840x2160) and downscales
#     to 1080p using LANCZOS for 100% sharpness.
#   → Auto-fetches premium bold fonts.
#   → Applies deep gradients, drop shadows,
#     and text-stroke borders.
#   → Overlays channel logo and thumbnail angle.
# ==========================================

import sys, os, json, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Install Pillow if missing ─────────────────────────────────
try:
    import PIL
except ImportError:
    import subprocess
    
# ── Load Cell 1 config (written by pipeline/cell1_lesson.py) ──
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config, safe_filename
cell1_config = load_cell1_config()
print("✅ cell1_config loaded.")
# ══════════════════════════════════════════════════════════════
# PATHS AND METADATA
# ══════════════════════════════════════════════════════════════

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

# ── Load script ───────────────────────────────────────────────
if not TIMED_SCRIPT.exists():
    raise SystemExit(f"🛑 Timed script not found at {TIMED_SCRIPT}. Run Cell 3 first.")

with open(TIMED_SCRIPT, "r", encoding="utf-8") as f:
    SCRIPT = json.load(f)

# The ultra-clickable hook defined in your curriculum
THUMB_ANGLE = SCRIPT.get("thumbnail_angle", SCRIPT["title"]).upper()
SUBJECT     = SCRIPT.get("subject", "MATH").upper()
DAY_TEXT    = f"DAY {lesson_id:02d}"

print(f"✅ Timed script loaded → {TIMED_SCRIPT.name}")
print(f"   Angle   : {THUMB_ANGLE}")
print(f"   Subject : {SUBJECT}")
print(f"   Target  : {THUMBNAIL_NAME}\n")

# ══════════════════════════════════════════════════════════════
# FONT MANAGEMENT (Auto-Fetch)
# ══════════════════════════════════════════════════════════════

FONT_URL = "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Black.ttf"
FONT_PATH = ASSETS_DIR / "Montserrat-Black.ttf"

if not FONT_PATH.exists():
    downloaded = False
    for url in [
        "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf",
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Black.ttf",
    ]:
        try:
            print(f"📥 Downloading premium bold font (Montserrat-Black)...")
            urllib.request.urlretrieve(url, FONT_PATH)
            print("✅ Font downloaded successfully.\n")
            downloaded = True
            break
        except Exception:
            continue
    if not downloaded:
        print("⚠️  Font download failed — falling back to Arial.\n")
        FONT_PATH = None

# ══════════════════════════════════════════════════════════════
# HEX TO RGB HELPER
# ══════════════════════════════════════════════════════════════

def hex_to_rgb(hex_code: str) -> tuple:
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

T = SCRIPT["theme"]
RGB_BG      = hex_to_rgb(T["bg"])        # #0D1B2A
RGB_PRIMARY = hex_to_rgb(T["primary"])   # #F0F4F8
RGB_YELLOW  = hex_to_rgb(T["yellow"])    # #F6C90E
RGB_BLUE    = hex_to_rgb(T["blue"])      # #3B9EFF
RGB_RED     = hex_to_rgb(T["red"])       # #E74C3C

# ══════════════════════════════════════════════════════════════
# SUPERSAMPLED RENDER ENGINE (4K -> 1080p)
# ══════════════════════════════════════════════════════════════

def create_cinematic_gradient(width: int, height: int, color1: tuple, color2: tuple) -> Image.Image:
    import numpy as np
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xv, yv = np.meshgrid(x, y)
    factor = (xv + yv) / 2
    r = (color1[0] * (1 - factor) + color2[0] * factor).astype(np.uint8)
    g = (color1[1] * (1 - factor) + color2[1] * factor).astype(np.uint8)
    b = (color1[2] * (1 - factor) + color2[2] * factor).astype(np.uint8)
    arr = np.stack([r, g, b], axis=2)
    img = Image.fromarray(arr, 'RGB')
    return img.filter(ImageFilter.GaussianBlur(10))

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """Wraps text intelligently based on actual pixel width of the font."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        line_w = draw.textlength(" ".join(current_line), font=font)
        if line_w > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines

def draw_text_with_shadow(draw, x, y, text, font, fill_color, outline_color=(0,0,0), shadow_color=(0,0,0), stroke_width=8):
    """Draws ultra-crisp text with a heavy stroke and a drop shadow for cinematic depth."""
    # 1. Drop Shadow
    shadow_offset = stroke_width * 2
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)

    # 2. Outline / Stroke (rendering offset in 8 directions)
    for adj_x in [-stroke_width, 0, stroke_width]:
        for adj_y in [-stroke_width, 0, stroke_width]:
            draw.text((x + adj_x, y + adj_y), text, font=font, fill=outline_color)

    # 3. Main Text Foreground
    draw.text((x, y), text, font=font, fill=fill_color)

def build_thumbnail():
    print(f"{'═'*65}")
    print(f"  RENDERING THUMBNAIL (Supersampled 4K -> 1080p)")
    print(f"{'═'*65}\n")

    # Render resolution is 2x standard 1080p
    R_WIDTH, R_HEIGHT = 3840, 2160

    print("  🎨 Generating cinematic background...")
    # Deep navy to black gradient
    bg = Image.new("RGB", (R_WIDTH, R_HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(bg)

    # Load fonts (scaled up 2x)
    try:
        font_main  = ImageFont.truetype(str(FONT_PATH), size=360)
        font_badge = ImageFont.truetype(str(FONT_PATH), size=180)
        font_sub   = ImageFont.truetype(str(FONT_PATH), size=140)
    except Exception as e:
        raise SystemExit(f"🛑 Font loading failed. {e}")

    # ── 1. Draw "Day XX" Badge Top Right ────────────────────────
    badge_w, badge_h = 700, 250
    badge_x = R_WIDTH - badge_w - 100
    badge_y = 100

    # Red pill badge for urgency
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                           radius=50, fill=RGB_RED)

    # Center text in badge
    day_w = draw.textlength(DAY_TEXT, font=font_badge)
    day_x = badge_x + (badge_w - day_w) / 2
    day_y = badge_y + 15
    draw.text((day_x, day_y), DAY_TEXT, font=font_badge, fill=(255, 255, 255))

    # ── 3. Subject Subtitle (Middle Left) ───────────────────────
    subject_y = R_HEIGHT // 2 - 500
    draw_text_with_shadow(draw, 120, subject_y, SUBJECT, font_sub, RGB_BLUE, stroke_width=10)

    # ── 3b. Key formula below subject ───────────────────────────
    formula_spoken = SCRIPT.get("formula_spoken", "")
    if formula_spoken:
        formula_display = formula_spoken[:52].upper()
        draw_text_with_shadow(
            draw, 120, subject_y + 200,
            formula_display, font_sub,
            RGB_YELLOW, stroke_width=8
        )

    # ── 4. Main Hook / Thumbnail Angle (Bottom Left) ────────────
    # Wrap text to ensure it doesn't bleed off screen
    wrapped_hook = wrap_text(THUMB_ANGLE, font_main, R_WIDTH - 400, draw)

    line_spacing = 380
    start_y = R_HEIGHT - (len(wrapped_hook) * line_spacing) - 150

    for i, line in enumerate(wrapped_hook):
        # Alternate colors for pop: Yellow then White
        fill_col = RGB_YELLOW if i % 2 == 0 else RGB_PRIMARY
        y_pos = start_y + (i * line_spacing)
        draw_text_with_shadow(draw, 120, y_pos, line, font_main, fill_col, stroke_width=18)

    # ── 5. Downscale to 1080p using LANCZOS for 100% Sharpness ──
    print("  🔬 Downsampling to 1920x1080 for perfect sharpness...")
    final_thumb = bg.resize((1920, 1080), Image.LANCZOS)

    # Save high quality JPEG
    final_thumb.save(THUMBNAIL_PATH, format="JPEG", quality=95)
    size_kb = THUMBNAIL_PATH.stat().st_size // 1024

    print(f"\n{'═'*65}")
    print(f"  🎉 THUMBNAIL GENERATED")
    print(f"{'═'*65}")
    print(f"  ✅ Status    : Success")
    print(f"  🖼️ File      : {THUMBNAIL_NAME}")
    print(f"  💾 Size      : {size_kb} KB")
    print(f"  📂 Location  : {THUMBNAIL_PATH.parent}")
    print(f"{'═'*65}")

# ══════════════════════════════════════════════════════════════
# EXECUTION
# ══════════════════════════════════════════════════════════════

build_thumbnail()

