"""The pacing engine has to work for the whole curriculum, not one day.

Every check here runs against the real `curriculum/*.json`, so a lesson
that would render as a static screen — or a formula that cannot be built
piece by piece — fails the build instead of quietly shipping.
"""

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.constants import PACING, SCENE_ORDER  # noqa: E402
from pipeline.mathtext import latex_to_plain  # noqa: E402
from pipeline.pacing import (  # noqa: E402
    CONSTRUCTION_KINDS, choose_construction, fill_times, split_latex_parts,
)


def load_lessons():
    lessons = []
    for path in sorted((REPO / "curriculum").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for lesson in data.get("lessons", []):
            if lesson.get("status") == "active":
                lessons.append((path.name, lesson))
    return lessons


LESSONS = load_lessons()


def board_of(lesson):
    board = lesson.get("board_examples", {}) or {}
    raw = list(board.get("worked_example", []) or []) + \
        list(board.get("practice", []) or [])
    return [latex_to_plain(line) for line in raw], raw


class CurriculumIsLoaded(unittest.TestCase):
    def test_there_are_lessons_to_check(self):
        self.assertGreater(len(LESSONS), 10)


class EveryLessonHasSomethingToBuild(unittest.TestCase):
    def test_no_lesson_falls_through_to_a_static_screen(self):
        missing = []
        for source, lesson in LESSONS:
            plain, raw = board_of(lesson)
            if choose_construction(plain, raw) is None:
                missing.append(f"{source} day {lesson['day']}")
        self.assertEqual(missing, [],
                         "these lessons have nothing to animate: "
                         f"{missing}")

    def test_every_choice_is_a_kind_cell4_can_draw(self):
        for source, lesson in LESSONS:
            plain, raw = board_of(lesson)
            choice = choose_construction(plain, raw)
            if choice is None:
                continue
            self.assertIn(choice[0], CONSTRUCTION_KINDS,
                          f"{source} day {lesson['day']}")

    def test_the_choice_is_stable(self):
        """Same lesson in, same construction out — renders must not vary."""
        for _, lesson in LESSONS[:12]:
            plain, raw = board_of(lesson)
            first = choose_construction(plain, raw)
            second = choose_construction(plain, raw)
            self.assertEqual(repr(first), repr(second))

    def test_the_reviewed_decimals_lesson_earns_a_comparison(self):
        """Day 3 is the lesson the review was written about: terminating
        against recurring is exactly the side-by-side it asked for, and
        it has to come out of the lesson's own board."""
        day3 = next(l for _, l in LESSONS if l["day"] == 3)
        kind, spec = choose_construction(*board_of(day3))
        self.assertEqual(kind, "compare")
        self.assertTrue(spec["left"]["terminating"])
        self.assertFalse(spec["right"]["terminating"])
        self.assertTrue(spec["left"]["steps"],
                        "the terminating decimal must divide out digit by digit")

    def test_the_next_lesson_earns_a_live_expansion(self):
        """Day 4 is Laws of Exponents — the same engine, no new code."""
        day4 = next(l for _, l in LESSONS if l["day"] == 4)
        kind, payload = choose_construction(*board_of(day4))
        self.assertEqual(kind, "expansion")
        base, exponent = payload
        self.assertGreaterEqual(exponent, 2)


class EveryFormulaCanBeBuilt(unittest.TestCase):
    def test_parts_always_rebuild_the_original_formula(self):
        for source, lesson in LESSONS:
            formula = lesson.get("key_formula", "")
            self.assertEqual("".join(split_latex_parts(formula)), formula,
                             f"{source} day {lesson['day']}")

    def test_most_formulas_split_into_more_than_one_stroke(self):
        """A formula that cannot be split lands in one frame — the exact
        thing the review objected to. A few atoms are fine; a majority
        would mean the splitter is not doing its job."""
        splittable = sum(1 for _, lesson in LESSONS
                         if len(split_latex_parts(lesson.get("key_formula", ""))) > 1)
        self.assertGreater(splittable, len(LESSONS) * 0.8,
                           f"only {splittable}/{len(LESSONS)} formulas build "
                           "in stages")


class NarrationIsCovered(unittest.TestCase):
    """The pacing budget applied to real narration lengths.

    Scene durations are not known until Cell 3 has spoken the script, so
    this checks the shape of the guarantee: however long a scene runs,
    the budget breaks it into stretches no viewer sees as frozen.
    """

    def test_a_long_scene_is_broken_into_short_stretches(self):
        budget = PACING["max_static_seconds"]
        for duration in (12.0, 25.0, 40.0, 75.0):
            marks = [0.0] + fill_times(0.0, duration, budget) + [duration]
            gaps = [b - a for a, b in zip(marks, marks[1:])]
            self.assertLessEqual(max(gaps), budget + 1e-6)

    def test_the_lesson_has_all_nine_scenes_to_pace(self):
        self.assertEqual(len(SCENE_ORDER), 9)


if __name__ == "__main__":
    unittest.main()
