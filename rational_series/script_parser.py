"""Script loading, concept detection and timing for the Rational series.

A "day" is entirely described by one script file — JSON or Markdown — that
lives in ``rational_series/scripts/``.  This module turns that file into a
list of :class:`NarrationBlock` objects, each carrying:

* the narration Ryan speaks,
* the **concept** that decides which animation beat runs,
* the parameters that beat needs (square side label, recap items, …),
* a duration, taken from the real TTS audio when it exists and estimated
  from the speaking rate when it does not.

Concept detection is keyword-driven, so a script writer can simply write
"Let's quickly recap Day 1" or "Draw a square measuring one foot by one
foot" and the right animation fires.  An explicit ``"concept"`` field always
wins over the inferred one.

Nothing here is Day-2 specific.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Speaking-rate model (used only when no audio file has been rendered yet)
# --------------------------------------------------------------------------

WORDS_PER_SECOND = 2.55  # en-GB-Ryan at the series' default prosody
COMMA_PAUSE = 0.22
SENTENCE_PAUSE = 0.42
MIN_BLOCK_SECONDS = 2.5
LEAD_IN = 0.35  # breath before the first word of a block
TAIL_OUT = 0.55  # beat is allowed to settle after the last word


class ScriptError(ValueError):
    """Raised when a script file cannot be used to build a video."""


# --------------------------------------------------------------------------
# Concept vocabulary
# --------------------------------------------------------------------------

#: Ordered ``(pattern, concept)`` rules.  First match wins, so put the
#: specific phrases above the generic ones.  Adding a new teaching visual to
#: the series means adding a rule here plus a beat in ``beats.py`` — never a
#: change to the scene or the renderer.
CONCEPT_RULES: Sequence[Tuple[str, str]] = (
    (r"\brecap\b|\blast time\b|\byesterday\b|\bday \d+ (?:we|you) (?:learn|cover)", "recap"),
    (r"\bdraw (?:a|the) (?:perfect )?square\b|\bsquare measuring\b|\bone (?:foot|metre|meter) by one\b", "draw_square"),
    (r"\bdiagonal\b", "draw_diagonal"),
    (r"\bpythagoras\b|\bright[- ]angled triangle\b|\bhypotenuse\b", "pythagoras"),
    (r"\bnumber line\b|\bzoom in on the line\b|\bbetween the whole numbers\b", "number_line"),
    (r"\bcontradiction\b|\bimpossible\b|\bcannot both\b", "contradiction"),
    (r"\bassume\b|\bsuppose (?:that )?(?:it|we|the)\b|\bstep \d\b|\btherefore\b|\bproof\b", "equation"),
    (r"\bfraction\b|\bp over q\b|\bnumerator\b|\bdenominator\b|\brational number\b", "fraction"),
    (r"\bclassify\b|\bwhich of these\b|\bsort\b|\brational or irrational\b", "classify"),
    (r"\bmistake\b|\bstudents (?:often )?think\b|\bcommon error\b|\bwrong\b", "mistake"),
    (r"\bpractice\b|\btry (?:this|it)\b|\bpause the video\b|\byour turn\b", "practice"),
    (r"\bdefinition\b|\bwe call (?:these|this|it)\b|\bis defined as\b|\bmeans that\b", "definition"),
    (r"\bcompare\b|\bside by side\b|\bdifference between\b", "compare"),
    (r"\btomorrow\b|\bnext (?:video|day|lesson)\b|\bsubscribe\b|\bsee you\b", "outro"),
    (r"\bwelcome\b|\bday \d+\b", "intro"),
)

#: Concepts the engine can render.  ``beats.py`` registers one function per
#: entry; anything unknown falls back to the ``statement`` beat, which still
#: produces a designed visual rather than a blank screen.
KNOWN_CONCEPTS = (
    "intro",
    "recap",
    "statement",
    "definition",
    "draw_square",
    "draw_diagonal",
    "pythagoras",
    "number_line",
    "fraction",
    "equation",
    "contradiction",
    "classify",
    "compare",
    "mistake",
    "practice",
    "outro",
)

_COMPILED_RULES = tuple((re.compile(pattern, re.IGNORECASE), concept) for pattern, concept in CONCEPT_RULES)


def infer_concept(narration: str) -> str:
    """Pick the animation concept implied by a line of narration."""
    for pattern, concept in _COMPILED_RULES:
        if pattern.search(narration):
            return concept
    return "statement"


# --------------------------------------------------------------------------
# Timing
# --------------------------------------------------------------------------


def estimate_duration(narration: str) -> float:
    """Estimate how long the narration takes to speak, in seconds.

    Used for layout/pacing before (or without) TTS.  Once real audio exists
    the measured duration replaces this everywhere.
    """
    words = len(re.findall(r"[\w'’\-]+", narration))
    commas = narration.count(",") + narration.count(";") + narration.count(":")
    sentences = len(re.findall(r"[.!?]+", narration))
    spoken = words / WORDS_PER_SECOND + commas * COMMA_PAUSE + sentences * SENTENCE_PAUSE
    return max(MIN_BLOCK_SECONDS, spoken + LEAD_IN + TAIL_OUT)


def caption_chunks(narration: str, max_words: int = 9) -> List[str]:
    """Split narration into readable caption lines.

    Breaks on punctuation first so captions land on natural phrases, then
    hard-wraps anything still too long for one overlay line.
    """
    if not narration.strip():
        return []
    phrases = [p.strip() for p in re.split(r"(?<=[.!?,;:])\s+", narration.strip()) if p.strip()]
    chunks: List[str] = []
    for phrase in phrases:
        words = phrase.split()
        if len(words) <= max_words:
            # Glue very short fragments onto the previous caption.
            if chunks and len(chunks[-1].split()) + len(words) <= max_words:
                chunks[-1] = f"{chunks[-1]} {phrase}"
            else:
                chunks.append(phrase)
            continue
        for i in range(0, len(words), max_words):
            chunks.append(" ".join(words[i : i + max_words]))
    return chunks


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------


@dataclass
class NarrationBlock:
    """One narration beat: what Ryan says and what the screen does."""

    index: int
    concept: str
    narration: str
    params: Dict[str, Any] = field(default_factory=dict)
    explicit_duration: Optional[float] = None
    hold: float = 0.0  # extra seconds of silence after the narration
    captions: bool = True
    keep_stage: bool = False  # don't clear the previous beat's visuals

    audio_path: Optional[Path] = None
    audio_duration: Optional[float] = None

    @property
    def id(self) -> str:
        return f"b{self.index:02d}_{self.concept}"

    @property
    def spoken_duration(self) -> float:
        """Length of the narration itself (measured if possible)."""
        if self.audio_duration is not None:
            return self.audio_duration
        if self.explicit_duration is not None:
            return self.explicit_duration
        return estimate_duration(self.narration)

    @property
    def duration(self) -> float:
        """Total screen time for the block: narration plus its hold."""
        return self.spoken_duration + self.hold

    @property
    def caption_lines(self) -> List[str]:
        return caption_chunks(self.narration) if self.captions else []

    def param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


@dataclass
class DayScript:
    """A complete day: metadata plus the ordered narration blocks."""

    day: int
    title: str
    subtitle: str = ""
    topic: str = ""
    voice: str = "en-GB-RyanNeural"
    thumbnail: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    blocks: List[NarrationBlock] = field(default_factory=list)
    source_path: Optional[Path] = None

    # ---- derived ---------------------------------------------------------

    @property
    def total_duration(self) -> float:
        return sum(block.duration for block in self.blocks)

    @property
    def slug(self) -> str:
        clean = re.sub(r"[^a-z0-9]+", "_", self.title.lower()).strip("_")
        return f"day{self.day:02d}_{clean}"[:60]

    def timeline(self) -> List[Tuple[float, float, NarrationBlock]]:
        """``(start, end, block)`` for every block, in seconds from t=0."""
        out, cursor = [], 0.0
        for block in self.blocks:
            out.append((cursor, cursor + block.duration, block))
            cursor += block.duration
        return out

    def concepts(self) -> List[str]:
        return [block.concept for block in self.blocks]

    def validate(self) -> None:
        """Fail loudly *before* a 20-minute render starts."""
        problems: List[str] = []
        if self.day < 1:
            problems.append("day number must be >= 1")
        if not self.title.strip():
            problems.append("title is empty")
        if not self.blocks:
            problems.append("script has no narration blocks")
        for block in self.blocks:
            if not block.narration.strip() and block.concept not in ("intro", "outro"):
                problems.append(f"block {block.index} ({block.concept}) has no narration")
            if block.concept not in KNOWN_CONCEPTS:
                problems.append(
                    f"block {block.index} uses unknown concept '{block.concept}' "
                    f"(known: {', '.join(KNOWN_CONCEPTS)})"
                )
        if problems:
            where = self.source_path or "<script>"
            raise ScriptError(f"{where}:\n  - " + "\n  - ".join(problems))


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def _block_from_mapping(index: int, raw: Dict[str, Any]) -> NarrationBlock:
    narration = str(raw.get("narration", raw.get("text", ""))).strip()
    concept = str(raw.get("concept") or infer_concept(narration)).strip().lower()
    known = {
        "concept",
        "narration",
        "text",
        "params",
        "duration",
        "hold",
        "captions",
        "keep_stage",
    }
    # Anything else at the top level of a block is treated as a beat
    # parameter, so scripts stay terse: {"concept": "draw_square", "side_label": "1 ft"}
    params = dict(raw.get("params", {}))
    params.update({k: v for k, v in raw.items() if k not in known})
    return NarrationBlock(
        index=index,
        concept=concept,
        narration=narration,
        params=params,
        explicit_duration=raw.get("duration"),
        hold=float(raw.get("hold", 0.0)),
        captions=bool(raw.get("captions", True)),
        keep_stage=bool(raw.get("keep_stage", False)),
    )


def script_from_dict(data: Dict[str, Any], *, source: Optional[Path] = None) -> DayScript:
    """Build a :class:`DayScript` from an already-parsed mapping."""
    try:
        day = int(data["day"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ScriptError(f"{source or '<script>'}: missing or invalid 'day' field") from exc

    blocks_raw = data.get("blocks") or data.get("script") or []
    if not isinstance(blocks_raw, list):
        raise ScriptError(f"{source or '<script>'}: 'blocks' must be a list")

    script = DayScript(
        day=day,
        title=str(data.get("title", f"Day {day}")).strip(),
        subtitle=str(data.get("subtitle", "")).strip(),
        topic=str(data.get("topic", "")).strip(),
        voice=str(data.get("voice", "en-GB-RyanNeural")),
        thumbnail=dict(data.get("thumbnail", {})),
        meta=dict(data.get("meta", {})),
        blocks=[_block_from_mapping(i, raw) for i, raw in enumerate(blocks_raw)],
        source_path=source,
    )
    script.validate()
    return script


_MD_HEADING = re.compile(r"^##\s+(?P<concept>[\w-]+)\s*(?:—|-|:)?\s*(?P<label>.*)$")
_MD_PARAM = re.compile(r"^-\s*(?P<key>[\w_]+)\s*:\s*(?P<value>.+)$")


def script_from_markdown(text: str, *, source: Optional[Path] = None) -> DayScript:
    """Parse the lightweight Markdown script format.

    ::

        # Day 2 — Irrational Numbers
        - subtitle: Why root 2 breaks the fractions
        - topic: Number Systems

        ## recap — Day 1 callback
        - items: Rational numbers | p over q | q is never zero
        Let's quickly recap Day 1.

        ## draw_square
        - side_label: 1 ft
        Draw a square measuring one foot by one foot.
    """
    header: Dict[str, Any] = {}
    blocks: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    lines_buffer: List[str] = []

    def flush() -> None:
        if current is not None:
            current["narration"] = " ".join(lines_buffer).strip()
            blocks.append(current)
        lines_buffer.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            flush()
            current = None
            title = stripped[2:].strip()
            match = re.match(r"day\s*(\d+)\s*(?:—|-|:)?\s*(.*)", title, re.IGNORECASE)
            if match:
                header["day"] = int(match.group(1))
                header["title"] = match.group(2).strip() or f"Day {match.group(1)}"
            else:
                header["title"] = title
            continue
        heading = _MD_HEADING.match(stripped)
        if heading:
            flush()
            current = {"concept": heading.group("concept").lower()}
            if heading.group("label"):
                current["label"] = heading.group("label").strip()
            continue
        param = _MD_PARAM.match(stripped)
        if param:
            key, value = param.group("key"), param.group("value").strip()
            parsed: Any = value
            if "|" in value:
                parsed = [v.strip() for v in value.split("|") if v.strip()]
            elif re.fullmatch(r"-?\d+(\.\d+)?", value):
                parsed = float(value) if "." in value else int(value)
            elif value.lower() in ("true", "false"):
                parsed = value.lower() == "true"
            (current if current is not None else header)[key] = parsed
            continue
        if stripped:
            lines_buffer.append(stripped)
    flush()

    header["blocks"] = blocks
    return script_from_dict(header, source=source)


def load_script(path: str | Path) -> DayScript:
    """Load a day script from ``.json`` or ``.md``."""
    path = Path(path)
    if not path.exists():
        raise ScriptError(f"script not found: {path}")
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".md", ".markdown", ".txt"):
        return script_from_markdown(raw, source=path)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScriptError(f"{path}: invalid JSON — {exc}") from exc
    return script_from_dict(data, source=path)


DEFAULT_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"


def script_path_for_day(day: int, scripts_dir: str | Path | None = None) -> Path:
    """Find ``dayNN.*`` in the scripts directory (``day2.json``, ``day02.md``…)."""
    directory = Path(scripts_dir or DEFAULT_SCRIPTS_DIR)
    candidates = [
        directory / f"day{day}.json",
        directory / f"day{day:02d}.json",
        directory / f"day{day}_script.json",
        directory / f"day{day:02d}_script.json",
        directory / f"day{day}.md",
        directory / f"day{day:02d}.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise ScriptError(
        f"no script for day {day} in {directory}. Expected one of: " + ", ".join(c.name for c in candidates)
    )


def load_day(day: int, scripts_dir: str | Path | None = None) -> DayScript:
    """Load the script for a day number."""
    return load_script(script_path_for_day(day, scripts_dir))


def available_days(scripts_dir: str | Path | None = None) -> List[int]:
    """Every day number that has a script file, ascending."""
    directory = Path(scripts_dir or DEFAULT_SCRIPTS_DIR)
    days = set()
    for path in directory.glob("day*"):
        match = re.match(r"day0*(\d+)", path.stem, re.IGNORECASE)
        if match and path.suffix.lower() in (".json", ".md", ".markdown", ".txt"):
            days.add(int(match.group(1)))
    return sorted(days)


def attach_audio(script: DayScript, tracks: Dict[str, Tuple[Path, float]]) -> DayScript:
    """Bind rendered narration audio (``block id -> (path, duration)``)."""
    for block in script.blocks:
        track = tracks.get(block.id)
        if track:
            block.audio_path, block.audio_duration = track[0], float(track[1])
    return script


def _srt_stamp(seconds: float) -> str:
    millis = int(round(max(seconds, 0.0) * 1000))
    h, millis = divmod(millis, 3_600_000)
    m, millis = divmod(millis, 60_000)
    s, millis = divmod(millis, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def srt_from_cues(cues: Sequence[Dict[str, Any]]) -> str:
    """Build an SRT from the scene's cue log (real on-screen timings).

    Preferred over :func:`to_srt`: the cue log records where each block
    actually landed in the finished video, including intro and transitions.
    """
    entries: List[str] = []
    counter = 1
    for cue in cues:
        lines = cue.get("captions") or []
        if not lines:
            continue
        start = float(cue["start"]) + LEAD_IN
        speakable = max(float(cue.get("spoken", cue["end"] - cue["start"])) - LEAD_IN, 0.5)
        total_chars = sum(len(line) for line in lines) or 1
        cursor = start
        for line in lines:
            share = speakable * (len(line) / total_chars)
            entries.append(f"{counter}\n{_srt_stamp(cursor)} --> {_srt_stamp(cursor + share)}\n{line}\n")
            cursor += share
            counter += 1
    return "\n".join(entries)


def to_srt(script: DayScript, *, offset: float = 0.0) -> str:
    """Render the whole day's captions as an SRT file (for YouTube)."""

    stamp = _srt_stamp
    entries: List[str] = []
    counter = 1
    for start, _end, block in script.timeline():
        lines = block.caption_lines
        if not lines:
            continue
        # Captions share the spoken portion of the block, weighted by length.
        total_chars = sum(len(line) for line in lines) or 1
        cursor = start + offset + LEAD_IN
        speakable = max(block.spoken_duration - LEAD_IN, 0.5)
        for line in lines:
            share = speakable * (len(line) / total_chars)
            entries.append(f"{counter}\n{stamp(cursor)} --> {stamp(cursor + share)}\n{line}\n")
            cursor += share
            counter += 1
    return "\n".join(entries)
