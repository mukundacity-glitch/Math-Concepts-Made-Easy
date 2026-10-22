"""Render-level test: every premium item shown with deterministic cue timings.

This smoke test uses silence and *synthetic* word timestamps. It validates
pagination, transitions and frame bounds; it does not certify recorded speech.
Production fails closed unless Cell 3 creates real word-boundary timestamps.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from manim import Scene, config

from pipeline.mathtext import normalize_word
from pipeline.premium_animation import build_premium_visual_plan
from pipeline.premium_manim_helpers import render_premium_board

ROOT = Path(__file__).resolve().parents[1]
DEMO = json.loads((ROOT / "examples" / "premium_algebra_lesson.json").read_text())
PLAN = build_premium_visual_plan(DEMO)
AUDIO = ROOT / "build" / "phase3-smoke" / "audio"
config.background_color = "#081B33"


class DeterministicSyntheticWordClock:
    def __init__(self, text):
        words = [w for w in text.split() if normalize_word(w)]
        self.words = [
            {"word": word, "norm": normalize_word(word),
             "start": round(i * 0.086, 4),
             "end": round((i + 1) * 0.086, 4)}
            for i, word in enumerate(words)
        ]
        self.cursor = 0
        self.duration = len(words) * 0.086 + 1.0

    def _find(self, tokens):
        for index in range(self.cursor, len(self.words) - len(tokens) + 1):
            if all(self.words[index + j]["norm"] == token
                   for j, token in enumerate(tokens)):
                return index
        return None


class PremiumWorkedExampleSmoke(Scene):
    def construct(self):
        stage = PLAN["stages"]["worked_example"]
        sd = {"scene_id": 6, "premium_items": stage["items"]}
        render_premium_board(
            self, "worked_example", sd,
            DeterministicSyntheticWordClock(stage["narration"]), AUDIO,
        )


class PremiumPracticeSmoke(Scene):
    def construct(self):
        stage = PLAN["stages"]["practice"]
        sd = {"scene_id": 8, "premium_items": stage["items"]}
        render_premium_board(
            self, "practice", sd,
            DeterministicSyntheticWordClock(stage["narration"]), AUDIO,
        )
