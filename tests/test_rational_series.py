"""Engine tests for the Rational Numbers series.

These cover the data layer (colour, parsing, timing, captions), which is
what breaks silently.  They run without Manim installed:

    python -m unittest discover tests -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rational_series.color_engine import (  # noqa: E402
    MIN_ACCENT_CONTRAST,
    MIN_TEXT_CONTRAST,
    contrast_ratio,
    days_are_distinct,
    hue_distance,
    palette_for_day,
)
from rational_series.script_parser import (  # noqa: E402
    ScriptError,
    available_days,
    caption_chunks,
    estimate_duration,
    infer_concept,
    load_day,
    script_from_markdown,
    srt_from_cues,
)


class ColorEngineTests(unittest.TestCase):
    def test_palette_is_deterministic(self):
        self.assertEqual(palette_for_day(7).as_dict(), palette_for_day(7).as_dict())

    def test_consecutive_days_look_different(self):
        for day in range(1, 40):
            self.assertTrue(
                days_are_distinct(day, day + 1),
                f"Day {day} and {day + 1} are only {hue_distance(day, day + 1):.1f}° apart",
            )

    def test_day_one_and_two_are_far_apart(self):
        self.assertGreater(hue_distance(1, 2), 100.0)

    def test_text_and_accents_stay_legible(self):
        for day in (1, 2, 3, 17, 64, 365):
            palette = palette_for_day(day)
            self.assertGreaterEqual(contrast_ratio(palette.ink, palette.background), MIN_TEXT_CONTRAST)
            self.assertGreaterEqual(contrast_ratio(palette.accent, palette.background), MIN_ACCENT_CONTRAST)
            self.assertGreaterEqual(contrast_ratio(palette.thumbnail_ink, palette.thumbnail_bg), MIN_TEXT_CONTRAST)
            self.assertGreaterEqual(
                contrast_ratio(palette.thumbnail_accent, palette.thumbnail_bg), MIN_ACCENT_CONTRAST
            )

    def test_cycle_returns_distinct_colors(self):
        colors = palette_for_day(2).cycle(5)
        self.assertEqual(len(set(colors)), 5)


class ConceptDetectionTests(unittest.TestCase):
    def test_keywords_map_to_beats(self):
        cases = {
            "Let's quickly recap Day 1.": "recap",
            "Draw a square measuring one foot by one foot.": "draw_square",
            "Now draw the diagonal, corner to corner.": "draw_diagonal",
            "It sits on the number line between one and two.": "number_line",
            "Both cannot be true — a contradiction.": "contradiction",
            "Classify these four numbers.": "classify",
            "Tomorrow we look at decimals.": "outro",
        }
        for narration, expected in cases.items():
            self.assertEqual(infer_concept(narration), expected, narration)

    def test_unknown_narration_falls_back_to_statement(self):
        self.assertEqual(infer_concept("Here is something entirely new."), "statement")


class TimingTests(unittest.TestCase):
    def test_longer_narration_takes_longer(self):
        short = estimate_duration("A rational number is p over q.")
        long = estimate_duration("A rational number is p over q. " * 6)
        self.assertGreater(long, short)

    def test_minimum_block_length(self):
        self.assertGreaterEqual(estimate_duration("Yes."), 2.5)

    def test_captions_split_on_phrases(self):
        chunks = caption_chunks("Let's quickly recap Day 1. We learned that a rational number is p over q.")
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c.split()) <= 9 for c in chunks), chunks)


class ScriptTests(unittest.TestCase):
    def test_day_two_script_is_valid(self):
        script = load_day(2)
        self.assertEqual(script.day, 2)
        self.assertEqual(script.blocks[0].concept, "intro")
        self.assertTrue(any(b.concept == "draw_square" for b in script.blocks))
        self.assertTrue(any(b.concept == "draw_diagonal" for b in script.blocks))
        self.assertGreater(script.total_duration, 120)

    def test_every_shipped_script_validates(self):
        for day in available_days():
            load_day(day).validate()  # raises on any problem

    def test_timeline_is_contiguous(self):
        script = load_day(2)
        timeline = script.timeline()
        for (_s1, e1, _b1), (s2, _e2, _b2) in zip(timeline, timeline[1:]):
            self.assertAlmostEqual(e1, s2, places=6)

    def test_block_extra_keys_become_beat_params(self):
        script = load_day(2)
        square = next(b for b in script.blocks if b.concept == "draw_square")
        self.assertEqual(square.param("side_label"), "1 ft")

    def test_unknown_concept_is_rejected(self):
        payload = {"day": 9, "title": "T", "blocks": [{"concept": "teleport", "narration": "hello there"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "day9.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            from rational_series.script_parser import load_script

            with self.assertRaises(ScriptError):
                load_script(path)

    def test_markdown_scripts_are_supported(self):
        markdown = """
# Day 12 — Surds

- subtitle: Roots that refuse to simplify
- topic: Number Systems

## recap
- items: Irrational numbers | Proof by contradiction
Let's quickly recap Day 11.

## draw_square
- side_label: 1 m
Draw a square measuring one metre by one metre.
"""
        script = script_from_markdown(markdown)
        self.assertEqual(script.day, 12)
        self.assertEqual(script.title, "Surds")
        self.assertEqual([b.concept for b in script.blocks], ["recap", "draw_square"])
        self.assertEqual(script.blocks[0].param("items"), ["Irrational numbers", "Proof by contradiction"])
        self.assertEqual(script.blocks[1].param("side_label"), "1 m")


class CaptionExportTests(unittest.TestCase):
    def test_srt_from_cues(self):
        cues = [
            {"start": 0.0, "end": 6.0, "spoken": 6.0, "captions": ["Hello there.", "Welcome back."]},
            {"start": 6.0, "end": 10.0, "spoken": 4.0, "captions": ["Day two."]},
        ]
        srt = srt_from_cues(cues)
        self.assertIn("00:00:00,350 --> ", srt)
        self.assertIn("Day two.", srt)
        self.assertEqual(srt.count("-->"), 3)


class IntroEngineTests(unittest.TestCase):
    """Skipped automatically when Manim is not installed."""

    def setUp(self):
        try:
            import importlib

            importlib.import_module("rational_series.intro_generator")
        except ImportError as exc:  # pragma: no cover
            self.skipTest(f"manim unavailable: {exc}")

    def test_intro_is_deterministic_and_varied(self):
        from rational_series.intro_generator import generate_intro

        self.assertEqual(generate_intro(2), generate_intro(2))
        signatures = {
            (p.motif, p.entrance, p.camera_path, p.backdrop)
            for p in (generate_intro(d) for d in range(1, 25))
        }
        # 24 days should not collapse into a handful of identical openings.
        self.assertGreater(len(signatures), 15)

    def test_consecutive_days_get_different_motifs(self):
        from rational_series.intro_generator import generate_intro

        clashes = sum(1 for d in range(1, 60) if generate_intro(d).motif == generate_intro(d + 1).motif)
        self.assertLess(clashes, 12)


if __name__ == "__main__":
    unittest.main()
