"""Unified verified, opt-in mathematical visual model gateway."""
from pipeline.math_models import build_computed_model, validate_computed_model
from pipeline.geometry_models import build_geometry_model, validate_geometry_model

SUPPORTED_KINDS = frozenset({"quadratic_function", "right_triangle", "circle"})


def build_verified_visual_model(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("math_model must be an object")
    if spec.get("kind") == "quadratic_function":
        return build_computed_model(spec)
    if spec.get("kind") in {"right_triangle", "circle"}:
        return build_geometry_model(spec)
    raise ValueError(f"unsupported verified math visualization {spec.get('kind')!r}")


def validate_verified_visual_model(model: dict) -> None:
    if not isinstance(model, dict):
        raise ValueError("math_model must be an object")
    if model.get("kind") == "quadratic_function":
        return validate_computed_model(model)
    if model.get("kind") in {"right_triangle", "circle"}:
        return validate_geometry_model(model)
    raise ValueError("unsupported mathematical visual model")
