"""Phase-2 regression tests: educational depth and exact solution verification."""

import copy
import json
from pathlib import Path

import pytest

from pipeline.curriculum import MASTER_CURRICULUM
from pipeline.curriculum_dependencies import (
    lesson_concept_id, prerequisite_report, validate_curriculum_dependencies,
)
from pipeline.lesson_contract import (
    validate_premium_content, validate_premium_lesson, premium_projection, verify_solution,
)
from pipeline.lesson_qa import build_coverage_report

ROOT = Path(__file__).resolve().parents[1]
DEMO_PATH = ROOT / "examples" / "premium_algebra_lesson.json"
ANSWERS_PATH = ROOT / "examples" / "premium_algebra_answers.md"


@pytest.fixture
def demo():
    return json.loads(DEMO_PATH.read_text(encoding="utf-8"))


def test_complete_premium_lesson_verifies_twenty_five_independent_solutions(demo):
    report = validate_premium_lesson(demo)
    assert report["verified"]
    assert report["worked_examples"] == 10
    assert report["practice_questions"] == 15
    assert report["verified_solutions"] == 25
    assert {r["verification_kind"] for r in report["questions"]} == {
        "linear_equation", "evaluate", "equivalent_expression",
    }
    companion = ANSWERS_PATH.read_text(encoding="utf-8")
    for item in (demo["educational_content"]["worked_examples"] +
                 demo["educational_content"]["practice_questions"]):
        assert f"### {item['id']}:" in companion
        assert f"Verified answer:** `{item['answer']}`" in companion


@pytest.mark.parametrize("mutation,expected", [
    (lambda d: d["educational_content"]["worked_examples"].pop(), "10 worked"),
    (lambda d: d["educational_content"]["practice_questions"].pop(), "15 practice"),
    (lambda d: d["educational_content"]["worked_examples"][0].update(answer="99"), "answer"),
    (lambda d: d["educational_content"]["practice_questions"][2]["steps"][0].update(math="x=999"), "step"),
    (lambda d: d["educational_content"]["practice_questions"][0].update(
        id="W01"), "duplicate question ID"),
    (lambda d: d["educational_content"]["practice_questions"][0].update(
        prompt=d["educational_content"]["worked_examples"][0]["prompt"]),
        "duplicate question prompt"),
    (lambda d: d["educational_content"].update(answer_delivery={"mode": "companion"}),
        "resource_id"),
    (lambda d: d["educational_content"]["worked_examples"][0].update(
        check={"kind": "linear_equation", "input": "x=x"}), "linear equations"),
])
def test_invalid_premium_content_is_rejected(demo, mutation, expected):
    mutation(demo)
    with pytest.raises(ValueError, match=expected):
        validate_premium_lesson(demo)


def test_math_parser_rejects_python_objects_and_code_execution(demo):
    item = copy.deepcopy(demo["educational_content"]["worked_examples"][0])
    for attack in [
        "__import__('os').system('echo unsafe')",
        "x.__class__",
        "9**9999",
        "[1,2,3]",
        "lambda x: x",
    ]:
        item["check"]["input"] = attack
        with pytest.raises(ValueError):
            verify_solution(item, "attack")


def test_division_by_zero_and_invalid_infinite_solution_rejected(demo):
    item = copy.deepcopy(demo["educational_content"]["worked_examples"][0])
    item["check"]["input"] = "x+3=1/0"
    with pytest.raises(ValueError, match="division by zero"):
        verify_solution(item, "division")
    item["check"]["input"] = "x=x"
    with pytest.raises(ValueError):
        verify_solution(item, "infinite roots")


def test_prerequisites_are_stable_and_ordered(demo):
    rows = list(MASTER_CURRICULUM) + [demo]
    validate_curriculum_dependencies(rows)
    report = prerequisite_report(rows, 999)
    assert report["concept_id"] == "g9.premium-algebra-contract-demo"
    assert report["prerequisites"][0]["day"] == 1
    assert lesson_concept_id(MASTER_CURRICULUM[0]) == "day-001"


@pytest.mark.parametrize("prerequisites,expected", [
    (["unknown-concept"], "unknown prerequisite"),
    (["g9.premium-algebra-contract-demo"], "earlier day"),
    (["day-001", "day-001"], "duplicate prerequisites"),
])
def test_bad_prerequisite_graph_fails(demo, prerequisites, expected):
    demo["prerequisite_ids"] = prerequisites
    with pytest.raises(ValueError, match=expected):
        validate_curriculum_dependencies(MASTER_CURRICULUM + [demo])


def test_lesson_qa_rejects_tampered_answers_even_when_scenes_cover_narration(demo):
    action = {"action": "write_formula", "target": "formula",
              "narration_sentence_index": 0}
    scene = lambda n, step: {
        "scene_id": n, "step": step, "narration": "Learn the mathematics.",
        "narration_beats": ["Learn the mathematics."],
        "objects": [{"object_id": "formula", "type": "formula"}],
        "actions": [action], "expected_duration": 6.0,
    }
    script = {
        "lesson_id": 999,
        "key_formula": "x+3=7",
        "scenes": [scene(1, "worked_example"), scene(2, "practice")],
        "concept_id": demo["concept_id"],
        "prerequisite_ids": demo["prerequisite_ids"],
        "educational_content": demo["educational_content"],
    }
    passed = build_coverage_report(script, check_history=False)
    assert passed["passed"], passed["errors"]
    script["educational_content"]["worked_examples"][0]["answer"] = "999"
    rejected = build_coverage_report(script, check_history=False)
    assert not rejected["passed"]
    assert any("premium lesson contract failed" in error for error in rejected["errors"])


def test_legacy_lesson_is_not_silently_fabricated_as_twenty_five_questions():
    legacy = next(row for row in MASTER_CURRICULUM if row["day"] == 43)
    assert "educational_content" not in legacy
    assert validate_premium_lesson(legacy) is None


def test_premium_fields_survive_legacy_cell1_to_cell2_handoff(demo):
    projected = premium_projection(demo)
    assert set(projected) == {"concept_id", "prerequisite_ids", "educational_content"}
    assert validate_premium_lesson(projected)["verified_solutions"] == 25
    assert premium_projection(MASTER_CURRICULUM[0]) == {}
    projected["educational_content"]["worked_examples"][0]["answer"] = "999"
    assert demo["educational_content"]["worked_examples"][0]["answer"] != "999"
    # Catch regressions where production config-building silently drops
    # the schema-2 fields that passed the first content QA gate.
    cell1_source = (ROOT / "pipeline" / "cell1_lesson.py").read_text(encoding="utf-8")
    cell2_source = (ROOT / "pipeline" / "cell2_script.py").read_text(encoding="utf-8")
    assert "curriculum_data.update(premium_projection(TODAY))" in cell1_source
    assert '"educational_content": lesson["educational_content"]' in cell2_source


def test_qa_rejects_premium_content_without_concept_identity(demo):
    assert validate_premium_lesson(demo)
    demo.pop("concept_id")
    with pytest.raises(ValueError, match="concept_id"):
        validate_premium_lesson(demo)


def test_nonpolynomial_equation_is_rejected_with_clear_error(demo):
    item = copy.deepcopy(demo["educational_content"]["worked_examples"][0])
    item["check"]["input"] = "x/(x+1)=2"
    with pytest.raises(ValueError, match="polynomial"):
        verify_solution(item, "nonpolynomial")
