from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from scripts import verify_inverse_master as integrity


def make_master(tmp_path: Path, gain: float) -> tuple[Path, dict]:
    source = tmp_path / 'public/inverse/audio/opening-00.wav'
    source.parent.mkdir(parents=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
        'anoisesrc=color=pink:seed=712:duration=3', '-af',
        'lowpass=f=3000,pan=stereo|c0=c0|c1=0.1*c0',
        '-ar', '48000', '-c:a', 'pcm_s24le', str(source)], check=True)
    final = tmp_path / 'encoded.m4a'
    graph = f'[0:a]volume={gain},apad=pad_len=12800,asplit=2[first][second];[first][second]concat=n=2:v=0:a=1[out]'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(source), '-filter_complex', graph,
        '-map', '[out]', '-c:a', 'aac', '-b:a', '192k', str(final)], check=True)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    return final, {'beats': [{'id': identifier, 'durationInFrames': 98,
        'audioSrc': 'inverse/audio/opening-00.wav', 'audioSha256': source_hash}
        for identifier in ['opening-00', 'opening-01']]}


def test_aac_integrity_checks_the_same_stereo_channel_at_quantized_offsets(tmp_path, monkeypatch):
    monkeypatch.setattr(integrity, 'REMOTION', tmp_path)
    monkeypatch.setattr(integrity, 'BUILD', tmp_path)
    final, props = make_master(tmp_path, 1.0)
    report = integrity.verify_master(final, props)
    assert report['verifiedBeats'] == 2
    assert report['minimumCorrelation'] >= .97
    assert report['maximumAbsoluteTimingErrorMs'] <= 1.0
    assert all(.95 <= beat['gain'] <= 1.05 for beat in report['beats'])


def test_doubled_narration_gain_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(integrity, 'REMOTION', tmp_path)
    monkeypatch.setattr(integrity, 'BUILD', tmp_path)
    final, props = make_master(tmp_path, 1.8)
    with pytest.raises(ValueError, match='Final narration mismatch'):
        integrity.verify_master(final, props)
