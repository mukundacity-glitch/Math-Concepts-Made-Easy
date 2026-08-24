from pathlib import Path

from pipeline.curriculum import MASTER_CURRICULUM, get_lesson
from pipeline.paths import MIN_OPEN_DAY, read_state


ROOT = Path(__file__).resolve().parents[1]


def test_day_22_is_next_and_previous_videos_are_locked():
    state = read_state()
    assert MIN_OPEN_DAY == 22
    assert state["next_day"] == 22
    assert state["completed"] == list(range(1, 22))
    assert state["uploaded"] == list(range(1, 22))


def test_day_22_has_content_for_required_teaching_stages():
    lesson = get_lesson(22)
    assert lesson["status"] == "active"
    assert len(lesson["board_examples"]["worked_example"]) >= 2
    assert len(lesson["board_examples"]["practice"]) >= 1
    assert lesson["key_formula"]


def test_every_future_lesson_can_pass_required_stage_selection():
    required = {
        "topic", "subtopic", "lesson_goal", "real_world_hook",
        "concept_intuition", "key_formula", "common_mistake",
    }
    for lesson in (item for item in MASTER_CURRICULUM if item["day"] >= 22):
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
