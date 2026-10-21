"""Offline contract and actual FFmpeg checks; never contact a TTS provider."""
import json
import subprocess

import pytest

from pipeline.voice import VOICE, speech_options, validate_word_stream
from pipeline.audio_master import narration_filter


def test_day2_effective_profiles_preserve_existing_scene_names():
    assert VOICE == 'en-GB-RyanNeural'
    expected = {
        'calm_intro': ('+13%', '-4Hz'), 'excited_hook': ('+13%', '-4Hz'),
        'calm_explain': ('+17%', '-4Hz'), 'slow_formal': ('+17%', '-4Hz'),
        'slow_formula': ('+17%', '-4Hz'), 'emphasis': ('+18%', '+0Hz'),
        'encouraging': ('+18%', '+0Hz'), 'friendly_mistake': ('+11%', '-4Hz'),
        'warm_close': ('+11%', '-4Hz'),
    }
    for name, (rate, pitch) in expected.items():
        assert speech_options(name) == dict(rate=rate, pitch=pitch, volume='+0%',
            boundary='WordBoundary', connect_timeout=10, receive_timeout=20)
    with pytest.raises(KeyError):
        speech_options('unrecognized')


def test_missing_audio_or_bad_timing_cannot_silently_pass():
    valid = [{'word': 'three', 'start': 0.1, 'end': 0.3},
             {'word': 'apples', 'start': 0.4, 'end': 0.9}]
    validate_word_stream(1024, valid)
    for size, words in [(0, valid), (1024, []), (1024, valid[::-1]),
                        (1024, [{'word': 'x', 'start': 1, 'end': 1}]),
                        (1024, [{'word': 'x', 'start': float('nan'), 'end': 2}])]:
        with pytest.raises(ValueError):
            validate_word_stream(size, words)


def test_day2_loudness_is_measured_and_mastered(tmp_path):
    tone, mastered = tmp_path / 'tone.wav', tmp_path / 'mastered.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=4', str(tone)], check=True)
    audio_filter = narration_filter(tone)
    assert 'measured_I=' in audio_filter
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(tone), '-af', audio_filter,
                    '-ar', '48000', '-ac', '2', str(mastered)], check=True)
    result = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(mastered), '-af',
        'loudnorm=I=-18:TP=-1.5:LRA=7:print_format=json', '-f', 'null', '-'],
        check=True, capture_output=True, text=True)
    report = json.loads(result.stderr[result.stderr.rfind('{'):result.stderr.rfind('}')+1])
    assert abs(float(report['input_i']) + 18) < 0.3
    assert float(report['input_tp']) <= -1.5
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
        'stream=sample_rate,channels', '-of', 'json', str(mastered)],
        check=True, capture_output=True, text=True)
    stream = json.loads(probe.stdout)['streams'][0]
    assert stream['sample_rate'] == '48000'
    assert stream['channels'] == 2
