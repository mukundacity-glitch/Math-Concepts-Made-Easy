"""Renderer-backed visual vocabulary; all numerical content comes from data."""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

VISUAL_MODELS = frozenset({
    "function_machine", "coordinate_graph", "unit_circle", "number_line", "countable_objects", "algebra_area",
    "area_tiles", "probability_tree", "data_plot", "vectors", "equation_steps",
})
STYLES = ("paper", "midnight", "blueprint")


def validate_visual(value: Any) -> dict:
    if not isinstance(value, dict) or value.get("model") not in VISUAL_MODELS:
        raise ValueError("visual must name an implemented model")
    visual = deepcopy(value)
    for name in ("xRange", "yRange"):
        if name in visual:
            bounds = visual[name]
            if (not isinstance(bounds, list) or len(bounds) != 2
                    or any(type(item) not in (int, float) or not math.isfinite(item) for item in bounds)
                    or bounds[0] >= bounds[1] or not bounds[0] <= 0 <= bounds[1]):
                raise ValueError(f"visual.{name} must be increasing finite bounds containing zero")
    labels = visual.get("labels", [])
    if not isinstance(labels, list) or any(not isinstance(item, str) for item in labels):
        raise ValueError("visual.labels must be a list of strings")
    values = visual.get("values", [])
    if not isinstance(values, list) or any(type(item) not in (int, float) or not math.isfinite(item) for item in values):
        raise ValueError("visual.values must be finite numbers")
    if visual["model"] == "countable_objects":
        if not values or any(type(item) is not int or item < 0 for item in values) or sum(values) > 24:
            raise ValueError("countable_objects requires integer groups with at most 24 objects")
        removed = visual.get("remove", 0)
        if type(removed) is not int or not 0 <= removed <= sum(values):
            raise ValueError("object removal must be an integer within the object count")
    if visual["model"] in ("area_tiles", "algebra_area") and (len(values) != 2 or any(type(item) is not int or not 1 <= item <= 7 for item in values)):
        raise ValueError("area_tiles requires two integer dimensions from 1 to 7")
    if visual["model"] == "data_plot" and (not values or any(item < 0 for item in values)):
        raise ValueError("data_plot requires nonnegative values")
    if visual["model"] == "function_machine" and (not 2 <= len(labels) <= 4 or len(values) != len(labels)):
        raise ValueError("function_machine requires 2–4 labels and one value per stage")
    if visual["model"] == "probability_tree" and not 1 <= len(labels) <= 5:
        raise ValueError("probability_tree requires 1–5 labelled branches")
    if visual["model"] in ("coordinate_graph", "vectors"):
        series = visual.get("points")
        if not isinstance(series, list) or not series:
            raise ValueError("graph/vector models require explicit points")
        for points in series:
            if not isinstance(points, list) or len(points) < 2:
                raise ValueError("each graph series requires at least two points")
            if visual["model"] == "vectors" and len(points) != 2:
                raise ValueError("each vector requires exactly two endpoints")
            for point in points:
                if (not isinstance(point, list) or len(point) != 2
                        or any(type(item) not in (int, float) or not math.isfinite(item) for item in point)):
                    raise ValueError("graph coordinates must be finite pairs")
    if "angle" in visual and (type(visual["angle"]) not in (int, float) or not math.isfinite(visual["angle"])):
        raise ValueError("visual.angle must be finite radians")
    return visual
