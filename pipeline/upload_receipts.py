"""Persist confirmed video IDs so a partial package retry reuses its uploads."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.paths import REPO_ROOT

RECEIPTS_PATH = REPO_ROOT / "state" / "upload_receipts.json"


def read_receipts(path: Path = RECEIPTS_PATH) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("upload receipts must be an object")
    return data


def receipt_for(day: int, asset: str, path: Path = RECEIPTS_PATH) -> str | None:
    return read_receipts(path).get(str(day), {}).get(asset)


def save_receipt(day: int, asset: str, video_id: str, path: Path = RECEIPTS_PATH) -> None:
    if not isinstance(video_id, str) or not video_id.strip():
        raise ValueError("a confirmed YouTube video ID is required")
    data = read_receipts(path)
    data.setdefault(str(day), {})[asset] = video_id
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    temporary.replace(path)
