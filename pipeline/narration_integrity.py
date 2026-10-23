"""Compare rendered speech to original narration, one output channel at a time."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def verify_narration(final: Path, segments: list[tuple[Path, float]]) -> list[dict]:
    import numpy as np
    streams = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
        '-of', 'json', str(final)], text=True))['streams']
    audio = next(s for s in streams if s['codec_type'] == 'audio')
    def samples(path, start, channel=False):
        # Decode before seeking: fast MP3 input seeks can omit the bit reservoir
        # and corrupt the beginning of a comparison window, despite intact audio.
        args = ['ffmpeg', '-v', 'error', '-i', str(path), '-ss', str(start), '-t', '1.5', '-vn']
        if channel and audio.get('channels', 1) > 1:
            args += ['-af', 'pan=mono|c0=FL']
        return np.frombuffer(subprocess.check_output(args + ['-ac', '1', '-ar', '8000',
            '-f', 'f32le', 'pipe:1']), dtype='<f4')
    reports = []
    for original, start in segments:
        source = samples(original, .2)
        rendered = samples(final, start + .2, True)
        length = min(len(source), len(rendered)) - 320
        if length < 1600:
            raise ValueError('Insufficient original speech for an integrity check')
        reference = source[160:160 + length]
        best = (-1., 0.)
        for offset in range(0, 321, 4):
            candidate = rendered[offset:offset + length]
            correlation = float(np.corrcoef(reference, candidate)[0, 1])
            gain = float(np.dot(reference, candidate) / max(float(np.dot(reference, reference)), 1e-12))
            if correlation > best[0]: best = (correlation, gain)
        if not best[0] >= .97 or not .8 <= best[1] <= 1.2:
            raise ValueError(f'Rendered narration differs from {original.name}: {best}')
        reports.append({'source': original.name, 'outputStart': start,
                        'correlation': best[0], 'gain': best[1]})
    return reports
