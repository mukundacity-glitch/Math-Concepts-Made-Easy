"""Check each authored narration segment in the final AAC encode."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REMOTION = ROOT / 'remotion'
BUILD = REMOTION / 'build/inverse'
SAMPLE_RATE = 8000


def decode_left(path: Path, start: float = 0.0, duration: float | None = None) -> np.ndarray:
    args = ['ffmpeg', '-v', 'error', '-i', str(path), '-ss', str(start)]
    if duration is not None:
        args += ['-t', str(duration)]
    args += ['-vn', '-af', 'pan=mono|c0=FL', '-ar', str(SAMPLE_RATE), '-f', 'f32le', 'pipe:1']
    return np.frombuffer(subprocess.check_output(args), dtype='<f4')


def verify_master(final: Path, props: dict[str, Any]) -> dict[str, Any]:
    if not final.is_file():
        raise FileNotFoundError(final)
    samples = decode_left(final)
    cursor = 0
    reports = []
    for beat in props['beats']:
        original = REMOTION / 'public' / beat['audioSrc']
        if hashlib.sha256(original.read_bytes()).hexdigest() != beat['audioSha256']:
            raise ValueError(f"Narration content changed for {beat['id']}")
        reference = decode_left(original, .25, 1.0)
        if len(reference) < SAMPLE_RATE // 2:
            raise ValueError(f"Insufficient speech to verify {beat['id']}")
        # Decode the same channel on both sides so stereo downmix gains cannot skew the proof.
        start = round((cursor / 30 + .25) * SAMPLE_RATE)
        best_correlation = -1.0
        best_gain = 0.0
        best_lag = 0
        for lag in range(-160, 161):
            candidate = samples[start + lag:start + lag + len(reference)]
            if len(candidate) != len(reference):
                continue
            correlation = float(np.corrcoef(reference, candidate)[0, 1])
            energy = float(np.dot(reference, reference))
            gain = float(np.dot(reference, candidate) / max(energy, 1e-12))
            if math.isfinite(correlation) and correlation > best_correlation:
                best_correlation, best_gain, best_lag = correlation, gain, lag
        if best_correlation < .97 or not .8 <= best_gain <= 1.2:
            raise ValueError(f"Final narration mismatch at {beat['id']}: correlation={best_correlation:.5f}, gain={best_gain:.5f}")
        reports.append({'beat': beat['id'], 'startSeconds': cursor / 30,
            'correlation': best_correlation, 'gain': best_gain,
            'lagMilliseconds': best_lag / SAMPLE_RATE * 1000})
        cursor += beat['durationInFrames']
    report = {'verifiedBeats': len(reports), 'minimumCorrelation': min(item['correlation'] for item in reports),
        'maximumAbsoluteTimingErrorMs': max(abs(item['lagMilliseconds']) for item in reports),
        'beats': reports}
    (BUILD / 'narration-integrity.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    try:
        props = json.loads((BUILD / 'lesson.json').read_text())
        report = verify_master(BUILD / 'Inverse-Functions.mp4', props)
        print(json.dumps({key: value for key, value in report.items() if key != 'beats'}, indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Final narration verification failed: {error}') from error
