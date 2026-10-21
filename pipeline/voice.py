"""Read-only reference: FPL Day 2 runner and linked DAY-2 notebook.

The notebook's effective runtime rates include its long-form rate overrides.
This module never reads, executes or writes that repository at runtime.
"""
from __future__ import annotations

import math

VOICE = 'en-GB-RyanNeural'
EDGE_TTS_VERSION = '7.2.8'
DAY2_PROFILES = {
    'intro': {'rate': '+13%', 'pitch': '-4Hz', 'volume': '+0%'},
    'analysis': {'rate': '+17%', 'pitch': '-4Hz', 'volume': '+0%'},
    'key_stat': {'rate': '+18%', 'pitch': '+0Hz', 'volume': '+0%'},
    'warning': {'rate': '+11%', 'pitch': '-4Hz', 'volume': '+0%'},
    'outro': {'rate': '+11%', 'pitch': '-4Hz', 'volume': '+0%'},
}
# Keep the existing lesson/manifest profile names compatible.
PROFILE_MOODS = {
    'calm_intro': 'intro', 'excited_hook': 'intro',
    'calm_explain': 'analysis', 'slow_formal': 'analysis',
    'slow_formula': 'analysis', 'emphasis': 'key_stat',
    'friendly_mistake': 'warning', 'encouraging': 'key_stat',
    'warm_close': 'outro',
}
PITCH_PROFILES = {name: dict(DAY2_PROFILES[mood]) for name, mood in PROFILE_MOODS.items()}


def configure_edge_transport():
    """Match Day 2's pinned Edge transport; no provider fallback."""
    import edge_tts
    from edge_tts import communicate, constants
    if edge_tts.__version__ != EDGE_TTS_VERSION:
        raise RuntimeError(f'Ryan requires edge-tts=={EDGE_TTS_VERSION}; got {edge_tts.__version__}')
    endpoint = ('wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1'
                f'?Ocp-Apim-Subscription-Key={constants.TRUSTED_CLIENT_TOKEN}')
    constants.WSS_URL = communicate.WSS_URL = endpoint
    constants.WSS_HEADERS['Sec-WebSocket-Protocol'] = 'synthesize'
    communicate.WSS_HEADERS['Sec-WebSocket-Protocol'] = 'synthesize'


def speech_options(profile_name):
    return {**PITCH_PROFILES[profile_name], 'boundary': 'WordBoundary',
            'connect_timeout': 10, 'receive_timeout': 20}


def validate_word_stream(audio_bytes, words):
    """Reject silent output, missing boundaries and unusable sync timings."""
    if audio_bytes <= 0 or not words:
        raise ValueError('Ryan returned empty audio or no WordBoundary events')
    previous = -1.0
    for word in words:
        start, end = word['start'], word['end']
        if not word.get('word') or not all(math.isfinite(x) for x in (start, end)):
            raise ValueError('Invalid Ryan word boundary')
        if start < 0 or start < previous or end <= start:
            raise ValueError('Non-monotonic or non-positive Ryan word timing')
        previous = start
