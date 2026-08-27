"""Exactly-once, in-order publishing state transitions.

The uploaded list and next_day move together.  Keeping this logic outside the
workflow YAML prevents a completed lesson from being uploaded twice and keeps
tests valid after the counter advances.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import MutableMapping

from pipeline.curriculum import TOTAL_DAYS
from pipeline.paths import MIN_OPEN_DAY


def _day_set(state: MutableMapping, key: str) -> set[int]:
    return {int(day) for day in state.get(key, [])}


def validate_next_publish_day(
    state: MutableMapping,
    requested_day: int | None = None,
) -> int:
    """Return the one lesson currently eligible for upload.

    Scheduled and recovery workflows may only publish ``next_day``.  Already
    uploaded lessons and gaps are rejected before any YouTube API call.
    """

    raw_uploaded = [int(day) for day in state.get("uploaded", [])]
    uploaded = set(raw_uploaded)
    if len(raw_uploaded) != len(uploaded):
        raise ValueError("progress state is inconsistent: uploaded contains duplicates")

    next_day = int(state.get("next_day", MIN_OPEN_DAY))
    inferred_next = max(MIN_OPEN_DAY, max(uploaded, default=MIN_OPEN_DAY - 1) + 1)
    expected_history = set(range(1, inferred_next))

    if uploaded != expected_history:
        missing = sorted(expected_history - uploaded)
        unexpected = sorted(uploaded - expected_history)
        raise ValueError(
            "progress state is inconsistent: uploaded history is not contiguous "
            f"(missing={missing}, unexpected={unexpected})"
        )

    if next_day != inferred_next:
        raise ValueError(
            "progress state is inconsistent: "
            f"next_day is {next_day}, but uploaded history requires {inferred_next}"
        )

    day = next_day if requested_day is None else int(requested_day)
    if day < MIN_OPEN_DAY:
        raise ValueError(f"Day {day} is already posted and locked")
    if day in uploaded:
        raise ValueError(f"Day {day} is already uploaded and locked")
    if day != next_day:
        raise ValueError(
            f"Day {day} is out of sequence; the next unpublished lesson is Day {next_day}"
        )
    if day > TOTAL_DAYS:
        raise ValueError(f"Curriculum complete — all {TOTAL_DAYS} lessons are uploaded")
    return day


def mark_uploaded(
    state: MutableMapping,
    day: int,
    *,
    when: dt.datetime | None = None,
) -> MutableMapping:
    """Atomically advance progress after a confirmed YouTube upload."""

    day = validate_next_publish_day(state, day)
    for key in ("completed", "uploaded"):
        days = _day_set(state, key)
        days.add(day)
        state[key] = sorted(days)

    state["locked_through_day"] = day
    state["open_from_day"] = day + 1
    state["next_day"] = day + 1
    state["last_run"] = (when or dt.datetime.now(dt.timezone.utc)).isoformat(
        timespec="seconds"
    )
    state["note"] = (
        "Uploaded lessons are locked. next_day is the only lesson eligible "
        "for automatic publishing."
    )
    return state
