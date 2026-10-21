"""Day 2 narration mastering: measured two-pass loudness, stereo 48 kHz."""
from __future__ import annotations

import json
import math
import subprocess

NARRATION_LUFS = -18.0
NARRATION_TRUE_PEAK = -1.5
LOUDNESS_RANGE = 7.0


def narration_filter(audio_path):
    target = f'loudnorm=I={NARRATION_LUFS}:TP={NARRATION_TRUE_PEAK}:LRA={LOUDNESS_RANGE}'
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-i', str(audio_path),
         '-af', target + ':print_format=json', '-f', 'null', '-'],
        capture_output=True, text=True, check=True,
    )
    report = result.stderr[result.stderr.rfind('{'):result.stderr.rfind('}') + 1]
    measured = json.loads(report)
    fields = {'input_i': 'measured_I', 'input_tp': 'measured_TP',
              'input_lra': 'measured_LRA', 'input_thresh': 'measured_thresh',
              'target_offset': 'offset'}
    values = {dest: float(measured[src]) for src, dest in fields.items()}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError('Cannot master silent or invalid narration')
    return target + ''.join(f':{key}={value}' for key, value in values.items()) + ':linear=true'
