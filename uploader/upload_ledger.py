"""Durable per-asset upload receipts. Ambiguous inserts require reconciliation.

The production runner commits and pushes an intent BEFORE sending a video and
its returned YouTube ID immediately afterward. Retrying a partially uploaded
day reuses completed IDs. A lost response never triggers a second insert.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "state/upload_ledger.json"


def read():
    return json.loads(PATH.read_text()) if PATH.exists() else {}


def save(data):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    staged = PATH.with_suffix(".tmp")
    staged.write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")
    staged.replace(PATH)
    if os.environ.get("MCME_PERSIST_UPLOAD_LEDGER") == "1":
        def git(*args):
            subprocess.run(["git", *args], cwd=ROOT, check=True)
        git("config", "user.name", "autopilot")
        git("config", "user.email", "actions@users.noreply.github.com")
        git("add", "state/upload_ledger.json")
        git("commit", "-m", "autopilot: checkpoint YouTube upload receipt")
        git("push", "origin", "HEAD:main")


def upload_once(day, key, insert, *, publish_at, privacy):
    ledger = read()
    assets = ledger.setdefault(str(day), {})
    previous = assets.get(key)
    if previous:
        if previous["status"] == "uploaded" and previous.get("video_id"):
            print(f"Reusing recorded {key}: https://youtu.be/{previous['video_id']}")
            return previous["video_id"]
        raise RuntimeError(f"Day {day} {key} has an uncertain prior upload. Reconcile its YouTube ID before retrying; duplicate upload blocked.")
    assets[key] = {"status": "uploading", "publish_at": publish_at, "privacy": privacy}
    save(ledger)
    video_id = insert()
    assets[key].update(status="uploaded", video_id=video_id)
    save(ledger)
    return video_id
