import datetime as dt
from pathlib import Path

import pytest

from pipeline.curriculum import MASTER_CURRICULUM, TOTAL_DAYS, get_lesson
from pipeline.paths import MIN_OPEN_DAY, read_state
from pipeline.progress import mark_uploaded, validate_next_publish_day


ROOT = Path(__file__).resolve().parents[1]


def test_progress_is_contiguous_and_moves_with_each_upload():
    state = read_state()
    next_day = int(state["next_day"])
    assert MIN_OPEN_DAY <= next_day <= TOTAL_DAYS + 1
    assert state["uploaded"] == list(range(1, next_day))
    assert set(state["uploaded"]).issubset(state["completed"])
    assert state["locked_through_day"] == next_day - 1
    assert state["open_from_day"] == next_day
    if next_day <= TOTAL_DAYS:
        assert validate_next_publish_day(state) == next_day


def test_state_transition_is_not_hardcoded_to_one_video_number():
    state = {
        "next_day": 23,
        "completed": list(range(1, 23)),
        "uploaded": list(range(1, 23)),
        "locked_through_day": 22,
        "open_from_day": 23,
    }
    mark_uploaded(
        state,
        23,
        when=dt.datetime(2026, 8, 27, tzinfo=dt.timezone.utc),
    )
    assert state["next_day"] == 24
    assert state["locked_through_day"] == 23
    assert state["open_from_day"] == 24
    assert state["uploaded"][-1] == 23
    assert validate_next_publish_day(state) == 24
    with pytest.raises(ValueError, match="already uploaded"):
        validate_next_publish_day(state, 23)

    state["uploaded"].append(23)
    with pytest.raises(ValueError, match="contains duplicates"):
        validate_next_publish_day(state)


def test_resume_boundary_has_content_for_required_teaching_stages():
    lesson = get_lesson(MIN_OPEN_DAY)
    assert lesson["status"] == "active"
    assert len(lesson["board_examples"]["worked_example"]) >= 2
    assert len(lesson["board_examples"]["practice"]) >= 1
    assert lesson["key_formula"]


def test_every_future_lesson_can_pass_required_stage_selection():
    required = {
        "topic", "subtopic", "lesson_goal", "real_world_hook",
        "concept_intuition", "key_formula", "common_mistake",
    }
    for lesson in (
        item for item in MASTER_CURRICULUM if item["day"] >= MIN_OPEN_DAY
    ):
        assert all(lesson.get(field) for field in required), lesson["day"]
        board = lesson.get("board_examples", {})
        assert board.get("worked_example"), lesson["day"]
        assert board.get("practice"), lesson["day"]


def test_daily_workflow_is_dst_safe_and_fail_closed():
    workflow = (ROOT / ".github/workflows/daily-video.yml").read_text(encoding="utf-8")
    assert 'cron: "0 10 * * *"' in workflow
    assert 'cron: "0 11 * * *"' in workflow
    assert "YT_MAIN_PUBLISH_LOCAL_TIME" in workflow
    assert "09:00" in workflow
    assert "--no-advance" in workflow
    assert "Advance progress only after upload succeeds" in workflow
    assert "validate_next_publish_day" in workflow
    assert "mark_uploaded" in workflow


def test_all_upload_entry_points_use_the_same_duplicate_guard():
    uploader = (ROOT / "uploader/youtube_upload.py").read_text(encoding="utf-8")
    recovery = (ROOT / ".github/workflows/publish-video.yml").read_text(
        encoding="utf-8"
    )
    assert "validate_next_publish_day" in uploader
    assert "mark_uploaded" in recovery
    assert "group: daily-lesson-production" in recovery
