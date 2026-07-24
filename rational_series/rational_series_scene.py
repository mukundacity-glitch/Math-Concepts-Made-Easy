"""The one scene class that renders any day of the Rational Numbers series.

``RationalNumberDayScene(day_number, script_path)`` reads a day script, asks
the colour engine for that day's palette, asks the intro engine for that
day's opening, then walks the narration blocks and lets ``beats.py`` draw
each one inside the exact time the narration takes.

The class contains no lesson content and no day-specific logic — Day 2 and
Day 200 run the same code path.

Rendered two ways:

* Python API (what ``generate_day.py`` uses)::

      from manim import tempconfig
      with tempconfig({"quality": "high_quality"}):
          RationalNumberDayScene(2, "rational_series/scripts/day2.json").render()

* Manim CLI (day comes from the environment)::

      RS_DAY=2 manim -qh rational_series/rational_series_scene.py RationalNumberDayScene
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow `manim path/to/rational_series_scene.py` to import the package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from manim import (  # noqa: E402
    AnimationGroup,
    FadeOut,
    ManimColor,
    MovingCameraScene,
    VGroup,
    config,
)

from rational_series.audio import build_narration  # noqa: E402
from rational_series.beats import BeatContext, get_beat  # noqa: E402
from rational_series.color_engine import DayPalette, palette_for_day  # noqa: E402
from rational_series.intro_generator import generate_intro, play_intro  # noqa: E402
from rational_series.script_parser import (  # noqa: E402
    DayScript,
    NarrationBlock,
    attach_audio,
    load_day,
    load_script,
)
from rational_series.visual_library import (  # noqa: E402
    CameraController,
    CaptionTrack,
    HUD,
    HighlightSystem,
    Storyboard,
    Style,
)

#: Seconds of settle time reserved at the end of every block so a beat never
#: finishes on the last syllable.
BEAT_TAIL = 0.3
#: Cross-fade between beats.
TRANSITION = 0.55


class RationalNumberDayScene(MovingCameraScene):
    """Renders one day of the series from its script file."""

    def __init__(
        self,
        day_number: Optional[int] = None,
        script_path: Optional[str] = None,
        *,
        audio: Optional[bool] = None,
        audio_dir: Optional[str] = None,
        cue_path: Optional[str] = None,
        block_limit: Optional[int] = None,
        **kwargs: Any,
    ):
        # --- resolve inputs (constructor first, environment second) -------
        env_day = os.environ.get("RS_DAY")
        env_script = os.environ.get("RS_SCRIPT")
        self.day_number = int(day_number if day_number is not None else (env_day or 1))
        self.script_path = script_path or env_script

        self.script: DayScript = (
            load_script(self.script_path) if self.script_path else load_day(self.day_number)
        )
        # The script file is the source of truth for the day number.
        self.day_number = self.script.day

        self.use_audio = (
            audio
            if audio is not None
            else os.environ.get("RS_AUDIO", "1") not in ("0", "false", "False", "")
        )
        self.audio_dir = Path(audio_dir or os.environ.get("RS_AUDIO_DIR") or (_REPO_ROOT / "output" / "rational_series" / f"day{self.day_number:02d}" / "audio"))
        self.cue_path = cue_path or os.environ.get("RS_CUES")
        limit = block_limit if block_limit is not None else os.environ.get("RS_BLOCK_LIMIT")
        self.block_limit = int(limit) if limit not in (None, "") else None

        self.palette: DayPalette = palette_for_day(self.day_number)
        self.intro_plan = generate_intro(self.day_number)
        self.cue_log: List[Dict[str, Any]] = []
        self.memory: Dict[str, Any] = {}
        self._carry: Optional[VGroup] = None  # visuals held over for a keep_stage block

        # Background must be set before the camera is constructed.
        config.background_color = ManimColor(self.palette.background)
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(self) -> None:
        super().setup()
        self.style = Style(self.palette)
        self.camera_control = CameraController(self)
        self.highlight = HighlightSystem(self.style)
        self.hud = HUD(self.style, self.day_number, topic=self.script.topic)
        self.camera.background_color = ManimColor(self.palette.background)

        blocks = self.script.blocks[: self.block_limit] if self.block_limit else self.script.blocks
        self.blocks: List[NarrationBlock] = blocks

        # Measure the real narration so every beat can be timed to the voice.
        if self.use_audio:
            tracks = build_narration(self.script, self.audio_dir, verbose=True)
            attach_audio(self.script, tracks)

        print(f"🎬 Day {self.day_number}: {self.script.title}")
        print(f"   {self.intro_plan.describe()}")
        print(f"   {len(self.blocks)} blocks · {self.script.total_duration:.1f}s narration")

    # ------------------------------------------------------------------
    # Main timeline
    # ------------------------------------------------------------------

    def construct(self) -> None:
        self.hud.attach(self)
        total = len(self.blocks)

        for index, block in enumerate(self.blocks):
            self.hud.set_progress(index / max(total, 1))
            self._play_block(block, index)

        self.hud.set_progress(1.0)
        self._finish()
        self._write_cues()

    # ------------------------------------------------------------------
    # Blocks
    # ------------------------------------------------------------------

    @property
    def now(self) -> float:
        """Current position on the video timeline, in seconds."""
        return float(getattr(self.renderer, "time", 0.0))

    def _play_block(self, block: NarrationBlock, index: int) -> None:
        start = self.now
        duration = block.duration

        # Narration starts exactly when the beat starts.
        if block.audio_path and Path(block.audio_path).exists():
            self.add_sound(str(block.audio_path))

        captions = CaptionTrack(self.style, block.caption_lines, block.spoken_duration)
        captions.attach(self)

        stage = VGroup()
        budget = max(duration - BEAT_TAIL, 0.6)

        if block.concept == "intro":
            intro_stage = play_intro(
                self,
                self.intro_plan,
                self.style,
                title=self.script.title,
                subtitle=self.script.subtitle,
                budget=budget,
                camera=self.camera_control,
            )
            stage.add(*intro_stage.submobjects)
        else:
            context = BeatContext(
                scene=self,
                style=self.style,
                block=block,
                budget=budget,
                board=Storyboard(self, budget),
                camera=self.camera_control,
                highlight=self.highlight,
                stage=stage,
                memory=self.memory,
            )
            get_beat(block.concept)(context)
            context.board.run()

        # Pad so the block always occupies exactly the narration's length.
        # Anything shorter than a couple of frames is not worth a wait call.
        remaining = duration - (self.now - start)
        if remaining > 2.0 / max(config.frame_rate, 1):
            self.wait(remaining)

        captions.detach(self)
        self.cue_log.append(
            {
                "id": block.id,
                "concept": block.concept,
                "start": round(start, 3),
                "end": round(self.now, 3),
                "spoken": round(block.spoken_duration, 3),
                "narration": block.narration,
                "captions": block.caption_lines,
            }
        )

        next_block = self.blocks[index + 1] if index + 1 < len(self.blocks) else None
        keep = bool(next_block and next_block.keep_stage)
        if not keep:
            self._clear_stage(stage)
            self.memory.clear()
        else:
            # Hand the visuals to the next beat untouched. Carries accumulate:
            # square → diagonal → Pythagoras all end up cleared together.
            carried = self._carry.submobjects if self._carry is not None else []
            self._carry = VGroup(*carried, *stage.submobjects)

    def _clear_stage(self, stage: VGroup) -> None:
        """Dissolve a beat's visuals and bring the camera home."""
        carried = self._carry
        if carried is not None:
            stage = VGroup(*carried.submobjects, *stage.submobjects)
            self._carry = None

        # De-duplicate: a mobject can be tracked by more than one beat.
        seen: List[int] = []
        mobjects = []
        for mob in stage.submobjects:
            if id(mob) not in seen:
                seen.append(id(mob))
                mobjects.append(mob)
        for mob in mobjects:
            mob.clear_updaters()

        animations = [FadeOut(m) for m in mobjects]
        if not self.camera_control.is_home():
            animations.append(self.camera_control.reset())
        if animations:
            self.play(AnimationGroup(*animations, lag_ratio=0.04), run_time=TRANSITION)
        self.remove(*mobjects)

    def _finish(self) -> None:
        """Fade the furniture out so the video ends clean."""
        self.hud.badge.clear_updaters()
        self.hud.progress.clear_updaters()
        leftovers = [m for m in self.mobjects if m is not None]
        if leftovers:
            self.play(AnimationGroup(*[FadeOut(m) for m in leftovers], lag_ratio=0.05), run_time=0.9)
        self.wait(0.4)

    def _write_cues(self) -> None:
        """Emit real on-screen timings so captions can be exported exactly."""
        if not self.cue_path:
            return
        path = Path(self.cue_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "day": self.day_number,
                    "title": self.script.title,
                    "duration": round(self.now, 3),
                    "palette": self.palette.as_dict(),
                    "intro": self.intro_plan.as_dict(),
                    "blocks": self.cue_log,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


# Convenience alias so `manim ... Day2Scene` also works for the demo.
class Day2Scene(RationalNumberDayScene):
    """Ready-to-run demo: ``manim -qh rational_series/rational_series_scene.py Day2Scene``."""

    def __init__(self, **kwargs: Any):
        super().__init__(day_number=2, **kwargs)


__all__ = ["RationalNumberDayScene", "Day2Scene"]
