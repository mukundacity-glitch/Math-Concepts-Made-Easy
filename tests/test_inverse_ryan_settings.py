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


def test_day2_voice_signature_is_preserved_with_premium_lesson_rates():
    assert BUILD.VOICE == 'en-GB-RyanNeural'
    expected = {
        'opening': ('-3%', '-4Hz'), 'machine': ('-6%', '-4Hz'),
        'algebra': ('-10%', '+0Hz'), 'verify': ('-6%', '-4Hz'),
        'graph': ('-6%', '-4Hz'), 'domain': ('-5%', '-4Hz'),
        'notation': ('-5%', '-4Hz'), 'practice': ('-10%', '+0Hz'),
        'recap': ('-3%', '-4Hz'),
    }
    assert BUILD.SETTINGS['runtime_rate_overrides'] == {'analysis': '+17%', 'key_stat': '+18%', 'warning': '+11%'}
    for scene, (rate, pitch) in expected.items():
        assert BUILD.voice_profile(scene) == {'rate': rate, 'pitch': pitch, 'volume': '+0%'}
    with pytest.raises(KeyError):
        BUILD.voice_profile('unknown-scene')


def test_profile_changes_invalidate_cached_narration(monkeypatch):
    beat = {'id': 'opening-00', 'scene': 'opening', 'speech': 'A function reverses a mapping.'}
    original = BUILD.narration_fingerprint(beat)
    settings = json.loads(json.dumps(BUILD.SETTINGS))
    settings['lesson_rate_overrides']['intro'] = '-2%'
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


def test_short_clip_loudness_trim_preserves_timing_and_peak_headroom(tmp_path):
    target = tmp_path / 'short.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=900:duration=4',
                    '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(target)], check=True)
    before = BUILD.probe(target)
    result = BUILD.trim_master_loudness(target)
    after = BUILD.probe(target)
    assert abs(float(result['input_i']) + 18) < .25
    assert float(result['input_tp']) <= -1.5
    assert before['format']['duration'] == after['format']['duration']
