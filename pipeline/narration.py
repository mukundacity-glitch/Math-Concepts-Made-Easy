"""Content-first narration and visual panels, without a repeated welcome speech."""
from __future__ import annotations

from pipeline.mathtext import latex_to_plain, latex_to_speech, split_sentences
from pipeline.practice import split_practice


def _panel(title: str, narration: list[str], lines: list[str], visual: dict | None = None, **extra) -> dict:
    return {"title": title, "narration": narration, "lines": lines,
            "visual": visual or {"model": "equation_steps", "labels": [latex_to_plain(line) for line in lines[:3]]}, **extra}


def write_narrations(lesson: dict, teaser: str, heading: str, plan: dict, recap: str = "") -> dict:
    board = lesson["board_examples"]
    question, solution = split_practice(board)
    design = plan.get("lesson_design")
    formula = lesson["key_formula"]
    hook = lesson.get("real_world_hook", "")
    hook_first = split_sentences(hook)[0] if hook else lesson["lesson_goal"]
    openers = {
        "mystery": "What makes this work?", "prediction": "Predict the result before we calculate.",
        "real_life_problem": "Start with this situation.", "visual_puzzle": "Look at the model. What changes?",
        "wrong_answer": "Which step would make this answer wrong?", "before_and_after": "Compare the input and the output.",
        "two_choices": "Would these two methods give the same result?", "surprising_shortcut": "Can the structure save us some work?",
        "pattern_spotting": "What pattern can you see?", "student_challenge": "Try a prediction before the explanation.",
    }
    closers = {
        "one_line_recap": lesson["lesson_goal"], "tomorrow_teaser": teaser,
        "confidence_close": "Check your result by reversing or verifying your steps.",
        "practice_prompt": "Create a different problem and test your method.",
        "exam_tip": "Write the reasoning that justifies your answer, not only the result.",
        "teach_it_back": "Explain why the method works in your own words.",
    }
    panels = {
        "opening": [_panel(lesson["topic"], [openers[plan["hook_variant"]], hook_first], [])],
        "hook": [_panel("Start with the situation", split_sentences(hook), [])],
        "concept": [_panel("Build the idea", split_sentences(lesson.get("concept_intuition", "")), [])],
        "definition": [_panel(lesson["subtopic"], [lesson["lesson_goal"], lesson["formula_spoken"]], [formula])],
        "formula": [_panel("Read the rule", [lesson["formula_spoken"], "Connect each symbol to the model."], [formula])],
        "worked_example": [_panel("Work through the example", [latex_to_speech(line) for line in board["worked_example"]], board["worked_example"])],
        "mistakes": [_panel("Find and fix the mistake", split_sentences(lesson["common_mistake"]), [])],
        "practice": [
            _panel("Your turn", [latex_to_speech(line) for line in question], question, pause_after=True),
            _panel("Check your reasoning", [latex_to_speech(line) for line in solution] or ["Compare your reasoning with the model."], solution),
        ],
        "summary": [_panel("Take the idea with you", [lesson["formula_spoken"], closers[plan["outro_variant"]]], [formula])],
    }
    if design:
        panels.update(design.get("scene_panels", {}))
        panels["worked_example"] = [
            _panel(example.get("title", example["id"]), example.get("narration") or [latex_to_speech(example["prompt"]), *[latex_to_speech(line) for line in example["solution_steps"]]],
                   example["solution_steps"], example["visual"], representation=example["representation"])
            for example in design["worked_examples"]
        ]
        practice_set = design.get("practice_set") or [design["student_pause"]]
        panels["practice"] = []
        for index, pause in enumerate(practice_set, 1):
            panels["practice"].extend([
                _panel(f"Practice {index}: your turn", [pause.get("spoken_prompt") or latex_to_speech(pause["prompt"])], [pause["prompt"]], pause.get("visual"), pause_after=True, pause_seconds=pause["pause_seconds"]),
                _panel(f"Practice {index}: check the method", pause.get("solution_narration") or [pause.get("spoken_answer") or latex_to_speech(pause["answer"])], pause.get("solution_steps") or [pause["answer"]], pause.get("visual")),
            ])
    result = {}
    for step in plan["scene_order"]:
        beats = []
        prepared = []
        pauses = []
        for panel in panels[step]:
            text = [" ".join(str(item).split()) for item in panel["narration"] if str(item).strip()]
            first = len(beats)
            line_sentences = []
            lines = panel["lines"]
            read_lines = bool(lines) and not panel.get("pause_after")
            for index, paragraph in enumerate(text):
                beats.extend(split_sentences(paragraph))
                if read_lines and index < len(lines):
                    line_sentences.append(len(beats))
                    beats.append(latex_to_speech(lines[index]))
            if read_lines:
                for line in lines[len(line_sentences):]:
                    line_sentences.append(len(beats))
                    beats.append(latex_to_speech(line))
            else:
                line_sentences = [first for line in lines]
            prepared.append({**panel, "start_sentence": first, "end_sentence": len(beats),
                             "line_sentences": line_sentences, "narration": text})
            if panel.get("pause_after"):
                pauses.append({"after_sentence":len(beats), "seconds":panel.get("pause_seconds", 7)})
        result[step] = {"full": " ".join(beats), "beats": beats, "panels": prepared}
        result[step]["pauses"] = pauses
    return result
