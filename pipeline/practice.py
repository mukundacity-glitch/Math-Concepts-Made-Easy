"""One question/solution boundary for narration and both renderers."""

from __future__ import annotations

from typing import Any


def split_practice(board: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Prefer explicit data; preserve a solution in legacy multi-line boards."""
    if "practice_question" in board or "practice_solution" in board:
        question = board.get("practice_question")
        solution = board.get("practice_solution")
        for name, lines in (("practice_question", question), ("practice_solution", solution)):
            if not isinstance(lines, list) or not lines or any(
                not isinstance(line, str) or not line.strip() for line in lines
            ):
                raise ValueError(f"board_examples.{name} requires nonempty text lines")
        return list(question), list(solution)
    lines = board.get("practice", [])
    if not isinstance(lines, list) or any(
        not isinstance(line, str) or not line.strip() for line in lines
    ):
        raise ValueError("board_examples.practice must contain nonempty text lines")
    if not lines:
        raise ValueError("board_examples.practice is empty")
    # Legacy single-line boards sometimes contain an entire solved verification.
    # Keep it visible as a question without constructing an empty solution group.
    boundary = next((index + 1 for index, line in enumerate(lines[:-1])
                     if line.rstrip().endswith("?")), 1)
    return list(lines[:boundary]), list(lines[boundary:])
