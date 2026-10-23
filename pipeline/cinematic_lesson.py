"""Produce the scheduled lesson through the approved shared cinematic renderer."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

from pipeline.cinematic_content import build_cinematic_plan
from pipeline.curriculum import get_lesson
from pipeline.paths import BASE_DIR, REPO_ROOT, get_day_number, safe_filename
from scripts.build_inverse_lesson import configure_ryan_transport, digest, probe, stamp, synthesize
from scripts.verify_inverse_master import verify_master

REMOTION = REPO_ROOT / 'remotion'


def preview_props(plan: dict) -> dict:
    result = json.loads(json.dumps(plan))
    for chapter in result['chapters']:
        for beat in chapter['beats']:
            beat['durationInFrames'] = math.ceil((len(beat['speech'].split()) / 2.2 + beat['holdSeconds']) * 30)
    return result


async def prepare(lesson: dict, work: Path) -> dict:
    plan = build_cinematic_plan(lesson)
    work.mkdir(parents=True, exist_ok=True)
    relative = f"cinematic/day-{lesson['day']:03d}"
    public = REMOTION / 'public' / relative
    public.mkdir(parents=True, exist_ok=True)
    configure_ryan_transport()
    beats = [beat for chapter in plan['chapters'] for beat in chapter['beats']]
    semaphore = asyncio.Semaphore(3)
    receipts = await asyncio.gather(*(synthesize(beat, semaphore, build_dir=work, public_dir=public) for beat in beats))
    for beat, receipt in zip(beats, receipts, strict=True):
        beat.update({'durationInFrames': math.ceil((receipt['durationSeconds'] + beat['holdSeconds']) * 30),
            'audioSrc': relative + '/' + beat['id'] + '.wav', 'audioSha256': receipt['sha256'], 'words': receipt['words']})
    (work / 'lesson.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')
    return plan


def export_captions(plan: dict, output: Path) -> None:
    captions: list[tuple[float, float, str]] = []
    cursor = 0
    for chapter in plan['chapters']:
        for beat in chapter['beats']:
            words = beat['words']
            for index in range(0, len(words), 6):
                group = words[index:index+6]
                captions.append((cursor / 30 + group[0]['start'], cursor / 30 + group[-1]['end'], ' '.join(item['text'] for item in group)))
            cursor += beat['durationInFrames']
    for extension, separator in [('srt', ','), ('vtt', '.')]:
        text = 'WEBVTT\n\n' if extension == 'vtt' else ''
        for index, (start, end, caption) in enumerate(captions, 1):
            text += f'{index}\n{stamp(start, separator)} --> {stamp(end, separator)}\n{caption}\n\n'
        output.with_suffix('.'+extension).write_text(text, encoding='utf8')


def build(day: int, *, prepare_only: bool = False) -> Path:
    lesson = get_lesson(day)
    work = BASE_DIR / 'cinematic' / f'day-{day:03d}'
    plan = asyncio.run(prepare(lesson, work))
    stem = f"Day_{day:03d}_{safe_filename(lesson['seo_title'])}"
    output = BASE_DIR / 'final_videos' / (stem + '.mp4')
    output.parent.mkdir(parents=True, exist_ok=True)
    if prepare_only: return work / 'lesson.json'
    beats = [beat for chapter in plan['chapters'] for beat in chapter['beats']]
    for beat in beats:
        if digest(REMOTION / 'public' / beat['audioSrc']) != beat['audioSha256']:
            raise ValueError('Narration changed after alignment: ' + beat['id'])
    subprocess.run(['npx', 'remotion', 'render', 'src/index.ts', 'CinematicLesson', str(output),
        '--props='+str(work/'lesson.json'), '--codec=h264', '--crf=18', '--audio-codec=aac',
        '--audio-bitrate=192k', '--concurrency=2', '--log=error'], cwd=REMOTION, check=True)
    media = probe(output)
    video = next(item for item in media['streams'] if item['codec_type'] == 'video')
    audio = [item for item in media['streams'] if item['codec_type'] == 'audio']
    frames = sum(beat['durationInFrames'] for beat in beats)
    if (video['width'], video['height']) != (1920, 1080) or video['avg_frame_rate'] != '30/1' or int(video['nb_frames']) != frames:
        raise ValueError('Cinematic master has invalid picture dimensions or timing')
    if len(audio) != 1 or audio[0]['sample_rate'] != '48000' or audio[0]['channels'] != 2:
        raise ValueError('Cinematic master requires exactly one 48 kHz stereo narration track')
    if any(item['codec_type'] == 'subtitle' for item in media['streams']):
        raise ValueError('Captions must remain optional sidecars')
    integrity = verify_master(output, {'beats': beats}, report_path=work/'narration-integrity.json')
    export_captions(plan, output)
    report = {'format': 'cinematic-v1', 'day': day, 'videoSha256': digest(output),
        'planSha256': digest(work/'lesson.json'), 'narrationBeats': len(beats),
        'verifiedNarrationBeats': integrity['verifiedBeats'], 'width': 1920, 'height': 1080,
        'frames': frames, 'voice': 'en-GB-RyanNeural', 'captions': 'optional-sidecars',
        'minimumLabelSize': 42, 'unreadableFallbackAllowed': False}
    output.with_name(f'Day_{day:03d}_cinematic-qa.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--day', type=int, default=get_day_number())
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args()
    if args.audit:
        from pipeline.curriculum import MASTER_CURRICULUM
        from pipeline.paths import read_state
        minimum = int(read_state()['next_day'])
        plans = [preview_props(build_cinematic_plan(lesson)) for lesson in MASTER_CURRICULUM if lesson['day'] >= minimum]
        destination = BASE_DIR / 'cinematic' / 'curriculum-audit.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(plans, ensure_ascii=False)+'\n')
        subprocess.run(['node', 'scripts-validate-cinematic.mjs', str(destination)], cwd=REMOTION, check=True)
    elif args.preview_only:
        work = BASE_DIR / 'cinematic' / f'day-{args.day:03d}'
        work.mkdir(parents=True, exist_ok=True)
        path = work / 'preview.json'
        path.write_text(json.dumps(preview_props(build_cinematic_plan(get_lesson(args.day))), indent=2)+'\n')
        print(path)
    else:
        print(build(args.day, prepare_only=args.prepare_only))


if __name__ == '__main__':
    main()
