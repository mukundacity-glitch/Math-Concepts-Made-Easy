"""Actual AAC transport preserves speech; an extra narration track is rejected."""
import shutil
import subprocess

import pytest

np = pytest.importorskip('numpy')
from pipeline.narration_integrity import verify_narration


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg media runtime required')
def test_actual_encoded_narration_and_doubled_voice(tmp_path):
    def run(*args):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', *map(str, args)], check=True)
    source = tmp_path / 'original.mp3'
    run('-f', 'lavfi', '-i', 'sine=frequency=173:sample_rate=24000:duration=3',
        '-af', 'vibrato=f=7:d=0.6', source)
    final = tmp_path / 'output.m4a'
    run('-i', source, '-af', 'pan=stereo|c0=c0|c1=c0', '-c:a', 'aac', final)
    assert verify_narration(final, [(source, 0)])[0]['correlation'] > .97
    doubled = tmp_path / 'doubled.m4a'
    run('-i', source, '-af', 'volume=2,pan=stereo|c0=c0|c1=c0', '-c:a', 'aac', doubled)
    with pytest.raises(ValueError, match='Rendered narration differs'):
        verify_narration(doubled, [(source, 0)])
