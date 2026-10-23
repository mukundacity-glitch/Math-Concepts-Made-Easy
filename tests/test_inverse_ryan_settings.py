from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('inverse_build', ROOT / 'scripts/build_inverse_lesson.py')
assert SPEC is not None and SPEC.loader is not None
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def test_day2_effective_profiles_preserve_ryan_and_runtime_overrides():
    assert BUILD.VOICE == 'en-GB-RyanNeural'
    expected = {
        'opening': ('+13%', '-4Hz'), 'machine': ('+17%', '-4Hz'),
        'algebra': ('+18%', '+0Hz'), 'verify': ('+17%', '-4Hz'),
        'graph': ('+17%', '-4Hz'), 'domain': ('+11%', '-4Hz'),
        'notation': ('+11%', '-4Hz'), 'practice': ('+18%', '+0Hz'),
        'recap': ('+11%', '-4Hz'),
    }
    for scene, (rate, pitch) in expected.items():
        assert BUILD.voice_profile(scene) == {'rate': rate, 'pitch': pitch, 'volume': '+0%'}
    with pytest.raises(KeyError):
        BUILD.voice_profile('unknown-scene')


def test_profile_changes_invalidate_cached_narration(monkeypatch):
    beat = {'id': 'opening-00', 'scene': 'opening', 'speech': 'A function reverses a mapping.'}
    original = BUILD.narration_fingerprint(beat)
    settings = json.loads(json.dumps(BUILD.SETTINGS))
    settings['moods']['intro']['rate'] = '+14%'
    monkeypatch.setattr(BUILD, 'SETTINGS', settings)
    assert BUILD.narration_fingerprint(beat) != original


def test_day2_mastering_uses_measured_two_pass_normalization(tmp_path):
    raw = tmp_path / 'source.wav'
    target = tmp_path / 'master.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
        'sine=frequency=900:duration=3', str(raw)], check=True)
    measurement = BUILD.measure_loudness(raw)
    filters = BUILD.day2_loudnorm_filter(measurement)
    assert 'measured_I=' in filters and 'linear=true' in filters
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(raw), '-af', filters,
        '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(target)], check=True)
    actual = BUILD.measure_loudness(target)
    assert abs(float(actual['input_i']) - (-18.0)) <= 0.8
    assert float(actual['input_tp']) <= -1.0
    stream = BUILD.probe(target)['streams'][0]
    assert stream['sample_rate'] == '48000'
    assert stream['channels'] == 2
    assert stream['codec_name'] == 'pcm_s24le'
