"""Standalone portrait teaching boards. Never opens a landscape video.

Each page has its own complete narration, original TTS word boundaries and a
new Manim animation rendered at the portrait teaching area's native resolution.
Remotion adds the permanent logo and a separate caption lane at 1080 x 1920.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

from pipeline.mathtext import latex_to_speech, split_sentences
from pipeline.remotion_bridge import _probe, _sha256
from pipeline.remotion_captions import load_scene_word_captions

ROOT = Path(__file__).resolve().parents[1]


def equation_speech(value: str) -> str:
    # Function inverses must not be narrated as reciprocal powers.
    value = re.sub(r"([A-Za-z])\^\{-1\}", r"\\text{\1 inverse}", value)
    value = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}",
                   lambda m: r"\text{the quantity }" + m[1] + r"\text{ divided by }" + m[2], value)
    spoken = latex_to_speech(value)
    spoken = re.sub(r"\b([A-Za-z]|\d+)\s*-\s*(?=\d|\b[A-Za-z]\b)", r"\1 minus ", spoken)
    return spoken


def short_plans(lesson: dict) -> dict:
    """Use complete curriculum statements/equations; no invented mathematics."""
    boards = lesson.get("board_examples", {})
    example = boards.get("worked_example", [])
    if not example:
        raise ValueError("Native Shorts require a complete worked example")
    formula = boards.get("formula") or lesson["key_formula"]
    hook = split_sentences(lesson["concept_intuition"])
    mistake = split_sentences(lesson["common_mistake"])
    def prose(text):
        return {"kind": "prose", "display": text, "speech": text}
    def equation(text):
        return {"kind": "math", "display": text, "speech": equation_speech(text)}
    return {
        "HOOK": {"title": lesson["topic"], "label": "Understand the idea",
                 "pages": [*(prose(t) for t in hook), equation(formula)]},
        "FORMULA": {"title": lesson["topic"], "label": "Work through an example",
                    "pages": [equation(t) for t in example]},
        "MISTAKE": {"title": lesson["topic"], "label": "Avoid a common mistake",
                    "pages": [*(prose(t) for t in mistake),
                              *(equation(t) for t in boards.get("practice", []))]},
    }


# A separate portrait camera and separate objects, not a transformed landscape
# scene. Bounds and minimum glyph sizes are verified against actual mobjects.
BOARD_SOURCE = r'''
import json, os, sys, re
sys.path.insert(0, __ROOT__)
from pathlib import Path
from manim import *
from pipeline.semantic_math import semantic_text, MATH_PALETTE
config.frame_width = 8
config.frame_height = 64 / 7
config.background_color = "#0B1F38"
PORTRAIT_TEX = TexTemplate()
PORTRAIT_TEX.add_to_preamble(r"\usepackage{xcolor}")

def math_rows(value):
    # Break only at top-level equalities: never split a fraction, exponent,
    # bracketed expression, or a LaTeX command. Keep every symbol in order.
    result, current, depth = [], "", 0
    for char in value:
        if char in "{([": depth += 1
        if char in "})]": depth -= 1
        if char == "=" and depth == 0 and current.strip():
            result.append(current.strip())
            current = "="
        else:
            current += char
    if current.strip(): result.append(current.strip())
    return result

class PortraitBoard(Scene):
    def construct(self):
        page = json.loads(Path(os.environ["MCME_SHORT_PAGE"]).read_text())
        rows = []
        if page["kind"] == "math":
            def colored(value):
                # Leave TeX commands and prose intact; color ordinary math atoms
                # inside intact fractions/groups with TeX itself (no substring
                # isolation that could corrupt a fraction's syntax).
                pattern = r"\^\{[^{}]*\}|\\text\{[^{}]*\}|\\[A-Za-z]+|[A-Za-z]|[0-9]+|[=<>+\-]"
                def atom(match):
                    token = match.group()
                    if token.startswith('^{'):
                        return r'^{\textcolor[HTML]{' + MATH_PALETTE['exponent'][1:] + '}{' + token[2:-1] + '}}'
                    if token.startswith('\\'): return token
                    role = ('number' if token.isdigit() else 'variable' if token.isalpha()
                            else 'relation' if token in '=<> ' else 'operator')
                    return r'\textcolor[HTML]{' + MATH_PALETTE[role][1:] + '}{' + token + '}'
                return re.sub(pattern, atom, value)
            whole = SingleStringMathTex(colored(page["display"]), font_size=90, tex_template=PORTRAIT_TEX)
            lines = [page["display"]] if whole.width <= 7 else math_rows(page["display"])
            for line in lines:
                obj = SingleStringMathTex(colored(line), font_size=90, tex_template=PORTRAIT_TEX)
                scale = min(1, 7.0 / max(obj.width, .001))
                if scale < .74:
                    raise ValueError("Equation needs a hand-authored portrait break; refusing tiny math")
                obj.scale(scale)
                rows.append(obj)
        else:
            line = ""
            for word in page["display"].split():
                test = semantic_text((line + " " + word).strip(), size=38)
                if test.width > 7.0 and line:
                    rows.append(semantic_text(line, size=38))
                    line = word
                else:
                    line = (line + " " + word).strip()
            if line: rows.append(semantic_text(line, size=38))
        group = VGroup(*rows).arrange(DOWN, buff=.28).move_to(ORIGIN)
        if group.width > 7.05 or group.height > 8.0:
            raise ValueError("Portrait teaching board overflow: refusing clipped content")
        # Simultaneous brief reveal, followed by a full uncut explanation.
        self.play(LaggedStart(*(FadeIn(row, shift=UP*.08) for row in rows),
                              lag_ratio=.08), run_time=.5)
        self.wait(page["durationInFrames"] / 30 - .5)
'''


async def narrate(text: str, audio: Path, words: Path, voice: str) -> None:
    import edge_tts
    error = None
    for attempt in range(3):
        try:
            events = []
            stream = edge_tts.Communicate(text, voice, rate="-5%", boundary="WordBoundary")
            with audio.open("wb") as fp:
                async for part in stream.stream():
                    if part["type"] == "audio":
                        fp.write(part["data"])
                    elif part["type"] == "WordBoundary":
                        start = part["offset"] / 10_000_000
                        events.append({"word": part["text"], "start": start,
                                       "end": start + part["duration"] / 10_000_000})
            if not events:
                raise ValueError("No real word boundaries from Shorts narration")
            words.write_text(json.dumps(events), encoding="utf8")
            return
        except Exception as exc:
            error = exc
            if attempt < 2:
                await asyncio.sleep(2)
    raise RuntimeError("Native Shorts narration failed") from error


def build(lesson: dict, final_dir: Path, work: Path, voice: str) -> list[Path]:
    from pipeline.hybrid_assembly import render
    import os
    work.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    source = work / "portrait_board.py"
    source.write_text(BOARD_SOURCE.replace("__ROOT__", repr(str(ROOT))), encoding="utf8")
    outputs = []
    receipts = {}
    for key, plan in short_plans(lesson).items():
        public = ROOT / "remotion/public/native-shorts" / f"day-{lesson['day']:03d}-{key.lower()}"
        public.mkdir(parents=True, exist_ok=True)
        pages = []
        for index, page in enumerate(plan["pages"]):
            audio = public / f"page-{index}.mp3"
            words = work / f"{key}-{index}.words.json"
            asyncio.run(narrate(page["speech"], audio, words, voice))
            seconds, _ = _probe(audio, "audio")
            frames = math.ceil((seconds + .4) * 30)
            page = {**page, "durationInFrames": frames}
            config = work / f"{key}-{index}.json"
            config.write_text(json.dumps(page), encoding="utf8")
            media = work / f"manim-{key}-{index}"
            subprocess.run([sys.executable, "-m", "manim", "--resolution", "840,960",
                "--fps", "30", "--disable_caching", "--progress_bar", "none",
                "--media_dir", str(media), str(source), "PortraitBoard"],
                env={**os.environ, "MCME_SHORT_PAGE": str(config)}, check=True)
            candidates = list((media / "videos").rglob("PortraitBoard.mp4"))
            if len(candidates) != 1:
                raise ValueError("Expected one native portrait board")
            video = public / f"page-{index}.mp4"
            shutil.copyfile(candidates[0], video)
            duration, stream = _probe(video, "video")
            if (stream["width"], stream["height"]) != (840, 960) or duration + .04 < frames / 30:
                raise ValueError("Native portrait media dimensions/timing invalid")
            relative = public.relative_to(ROOT / "remotion/public").as_posix()
            captions = load_scene_word_captions(words, clip_seconds=frames / 30, audio_seconds=seconds)
            pages.append({"durationInFrames": frames, "videoSrc": f"{relative}/{video.name}",
                          "audioSrc": f"{relative}/{audio.name}", "captions": captions,
                          "videoSha256": _sha256(video), "audioSha256": _sha256(audio)})
        total = sum(p["durationInFrames"] for p in pages)
        if not 30 <= total <= 5400:
            raise ValueError(f"{key} needs editorial review: complete Short exceeds 180 seconds")
        props = work / f"{key}.json"
        props.write_text(json.dumps({"title": plan["title"], "label": plan["label"], "pages": pages}), encoding="utf8")
        from pipeline.paths import safe_filename
        output = final_dir / f"Day_{lesson['day']:03d}_{safe_filename(lesson['seo_title'])}_SHORT_{key}.mp4"
        render("NativeShort", props, output)
        from pipeline.narration_integrity import verify_narration
        offset, segments = 0., []
        for page in pages:
            segments.append((ROOT / "remotion/public" / page["audioSrc"], offset))
            offset += page["durationInFrames"] / 30
        speech_checks = verify_narration(output, segments)
        probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams",
            "-of", "json", str(output)], text=True))
        picture = next(s for s in probe["streams"] if s["codec_type"] == "video")
        if ((picture["width"], picture["height"]) != (1080, 1920) or
            picture["avg_frame_rate"] != "30/1" or int(picture["nb_frames"]) != total or
            not any(s["codec_type"] == "audio" for s in probe["streams"])):
            raise ValueError("Completed native Short failed final stream verification")
        receipts[key] = {"sha256": _sha256(output), "frames": total,
                         "nativeBoardSize": [840, 960], "completePages": len(pages),
                         "speechChecks": speech_checks}
        outputs.append(output)
    receipt = final_dir / f"Day_{lesson['day']:03d}_native-shorts.json"
    receipt.write_text(json.dumps({"format": "native-portrait-v1", "day": lesson["day"],
                                  "shorts": receipts}, indent=2) + "\n", encoding="utf8")
    return outputs


def main():
    from pipeline.paths import BASE_DIR, load_cell1_config
    config = load_cell1_config()
    lesson = config.CURRICULUM[0]
    build({**lesson, "day": lesson["id"], "topic": lesson["title"]}, config.FINAL_DIR,
          BASE_DIR / "native-shorts", config.TTS_CONFIG["voice"])


if __name__ == "__main__":
    main()
