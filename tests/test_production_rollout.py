"""Publishing retry safety and portrait content completeness."""
import json
from datetime import datetime, time, timezone

import pytest

from pipeline.curriculum import get_lesson
from pipeline.native_shorts import short_plans
from uploader import upload_ledger, youtube_upload


def test_native_short_preserves_complete_worked_example():
    lesson = get_lesson(43)
    plans = short_plans(lesson)
    assert set(plans) == {"HOOK", "FORMULA", "MISTAKE"}
    assert [p["display"] for p in plans["FORMULA"]["pages"]] == lesson["board_examples"]["worked_example"]
    assert all(page["speech"] and page["display"] for plan in plans.values() for page in plan["pages"])


def test_partial_upload_retry_reuses_returned_video_id(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_ledger, "PATH", tmp_path / "ledger.json")
    monkeypatch.delenv("MCME_PERSIST_UPLOAD_LEDGER", raising=False)
    inserted = []
    def insert():
        inserted.append(1)
        return "original-youtube-id"
    for _ in range(2):
        assert upload_ledger.upload_once(43, "MAIN", insert, publish_at=None, privacy="private") == "original-youtube-id"
    assert len(inserted) == 1


def test_ambiguous_insert_is_not_repeated(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_ledger, "PATH", tmp_path / "ledger.json")
    monkeypatch.delenv("MCME_PERSIST_UPLOAD_LEDGER", raising=False)
    def lost_response():
        raise ConnectionError("Response lost after request")
    with pytest.raises(ConnectionError):
        upload_ledger.upload_once(43, "HOOK", lost_response, publish_at=None, privacy="public")
    with pytest.raises(RuntimeError, match="duplicate upload blocked"):
        upload_ledger.upload_once(43, "HOOK", lambda: pytest.fail("Duplicate insert"), publish_at=None, privacy="public")


@pytest.mark.parametrize("utc,slot,expected", [
    ("2026-10-23T17:00:00+00:00", time(12), "2026-10-24T16:00:00Z"),
    ("2026-10-23T10:00:00+00:00", time(9), "2026-10-23T13:00:00Z"),
    ("2026-11-02T10:00:00+00:00", time(9), "2026-11-02T14:00:00Z"),
])
def test_schedule_keeps_local_slots_and_never_posts_immediately(monkeypatch, utc, slot, expected):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat(utc).astimezone(tz or timezone.utc)
    monkeypatch.setattr(youtube_upload, "datetime", Clock)
    assert youtube_upload._compute_local_publish_at(slot) == expected
