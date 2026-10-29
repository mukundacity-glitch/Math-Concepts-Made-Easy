"""Thumbnail content needs curriculum metadata, never audio timestamps."""
from __future__ import annotations

import json
from pathlib import Path


def thumbnail_metadata(lesson: dict, timed_script: Path) -> dict:
    if timed_script.exists():
        with timed_script.open(encoding='utf8') as source:
            return json.load(source)
    # Cinematic production bypasses Cells 2/3. Its thumbnail still has the
    # same title/subject/formula in the Cell-1 curriculum configuration.
    title = lesson.get('title') or lesson.get('topic')
    if not isinstance(title, str) or not title.strip():
        raise ValueError('Thumbnail requires a curriculum title')
    return {**lesson, 'title': title, 'subject': lesson.get('subject', 'MATH'),
            'formula_spoken': lesson.get('formula_spoken', '')}
