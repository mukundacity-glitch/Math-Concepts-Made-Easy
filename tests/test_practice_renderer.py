from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from pipeline.curriculum import get_lesson
from pipeline.mathtext import latex_to_plain

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def practice_namespace():
    tree = ast.parse((ROOT / "pipeline/cell4_animation.py").read_text(encoding="utf-8"))
    template = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "MANIM_SCENE_CODE"
                for target in node.targets)
    )
    embedded = ast.parse(template)
    selected = [
        node for node in embedded.body
        if (isinstance(node, ast.FunctionDef) and node.name == "practice_question_count")
        or (isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "_VERDICT_RE"
                    for target in node.targets))
    ]
    namespace = {"re": re}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<practice>", "exec"), namespace)
    namespace["scene"] = next(
        node for node in embedded.body
        if isinstance(node, ast.ClassDef) and node.name == "Scene08_Practice"
    )
    return namespace


def test_day42_retains_solution(practice_namespace):
    lines = [latex_to_plain(line)
             for line in get_lesson(42)["board_examples"]["practice"]]
    assert len(lines) == 2
    assert practice_namespace["practice_question_count"](lines) == 1


@pytest.mark.parametrize(("lines", "expected"), [
    ([], 0),
    (["Evaluate f(2)"], 1),
    (["What is the answer?", "8"], 1),
    (["Is it defined?", "No"], 1),
    (["Which are prime?", "2, 3, 4", "2 and 3"], 2),
    (["What are f and g?", "f(x)=x+1", "g(x)=2x", "f(g(x))=2x+1"], 2),
])
def test_practice_question_split(practice_namespace, lines, expected):
    assert practice_namespace["practice_question_count"](lines) == expected


def test_empty_solution_skips_group_layout(practice_namespace):
    construct = practice_namespace["scene"].body[0]
    start = next(index for index, node in enumerate(construct.body)
                 if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "rows"
                         for target in node.targets))
    stop = next(index for index in range(start + 1, len(construct.body))
                if isinstance(construct.body[index], ast.Expr))
    layout = ast.Module(body=construct.body[start:stop], type_ignores=[])
    namespace = {
        "sol_lines": [],
        "build_board_rows": lambda *args, **kwargs: [],
    }
    # No Manim objects exist: touching VGroup or card geometry must fail this test.
    exec(compile(layout, "<empty-solution>", "exec"), namespace)
    assert namespace["rows"] == []
