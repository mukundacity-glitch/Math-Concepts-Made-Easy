"""Insert measured silent thinking time without shifting answer narration early."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
from typing import Awaitable, Callable

from pipeline.mathtext import normalize_word


async def synthesize_with_pauses(scene: dict, audio_path: Path, words_path: Path,
                                 synthesize: Callable[[str, Path, Path], Awaitable[bool]],
                                 measure: Callable[[Path], Awaitable[float]]) -> bool:
    beats = scene["narration_beats"]
    pauses = scene.get("pauses", [])
    boundaries = {int(pause["after_sentence"]): float(pause["seconds"]) for pause in pauses}
    offsets = [0, *sorted(boundaries), len(beats)]
    if len(set(offsets)) != len(offsets) or any(index <= 0 or index >= len(beats) for index in boundaries):
        raise ValueError("thinking pauses must fall strictly between narration statements")
    paths = []
    words = []
    cursor = 0.0
    pause_timing = []
    for index, (start, end) in enumerate(zip(offsets, offsets[1:])):
        text = " ".join(beats[start:end])
        part = audio_path.with_name(f"{audio_path.stem}_part{index}.mp3")
        word_part = part.with_suffix(".words.json")
        if not await synthesize(text, part, word_part):
            return False
        duration = await measure(part)
        if duration <= 0:
            return False
        rows = json.loads(word_part.read_text(encoding="utf-8"))
        if not rows:
            scene["word_timing_estimated"] = True
            tokens = text.split()
            rows = [{"word":word,"norm":normalize_word(word),"start":duration*position/len(tokens),
                     "end":duration*(position+1)/len(tokens)} for position, word in enumerate(tokens)]
        words.extend({**row,"start":row["start"]+cursor,"end":row["end"]+cursor} for row in rows)
        paths.append(part)
        cursor += duration
        if end in boundaries:
            seconds = boundaries[end]
            if not 0 < seconds <= 60:
                raise ValueError("thinking pauses must be between 0 and 60 seconds")
            silence = audio_path.with_name(f"{audio_path.stem}_silence{index}.mp3")
            await asyncio.to_thread(subprocess.run,["ffmpeg","-y","-v","error","-f","lavfi","-i",
                "anullsrc=r=24000:cl=mono","-t",str(seconds),"-codec:a","libmp3lame",str(silence)],check=True)
            measured = await measure(silence)
            pause_timing.append({"start":cursor,"seconds":measured})
            cursor += measured
            paths.append(silence)
    manifest = audio_path.with_suffix(".concat.txt")
    manifest.write_text("\n".join("file '"+str(path.resolve()).replace("'", "'\\''")+"'" for path in paths),encoding="utf-8")
    await asyncio.to_thread(subprocess.run,["ffmpeg","-y","-v","error","-f","concat","-safe","0",
        "-i",str(manifest),"-codec:a","libmp3lame",str(audio_path)],check=True)
    words_path.write_text(json.dumps(words),encoding="utf-8")
    scene["pause_timing"] = pause_timing
    scene["timing_source"] = "segmented_speech_with_measured_pauses"
    return True
