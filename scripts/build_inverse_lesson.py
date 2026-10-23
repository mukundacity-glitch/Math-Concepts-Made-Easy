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
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REMOTION = ROOT / 'remotion'
BUILD = REMOTION / 'build/inverse'
PUBLIC = REMOTION / 'public/inverse/audio'
STORY = REMOTION / 'src/inverse/storyboard.json'
FPS = 30


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


async def synthesize(beat: dict[str, Any], voice: str, semaphore: asyncio.Semaphore) -> dict[str, Any]:
    import edge_tts
    identifier = beat['id']
    raw = BUILD / f'{identifier}.mp3'
    target = PUBLIC / f'{identifier}.wav'
    receipt = BUILD / f'{identifier}.json'
    fingerprint = hashlib.sha256(json.dumps([beat, voice, '-5%', 'dry-v1'],
        sort_keys=True).encode()).hexdigest()
    async with semaphore:
        if target.exists() and receipt.exists():
            cached = json.loads(receipt.read_text())
            if cached.get('fingerprint') == fingerprint and cached.get('sha256') == digest(target):
                return cached
        for attempt in range(3):
            try:
                words: list[dict[str, Any]] = []
                communicator = edge_tts.Communicate(beat['speech'], voice, rate='-5%',
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
                filters = 'highpass=f=75,lowpass=f=14500,loudnorm=I=-16:TP=-1.5:LRA=7'
                process = await asyncio.create_subprocess_exec('ffmpeg', '-v', 'error', '-y',
                    '-i', str(raw), '-af', filters, '-ar', '48000', '-ac', '1',
                    '-c:a', 'pcm_s16le', str(target), stderr=asyncio.subprocess.PIPE)
                _, errors = await process.communicate()
                if process.returncode:
                    raise RuntimeError(errors.decode())
                media = probe(target)
                duration = float(media['format']['duration'])
                if not math.isfinite(duration) or not 0.3 < duration < 60 or words[-1]['end'] > duration + .1:
                    raise ValueError(f'Invalid narration duration for {identifier}')
                result = {'fingerprint': fingerprint, 'sha256': digest(target), 'voice': voice,
                    'durationSeconds': duration, 'words': words}
                receipt.write_text(json.dumps(result, indent=2)+'\n')
                print(f'{identifier}: {duration:.2f}s', flush=True)
                return result
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(1 + attempt)
    raise RuntimeError(f'Unreachable synthesis failure: {identifier}')


async def prepare(voice: str) -> dict[str, Any]:
    BUILD.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    # Some managed hosts provide an additional trusted CA; certificate validation stays enabled.
    certificate = os.environ.get('SSL_CERT_FILE')
    if certificate:
        import edge_tts.communicate
        edge_tts.communicate._SSL_CTX.load_verify_locations(cafile=certificate)
    story = json.loads(STORY.read_text())
    semaphore = asyncio.Semaphore(3)
    receipts = await asyncio.gather(*(synthesize(beat, voice, semaphore) for beat in story['beats']))
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
            'audioSrc': f"inverse/audio/{beat['id']}.wav", 'audioSha256': receipt['sha256']})
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
        'voice': voice, 'beats': len(beats), 'totalFrames': cursor, 'fps': FPS,
        'audioTreatment': 'Dry mono; highpass 75 Hz; lowpass 14.5 kHz; EBU R128 -16 LUFS / -1.5 dBTP',
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
        'audioCodec': audio['codec_name'], 'videoSha256': digest(output), 'completeNarrationBeats': len(props['beats'])}
    (BUILD / 'render-qa.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--voice', default='en-US-AndrewNeural')
    parser.add_argument('--scale', type=float, default=1.0, choices=[0.5, 1.0, 2.0])
    args = parser.parse_args()
    try:
        props = asyncio.run(prepare(args.voice))
        if not args.prepare_only:
            render(props, args.scale)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Inverse lesson build failed: {error}') from error


if __name__ == '__main__':
    main()
