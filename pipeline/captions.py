"""Burns SRT captions into video pixels via ffmpeg's libass `subtitles`
filter — the "true subtitles" layer requested for the video engine: a
small, bottom-center, word-synced caption track that stays visible
regardless of the viewer's own caption settings, freeing the board's
center for diagrams instead of narration-mirroring text.
"""

import subprocess
from pathlib import Path


def _probe_height(video_path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=height",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, check=True,
    )
    return int(out.stdout.strip())


def burn_captions(video_path, srt_path, out_path, base_font_px=42):
    """Burn `srt_path` onto `video_path`, writing the result to `out_path`.

    Font size and bottom margin scale with the input video's real height
    (measured via ffprobe) so captions read correctly at any resolution —
    1080p, 4K, or otherwise — not just the resolution this was tuned at.
    """
    video_path = Path(video_path)
    srt_path = Path(srt_path)
    out_path = Path(out_path)

    if not video_path.exists():
        raise SystemExit(f"🛑 burn_captions: video not found: {video_path}")
    if not srt_path.exists():
        raise SystemExit(f"🛑 burn_captions: SRT not found: {srt_path}")

    height = _probe_height(video_path)
    scale = height / 1080.0
    font_px = max(18, round(base_font_px * scale))
    # The channel's footer band occupies the bottom ~10% of frame — clear
    # it with margin to spare, so captions never overlap the footer chips.
    margin_v = max(20, round(140 * scale))

    # Copy the SRT to a flat scratch path first — ffmpeg's subtitles filter
    # parses its filename argument on ':' and ',', so this is cheap
    # insurance even though safe_filename() already strips those from the
    # real path.
    scratch_srt = out_path.parent / "_burn_captions.srt"
    scratch_srt.write_text(srt_path.read_text(encoding="utf-8"), encoding="utf-8")

    # ASS colours are &HAABBGGRR. PrimaryColour white text, BackColour a
    # ~50%-opaque black box (BorderStyle=3 turns outline/shadow into a
    # solid box instead of a stroke), bottom-center (Alignment=2).
    style = (
        "FontName=DejaVu Sans,"
        f"FontSize={font_px},"
        "PrimaryColour=&H00FFFFFF,"
        "BorderStyle=3,"
        "BackColour=&H80000000,"
        "Outline=0,Shadow=0,"
        "Alignment=2,"
        f"MarginV={margin_v}"
    )
    vf = f"subtitles={scratch_srt.as_posix()}:force_style='{style}'"

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    scratch_srt.unlink(missing_ok=True)
    return out_path
