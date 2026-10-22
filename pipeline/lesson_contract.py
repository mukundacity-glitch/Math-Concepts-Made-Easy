"""Opt-in, mathematically checked education contract for premium lessons.

Legacy curriculum entries are deliberately unchanged. Schema 2 requires ten
distinct worked solutions and fifteen distinct answered practice problems.
Math is parsed through a restricted expression AST (no Python eval/sympify on
arbitrary strings). The checks verify every recorded step, not just a key.
"""

from __future__ import annotations

import ast
import re

from sympy import Add, Mul, Poly, Rational, Symbol, count_ops, simplify, solve
from sympy.polys.polyerrors import PolynomialError

SCHEMA = "2.0"
MIN_WORKED_EXAMPLES = 10
MIN_PRACTICE_QUESTIONS = 15
ALLOWED_FORMATS = {"algebra", "visual", "word_problem", "graphical", "exam"}
ALLOWED_DIFFICULTIES = {"foundation", "intermediate", "advanced"}
_X = Symbol("x")
_OPERATORS = {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow}


def _required_text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be nonempty text")
    if len(value) > 2000:
        raise ValueError(f"{path} exceeds the text size limit")
    return value.strip()


def _math_expr(value: object):
    """Compile a bounded arithmetic/algebraic expression to exact SymPy."""
    text = _required_text(value, "mathematical expression")
    if len(text) > 120:
        raise ValueError("mathematical expression exceeds 120 characters")
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError as exc:
        raise ValueError("malformed mathematical expression") from exc

    def walk(n, depth=0):
        if depth > 22:
            raise ValueError("mathematical expression nesting too deep")
        if isinstance(n, ast.Constant):
            if isinstance(n.value, bool) or not isinstance(n.value, (int, float)):
                raise ValueError("only finite numeric literals are allowed")
            if abs(n.value) > 1000000:
                raise ValueError("number exceeds mathematical input bound")
            return Rational(str(n.value))
        if isinstance(n, ast.Name):
            if n.id != "x":
                raise ValueError("only the explicitly supported variable x is allowed")
            return _X
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            expr = walk(n.operand, depth + 1)
            return expr if isinstance(n.op, ast.UAdd) else -expr
        if isinstance(n, ast.BinOp) and type(n.op) in _OPERATORS:
            left, right = walk(n.left, depth + 1), walk(n.right, depth + 1)
            if isinstance(n.op, ast.Add):
                return Add(left, right)
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return Mul(left, right)
            if isinstance(n.op, ast.Div):
                if right == 0:
                    raise ValueError("division by zero")
                return left / right
            if not right.is_integer or not right.is_number or abs(int(right)) > 8:
                raise ValueError("exponent must be an integer from -8 through 8")
            return left ** int(right)
        raise ValueError("unsupported mathematical expression syntax")

    result = walk(node)
    if count_ops(result) > 100:
        raise ValueError("mathematical expression is too complex")
    if result.is_finite is False:
        raise ValueError("mathematical expression is not finite")
    return result


def _equation(value: object):
    value = _required_text(value, "equation")
    sides = value.split("=")
    if len(sides) != 2:
        raise ValueError("equation must contain exactly one '='")
    return _math_expr(sides[0]), _math_expr(sides[1])


def _linear_root(value: object):
    left, right = _equation(value)
    try:
        polynomial = Poly(left - right, _X)
    except PolynomialError as exc:
        raise ValueError("only polynomial linear equations are supported") from exc
    if polynomial.degree() != 1:
        raise ValueError("only unique-solution linear equations are supported")
    roots = solve(left - right, _X)
    if len(roots) != 1 or roots[0].is_finite is not True:
        raise ValueError("linear equation must have exactly one finite root")
    return roots[0]


def _equal(a, b) -> bool:
    return simplify(a - b) == 0


def verify_solution(item: dict, path: str) -> dict:
    """Verify an independently computed answer and every intermediate state."""
    if not isinstance(item, dict):
        raise ValueError(f"{path} must be an object")
    _required_text(item.get("id"), f"{path}.id")
    _required_text(item.get("prompt"), f"{path}.prompt")
    if item.get("difficulty") not in ALLOWED_DIFFICULTIES:
        raise ValueError(f"{path}.difficulty must be a supported tier")
    if item.get("format") not in ALLOWED_FORMATS:
        raise ValueError(f"{path}.format must be a supported presentation format")
    steps = item.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        raise ValueError(f"{path}.steps needs at least two explained mathematical states")
    check = item.get("check")
    if not isinstance(check, dict):
        raise ValueError(f"{path}.check must describe independent mathematical verification")
    kind = check.get("kind")
    answer = _math_expr(item.get("answer"))
    original = _required_text(check.get("input"), f"{path}.check.input")

    if kind == "linear_equation":
        expected = _linear_root(original)
        if not _equal(answer, expected):
            raise ValueError(f"{path}: answer disagrees with computed equation solution")
        check_step = lambda expression: _equal(_linear_root(expression), expected)
    elif kind == "equivalent_expression":
        expected = _math_expr(original)
        if not _equal(answer, expected):
            raise ValueError(f"{path}: answer is not symbolically equivalent")
        check_step = lambda expression: _equal(_math_expr(expression), expected)
    elif kind == "evaluate":
        substitutions = check.get("substitutions", {})
        if not isinstance(substitutions, dict) or set(substitutions) != {"x"}:
            raise ValueError(f"{path}: evaluation requires exactly one x substitution")
        xv = _math_expr(substitutions["x"])
        if xv.free_symbols:
            raise ValueError(f"{path}: substitution must be numeric")
        expected = simplify(_math_expr(original).subs(_X, xv))
        if expected.free_symbols or not _equal(answer, expected):
            raise ValueError(f"{path}: answer disagrees with computed evaluation")
        check_step = lambda expression: _equal(_math_expr(expression).subs(_X, xv), expected)
    else:
        raise ValueError(f"{path}: unsupported verification kind {kind!r}")

    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise ValueError(f"{path}.steps[{index}] must be an object")
        _required_text(step.get("explanation"), f"{path}.steps[{index}].explanation")
        state = _required_text(step.get("math"), f"{path}.steps[{index}].math")
        try:
            valid = check_step(state)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{path}.steps[{index}] invalid mathematical state: {exc}") from exc
        if not valid:
            raise ValueError(f"{path}.steps[{index}] changes the mathematical result")

    if kind != "linear_equation" and answer.free_symbols and kind == "evaluate":
        raise ValueError(f"{path}: evaluated answer must be numeric")
    return {
        "id": item["id"],
        "verified": True,
        "verification_kind": kind,
        "step_count": len(steps),
    }


