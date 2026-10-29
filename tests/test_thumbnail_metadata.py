import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from pipeline.thumbnail_metadata import thumbnail_metadata

ROOT = Path(__file__).resolve().parents[1]


def test_cinematic_thumbnail_does_not_need_a_legacy_timed_script(tmp_path):
    lesson = {'title': 'Even and Odd Functions', 'subject': 'Functions',
              'grade': 11, 'formula_spoken': 'Compare f of negative x'}
    result = thumbnail_metadata(lesson, tmp_path / 'absent.json')
    assert result['title'] == lesson['title']
    assert result['subject'] == 'Functions'
    assert result['grade'] == 11
    assert result['formula_spoken'] == lesson['formula_spoken']


def test_existing_legacy_thumbnail_metadata_is_preserved(tmp_path):
    path = tmp_path / 'timed.json'
    metadata = {'title': 'Existing title', 'thumbnail_features': [['target', 'A', 'B']]}
    path.write_text(json.dumps(metadata))
    assert thumbnail_metadata({'title': 'Curriculum title'}, path) == metadata
    path.write_text('invalid json')
    with pytest.raises(ValueError):
        thumbnail_metadata({'title': 'Curriculum title'}, path)


def test_missing_curriculum_title_fails_explicitly(tmp_path):
    with pytest.raises(ValueError, match='title'):
        thumbnail_metadata({}, tmp_path / 'absent.json')


def test_real_thumbnail_stage_after_cell1_without_cells2_or3(tmp_path):
    assets = tmp_path / 'assets'
    assets.mkdir()
    # Avoid networking in a regression; these are valid font files with the
    # same names the thumbnail stage already recognizes as cached assets.
    font = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    if not font.exists():
        pytest.skip('System test font unavailable')
    for name in ['Montserrat-Black.ttf', 'Montserrat-Bold.ttf']:
        shutil.copyfile(font, assets / name)
    env = dict(os.environ, MCME_OUTPUT_DIR=str(tmp_path), LESSON_DAY='44')
    for module in ['pipeline.cell1_lesson', 'pipeline.cell6_thumbnail']:
        subprocess.run([sys.executable, '-m', module], cwd=ROOT, env=env,
                       check=True, capture_output=True, text=True, timeout=60)
    assert not list((tmp_path / 'scripts').glob('*timed*'))
    thumbnails = list((tmp_path / 'thumbnails').glob('*.jpg'))
    assert len(thumbnails) == 1
    with Image.open(thumbnails[0]) as picture:
        assert picture.size == (1920, 1080)
        assert picture.format == 'JPEG'
