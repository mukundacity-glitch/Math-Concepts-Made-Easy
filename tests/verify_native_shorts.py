"""Stream checks and phone-sized evidence from every completed native page."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.remotion_bridge import _sha256

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'output/native-shorts'
reports = []
for key in ['HOOK', 'FORMULA', 'MISTAKE']:
    props = json.loads((WORK / f'{key}.json').read_text())
    finals = list((ROOT / 'output/final_videos').glob(f'*_SHORT_{key}.mp4'))
    if len(finals) != 1:
        raise ValueError(f'Missing or ambiguous final {key}')
    final = finals[0]
    data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
        '-show_format', '-of', 'json', str(final)], text=True))
    video = next(s for s in data['streams'] if s['codec_type'] == 'video')
    expected_frames = sum(p['durationInFrames'] for p in props['pages'])
    assert (video['width'], video['height']) == (1080, 1920)
    assert video['r_frame_rate'] == '30/1'
    assert int(video['nb_frames']) == expected_frames
    assert expected_frames <= 5400
    assert any(s['codec_type'] == 'audio' for s in data['streams'])
    offset = 0
    for index, page in enumerate(props['pages']):
        for field, checksum in [('videoSrc', 'videoSha256'), ('audioSrc', 'audioSha256')]:
            assert _sha256(ROOT / 'remotion/public' / page[field]) == page[checksum]
        midpoint = offset + min(2, page['durationInFrames'] / 60)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(midpoint), '-i', str(final),
            '-frames:v', '1', '-vf', 'scale=360:640', str(WORK / f'{key}-{index}-phone.png')], check=True)
        offset += page['durationInFrames'] / 30
    reports.append({'key': key, 'frames': expected_frames, 'seconds': expected_frames / 30,
                    'sha256': _sha256(final), 'nativeBoardResolution': [840, 960],
                    'canvas': [1080, 1920], 'completePages': len(props['pages'])})
(WORK / 'verification.json').write_text(json.dumps(reports, indent=2) + '\n')
print(json.dumps(reports, indent=2))
