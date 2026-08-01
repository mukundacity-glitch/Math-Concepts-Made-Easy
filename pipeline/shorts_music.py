# ==========================================
# PROCEDURAL SHORTS AUDIO
# CHANNEL: MathConceptsMadeEasy
#
# Copyright-free, fully automated background music + SFX for Shorts.
# No external audio assets and nothing pulled from the internet — every
# track is synthesized from scratch with numpy and written out as a
# plain WAV via the stdlib `wave` module, so there is zero licensing
# risk and zero manual step.
#
# Because the pipeline generates the beat grid itself (rather than
# detecting beats in someone else's track), every Short segment can be
# timed to land exactly on a beat_times[] entry — genuine beat-sync,
# not an approximation.
# ==========================================

import math
import wave

import numpy as np

SAMPLE_RATE = 44100

# Small note sets (Hz) so the arpeggio always sounds "in key" without
# needing real music theory. Two different scales/characters so the
# two daily Shorts don't share the same musical identity.
SCALES = {
    "major_pop":   [261.63, 293.66, 329.63, 392.00, 440.00],  # C D E G A
    "minor_drive": [220.00, 246.94, 261.63, 293.66, 329.63],  # A B C D E
}


def _kick(n_samples, sr=SAMPLE_RATE):
    """A short pitch-dropping thump — the classic 'kick drum' synth trick:
    sweep an oscillator's frequency down fast under a fast decay envelope."""
    n_samples = max(1, n_samples)
    t = np.arange(n_samples) / sr
    freq = 150.0 * np.exp(-t * 28.0)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    env = np.exp(-t * 18.0)
    return np.sin(phase) * env


def _hat(n_samples, seed=0):
    """A short filtered noise burst — a 'hi-hat' tick."""
    n_samples = max(1, n_samples)
    rng = np.random.RandomState(seed)
    t = np.arange(n_samples) / SAMPLE_RATE
    env = np.exp(-t * 60.0)
    noise = rng.uniform(-1.0, 1.0, n_samples)
    return noise * env


def _tone(freq, n_samples, wave_shape="square"):
    """A short synth note with a quick attack and decay."""
    n_samples = max(1, n_samples)
    t = np.arange(n_samples) / SAMPLE_RATE
    if wave_shape == "square":
        s = np.sign(np.sin(2 * np.pi * freq * t))
    else:
        s = np.sin(2 * np.pi * freq * t)
    env = np.minimum(1.0, 25.0 * t) * np.exp(-t * 4.0)
    return s * env


def generate_track(duration_sec, bpm, scale_name="major_pop", seed=0):
    """Synthesize `duration_sec` of upbeat, beat-locked music.

    Returns (samples: float32 ndarray in [-1, 1], beat_times: list[float])
    — beat_times are the exact second offsets every Short segment's
    cuts should be scheduled on.
    """
    sr = SAMPLE_RATE
    beat_dur = 60.0 / bpm
    n_beats = int(math.ceil(duration_sec / beat_dur)) + 1
    total_samples = int(duration_sec * sr) + sr
    mix = np.zeros(total_samples, dtype=np.float64)

    scale = SCALES.get(scale_name, SCALES["major_pop"])
    beat_times = []

    for i in range(n_beats):
        t0 = i * beat_dur
        start = int(t0 * sr)
        if start >= total_samples:
            break
        beat_times.append(t0)

        k = _kick(min(int(0.20 * sr), total_samples - start))
        mix[start:start + len(k)] += k * 0.9

        hstart = start + int(beat_dur * sr / 2)
        if hstart < total_samples:
            h = _hat(min(int(0.06 * sr), total_samples - hstart), seed=seed + i)
            mix[hstart:hstart + len(h)] += h * 0.35

        note = scale[i % len(scale)]
        n = _tone(note, min(int(beat_dur * 0.9 * sr), total_samples - start))
        mix[start:start + len(n)] += n * 0.18

    mix = mix[: int(duration_sec * sr)]
    peak = float(np.max(np.abs(mix))) or 1.0
    mix = np.tanh(mix / peak * 1.2) * 0.85
    beat_times = [b for b in beat_times if b <= duration_sec]
    return mix.astype(np.float32), beat_times


def generate_whoosh(duration_sec=0.18, seed=0):
    """A quick noise sweep for cut/flash transitions — one-pole lowpass
    with a rising cutoff, so it reads as a 'whoosh' rather than static."""
    sr = SAMPLE_RATE
    n = max(1, int(duration_sec * sr))
    rng = np.random.RandomState(seed)
    noise = rng.uniform(-1.0, 1.0, n)
    out = np.empty(n, dtype=np.float64)
    prev = 0.0
    for i in range(n):
        cutoff = 0.05 + 0.9 * (i / n)
        prev += cutoff * (noise[i] - prev)
        out[i] = prev
    t = np.arange(n) / sr
    env = np.sin(np.pi * t / duration_sec)
    return (out * env * 0.6).astype(np.float32)


def write_wav(path, samples, sr=SAMPLE_RATE):
    """Write mono float32 [-1, 1] samples out as a 16-bit PCM WAV."""
    samples = np.clip(samples, -1.0, 1.0)
    ints = (samples * 32767.0).astype(np.int16)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(ints.tobytes())


def mix_into(base, overlay, start_sec, gain=1.0, sr=SAMPLE_RATE):
    """Add `overlay` into `base` starting at start_sec, in place-safe
    (returns a new array). Used to stack whoosh SFX onto the music bed."""
    start = int(start_sec * sr)
    out = np.array(base, dtype=np.float64, copy=True)
    end = min(len(out), start + len(overlay))
    if start < len(out) and end > start:
        out[start:end] += overlay[: end - start] * gain
    return out
