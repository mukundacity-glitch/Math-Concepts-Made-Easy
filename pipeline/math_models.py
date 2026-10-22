"""Deterministic, validated mathematical geometry for opt-in teaching scenes.

A mathematical model is computed from data, never inferred from a lesson's title
or from loosely related narration. Legacy lessons with no math_model are unchanged.
All fields returned here are JSON-compatible so Manim/Remotion can share them.
"""

from __future__ import annotations

import math

from sympy import Rational, sqrt


def _rational(value: object, name: str) -> Rational:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{name} must be a finite real number")
    try:
        number = Rational(str(value))
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if number.is_finite is not True or not math.isfinite(float(number)):
        raise ValueError(f"{name} must be a finite real number")
    return number


def _point(x: object, y: object) -> dict[str, float]:
    return {"x": float(x), "y": float(y)}


def build_computed_model(spec: dict) -> dict:
    """Build mathematical objects from explicit lesson data; fail closed.

    v1 supports quadratic_function only. Other topics need their own actual
    mathematical renderer before they can opt into this contract.
    """
    if not isinstance(spec, dict):
        raise ValueError("math_model must be an object")
    if spec.get("kind") != "quadratic_function":
        raise ValueError(f"unsupported math_model kind: {spec.get('kind')!r}")

    coefficients = spec.get("coefficients")
    if not isinstance(coefficients, dict):
        raise ValueError("quadratic_function requires coefficients a, b and c")
    if any(name not in coefficients for name in ("a", "b", "c")):
        raise ValueError("quadratic_function requires coefficients a, b and c")
    a, b, c = (_rational(coefficients[name], name) for name in ("a", "b", "c"))
    if a == 0:
        raise ValueError("quadratic_function requires a nonzero leading coefficient")

    domain = spec.get("domain", [-5, 5])
    if not isinstance(domain, (list, tuple)) or len(domain) != 2:
        raise ValueError("quadratic_function domain must be [min, max]")
    xmin, xmax = (_rational(domain[0], "domain minimum"),
                  _rational(domain[1], "domain maximum"))
    if not xmin < xmax or float(xmax - xmin) > 1000:
        raise ValueError("quadratic_function domain must increase and span <= 1000")

    samples = spec.get("samples", 65)
    if isinstance(samples, bool) or not isinstance(samples, int) or not 9 <= samples <= 401:
        raise ValueError("quadratic_function samples must be an integer from 9 to 401")

    def f(x):
        return a * x * x + b * x + c

    xvertex = -b / (2 * a)
    yvertex = f(xvertex)
    discr = b * b - 4 * a * c
    roots = []
    if discr >= 0:
        exact_roots = [(-b - sqrt(discr)) / (2 * a),
                       (-b + sqrt(discr)) / (2 * a)]
        roots = sorted({_to_real(root) for root in exact_roots})
        if not all(math.isclose(float(f(Rational(str(root)))), 0.0, abs_tol=1e-7,
                                    rel_tol=1e-7) for root in roots):
            raise ValueError("computed root failed numerical verification")

    xvalues = [xmin + (xmax - xmin) * i / (samples - 1) for i in range(samples)]
    curve = [_point(x, f(x)) for x in xvalues]
    extrema = [f(xmin), f(xmax)]
    if xmin <= xvertex <= xmax:
        extrema.append(yvertex)
    low, high = map(float, (min(extrema), max(extrema)))
    if not all(math.isfinite(p["y"]) for p in curve):
        raise ValueError("quadratic curve exceeded finite numeric range")
    if not all(math.isfinite(v) for v in (low, high)):
        raise ValueError("quadratic extrema exceeded finite numeric range")

    return {
        "kind": "quadratic_function",
        "equation": _format_quadratic(a, b, c),
        "coefficients": {"a": float(a), "b": float(b), "c": float(c)},
        "exact_coefficients": {"a": str(a), "b": str(b), "c": str(c)},
        "domain": [float(xmin), float(xmax)],
        "curve": curve,
        "vertex": _point(xvertex, yvertex),
        "axis_of_symmetry": float(xvertex),
        "x_intercepts": [_point(root, 0.0) for root in roots],
        "y_intercept": _point(0, c),
        "discriminant": float(discr),
        "y_bounds": [low, high],
    }


def _format_quadratic(a: Rational, b: Rational, c: Rational) -> str:
    """Readable exact notation: never display a negative as '+ (-3)x'."""
    terms = []
    for coefficient, symbol in ((a, "x²"), (b, "x"), (c, "")):
        if coefficient == 0:
            continue
        magnitude = abs(coefficient)
        fragment = (symbol if magnitude == 1 and symbol
                    else f"{magnitude}{symbol}")
        if not terms:
            terms.append(("-" if coefficient < 0 else "") + fragment)
        else:
            terms.append((" - " if coefficient < 0 else " + ") + fragment)
    return "y = " + "".join(terms)


def _to_real(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("quadratic roots must be finite")
    return result


def validate_computed_model(model: dict) -> None:
    """Reject forged or stale coordinates before any scene can be rendered."""
    if not isinstance(model, dict) or model.get("kind") != "quadratic_function":
        raise ValueError("unknown mathematical model")
    exact = model.get("exact_coefficients")
    if not isinstance(exact, dict):
        raise ValueError("missing exact quadratic coefficients")
    spec = {
        "kind": "quadratic_function",
        "coefficients": exact,
        "domain": model.get("domain"),
        "samples": len(model.get("curve", [])),
    }
    expected = build_computed_model(spec)
    for key in ("coefficients", "vertex", "x_intercepts", "y_intercept",
                "axis_of_symmetry", "discriminant", "y_bounds", "curve"):
        if not _nearly_equal(expected[key], model.get(key)):
            raise ValueError(f"mathematical model mismatch in {key}")


def _nearly_equal(first: object, second: object) -> bool:
    if isinstance(first, dict):
        return isinstance(second, dict) and first.keys() == second.keys() and all(
            _nearly_equal(v, second[k]) for k, v in first.items())
    if isinstance(first, list):
        return isinstance(second, list) and len(first) == len(second) and all(
            _nearly_equal(a, b) for a, b in zip(first, second))
    if isinstance(first, (int, float)):
        return (isinstance(second, (int, float)) and
                math.isclose(first, second, rel_tol=1e-8, abs_tol=1e-8))
    return first == second
