"""Narration audio: text-to-speech, duration probing and caching.

The visuals are timed to the *measured* length of Ryan's voice, so the
animation and the narration finish together.  When TTS is unavailable
(offline CI, no ``edge-tts``) the engine falls back to the speaking-rate
estimate in :mod:`rational_series.script_parser` and simply renders a silent
video — a render never fails because of audio.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

from rational_series.script_parser import DayScript

DEFAULT_VOICE = "en-GB-RyanNeural"
DEFAULT_RATE = "-5%"
DEFAULT_PITCH = "+0Hz"


class AudioUnavailable(RuntimeError):
    """Raised internally when TTS cannot run; callers degrade gracefully."""


def _fingerprint(text: str, voice: str, rate: str, pitch: str) -> str:
    return hashlib.sha1(f"{voice}|{rate}|{pitch}|{text}".encode("utf-8")).hexdigest()[:16]


def probe_duration(path: Path) -> Optional[float]:
    """Length of an audio file in seconds, via ffprobe (None if unknown)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.exists():
        return None
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return None


def synthesize(text: str, out_path: Path, *, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE,
               pitch: str = DEFAULT_PITCH) -> Path:
    """Render one narration line to MP3 with edge-tts."""
    try:
        import asyncio

        import edge_tts
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise AudioUnavailable("edge-tts is not installed") from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(str(out_path))

    try:
        asyncio.run(_run())
    except RuntimeError:
        # Already inside a loop (notebooks): fall back to a fresh loop.
        loop = __import__("asyncio").new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()
    except Exception as exc:  # network down, service error…
        raise AudioUnavailable(str(exc)) from exc

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise AudioUnavailable(f"edge-tts produced no audio for {out_path.name}")
    return out_path


def build_narration(
    script: DayScript,
    audio_dir: Path,
    *,
    voice: Optional[str] = None,
    rate: str = DEFAULT_RATE,
    enabled: bool = True,
    verbose: bool = True,
) -> Dict[str, Tuple[Path, float]]:
    """Synthesize (or reuse) every block's narration.

    Returns ``{block id: (path, duration)}``.  Blocks whose audio could not
    be produced are simply absent, and the caller keeps the estimate.
    """
    if not enabled:
        return {}

    voice = voice or script.voice
    audio_dir.mkdir(parents=True, exist_ok=True)
    tracks: Dict[str, Tuple[Path, float]] = {}
    failures = 0

    for block in script.blocks:
        if not block.narration.strip():
            continue
        stamp = _fingerprint(block.narration, voice, rate, DEFAULT_PITCH)
        path = audio_dir / f"{block.id}_{stamp}.mp3"
        if not path.exists():
            try:
                synthesize(block.narration, path, voice=voice, rate=rate)
                if verbose:
                    print(f"   🎙  {block.id}: synthesized")
            except AudioUnavailable as exc:
                failures += 1
                if verbose and failures == 1:
                    print(f"   ⚠️  narration unavailable ({exc}) — timing from the speaking-rate model")
                continue
        elif verbose:
            print(f"   ♻️  {block.id}: cached audio")

        duration = probe_duration(path)
        if duration is None:
            continue
        tracks[block.id] = (path, duration)

    return tracks


def stale_files(audio_dir: Path, keep: Dict[str, Tuple[Path, float]]) -> None:
    """Delete cached audio that no longer belongs to the current script."""
    if not audio_dir.exists():
        return
    wanted = {path.name for path, _ in keep.values()}
    for path in audio_dir.glob("*.mp3"):
        if path.name not in wanted:
            path.unlink(missing_ok=True)


__all__ = ["DEFAULT_VOICE", "AudioUnavailable", "build_narration", "probe_duration", "stale_files", "synthesize"]
