"""
ONE-TIME SETUP SCRIPT — not part of the daily autopilot pipeline.

Generates the fixed Like/Comment/Subscribe outro narration once and
saves it to assets/outro_like_comment_subscribe.mp3. Scene10_Outro
(in cell4_animation.py) plays this file on every lesson — it is not
regenerated per lesson, since the line never changes with the topic.

Run manually, once, after cloning the repo or if you want to change
the voice/wording:

    python3 pipeline/generate_outro_audio.py

Uses the same edge_tts.Communicate() pattern as cell3_audio.py so the
voice matches the rest of the channel.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.paths import load_cell1_config

cell1_config = load_cell1_config()

OUTRO_TEXT = (
    "If this lesson helped you, tap that like button. "
    "Drop your questions in the comments below — I read every one. "
    "And hit subscribe, because a brand new math lesson is waiting "
    "for you tomorrow."
)

OUTRO_PATH = cell1_config.ASSETS_DIR / "outro_like_comment_subscribe.mp3"


async def main():
    import edge_tts

    voice   = cell1_config.TTS_CONFIG["voice"]
    profile = cell1_config.PITCH_PROFILES.get(
        "encouraging", {"rate": "+3%", "pitch": "+4Hz"}
    )

    cell1_config.ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    comm = edge_tts.Communicate(
        OUTRO_TEXT, voice,
        rate=profile["rate"], pitch=profile["pitch"],
    )

    with open(str(OUTRO_PATH), "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])

    size_kb = OUTRO_PATH.stat().st_size // 1024
    print(f"✅ Outro audio generated → {OUTRO_PATH} ({size_kb} KB)")
    print("   This file is reused by every lesson's Scene10_Outro.")
    print("   Re-run this script only if you want to change the wording/voice.")


if __name__ == "__main__":
    asyncio.run(main())
