"""Render the authored inverse-functions lesson, with dry word-timed narration.

python scripts/build_inverse_lesson.py --prepare-only
python scripts/build_inverse_lesson.py
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REMOTION = ROOT / 'remotion'
BUILD = REMOTION / 'build/inverse'
PUBLIC = REMOTION / 'public/inverse/audio'
STORY = REMOTION / 'src/inverse/storyboard.json'
FPS = 30
SETTINGS_PATH = ROOT / 'scripts/day2_ryan_settings.json'
SETTINGS = json.loads(SETTINGS_PATH.read_text())
VOICE = SETTINGS['voice']


def voice_profile(scene: str) -> dict[str, str]:
    mood = SETTINGS['scene_moods'][scene]
    profile = dict(SETTINGS['moods'][mood])
    profile['rate'] = SETTINGS['lesson_rate_overrides'][mood]
    return profile


def narration_fingerprint(beat: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps([beat, SETTINGS, 'day2-ryan-premium-paced-v1'],
        sort_keys=True).encode()).hexdigest()


def configure_ryan_transport() -> None:
    import edge_tts
    import edge_tts.communicate as communicate
    from edge_tts import constants
    if edge_tts.__version__ != SETTINGS['edge_tts_version']:
        raise RuntimeError('Install scripts/requirements-inverse.txt for the tested Day 2 Ryan transport')
    endpoint = SETTINGS['transport'] + '?Ocp-Apim-Subscription-Key=' + constants.TRUSTED_CLIENT_TOKEN
    constants.WSS_URL = endpoint
    communicate.WSS_URL = endpoint
    constants.WSS_HEADERS['Sec-WebSocket-Protocol'] = 'synthesize'
    communicate.WSS_HEADERS['Sec-WebSocket-Protocol'] = 'synthesize'
    certificate = os.environ.get('SSL_CERT_FILE')
    if certificate:
        communicate._SSL_CTX.load_verify_locations(cafile=certificate)


def measure_loudness(path: Path, prefilter: str = '') -> dict[str, str]:
    mastering = SETTINGS['mastering']
    analyzer = (f"loudnorm=I={mastering['integrated_lufs']}:"
        f"TP={mastering['true_peak_dbtp']}:LRA={mastering['lra_lu']}:print_format=json")
    filters = f'{prefilter},{analyzer}' if prefilter else analyzer
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path),
        '-map', '0:a:0', '-af', filters, '-f', 'null', '-'],
        check=True, capture_output=True, text=True)
    matches = re.findall(r'\{\s*"input_i"[\s\S]*?\}', result.stderr)
    if len(matches) != 1:
        raise ValueError('Expected one stable narration loudness measurement')
    measurement = json.loads(matches[0])
    for key in ['input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset']:
        if not math.isfinite(float(measurement[key])):
            raise ValueError('Narration loudness measurement is not finite')
    return measurement


def day2_loudnorm_filter(measurement: dict[str, str]) -> str:
    mastering = SETTINGS['mastering']
    return (f"loudnorm=I={mastering['integrated_lufs']}:TP={mastering['true_peak_dbtp']}:"
        f"LRA={mastering['lra_lu']}:measured_I={measurement['input_i']}:"
        f"measured_TP={measurement['input_tp']}:measured_LRA={measurement['input_lra']}:"
        f"measured_thresh={measurement['input_thresh']}:offset={measurement['target_offset']}:"
        'linear=true:print_format=none')


def trim_master_loudness(path: Path) -> dict[str, str]:
    """Correct measured short-clip gating error without changing duration or adding room effects."""
    actual = measure_loudness(path)
    mastering = SETTINGS['mastering']
    gain = mastering['integrated_lufs'] - float(actual['input_i'])
    if abs(gain) > .2:
        if abs(gain) > 6:
            raise ValueError('Unexpected mastering gain; refusing a damaged narration clip')
        if float(actual['input_tp']) + gain > mastering['true_peak_dbtp']:
            raise ValueError('Loudness correction would exceed the approved true-peak ceiling')
        temporary = path.with_name(path.stem + '.levelled.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-af', f'volume={gain:.5f}dB',
            '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(temporary)], check=True)
        temporary.replace(path)
        actual = measure_loudness(path)
    return actual


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_format',
        '-show_streams', '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def stamp(seconds: float, separator: str = ',') -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02}{separator}{millis:03}'


async def synthesize(beat: dict[str, Any], semaphore: asyncio.Semaphore, *,
                     build_dir: Path | None = None, public_dir: Path | None = None) -> dict[str, Any]:
    import edge_tts
    identifier = beat['id']
    build_dir = BUILD if build_dir is None else build_dir
    public_dir = PUBLIC if public_dir is None else public_dir
    raw = build_dir / f'{identifier}.mp3'
    target = public_dir / f'{identifier}.wav'
    receipt = build_dir / f'{identifier}.json'
    fingerprint = narration_fingerprint(beat)
    profile = voice_profile(beat['scene'])
    async with semaphore:
        if target.exists() and receipt.exists():
            cached = json.loads(receipt.read_text())
            if cached.get('fingerprint') == fingerprint and cached.get('sha256') == digest(target):
                return cached
        for attempt in range(3):
            try:
                words: list[dict[str, Any]] = []
                communicator = edge_tts.Communicate(beat['speech'], VOICE, **profile,
                    boundary='WordBoundary', connect_timeout=15, receive_timeout=45)
                with raw.open('wb') as output:
                    async for chunk in communicator.stream():
                        if chunk['type'] == 'audio':
                            output.write(chunk['data'])
                        elif chunk['type'] == 'WordBoundary':
                            words.append({'text': chunk['text'], 'start': chunk['offset'] / 10000000,
                                'end': (chunk['offset'] + chunk['duration']) / 10000000})
                if not words or raw.stat().st_size < 1000:
                    raise ValueError(f'Missing real narration/word timing for {identifier}')
                # Preserve timing: no time stretching, room effects, echo or silence trimming.
                measurement = measure_loudness(raw)
                filters = day2_loudnorm_filter(measurement)
                process = await asyncio.create_subprocess_exec('ffmpeg', '-v', 'error', '-y',
                    '-i', str(raw), '-af', filters, '-ar', '48000', '-ac', '2',
                    '-c:a', 'pcm_s24le', str(target), stderr=asyncio.subprocess.PIPE)
                _, errors = await process.communicate()
                if process.returncode:
                    raise RuntimeError(errors.decode())
                media = probe(target)
                duration = float(media['format']['duration'])
                if not math.isfinite(duration) or not 0.3 < duration < 60 or words[-1]['end'] > duration + .1:
                    raise ValueError(f'Invalid narration duration for {identifier}')
                post_measurement = trim_master_loudness(target)
                if abs(float(post_measurement['input_i']) + 18.0) > 0.8:
                    raise ValueError(f'Day 2 narration loudness missed target for {identifier}')
                if float(post_measurement['input_tp']) > -1.0:
                    raise ValueError(f'Narration true peak exceeded the ceiling for {identifier}')
                result = {'fingerprint': fingerprint, 'sha256': digest(target), 'voice': VOICE,
                    'profile': profile, 'loudness': post_measurement,
                    'durationSeconds': duration, 'words': words}
                receipt.write_text(json.dumps(result, indent=2)+'\n')
                print(f'{identifier}: {duration:.2f}s', flush=True)
                return result
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(1 + attempt)
    raise RuntimeError(f'Unreachable synthesis failure: {identifier}')


async def prepare() -> dict[str, Any]:
    BUILD.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    configure_ryan_transport()
    story = json.loads(STORY.read_text())
    semaphore = asyncio.Semaphore(3)
    receipts = await asyncio.gather(*(synthesize(beat, semaphore) for beat in story['beats']))
    beats = []
    captions = []
    cursor = 0
    chapters = []
    last_scene = None
    for beat, receipt in zip(story['beats'], receipts, strict=True):
        if beat['scene'] != last_scene:
            chapters.append({'title': beat['title'], 'startSeconds': cursor / FPS})
            last_scene = beat['scene']
        frames = math.ceil((receipt['durationSeconds'] + beat['holdSeconds']) * FPS)
        beats.append({**beat, 'durationInFrames': frames,
            'audioSrc': f"inverse/audio/{beat['id']}.wav", 'audioSha256': receipt['sha256'],
            'words': receipt['words']})
        words = receipt['words']
        for index in range(0, len(words), 6):
            group = words[index:index+6]
            captions.append((cursor / FPS + group[0]['start'], cursor / FPS + group[-1]['end'],
                ' '.join(word['text'] for word in group)))
        cursor += frames
    props = {'beats': beats}
    (BUILD / 'lesson.json').write_text(json.dumps(props, indent=2, ensure_ascii=False)+'\n')
    for suffix, separator in [('srt', ','), ('vtt', '.')]:
        text = 'WEBVTT\n\n' if suffix == 'vtt' else ''
        for index, (start, end, caption) in enumerate(captions, 1):
            text += f'{index}\n{stamp(start, separator)} --> {stamp(end, separator)}\n{caption}\n\n'
        (BUILD / f'Inverse-Functions.{suffix}').write_text(text)
    (BUILD / 'chapters.json').write_text(json.dumps(chapters, indent=2)+'\n')
    (BUILD / 'narration.txt').write_text('\n\n'.join(beat['speech'] for beat in beats)+'\n')
    (BUILD / 'source-proof.json').write_text(json.dumps({'storyboardSha256': digest(STORY),
        'voice': VOICE, 'settingsSha256': digest(SETTINGS_PATH), 'beats': len(beats), 'totalFrames': cursor, 'fps': FPS,
        'audioTreatment': 'Day 2 Ryan pitch/volume; premium lesson rates; stereo 48 kHz PCM; two-pass -18 LUFS / -1.5 dBTP',
        'burnedInCaptions': False}, indent=2)+'\n')
    return props



def render(props: dict[str, Any], scale: float) -> None:
    for beat in props['beats']:
        path = REMOTION / 'public' / beat['audioSrc']
        if digest(path) != beat['audioSha256']:
            raise ValueError(f"Narration changed after timing: {beat['id']}")
    output = BUILD / 'Inverse-Functions.mp4'
    subprocess.run(['npx', 'remotion', 'render', 'src/index.ts', 'InverseFunctions', str(output),
        '--props=' + str(BUILD / 'lesson.json'), '--codec=h264', '--crf=18',
        '--audio-codec=aac', '--audio-bitrate=192k', '--concurrency=2',
        '--scale=' + str(scale), '--log=error'], cwd=REMOTION, check=True)
    media = probe(output)
    video = next(stream for stream in media['streams'] if stream['codec_type'] == 'video')
    audio = next(stream for stream in media['streams'] if stream['codec_type'] == 'audio')
    expected = sum(beat['durationInFrames'] for beat in props['beats']) / FPS
    if video['width'] != round(1920 * scale) or video['height'] != round(1080 * scale):
        raise ValueError('Final video dimensions do not match the requested full-frame canvas')
    if abs(float(media['format']['duration']) - expected) > .1:
        raise ValueError('Final video duration disagrees with narration timeline')
    report = {'width': video['width'], 'height': video['height'], 'durationSeconds': expected,
        'audioCodec': audio['codec_name'], 'videoSha256': digest(output), 'completeNarrationBeats': len(props['beats']), 'optionalEnglishCaptionSidecar': 'Inverse-Functions.srt'}
    (BUILD / 'render-qa.json').write_text(json.dumps(report, indent=2)+'\n')
    subprocess.run([sys.executable, str(ROOT / 'scripts/verify_inverse_master.py')], check=True)
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--scale', type=float, default=1.0, choices=[0.5, 1.0, 2.0])
    args = parser.parse_args()
    try:
        props = asyncio.run(prepare())
        if not args.prepare_only:
            render(props, args.scale)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Inverse lesson build failed: {error}') from error


if __name__ == '__main__':
    main()
