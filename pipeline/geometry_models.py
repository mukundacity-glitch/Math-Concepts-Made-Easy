"""Verified Grade 9–12 right-triangle and circle diagrams from exact inputs."""
from __future__ import annotations

import math
from sympy import pi, sqrt

from pipeline.math_models import _rational, _nearly_equal


def build_geometry_model(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("geometry model specification must be an object")
    kind = spec.get("kind")
    if kind == "right_triangle":
        sides = spec.get("legs")
        if not isinstance(sides, dict) or set(sides) != {"a", "b"}:
            raise ValueError("right triangle needs exactly leg lengths a and b")
        a = _rational(sides["a"], "triangle leg a")
        b = _rational(sides["b"], "triangle leg b")
        if a <= 0 or b <= 0 or max(float(a), float(b)) > 10000:
            raise ValueError("triangle leg lengths must be positive and bounded")
        hyp = sqrt(a*a + b*b)
        return {
            "kind": kind,
            "exact_inputs": {"a": str(a), "b": str(b)},
            "vertices": [{"x": 0.0, "y": 0.0},
                         {"x": float(a), "y": 0.0},
                         {"x": 0.0, "y": float(b)}],
            "legs": {"a": float(a), "b": float(b)},
            "hypotenuse": float(hyp),
            "area": float(a*b / 2),
            "right_angle_vertex": 0,
            "pythagorean_residual": float(hyp**2 - a**2 - b**2),
        }
    if kind == "circle":
        radius = _rational(spec.get("radius"), "circle radius")
        if radius <= 0 or float(radius) > 10000:
            raise ValueError("circle radius must be positive and bounded")
        return {
            "kind": kind,
            "exact_inputs": {"radius": str(radius)},
            "center": {"x": 0.0, "y": 0.0},
            "radius": float(radius),
            "diameter": float(2*radius),
            "circumference": float(2*pi*radius),
            "area": float(pi*radius*radius),
        }
    raise ValueError(f"unsupported geometry model kind {kind!r}")


def validate_geometry_model(model: dict) -> None:
    if not isinstance(model, dict) or model.get("kind") not in {
            "right_triangle", "circle"}:
        raise ValueError("unsupported or absent geometry model")
    spec = {"kind": model["kind"]}
    spec["legs" if model["kind"] == "right_triangle" else "radius"] = (
        model.get("exact_inputs", {}) if model["kind"] == "right_triangle"
        else model.get("exact_inputs", {}).get("radius")
    )
    expected = build_geometry_model(spec)
    if not _nearly_equal(expected, model):
        raise ValueError("geometry has been altered from independently computed values")