def validate_premium_content(content: dict) -> dict:
    """Require complete, nonduplicate teaching and independent math checks."""
    if not isinstance(content, dict) or content.get("schema_version") != SCHEMA:
        raise ValueError(f"educational_content.schema_version must be {SCHEMA!r}")
    objectives = content.get("learning_objectives")
    if not isinstance(objectives, list) or len(objectives) < 2:
        raise ValueError("at least two learning objectives are required")
    for i, objective in enumerate(objectives, 1):
        _required_text(objective, f"learning_objectives[{i}]")

    delivery = content.get("answer_delivery")
    if not isinstance(delivery, dict) or delivery.get("mode") not in {
            "companion", "in_video", "next_lesson"}:
        raise ValueError("answer_delivery.mode must be companion, in_video or next_lesson")
    _required_text(delivery.get("resource_id"), "answer_delivery.resource_id")

    worked, practice = content.get("worked_examples"), content.get("practice_questions")
    if not isinstance(worked, list) or len(worked) < MIN_WORKED_EXAMPLES:
        raise ValueError(f"requires at least {MIN_WORKED_EXAMPLES} worked examples")
    if not isinstance(practice, list) or len(practice) < MIN_PRACTICE_QUESTIONS:
        raise ValueError(f"requires at least {MIN_PRACTICE_QUESTIONS} practice questions")

    seen_ids, seen_prompts = set(), set()
    reports = []
    for section, items in (("worked_examples", worked), ("practice_questions", practice)):
        for index, item in enumerate(items, 1):
            path = f"{section}[{index}]"
            row = verify_solution(item, path)
            identifier = item["id"].strip().lower()
            prompt = re.sub(r"\s+", " ", item["prompt"]).strip().casefold()
            if identifier in seen_ids:
                raise ValueError(f"duplicate question ID: {identifier}")
            if prompt in seen_prompts:
                raise ValueError(f"duplicate question prompt: {prompt}")
            seen_ids.add(identifier)
            seen_prompts.add(prompt)
            reports.append(row)

    worked_difficulties = {item["difficulty"] for item in worked}
    worked_formats = {item["format"] for item in worked}
    if worked_difficulties != ALLOWED_DIFFICULTIES:
        raise ValueError("worked examples must cover foundation/intermediate/advanced")
    if len(worked_formats) < 3:
        raise ValueError("worked examples must include at least three presentation formats")
    if {item["difficulty"] for item in practice} != ALLOWED_DIFFICULTIES:
        raise ValueError("practice questions must cover foundation/intermediate/advanced")

    return {
        "schema_version": SCHEMA,
        "verified": True,
        "worked_examples": len(worked),
        "practice_questions": len(practice),
        "verified_solutions": len(reports),
        "answer_delivery": delivery["mode"],
        "questions": reports,
    }


def validate_premium_lesson(lesson: dict) -> dict | None:
    """Legacy material remains readable; schema-2 material fails closed."""
    if "educational_content" not in lesson:
        return None
    _required_text(lesson.get("concept_id"), "concept_id")
    deps = lesson.get("prerequisite_ids")
    if not isinstance(deps, list) or any(not isinstance(x, str) or not x.strip() for x in deps):
        raise ValueError("prerequisite_ids must be a list of concept IDs")
    if len(deps) != len(set(deps)):
        raise ValueError("duplicate prerequisite IDs")
    return validate_premium_content(lesson["educational_content"])


def premium_projection(lesson: dict) -> dict:
    """Preserve independently validated premium lesson fields for downstream cells.

    This is deliberately a separate pure function: the production Cell-1
    config adapter can opt in without silently dropping all 25 questions.
    """
    if "educational_content" not in lesson:
        return {}
    validate_premium_lesson(lesson)
    from copy import deepcopy

    keys = ("concept_id", "prerequisite_ids", "educational_content")
    return {key: deepcopy(lesson[key]) for key in keys}
